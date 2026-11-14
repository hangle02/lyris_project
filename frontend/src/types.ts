// Mirror of backend/lyris/models.py (the contract) plus the API shapes in docs/phase1.md.
// Keep in sync with the backend; do not invent fields here.

export type Gender = "male" | "female" | "other";
export type Language = "vi" | "en";
export type Mode = "story" | "dm";
export type Role = "user" | "assistant";
export type RelationshipType = "het" | "bl" | "gl" | "none";
export type Pov = "third" | "first";
/** inline: several [Thought: ...] woven into the story; end: exactly one at the end. */
export type ThoughtStyle = "inline" | "end";
/** Phase 2c: who can see a card once the community exists (Phase 7). Stored only for now. */
export type Visibility = "private" | "unlisted" | "public";
export type Rating = "up" | "down";

export interface AddressTerms {
  self_term: string;
  player_term: string;
  nicknames: string[];
  others: string;
}

export interface NarrationPronouns {
  character: string;
  player: string;
}

export interface CharacterCard {
  id: number | null;
  /** Phase 2c: global id set by the backend; send back unchanged. */
  uid?: string | null;
  visibility?: Visibility;
  name: string;
  /** Short role shown under the name, e.g. "Chủ tiệm sách mùa thu". */
  role: string;
  gender: Gender;
  language: Language;
  description: string;
  personality: string;
  appearance: string;
  background: string;
  goals: string;
  secrets: string;
  speech_style: string;
  style_profile: string;
  address_terms: AddressTerms;
  greeting: string;
  example_dialogues: string;
  tags: string[];
  // ---- Phase 2 ----
  /** Default scenario for new stories (Character Card V2 "scenario"). */
  scenario: string;
  alternate_greetings: string[];
  /** Never sent to the model. */
  creator_notes: string;
  /** Backend-managed file name; use CardOut.avatar_url to display. Send back unchanged. */
  avatar: string | null;
  /** Unused Character Card V2 data kept for export (character_book, creator, ...). Send back unchanged. */
  extensions: Record<string, unknown>;
}

export interface Persona {
  id: number | null;
  /** Phase 2c: global id set by the backend. */
  uid?: string | null;
  name: string;
  gender: Gender;
  description: string;
  /** Backend-managed file name; display PersonaOut.avatar_url. */
  avatar?: string | null;
}

export interface Story {
  id: number | null;
  uid?: string | null;
  card_id: number;
  persona_id: number;
  title: string;
  scenario: string;
  language: Language;
  mode: Mode;
  relationship_type: RelationshipType;
  pov: Pov;
  thought_style: ThoughtStyle;
  narration_pronouns: NarrationPronouns;
  model_name: string;
  scene_summary: string;
  created_at: string | null;
  /**
   * Phase 4 (B): show the character's thought cards in this story. Display only (the model still writes
   * [Thought: ...]). Optional so older servers still work: missing means true (`showThoughtsOf(story)`).
   */
  show_thoughts?: boolean;
}

/** GET/POST /api/stories: Story + names of its character and persona. */
export interface StoryOut extends Story {
  card_name: string;
  persona_name: string;
  /** Phase 2: the character's avatar (null if none). */
  card_avatar_url: string | null;
  /** Phase 2: last activity (newest message or creation), ISO UTC. */
  updated_at: string | null;
  // ---- Lyris design ----
  card_role: string;
  /** Visible text of the newest active message (no Thought, no ((...))), max 140 chars; null if none. */
  last_preview: string | null;
  last_role: Role | null;
  last_mode: Mode | null;
  // ---- Phase 3 (optional: older servers do not send them) ----
  /** Strongest of the six emotions; null until the story has a real relationship event. */
  dominant_emotion?: DominantEmotion | null;
  /** Current in-world place from the state fold; null when unknown. */
  location?: string | null;
}

// ---- Phase 2: Character Studio ----

/** Settings of a story (story creation, prompt preview, test chat). */
export interface StorySettings {
  scenario: string;
  language: Language;
  mode: Mode;
  relationship_type: RelationshipType;
  pov: Pov;
  thought_style: ThoughtStyle;
  narration_pronouns: NarrationPronouns;
}

export interface StyleProfileInfo {
  name: string;
  title: string;
  description: string;
  /** narration[language][gender] = default third-person narration pronoun. */
  narration: Record<string, Record<string, string>>;
  address_examples: { self: string; player: string; note?: string }[];
}

/** GET /api/cards/{id}, POST/PUT /api/cards. */
export interface CardOut extends CharacterCard {
  /** Phase 2c: the account that created the card. */
  creator_handle: string | null;
  creator_name: string | null;
  avatar_url: string | null;
  story_count: number;
  updated_at: string | null;
}

/** GET /api/cards (list). */
export interface CardSummary {
  id: number;
  /** Phase 2c. */
  uid: string | null;
  visibility: Visibility;
  creator_handle: string | null;
  creator_name: string | null;
  name: string;
  gender: Gender;
  language: Language;
  style_profile: string;
  description: string;
  tags: string[];
  avatar_url: string | null;
  story_count: number;
  updated_at: string | null;
}

/** A card the user has not saved yet (from AI draft or import) plus notes for the user. */
export interface CardDraftResult {
  card: CharacterCard;
  warnings: string[];
  /** Import only: image held by the server; pass to createCard to attach it as the avatar. */
  avatar_token: string | null;
}

export interface CardDraftRequest {
  idea: string;
  language: Language;
  gender?: Gender | null;
  style_profile?: string | null;
}

export interface PersonaOut extends Persona {
  story_count: number;
  /** Phase 2c. */
  avatar_url: string | null;
}

/** POST /api/stories (Phase 2). Missing fields get defaults from the card, persona and style profile. */
export interface StoryCreateRequest {
  card_id: number;
  persona_id: number;
  title?: string;
  /** 0 = card.greeting, 1.. = card.alternate_greetings[i-1]; -1 = no greeting. */
  greeting_index?: number;
  settings?: Partial<StorySettings>;
  /** Phase 4 (B): top level, not part of `settings` (display only). Omit = true. */
  show_thoughts?: boolean;
}

/** GET /api/stories/defaults?card_id=&persona_id=&language= : what POST /api/stories would use. */
export interface StoryDefaults {
  title: string;
  settings: StorySettings;
}

export interface PromptPreviewRequest {
  card: CharacterCard;
  persona_id: number;
  settings: StorySettings;
}

export interface PromptPreview {
  messages: ChatTurn[];
  token_estimate: Record<string, number>;
  num_ctx: number;
}

export interface TestChatTurn {
  role: "user" | "assistant";
  content: string;
}

export interface TestChatRequest extends PromptPreviewRequest {
  /** Conversation so far (assistant turns raw, with [Thought: ...]); the last one must be the player's. */
  messages: TestChatTurn[];
}

/** SSE events of POST /api/cards/test-chat (nothing is saved). */
export type TestChatEvent =
  /** Phase 4b: every generation slot is busy. */
  | { name: "waiting"; data: Record<string, never> }
  | { name: "start"; data: Record<string, never> }
  | { name: "delta"; data: { kind: DeltaKind; text: string } }
  | { name: "done"; data: { raw: string; visible: string; thought: string | null; stats: GenStats } }
  | { name: "error"; data: { detail: string; technical?: string | null } };

export interface GenStats {
  ttft_ms: number | null;
  total_ms: number | null;
  prompt_tokens: number | null;
  output_tokens: number | null;
  tok_per_s: number | null;
  done_reason: string | null;
  aborted: boolean;
}

export interface Message {
  id: number | null;
  story_id: number;
  turn_index: number;
  variant_index: number;
  is_active: boolean;
  role: Role;
  mode: Mode;
  /** assistant: includes [Thought: ...]; user: verbatim including ((...)) */
  raw_content: string;
  /** assistant: without Thought; user: without ((...)) */
  visible_content: string;
  thought: string | null;
  directive: string | null;
  model_output: string | null;
  /** Never sent by the list/SSE endpoints; present only in the snapshot endpoint's source. */
  prompt_snapshot?: Record<string, unknown> | null;
  model_name: string | null;
  gen_stats: GenStats | null;
  rating: Rating | null;
  variant_count: number;
  created_at: string | null;
  edited_at: string | null;
}

export interface ChatTurn {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface BuiltPrompt {
  messages: ChatTurn[];
  stop: string[];
  options: Record<string, unknown>;
  token_estimate: Record<string, number>;
  dropped_turns: number;
  // ---- Phase 4 (optional) ----
  /** World entries that went into this prompt (block D at the head of the last user message). */
  lore_used?: LoreUse[];
  /** Head of the last user message that prefill may send early (header + carried entries); null if none. */
  lore_head?: string | null;
  /** The last message is an open user turn (prefill only). */
  open_last?: boolean;
}

// ---- API shapes ----

export interface HealthResponse {
  ok: boolean;
  chat_model: string;
  ollama: {
    reachable: boolean;
    models: string[];
    error: string | null;
  };
}

export interface StoryDetail {
  story: Story;
  /**
   * The story's card. Phase 4b: a story started from someone else's public character uses a copy, and
   * then this is a PublicCardView (no personality, background, goals, secrets, example dialogues).
   */
  card: CharacterCard | PublicCardView;
  persona: Persona;
}

export interface DeleteResponse {
  deleted: number;
  messages: Message[];
}

export interface StoryPatch {
  /** Lyris design: Ollama model of this story (must exist in Ollama when it is reachable). */
  model_name?: string;
  mode?: Mode;
  thought_style?: ThoughtStyle;
  title?: string;
  scenario?: string;
  // Phase 2 (card and persona of a story never change)
  language?: Language;
  relationship_type?: RelationshipType;
  pov?: Pov;
  narration_pronouns?: NarrationPronouns;
  /** Phase 4 (B): display only; changing only this does not bump the story's activity time. */
  show_thoughts?: boolean;
}

// ---- SSE events (chat/service.py ChatEvent) ----

export type DeltaKind = "text" | "thought";

export type ChatStreamEvent =
  | { name: "user_message"; data: { message: Message } }
  /** Phase 4b (docs/auth.md §5.5): every generation slot is taken; `start` follows once it is our turn. */
  | { name: "waiting"; data: Record<string, never> }
  | { name: "start"; data: { turn_index: number; variant_index: number } }
  | { name: "delta"; data: { kind: DeltaKind; text: string } }
  | { name: "done"; data: { message: Message } }
  | { name: "error"; data: { detail: string; technical?: string | null } };

// ---- Lyris design (Phase 2b) ----

export interface AppSettings {
  default_persona_id: number | null;
  default_chat_model: string | null;
}

/** 6-emotion matrix, 0-100 each, plus the acting directive (lyris/state/directive.py). */
export interface RelationshipState {
  affection: number;
  trust: number;
  attraction: number;
  obsession: number;
  fear: number;
  aversion: number;
  directive: string | null;
}

export type EmotionKey = Exclude<keyof RelationshipState, "directive">;

export interface Moment {
  text: string;
  effect: string | null;
}

/** The hub chip: the strongest of the six emotions (StoryOut.dominant_emotion). */
export interface DominantEmotion {
  key: EmotionKey;
  value: number;
}

export type MemoryKind = "memory" | "fact";

/** One memory (something that happened in a turn) or fact (a lasting truth). Table `memories`. */
export interface MemoryItem {
  id: number | null;
  story_id: number;
  message_id: number;
  turn_index: number;
  kind: MemoryKind;
  text: string;
  /** fact: who or what it is about. */
  subject: string | null;
  /** 1-5. */
  importance: number;
  created_at: string | null;
}

/** "hybrid" when an embedding model (bge-m3) is installed, else keyword search only. */
export type MemorySearch = "keyword" | "hybrid";

// ---- Phase 3b (phase3.md §10) ----

/** POST /api/stories/{id}/suggestions: quick replies written on demand. */
export interface SuggestionsResponse {
  items: string[];
}

/** One turn of GET /api/stories/{id}/timeline (the "Sự kiện" sheet). */
export interface TimelineEntry {
  turn_index: number;
  message_id: number;
  mode: Mode;
  created_at: string | null;
  /** The memory sentence written for this turn, if any. */
  memory: string | null;
  facts: string[];
  /** Emotion changes of this turn (nonzero only). */
  delta: Partial<Record<EmotionKey, number>>;
  scene: { location: string | null; time: string | null } | null;
}

/** GET /api/stories/{id}/extras. Moment (Phase 8) is still empty. */
export interface StoryExtras {
  relationship: RelationshipState | null;
  /**
   * Up to 3 quick replies the player asked for ("Nhận gợi ý", Phase 3b); kept until the player
   * replies. Never written automatically.
   */
  suggestions: string[];
  moment: Moment | null;
  /**
   * Phase 4: titles of unlocked world entries the player may see (everyone + player-only), most recently
   * triggered first. Character-only entries are not listed (see `lore_count`).
   */
  lore_tags: string[];
  /** Phase 4: the story's character has at least one enabled world entry. Missing = false. */
  lore_available?: boolean;
  /** Phase 4: number of unlocked entries incl. character-only ones (reload signature for the drawer). Missing = 0. */
  lore_count?: number;
  location: string | null;
  in_world_time: string | null;
  // ---- Phase 3 ----
  /** Active memories and facts, newest first, at most 50. */
  memories: MemoryItem[];
  /** Extraction / summary jobs are queued or running for this story. */
  pending: boolean;
  /** Active replies never extracted (the greeting, turn 0, included since Phase 3b); > 0 invites a rebuild. */
  unprocessed_turns: number;
  memory_search: MemorySearch;
  /** Current automatic summary, if any. */
  summary: string | null;
}

export interface TemplateInfo {
  slug: string;
  featured: boolean;
  vibes: string[];
  card: CharacterCard;
  installed_card_id: number | null;
}

/**
 * GET /api/lore/status. Phase 4: world entries live in the DB per character (no world_wiki folder):
 * enabled true, entries = entries of the account, files 0, dir "". Kept for old clients; nothing calls it.
 */
export interface LoreStatus {
  enabled: boolean;
  dir: string;
  files: number;
  entries: number;
  last_sync: string | null;
}

export interface SystemInfo {
  ollama_reachable: boolean;
  ollama_version: string | null;
  ollama_error: string | null;
  models: { name: string; size_gb: number | null; parameter_size: string | null; quantization: string | null }[];
  loaded: { name: string; size_gb: number | null; expires_at: string | null }[];
  memory_total_gb: number | null;
  memory_used_gb: number | null;
  on_battery: boolean | null;
  low_power_mode: boolean | null;
  kv_cache_type: string | null;
  flash_attention: boolean | null;
  num_parallel: number | null;
  max_loaded_models: number | null;
  chat_model_default: string;
  // ---- Phase 3 (optional: older servers do not send them) ----
  /** How memories are looked up: "hybrid" once Ollama has the embedding model. */
  memory_search?: MemorySearch;
  /** Configured embedding model (LYRIS_EMBED_MODEL), for the `ollama pull` hint. */
  embed_model?: string | null;
}

// ---- Phase 2c: account (docs/accounts.md) ----

export interface Account {
  id: number;
  uid: string;
  handle: string;
  display_name: string;
  bio: string;
  profile_completed: boolean;
  created_at: string | null;
  /** Phase 4b (only on GET/PUT /api/account, your own account). */
  role?: AccountRole;
  status?: "active" | "disabled";
  must_change_password?: boolean;
}

/** GET/PUT /api/account. */
export interface AccountOut extends Account {
  avatar_url: string | null;
  banner_url: string | null;
  card_count: number;
  story_count: number;
  persona_count: number;
  /** "Chia sẻ dữ liệu sử dụng ẩn danh" turned off (docs/tracking-plan.md). Older servers: missing. */
  analytics_opt_out?: boolean;
  /** docs/compliance.md §3: the current Terms / Privacy Policy not accepted yet. */
  terms_required?: boolean;
  terms_accepted_at?: string | null;
  privacy_version?: string | null;
  legal_version?: string;
}

/** PATCH /api/account: the account's own settings (only usage sharing for now). */
export interface AccountPatch {
  analytics_opt_out?: boolean;
}

export interface AccountUpdate {
  display_name: string;
  handle: string;
  bio: string;
}

/** GET /api/accounts/{handle}: what others would see (community, Phase 7). */
export interface PublicProfile {
  handle: string;
  display_name: string;
  bio: string;
  avatar_url: string | null;
  banner_url: string | null;
  created_at: string | null;
  /** Cards whose visibility is not private (usually empty until sharing exists). */
  cards: CardSummary[];
}

// ---- Phase 4b: sign-in, accounts, public characters (docs/auth.md §4.4, §6) ----

export type AccountRole = "owner" | "member";

/** The signed-in account as /api/auth/* returns it. */
export interface AuthAccount {
  id: number;
  handle: string;
  display_name: string;
  avatar_url: string | null;
  role: AccountRole;
  must_change_password: boolean;
  profile_completed: boolean;
  /** docs/compliance.md §3: has not accepted the current Terms / Privacy Policy (asked once). */
  terms_required?: boolean;
}

/** GET /api/auth/me (always 200), and the answer of login, signup, setup-owner, change-password. */
export interface AuthState {
  setup_required: boolean;
  /** Only with setup_required, on a brand-new machine: the setup page also asks for a name and handle. */
  setup_needs_profile: boolean;
  account: AuthAccount | null;
  /** Version of the Terms + Privacy Policy now in force (sent back when agreeing). */
  legal_version?: string;
  /** The operator's contact (LYRIS_CONTACT: an email or an https address), null when not set. */
  contact?: string | null;
}

export interface LoginRequest {
  handle: string;
  password: string;
}

export interface SignupRequest {
  invite_code: string;
  handle: string;
  display_name: string;
  password: string;
  /** Required true (docs/compliance.md §3): the box "Tôi đồng ý với Điều khoản…" is ticked. */
  accept_terms: boolean;
  terms_version?: string;
}

export interface SetupOwnerRequest {
  setup_code: string;
  password: string;
  display_name?: string;
  handle?: string;
  accept_terms: boolean;
  terms_version?: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

/** GET /api/admin/accounts (owner only). Never anything inside the account (stories, private cards). */
export interface AdminAccount {
  id: number;
  handle: string;
  display_name: string;
  avatar_url: string | null;
  role: AccountRole;
  status: "active" | "disabled";
  must_change_password: boolean;
  created_at: string;
  last_login_at: string | null;
  invited_by_handle: string | null;
  /** Devices signed in. */
  session_count: number;
}

export type InviteStatus = "active" | "used" | "expired" | "revoked";

export interface InviteOut {
  id: number;
  /** Last 4 characters of the code. */
  hint: string;
  note: string;
  created_at: string;
  expires_at: string;
  status: InviteStatus;
  used_by_handle: string | null;
}

export type InviteDays = 1 | 7 | 30;

/** POST /api/admin/invites: the full code is shown once. */
export interface InviteCreated {
  invite: InviteOut;
  code: string;
}

/** POST /api/admin/accounts/{id}/reset-password: the temporary password is shown once. */
export interface ResetPasswordOut {
  account: AdminAccount;
  temporary_password: string;
}

/**
 * What other accounts see of a public character (allow-list, docs/auth.md §4.4). Also the `card` of
 * a story started from someone else's character (a copy).
 */
export interface PublicCardView {
  id: number;
  uid?: string | null;
  name: string;
  role: string;
  gender: Gender;
  language: Language;
  description: string;
  appearance: string;
  scenario: string;
  greeting: string;
  alternate_greetings: string[];
  tags: string[];
  style_profile: string;
  address_terms: AddressTerms;
  speech_style: string;
  avatar_url: string | null;
  creator_handle: string | null;
  creator_name: string | null;
  visibility: Visibility;
  /** Only `lyris.initial_relationship`, `lyris.narration_character`, `lyris.signature_lines`. */
  extensions: Record<string, unknown>;
}

/** GET /api/cards/{id}/public. `can_start` is false for a copy (opened from a story). */
export interface PublicCardOut extends PublicCardView {
  can_start: boolean;
}

/** GET /api/public-cards: other accounts' public characters, newest first. */
export interface PublicCardSummary {
  id: number;
  uid: string | null;
  visibility: Visibility;
  name: string;
  role: string;
  gender: Gender;
  language: Language;
  style_profile: string;
  description: string;
  tags: string[];
  avatar_url: string | null;
  updated_at: string | null;
  creator_handle: string;
  creator_name: string;
  creator_avatar_url: string | null;
}

// ---- Phase 4: world book (lorebook) per character (docs/phase4.md §2, §13) ----
// Code words (lore, keys, known_by) never appear in normal UI: "Thế giới", "Từ khoá gợi nhớ", "Ai biết điều này".

export type LoreCategory = "lore" | "character" | "place";
export type LoreSource = "manual" | "world_md" | "card_book";
/** Who knows it: everyone ("*"), character ("{{char}}" or the character's name), player ("{{user}}" only), others. */
export type LoreAudience = "everyone" | "character" | "player" | "others";
export type LoreSlot = "carried" | "fresh" | "unsent";

// Server limits (models.py; keep client constants in loreLogic): title 120, 32 keys of ≤ 80 chars,
// known_by ≤ 8, content 4000, import file 500 KB; the prompt reads only 450 chars of an entry.

/** GET/POST/PUT/PATCH /api/cards/{card_id}/lore[/{entry_id}] (LoreEntryOut). */
export interface LoreEntry {
  id: number;
  card_id: number;
  slug: string;
  title: string;
  category: LoreCategory;
  keys: string[];
  /** "*", "{{user}}", "{{char}}" or another character's name. */
  known_by: string[];
  /** May contain {{user}} / {{char}}. */
  content: string;
  source: LoreSource;
  /** An entry imported from a file / card that the user changed (re-import keeps it). */
  edited: boolean;
  enabled: boolean;
  priority: number;
  position: number;
  /** Unused Card V2 fields kept for export. */
  extra: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
  audience: LoreAudience;
  /** Friendly Vietnamese hints for Studio (one-syllable key, no keys, known only by someone else...). */
  warnings: string[];
}

/** POST / PUT body. The server trims, drops empty and duplicate keys, maps the character's name to "{{char}}". */
export interface LoreEntryInput {
  title: string;
  category: LoreCategory;
  keys: string[];
  known_by: string[];
  content: string;
  enabled: boolean;
  /** -100..100 (advanced tools only). */
  priority: number;
}

/** PATCH body: toggle / reorder; never marks the entry as edited. */
export interface LorePatch {
  enabled?: boolean;
  position?: number;
}

/** POST /api/cards/{card_id}/lore/import (world.md text, read with File.text()). */
export interface LoreImportRequest {
  text: string;
  filename?: string | null;
  dry_run: boolean;
  /** Also delete file entries missing from this file (only when the user ticks it in the preview). */
  delete_missing?: boolean;
}

/** POST /api/cards/{card_id}/lore/import-book (character_book kept in an old card's extensions). */
export interface LoreBookImportRequest {
  dry_run: boolean;
}

export type LoreImportAction =
  | "create"
  | "update"
  | "unchanged"
  | "keep_edited"
  | "delete"
  | "keep_missing"
  | "skip_removed";

export interface LoreImportItem {
  slug: string;
  title: string;
  category: LoreCategory;
  action: LoreImportAction;
}

export interface LoreImportResult {
  dry_run: boolean;
  created: number;
  updated: number;
  unchanged: number;
  /** File entries the user edited: neither overwritten nor deleted. */
  kept_edited: number;
  /** Deleted because missing from the file (only with delete_missing). */
  deleted: number;
  /** File entries missing from this file (> 0: show the "Xoá N mục không còn trong file" toggle). */
  missing: number;
  /** Entries the user deleted in Studio; not added back. */
  skipped_removed: number;
  /** People / places imported as "Chỉ bạn" because the world has player-only things about them. */
  player_only: string[];
  /** Sentences dropped because they reveal player-only things, as "Tên mục: câu…" (≤ 50). */
  dropped_sentences: string[];
  items: LoreImportItem[];
  notes: string[];
  warnings: string[];
}

/** One unlocked entry of a story (GET /api/stories/{id}/lore). "others" is never returned. */
export interface UnlockedLore {
  entry_id: number;
  title: string;
  category: LoreCategory;
  audience: "everyone" | "character" | "player";
  /** {{user}} / {{char}} already replaced with the persona / character names. */
  content: string;
  /** Internal turn_index, only to jump to; never print it in the UI. */
  first_turn: number;
  last_turn: number;
  /** Number of turns that triggered it. */
  turns: number;
}

/** GET /api/stories/{story_id}/lore. */
export interface StoryLore {
  /** The character has at least one enabled entry. */
  available: boolean;
  /** The character belongs to this account: offer "Thêm trong Studio". */
  can_edit: boolean;
  card_id: number;
  /** Most recently triggered first. */
  entries: UnlockedLore[];
}

/** GET /api/cards/{card_id}/lore/summary (character profile: names only, never content or story entries). */
export interface LoreSummary {
  /** Enabled entries. */
  total: number;
  /** Names of people everyone knows, at most 8. */
  people: string[];
  /** Names of places everyone knows, at most 8. */
  places: string[];
  /** How many more people / places were not listed (UI prints "+N"). */
  people_more: number;
  places_more: number;
}

/** An entry that went into a prompt (BuiltPrompt.lore_used, prompt snapshot). */
export interface LoreUse {
  entry_id: number;
  title: string;
  slot: "carried" | "fresh";
  tokens: number;
}

// ---- launch: legal pages, consent, reports, account data, usage numbers (docs/compliance.md) ----

export type LegalDoc = "terms" | "privacy";

/** GET /api/legal/{doc} (no sign-in needed). */
export interface LegalOut {
  doc: LegalDoc;
  version: string;
  markdown: string;
}

/** POST /api/account/terms. */
export interface TermsState {
  terms_required: boolean;
  legal_version: string;
  terms_accepted_at: string | null;
  privacy_version: string | null;
}

export type ReportReason = "sexual" | "minor_safety" | "violent" | "hateful" | "self_harm" | "harassment" | "other";
export type ReportStatus = "open" | "reviewed" | "dismissed";
/** What a report is about: an AI reply, or a public character's profile. */
export type ReportTarget = "message" | "character";

/** POST /api/cards/{id}/report body (a public character's profile). */
export interface CardReportRequest {
  reason: ReportReason;
  /** At most 300 characters. */
  note: string;
}

/** POST /api/messages/{id}/report body. */
export interface ReportRequest {
  reason: ReportReason;
  /** At most 300 characters. */
  note: string;
  /** Send the reply text along for the owner to review (off unless the reporter turns it on). */
  share_text: boolean;
}

export interface ReportOut {
  id: number;
  reason: ReportReason;
  shared_text: boolean;
  status: ReportStatus;
}

/** GET /api/admin/reports (owner): never who reported, nor the story or message. */
export interface AdminReport {
  id: number;
  target: ReportTarget;
  created_at: string;
  updated_at: string;
  reason: ReportReason;
  note: string;
  mode: Mode | null;
  language: Language | null;
  model_name: string | null;
  shared_text: boolean;
  message_text: string | null;
  status: ReportStatus;
  reviewed_at: string | null;
  public_card_id: number | null;
  public_card_name: string | null;
  public_card_creator: string | null;
}

/** DELETE /api/account. */
export interface AccountDeleted {
  deleted: boolean;
  /** The owner deleted the last account: Lyris is back to its first-run setup. */
  setup_required: boolean;
}

/** GET /api/admin/analytics/summary (owner). */
export interface AnalyticsSummary {
  since: string;
  until: string;
  days: number;
  total_events: number;
  counts: { name: string; count: number }[];
  dau: number;
  wau: number;
  mau: number;
  daily: { date: string; active: number }[];
  funnel: { step: string; label: string; users: number; converted: number }[];
  retention: {
    d1: { cohort: number; retained: number; rate: number | null };
    d7: { cohort: number; retained: number; rate: number | null };
  };
  posthog_enabled: boolean;
}
