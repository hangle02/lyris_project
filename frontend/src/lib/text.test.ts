import { test } from "node:test";
import assert from "node:assert/strict";
import { appendSegment, extractDirectives, joinSegments, parseInline, splitParagraphs, splitSegments } from "./text.ts";

test("extractDirectives removes ((...)) and joins them", () => {
  assert.deepEqual(extractDirectives("*Tớ cười* ((Lạc Dương ghen)) Chào cậu ((trời mưa))"), {
    visible: "*Tớ cười* Chào cậu",
    directive: "Lạc Dương ghen; trời mưa",
  });
  assert.deepEqual(extractDirectives("((chỉ\nđạo))"), { visible: "", directive: "chỉ đạo" });
  assert.deepEqual(extractDirectives("Không có chỉ đạo"), { visible: "Không có chỉ đạo", directive: null });
});

test("extractDirectives leaves emoticons alone", () => {
  assert.deepEqual(extractDirectives("Hic :(( cậu không đến thật à?"), {
    visible: "Hic :(( cậu không đến thật à?",
    directive: null,
  });
  assert.deepEqual(extractDirectives("Tớ buồn quá :(( Cậu đi đâu vậy :))"), {
    visible: "Tớ buồn quá :(( Cậu đi đâu vậy :))",
    directive: null,
  });
  assert.deepEqual(extractDirectives("Haha =)) ((cho anh ấy cười))"), { visible: "Haha =))", directive: "cho anh ấy cười" });
  assert.deepEqual(extractDirectives("Đi thôi. ((cho trời đổ mưa"), { visible: "Đi thôi.", directive: "cho trời đổ mưa" });
  assert.deepEqual(extractDirectives("Buồn ghê (("), { visible: "Buồn ghê ((", directive: null });
});

test("splitParagraphs keeps non-empty lines", () => {
  assert.deepEqual(splitParagraphs("Một.\n\n\nHai.\r\n  Ba.  \n"), ["Một.", "Hai.", "Ba."]);
});

test("parseInline marks dialogue and actions", () => {
  assert.deepEqual(parseInline("Anh nói: “Đi thôi.” rồi *quay đi*."), [
    { kind: "plain", text: "Anh nói: " },
    { kind: "quote", text: "“Đi thôi.”" },
    { kind: "plain", text: " rồi " },
    { kind: "action", text: "quay đi" },
    { kind: "plain", text: "." },
  ]);
  assert.deepEqual(parseInline('"Vãn Vãn'), [{ kind: "quote", text: '"Vãn Vãn' }]);
  assert.deepEqual(parseInline("2 * 3"), [{ kind: "plain", text: "2 * 3" }]);
});

test("splitSegments keeps thoughts in place", () => {
  const raw = 'Anh khựng lại.\n\n[Thought: Cô ấy lại thức khuya.]\n\n"Ngủ đi."\n[ thought : Ngốc thật ]';
  assert.deepEqual(splitSegments(raw), [
    { kind: "text", text: "Anh khựng lại." },
    { kind: "thought", text: "Cô ấy lại thức khuya." },
    { kind: "text", text: '"Ngủ đi."' },
    { kind: "thought", text: "Ngốc thật" },
  ]);
});

test("splitSegments handles unclosed and empty thoughts, plain brackets", () => {
  assert.deepEqual(splitSegments("Chào [Thought: chưa xong"), [
    { kind: "text", text: "Chào" },
    { kind: "thought", text: "chưa xong" },
  ]);
  assert.deepEqual(splitSegments("[Thought: ] [ghi chú] hết"), [{ kind: "text", text: "[ghi chú] hết" }]);
  assert.deepEqual(splitSegments(""), []);
});

test("appendSegment and joinSegments round-trip", () => {
  let segs = appendSegment([], "text", "Anh ");
  segs = appendSegment(segs, "text", "cười.");
  segs = appendSegment(segs, "thought", "Vui.");
  assert.deepEqual(segs, [
    { kind: "text", text: "Anh cười." },
    { kind: "thought", text: "Vui." },
  ]);
  assert.deepEqual(splitSegments(joinSegments(segs)), segs);
});

test("splitSegments: an empty thought does not split the text around it", () => {
  assert.deepEqual(splitSegments("Cô bước vào [Thought: ] rồi ngồi xuống."), [
    { kind: "text", text: "Cô bước vào  rồi ngồi xuống." },
  ]);
});

test("splitSegments: closed thoughts still run to the first ]", () => {
  assert.deepEqual(splitSegments('Anh cười. [Thought: Dòng một.\nDòng hai."] Hết.'), [
    { kind: "text", text: "Anh cười." },
    { kind: "thought", text: 'Dòng một.\nDòng hai."' },
    { kind: "text", text: "Hết." },
  ]);
});

test("splitSegments: an unclosed thought ends at a blank line (gemma example)", () => {
  const raw =
    'Hắn cười.\n\n[Thought: Người đẹp nào? Tôi chỉ đang trêu cậu thôi, Đậu Đinh."\n\nCố Hoài Dã vươn tay.\n\n"Sao?"';
  assert.deepEqual(splitSegments(raw), [
    { kind: "text", text: "Hắn cười." },
    { kind: "thought", text: "Người đẹp nào? Tôi chỉ đang trêu cậu thôi, Đậu Đinh." },
    { kind: "text", text: 'Cố Hoài Dã vươn tay.\n\n"Sao?"' },
  ]);
  // A blank line with spaces/tabs also ends it; a "]" after the break is story text.
  assert.deepEqual(splitSegments("Mở. [Thought: giận rồi \t\n \t\nAnh bước tới.] Hết."), [
    { kind: "text", text: "Mở." },
    { kind: "thought", text: "giận rồi" },
    { kind: "text", text: "Anh bước tới.] Hết." },
  ]);
});

test("splitSegments: unclosed thought at the end drops one unmatched trailing quote", () => {
  assert.deepEqual(splitSegments('Chào [Thought: Ngốc thật."  '), [
    { kind: "text", text: "Chào" },
    { kind: "thought", text: "Ngốc thật." },
  ]);
  assert.deepEqual(splitSegments("[Thought: đi mất ” "), [{ kind: "thought", text: "đi mất" }]);
  assert.deepEqual(splitSegments("[Thought: đi mất “"), [{ kind: "thought", text: "đi mất" }]);
  assert.deepEqual(splitSegments('[Thought: a "" "\n\nb'), [
    { kind: "thought", text: 'a ""' },
    { kind: "text", text: "b" },
  ]);
  // Matched quotes stay.
  assert.deepEqual(splitSegments('[Thought: Cô ấy nói "đi thôi"'), [{ kind: "thought", text: 'Cô ấy nói "đi thôi"' }]);
  assert.deepEqual(splitSegments("[Thought: bảo “đợi”"), [{ kind: "thought", text: "bảo “đợi”" }]);
  assert.deepEqual(splitSegments('[Thought: "'), []);
});

test("splitSegments: a single newline inside an unclosed thought does not end it", () => {
  assert.deepEqual(splitSegments("Anh nhìn. [Thought: Dòng một.\nDòng hai.\n\n\nCô quay lại."), [
    { kind: "text", text: "Anh nhìn." },
    { kind: "thought", text: "Dòng một.\nDòng hai." },
    { kind: "text", text: "Cô quay lại." },
  ]);
});

test("plainMessage turns backtick code spans into quotes", async () => {
  const { plainMessage } = await import("./text.ts");
  assert.equal(
    plainMessage("Hãy mở app Ollama (hoặc chạy `ollama serve`) rồi thử lại."),
    "Hãy mở app Ollama (hoặc chạy “ollama serve”) rồi thử lại.",
  );
  assert.equal(plainMessage("Không có mã"), "Không có mã");
  assert.equal(plainMessage("lẻ ` một dấu"), "lẻ ` một dấu");
});

test("spaceAfterHorn separates a quote from the horn of ơ/ư", async () => {
  const { spaceAfterHorn } = await import("./text.ts");
  assert.equal(spaceAfterHorn("là 'gia sư' của"), "là 'gia sư ' của");
  assert.equal(spaceAfterHorn("“Từ” và \"Ơ\""), "“Từ ” và \"Ơ \"");
  assert.equal(spaceAfterHorn("sự’ thật"), "sự ’ thật");
  assert.equal(spaceAfterHorn("'Không' sao"), "'Không' sao");
  assert.equal(spaceAfterHorn("sư tử"), "sư tử");
});

test("parseInline: a ” that opens a word pairs with the next ”; a lone ” stays text", () => {
  assert.deepEqual(parseInline("nói ”chào cậu” rồi đi"), [
    { kind: "plain", text: "nói " },
    { kind: "quote", text: "”chào cậu”" },
    { kind: "plain", text: " rồi đi" },
  ]);
  assert.deepEqual(parseInline("cậu ấy nói vậy” rồi đi"), [{ kind: "plain", text: "cậu ấy nói vậy” rồi đi" }]);
  assert.deepEqual(parseInline("dấu ” lẻ"), [{ kind: "plain", text: "dấu ” lẻ" }]);
});
