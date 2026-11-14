// Words and small rules of the launch screens (docs/compliance.md §7, docs/tracking-plan.md): consent,
// legal pages, reports, usage sharing, account deletion, the owner's numbers. Pure, tested in
// compliance.test.ts. UI copy stays plain: no "event", "analytics", "tracking" or service names.
import type { AdminReport, AnalyticsSummary, ReportReason, ReportStatus, ReportTarget } from "../types.ts";

export const PRIVACY_LABEL = "Quyền riêng tư";
export const TERMS_LABEL = "Điều khoản";
export const PRIVACY_TITLE = "Chính sách quyền riêng tư";
export const TERMS_TITLE = "Điều khoản sử dụng";

/** One quiet line where a story starts (StartStorySheet) and on an empty chat. */
export const AI_DISCLAIMER = "Nhân vật do AI đóng vai, có thể sai. Đừng xem là lời khuyên chuyên môn.";

/** The consent box at signup and owner setup; the two names in it are links. */
export const CONSENT_PARTS = { before: "Tôi đồng ý với ", terms: "Điều khoản", middle: " và ", privacy: "Chính sách quyền riêng tư" } as const;
export const CONSENT_TEXT = `${CONSENT_PARTS.before}${CONSENT_PARTS.terms}${CONSENT_PARTS.middle}${CONSENT_PARTS.privacy}`;
export const CONSENT_MISSING = "Hãy đánh dấu đồng ý để tiếp tục.";

/** The one-time screen for accounts made before the Terms existed (or changed). */
export const TERMS_SCREEN_TITLE = "Trước khi tiếp tục";
export const TERMS_SCREEN_INTRO =
  "Lyris vừa có Điều khoản sử dụng và Chính sách quyền riêng tư. Hãy đọc và đồng ý một lần để dùng tiếp.";
export const TERMS_SCREEN_POINTS: readonly string[] = [
  "Nhân vật do AI đóng vai, có thể sai.",
  "Không có nội dung tình dục; nội dung liên quan trẻ vị thành niên bị cấm tuyệt đối.",
  "Lyris không bao giờ ghi lại chữ bạn viết vào số liệu sử dụng. Bạn tắt được trong Tài khoản.",
];
export const TERMS_ACCEPT = "Đồng ý và tiếp tục";

// ---- where the data lives (open web: the operator's server, not the visitor's device) ----

/** "Giới thiệu" in Tài khoản. Matches docs/legal/privacy.md §1 and §4: stored on the server running Lyris. */
export const ABOUT_TEXT =
  "Nhân vật, story và ký ức của bạn được lưu trên máy chủ chạy Lyris. Tài khoản khác không xem được, và chữ bạn viết không bao giờ được gửi đi để thống kê.";

// ---- usage sharing, own data, deletion (AccountSheet) ----

export const SHARING_LABEL = "Chia sẻ dữ liệu sử dụng ẩn danh";
export const SHARING_HINT = "Giúp cải thiện Lyris. Chỉ ghi thao tác, không bao giờ ghi chữ bạn viết.";
export const SHARING_OFF_NOTE = "Đã tắt. Dữ liệu sử dụng đã lưu của bạn cũng đã được xoá.";
export const EXPORT_LABEL = "Tải dữ liệu của tôi";
export const EXPORT_HINT = "Một tệp JSON gồm hồ sơ, persona, nhân vật, story và tin nhắn của bạn.";
export const DELETE_LABEL = "Xoá tài khoản";
export const DELETE_WHAT =
  "Xoá ngay và không hoàn tác được: mọi story, tin nhắn, ký ức, persona, nhân vật (kể cả nhân vật công khai), ảnh và thiết bị đăng nhập của bạn.";
export const DELETE_KEPT =
  "Còn lại nhưng không gắn với bạn: số liệu sử dụng ẩn danh, lý do các báo cáo bạn đã gửi, và bản sao nhân vật công khai mà người khác đang dùng trong story của họ.";
export const DELETE_OWNER =
  "Bạn là chủ máy. Chỉ xoá được khi Lyris không còn tài khoản nào khác. Xoá xong, Lyris trở về màn thiết lập ban đầu và in mã thiết lập mới trong Terminal.";
export const DELETE_CONFIRM = "Xoá vĩnh viễn";

// ---- report an AI reply ----

export interface ReasonOption {
  value: ReportReason;
  label: string;
}

/** In the order of the sheet; `minor_safety` right after sexual content (zero tolerance). */
export const REPORT_REASONS: readonly ReasonOption[] = [
  { value: "sexual", label: "Nội dung tình dục" },
  { value: "minor_safety", label: "Liên quan trẻ vị thành niên" },
  { value: "violent", label: "Bạo lực" },
  { value: "hateful", label: "Thù ghét" },
  { value: "self_harm", label: "Tự làm hại bản thân" },
  { value: "harassment", label: "Quấy rối" },
  { value: "other", label: "Khác" },
];

export const REPORT_NOTE_MAX = 300;
export const REPORT_SHARE_LABEL = "Gửi kèm câu trả lời này để người quản lý xem xét";
export const REPORT_SHARE_HINT = "Không bật thì chỉ gửi lý do và ghi chú. Người quản lý không biết ai báo cáo.";
export const REPORT_DONE = "Đã gửi báo cáo. Cảm ơn bạn.";
/** A public character's profile: what is reported, and the same promise as for a reply. */
export const REPORT_CARD_LABEL = "Báo cáo nhân vật";
export const REPORT_CARD_HINT = "Người quản lý xem lại tên, mô tả, lời chào và ảnh của nhân vật. Người quản lý không biết ai báo cáo.";

/** Title and description of the report sheet, for a reply or for a public character. */
export function reportSheetText(target: ReportTarget, characterName: string): { title: string; description: string } {
  const name = characterName.trim() || "nhân vật";
  return target === "character"
    ? { title: "Báo cáo nhân vật", description: `Hồ sơ của ${name} có điều gì chưa ổn?` }
    : { title: "Báo cáo câu trả lời", description: `Câu trả lời này của ${name} có điều gì chưa ổn?` };
}

export function reasonLabel(reason: ReportReason): string {
  return REPORT_REASONS.find((r) => r.value === reason)?.label ?? "Khác";
}

/** The note as sent: spaces collapsed, at most REPORT_NOTE_MAX characters. */
export function cleanNote(note: string): string {
  return Array.from(note.replace(/\s+/g, " ").trim()).slice(0, REPORT_NOTE_MAX).join("");
}

/** Characters left in the note field ("120/300"), counting code points like the server. */
export function noteCounter(note: string): string {
  return `${Array.from(note).length}/${REPORT_NOTE_MAX}`;
}

// ---- owner: reports ----

/** Owner: hide a reported public character (it becomes private; its creator keeps it). */
export const UNPUBLISH_LABEL = "Ẩn nhân vật";
export const UNPUBLISH_CONFIRM = "Ẩn nhân vật này khỏi mọi người? Nhân vật chuyển về Riêng tư; người tạo vẫn giữ và sửa được.";
export const UNPUBLISH_DONE = "Đã ẩn nhân vật. Nhân vật giờ chỉ người tạo thấy.";

export const REPORT_STATUS_OPTIONS: readonly { value: ReportStatus; label: string }[] = [
  { value: "open", label: "Cần xem" },
  { value: "reviewed", label: "Đã xem" },
  { value: "dismissed", label: "Bỏ qua" },
];

export function reportStatusLabel(status: ReportStatus): string {
  return REPORT_STATUS_OPTIONS.find((o) => o.value === status)?.label ?? status;
}

/** Zero-tolerance reasons first, then newest. */
export function sortReports(list: readonly AdminReport[]): AdminReport[] {
  const rank = (r: AdminReport) => (r.reason === "minor_safety" ? 0 : 1);
  return [...list].sort((a, b) => rank(a) - rank(b) || b.created_at.localeCompare(a.created_at) || b.id - a.id);
}

/**
 * "Story · Tiếng Việt", "Nhắn tin · English" (the reply's context, never the story); a character
 * report starts with "Hồ sơ nhân vật".
 */
export function reportContext(r: Pick<AdminReport, "mode" | "language"> & { target?: ReportTarget }): string {
  const parts: string[] = [];
  if (r.target === "character") parts.push("Hồ sơ nhân vật");
  if (r.mode) parts.push(r.mode === "dm" ? "Nhắn tin" : "Story");
  if (r.language) parts.push(r.language === "en" ? "Tiếng Anh" : "Tiếng Việt");
  return parts.join(" · ");
}

// ---- owner: usage numbers ----

export const METRIC_DAYS: readonly { value: "7" | "30" | "90"; label: string }[] = [
  { value: "7", label: "7 ngày" },
  { value: "30", label: "30 ngày" },
  { value: "90", label: "90 ngày" },
];

/** Plain names of what people did, for the "Thao tác" list (unknown names keep the code). */
const EVENT_LABELS: Readonly<Record<string, string>> = {
  app_opened: "Mở Lyris",
  session_started: "Lượt ghé thăm",
  signup_viewed: "Mở trang tạo tài khoản",
  signup_completed: "Tạo tài khoản",
  invite_redeemed: "Dùng mã mời",
  owner_setup_completed: "Thiết lập chủ máy",
  login_succeeded: "Đăng nhập",
  login_failed: "Đăng nhập sai",
  invite_created: "Tạo mã mời",
  explore_viewed: "Xem Khám phá",
  vibe_filter_used: "Lọc theo cảm xúc",
  character_profile_viewed: "Xem hồ sơ nhân vật",
  story_start_clicked: "Bấm bắt đầu story",
  story_started: "Bắt đầu story",
  message_sent: "Gửi lượt",
  reply_completed: "Nhân vật trả lời xong",
  reply_failed: "Nhân vật trả lời lỗi",
  regenerate_used: "Tạo lại câu trả lời",
  message_edited: "Sửa tin",
  message_deleted: "Xoá tin",
  variant_switched: "Đổi phiên bản trả lời",
  reply_rated: "Thích / chê câu trả lời",
  suggestions_requested: "Xin gợi ý",
  suggestion_used: "Dùng gợi ý",
  thought_revealed: "Mở suy nghĩ",
  show_thoughts_toggled: "Bật/tắt suy nghĩ",
  mode_switched: "Đổi Story / Nhắn tin",
  heart_drawer_opened: "Mở ngăn trái tim",
  lore_unlocked: "Mở mục thế giới",
  memory_forgotten: "Xoá ký ức",
  events_timeline_opened: "Xem dòng sự kiện",
  character_created: "Tạo nhân vật",
  character_published: "Công khai nhân vật",
  lore_imported: "Nhập sổ thế giới",
  persona_created: "Tạo persona",
  story_resumed: "Quay lại story cũ",
  content_reported: "Báo cáo nội dung",
  account_deleted: "Xoá tài khoản",
  data_exported: "Tải dữ liệu",
  analytics_opt_out: "Tắt chia sẻ dữ liệu",
};

export function eventLabel(name: string): string {
  return EVENT_LABELS[name] ?? name;
}

/** "42%" (rounded), "—" when there is nobody to count. */
export function percentText(rate: number | null | undefined): string {
  if (rate === null || rate === undefined || !Number.isFinite(rate)) return "—";
  return `${Math.round(Math.max(0, Math.min(1, rate)) * 100)}%`;
}

/** Share of the funnel's first step that reached each step (nested), 0..1; null when the first is 0. */
export function funnelRates(funnel: AnalyticsSummary["funnel"]): (number | null)[] {
  const top = funnel[0]?.users ?? 0;
  return funnel.map((s, i) => (top > 0 ? (i === 0 ? 1 : s.converted / top) : null));
}

/** "1.234" (Vietnamese grouping). */
export function countText(n: number): string {
  return Math.round(n)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

/** The busiest of the most-counted actions, at most `limit`, people's actions before automatic ones. */
export function topActions(counts: AnalyticsSummary["counts"], limit = 8): { name: string; label: string; count: number }[] {
  return [...counts]
    .filter((c) => c.name !== "session_started" && c.count > 0)
    .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name))
    .slice(0, limit)
    .map((c) => ({ ...c, label: eventLabel(c.name) }));
}

/** "YYYY-MM-DD" of a moment in Vietnam time (the server's days for the CSV range). */
export function vietnamDay(at: Date): string {
  const d = new Date(at.getTime() + 7 * 3600_000);
  return d.toISOString().slice(0, 10);
}

/** The CSV range for the last `days` days, today included (Vietnam days). */
export function csvRange(days: number, now: Date): { since: string; until: string } {
  const until = vietnamDay(now);
  const since = vietnamDay(new Date(now.getTime() - (Math.max(1, days) - 1) * 86_400_000));
  return { since, until };
}

/** "Hôm nay" style short date of a "YYYY-MM-DD" day: "14/11". */
export function dayLabel(day: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(day);
  return m ? `${m[3]}/${m[2]}` : day;
}
