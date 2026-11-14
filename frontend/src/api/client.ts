import { AUTH_EVENT, signalsAuth } from "../lib/auth.ts";
import { friendlyError } from "../lib/friendlyError.ts";
import type { FriendlyError } from "../lib/friendlyError.ts";
import { SSEParser } from "../lib/sse.ts";
import type {
  AccountDeleted,
  AccountOut,
  AccountPatch,
  AdminAccount,
  AdminReport,
  AnalyticsSummary,
  LegalDoc,
  LegalOut,
  ReportOut,
  ReportRequest,
  CardReportRequest,
  ReportStatus,
  TermsState,
  AuthState,
  ChangePasswordRequest,
  InviteCreated,
  InviteDays,
  InviteOut,
  LoginRequest,
  PublicCardOut,
  PublicCardSummary,
  ResetPasswordOut,
  SetupOwnerRequest,
  SignupRequest,
  AccountUpdate,
  PublicProfile,
  AppSettings,
  LoreEntry,
  LoreEntryInput,
  LoreImportRequest,
  LoreImportResult,
  LorePatch,
  LoreStatus,
  LoreSummary,
  StoryExtras,
  StoryLore,
  SystemInfo,
  TemplateInfo,
  CardDraftRequest,
  CardDraftResult,
  CardOut,
  CardSummary,
  CharacterCard,
  ChatStreamEvent,
  DeleteResponse,
  HealthResponse,
  Language,
  Message,
  Persona,
  PersonaOut,
  PromptPreview,
  PromptPreviewRequest,
  Rating,
  Story,
  StoryCreateRequest,
  StoryDefaults,
  StoryDetail,
  StoryOut,
  StoryPatch,
  StyleProfileInfo,
  SuggestionsResponse,
  TimelineEntry,
  TestChatEvent,
  TestChatRequest,
} from "../types.ts";

const BASE = "/api";

/**
 * Sent with every request (docs/auth.md §3.3): the server refuses a write without it, and another site
 * cannot add a custom header without a CORS preflight the server never allows.
 */
export const CSRF_HEADER = { "X-Lyris": "1" } as const;

/** Same-origin requests carry the HttpOnly sign-in cookie (the token is never read by JavaScript). */
const CREDENTIALS: RequestCredentials = "same-origin";

export class ApiError extends Error {
  readonly status: number;
  /** Technical detail for "Chi tiết" (the server's `technical` field, or the client's own). */
  readonly technical: string | null;
  /** Machine-readable reason of a sign-in error (Phase 4b: "auth_required", "owner_only", "rate_limited"...). */
  readonly code: string | null;
  constructor(status: number, message: string, technical: string | null = null, code: string | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.technical = technical;
    this.code = code;
  }
}

/**
 * Tells the sign-in gate (hooks/useAuth) that the server answered "signed out", "change your password"
 * or "set up the owner first" (window event `lyris:auth`). Nothing happens outside a browser.
 */
function notifyAuth(path: string, err: ApiError): void {
  if (!signalsAuth(path, err.status, err.code)) return;
  const target = globalThis as unknown as { dispatchEvent?: (e: Event) => boolean };
  if (typeof target.dispatchEvent !== "function" || typeof CustomEvent !== "function") return;
  target.dispatchEvent(new CustomEvent(AUTH_EVENT, { detail: { status: err.status, code: err.code } }));
}

const NETWORK_ERROR = "Không kết nối được Lyris. Hãy kiểm tra mạng rồi thử lại sau giây lát.";
/** What "Chi tiết" says about NETWORK_ERROR. */
const NETWORK_TECHNICAL = "Không gọi được máy chủ Lyris (/api). Kiểm tra backend đã chạy chưa: bash scripts/dev.sh.";

/** Where-prefixes FastAPI puts first in `loc`; the field path after them is what the user needs. */
const LOC_ROOTS = new Set(["body", "query", "path", "header", "cookie"]);

/** "handle", "card.address_terms.self_term", "tags.0"; "" when the error is about the whole body. */
export function locToText(loc: unknown): string {
  if (!Array.isArray(loc)) return "";
  const parts = loc.filter((p): p is string | number => typeof p === "string" || typeof p === "number").map(String);
  if (parts.length > 0 && LOC_ROOTS.has(parts[0] ?? "")) parts.shift();
  return parts.join(".");
}

/**
 * `detail` of an error body as one line. A FastAPI 422 list ([{loc, msg, type}, ...]) keeps the
 * field of each error: "Dữ liệu không hợp lệ: handle: String should have at least 3 characters".
 */
export function detailToText(detail: unknown): string | null {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const parts = detail
      .map((d) => {
        if (!d || typeof d !== "object" || !("msg" in d)) return null;
        const msg = String((d as { msg: unknown }).msg).trim();
        if (!msg) return null;
        const where = locToText((d as { loc?: unknown }).loc);
        return where ? `${where}: ${msg}` : msg;
      })
      .filter((s): s is string => !!s);
    if (parts.length) return `Dữ liệu không hợp lệ: ${parts.join("; ")}`;
  }
  return null;
}

function statusFallback(status: number): string {
  switch (status) {
    case 401:
      return "Bạn cần đăng nhập.";
    case 403:
      return "Bạn không làm được việc này. Hãy tải lại trang.";
    case 404:
      return "Không tìm thấy dữ liệu (có thể đã bị xoá).";
    case 429:
      return "Bạn đã thử sai nhiều lần. Hãy đợi 15 phút rồi thử lại.";
    case 409:
      return "Đang bận sinh câu trả lời khác, hoặc thao tác này không hợp lệ lúc này.";
    case 422:
      return "Dữ liệu gửi lên không hợp lệ.";
    default:
      return `Máy chủ báo lỗi (HTTP ${status}).`;
  }
}

async function errorFromResponse(res: Response, path: string): Promise<ApiError> {
  const err = await readError(res);
  notifyAuth(path, err);
  return err;
}

async function readError(res: Response): Promise<ApiError> {
  let msg: string | null = null;
  let technical: string | null = null;
  let code: string | null = null;
  try {
    const text = await res.text();
    if (text) {
      try {
        const body: unknown = JSON.parse(text);
        if (body && typeof body === "object" && "detail" in body) {
          msg = detailToText((body as { detail: unknown }).detail);
        }
        technical = technicalOf(body);
        code = codeOf(body);
      } catch {
        // not JSON (e.g. proxy error page)
      }
    }
  } catch {
    // ignore body read errors
  }
  if (!msg && (res.status === 502 || res.status === 503 || res.status === 504)) {
    return new ApiError(res.status, NETWORK_ERROR, technical ?? `${NETWORK_TECHNICAL} (HTTP ${res.status})`);
  }
  return new ApiError(res.status, msg ?? statusFallback(res.status), technical, code);
}

/** `code` of an error body (Phase 4b sign-in errors), or null. */
export function codeOf(body: unknown): string | null {
  if (!body || typeof body !== "object" || !("code" in body)) return null;
  const c = (body as { code: unknown }).code;
  return typeof c === "string" && c ? c : null;
}

/** `technical` of an error body (Phase 3b: `{detail, technical}`), or null. */
export function technicalOf(body: unknown): string | null {
  if (!body || typeof body !== "object" || !("technical" in body)) return null;
  const t = (body as { technical: unknown }).technical;
  return typeof t === "string" && t.trim() ? t.trim() : null;
}

async function request<T>(method: string, path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  let res: Response;
  try {
    res = await fetch(BASE + path, {
      method,
      credentials: CREDENTIALS,
      headers: body !== undefined ? { ...CSRF_HEADER, "Content-Type": "application/json" } : { ...CSRF_HEADER },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (e) {
    if (isAbortError(e)) throw e;
    throw new ApiError(0, NETWORK_ERROR, NETWORK_TECHNICAL);
  }
  if (!res.ok) throw await errorFromResponse(res, path);
  // 204 (e.g. a DELETE) has no body.
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

/** Sends a file as the raw request body (no multipart): the server reads Content-Type and bytes. */
async function upload<T>(method: string, path: string, file: Blob, signal?: AbortSignal): Promise<T> {
  let res: Response;
  try {
    res = await fetch(BASE + path, {
      method,
      credentials: CREDENTIALS,
      headers: { ...CSRF_HEADER, "Content-Type": file.type || "application/octet-stream" },
      body: file,
      signal,
    });
  } catch (e) {
    if (isAbortError(e)) throw e;
    throw new ApiError(0, NETWORK_ERROR, NETWORK_TECHNICAL);
  }
  if (!res.ok) throw await errorFromResponse(res, path);
  return (await res.json()) as T;
}

function query(params: Record<string, string | number | boolean | null | undefined>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== null) q.set(k, String(v));
  const text = q.toString();
  return text ? `?${text}` : "";
}

export function isAbortError(e: unknown): boolean {
  return e instanceof DOMException ? e.name === "AbortError" : e instanceof Error && e.name === "AbortError";
}

/** An error in plain words plus its technical text for "Chi tiết" (lib/friendlyError). */
export function friendlyOf(e: unknown): FriendlyError {
  if (e instanceof ApiError) return friendlyError(e.message, e.technical);
  if (e instanceof Error && e.message) return friendlyError(e.message);
  return friendlyError("Đã có lỗi không xác định.");
}

/** The plain sentence of an error (never "Ollama", "model", HTTP codes). */
export function errorMessage(e: unknown): string {
  return friendlyOf(e).text;
}

/** The technical text of an error for a "Chi tiết" disclosure; null when there is none. */
export function errorTechnical(e: unknown): string | null {
  return friendlyOf(e).technical;
}

// ---- REST ----

export const api = {
  health: (signal?: AbortSignal) => request<HealthResponse>("GET", "/health", undefined, signal),
  listStories: () => request<StoryOut[]>("GET", "/stories"),
  createStory: (title?: string) => request<StoryOut>("POST", "/stories", title ? { title } : {}),
  getStory: (id: number) => request<StoryDetail>("GET", `/stories/${id}`),
  patchStory: (id: number, patch: StoryPatch) => request<Story>("PATCH", `/stories/${id}`, patch),
  listMessages: (storyId: number) => request<Message[]>("GET", `/stories/${storyId}/messages`),
  selectVariant: (messageId: number, variantIndex: number) =>
    request<Message>("POST", `/messages/${messageId}/variant`, { variant_index: variantIndex }),
  editMessage: (messageId: number, content: string) =>
    request<Message>("PATCH", `/messages/${messageId}`, { content }),
  deleteFrom: (messageId: number) => request<DeleteResponse>("DELETE", `/messages/${messageId}`),
  setFeedback: (messageId: number, rating: Rating | null) =>
    request<Message>("PUT", `/messages/${messageId}/feedback`, { rating }),

  // ---- Phase 2: stories ----
  /** Phase 2 story creation (card + persona + settings). `createStory(title)` keeps the Phase 1 seed behavior. */
  createStoryFor: (body: StoryCreateRequest) => request<StoryOut>("POST", "/stories", body),
  storyDefaults: (cardId: number, personaId: number, language?: Language) =>
    request<StoryDefaults>(
      "GET",
      `/stories/defaults${query({ card_id: cardId, persona_id: personaId, language })}`,
    ),
  deleteStory: (id: number) => request<{ deleted: number }>("DELETE", `/stories/${id}`),

  // ---- Phase 2: style profiles ----
  listStyles: () => request<StyleProfileInfo[]>("GET", "/styles"),

  // ---- Phase 2: cards ----
  listCards: () => request<CardSummary[]>("GET", "/cards"),
  getCard: (id: number) => request<CardOut>("GET", `/cards/${id}`),
  /**
   * `avatarToken` attaches the image held from an import. `via`: how the card was made, and
   * `withAvatar`: a picture is uploaded right after (uploadAvatar), both for the usage numbers only
   * (docs/tracking-plan.md `character_created`).
   */
  createCard: (
    card: CharacterCard,
    avatarToken?: string | null,
    via: "form" | "ai_draft" | "import" = "form",
    withAvatar = false,
  ) =>
    request<CardOut>("POST", `/cards${query({ via, with_avatar: withAvatar || undefined })}`, {
      card,
      avatar_token: avatarToken ?? null,
    }),
  updateCard: (id: number, card: CharacterCard) => request<CardOut>("PUT", `/cards/${id}`, card),
  /** 409 when stories use the card, unless withStories (deletes those stories and their messages too). */
  deleteCard: (id: number, withStories = false) =>
    request<{ deleted_stories: number }>("DELETE", `/cards/${id}${query({ with_stories: withStories || undefined })}`),
  duplicateCard: (id: number) => request<CardOut>("POST", `/cards/${id}/duplicate`),
  uploadAvatar: (id: number, file: Blob) => upload<CardOut>("PUT", `/cards/${id}/avatar`, file),
  deleteAvatar: (id: number) => request<CardOut>("DELETE", `/cards/${id}/avatar`),
  /** URL to download the card (Character Card V2); open it or put it in an <a download>. */
  exportCardUrl: (id: number, format: "json" | "png") => `${BASE}/cards/${id}/export${query({ format })}`,
  /** Character Card V2/V1 JSON or PNG file. Returns an unsaved draft. */
  importCard: (file: Blob) => upload<CardDraftResult>("POST", "/cards/import", file),
  /** AI viết nháp: can take 1-2 minutes. Returns an unsaved draft. */
  draftCard: (body: CardDraftRequest, signal?: AbortSignal) =>
    request<CardDraftResult>("POST", "/cards/draft", body, signal),
  previewPrompt: (body: PromptPreviewRequest) => request<PromptPreview>("POST", "/cards/preview-prompt", body),

  // ---- Phase 2: personas ----
  listPersonas: () => request<PersonaOut[]>("GET", "/personas"),
  createPersona: (p: Persona) => request<PersonaOut>("POST", "/personas", p),
  updatePersona: (id: number, p: Persona) => request<PersonaOut>("PUT", `/personas/${id}`, p),
  // ---- Lyris design (Phase 2b) ----
  getSettings: () => request<AppSettings>("GET", "/settings"),
  putSettings: (s: AppSettings) => request<AppSettings>("PUT", "/settings", s),
  getSystem: (signal?: AbortSignal) => request<SystemInfo>("GET", "/system", undefined, signal),
  /** Read it through chat/chatLogic.normalizeExtras: older servers miss the Phase 3 fields. */
  getStoryExtras: (storyId: number, signal?: AbortSignal) =>
    request<StoryExtras>("GET", `/stories/${storyId}/extras`, undefined, signal),
  // ---- Phase 3: state & memory ----
  /** Forgets one memory or fact (deletes the row). 404 when it is not in this story. */
  forgetMemory: (storyId: number, memoryId: number) =>
    request<unknown>("DELETE", `/stories/${storyId}/memories/${memoryId}`),
  /** Queues extraction for every active reply not processed yet; `queued` jobs were added. */
  rebuildStoryState: (storyId: number) => request<{ queued: number }>("POST", `/stories/${storyId}/state/rebuild`),
  // ---- Phase 3b ----
  /** Quick replies on demand ("Nhận gợi ý"). 409 while busy or when the newest message is the player's. */
  requestSuggestions: (storyId: number, signal?: AbortSignal) =>
    request<SuggestionsResponse>("POST", `/stories/${storyId}/suggestions`, undefined, signal),
  /** Story timeline ("Xem sự kiện"); read it through chat/eventsLogic.normalizeTimeline. */
  getTimeline: (storyId: number, signal?: AbortSignal) =>
    request<TimelineEntry[]>("GET", `/stories/${storyId}/timeline`, undefined, signal),
  getLoreStatus: () => request<LoreStatus>("GET", "/lore/status"),
  listTemplates: () => request<TemplateInfo[]>("GET", "/templates"),
  /** Returns the existing card when the template is already installed. */
  installTemplate: (slug: string) => request<CardOut>("POST", `/templates/${encodeURIComponent(slug)}/install`),

  // ---- Phase 4: world book per character (docs/phase4.md §8) ----
  /** Entries of a card in display order (position, id). */
  listLore: (cardId: number, signal?: AbortSignal) => request<LoreEntry[]>("GET", `/cards/${cardId}/lore`, undefined, signal),
  /** 422 with a plain Vietnamese sentence; 409 past 500 entries. */
  createLore: (cardId: number, body: LoreEntryInput) => request<LoreEntry>("POST", `/cards/${cardId}/lore`, body),
  updateLore: (cardId: number, entryId: number, body: LoreEntryInput) =>
    request<LoreEntry>("PUT", `/cards/${cardId}/lore/${entryId}`, body),
  /** Toggle / reorder (never marks an imported entry as edited). */
  patchLore: (cardId: number, entryId: number, patch: LorePatch) =>
    request<LoreEntry>("PATCH", `/cards/${cardId}/lore/${entryId}`, patch),
  /** An imported entry stays as a tombstone so a re-import does not bring it back. */
  deleteLore: (cardId: number, entryId: number) =>
    request<{ deleted: number }>("DELETE", `/cards/${cardId}/lore/${entryId}`),
  /** world.md text; `dry_run` for the preview step. */
  importLore: (cardId: number, body: LoreImportRequest, signal?: AbortSignal) =>
    request<LoreImportResult>("POST", `/cards/${cardId}/lore/import`, body, signal),
  /** The character_book an old imported card still carries (Card V2). */
  importCardBook: (cardId: number, dryRun: boolean, signal?: AbortSignal) =>
    request<LoreImportResult>("POST", `/cards/${cardId}/lore/import-book`, { dry_run: dryRun }, signal),
  /** Character profile teaser (names of people and places everyone knows). 404 for a template not installed. */
  getLoreSummary: (cardId: number, signal?: AbortSignal) =>
    request<LoreSummary>("GET", `/cards/${cardId}/lore/summary`, undefined, signal),
  /** Unlocked entries of a story (heart drawer). */
  getStoryLore: (storyId: number, signal?: AbortSignal) =>
    request<StoryLore>("GET", `/stories/${storyId}/lore`, undefined, signal),

  // ---- Phase 2c: account ----
  getAccount: () => request<AccountOut>("GET", "/account"),
  /** 422 with a Vietnamese message when the handle is invalid or taken. */
  updateAccount: (body: AccountUpdate) => request<AccountOut>("PUT", "/account", body),
  uploadAccountAvatar: (file: Blob) => upload<AccountOut>("PUT", "/account/avatar", file),
  deleteAccountAvatar: () => request<AccountOut>("DELETE", "/account/avatar"),
  uploadAccountBanner: (file: Blob) => upload<AccountOut>("PUT", "/account/banner", file),
  deleteAccountBanner: () => request<AccountOut>("DELETE", "/account/banner"),
  getProfile: (handle: string) => request<PublicProfile>("GET", `/accounts/${encodeURIComponent(handle)}`),
  uploadPersonaAvatar: (id: number, file: Blob) => upload<PersonaOut>("PUT", `/personas/${id}/avatar`, file),
  deletePersonaAvatar: (id: number) => request<PersonaOut>("DELETE", `/personas/${id}/avatar`),

  // ---- Phase 4b: sign-in (docs/auth.md §6.2). Errors carry the server's Vietnamese sentence and `code`. ----
  /** Always 200: `account` is null when signed out; `setup_required` before the owner has a password. */
  authMe: (signal?: AbortSignal) => request<AuthState>("GET", "/auth/me", undefined, signal),
  setupOwner: (body: SetupOwnerRequest) => request<AuthState>("POST", "/auth/setup-owner", body),
  login: (body: LoginRequest) => request<AuthState>("POST", "/auth/login", body),
  signup: (body: SignupRequest) => request<AuthState>("POST", "/auth/signup", body),
  logout: () => request<void>("POST", "/auth/logout"),
  /** Signs out every device of the account, this one too. */
  logoutAll: () => request<void>("POST", "/auth/logout-all"),
  /** Signs out the other devices; this one gets a fresh sign-in. */
  changePassword: (body: ChangePasswordRequest) => request<AuthState>("POST", "/auth/change-password", body),

  // ---- Phase 4b: owner only ("Quản lý tài khoản", §6.3) ----
  listAdminAccounts: () => request<AdminAccount[]>("GET", "/admin/accounts"),
  resetAccountPassword: (id: number) => request<ResetPasswordOut>("POST", `/admin/accounts/${id}/reset-password`),
  disableAccount: (id: number) => request<AdminAccount>("POST", `/admin/accounts/${id}/disable`),
  enableAccount: (id: number) => request<AdminAccount>("POST", `/admin/accounts/${id}/enable`),
  listInvites: () => request<InviteOut[]>("GET", "/admin/invites"),
  createInvite: (note: string, expiresInDays: InviteDays) =>
    request<InviteCreated>("POST", "/admin/invites", { note, expires_in_days: expiresInDays }),
  revokeInvite: (id: number) => request<void>("DELETE", `/admin/invites/${id}`),

  // ---- Phase 4b: other accounts' public characters (§4.4, §6.4) ----
  listPublicCards: () => request<PublicCardSummary[]>("GET", "/public-cards"),
  /** Read-only profile: someone's public card, your own card, or the copy of a story (`can_start` false). */
  getPublicCard: (id: number) => request<PublicCardOut>("GET", `/cards/${id}/public`),

  /** 409 when stories use the persona, unless withStories. */
  deletePersona: (id: number, withStories = false) =>
    request<{ deleted_stories: number }>(
      "DELETE",
      `/personas/${id}${query({ with_stories: withStories || undefined })}`,
    ),

  // ---- launch: legal, consent, reports, own data (docs/compliance.md §7) ----
  /** Terms / Privacy Policy as markdown; works signed out and before the owner setup. */
  getLegal: (doc: LegalDoc, signal?: AbortSignal) => request<LegalOut>("GET", `/legal/${doc}`, undefined, signal),
  /** The one-time agreement of an existing account (409 when the version moved on meanwhile). */
  acceptTerms: (version: string) => request<TermsState>("POST", "/account/terms", { accept_terms: true, version }),
  /** "Chia sẻ dữ liệu sử dụng ẩn danh": turning it off also deletes the account's stored usage events. */
  patchAccount: (body: AccountPatch) => request<AccountOut>("PATCH", "/account", body),
  /** 404 for a message outside your stories; 422 for a player's turn. */
  reportMessage: (messageId: number, body: ReportRequest) => request<ReportOut>("POST", `/messages/${messageId}/report`, body),
  /** Someone else's public character (or the original of a story's copy). 404 when not public; 422 for your own. */
  reportCard: (cardId: number, body: CardReportRequest) => request<ReportOut>("POST", `/cards/${cardId}/report`, body),
  /** Owner: hide a reported public character (it becomes private; its creator keeps it). */
  unpublishCard: (cardId: number) => request<{ unpublished: boolean }>("POST", `/admin/cards/${cardId}/unpublish`),
  /** 400 `bad_password`; 409 while a story is generating, or the owner with other accounts left. */
  deleteAccount: (password: string) => request<AccountDeleted>("DELETE", "/account", { password }),
  /** Owner: reports, newest first. */
  listReports: (status?: ReportStatus) => request<AdminReport[]>("GET", `/admin/reports${query({ status })}`),
  setReportStatus: (id: number, status: ReportStatus) => request<AdminReport>("PATCH", `/admin/reports/${id}`, { status }),
  /** Owner: usage numbers of the last `days` days. */
  analyticsSummary: (days: number, signal?: AbortSignal) =>
    request<AnalyticsSummary>("GET", `/admin/analytics/summary${query({ days })}`, undefined, signal),
  /** Owner: CSV of the usage events (a plain link: GET with the sign-in cookie). Dates are Vietnam days. */
  analyticsCsvUrl: (since: string, until: string) => `${BASE}/admin/analytics/export.csv${query({ since, until })}`,
};

/**
 * GET /api/account/export as a file: the JSON body and the server's file name
 * ("lyris-<handle>-<date>.json"). Errors as ApiError, like every request.
 */
export async function downloadAccountData(): Promise<{ blob: Blob; filename: string }> {
  let res: Response;
  try {
    res = await fetch(`${BASE}/account/export`, { credentials: CREDENTIALS, headers: { ...CSRF_HEADER } });
  } catch {
    throw new ApiError(0, NETWORK_ERROR, NETWORK_TECHNICAL);
  }
  if (!res.ok) throw await errorFromResponse(res, "/account/export");
  const blob = await res.blob();
  return { blob, filename: filenameOf(res.headers.get("Content-Disposition")) ?? "lyris-du-lieu.json" };
}

/** The file name of a `Content-Disposition: attachment; filename="…"` header, or null. */
export function filenameOf(disposition: string | null): string | null {
  if (!disposition) return null;
  const m = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(disposition);
  if (!m || !m[1]) return null;
  let name: string;
  try {
    name = decodeURIComponent(m[1].trim());
  } catch {
    name = m[1].trim();
  }
  // Only a plain file name (no path).
  const base = name.split(/[\\/]/).pop() ?? "";
  return base && base !== "." && base !== ".." ? base : null;
}

// ---- SSE over fetch POST ----

const EVENT_NAMES = new Set<string>(["user_message", "waiting", "start", "delta", "done", "error"]);

function toChatEvent(name: string, data: string): ChatStreamEvent | null {
  if (!EVENT_NAMES.has(name)) return null;
  let parsed: unknown;
  try {
    parsed = JSON.parse(data);
  } catch {
    return null;
  }
  if (!parsed || typeof parsed !== "object") return null;
  return { name, data: parsed } as ChatStreamEvent;
}

/**
 * POSTs to an SSE endpoint and calls onEvent for each chat event, in order.
 * Resolves when the stream ends; rejects with ApiError for non-2xx responses
 * (404/409/422 come back as plain JSON before any streaming), or with an
 * AbortError when the signal fires.
 */
export async function streamChat(
  path: string,
  body: unknown,
  onEvent: (ev: ChatStreamEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  let res: Response;
  try {
    res = await fetch(BASE + path, {
      method: "POST",
      credentials: CREDENTIALS,
      headers: {
        ...CSRF_HEADER,
        Accept: "text/event-stream",
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (e) {
    if (isAbortError(e)) throw e;
    throw new ApiError(0, NETWORK_ERROR, NETWORK_TECHNICAL);
  }
  if (!res.ok) throw await errorFromResponse(res, path);
  if (!res.body) throw new ApiError(res.status, "Trình duyệt không đọc được luồng trả lời.");

  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");
  const parser = new SSEParser();
  const emit = (msgs: ReturnType<SSEParser["feed"]>) => {
    for (const m of msgs) {
      const ev = toChatEvent(m.event, m.data);
      if (ev) onEvent(ev);
    }
  };

  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      emit(parser.feed(decoder.decode(value, { stream: true })));
    }
    emit(parser.feed(decoder.decode()));
    emit(parser.flush());
  } catch (e) {
    if (isAbortError(e) || signal.aborted) {
      throw new DOMException("Aborted", "AbortError");
    }
    throw new ApiError(0, "Mất kết nối giữa chừng khi đang nhận câu trả lời.");
  } finally {
    try {
      reader.releaseLock();
    } catch {
      // already released
    }
  }
}

export const streams = {
  send: (storyId: number, content: string, onEvent: (ev: ChatStreamEvent) => void, signal: AbortSignal) =>
    streamChat(`/stories/${storyId}/messages`, { content }, onEvent, signal),
  reply: (storyId: number, onEvent: (ev: ChatStreamEvent) => void, signal: AbortSignal) =>
    streamChat(`/stories/${storyId}/reply`, undefined, onEvent, signal),
  regenerate: (messageId: number, onEvent: (ev: ChatStreamEvent) => void, signal: AbortSignal) =>
    streamChat(`/messages/${messageId}/regenerate`, undefined, onEvent, signal),
};

/** "Chat thử" in the Studio: streams one reply for an unsaved card; nothing is stored. */
export function streamTestChat(
  body: TestChatRequest,
  onEvent: (ev: TestChatEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  // Same wire format as chat streams: start / delta / done / error.
  return streamChat("/cards/test-chat", body, (ev) => onEvent(ev as unknown as TestChatEvent), signal);
}
