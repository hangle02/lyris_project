import { test } from "node:test";
import assert from "node:assert/strict";
import { authFieldOf, loginHandle, logoutAllConfirm } from "./logic.ts";

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
  assert.equal(authFieldOf("Mật khẩu tạm đã hết hạn. Hãy nhờ chủ máy đặt lại."), null);
  assert.equal(authFieldOf("Tài khoản này đang tạm khoá. Hãy hỏi chủ máy."), null);
});

test("loginHandle trims; logoutAllConfirm names the handle once", () => {
  assert.equal(loginHandle("  @MinhThu  "), "@MinhThu");
  assert.equal(
    logoutAllConfirm("@minhthu.viet"),
    "Mọi điện thoại và máy tính đang đăng nhập @minhthu.viet sẽ phải đăng nhập lại, kể cả máy này.",
  );
});
