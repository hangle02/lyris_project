import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  ABOUT_TEXT,
  AI_DISCLAIMER,
  cleanNote,
  CONSENT_TEXT,
  countText,
  csvRange,
  dayLabel,
  eventLabel,
  funnelRates,
  noteCounter,
  percentText,
  REPORT_CARD_HINT,
  REPORT_NOTE_MAX,
  REPORT_REASONS,
  REPORT_SHARE_HINT,
  reasonLabel,
  reportContext,
  reportSheetText,
  SHARING_HINT,
  SHARING_LABEL,
  sortReports,
  topActions,
  UNPUBLISH_CONFIRM,
} from "./compliance.ts";
import type { AdminReport } from "../types.ts";

test("report reasons cover every reason the server accepts, in Vietnamese", () => {
  const py = readFileSync(new URL("../../../backend/lyris/compliance/reports.py", import.meta.url), "utf8");
  const m = /ReportReason = Literal\[([^\]]+)\]/.exec(py);
  assert.ok(m, "ReportReason in reports.py");
  const server = [...(m?.[1] ?? "").matchAll(/"([a-z_]+)"/g)].map((x) => x[1]).sort();
  assert.deepEqual(REPORT_REASONS.map((r) => r.value).sort(), server);
  assert.equal(reasonLabel("sexual"), "Nội dung tình dục");
  assert.equal(reasonLabel("self_harm"), "Tự làm hại bản thân");
  assert.equal(REPORT_REASONS.at(-1)?.label, "Khác");
});

test("report note: spaces collapsed, cut at 300 code points like the server", () => {
  assert.equal(cleanNote("  một   câu\n\nhai  "), "một câu hai");
  const long = "ạ".repeat(REPORT_NOTE_MAX + 20);
  assert.equal(Array.from(cleanNote(long)).length, REPORT_NOTE_MAX);
  assert.equal(noteCounter("abc"), "3/300");
});

test("plain copy: no technical words in the user-facing lines", () => {
  for (const text of [AI_DISCLAIMER, CONSENT_TEXT, SHARING_LABEL, SHARING_HINT]) {
    assert.ok(!/posthog|analytics|event|tracking|cookie|token|model|ollama/i.test(text), text);
  }
  assert.equal(AI_DISCLAIMER, "Nhân vật do AI đóng vai, có thể sai. Đừng xem là lời khuyên chuyên môn.");
  assert.equal(CONSENT_TEXT, "Tôi đồng ý với Điều khoản và Chính sách quyền riêng tư");
});

test("owner numbers: percent, funnel share, grouping, top actions, labels", () => {
  assert.equal(percentText(0.4249), "42%");
  assert.equal(percentText(null), "—");
  assert.equal(percentText(1.7), "100%");
  assert.deepEqual(
    funnelRates([
      { step: "a", label: "", users: 10, converted: 10 },
      { step: "b", label: "", users: 8, converted: 5 },
      { step: "c", label: "", users: 3, converted: 2 },
    ]),
    [1, 0.5, 0.2],
  );
  assert.deepEqual(funnelRates([{ step: "a", label: "", users: 0, converted: 0 }]), [null]);
  assert.equal(countText(1234567), "1.234.567");
  assert.equal(countText(12), "12");
  const top = topActions([
    { name: "session_started", count: 99 },
    { name: "message_sent", count: 40 },
    { name: "explore_viewed", count: 40 },
    { name: "made_up", count: 3 },
    { name: "story_started", count: 0 },
  ]);
  assert.deepEqual(
    top.map((t) => t.label),
    ["Xem Khám phá", "Gửi lượt", "made_up"],
  );
  assert.equal(eventLabel("reply_failed"), "Nhân vật trả lời lỗi");
});

test("every registered event has a plain label", () => {
  const py = readFileSync(new URL("../../../backend/lyris/analytics/events.py", import.meta.url), "utf8");
  const names = [...py.matchAll(/_spec\(\s*"([a-z_]+)"/g)].map((m) => m[1] ?? "");
  assert.ok(names.length >= 40);
  for (const n of names) assert.notEqual(eventLabel(n), n, n);
});

test("CSV range in Vietnam days, today included", () => {
  // 2026-11-14 18:30 UTC is already 15/11 in Vietnam.
  const now = new Date("2026-11-14T18:30:00Z");
  assert.deepEqual(csvRange(1, now), { since: "2026-11-15", until: "2026-11-15" });
  assert.deepEqual(csvRange(7, now), { since: "2026-11-09", until: "2026-11-15" });
  assert.equal(dayLabel("2026-11-09"), "09/11");
});

test("reports: zero-tolerance first, then newest; context line", () => {
  const base: AdminReport = {
    id: 1,
    target: "message",
    created_at: "2026-11-14T10:00:00Z",
    updated_at: "2026-11-14T10:00:00Z",
    reason: "other",
    note: "",
    mode: "story",
    language: "vi",
    model_name: null,
    shared_text: false,
    message_text: null,
    status: "open",
    reviewed_at: null,
    public_card_id: null,
    public_card_name: null,
    public_card_creator: null,
  };
  const list = sortReports([
    { ...base, id: 1, created_at: "2026-11-14T10:00:00Z" },
    { ...base, id: 2, created_at: "2026-11-14T11:00:00Z" },
    { ...base, id: 3, reason: "minor_safety", created_at: "2026-11-01T00:00:00Z" },
  ]);
  assert.deepEqual(
    list.map((r) => r.id),
    [3, 2, 1],
  );
  assert.equal(reportContext(base), "Story · Tiếng Việt");
  assert.equal(reportContext({ mode: "dm", language: "en" }), "Nhắn tin · Tiếng Anh");
  assert.equal(reportContext({ mode: null, language: null }), "");
  assert.equal(reportContext({ target: "character", mode: null, language: "vi" }), "Hồ sơ nhân vật · Tiếng Việt");
});

test("a public character can be reported, with the same 'nobody knows who reported' promise", () => {
  assert.deepEqual(reportSheetText("character", " Lâm "), { title: "Báo cáo nhân vật", description: "Hồ sơ của Lâm có điều gì chưa ổn?" });
  assert.deepEqual(reportSheetText("message", ""), { title: "Báo cáo câu trả lời", description: "Câu trả lời này của nhân vật có điều gì chưa ổn?" });
  assert.match(REPORT_CARD_HINT, /không biết ai báo cáo/);
  assert.match(REPORT_SHARE_HINT, /không biết ai báo cáo/);
  assert.match(UNPUBLISH_CONFIRM, /Riêng tư/);
});

test("where the data lives: the server running Lyris, never 'this Mac' (docs/legal/privacy.md §1)", () => {
  assert.ok(!/máy này|Mac|không rời khỏi máy/.test(ABOUT_TEXT), ABOUT_TEXT);
  assert.match(ABOUT_TEXT, /máy chủ chạy Lyris/);
  const privacy = readFileSync(new URL("../../../docs/legal/privacy.md", import.meta.url), "utf8");
  assert.match(privacy, /máy chủ/);
});

test("the privacy policy names the sharing switch exactly as the UI shows it", () => {
  const privacy = readFileSync(new URL("../../../docs/legal/privacy.md", import.meta.url), "utf8");
  assert.ok(privacy.includes(`"${SHARING_LABEL}"`), "privacy.md quotes the switch label");
  assert.ok(!privacy.includes(`${SHARING_LABEL} để cải thiện Lyris`), "no label the UI does not show");
});
