"""Lỗi đăng nhập (docs/auth.md §6.1): `{detail, technical, code}` để giao diện xử lý theo `code`."""
from __future__ import annotations

from typing import Any


class AuthError(Exception):
    """Lỗi trả thẳng cho giao diện. `detail` là câu tiếng Việt; `code` là mã máy đọc (`auth_required`...)."""

    def __init__(
        self, status: int, detail: str, code: str | None = None, *, headers: dict[str, str] | None = None
    ) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail
        self.code = code
        self.headers = headers or {}

    def payload(self) -> dict[str, Any]:
        out: dict[str, Any] = {"detail": self.detail, "technical": None}
        if self.code is not None:
            out["code"] = self.code
        return out


# Câu chữ (§6.1, §7.4). Không nhắc tới token, cookie, phiên, HTTP.
AUTH_REQUIRED = "Bạn cần đăng nhập."
LOGGED_OUT = "Bạn đã bị đăng xuất. Hãy đăng nhập lại."
PASSWORD_CHANGE_REQUIRED = "Hãy đặt mật khẩu mới để tiếp tục."
OWNER_ONLY = "Chỉ chủ máy làm được việc này."
CSRF = "Yêu cầu không hợp lệ. Hãy tải lại trang."
ACCOUNT_DISABLED = "Tài khoản này đang tạm khoá. Hãy liên hệ người quản lý Lyris."
SETUP_REQUIRED = "Lyris cần chủ máy đặt mật khẩu trước."
RATE_LIMITED = "Bạn đã thử sai nhiều lần. Hãy đợi 15 phút rồi thử lại."
BAD_LOGIN = "Tên đăng nhập hoặc mật khẩu không đúng."
TEMP_EXPIRED = "Mật khẩu tạm đã hết hạn. Hãy nhờ người quản lý Lyris đặt lại."
TEMP_EXPIRED_OWNER = "Mật khẩu tạm đã hết hạn. Chạy lại lệnh đặt lại mật khẩu trên Mac."
BAD_INVITE = "Mã mời không đúng hoặc đã hết hạn."
BAD_SETUP_CODE = "Mã thiết lập không đúng. Xem lại dòng in trong cửa sổ Terminal đang chạy Lyris."
ALREADY_SET_UP = "Lyris đã được thiết lập. Hãy đăng nhập."
BAD_CURRENT_PASSWORD = "Mật khẩu hiện tại không đúng."
BUSY = "Lyris đang bận. Hãy thử lại sau giây lát."


def auth_required(*, logged_out: bool = False) -> AuthError:
    return AuthError(401, LOGGED_OUT if logged_out else AUTH_REQUIRED, "auth_required")


def setup_required() -> AuthError:
    return AuthError(409, SETUP_REQUIRED, "setup_required")


def rate_limited(retry_after: int) -> AuthError:
    return AuthError(429, RATE_LIMITED, "rate_limited", headers={"Retry-After": str(max(1, retry_after))})




def busy() -> AuthError:
    """Hàng chờ băm mật khẩu đã đầy (`passwords.HashingBusy`): không có lần thử nào bị tính."""
    return AuthError(503, BUSY, "busy", headers={"Retry-After": "5"})
