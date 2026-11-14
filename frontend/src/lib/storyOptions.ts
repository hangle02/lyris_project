// Nhãn và logic thuần cho thiết lập story (trang tạo story, bảng thiết lập story, header).
import type {
  Gender,
  Language,
  Mode,
  NarrationPronouns,
  Pov,
  RelationshipType,
  Story,
  StoryPatch,
  StyleProfileInfo,
  ThoughtStyle,
} from "../types.ts";

export interface Option<T extends string> {
  value: T;
  label: string;
  hint?: string;
}

export const LANGUAGE_OPTIONS: Option<Language>[] = [
  { value: "vi", label: "Tiếng Việt" },
  { value: "en", label: "Tiếng Anh" },
];

export const MODE_OPTIONS: Option<Mode>[] = [
  { value: "story", label: "Story", hint: "Văn tiểu thuyết, có suy nghĩ của nhân vật." },
  { value: "dm", label: "DM", hint: "Nhắn tin riêng, như trên điện thoại." },
];

export const RELATIONSHIP_OPTIONS: Option<RelationshipType>[] = [
  { value: "het", label: "Nam - nữ" },
  { value: "bl", label: "Nam - nam (đam mỹ)" },
  { value: "gl", label: "Nữ - nữ (bách hợp)" },
  { value: "none", label: "Không lãng mạn" },
];

export const POV_OPTIONS: Option<Pov>[] = [
  { value: "third", label: "Ngôi thứ ba", hint: "Người dẫn truyện kể về cả hai bằng đại từ." },
  { value: "first", label: "Ngôi thứ nhất", hint: "Nhân vật tự kể bằng giọng của mình." },
];

export const THOUGHT_STYLE_OPTIONS: Option<ThoughtStyle>[] = [
  {
    value: "inline",
    label: "Lồng trong truyện",
    hint: "Vài dòng suy nghĩ xen giữa diễn biến, ngay sau hành động hay lời nói khơi ra nó.",
  },
  { value: "end", label: "Một đoạn ở cuối", hint: "Một đoạn suy nghĩ dài hơn ở cuối mỗi lượt." },
];

/**
 * Phase 4 (B): show the character's thought cards in this story (display only: the character still
 * thinks, the model still writes [Thought: ...]). Missing on older servers means true.
 */
export function showThoughtsOf(story: Pick<Story, "show_thoughts"> | null | undefined): boolean {
  return story?.show_thoughts !== false;
}

/** The one switch used in the start sheet, the story settings and the header's "Suy nghĩ" menu. */
export const SHOW_THOUGHTS_LABEL = "Đọc suy nghĩ của nhân vật";

export function showThoughtsHint(characterName: string): string {
  const name = characterName.trim() || "Nhân vật";
  return `Tắt thì thẻ suy nghĩ không hiện trong story. ${name} vẫn nghĩ như thường, chỉ là bạn không đọc thấy.`;
}

export const GENDER_LABELS: Record<Gender, string> = { male: "Nam", female: "Nữ", other: "Khác" };

export function labelOf<T extends string>(options: Option<T>[], value: T): string {
  return options.find((o) => o.value === value)?.label ?? value;
}

const FALLBACK_NARRATION: Record<Language, Record<Gender, string>> = {
  vi: { male: "anh", female: "cô", other: "" },
  en: { male: "he", female: "she", other: "they" },
};

/** Third-person narration pronoun from the style profile (empty in the profile -> the name in Vietnamese). */
export function narrationFor(
  profile: StyleProfileInfo | null | undefined,
  language: Language,
  gender: Gender,
  name: string,
): string {
  const fromProfile = profile?.narration?.[language]?.[gender];
  const value = (fromProfile ?? FALLBACK_NARRATION[language][gender]).trim();
  return value || name.trim();
}

export interface PronounContext {
  profile: StyleProfileInfo | null | undefined;
  language: Language;
  pov: Pov;
  cardGender: Gender;
  cardName: string;
  personaGender: Gender;
  personaName: string;
}

/** Suggested narration pronouns; first person -> the character narrates as "tôi" / "I". */
export function suggestPronouns(ctx: PronounContext): NarrationPronouns {
  const player = narrationFor(ctx.profile, ctx.language, ctx.personaGender, ctx.personaName);
  const character =
    ctx.pov === "first"
      ? ctx.language === "vi"
        ? "tôi"
        : "I"
      : narrationFor(ctx.profile, ctx.language, ctx.cardGender, ctx.cardName);
  return { character, player };
}

/** Same rule as the backend's default_settings. */
export function defaultRelationship(cardGender: Gender, personaGender: Gender): RelationshipType {
  if (cardGender === "other" || personaGender === "other") return "none";
  if (cardGender !== personaGender) return "het";
  return cardGender === "male" ? "bl" : "gl";
}

/** Editable story settings (everything except mode, which the header toggles). */
export interface StorySettingsForm {
  title: string;
  scenario: string;
  language: Language;
  relationship_type: RelationshipType;
  pov: Pov;
  narration_pronouns: NarrationPronouns;
  thought_style: ThoughtStyle;
  /** Phase 4 (B): display only; saved with the same "Lưu". */
  show_thoughts: boolean;
}

export function formFromStory(s: Story): StorySettingsForm {
  return {
    title: s.title,
    scenario: s.scenario,
    language: s.language,
    relationship_type: s.relationship_type,
    pov: s.pov,
    narration_pronouns: { ...s.narration_pronouns },
    thought_style: s.thought_style,
    show_thoughts: showThoughtsOf(s),
  };
}

/** Only the changed fields (trimmed); {} when nothing changed. */
export function settingsPatch(before: Story, form: StorySettingsForm): StoryPatch {
  const patch: StoryPatch = {};
  const title = form.title.trim();
  if (title && title !== before.title) patch.title = title;
  const scenario = form.scenario.trim();
  if (scenario !== before.scenario.trim()) patch.scenario = scenario;
  if (form.language !== before.language) patch.language = form.language;
  if (form.relationship_type !== before.relationship_type) patch.relationship_type = form.relationship_type;
  if (form.pov !== before.pov) patch.pov = form.pov;
  if (form.thought_style !== before.thought_style) patch.thought_style = form.thought_style;
  if (form.show_thoughts !== showThoughtsOf(before)) patch.show_thoughts = form.show_thoughts;
  const np = {
    character: form.narration_pronouns.character.trim(),
    player: form.narration_pronouns.player.trim(),
  };
  if (np.character !== before.narration_pronouns.character || np.player !== before.narration_pronouns.player) {
    patch.narration_pronouns = np;
  }
  return patch;
}

/** Problems that block saving or creating (Vietnamese, for the UI). */
export function validateSettingsForm(form: StorySettingsForm): string[] {
  const errors: string[] = [];
  if (!form.title.trim()) errors.push("Tiêu đề không được để trống.");
  if (form.title.trim().length > 120) errors.push("Tiêu đề tối đa 120 ký tự.");
  if (!form.narration_pronouns.character.trim() || !form.narration_pronouns.player.trim()) {
    errors.push("Hãy điền đủ đại từ dẫn truyện cho nhân vật và người chơi.");
  }
  return errors;
}

/** Changes that only take effect on the next reply (shown as a reminder). */
export function affectsNextTurn(patch: StoryPatch): boolean {
  return (
    patch.language !== undefined ||
    patch.pov !== undefined ||
    patch.narration_pronouns !== undefined ||
    patch.relationship_type !== undefined ||
    patch.thought_style !== undefined ||
    patch.scenario !== undefined
  );
}

/** Pick a greeting: 0 = card.greeting, i = alternate_greetings[i-1], -1 = none. */
export function greetingAt(greeting: string, alternates: string[], index: number): string {
  if (index < 0) return "";
  if (index === 0) return greeting;
  return alternates[index - 1] ?? "";
}

/** Replace {{char}} / {{user}} (case-insensitive, like the backend's PromptContext.fill). */
export function fillPlaceholders(text: string, charName: string, userName: string): string {
  return text.replace(/\{\{\s*char\s*\}\}/gi, charName).replace(/\{\{\s*user\s*\}\}/gi, userName);
}

const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

/** Parses a backend timestamp (UTC; old SQLite values may lack the zone). NaN if invalid. */
export function parseTimestamp(iso: string | null | undefined): number {
  if (!iso) return NaN;
  const d = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso.replace(" ", "T")}Z`);
  return d.getTime();
}

/** "vừa xong", "5 phút trước", "3 giờ trước", "hôm qua", "4 ngày trước", or a date. */
export function formatActivity(iso: string | null | undefined, now: number = Date.now()): string {
  const t = parseTimestamp(iso);
  if (Number.isNaN(t)) return "";
  const diff = now - t;
  if (diff < MINUTE) return "vừa xong";
  if (diff < HOUR) return `${Math.floor(diff / MINUTE)} phút trước`;
  if (diff < DAY) return `${Math.floor(diff / HOUR)} giờ trước`;
  if (diff < 2 * DAY) return "hôm qua";
  if (diff < 7 * DAY) return `${Math.floor(diff / DAY)} ngày trước`;
  const d = new Date(t);
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  return `${dd}/${mm}/${d.getFullYear()}`;
}
