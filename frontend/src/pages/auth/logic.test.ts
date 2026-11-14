import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  authFieldOf,
  contactHref,
  FORGOT_TEXT,
  loginHandle,
  logoutAllConfirm,
  NO_INVITE_TEXT,
  SIGNUP_PRIVACY,
  TAGLINE,
} from "./logic.ts";

test("authFieldOf puts server sentences under the right field", () => {
  assert.equal(authFieldOf("Mã mời không đúng hoặc đã hết hạn."), "code");
  assert.equal(authFieldOf("Mã thiết lập không đúng. Xem lại dòng in trong cửa sổ Terminal đang chạy Lyris."), "code");
  assert.equal(authFieldOf("Mật khẩu này quá dễ đoán. Hãy chọn mật khẩu khác."), "password");
  assert.equal(authFieldOf("Mật khẩu không được giống tên đăng nhập."), "password");
  assert.equal(authFieldOf("Mật khẩu mới phải khác mật khẩu cũ."), "password");
  assert.equal(authFieldOf("Mật khẩu hiện tại không đúng."), "current");
  assert.equal(authFieldOf("Handle @mai đã có người dùng."), "handle");
  assert.equal(authFieldOf("Tên hiển thị dài tối đa 60 ký tự."), "display_name");
  // General: shown above or under the button, never under one field.
  assert.equal(authFieldOf("Tên đăng nhập hoặc mật khẩu không đúng."), null);
  assert.equal(authFieldOf("Bạn đã thử sai nhiều lần. Hãy đợi 15 phút rồi thử lại."), null);
  assert.equal(authFieldOf("Mật khẩu tạm đã hết hạn. Hãy nhờ người quản lý Lyris đặt lại."), null);
  assert.equal(authFieldOf("Tài khoản này đang tạm khoá. Hãy liên hệ người quản lý Lyris."), null);
});

test("loginHandle trims; logoutAllConfirm names the handle once", () => {
  assert.equal(loginHandle("  @MinhThu  "), "@MinhThu");
  assert.equal(
    logoutAllConfirm("@minhthu.viet"),
    "Mọi điện thoại và máy tính đang đăng nhập @minhthu.viet sẽ phải đăng nhập lại, kể cả máy này.",
  );
});

test("tagline matches README and the PWA manifest / meta description", () => {
  assert.equal(TAGLINE, "Nơi những tâm hồn từ trang sách bước ra sưởi ấm thực tại");
  const manifest = JSON.parse(readFileSync(new URL("../../../public/manifest.webmanifest", import.meta.url), "utf8"));
  assert.ok(String(manifest.description).startsWith(TAGLINE), manifest.description);
  const html = readFileSync(new URL("../../../index.html", import.meta.url), "utf8");
  assert.ok(html.includes(`content="Lyris: ${TAGLINE.charAt(0).toLowerCase()}${TAGLINE.slice(1)}.`), "index.html meta description");
  const readme = readFileSync(new URL("../../../../README.md", import.meta.url), "utf8");
  assert.ok(readme.includes(TAGLINE));
});

test("open-web copy: no 'this Mac' / 'chủ máy' for visitors; a way to get a code or reset a password", () => {
  for (const text of [SIGNUP_PRIVACY, FORGOT_TEXT, NO_INVITE_TEXT]) {
    assert.ok(!/chủ máy|máy này|Mac/.test(text), text);
  }
  assert.match(SIGNUP_PRIVACY, /máy chủ chạy Lyris/);
  assert.equal(contactHref("hotro@lyris.vn", "Xin mã mời Lyris"), "mailto:hotro@lyris.vn?subject=Xin%20m%C3%A3%20m%E1%BB%9Di%20Lyris");
  assert.equal(contactHref("https://lyris.vn/lien-he", "x"), "https://lyris.vn/lien-he");
  assert.equal(contactHref("http://lyris.vn", "x"), null);
  assert.equal(contactHref("javascript:alert(1)", "x"), null);
  assert.equal(contactHref(null, "x"), null);
  assert.equal(contactHref("  ", "x"), null);
});
