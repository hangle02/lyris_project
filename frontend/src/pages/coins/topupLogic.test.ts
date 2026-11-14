// F43 (docs/coins.md §4, §10.5): "Nạp coin" — VND prices, the pack words, the top-up code normalised exactly
// like an invite code (lib/inviteCode.ts, shared case table with the backend), and the error sentences.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { normalizeCode } from "../../lib/inviteCode.ts";
import { allCoinStrings } from "../../lib/coinCopy.ts";
import {
  checkCodeInput,
  formatTopupCode,
  formatVnd,
  normalizeTopupCode,
  packBonus,
  packDialogTitle,
  packTitle,
  redeemErrorText,
  redeemedText,
  noteTopUpFrom,
  takeTopUpFrom,
} from "./topupLogic.ts";
import type { CoinPack } from "./topupLogic.ts";

const pack = (over: Partial<CoinPack> = {}): CoinPack => ({ id: "p550", coins: 550, bonus: 50, price_vnd: 50000, ...over });

test("formatVnd: Vietnamese thousands and the đ sign", () => {
  assert.equal(formatVnd(50000), "50.000đ");
  assert.equal(formatVnd(10000), "10.000đ");
  assert.equal(formatVnd(100000), "100.000đ");
  assert.equal(formatVnd(200000), "200.000đ");
  assert.equal(formatVnd(0), "0đ");
});

test("the top-up code is normalised like an invite code (shared case table)", () => {
  const table = JSON.parse(readFileSync(new URL("../../lib/inviteCode.cases.json", import.meta.url), "utf8")) as {
    cases: { input: string; expected: string | null }[];
  };
  assert.ok(table.cases.length >= 10);
  for (const c of table.cases) {
    assert.equal(normalizeTopupCode(c.input), c.expected, JSON.stringify(c.input));
    assert.equal(normalizeTopupCode(c.input), normalizeCode(c.input));
  }
  // Lowercase, the dashes an iPhone keyboard types, spaces.
  assert.equal(normalizeTopupCode("  7kq2‐m9xd — 4tpa "), "7KQ2M9XD4TPA");
  assert.equal(normalizeTopupCode("7KQ2−M9XD–4TPA"), "7KQ2M9XD4TPA");
  assert.equal(normalizeTopupCode(""), null);
  assert.equal(formatTopupCode("7kq2m9xd4tpa"), "7KQ2-M9XD-4TPA");
});

test("checkCodeInput: empty or malformed codes never reach the server, with the one shared sentence", () => {
  assert.deepEqual(checkCodeInput("7kq2-m9xd-4tpa"), { ok: true, code: "7KQ2M9XD4TPA" });
  for (const bad of ["", "   ", "abc", "7KQ2-M9XD-4TP"]) {
    assert.deepEqual(checkCodeInput(bad), { ok: false, text: "Mã nạp không đúng hoặc đã hết hạn." });
  }
});

test("pack words: '{n} coin', 'Tặng thêm {k}', the dialog title", () => {
  assert.equal(packTitle(pack()), "550 coin");
  assert.equal(packTitle(pack({ coins: 1200 })), "1.200 coin");
  assert.equal(packBonus(pack()), "Tặng thêm 50");
  assert.equal(packBonus(pack({ id: "p100", coins: 100, bonus: 0, price_vnd: 10000 })), null);
  assert.equal(packDialogTitle(pack()), "Gói 550 coin · Giá dự kiến 50.000đ");
  assert.equal(packDialogTitle(pack({ id: "p2500", coins: 2500, bonus: 500, price_vnd: 200000 })), "Gói 2.500 coin · Giá dự kiến 200.000đ");
});

test("redeem results: 'Đã nạp {n} coin.', one sentence for every wrong code, the rate limit", () => {
  assert.equal(redeemedText(100), "Đã nạp 100 coin.");
  assert.equal(redeemedText(1200), "Đã nạp 1.200 coin.");
  assert.equal(redeemErrorText(422, "topup_code_invalid", "x"), "Mã nạp không đúng hoặc đã hết hạn.");
  assert.equal(redeemErrorText(429, "rate_limited", "x"), "Bạn đã thử sai nhiều lần. Hãy đợi một lúc rồi thử lại.");
  assert.equal(redeemErrorText(422, "topup_code_owner", "Tài khoản quản lý không cần nạp coin."), "Tài khoản quản lý không cần nạp coin.");
  assert.equal(redeemErrorText(0, null, "Không kết nối được Lyris."), "Không kết nối được Lyris.");
});

test("topup_viewed 'from': the button that opened the screen, once; a typed link is 'link'", () => {
  noteTopUpFrom("composer");
  assert.equal(takeTopUpFrom(), "composer");
  assert.equal(takeTopUpFrom(), "link");
  noteTopUpFrom("wallet");
  assert.equal(takeTopUpFrom(), "wallet");
});

test("the member's top-up words never say 'chủ máy' or technical words", () => {
  const all = allCoinStrings().join("\n");
  for (const want of [
    "Chế độ thử: Lyris chưa bán coin. Nhập mã nạp người quản lý tặng bạn.",
    "Giá dự kiến khi Lyris ra mắt. Ở chế độ thử chưa bán coin; người quản lý có thể tặng bạn mã nạp để thử.",
    "Dùng mã",
    "Mã nạp",
  ]) {
    assert.ok(all.includes(want), want);
  }
  assert.doesNotMatch(all, /chủ máy|token|credits|\bmodel\b|ollama|thanh toán|liên hệ/i);
});
