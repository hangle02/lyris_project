import { test } from "node:test";
import assert from "node:assert/strict";
import { playerStoryBlocks } from "./playerBlocks.ts";
import { blockText, speechText } from "./storyBlocks.ts";
import type { StoryBlock } from "./storyBlocks.ts";

/** Compact view: ["n", text] / ["d", text]. */
function view(blocks: StoryBlock[]): [string, string][] {
  return blocks.map((b) => [b.kind[0] as string, blockText(b)]);
}

test("empty and blank turns give no blocks", () => {
  assert.deepEqual(playerStoryBlocks(""), []);
  assert.deepEqual(playerStoryBlocks("  \n\n \t"), []);
});

test("straight and curly quotes become dialogue blocks (straight ones turn curly)", () => {
  assert.deepEqual(view(playerStoryBlocks('"Chào em, lâu rồi không gặp."')), [["d", "“Chào em, lâu rồi không gặp.”"]]);
  assert.deepEqual(view(playerStoryBlocks("“Anh về rồi đây.”")), [["d", "“Anh về rồi đây.”"]]);
});

test("an unclosed quote runs to the end of its line", () => {
  assert.deepEqual(view(playerStoryBlocks('Tôi gọi với theo. "Khoan đã, đợi tôi với')), [
    ["n", "Tôi gọi với theo."],
    ["d", "“Khoan đã, đợi tôi với"],
  ]);
});

test("*actions* become narration without the asterisks", () => {
  const blocks = playerStoryBlocks("*khẽ kéo ghế ngồi xuống cạnh cô*");
  assert.deepEqual(blocks, [{ kind: "narration", parts: [{ kind: "action", text: "khẽ kéo ghế ngồi xuống cạnh cô" }] }]);
  assert.doesNotMatch(blockText(blocks[0] as StoryBlock), /\*/);
});

test("mixed narration, action and speech keep their order and paragraphs", () => {
  const text = [
    "Tôi đẩy cửa bước vào tiệm sách, chuông gió khẽ reo.",
    "",
    '*Đặt túi bánh lên quầy* "Mình mang bánh hạt dẻ cho cậu này." Tôi cười.',
  ].join("\n");
  assert.deepEqual(view(playerStoryBlocks(text)), [
    ["n", "Tôi đẩy cửa bước vào tiệm sách, chuông gió khẽ reo."],
    ["n", "Đặt túi bánh lên quầy"],
    ["d", "“Mình mang bánh hạt dẻ cho cậu này.”"],
    ["n", "Tôi cười."],
  ]);
});

test("every quote the player writes is a card, however short", () => {
  assert.deepEqual(view(playerStoryBlocks("Tôi gật đầu “Ừ.” rồi quay đi")), [
    ["n", "Tôi gật đầu"],
    ["d", "“Ừ.”"],
    ["n", "rồi quay đi"],
  ]);
});

test("a quote inside asterisks is a citation: inline, upright, marks kept", () => {
  const blocks = playerStoryBlocks("Tôi đọc to hai chữ *“Mùa thu”* trên bìa sách.");
  assert.equal(blocks.length, 1);
  const b = blocks[0];
  assert.ok(b && b.kind === "narration");
  assert.deepEqual(
    b.parts.map((p) => p.kind),
    ["plain", "quote", "plain"],
  );
});

test("Vietnamese diacritics and emoji pass through untouched", () => {
  assert.deepEqual(view(playerStoryBlocks("“Ừ, mình nhớ cậu lắm đấy \u{1F97A}”")), [["d", "“Ừ, mình nhớ cậu lắm đấy \u{1F97A}”"]]);
  assert.deepEqual(view(playerStoryBlocks("Tôi gật đầu \u{1F60A} rồi ngồi xuống.")), [["n", "Tôi gật đầu \u{1F60A} rồi ngồi xuống."]]);
  assert.deepEqual(view(playerStoryBlocks("*ngượng ngùng gãi đầu* \u{1F648}")), [["n", "ngượng ngùng gãi đầu \u{1F648}"]]);
});

test("a lone asterisk stays literal text", () => {
  assert.deepEqual(view(playerStoryBlocks("Điểm 5* cho quán này")), [["n", "Điểm 5* cho quán này"]]);
});

test("a turn of only punctuation or emoji still shows its text", () => {
  for (const t of ["...", "…", "\u{1F633}", "?!"]) {
    assert.deepEqual(view(playerStoryBlocks(t)), [["n", t]], t);
  }
  // Wrapping asterisks are still removed.
  const dots = playerStoryBlocks("*...*");
  assert.equal(dots.length, 1);
  const b = dots[0];
  assert.ok(b && b.kind === "narration");
  assert.deepEqual(b.parts, [{ kind: "action", text: "..." }]);
  // A dropped paragraph keeps its place between the others.
  assert.deepEqual(view(playerStoryBlocks("Tôi im lặng.\n...\n“Ừ.”")), [
    ["n", "Tôi im lặng."],
    ["n", "..."],
    ["d", "“Ừ.”"],
  ]);
});

test("**bold** reads as an action, no stray asterisks", () => {
  const blocks = playerStoryBlocks("**ôm chặt** cậu ấy");
  assert.equal(blocks.length, 1);
  const b = blocks[0];
  assert.ok(b && b.kind === "narration");
  assert.equal(b.parts.map((p) => p.text).join(""), "ôm chặt cậu ấy");
  assert.equal(b.parts[0]?.kind, "action");
  assert.deepEqual(view(playerStoryBlocks("**ôm chặt**")), [["n", "ôm chặt"]]);
});

test("two lines of speech in one turn, the first opened with a phone keyboard's ”, are two cards", () => {
  const input =
    "Tôi nhìn bóng dáng nhỏ con đứng trước cửa, bình thản nói ”ồ vậy sao, cảm ơn cậu nhé cậu nhóc” rồi nhìn ra hành lang tối thui sau lưng cậu, tôi bèn hỏi “tôi mới chuyển đến cũng không quen lắm, khu này hay mất điện như vậy à?”";
  const blocks = playerStoryBlocks(input);
  const dialogue = blocks.filter((b) => b.kind === "dialogue").map((b) => speechText(blockText(b)));
  assert.deepEqual(dialogue, [
    "ồ vậy sao, cảm ơn cậu nhé cậu nhóc",
    "tôi mới chuyển đến cũng không quen lắm, khu này hay mất điện như vậy à?",
  ]);
  for (const b of blocks) if (b.kind === "narration") assert.ok(!/[“”"]/.test(blockText(b)), blockText(b));
});
test("*\"…\"*: another person's long words stay in the narration line, the player's own speech is a card", () => {
  const blocks = playerStoryBlocks(
    'Bảo vệ gọi với theo *"Cậu kia, khu này mười một giờ là khoá cổng rồi đấy nhé!"* tôi quay lại "Cháu biết rồi ạ."',
  );
  assert.deepEqual(blocks.map((b) => b.kind), ["narration", "dialogue"]);
  const n = blocks[0];
  assert.ok(n && n.kind === "narration");
  assert.deepEqual(n.parts.map((p) => p.kind), ["plain", "quote", "plain"]);
  assert.equal(n.parts[1]?.text, "“Cậu kia, khu này mười một giờ là khoá cổng rồi đấy nhé!”");
});
