"""Fixture dùng chung: repo SQLite trong bộ nhớ (đã migrate) và repo đã seed."""
from __future__ import annotations

import importlib
import re
import sys
import types
from collections.abc import Iterator
from pathlib import Path

import pytest

# Phòng khi bản cài editable của package `lyris` hỏng (thiếu file .pth trong .venv):
# thêm thư mục backend/ vào sys.path để `import lyris` luôn trỏ tới mã nguồn.
_BACKEND_DIR = str(Path(__file__).resolve().parents[1])
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from lyris.db.connection import connect, migrate  # noqa: E402
from lyris.db.repo import Repo  # noqa: E402


def thought_module_available() -> bool:
    """lyris.llm.thought do module [llm] viết song song; có thể chưa có."""
    try:
        importlib.import_module("lyris.llm.thought")
    except ImportError:
        return False
    return True


def _stub_split_thought(raw: str) -> tuple[str, str | None]:
    """Bản tạm chỉ dùng trong test khi lyris.llm.thought chưa có."""
    thoughts = [t.strip() for t in re.findall(r"\[\s*thought\s*:(.*?)\]", raw, flags=re.I | re.S)]
    visible = re.sub(r"\[\s*thought\s*:.*?\]", "", raw, flags=re.I | re.S)
    visible = re.sub(r"\n{3,}", "\n\n", visible).strip()
    return visible, ("\n".join(thoughts) if thoughts else None)


@pytest.fixture
def repo() -> Iterator[Repo]:
    conn = connect(":memory:")
    migrate(conn)
    try:
        yield Repo(conn)
    finally:
        conn.close()


@pytest.fixture
def seeded_repo(repo: Repo, monkeypatch: pytest.MonkeyPatch) -> Repo:
    from lyris.seed import ensure_seed

    if not thought_module_available():
        stub = types.ModuleType("lyris.llm.thought")
        stub.split_thought = _stub_split_thought  # type: ignore[attr-defined]
        stub.LYRIS_TEST_STUB = True  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "lyris.llm.thought", stub)
    ensure_seed(repo)
    return repo
