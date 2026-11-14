import { test } from "node:test";
import assert from "node:assert/strict";
import {
  accountBadges,
  devicesLine,
  disableConfirm,
  inviteBadge,
  inviteDateLine,
  isLocalOrigin,
  lastSeenLine,
  relativeTime,
  resetNote,
  revokeConfirm,
  sortAccounts,
  sortInvites,
} from "./logic.ts";
import type { AdminAccount, InviteOut } from "../../types.ts";

const NOW = new Date("2026-11-14T12:00:00.000Z");
const ago = (ms: number) => new Date(NOW.getTime() - ms).toISOString();
const MIN = 60_000;
const HOUR = 60 * MIN;
const DAY = 24 * HOUR;

test("invite badges: active is ok, the rest are quiet", () => {
  assert.deepEqual(inviteBadge({ status: "active", used_by_handle: null }), { label: "Còn hiệu lực", tone: "ok" });
  assert.deepEqual(inviteBadge({ status: "used", used_by_handle: "mai" }), { label: "Đã dùng bởi @mai", tone: "neutral" });
  assert.deepEqual(inviteBadge({ status: "used", used_by_handle: null }), { label: "Đã dùng", tone: "neutral" });
  assert.deepEqual(inviteBadge({ status: "expired", used_by_handle: null }), { label: "Hết hạn", tone: "neutral" });
  assert.deepEqual(inviteBadge({ status: "revoked", used_by_handle: null }), { label: "Đã huỷ", tone: "neutral" });
});

test("account badges: owner gold, disabled danger, waiting for a new password warn", () => {
  assert.deepEqual(accountBadges({ role: "owner", status: "active", must_change_password: false }), [{ label: "Chủ máy", tone: "gold" }]);
  assert.deepEqual(accountBadges({ role: "member", status: "active", must_change_password: false }), []);
  assert.deepEqual(accountBadges({ role: "member", status: "disabled", must_change_password: true }), [
    { label: "Tạm khoá", tone: "danger" },
    { label: "Chờ đổi mật khẩu", tone: "warn" },
  ]);
});

test("relative time in plain words", () => {
  assert.equal(relativeTime(ago(10_000), NOW), "vừa xong");
  assert.equal(relativeTime(ago(5 * MIN), NOW), "5 phút trước");
  assert.equal(relativeTime(ago(3 * HOUR), NOW), "3 giờ trước");
  assert.equal(relativeTime(ago(DAY + HOUR), NOW), "hôm qua");
  assert.equal(relativeTime(ago(4 * DAY), NOW), "4 ngày trước");
  assert.match(relativeTime(ago(45 * DAY), NOW) ?? "", /^\d{2}\/\d{2}\/2026$/);
  // A clock a bit ahead of the server's: never "in the future".
  assert.equal(relativeTime(new Date(NOW.getTime() + 5000).toISOString(), NOW), "vừa xong");
  assert.equal(relativeTime(null, NOW), null);
  assert.equal(relativeTime("không phải ngày", NOW), null);
});

test("last seen and devices lines", () => {
  assert.equal(lastSeenLine(ago(2 * HOUR), NOW), "Vào lần cuối 2 giờ trước");
  assert.equal(lastSeenLine(null, NOW), "Chưa đăng nhập lần nào");
  assert.equal(devicesLine(2), "2 thiết bị");
  assert.equal(devicesLine(0), "Không thiết bị nào đang đăng nhập");
});

test("invite date line and the sentences of the confirmations", () => {
  const exp = new Date(2026, 10, 21, 12, 0).toISOString();
  const made = new Date(2026, 10, 14, 12, 0).toISOString();
  assert.equal(inviteDateLine({ status: "active", expires_at: exp, created_at: made }), "Hết hạn 21/11/2026");
  assert.equal(inviteDateLine({ status: "expired", expires_at: exp, created_at: made }), "Hết hạn 21/11/2026");
  assert.equal(inviteDateLine({ status: "used", expires_at: exp, created_at: made }), "Tạo 14/11/2026");
  assert.equal(revokeConfirm("4TPA"), "Huỷ mã …4TPA? Ai đang giữ mã này sẽ không dùng được nữa.");
  assert.equal(
    resetNote("mai"),
    "Gửi mật khẩu này cho @mai. Mật khẩu chỉ hiện một lần, dùng được 3 ngày, và @mai sẽ phải đổi ngay khi đăng nhập.",
  );
  assert.match(disableConfirm("mai"), /^@mai sẽ bị đăng xuất khỏi mọi thiết bị\./);
});

test("sorting: owner first then by creation; invites newest first", () => {
  const acc = (id: number, role: AdminAccount["role"], created: string): AdminAccount => ({
    id,
    handle: `h${id}`,
    display_name: `H${id}`,
    avatar_url: null,
    role,
    status: "active",
    must_change_password: false,
    created_at: created,
    last_login_at: null,
    invited_by_handle: null,
    session_count: 0,
  });
  const sorted = sortAccounts([acc(3, "member", "2026-11-14"), acc(2, "member", "2026-11-13"), acc(1, "owner", "2026-11-15")]);
  assert.deepEqual(
    sorted.map((a) => a.id),
    [1, 2, 3],
  );
  const inv = (id: number, created: string): InviteOut => ({
    id,
    hint: "AAAA",
    note: "",
    created_at: created,
    expires_at: created,
    status: "active",
    used_by_handle: null,
  });
  assert.deepEqual(
    sortInvites([inv(1, "2026-11-10"), inv(3, "2026-11-12"), inv(2, "2026-11-11")]).map((i) => i.id),
    [3, 2, 1],
  );
});

test("a localhost page cannot make a link for someone else", () => {
  assert.equal(isLocalOrigin("localhost"), true);
  assert.equal(isLocalOrigin("127.0.0.1"), true);
  assert.equal(isLocalOrigin("192.168.1.5"), false);
});
