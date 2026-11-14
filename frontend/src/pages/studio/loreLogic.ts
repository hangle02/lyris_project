// Sổ thế giới trong Studio (docs/phase4.md §9): chữ, cảnh báo và gom nhóm cho phần "Thế giới" của trình
// sửa nhân vật. Hàm thuần, không React; có test ở loreLogic.test.ts.
//
// Trên giao diện không bao giờ hiện chữ "lore", "keys", "known_by": dùng "Thế giới", "Mục thế giới",
// "Từ khoá gợi nhớ", "Ai biết điều này".
import type {
  LoreAudience,
  LoreCategory,
  LoreEntry,
  LoreEntryInput,
  LoreImportAction,
  LoreImportItem,
  LoreImportResult,
  LoreSource,
} from "../../types.ts";

// ---- giới hạn (khớp backend/lyris/models.py và lore/select.py) ----

export const MAX_LORE_TITLE = 120;
export const MAX_LORE_KEYS = 32;
export const MAX_LORE_KEY_CHARS = 80;
export const MAX_LORE_CONTENT = 4000;
/** Phần nhân vật đọc được của một mục trong mỗi lượt (cắt ở cuối câu). */
export const MAX_LORE_ITEM_CHARS = 450;
export const MAX_LORE_IMPORT_BYTES = 512_000;
/** Từ số mục này trở lên thì có ô "Tìm trong thế giới". */
export const SEARCH_FROM_ENTRIES = 12;

/** Từ lộ cốt truyện gốc (backend lore/parse.py META_SPOILER_TERMS). */
export const META_SPOILER_TERMS: readonly string[] = [
  "nguyên tác",
  "nguyên chủ",
  "cốt truyện gốc",
  "xuyên sách",
  "xuyên không",
  "kiếp trước",
  "trùng sinh",
  "nữ chính",
  "nam chính",
  "nữ phụ",
  "nam phụ",
];

/** Ví dụ từ ghép cho câu cảnh báo khoá một chữ (giống backend, không cần đủ). */
const COMPOUND_EXAMPLES: Record<string, string> = {
  nhẫn: "kiên nhẫn",
  lục: "lục tung",
  mắt: "mắt xích",
  hoa: "hoa mắt",
  tâm: "quan tâm",
  trì: "trì hoãn",
  tình: "tình cờ",
  đông: "đám đông",
  kim: "kim chỉ",
  đường: "con đường",
  giang: "giang hồ",
  thiên: "thiên nhiên",
  dương: "đại dương",
};

// ---- dạng so khớp (bản rút gọn của backend lore/normalize.py; chỉ dùng cho cảnh báo) ----

const TONE_MARKS = new Set(["̀", "́", "̃", "̉", "̣"]);
const CJK = /[㐀-䶿一-鿿豈-﫿]/u;

/** "hoà" -> "hòa", "thuý" -> "thúy"; "quý", "hoàng" giữ nguyên (backend canon_tone). `word` đã NFC, chữ thường. */
export function canonTone(word: string): string {
  const chars = [...word];
  if (chars.length < 2) return word;
  const parts = chars.map((c) => {
    const d = c.normalize("NFD");
    let base = "";
    let tone: string | null = null;
    for (const ch of d) {
      if (TONE_MARKS.has(ch)) tone = ch;
      else base += ch;
    }
    return { base: base.normalize("NFC"), tone };
  });
  if (!parts.some((p) => p.tone)) return word;
  const bases = parts.map((p) => p.base).join("");
  for (const pair of ["oa", "oe", "uy"]) {
    if (!bases.endsWith(pair)) continue;
    if (pair === "uy" && bases.slice(0, -2).endsWith("q")) return word;
    const i = parts.length - 2;
    const tone = parts[i]?.tone ?? parts[i + 1]?.tone ?? null;
    if (tone === null || parts[i]?.tone) return word;
    return parts
      .map((p, j) => {
        if (j === i) return (p.base + tone).normalize("NFC");
        if (j === i + 1) return p.base;
        return p.tone ? (p.base + p.tone).normalize("NFC") : p.base;
      })
      .join("");
  }
  return word;
}

/** Các âm tiết (chữ/số) đã NFC, chữ thường, chuẩn vị trí dấu. Giữ nguyên dấu: "Lục" khác "lúc". */
export function matchTokens(text: string): string[] {
  const t = text.normalize("NFC").toLocaleLowerCase("vi-VN").normalize("NFC");
  return (t.match(/[\p{L}\p{M}\p{N}_]+/gu) ?? []).map(canonTone);
}

/** " tok tok " như backend match_form: so trọn âm tiết bằng `includes(" " + key + " ")`. */
export function matchForm(text: string): string {
  return ` ${matchTokens(text).join(" ")} `;
}

function stripParens(text: string): string {
  return text.replace(/\([^)]*\)/g, " ").replace(/\s+/g, " ").trim();
}

/** Hai tên giống nhau (bỏ phần trong ngoặc, so theo dạng so khớp). */
export function sameName(a: string, b: string): boolean {
  const fa = matchForm(stripParens(a));
  return fa.trim() !== "" && fa === matchForm(stripParens(b));
}

/** Khoá dạng tên riêng: có chữ hoa, chữ số hoặc chữ Hán (gợi nhớ cả khi nhân vật tự nhắc tới). */
export function isNameLike(key: string): boolean {
  if (CJK.test(key)) return true;
  return [...key].some((c) => /\p{N}/u.test(c) || (c !== c.toLocaleLowerCase("vi-VN") && /\p{L}/u.test(c)));
}

// ---- ai biết ----

const EVERYONE = "*";
const USER_RE = /^\{\{\s*user\s*\}\}$/i;
const CHAR_RE = /^\{\{\s*char\s*\}\}$/i;

/** everyone > character > player > others (backend select.audience_of). */
export function audienceOf(knownBy: readonly string[], charName: string): LoreAudience {
  const values = knownBy.map((v) => v.trim()).filter(Boolean);
  if (values.includes(EVERYONE)) return "everyone";
  if (values.some((v) => CHAR_RE.test(v) || (charName.trim() !== "" && sameName(v, charName)))) return "character";
  if (values.some((v) => USER_RE.test(v))) return "player";
  return "others";
}

/** Tên người khác trong known_by (không phải *, {{user}}, {{char}}). */
export function otherNames(knownBy: readonly string[]): string[] {
  return knownBy.map((v) => v.trim()).filter((v) => v && v !== EVERYONE && !USER_RE.test(v) && !CHAR_RE.test(v));
}

function nameOr(name: string): string {
  return name.trim() || "nhân vật";
}

export type BadgeTone = "neutral" | "accent" | "gold";

/** Nhãn nhỏ "ai biết" trên một hàng của danh sách. */
export function audienceBadge(audience: LoreAudience, charName: string): { label: string; tone: BadgeTone } {
  switch (audience) {
    case "everyone":
      return { label: "Mọi người", tone: "neutral" };
    case "character":
      return { label: `Chỉ ${nameOr(charName)}`, tone: "accent" };
    case "player":
      return { label: "Chỉ bạn", tone: "gold" };
    default:
      return { label: "Người khác", tone: "neutral" };
  }
}

export interface KnowOption {
  value: LoreAudience;
  label: string;
  hint: string;
}

/**
 * Lựa chọn "Ai biết điều này". Mục mà chỉ người khác biết (known_by là tên nhân vật phụ) có thêm một
 * lựa chọn thứ tư để giữ nguyên như cũ; chọn lựa chọn khác thì thay known_by.
 */
export function knowOptions(charName: string, original: readonly string[]): KnowOption[] {
  const name = nameOr(charName);
  const options: KnowOption[] = [
    { value: "everyone", label: "Mọi người", hint: `${name} và mọi người trong thế giới đều biết.` },
    { value: "character", label: `Chỉ ${name}`, hint: `${name} biết nhưng giữ trong lòng, không tự kể ra.` },
    { value: "player", label: "Chỉ bạn", hint: `Chỉ bạn biết. ${name} không bao giờ được đọc điều này.` },
  ];
  if (audienceOf(original, charName) === "others") {
    const others = otherNames(original);
    options.push({
      value: "others",
      label: `Chỉ ${others.join(", ") || "người khác"} biết`,
      hint: `${name} không biết điều này.`,
    });
  }
  return options;
}

/** known_by gửi lên cho một lựa chọn; "others" giữ nguyên known_by ban đầu của mục. */
export function knownByFor(choice: LoreAudience, original: readonly string[]): string[] {
  switch (choice) {
    case "everyone":
      return [EVERYONE];
    case "character":
      return ["{{char}}"];
    case "player":
      return ["{{user}}"];
    default:
      return original.length ? [...original] : [EVERYONE];
  }
}

// ---- cảnh báo khi sửa ----

/** Câu cảnh báo từng từ khoá (giống backend key_warnings): khoá một chữ, khoá là tên nhân vật. */
export function keyWarnings(keys: readonly string[], charName: string): string[] {
  const out: string[] = [];
  for (const raw of keys) {
    const k = raw.trim();
    if (!k) continue;
    if (charName.trim() && sameName(k, charName)) {
      out.push(`Từ khoá “${k}” là tên nhân vật nên không dùng để gợi nhớ.`);
      continue;
    }
    if (CJK.test(k) || matchTokens(k).length !== 1) continue;
    if (isNameLike(k)) continue; // tên riêng một chữ (London, GHOST): tác giả tự chọn
    const example = COMPOUND_EXAMPLES[matchTokens(k)[0] ?? ""];
    out.push(
      example
        ? `Từ khoá “${k}” chỉ có một chữ, cũng khớp trong những từ như “${example}”.`
        : `Từ khoá “${k}” chỉ có một chữ nên sẽ gợi rất thường xuyên.`,
    );
  }
  return out;
}

/** Từ lộ cốt truyện gốc có trong nội dung. */
export function spoilerTerms(content: string): string[] {
  const form = matchForm(content);
  return META_SPOILER_TERMS.filter((t) => form.includes(matchForm(t)));
}

/**
 * Nhắc dưới ô nội dung: mục nhân vật được đọc ("Mọi người", "Chỉ {tên}") mà có chữ như "nguyên tác".
 * Chỉ nhắc, không chặn lưu. Cộng thêm câu "Dài quá…" khi nội dung vượt phần nhân vật đọc được.
 */
export function contentWarnings(content: string, audience: LoreAudience, charName: string): string[] {
  const out: string[] = [];
  const name = nameOr(charName);
  if (audience === "everyone" || audience === "character") {
    const terms = spoilerTerms(content);
    if (terms.length) {
      out.push(
        `Có chữ ${terms.map((t) => `“${t}”`).join(", ")}. Nếu đây là điều ${name} không được biết, hãy chọn “Chỉ bạn”.`,
      );
    }
  }
  if (content.trim().length > MAX_LORE_ITEM_CHARS) out.push(`Dài quá thì ${name} chỉ đọc phần đầu.`);
  return out;
}

/** Lỗi chặn lưu (câu giống backend). */
export function validateEntry(input: Pick<LoreEntryInput, "title" | "keys" | "known_by" | "content">): string[] {
  const errors: string[] = [];
  const title = input.title.trim();
  if (!title) errors.push("Mục thế giới cần có tên.");
  else if (title.length > MAX_LORE_TITLE) errors.push(`Tên mục thế giới dài tối đa ${MAX_LORE_TITLE} ký tự.`);
  const keys = input.keys.map((k) => k.trim()).filter(Boolean);
  if (keys.length > MAX_LORE_KEYS) errors.push(`Mỗi mục có tối đa ${MAX_LORE_KEYS} từ khoá.`);
  if (keys.some((k) => k.length > MAX_LORE_KEY_CHARS)) errors.push(`Mỗi từ khoá dài tối đa ${MAX_LORE_KEY_CHARS} ký tự.`);
  if (input.known_by.filter((v) => v.trim()).length === 0) errors.push("Cần chọn ai biết điều này.");
  if (input.content.length > MAX_LORE_CONTENT) errors.push(`Nội dung dài tối đa ${MAX_LORE_CONTENT} ký tự.`);
  return errors;
}

// ---- danh sách ----

export const CATEGORY_LABELS: Record<LoreCategory, string> = {
  lore: "Chuyện và bí mật",
  character: "Người xung quanh",
  place: "Nơi chốn",
};

/** Lựa chọn "Loại" trong hộp sửa (nhãn ngắn). */
export const CATEGORY_OPTIONS: { value: LoreCategory; label: string }[] = [
  { value: "lore", label: "Chuyện và bí mật" },
  { value: "character", label: "Người" },
  { value: "place", label: "Nơi chốn" },
];

const CATEGORY_ORDER: readonly LoreCategory[] = ["lore", "character", "place"];

export interface EntryGroup<T> {
  category: LoreCategory;
  title: string;
  entries: T[];
}

/** Ba nhóm theo thứ tự cố định, giữ thứ tự trong nhóm; nhóm rỗng bị bỏ. */
export function groupEntries<T extends { category: LoreCategory }>(entries: readonly T[]): EntryGroup<T>[] {
  return CATEGORY_ORDER.map((category) => ({
    category,
    title: CATEGORY_LABELS[category],
    entries: entries.filter((e) => e.category === category),
  })).filter((g) => g.entries.length > 0);
}

function searchForm(text: string): string {
  return text.normalize("NFC").toLocaleLowerCase("vi-VN");
}

/** Tìm trong tên, từ khoá và nội dung: không phân biệt hoa thường, giữ dấu ("lục" không ra "lúc"). */
export function filterEntries<T extends Pick<LoreEntry, "title" | "keys" | "content">>(entries: readonly T[], query: string): T[] {
  const q = searchForm(query).trim();
  if (!q) return [...entries];
  return entries.filter((e) => [e.title, ...e.keys, e.content].some((s) => searchForm(s).includes(q)));
}

/** Có hiện ô "Tìm trong thế giới" không (chỉ khi danh sách đủ dài). */
export function searchShown(count: number): boolean {
  return count > SEARCH_FROM_ENTRIES;
}

/** Từ khoá tìm đang có hiệu lực: ô tìm đã ẩn (xoá bớt còn ≤ SEARCH_FROM_ENTRIES mục) thì không lọc gì nữa,
 * để danh sách không bị lọc bởi một ô người dùng không còn thấy để xoá. */
export function activeQuery(count: number, query: string): string {
  return searchShown(count) ? query : "";
}

/** Dòng phụ của một hàng: "Gợi nhớ khi nhắc: a, b, c…"; null khi chưa có từ khoá. */
export function keysLine(keys: readonly string[]): string | null {
  const ks = keys.map((k) => k.trim()).filter(Boolean);
  if (ks.length === 0) return null;
  return `Gợi nhớ khi nhắc: ${ks.slice(0, 3).join(", ")}${ks.length > 3 ? "…" : ""}`;
}

export const SOURCE_LABELS: Record<LoreSource, string> = {
  world_md: "Nhập từ file",
  card_book: "Từ card gốc",
  manual: "Tự thêm",
};

/** Ước lượng thô phần nhân vật đọc (chỉ cho công cụ nâng cao). */
export function tokenEstimate(content: string): number {
  const text = content.replace(/\s+/g, " ").trim().slice(0, MAX_LORE_ITEM_CHARS);
  const cjk = (text.match(new RegExp(CJK.source, "gu")) ?? []).length;
  return Math.ceil(text.length / 3) + cjk;
}

export function emptyInput(): LoreEntryInput {
  return { title: "", category: "lore", keys: [], known_by: [EVERYONE], content: "", enabled: true, priority: 0 };
}

export function inputOf(e: LoreEntry): LoreEntryInput {
  return {
    title: e.title,
    category: e.category,
    keys: [...e.keys],
    known_by: [...e.known_by],
    content: e.content,
    enabled: e.enabled,
    priority: e.priority,
  };
}

/** Body gửi lên: cắt khoảng trắng, bỏ khoá rỗng; priority trong −100..100. */
export function cleanInput(input: LoreEntryInput): LoreEntryInput {
  const priority = Number.isFinite(input.priority) ? Math.max(-100, Math.min(100, Math.round(input.priority))) : 0;
  return {
    ...input,
    title: input.title.trim(),
    keys: input.keys.map((k) => k.trim()).filter(Boolean),
    known_by: input.known_by.map((v) => v.trim()).filter(Boolean),
    content: input.content.trim(),
    priority,
  };
}

/** Câu hỏi lại khi xoá một mục. */
export function deletePrompt(entry: Pick<LoreEntry, "title" | "source">): string {
  const base = `Xoá “${entry.title}”? Story đã mở mục này sẽ không còn thấy nó.`;
  return entry.source === "manual" ? base : `${base} Nhập lại file sẽ không thêm lại mục này.`;
}

// ---- nhập file ----

/** Lời gợi ý dưới tiêu đề "Thế giới". */
export function sectionHint(charName: string): string {
  const name = nameOr(charName);
  return `Người, nơi chốn và chuyện cũ quanh ${name}. Khi story nhắc tới một từ khoá, ${name} sẽ nhớ ra điều đó. Các mục ở đây được lưu ngay, không cần bấm Lưu nhân vật.`;
}

/** Gợi ý của ô từ khoá. */
export function keysHint(charName: string): string {
  const name = nameOr(charName);
  return `Khi story nhắc đúng một trong các từ này, ${name} sẽ nhớ ra mục này. Có phân biệt dấu: “Lục” khác “lúc”. Tên riêng viết hoa (như “Hạ Trì”) gợi nhớ cả khi ${name} tự nhắc tới; từ thường (như “căn hộ”) chỉ gợi nhớ khi bạn nhắc.`;
}

/** Lỗi của file chọn để nhập (báo ngay, không gửi). */
export function importFileError(file: { name: string; size: number }): string | null {
  if (file.size > MAX_LORE_IMPORT_BYTES) return "File quá lớn (tối đa 500 KB).";
  if (file.size === 0) return "File này trống.";
  return null;
}

/** Không có gì để thêm, sửa hay xoá: nút cuối là "Đóng". */
export function nothingNew(r: Pick<LoreImportResult, "created" | "updated" | "deleted">): boolean {
  return r.created + r.updated + r.deleted === 0;
}

/** Các dòng số liệu của bước xem trước (số 0 thì bỏ dòng). */
export function importSummaryLines(r: LoreImportResult): string[] {
  if (nothingNew(r)) {
    const lines = ["File này đã được nhập, không có gì mới."];
    if (r.kept_edited > 0) lines.push(`Giữ nguyên ${r.kept_edited} mục bạn đã sửa.`);
    if (r.skipped_removed > 0) lines.push(`Bỏ qua ${r.skipped_removed} mục bạn đã xoá.`);
    return lines;
  }
  const lines: string[] = [];
  if (r.created > 0) lines.push(`Thêm ${r.created} mục mới.`);
  if (r.updated > 0) lines.push(`Cập nhật ${r.updated} mục.`);
  if (r.deleted > 0) lines.push(`Xoá ${r.deleted} mục không còn trong file.`);
  if (r.kept_edited > 0) lines.push(`Giữ nguyên ${r.kept_edited} mục bạn đã sửa.`);
  if (r.skipped_removed > 0) lines.push(`Bỏ qua ${r.skipped_removed} mục bạn đã xoá.`);
  if (r.unchanged > 0) lines.push(`Không đổi ${r.unchanged} mục.`);
  return lines;
}

/** Nhãn công tắc xoá mục không còn trong file; null khi không có mục nào như vậy. */
export function missingToggleLabel(r: Pick<LoreImportResult, "missing">): string | null {
  return r.missing > 0 ? `Xoá ${r.missing} mục không còn trong file` : null;
}

/**
 * Ghi chú của server, bỏ câu đã có trên màn hình: dòng số liệu ("Bỏ qua N mục bạn đã xoá.") và câu về
 * người/nơi "Chỉ bạn" (đã có khung riêng, playerOnlyLine).
 */
export function importNotes(r: LoreImportResult): string[] {
  const shown = new Set(importSummaryLines(r));
  const first = r.player_only[0];
  return r.notes.filter((n) => {
    const t = n.trim();
    if (!t || shown.has(t)) return false;
    return !(first && t.startsWith(first) && t.includes("chỉ bạn biết"));
  });
}

/** Câu về người/nơi nhập là "Chỉ bạn"; null khi không có. */
export function playerOnlyLine(names: readonly string[], charName: string): string | null {
  if (names.length === 0) return null;
  return `Chỉ bạn biết: ${names.join(", ")}, vì thế giới có điều chỉ bạn biết về họ. Đổi trong danh sách sau khi nhập nếu ${nameOr(charName)} cũng biết họ.`;
}

/** Dòng nhắc cố định của bước xem trước. */
export function reviewLine(charName: string): string {
  return `Người và nơi chốn được nhập với “Mọi người biết”. Hãy đọc lại: điều gì ${nameOr(charName)} không nên biết thì sửa hoặc chuyển sang “Chỉ bạn”.`;
}

const ACTION_TAGS: Partial<Record<LoreImportAction, string>> = {
  create: "mới",
  update: "cập nhật",
  delete: "sẽ xoá",
  keep_edited: "giữ bản bạn sửa",
  skip_removed: "bạn đã xoá",
  keep_missing: "không còn trong file",
};

/** "Xem các mục": tên theo nhóm, kèm chữ nhỏ cho thao tác (không đổi thì không có chữ). */
export function importItemGroups(items: readonly LoreImportItem[]): EntryGroup<{ title: string; tag: string | null }>[] {
  return groupEntries(items).map((g) => ({
    ...g,
    entries: g.entries.map((i) => ({ title: i.title, tag: ACTION_TAGS[i.action] ?? null })),
  }));
}

// ---- card V2 cũ còn book ----

/** Số mục của `extensions.v2.character_book` mà card còn mang (card import trước Phase 4); 0 nếu không có. */
export function bookEntryCount(extensions: Record<string, unknown> | null | undefined): number {
  const v2 = extensions && typeof extensions === "object" ? (extensions as Record<string, unknown>).v2 : null;
  if (!v2 || typeof v2 !== "object") return 0;
  const book = (v2 as Record<string, unknown>).character_book;
  if (!book || typeof book !== "object") return 0;
  const entries = (book as Record<string, unknown>).entries;
  return Array.isArray(entries) ? entries.length : 0;
}

/** "Lưu nhân vật" của một card còn book: server đã đổi book thành mục thế giới rồi bỏ khỏi card, nên phần
 * "Thế giới" phải tải lại danh sách. `sent` = extensions đã gửi, `saved` = extensions server trả về. */
export function bookConvertedOnSave(
  sent: Record<string, unknown> | null | undefined,
  saved: Record<string, unknown> | null | undefined,
): boolean {
  return bookEntryCount(sent) > 0 && bookEntryCount(saved) === 0;
}

/** Bỏ book khỏi extensions trong bộ nhớ (sau khi server đã dùng nó). */
export function withoutBook(extensions: Record<string, unknown>): Record<string, unknown> {
  const v2 = extensions.v2;
  if (!v2 || typeof v2 !== "object" || !("character_book" in (v2 as object))) return extensions;
  const rest: Record<string, unknown> = { ...(v2 as Record<string, unknown>) };
  delete rest.character_book;
  const out = { ...extensions };
  if (Object.keys(rest).length) out.v2 = rest;
  else delete out.v2;
  return out;
}
