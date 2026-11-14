import { test } from "node:test";
import assert from "node:assert/strict";
import {
  cleanSignatureLine,
  cleanSignatureLines,
  pickSignatureLines,
  readSignatureLines,
  SIGNATURE_MAX_CHARS,
  signatureLinesFor,
  signatureProblems,
  signatureText,
  withCleanSignatureLines,
  withSignatureText,
} from "./signatureLines.ts";

type PickInput = Parameters<typeof pickSignatureLines>[0];

const haVy: PickInput = {
  name: "Hạ Vy",
  language: "vi",
  example_dialogues: [
    '{{char}}: "Cuốn này bà ngoại mình thích nhất đó. Cậu đọc chậm thôi nha, đoạn cuối buồn lắm."',
    '{{char}}: "Hôm nay tiệm vắng, nên mình có nguyên buổi chiều để nghe cậu kể chuyện hen."',
    '{{char}}: "Có những câu mình không biết nói sao, nên mình gạch chân nó trong sách rồi đưa cậu đọc."',
  ].join("\n"),
  greeting: "Bốn giờ chiều, mưa phùn lại phủ xuống con dốc.",
};

test("cleanSignatureLine: drops wrapping quotes of any kind and extra spaces", () => {
  assert.equal(cleanSignatureLine("  “Ai đợi   cậu.”  "), "Ai đợi cậu.");
  assert.equal(cleanSignatureLine('"Tea first, questions dreckly."'), "Tea first, questions dreckly.");
  assert.equal(cleanSignatureLine("«Ngươi nóng vội»"), "Ngươi nóng vội");
  assert.equal(cleanSignatureLine("   "), "");
});

test("cleanSignatureLines: at most 3, no blanks or repeats, cut to 140 characters", () => {
  const long = "ầ".repeat(200);
  assert.deepEqual(cleanSignatureLines(["a b c", "", "  ", "A B C", 5, "d e f", "g h i", "j k l"]), ["a b c", "d e f", "g h i"]);
  const [cut] = cleanSignatureLines([long]);
  assert.equal(Array.from(cut ?? "").length, SIGNATURE_MAX_CHARS);
});

test("stored lines: read, edit as text, clean on save; other extensions kept", () => {
  const card = { extensions: { foo: 1, lyris: { template: "ha-vy", initial_relationship: { trust: 40 } } } };
  assert.deepEqual(readSignatureLines(card), []);
  assert.equal(signatureText(card), "");

  const edited = withSignatureText(card, "“Ai đợi cậu.”\n\n  Tớ tiện đường thôi.  \n");
  assert.equal(signatureText(edited), "“Ai đợi cậu.”\n\n  Tớ tiện đường thôi.  \n");
  assert.deepEqual(readSignatureLines(edited), ["Ai đợi cậu.", "Tớ tiện đường thôi."]);
  const lyris = (edited.extensions as { lyris: Record<string, unknown> }).lyris;
  assert.equal(lyris.template, "ha-vy");
  assert.deepEqual(lyris.initial_relationship, { trust: 40 });
  assert.equal((edited.extensions as { foo: number }).foo, 1);

  const saved = withCleanSignatureLines(edited);
  assert.deepEqual((saved.extensions as { lyris: Record<string, unknown> }).lyris.signature_lines, [
    "Ai đợi cậu.",
    "Tớ tiện đường thôi.",
  ]);

  const cleared = withSignatureText(edited, "  \n ");
  assert.equal("signature_lines" in (cleared.extensions as { lyris: object }).lyris, false);
  assert.equal(withCleanSignatureLines(card), card);
});

test("signatureProblems: more than 3 lines or a line over 140 characters blocks saving", () => {
  assert.deepEqual(signatureProblems(withSignatureText({ extensions: {} }, "một\nhai\nba")), []);
  assert.deepEqual(signatureProblems(withSignatureText({ extensions: {} }, "một\nhai\nba\nbốn")), [
    "Tối đa 3 lời nói đặc trưng.",
  ]);
  const long = withSignatureText({ extensions: {} }, `ngắn\n${"ơ".repeat(141)}`);
  assert.deepEqual(signatureProblems(long), ["Lời nói đặc trưng số 2 dài quá 140 ký tự."]);
  // Wrapping quotes do not count.
  assert.deepEqual(signatureProblems(withSignatureText({ extensions: {} }, `“${"ơ".repeat(140)}”`)), []);
});

test("pickSignatureLines: spoken lines of the example dialogues, quotes and labels removed", () => {
  assert.deepEqual(pickSignatureLines(haVy), [
    "Cuốn này bà ngoại mình thích nhất đó. Cậu đọc chậm thôi nha, đoạn cuối buồn lắm.",
    "Hôm nay tiệm vắng, nên mình có nguyên buổi chiều để nghe cậu kể chuyện hen.",
    "Có những câu mình không biết nói sao, nên mình gạch chân nó trong sách rồi đưa cậu đọc.",
  ]);
});

test("pickSignatureLines: skips the player's lines and Thought, fills placeholders for the reader", () => {
  const card: PickInput = {
    name: "Lạc Dương",
    language: "vi",
    example_dialogues: [
      "<START>",
      "{{user}}: “Cậu đợi tớ à?”",
      "{{char}}: *nhún vai* “Ai đợi cậu. Tớ tiện đường thôi mà, {{user}}.” [Thought: Đợi cả tiếng rồi.]",
      "Lạc Dương: “Ăn xong rồi hẵng ôn tiếp. Đề cương có chạy mất đâu.”",
      "<START>",
      "User: \"Hôm nay cậu lạ quá.\"",
      "{{char}}: Không phải tiện đường. Tớ cố ý đợi cậu. *quay mặt đi*",
    ].join("\n"),
    greeting: "",
  };
  assert.deepEqual(pickSignatureLines(card), [
    "Ai đợi cậu. Tớ tiện đường thôi mà, bạn.",
    "Ăn xong rồi hẵng ôn tiếp. Đề cương có chạy mất đâu.",
    "Không phải tiện đường. Tớ cố ý đợi cậu.",
  ]);
});

test("pickSignatureLines: prefers distinct, mid-length lines and keeps the card's order", () => {
  const card: PickInput = {
    name: "Tạ Vân Lan",
    language: "vi",
    example_dialogues: [
      '{{char}}: "Ừ."',
      '{{char}}: "Kiếm theo ý, ý theo khí. Ngươi nóng vội nên kiếm mới loạn; luyện lại từ thức thứ nhất."',
      '{{char}}: "Vết thương này, ai làm? Nói tên ra."',
      '{{char}}: "Vết thương này, ai làm?  Nói tên ra!"',
      '{{char}}: "Trưởng lão có hỏi thì cứ nói ta phạt ngươi quét Tàng Kinh Các."',
      `{{char}}: "${"Rất dài ".repeat(30)}"`,
      '{{char}}: "Đứng lên, luyện tiếp đi."',
    ].join("\n"),
    greeting: "",
  };
  const lines = pickSignatureLines(card);
  assert.equal(lines.length, 3);
  assert.deepEqual(lines, [
    "Kiếm theo ý, ý theo khí. Ngươi nóng vội nên kiếm mới loạn; luyện lại từ thức thứ nhất.",
    "Vết thương này, ai làm? Nói tên ra.",
    "Trưởng lão có hỏi thì cứ nói ta phạt ngươi quét Tàng Kinh Các.",
  ]);
  assert.equal(pickSignatureLines(card, 1).length, 1);
});

test("pickSignatureLines: greeting quotes only when the character speaks them", () => {
  const card: PickInput = {
    name: "Lạc Dương",
    language: "vi",
    example_dialogues: "",
    greeting: [
      "Nắng chiều cuối thu xuyên qua ô cửa kính.",
      "[Thought: Lại thức khuya ôn bài rồi. “Đồ ngốc này.”]",
      "Một nữ sinh khóa dưới rụt rè đi tới: “Học trưởng, có thể cho em xin WeChat không ạ?”",
      "Lạc Dương không ngẩng đầu, giọng nhạt như nước: “Không tiện. Bạn gái tôi đang ngủ.”",
      "Anh cúi xuống sát tai {{user}}.",
      '"Dậy đi, thư viện sắp đóng cửa rồi, {{user}}."',
    ].join("\n\n"),
  };
  assert.deepEqual(pickSignatureLines(card), [
    "Không tiện. Bạn gái tôi đang ngủ.",
    "Dậy đi, thư viện sắp đóng cửa rồi, bạn.",
  ]);
});

test("pickSignatureLines: examples first, the greeting fills up; English uses 'you'", () => {
  const card: PickInput = {
    name: "Morwenna Penrose",
    language: "en",
    example_dialogues: "{{char}}: \"Sit down before you fall down. Tea first, questions dreckly.\"",
    greeting:
      "Morwenna dragged the door open. “{{user}}, you'll catch your death out there.”\n\nThe wind howled. “Who's there?” someone shouted.",
  };
  assert.deepEqual(pickSignatureLines(card), [
    "Sit down before you fall down. Tea first, questions dreckly.",
    "You, you'll catch your death out there.",
  ]);
});

test("pickSignatureLines: narration lines of a {{char}} turn are not taken as speech", () => {
  const base = { name: "Hạ Vy", language: "vi" as const, greeting: "" };
  // A continuation line without quotes is narration.
  assert.deepEqual(
    pickSignatureLines({
      ...base,
      example_dialogues:
        '{{char}}: *Cô đặt tách trà xuống.* "Muộn rồi đấy, cậu về đi."\nCô quay lưng bước về phía cửa sổ mà không nói thêm lời nào.',
    }),
    ["Muộn rồi đấy, cậu về đi."],
  );
  // A turn that is only narration about her gives nothing.
  assert.deepEqual(
    pickSignatureLines({ ...base, example_dialogues: "{{char}}: Cô lặng im một lúc lâu rồi khẽ thở dài nhìn ra mưa." }),
    [],
  );
  // A speech tag naming her, or a pronoun + speech word inside her turn, still counts.
  assert.deepEqual(
    pickSignatureLines({
      ...base,
      example_dialogues:
        '{{char}}: *ngẩng lên*\nCô khẽ nói: “Mưa thế này thì ở lại thêm chút đi.”\nHạ Vy mỉm cười: «Mình pha thêm ấm trà nhé.»',
    }),
    ["Mưa thế này thì ở lại thêm chút đi.", "Mình pha thêm ấm trà nhé."],
  );
});

test("pickSignatureLines: lines of other speakers are skipped", () => {
  // An unknown "Label:" starts someone else's turn, even after a {{char}} turn (and "Bà" is not "she" here).
  assert.deepEqual(
    pickSignatureLines({
      name: "Hạ Vy",
      language: "vi",
      greeting: "",
      example_dialogues:
        '{{user}}: Chào cô.\n{{char}}: "Ừ, chào cậu, hôm nay trời đẹp nhỉ."\nBà chủ quán: "Hai đứa dùng gì thì gọi bà nhé con."',
    }),
    ["Ừ, chào cậu, hôm nay trời đẹp nhỉ."],
  );
  // In the greeting each quote is judged by the clause right before it.
  assert.deepEqual(
    pickSignatureLines({
      name: "Hạ Vy",
      language: "vi",
      example_dialogues: "",
      greeting:
        'Hạ Vy ngẩng lên: "Cậu đến rồi à, mình chờ mãi." Người phục vụ chen vào: “Quý khách dùng gì ạ, hôm nay có trà sen.”',
    }),
    ["Cậu đến rồi à, mình chờ mãi."],
  );
  // ...and a standalone quote after the waiter's line is still the waiter's.
  assert.deepEqual(
    pickSignatureLines({
      name: "Hạ Vy",
      language: "vi",
      example_dialogues: "",
      greeting:
        'Hạ Vy ngẩng lên: "Cậu đến rồi à, mình chờ mãi."\n\nNgười phục vụ đặt menu xuống bàn.\n\n“Quý khách gọi món sau cũng được ạ.”',
    }),
    ["Cậu đến rồi à, mình chờ mãi."],
  );
});

test("pickSignatureLines: nothing usable gives an empty list", () => {
  assert.deepEqual(pickSignatureLines({ name: "A", language: "vi", example_dialogues: "", greeting: "" }), []);
  assert.deepEqual(
    pickSignatureLines({ name: "A", language: "vi", example_dialogues: '{{char}}: "Ừ."', greeting: "Trời mưa." }),
    [],
  );
});

test("pickSignatureLines: a very long line is cut at a sentence end", () => {
  const long = `Câu đầu tiên ngắn thôi. ${"Câu sau rất dài và cứ kéo mãi không dừng ".repeat(6)}.`;
  const [line] = pickSignatureLines({ name: "A", language: "vi", example_dialogues: `{{char}}: "${long}"`, greeting: "" });
  assert.equal(line, "Câu đầu tiên ngắn thôi.");
});

test("signatureLinesFor: the card's own lines win, filled for the reader", () => {
  const own = signatureLinesFor({
    ...haVy,
    extensions: { lyris: { signature_lines: ["“Trà gừng cho {{user}} nè.”", ""] } },
  });
  assert.deepEqual(own, { lines: ["Trà gừng cho bạn nè."], own: true });
  const picked = signatureLinesFor({ ...haVy, extensions: {} });
  assert.equal(picked.own, false);
  assert.equal(picked.lines.length, 3);
});
