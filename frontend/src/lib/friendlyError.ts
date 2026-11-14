// Errors in plain words (phase3.md §10, Phase 3b): the player never reads "Ollama", "model", HTTP
// codes or stack traces. The technical text stays available under a small "Chi tiết" disclosure.
// Pure, no React; tested in friendlyError.test.ts.

export interface FriendlyError {
  /** What the player reads: one or two plain sentences. */
  text: string;
  /** The original technical text for "Chi tiết"; null when there is nothing more to say. */
  technical: string | null;
}

/** Words that mark a message as technical (it is then rephrased; the original goes to "Chi tiết"). */
const TECHNICAL =
  /ollama|\bmodel\b|\bHTTP\b|num_ctx|token|\bKV\b|traceback|exception|sqlite|database|localhost|127\.0\.0\.1|\bapi\b|`|scripts\/|\bjson\b|embedding|backend|uvicorn|errno|timeout/i;

/** Ordered rules: the first that matches the raw text gives the plain sentence. */
const RULES: { test: RegExp; text: string }[] = [
  {
    // The Lyris server itself cannot be reached (client.ts NETWORK_ERROR and friends).
    test: /máy chủ lyris|backend lyris|scripts\/dev\.sh/i,
    text: "Không kết nối được Lyris trên máy này. Hãy thử lại sau giây lát.",
  },
  {
    test: /quá lâu|timed? ?out|timeout|hết thời gian/i,
    text: "Lyris phản hồi lâu quá. Hãy thử lại sau giây lát.",
  },
  {
    test: /chưa có model|không có model|thiếu model|ollama pull|not found.*model|model.*not found/i,
    text: "Máy chưa sẵn sàng để trả lời. Xem mục Nâng cao trong Tài khoản.",
  },
  {
    test: /không kết nối được ollama|ollama không chạy|mất kết nối|connection|connect|đóng kết nối/i,
    text: "Lyris chưa kết nối được phần trả lời trên máy. Hãy thử lại sau giây lát.",
  },
  {
    test: /không trả về nội dung|trả về rỗng|empty/i,
    text: "Nhân vật chưa nói được gì. Hãy thử lại.",
  },
  {
    test: /không lưu được|database is locked|sqlite/i,
    text: "Chưa lưu được lượt này. Hãy thử lại.",
  },
];

const FALLBACK = "Có lỗi xảy ra. Hãy thử lại.";

/** True when the text uses words the player should not have to read. */
export function looksTechnical(text: string): boolean {
  return TECHNICAL.test(text);
}

/**
 * A message for the player. `raw` is what the server or the client said; `technical` is extra
 * detail the server sent separately (`{detail, technical}`), if any.
 *
 * - Plain text stays as it is (validation messages, "Không tìm thấy story."), with the server's
 *   technical detail, if any, under "Chi tiết".
 * - Technical text is rephrased by the first matching rule (or a general sentence); the original
 *   goes to "Chi tiết" (after the server's detail, when both exist and differ).
 */
export function friendlyError(raw: string | null | undefined, technical?: string | null): FriendlyError {
  const text = (raw ?? "").replace(/\s+/g, " ").trim();
  const extra = (technical ?? "").trim() || null;
  if (!text) return { text: FALLBACK, technical: extra };
  if (!looksTechnical(text)) return { text, technical: extra && extra !== text ? extra : null };
  const rule = RULES.find((r) => r.test.test(text));
  const details = [extra, text].filter((s, i, all): s is string => !!s && all.indexOf(s) === i);
  return { text: rule ? rule.text : FALLBACK, technical: details.join("\n") || null };
}
