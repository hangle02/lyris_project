import { test } from "node:test";
import assert from "node:assert/strict";
import { emptyCard } from "../../lib/cardForm.ts";
import type { CharacterCard, StoryOut, StyleProfileInfo, TemplateInfo } from "../../types.ts";
import {
  introSections,
  profileTags,
  readerParagraphs,
  settingGroups,
  startingEmotions,
  storiesWith,
  templateOfCard,
  worldTeaser,
} from "./logic.ts";

function card(patch: Partial<CharacterCard> = {}): CharacterCard {
  return { ...emptyCard("viet_hien_dai"), name: "Hạ Vy", gender: "female", ...patch };
}

const PROFILE: StyleProfileInfo = {
  name: "viet_hien_dai",
  title: "Việt Nam hiện đại",
  description: "",
  narration: { vi: { female: "cô", male: "anh", other: "" }, en: { female: "she", male: "he", other: "they" } },
  address_examples: [],
};

test("readerParagraphs: placeholders for the reader, one entry per paragraph", () => {
  assert.deepEqual(readerParagraphs("{{char}} mở tiệm sách.\n\n{{user}} hay ghé   vào chiều thứ sáu.", "Hạ Vy", "vi"), [
    "Hạ Vy mở tiệm sách.",
    "Bạn hay ghé vào chiều thứ sáu.",
  ]);
  assert.deepEqual(readerParagraphs("  \n ", "A", "vi"), []);
  assert.deepEqual(readerParagraphs("{{user}} walks in.", "Morwenna", "en"), ["You walks in."]);
});

test("introSections: reader-facing fields in order, empty ones left out, secrets never shown", () => {
  const c = card({
    description: "Chủ tiệm sách cũ, quen {{user}} từ mùa thu năm ngoái.",
    personality: "Dịu dàng, hay ngượng.",
    goals: "Muốn giữ tiệm sách của bà.",
    secrets: "Đã viết một lá thư cho {{user}} nhưng chưa gửi.",
    scenario: "Chiều mưa ở Đà Lạt.",
  });
  const sections = introSections(c);
  assert.deepEqual(
    sections.map((s) => s.title),
    ["Đôi nét", "Tính cách", "Điều mong muốn", "Bối cảnh"],
  );
  assert.deepEqual(sections[0]?.paragraphs, ["Chủ tiệm sách cũ, quen bạn từ mùa thu năm ngoái."]);
  assert.ok(!JSON.stringify(sections).includes("lá thư"));
});

test("settingGroups: address terms, then style, language, gender and narration", () => {
  const c = card({
    address_terms: { self_term: "mình", player_term: "cậu", nicknames: ["mọt sách", " "], others: "Gọi khách là {{user}} ơi." },
    speech_style: "Câu ngắn, hay thêm “hen”.",
  });
  const groups = settingGroups(c, PROFILE);
  assert.deepEqual(groups[0], {
    title: "Xưng hô",
    rows: [
      { label: "Tự xưng", value: "mình" },
      { label: "Gọi bạn là", value: "cậu" },
      { label: "Tên gọi thân mật", value: "mọt sách" },
      { label: "Với người khác", value: "Gọi khách là bạn ơi." },
    ],
  });
  assert.deepEqual(groups[1]?.rows, [
    { label: "Văn phong", value: "Việt Nam hiện đại" },
    { label: "Ngôn ngữ", value: "Tiếng Việt" },
    { label: "Giới tính", value: "Nữ" },
    { label: "Dẫn truyện gọi nhân vật là", value: "cô" },
    { label: "Cách nói", value: "Câu ngắn, hay thêm “hen”." },
  ]);
});

test("settingGroups: own narration pronoun wins; no address terms drops the group", () => {
  const c = card({ gender: "male", name: "Yến Hoành Sinh", extensions: { lyris: { narration_character: "hắn" } } });
  const groups = settingGroups(c, null);
  assert.equal(groups.length, 1);
  assert.equal(groups[0]?.title, "Giọng kể");
  assert.deepEqual(groups[0]?.rows.find((r) => r.label === "Dẫn truyện gọi nhân vật là"), {
    label: "Dẫn truyện gọi nhân vật là",
    value: "hắn",
  });
  // Unknown style (or styles not loaded yet): a plain word, never the file id.
  assert.deepEqual(groups[0]?.rows[0], { label: "Văn phong", value: "Chưa rõ" });
  assert.ok(!JSON.stringify(groups).includes("viet_hien_dai"));
});

test("startingEmotions: only when the card stores them", () => {
  assert.equal(startingEmotions(card()), null);
  const rows = startingEmotions(card({ extensions: { lyris: { initial_relationship: { affection: 55, fear: 140 } } } }));
  assert.equal(rows?.length, 6);
  assert.deepEqual(rows?.[0], { key: "affection", label: "Thương mến", value: 55 });
  assert.deepEqual(rows?.find((r) => r.key === "fear")?.value, 100);
  assert.deepEqual(rows?.find((r) => r.key === "trust")?.value, 30);
});

test("profileTags: vibes then tags, no repeats, sentence case", () => {
  assert.deepEqual(profileTags(["chữa lành", "việt nam hiện đại", "Đà Lạt"], ["\u{2728} Chữa Lành", "Dịu dàng"]), [
    "Chữa lành",
    "Dịu dàng",
    "Việt Nam hiện đại",
    "Đà Lạt",
  ]);
  assert.deepEqual(profileTags([]), []);
});

function story(id: number, cardId: number, updated: string | null, created: string | null = null): StoryOut {
  return { id, card_id: cardId, updated_at: updated, created_at: created } as unknown as StoryOut;
}

test("storiesWith: this card's stories, newest activity first", () => {
  const list = [
    story(1, 5, "2026-11-10T10:00:00Z"),
    story(2, 6, "2026-11-12T10:00:00Z"),
    story(3, 5, "2026-11-12T09:00:00"),
    story(4, 5, null, "2026-11-11T00:00:00Z"),
  ];
  assert.deepEqual(
    storiesWith(list, 5).map((s) => s.id),
    [3, 4, 1],
  );
  assert.deepEqual(storiesWith(list, null), []);
  assert.deepEqual(storiesWith(list, 9), []);
});

test("templateOfCard: the template a card was installed from", () => {
  const t = { slug: "ha-vy", installed_card_id: 4 } as TemplateInfo;
  assert.equal(templateOfCard([t], 4), t);
  assert.equal(templateOfCard([t], 5), null);
  assert.equal(templateOfCard(null, 4), null);
});

test("worldTeaser: hidden without entries, names only, +N", () => {
  assert.equal(worldTeaser(null, "A"), null);
  assert.equal(worldTeaser({ total: 0, people: ["X"], places: [] }, "A"), null);
  const t = worldTeaser(
    { total: 27, people: ["Hạ Trì", "Thẩm Kính Ngôn"], places: ["Lục trạch"], people_more: 0, places_more: 3 },
    "Lục Bắc Uyên",
  );
  assert.deepEqual(t, {
    line: "27 điều về thế giới của Lục Bắc Uyên.",
    groups: [
      { title: "Người quanh Lục Bắc Uyên", names: ["Hạ Trì", "Thẩm Kính Ngôn"], more: 0 },
      { title: "Nơi chốn", names: ["Lục trạch"], more: 3 },
    ],
  });
  // Only story entries (no people or places everyone knows): the count line alone.
  assert.deepEqual(worldTeaser({ total: 5, people: [], places: [] }, "A")?.groups, []);
  // Defensive: an older server without the "+N" fields, junk in the lists.
  assert.deepEqual(worldTeaser({ total: 2, people: ["  ", 3 as never, "Hạ Trì"], places: "x" as never }, "A")?.groups, [
    { title: "Người quanh A", names: ["Hạ Trì"], more: 0 },
  ]);
});

test("cardFromPublic keeps the public profile and leaves what others never get empty", async () => {
  const { cardFromPublic, introSections: sections, sharedStartNote } = await import("./logic.ts");
  const view = {
    id: 12,
    uid: "u12",
    name: "Hạ Vy",
    role: "Chủ tiệm sách",
    gender: "female" as const,
    language: "vi" as const,
    description: "Cô gái giữ tiệm sách cũ.",
    appearance: "Tóc dài.",
    scenario: "Một chiều mưa.",
    greeting: "Chào {{user}}.",
    alternate_greetings: ["Lại là bạn."],
    tags: ["chữa lành"],
    style_profile: "viet_hien_dai",
    address_terms: { self_term: "em", player_term: "anh", nicknames: ["Vy"], others: "" },
    speech_style: "Nhẹ nhàng.",
    avatar_url: "/api/cards/12/avatar",
    creator_handle: "minhthu.viet",
    creator_name: "Minh Thư",
    visibility: "public" as const,
    extensions: { lyris: { signature_lines: ["Mưa rồi."] } },
  };
  const card = cardFromPublic(view);
  assert.equal(card.name, "Hạ Vy");
  assert.equal(card.greeting, "Chào {{user}}.");
  assert.deepEqual(card.alternate_greetings, ["Lại là bạn."]);
  for (const hidden of ["personality", "background", "goals", "secrets", "example_dialogues", "creator_notes"] as const) {
    assert.equal(card[hidden], "", hidden);
  }
  const keys = sections(card).map((s) => s.key);
  assert.ok(!keys.includes("personality") && !keys.includes("background") && !keys.includes("goals"));
  assert.ok(keys.includes("description"));
  assert.equal(
    sharedStartNote("Hạ Vy", "minhthu.viet"),
    "Bạn chơi với Hạ Vy như bây giờ. @minhthu.viet sửa nhân vật sau này thì story của bạn không đổi.",
  );
});
