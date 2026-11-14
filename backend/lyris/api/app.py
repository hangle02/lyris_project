"""FastAPI app: `create_app()` cho test, `app` ở cấp module cho uvicorn (`lyris.api.app:app`)."""
from __future__ import annotations

import asyncio
import logging
import sys
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from lyris.accounts import AccountInputError
from lyris.analytics import store as analytics_store
from lyris.analytics.forwarder import PostHogForwarder
from lyris.analytics.tracker import Tracker
from lyris.api.routes import router
from lyris.api.routes_accounts import router as accounts_router
from lyris.api.routes_admin import router as admin_router
from lyris.api.routes_analytics import admin_router as analytics_admin_router
from lyris.api.routes_analytics import router as analytics_router
from lyris.api.routes_auth import router as auth_router
from lyris.api.routes_coins import admin_router as coins_admin_router
from lyris.api.routes_coins import explore_router as hot_router
from lyris.api.routes_coins import router as coins_router
from lyris.api.routes_compliance import admin_router as compliance_admin_router
from lyris.api.routes_compliance import public_router as legal_router
from lyris.api.routes_compliance import router as compliance_router
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
from lyris.coins.errors import IDEM_CONFLICT_DETAIL, AdjustRejected, CoinsRequired, HoldBusy, IdemConflict
from lyris.coins.missions import MissionRejected
from lyris.coins.topup import TopupRejected
from lyris.coins.wallet import CoinService, emit_restart_releases
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
analytics_logger = logging.getLogger("lyris.analytics")

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
        analytics_store.purge(conn, now)  # sự kiện cũ hơn 180 ngày (docs/tracking-plan.md)
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
        try:
            with repo.transaction():
                events = analytics_store.purge(repo.conn, clock.now())
            if events:
                analytics_logger.info("Đã dọn %d sự kiện cũ hơn 180 ngày", events)
        except Exception:
            analytics_logger.exception("Không dọn được sự kiện cũ")


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

    @app.exception_handler(CoinsRequired)
    async def _coins_required(_: Request, exc: CoinsRequired) -> JSONResponse:
        # F42 (docs/coins.md §3.3): hết coin, trước khi stream (lỗi được "mồi" như 404/409).
        return JSONResponse(status_code=402, content=exc.payload())

    @app.exception_handler(HoldBusy)
    async def _hold_busy(_: Request, exc: HoldBusy) -> JSONResponse:
        return _error(409, "Bạn đang có một việc khác của AI chưa xong. Đợi xong rồi thử lại nhé.")

    @app.exception_handler(AdjustRejected)
    async def _adjust_rejected(_: Request, exc: AdjustRejected) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": exc.detail, "code": exc.code})

    @app.exception_handler(TopupRejected)
    async def _topup_rejected(_: Request, exc: TopupRejected) -> JSONResponse:
        # F43 (docs/coins.md §4.3): mã nạp sai (một câu cho mọi lý do), chủ máy nhập mã, thử sai quá nhiều, quá 50 mã.
        return JSONResponse(status_code=exc.status, content=exc.payload())

    @app.exception_handler(MissionRejected)
    async def _mission_rejected(_: Request, exc: MissionRejected) -> JSONResponse:
        # F45 (docs/coins.md §6, §7): ad_limit, ad_not_finished, ad_expired, mission_not_done, mission_cap, no_missions.
        return JSONResponse(status_code=exc.status, content=exc.payload())

    @app.exception_handler(IdemConflict)
    async def _idem_conflict(_: Request, exc: IdemConflict) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": IDEM_CONFLICT_DETAIL, "code": "idem_conflict"})

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
    start_forwarder: bool | None = None,
    posthog_transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    """Tạo app. `settings` mặc định đọc từ biến môi trường lúc khởi động; `llm` mặc định là OllamaClient.

    `start_worker`: chạy worker job nền (Phase 3) trong lifespan. None = chỉ chạy khi dùng Ollama thật
    (`llm` None); test truyền LLM giả thì worker không tự chạy, test gọi `app.state.worker.run_until_idle()`.

    Event tracking: `app.state.analytics` (Tracker) luôn có; `app.state.posthog` (PostHogForwarder) chỉ khi có
    `LYRIS_POSTHOG_KEY`. `start_forwarder` None = chạy task gửi nền khi có khoá; test truyền False và gọi
    `app.state.posthog.flush()`, kèm `posthog_transport` giả.
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
            # F42 (docs/coins.md §3.2a): ví coin dùng chung cho chat, chat thử và route /api/coins.
            coins = CoinService(repo, enabled=cfg.coins_enabled, ad_seconds=cfg.ad_seconds)
            app.state.coins = coins
            app.state.chat = ChatService(
                repo, client, budget=budget, state=state, jobs=jobs, lore=lore, gate=gate, coins=coins
            )
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
            # Event tracking (docs/tracking-plan.md): ghi vào DB; có khoá PostHog thì chuyển tiếp nền.
            posthog: PostHogForwarder | None = None
            if cfg.posthog_key:
                posthog = PostHogForwarder(
                    repo, api_key=cfg.posthog_key, host=cfg.posthog_host, transport=posthog_transport
                )
            tracker = Tracker(repo, forward=posthog is not None)
            if posthog is not None:
                tracker.on_pending = posthog.notify
            app.state.analytics = tracker
            app.state.posthog = posthog
            coins.tracker = tracker  # F44: sự kiện thưởng mốc của người tạo (ghi tách khỏi request)
            # F42 (docs/coins.md §3.2): máy tắt giữa chừng thì giữ chỗ coin còn `held` được nhả (không ai bị trừ cho
            # lượt không có chữ). CHỈ ở đây, trước khi nhận request: CLI, migrate(), script, test không nhả.
            released = coins.release_stale()
            if released:
                logger.info("Đã nhả %d giữ chỗ coin còn mở từ lần chạy trước", len(released))
                emit_restart_releases(tracker, released)
            if posthog is not None and (start_forwarder if start_forwarder is not None else True):
                await posthog.start()
            cleanup = asyncio.create_task(_auth_cleanup_loop(repo))
            logger.info("Lyris sẵn sàng: DB %s, model %s, Ollama %s", cfg.db_path, cfg.chat_model, cfg.ollama_url)
            try:
                yield
            finally:
                cleanup.cancel()
                if posthog is not None:
                    await posthog.stop()
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
    app.include_router(analytics_admin_router)
    app.include_router(analytics_router)
    app.include_router(compliance_admin_router)
    app.include_router(legal_router)
    app.include_router(router)
    app.include_router(studio_router)
    app.include_router(lyris_router)
    app.include_router(state_router)
    app.include_router(accounts_router)
    app.include_router(lore_router)
    app.include_router(compliance_router)
    app.include_router(coins_router)
    app.include_router(coins_admin_router)
    app.include_router(hot_router)
    return app


app = create_app()

__all__ = ["app", "create_app", "prepare_auth"]
