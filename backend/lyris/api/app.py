"""FastAPI app: `create_app()` cho test, `app` ở cấp module cho uvicorn (`lyris.api.app:app`)."""
from __future__ import annotations

import asyncio
import logging
import sys
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from lyris.accounts import AccountInputError
from lyris.api.routes import router
from lyris.api.routes_accounts import router as accounts_router
from lyris.api.routes_admin import router as admin_router
from lyris.api.routes_auth import router as auth_router
from lyris.api.routes_lore import router as lore_router
from lyris.api.routes_lyris import router as lyris_router
from lyris.api.routes_state import router as state_router
from lyris.api.routes_studio import router as studio_router
from lyris.auth import clock
from lyris.auth import setup as owner_setup
from lyris.auth import store as auth_store
from lyris.auth.errors import AuthError
from lyris.auth.middleware import AuthMiddleware
from lyris.chat.gate import GenerationGate
from lyris.chat.service import Busy, ChatService, EmptyContent, InvalidOperation
from lyris.config import Settings, get_settings, migrate_legacy_db
from lyris.db.connection import connect, migrate
from lyris.db.repo import ANY_ACCOUNT, HandleTaken, InUse, NotFound, Repo
from lyris.jobs import JobQueue, Worker
from lyris.llm.base import LLMClient
from lyris.llm.errors import UserFacingError
from lyris.llm.ollama import OllamaClient
from lyris.lore.service import LoreInputError, LoreLimitError, LoreService
from lyris.prompt.builder import PromptBudget
from lyris.seed import ensure_seed
from lyris.state.service import ModelCatalog, StateService
from lyris.studio.avatars import AvatarError, cleanup_temp, remove_avatar
from lyris.studio.card_v2 import CardImportError
from lyris.studio.draft import DraftError
from lyris.system import SystemMonitor

logger = logging.getLogger("lyris.api")
auth_logger = logging.getLogger("lyris.auth")

# Dọn phiên hết hạn và lần thử cũ (docs/auth.md §1.4, §3.4): lúc khởi động và mỗi giờ.
AUTH_CLEANUP_SECONDS = 3600


def _install_auth_logging() -> None:
    """uvicorn chỉ cấu hình logger `uvicorn.*`: không gắn handler thì mọi dòng INFO của `lyris.auth` mất
    (docs/auth.md §3.6). Chỉ gắn khi chưa có handler."""
    if not auth_logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(levelname)s:     %(name)s: %(message)s"))
        auth_logger.addHandler(handler)
    if auth_logger.level == logging.NOTSET:
        auth_logger.setLevel(logging.INFO)


def prepare_auth(repo: Repo) -> str | None:
    """Lúc khởi động: dọn phiên/lần thử cũ; chủ máy chưa có mật khẩu thì sinh mã thiết lập mới (ghi đè mã
    cũ) và trả mã để in ra Terminal. Có mật khẩu rồi thì bỏ mã cũ còn sót."""
    repo.owner_account()  # DB chưa có tài khoản nào thì tạo chủ máy mặc định
    now = clock.now()
    with repo.transaction():
        conn = repo.conn
        auth_store.purge(conn, now)
        if auth_store.owner_needs_setup(conn):
            return owner_setup.write_new_code(conn, now)
        auth_store.delete_setup(conn)
    return None


async def _auth_cleanup_loop(repo: Repo) -> None:
    while True:
        await asyncio.sleep(AUTH_CLEANUP_SECONDS)
        try:
            with repo.transaction():
                sessions, attempts = auth_store.purge(repo.conn, clock.now())
            if sessions or attempts:
                auth_logger.info("Đã dọn %d phiên hết hạn, %d lần thử cũ", sessions, attempts)
        except Exception:
            auth_logger.exception("Không dọn được phiên hết hạn")


def _error(status: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": detail})


def _ctx(err: Mapping[str, Any], key: str) -> str:
    ctx = err.get("ctx") or {}
    value = ctx.get(key, "") if isinstance(ctx, Mapping) else ""
    return str(value)


def _error_text(err: Mapping[str, Any]) -> str:
    """Thông điệp tiếng Việt cho các loại lỗi pydantic hay gặp; loại lạ thì ghi chung chung."""
    kind = str(err.get("type", ""))
    if kind == "missing":
        return "thiếu trường bắt buộc"
    if kind == "extra_forbidden":
        return "trường không được hỗ trợ"
    if kind == "string_too_long":
        return f"dài quá {_ctx(err, 'max_length')} ký tự"
    if kind == "string_too_short":
        return f"phải có ít nhất {_ctx(err, 'min_length')} ký tự"
    if kind in ("string_type", "string_unicode"):
        return "phải là chuỗi ký tự"
    if kind in ("int_type", "int_parsing", "int_from_float"):
        return "phải là số nguyên"
    if kind in ("bool_type", "bool_parsing"):
        return "phải là true hoặc false"
    if kind in ("greater_than_equal", "greater_than", "less_than_equal", "less_than"):
        limits = {
            "greater_than_equal": ("ge", "phải lớn hơn hoặc bằng"),
            "greater_than": ("gt", "phải lớn hơn"),
            "less_than_equal": ("le", "phải nhỏ hơn hoặc bằng"),
            "less_than": ("lt", "phải nhỏ hơn"),
        }
        key, text = limits[kind]
        return f"{text} {_ctx(err, key)}"
    if kind in ("literal_error", "enum"):
        expected = _ctx(err, "expected").replace(" or ", " hoặc ")
        return f"phải là một trong: {expected}" if expected else "giá trị không được phép"
    if kind in ("json_invalid", "json_type"):
        return "JSON không hợp lệ"
    if kind in ("model_type", "model_attributes_type", "dict_type"):
        return "phải là một object JSON"
    if kind == "list_type":
        return "phải là một danh sách"
    return "giá trị không hợp lệ"


def _validation_detail(exc: RequestValidationError) -> str:
    parts: list[str] = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err.get("loc", ()) if p not in ("body", "path", "query"))
        msg = _error_text(err)
        parts.append(f"{loc}: {msg}" if loc else msg)
    return "Dữ liệu không hợp lệ: " + "; ".join(parts) if parts else "Dữ liệu không hợp lệ."


def _install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AuthError)
    async def _auth_error(_: Request, exc: AuthError) -> JSONResponse:
        # Phase 4b: {detail, technical, code}; cookie cần xoá do AuthMiddleware gắn vào.
        return JSONResponse(status_code=exc.status, content=exc.payload(), headers=exc.headers or None)

    @app.exception_handler(NotFound)
    async def _not_found(_: Request, exc: NotFound) -> JSONResponse:
        return _error(404, str(exc) or "Không tìm thấy.")

    @app.exception_handler(Busy)
    async def _busy(_: Request, exc: Busy) -> JSONResponse:
        return _error(409, str(exc))

    @app.exception_handler(EmptyContent)
    async def _empty(_: Request, exc: EmptyContent) -> JSONResponse:
        # Nội dung rỗng là dữ liệu sai (422), không phải thao tác sai với trạng thái story (409).
        return _error(422, str(exc) or "Nội dung không được để trống.")

    @app.exception_handler(InvalidOperation)
    async def _invalid(_: Request, exc: InvalidOperation) -> JSONResponse:
        return _error(409, str(exc) or "Thao tác không hợp lệ.")

    @app.exception_handler(UserFacingError)
    async def _user_facing(_: Request, exc: UserFacingError) -> JSONResponse:
        # Phase 3b: câu dễ hiểu + chi tiết kỹ thuật (giao diện để dưới "Chi tiết").
        return JSONResponse(status_code=exc.status, content=exc.payload())

    @app.exception_handler(InUse)
    async def _in_use(_: Request, exc: InUse) -> JSONResponse:
        return _error(409, f"Có {exc.count} story đang dùng mục này. Xoá luôn các story đó?")

    @app.exception_handler(LoreLimitError)
    async def _lore_limit(_: Request, exc: LoreLimitError) -> JSONResponse:
        return _error(409, str(exc) or "Nhân vật này đã có quá nhiều mục thế giới.")

    async def _studio_input(_: Request, exc: Exception) -> JSONResponse:
        # Thông điệp của các lỗi này đã là câu tiếng Việt hoàn chỉnh cho người dùng.
        return _error(422, str(exc) or "Dữ liệu không hợp lệ.")

    for exc_type in (AvatarError, CardImportError, DraftError, AccountInputError, HandleTaken, LoreInputError):
        app.add_exception_handler(exc_type, _studio_input)

    @app.exception_handler(ValueError)
    async def _value_error(_: Request, exc: ValueError) -> JSONResponse:
        # Repo raise ValueError (và pydantic ValidationError) khi dữ liệu sai.
        return _error(422, f"Dữ liệu không hợp lệ: {exc}")

    @app.exception_handler(RequestValidationError)
    async def _request_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return _error(422, _validation_detail(exc))


def create_app(
    settings: Settings | None = None,
    llm: LLMClient | None = None,
    *,
    start_worker: bool | None = None,
) -> FastAPI:
    """Tạo app. `settings` mặc định đọc từ biến môi trường lúc khởi động; `llm` mặc định là OllamaClient.

    `start_worker`: chạy worker job nền (Phase 3) trong lifespan. None = chỉ chạy khi dùng Ollama thật
    (`llm` None); test truyền LLM giả thì worker không tự chạy, test gọi `app.state.worker.run_until_idle()`.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        cfg = settings or get_settings()
        if migrate_legacy_db(cfg.db_path):
            logger.info("Đã đổi tên DB cũ nora.db thành %s", cfg.db_path.name)
        conn = connect(cfg.db_path)
        try:
            migrate(conn)
            repo = Repo(conn)
            setup_code = prepare_auth(repo)
            if setup_code is not None:
                # In thẳng ra stderr (không qua logging): mã không được vào file log nào (docs/auth.md §2.4).
                owner_setup.print_banner(setup_code)
            had_story = bool(repo.list_stories(account_id=ANY_ACCOUNT))
            newest = ensure_seed(repo)
            # Story seed đầu tiên dùng model mặc định (cài đặt chung, không có thì LYRIS_CHAT_MODEL).
            seed_model = repo.default_chat_model() or cfg.chat_model
            if (
                newest is not None
                and not had_story
                and repo.get_story(newest, account_id=ANY_ACCOUNT).model_name != seed_model
            ):
                repo.update_story(newest, account_id=ANY_ACCOUNT, model_name=seed_model)
            # Phase 4b (docs/auth.md §4.3): bản sao nhân vật công khai không còn story nào (sót lại) thì dọn.
            repo.drop_orphan_copies()
            for name in repo.pop_orphan_avatars():
                remove_avatar(cfg.avatars_dir, name)
            client: LLMClient = llm if llm is not None else OllamaClient(cfg.ollama_url)
            budget = PromptBudget(num_ctx=cfg.num_ctx)
            app.state.settings = cfg
            app.state.repo = repo
            app.state.llm = client
            # Phase 4: sổ thế giới theo card (docs/phase4.md). Sửa sổ thì hẹn prefill lại (on_change bên dưới).
            lore = LoreService(repo)
            # Phase 3: state, hàng đợi job nền và worker (docs/phase3.md §4).
            state = StateService(
                repo,
                client,
                embed_model=cfg.embed_model,
                catalog=ModelCatalog.for_client(client),
                budget=budget,
                lore=lore,
            )
            jobs = JobQueue(repo, state)
            lore.on_change = jobs.lore_changed
            # Prefill lượt sau (§10.6) chỉ với Ollama thật; LLM tiêm vào (test) không có cache prompt.
            worker = Worker(
                repo, jobs, state, client, budget=budget, extract_model=cfg.extract_model, prefill=llm is None
            )
            app.state.state = state
            app.state.jobs = jobs
            app.state.worker = worker
            app.state.lore = lore
            # Phase 4b (§5.1): một cổng sinh cho cả máy (chat, gợi ý, chat thử, viết nháp).
            gate = GenerationGate(cfg.chat_slots)
            app.state.gate = gate
            app.state.chat = ChatService(repo, client, budget=budget, state=state, jobs=jobs, lore=lore, gate=gate)
            # Một lượt viết nháp / chat thử tại một thời điểm (bận -> 409); không chặn chat thường.
            app.state.draft_lock = asyncio.Lock()
            app.state.test_chat_lock = asyncio.Lock()
            app.state.template_lock = asyncio.Lock()
            # GET /api/system: đo máy + Ollama, cache 5 giây. LLM giả (test) không có base_url -> bỏ phần Ollama.
            app.state.system = SystemMonitor(
                base_url=getattr(client, "base_url", None), transport=getattr(client, "_transport", None)
            )
            try:
                removed = cleanup_temp(cfg.avatars_dir)
                if removed:
                    logger.info("Đã dọn %d ảnh tạm cũ trong %s", removed, cfg.avatars_dir)
            except OSError:
                logger.exception("Không dọn được ảnh tạm trong %s", cfg.avatars_dir)
            run_worker = start_worker if start_worker is not None else llm is None
            if run_worker and newest is not None and not had_story:
                # Phase 3b: lời mở đầu của story seed cũng được trích xuất (cảnh + ký ức). Chỉ khi worker tự
                # chạy (Ollama thật); test/script dùng LLM giả tự lái worker và tự quyết định việc này.
                jobs.story_created(newest)
            if run_worker:
                await worker.start()
            else:
                worker.recover()
            cleanup = asyncio.create_task(_auth_cleanup_loop(repo))
            logger.info("Lyris sẵn sàng: DB %s, model %s, Ollama %s", cfg.db_path, cfg.chat_model, cfg.ollama_url)
            try:
                yield
            finally:
                cleanup.cancel()
                await worker.stop()
        finally:
            conn.close()

    _install_auth_logging()
    # Phase 4b: tắt /openapi.json, /docs, /redoc (ngoài /api, không qua auth); test vẫn gọi app.openapi().
    # Không còn CORSMiddleware: frontend chỉ gọi /api tương đối qua proxy của Vite (docs/auth.md §3.3).
    app = FastAPI(
        title="Lyris", version="0.1.0", lifespan=lifespan, openapi_url=None, docs_url=None, redoc_url=None
    )
    app.add_middleware(AuthMiddleware)
    _install_error_handlers(app)
    app.include_router(auth_router)
    app.include_router(admin_router)
    app.include_router(router)
    app.include_router(studio_router)
    app.include_router(lyris_router)
    app.include_router(state_router)
    app.include_router(accounts_router)
    app.include_router(lore_router)
    return app


app = create_app()

__all__ = ["app", "create_app", "prepare_auth"]
