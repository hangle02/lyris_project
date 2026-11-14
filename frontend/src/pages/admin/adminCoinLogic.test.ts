// F43 (docs/coins.md §4.3–§4.5): the owner's coin tools in "#/admin" check what is typed BEFORE sending —
// a code's coins 1–10.000, a manual change −10.000…10.000 and not 0, a reason of 3–120 characters — and
// word the code list and the coin log.
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  adjustRequest,
  codeAmountProblem,
  codeRequest,
  coinLogTitle,
  memberCoinLine,
  newRequestId,
  parseWholeNumber,
  reasonProblem,
  topupCodeBadge,
} from "./adminCoinLogic.ts";

test("parseWholeNumber: digits, Vietnamese thousands, a sign; anything else is null", () => {
  assert.equal(parseWholeNumber("20"), 20);
  assert.equal(parseWholeNumber(" 1.200 "), 1200);
  assert.equal(parseWholeNumber("-5"), -5);
  assert.equal(parseWholeNumber("−5"), -5); // the minus sign of some keyboards
  assert.equal(parseWholeNumber("+20"), 20);
  for (const bad of ["", "abc", "1.5", "12,5", "1.20", "--3", "2e3"]) assert.equal(parseWholeNumber(bad), null, bad);
});

test("codeAmountProblem: a code holds 1 to 10.000 coins", () => {
  assert.equal(codeAmountProblem("1"), null);
  assert.equal(codeAmountProblem("10000"), null);
  assert.equal(codeAmountProblem("10.000"), null);
  for (const bad of ["0", "10001", "-5", "", "abc", "1.5"]) assert.equal(codeAmountProblem(bad), "Số coin từ 1 đến 10.000.", bad);
});

test("reasonProblem: 3 to 120 characters after trimming", () => {
  assert.equal(reasonProblem("abc"), null);
  assert.equal(reasonProblem("x".repeat(120)), null);
  for (const bad of ["", "ab", "  a  ", "x".repeat(121)]) assert.equal(reasonProblem(bad), "Lý do cần từ 3 đến 120 ký tự.", bad);
});

test("adjustRequest: checks the number and the reason before sending", () => {
  assert.deepEqual(adjustRequest("20", "  thử   bot ", "req-1234-abcd"), {
    ok: true,
    body: { delta: 20, reason: "thử bot", request_id: "req-1234-abcd" },
  });
  assert.deepEqual(adjustRequest("-1.200", "thu lại", "req-1234-abcd"), {
    ok: true,
    body: { delta: -1200, reason: "thu lại", request_id: "req-1234-abcd" },
  });
  const zero = adjustRequest("0", "x", "req-1234-abcd");
  assert.equal(zero.ok, false);
  if (!zero.ok) {
    assert.equal(zero.problems.delta, "Nhập số coin khác 0, từ −10.000 đến 10.000.");
    assert.equal(zero.problems.reason, "Lý do cần từ 3 đến 120 ký tự.");
  }
  for (const bad of ["10001", "-10001", "", "abc"]) {
    const r = adjustRequest(bad, "lý do đủ dài", "req-1234-abcd");
    assert.equal(r.ok, false, bad);
  }
  assert.equal(adjustRequest("10000", "lý do", "r-12345678").ok, true);
  assert.equal(adjustRequest("-10000", "lý do", "r-12345678").ok, true);
});

test("codeRequest: a pack sends pack_id only; 'Tự nhập' sends amount only, checked", () => {
  assert.deepEqual(codeRequest("p100", "", " cho  Mai ", "7"), { ok: true, body: { pack_id: "p100", note: "cho Mai", expires_days: 7 } });
  assert.deepEqual(codeRequest("custom", "250", "", "30"), { ok: true, body: { amount: 250, note: "", expires_days: 30 } });
  assert.deepEqual(codeRequest("custom", "0", "", "7"), { ok: false, problem: "Số coin từ 1 đến 10.000." });
  assert.deepEqual(codeRequest("custom", "10001", "", "1"), { ok: false, problem: "Số coin từ 1 đến 10.000." });
});

test("newRequestId: a fresh id the server accepts (8–64 of A-Z a-z 0-9 _ -)", () => {
  const a = newRequestId();
  const b = newRequestId();
  assert.notEqual(a, b);
  for (const id of [a, b]) assert.match(id, /^[A-Za-z0-9_-]{8,64}$/);
});

test("code badges, member coin line and coin log titles", () => {
  assert.deepEqual(topupCodeBadge({ status: "active", used_by_handle: null }), { label: "Còn hiệu lực", tone: "ok" });
  assert.deepEqual(topupCodeBadge({ status: "used", used_by_handle: "mai" }), { label: "Đã dùng bởi @mai", tone: "neutral" });
  assert.deepEqual(topupCodeBadge({ status: "expired", used_by_handle: null }), { label: "Hết hạn", tone: "neutral" });
  assert.deepEqual(topupCodeBadge({ status: "revoked", used_by_handle: null }), { label: "Đã huỷ", tone: "neutral" });
  assert.equal(memberCoinLine(1200), "1.200 coin");
  assert.equal(memberCoinLine(null), null);
  assert.equal(coinLogTitle({ kind: "topup_code", note: "quà", reason: null, milestone: null }), "Nạp bằng mã · quà");
  assert.equal(coinLogTitle({ kind: "topup_code", note: null, reason: null, milestone: null }), "Nạp bằng mã");
  assert.equal(coinLogTitle({ kind: "admin_adjust", note: null, reason: "thử bot", milestone: null }), "thử bot");
  assert.equal(coinLogTitle({ kind: "creator_milestone", note: null, reason: null, milestone: 10 }), "Thưởng mốc 10 người chơi");
  // F44 làm lại: the server names creator rewards by kind of reward (ranking tier, first public character).
  assert.equal(
    coinLogTitle({ kind: "creator_milestone", note: null, reason: null, milestone: 10, label: "Thưởng xếp hạng top 10" }),
    "Thưởng xếp hạng top 10",
  );
  assert.equal(
    coinLogTitle({ kind: "creator_milestone", note: null, reason: null, milestone: null, label: "Thưởng công khai lần đầu" }),
    "Thưởng công khai lần đầu",
  );
});
