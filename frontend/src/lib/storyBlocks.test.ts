import { test } from "node:test";
import assert from "node:assert/strict";
import {
  blockText,
  buildStoryBlocks,
  curlyQuote,
  dmOnlyHiddenThought,
  onlyHiddenThoughts,
  paragraphBlocks,
  quoteWordCount,
  speechText,
  visibleBlocks,
} from "./storyBlocks.ts";
import type { StoryBlock } from "./storyBlocks.ts";
import { splitSegments } from "./text.ts";

/** Compact view of blocks: ["n", text] / ["d", text] / ["t", text]. */
function view(blocks: StoryBlock[]): [string, string][] {
  return blocks.map((b) => [b.kind[0] as string, blockText(b)]);
}

test("quoteWordCount ignores the marks and lone punctuation", () => {
  assert.equal(quoteWordCount("“Em đến rồi à?”"), 4);
  assert.equal(quoteWordCount("“Hạ Vy”"), 2);
  assert.equal(quoteWordCount('"Thật — sao?"'), 2);
  assert.equal(quoteWordCount("“Anh đang"), 2);
  assert.equal(quoteWordCount("「」"), 0);
});

test("curlyQuote turns straight quotes curly and keeps the others", () => {
  assert.equal(curlyQuote('"Em về rồi đây."'), "“Em về rồi đây.”");
  assert.equal(curlyQuote('"Em về'), "“Em về");
  assert.equal(curlyQuote("«Bonjour à tous»"), "«Bonjour à tous»");
  assert.equal(curlyQuote("“Đã lâu không gặp.”"), "“Đã lâu không gặp.”");
});

test("narration paragraph stays one narration block", () => {
  const blocks = paragraphBlocks("Cô đặt chồng sách xuống quầy, phủi bụi trên tay.");
  assert.deepEqual(blocks, [
    { kind: "narration", parts: [{ kind: "plain", text: "Cô đặt chồng sách xuống quầy, phủi bụi trên tay." }] },
  ]);
});

test("speech of 3+ words becomes a dialogue card with text before and after as narration", () => {
  const blocks = paragraphBlocks("Cô ngẩng lên, mỉm cười. “Hôm nay anh đến sớm thế?” Giọng cô nhẹ như gió.");
  assert.deepEqual(view(blocks), [
    ["n", "Cô ngẩng lên, mỉm cười."],
    ["d", "“Hôm nay anh đến sớm thế?”"],
    ["n", "Giọng cô nhẹ như gió."],
  ]);
});

test("short quotes stay inline, upright, with their marks", () => {
  const blocks = paragraphBlocks("Trên bìa sách có hai chữ “Mùa thu” mờ nhạt.");
  assert.equal(blocks.length, 1);
  const b = blocks[0];
  assert.ok(b && b.kind === "narration");
  assert.deepEqual(b.parts, [
    { kind: "plain", text: "Trên bìa sách có hai chữ " },
    { kind: "quote", text: "“Mùa thu”" },
    { kind: "plain", text: " mờ nhạt." },
  ]);
});

test("a paragraph that is only a short quote is still a card", () => {
  assert.deepEqual(view(paragraphBlocks("“Ừ.”")), [["d", "“Ừ.”"]]);
  assert.deepEqual(view(paragraphBlocks("  “Ừm…” ")), [["d", "“Ừm…”"]]);
});

test("punctuation left between two cards is dropped", () => {
  const blocks = paragraphBlocks("“Anh nói thật đấy chứ,” “em không tin nổi đâu.”");
  assert.deepEqual(view(blocks), [
    ["d", "“Anh nói thật đấy chứ,”"],
    ["d", "“em không tin nổi đâu.”"],
  ]);
  assert.deepEqual(view(paragraphBlocks("“Em đến rồi à,” cô nói. “Vào đi, ngoài trời lạnh lắm.”.")), [
    ["d", "“Em đến rồi à,”"],
    ["n", "cô nói."],
    ["d", "“Vào đi, ngoài trời lạnh lắm.”"],
  ]);
});

test("*actions* render as narration without the asterisks", () => {
  const blocks = paragraphBlocks("*Khẽ kéo ghế ra* “Ngồi xuống đây với em đi.”");
  assert.deepEqual(blocks, [
    { kind: "narration", parts: [{ kind: "action", text: "Khẽ kéo ghế ra" }] },
    { kind: "dialogue", text: "“Ngồi xuống đây với em đi.”" },
  ]);
});

test("straight quotes become curly in the card", () => {
  assert.deepEqual(view(paragraphBlocks('Anh cười. "Em lo xa quá rồi."')), [
    ["n", "Anh cười."],
    ["d", "“Em lo xa quá rồi.”"],
  ]);
});

test("thoughts keep their position between paragraphs", () => {
  const raw = [
    "Cô rót trà, hơi nóng bốc lên mờ cả kính.",
    "[Thought: Anh ấy lại đến. Mình có nên nói không?]",
    "“Trà gừng đấy, anh uống cho ấm người.”",
    "[Thought: Đừng để anh ấy thấy tay mình đang run.]",
  ].join("\n");
  assert.deepEqual(view(buildStoryBlocks(splitSegments(raw))), [
    ["n", "Cô rót trà, hơi nóng bốc lên mờ cả kính."],
    ["t", "Anh ấy lại đến. Mình có nên nói không?"],
    ["d", "“Trà gừng đấy, anh uống cho ấm người.”"],
    ["t", "Đừng để anh ấy thấy tay mình đang run."],
  ]);
});

test("each non-empty line is its own paragraph; a multi-line thought stays one card", () => {
  const blocks = buildStoryBlocks([
    { kind: "text", text: "Dòng một.\n\n  \nDòng hai." },
    { kind: "thought", text: "Ý một.\nÝ hai." },
  ]);
  assert.deepEqual(view(blocks), [
    ["n", "Dòng một."],
    ["n", "Dòng hai."],
    ["t", "Ý một.\n\nÝ hai."],
  ]);
});

test("an unclosed quote while streaming becomes a card once it has 3 words", () => {
  assert.deepEqual(view(paragraphBlocks("Cô quay lại. “Anh")), [["n", "Cô quay lại. “Anh"]]);
  assert.deepEqual(view(paragraphBlocks("Cô quay lại. “Anh đừng đi")), [
    ["n", "Cô quay lại."],
    ["d", "“Anh đừng đi"],
  ]);
});

test("empty input gives no blocks", () => {
  assert.deepEqual(buildStoryBlocks([]), []);
  assert.deepEqual(buildStoryBlocks([{ kind: "text", text: "  \n " }]), []);
  assert.deepEqual(paragraphBlocks(" . , "), []);
});

test("speechText drops only the outer quote marks of a dialogue card", () => {
  assert.equal(speechText("“Cậu đến rồi à?”"), "Cậu đến rồi à?");
  assert.equal(speechText('"Đi thôi nào."'), "Đi thôi nào.");
  assert.equal(speechText("« Bonjour, mon ami »"), "Bonjour, mon ami");
  assert.equal(speechText("“Đang gõ dở"), "Đang gõ dở");
  assert.equal(speechText("“Cô ấy nói “không” với tớ.”"), "Cô ấy nói “không” với tớ.");
});

// ---- Phase 4 (B): "Đọc suy nghĩ của nhân vật" off ----

test("visibleBlocks: thoughts are dropped only when reading thoughts is off", () => {
  const blocks = buildStoryBlocks(
    splitSegments('Cô đặt tách trà xuống.\n[Thought: Anh ấy lại đến muộn.]\n"Anh ngồi đi, trà còn nóng."'),
  );
  assert.deepEqual(view(visibleBlocks(blocks, true)), view(blocks));
  assert.deepEqual(view(visibleBlocks(blocks, false)), [
    ["n", "Cô đặt tách trà xuống."],
    ["d", "“Anh ngồi đi, trà còn nóng.”"],
  ]);
});

test("visibleBlocks: while a hidden thought streams at the end, the last shown block takes the caret", () => {
  // thought_style "end": the reply is still writing its closing thought.
  const streaming = [
    { kind: "text" as const, text: '"Mai gặp lại nhé, đừng quên ô."' },
    { kind: "thought" as const, text: "Mình đã muốn nói thêm" },
  ];
  const shown = visibleBlocks(buildStoryBlocks(streaming), false);
  assert.equal(shown.length, 1);
  assert.equal(shown[shown.length - 1]?.kind, "dialogue");
  // A thought in the middle: the caret block is the text after it.
  const middle = visibleBlocks(
    buildStoryBlocks([
      { kind: "text", text: "Mưa rơi." },
      { kind: "thought", text: "Lạnh quá." },
      { kind: "text", text: "Cô kéo cao cổ áo" },
    ]),
    false,
  );
  assert.deepEqual(view(middle), [
    ["n", "Mưa rơi."],
    ["n", "Cô kéo cao cổ áo"],
  ]);
});

test("visibleBlocks / onlyHiddenThoughts: a turn of only a thought shows nothing", () => {
  const blocks = buildStoryBlocks(splitSegments("[Thought: Chỉ là một suy nghĩ.]"));
  assert.deepEqual(visibleBlocks(blocks, false), []);
  assert.equal(onlyHiddenThoughts(blocks, false), true);
  assert.equal(onlyHiddenThoughts(blocks, true), false);
  assert.equal(onlyHiddenThoughts([], false), false);
  assert.equal(onlyHiddenThoughts(buildStoryBlocks(splitSegments("Cô cười.")), false), false);
});

test("dmOnlyHiddenThought: DM reply with only a hidden thought gets the note, not an empty bubble", () => {
  assert.equal(dmOnlyHiddenThought(0, "Mình nhớ cậu.", false), true);
  assert.equal(dmOnlyHiddenThought(0, "Mình nhớ cậu.", true), false);
  assert.equal(dmOnlyHiddenThought(1, "Mình nhớ cậu.", false), false);
  assert.equal(dmOnlyHiddenThought(0, "  ", false), false);
  assert.equal(dmOnlyHiddenThought(0, null, false), false);
});
