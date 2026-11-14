"""Trạng thái máy Mac và Ollama cho modal "Persona & Máy chủ" (GET /api/system).

Đọc bằng các lệnh macOS có sẵn (mỗi lệnh timeout 2 giây) và API HTTP của Ollama (`/api/version`,
`/api/tags`, `/api/ps`, timeout 2 giây). Lỗi ở phần nào thì phần đó là None/rỗng; không bao giờ raise.
Kết quả được cache 5 giây (`SystemMonitor`) để modal làm mới 10 giây một lần không chạy lệnh liên tục.

Đơn vị: RAM tính theo GiB (2^30 byte, máy "24 GB" hiện 24.0); dung lượng model theo GB thập phân
(10^9 byte) giống `ollama list`.
"""
from __future__ import annotations

import asyncio
import re
import subprocess
import time
from collections.abc import Callable
from typing import Any

import httpx

from lyris.models import LoadedModelInfo, OllamaModelInfo, SystemInfo

COMMAND_TIMEOUT_S = 2.0
OLLAMA_TIMEOUT_S = 2.0
CACHE_TTL_S = 5.0
GIB = 1024**3
GB = 1000**3

# Chạy một lệnh, trả stdout (None khi lỗi, timeout hoặc mã thoát khác 0).
Runner = Callable[[list[str]], str | None]


def run_command(args: list[str], timeout: float = COMMAND_TIMEOUT_S) -> str | None:
    try:
        proc = subprocess.run(  # noqa: S603 - lệnh cố định, không qua shell
            args, capture_output=True, text=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


# ---------------------------------------------------------------------------- parse (hàm thuần)


def parse_memsize(text: str | None) -> float | None:
    """`sysctl -n hw.memsize` (byte) -> GiB, làm tròn 1 chữ số."""
    if not text:
        return None
    try:
        value = int(text.strip())
    except ValueError:
        return None
    return round(value / GIB, 1) if value > 0 else None


_PAGE_SIZE = re.compile(r"page size of (\d+) bytes")
_VM_LINE = re.compile(r'^"?([A-Za-z][^:"]*?)"?\s*:\s*(\d+)\.?\s*$', re.M)


def parse_vm_stat(text: str | None) -> float | None:
    """`vm_stat` -> RAM đang dùng (GiB) = (active + wired + compressed) x page size."""
    if not text:
        return None
    m = _PAGE_SIZE.search(text)
    if m is None:
        return None
    page = int(m.group(1))
    pages = {name.strip().lower(): int(value) for name, value in _VM_LINE.findall(text)}
    needed = ("pages active", "pages wired down", "pages occupied by compressor")
    if not all(k in pages for k in needed):
        return None
    used = sum(pages[k] for k in needed) * page
    return round(used / GIB, 1)


def parse_on_battery(text: str | None) -> bool | None:
    """`pmset -g batt`: dòng đầu "Now drawing from 'Battery Power'" / "'AC Power'"."""
    if not text:
        return None
    m = re.search(r"drawing from '([^']+)'", text)
    if m is None:
        return None
    source = m.group(1).lower()
    if "battery" in source:
        return True
    if "ac" in source.split() or "ac power" in source:
        return False
    return None


def parse_low_power(text: str | None) -> bool | None:
    """`pmset -g`: dòng " lowpowermode         1". Máy đời mới có thể chỉ có " powermode N"
    (0 tự động, 1 tiết kiệm pin, 2 hiệu năng cao). Không có dòng nào -> None."""
    if not text:
        return None
    m = re.search(r"^\s*lowpowermode\s+(\d+)\s*$", text, re.M | re.I)
    if m is not None:
        return int(m.group(1)) != 0
    m = re.search(r"^\s*powermode\s+(\d+)\s*$", text, re.M | re.I)
    if m is not None:
        return int(m.group(1)) == 1
    return None


def parse_env_str(text: str | None) -> str | None:
    value = (text or "").strip()
    return value or None


def parse_env_bool(text: str | None) -> bool | None:
    value = (text or "").strip().lower()
    if value in ("1", "true", "yes", "on"):
        return True
    if value in ("0", "false", "no", "off"):
        return False
    return None


def parse_env_int(text: str | None) -> int | None:
    value = (text or "").strip()
    try:
        return int(value)
    except ValueError:
        return None


def _gb(value: Any, unit: int = GB) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float) or value <= 0:
        return None
    return round(value / unit, 1)


def _str_or_none(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def parse_tags(data: Any) -> list[OllamaModelInfo]:
    """Body của GET /api/tags -> danh sách model (theo tên)."""
    models = data.get("models") if isinstance(data, dict) else None
    if not isinstance(models, list):
        return []
    out: list[OllamaModelInfo] = []
    for m in models:
        if not isinstance(m, dict):
            continue
        name = _str_or_none(m.get("name")) or _str_or_none(m.get("model"))
        if name is None:
            continue
        details = m.get("details") if isinstance(m.get("details"), dict) else {}
        out.append(
            OllamaModelInfo(
                name=name,
                size_gb=_gb(m.get("size")),
                parameter_size=_str_or_none(details.get("parameter_size")),
                quantization=_str_or_none(details.get("quantization_level")),
            )
        )
    return sorted(out, key=lambda x: x.name.lower())


def parse_ps(data: Any) -> list[LoadedModelInfo]:
    """Body của GET /api/ps -> các model đang nạp trong RAM."""
    models = data.get("models") if isinstance(data, dict) else None
    if not isinstance(models, list):
        return []
    out: list[LoadedModelInfo] = []
    for m in models:
        if not isinstance(m, dict):
            continue
        name = _str_or_none(m.get("name")) or _str_or_none(m.get("model"))
        if name is None:
            continue
        out.append(
            LoadedModelInfo(name=name, size_gb=_gb(m.get("size")), expires_at=_str_or_none(m.get("expires_at")))
        )
    return out


# ---------------------------------------------------------------------------- thu thập


def collect_machine(runner: Runner = run_command) -> dict[str, Any]:
    """Các trường phần máy của SystemInfo (chạy lệnh đồng bộ, gọi trong thread)."""

    def run(*args: str) -> str | None:
        try:
            return runner(list(args))
        except Exception:  # runner tự viết (test) lỗi cũng không được làm hỏng cả endpoint
            return None

    def getenv(name: str) -> str | None:
        return run("launchctl", "getenv", name)

    return {
        "memory_total_gb": parse_memsize(run("sysctl", "-n", "hw.memsize")),
        "memory_used_gb": parse_vm_stat(run("vm_stat")),
        "on_battery": parse_on_battery(run("pmset", "-g", "batt")),
        "low_power_mode": parse_low_power(run("pmset", "-g")),
        "kv_cache_type": parse_env_str(getenv("OLLAMA_KV_CACHE_TYPE")),
        "flash_attention": parse_env_bool(getenv("OLLAMA_FLASH_ATTENTION")),
        "num_parallel": parse_env_int(getenv("OLLAMA_NUM_PARALLEL")),
        "max_loaded_models": parse_env_int(getenv("OLLAMA_MAX_LOADED_MODELS")),
    }


async def _get_json(client: httpx.AsyncClient, path: str) -> Any:
    """GET path -> JSON; None khi lỗi mạng, HTTP lỗi hoặc body không phải JSON."""
    try:
        resp = await client.get(path)
    except httpx.HTTPError:
        return None
    if resp.status_code != 200:
        return None
    try:
        return resp.json()
    except ValueError:
        return None


async def collect_ollama(
    base_url: str | None, transport: httpx.AsyncBaseTransport | None = None
) -> dict[str, Any]:
    """Các trường phần Ollama của SystemInfo. `base_url` None = app không dùng Ollama (LLM giả khi test)."""
    if not base_url:
        return {
            "ollama_reachable": False,
            "ollama_error": "Lyris đang chạy với LLM thử nghiệm, không kết nối Ollama.",
        }
    timeout = httpx.Timeout(OLLAMA_TIMEOUT_S)
    try:
        async with httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=timeout, transport=transport) as client:
            version, tags, ps = await asyncio.gather(
                _get_json(client, "/api/version"), _get_json(client, "/api/tags"), _get_json(client, "/api/ps")
            )
    except Exception:
        version = tags = ps = None
    reachable = version is not None or tags is not None
    out: dict[str, Any] = {
        "ollama_reachable": reachable,
        "ollama_version": _str_or_none(version.get("version")) if isinstance(version, dict) else None,
        "models": parse_tags(tags),
        "loaded": parse_ps(ps),
    }
    if not reachable:
        out["ollama_error"] = (
            f"Không kết nối được Ollama ở {base_url.rstrip('/')}. Hãy mở app Ollama (hoặc chạy `ollama serve`)."
        )
    return out


async def collect_system_info(
    *,
    base_url: str | None,
    chat_model_default: str,
    transport: httpx.AsyncBaseTransport | None = None,
    runner: Runner = run_command,
) -> SystemInfo:
    """SystemInfo đầy đủ; phần máy chạy trong thread song song với các lời gọi Ollama."""
    try:
        machine, ollama = await asyncio.gather(
            asyncio.to_thread(collect_machine, runner), collect_ollama(base_url, transport)
        )
    except Exception:  # phòng hờ: endpoint không bao giờ 500
        machine, ollama = {}, {"ollama_reachable": False}
    return SystemInfo(**{**machine, **ollama, "chat_model_default": chat_model_default})


class SystemMonitor:
    """Cache SystemInfo trong `ttl` giây; nhiều request cùng lúc chỉ đo một lần.

    Cache theo `chat_model_default`: đổi model mặc định thì lần gọi sau đo lại ngay.
    """

    def __init__(
        self,
        *,
        base_url: str | None,
        transport: httpx.AsyncBaseTransport | None = None,
        runner: Runner = run_command,
        ttl: float = CACHE_TTL_S,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.base_url = base_url
        self.transport = transport
        self.runner = runner
        self.ttl = ttl
        self._clock = clock
        self._lock = asyncio.Lock()
        self._cached: SystemInfo | None = None
        self._at = 0.0

    def invalidate(self) -> None:
        self._cached = None

    async def get(self, chat_model_default: str) -> SystemInfo:
        async with self._lock:
            now = self._clock()
            cached = self._cached
            if cached is not None and now - self._at < self.ttl and cached.chat_model_default == chat_model_default:
                return cached
            info = await collect_system_info(
                base_url=self.base_url,
                chat_model_default=chat_model_default,
                transport=self.transport,
                runner=self.runner,
            )
            self._cached, self._at = info, self._clock()
            return info


__all__ = [
    "CACHE_TTL_S",
    "Runner",
    "SystemMonitor",
    "collect_machine",
    "collect_ollama",
    "collect_system_info",
    "parse_env_bool",
    "parse_env_int",
    "parse_low_power",
    "parse_memsize",
    "parse_on_battery",
    "parse_ps",
    "parse_tags",
    "parse_vm_stat",
    "run_command",
]
