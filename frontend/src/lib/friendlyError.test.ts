import { test } from "node:test";
import assert from "node:assert/strict";
import { friendlyError, looksTechnical } from "./friendlyError.ts";

test("plain messages stay as they are", () => {
  assert.deepEqual(friendlyError("Không tìm thấy story."), { text: "Không tìm thấy story.", technical: null });
  assert.deepEqual(friendlyError("Dữ liệu không hợp lệ: handle: String should have at least 3 characters").technical, null);
  // The server's own technical detail still goes under "Chi tiết".
  assert.deepEqual(friendlyError("Nhân vật đang bận trả lời.", "409: stream active"), {
    text: "Nhân vật đang bận trả lời.",
    technical: "409: stream active",
  });
});

test("connection and timeout errors are rephrased, the original kept", () => {
  const raw = "Không kết nối được Ollama ở http://localhost:11434. Hãy mở app Ollama (hoặc chạy `ollama serve`) rồi thử lại.";
  const e = friendlyError(raw);
  assert.equal(e.text, "Lyris chưa kết nối được phần trả lời. Hãy thử lại sau giây lát.");
  assert.equal(e.technical, raw);
  assert.doesNotMatch(e.text, /ollama|model/i);
  assert.equal(friendlyError("Ollama phản hồi quá lâu (quá 300 giây). Máy có thể đang thiếu RAM").text, "Lyris phản hồi lâu quá. Hãy thử lại sau giây lát.");
  assert.equal(friendlyError("Mất kết nối với Ollama ở http://x giữa chừng (ReadError). Hãy thử lại.").text, "Lyris chưa kết nối được phần trả lời. Hãy thử lại sau giây lát.");
});

test("missing model, empty reply, save failure, unknown", () => {
  assert.match(friendlyError("Ollama chưa có model gemma4:12b. Hãy tải về bằng lệnh: ollama pull gemma4:12b").text, /chưa sẵn sàng/);
  assert.equal(friendlyError("Model không trả về nội dung nào. Hãy bấm Thử lại.").text, "Nhân vật chưa nói được gì. Hãy thử lại.");
  assert.equal(friendlyError("Không lưu được câu trả lời: database is locked").text, "Chưa lưu được lượt này. Hãy thử lại.");
  assert.equal(friendlyError("Máy chủ báo lỗi (HTTP 500).").text, "Có lỗi xảy ra. Hãy thử lại.");
  assert.equal(friendlyError("").text, "Có lỗi xảy ra. Hãy thử lại.");
  assert.equal(friendlyError(null, "boom").technical, "boom");
});

test("server detail plus technical: both kept once, server's first", () => {
  const e = friendlyError("Ollama báo lỗi (HTTP 500): out of memory", "trace id 7");
  assert.equal(e.technical, "trace id 7\nOllama báo lỗi (HTTP 500): out of memory");
  assert.equal(friendlyError("Ollama báo lỗi", "Ollama báo lỗi").technical, "Ollama báo lỗi");
});

test("looksTechnical", () => {
  assert.equal(looksTechnical("Ollama chưa chạy"), true);
  assert.equal(looksTechnical("Chạy `ollama pull bge-m3`"), true);
  assert.equal(looksTechnical("Story này không còn."), false);
  // Vietnamese words that merely contain the letters do not count.
  assert.equal(looksTechnical("Mô hình tính cách dịu dàng"), false);
});

test("the server's plain Phase 3b messages pass through unchanged", () => {
  // backend/lyris/llm/errors.py (_BY_KIND, _MISSING_MODEL, _FALLBACK, EMPTY_*, SAVE_FAILED, UNEXPECTED) and
  // lyris/chat/service.py (BUSY_DETAIL, SUGGEST_BUSY_DETAIL, NO_REPLY_TO_SUGGEST): the client must not
  // rephrase them again (they would turn into a vaguer sentence).
  const server = [
    "Chưa kết nối được với phần AI của Lyris. Hãy thử lại sau ít phút.",
    "Máy đang bận nên phản hồi quá lâu. Hãy thử lại sau ít phút.",
    "Bộ AI mà story này dùng chưa có trên máy. Hãy chọn bộ khác trong Thiết lập story > Nâng cao.",
    "Bộ AI dùng để viết nháp chưa có trên máy. Xem các bộ đang có trong Tài khoản > Nâng cao.",
    "Bộ AI dùng để chat thử chưa có trên máy. Xem các bộ đang có trong Tài khoản > Nâng cao.",
    "Nhân vật chưa trả lời được. Hãy thử lại.",
    "Chưa nghĩ ra được gợi ý. Hãy thử lại.",
    "Chưa viết nháp được nhân vật. Hãy thử lại.",
    "Nhân vật chưa trả lời được. Hãy bấm Làm lại.",
    "Nhân vật chưa nói được gì. Hãy bấm Thử lại.",
    "Nhân vật chưa nói được gì. Hãy bấm Làm lại.",
    "Không lưu được câu trả lời. Hãy thử lại.",
    "Có lỗi không mong đợi. Hãy thử lại.",
    "Nhân vật đang trả lời trong story này. Hãy đợi xong hoặc bấm Dừng rồi thử lại.",
    "Đang nghĩ gợi ý cho bạn. Đợi một chút rồi thử lại nhé.",
    "Chỉ nhận gợi ý được khi nhân vật vừa trả lời xong và bạn chưa viết tiếp.",
    // Phase 4: lyris/lore/service.py (LoreInputError, LoreLimitError, NO_ENTRIES_DETAIL, NO_BOOK_DETAIL).
    "Mục thế giới cần có tên.",
    "Tên mục thế giới dài tối đa 120 ký tự.",
    "Mỗi từ khoá dài tối đa 80 ký tự.",
    "Mỗi mục có tối đa 32 từ khoá.",
    "Cần chọn ai biết điều này.",
    "Mỗi mục có tối đa 8 người biết.",
    "Nội dung dài tối đa 4000 ký tự.",
    "File quá lớn (tối đa 500 KB).",
    "Không tìm thấy mục thế giới nào. File cần có phần “## Mục lore”, “## Nhân vật xung quanh” hoặc “## Địa điểm”.",
    "Nhân vật này không có sổ thế giới đi kèm để dùng.",
    "Mỗi nhân vật có tối đa 500 mục thế giới.",
  ];
  const technical = "Không kết nối được Ollama ở http://127.0.0.1:11434. Hãy mở app Ollama (hoặc chạy `ollama serve`) rồi thử lại.";
  for (const detail of server) {
    assert.equal(looksTechnical(detail), false, detail);
    assert.deepEqual(friendlyError(detail, technical), { text: detail, technical });
  }
});
