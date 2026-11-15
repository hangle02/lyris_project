import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import type { CardSummary, CharacterCard, TemplateInfo } from "../../types.ts";
import {
  buildItems,
  byHandle,
  creatorLine,
  creditLine,
  privateLabelFor,
  installedTemplateIds,
  isPrivate,
  isInstalledTemplate,
  isTemplateCard,
  PRIVATE_LABEL,
  TEMPLATE_CREDIT,
  buildVibes,
  cardRole,
  teaserOf,
  TEASER_CHARS,
  fillForReader,
  filterByVibe,
  itemRoute,
  normalizeTag,
  shortText,
  templateEntryRoute,
  templateImageCredit,
  templateImageUrl,
  vibeLabel,
} from "./logic.ts";

function card(id: number, name: string, tags: string[], extra: Record<string, unknown> = {}): CardSummary {
  return {
    id,
    name,
    gender: "female",
    language: "vi",
    style_profile: "viet_hien_dai",
    description: "",
    tags,
    avatar_url: null,
    story_count: 0,
    updated_at: null,
    ...extra,
  } as CardSummary;
}

function template(
  slug: string,
  name: string,
  opts: { featured?: boolean; vibes?: string[]; tags?: string[]; installed?: number | null; extra?: Record<string, unknown> } = {},
): TemplateInfo {
  return {
    slug,
    featured: opts.featured ?? false,
    vibes: opts.vibes ?? [],
    installed_card_id: opts.installed ?? null,
    card: { name, role: `Vai của ${name}`, tags: opts.tags ?? [] } as unknown as CharacterCard,
    ...(opts.extra ?? {}),
  } as TemplateInfo;
}

test("normalizeTag and vibeLabel: no sparkle, lowercase, keep diacritics", () => {
  assert.equal(normalizeTag("\u2728 Chữa Lành"), "chữa lành");
  assert.equal(normalizeTag("  Bí  Ẩn Nội Tâm "), "bí ẩn nội tâm");
  assert.equal(normalizeTag("Tình đầu"), "tình đầu");
  assert.notEqual(normalizeTag("Tình đầu"), normalizeTag("tinh dau"));
  // NFD input (macOS file names, some keyboards) compares equal to NFC.
  assert.equal(normalizeTag("Chữa lành".normalize("NFD")), "chữa lành");
  assert.equal(vibeLabel("\u2728 CHỮA LÀNH"), "Chữa lành");
  assert.equal(vibeLabel("đà lạt"), "Đà Lạt");
  assert.equal(vibeLabel("\u2728"), "");
  assert.equal(vibeLabel("việt nam hiện đại"), "Việt Nam hiện đại");
  assert.equal(vibeLabel("trung quốc hiện đại"), "Trung Quốc hiện đại");
  assert.equal(vibeLabel("phố sài gòn"), "Phố Sài Gòn");
  assert.equal(vibeLabel("huế xưa"), "Huế xưa");
  assert.equal(vibeLabel("thuế"), "Thuế");
});

test("buildItems: user cards first, installed templates merged, others marked as templates", () => {
  const cards = [card(1, "Lạc Dương", ["ngôn tình"]), card(2, "Riêng tôi", ["Chữa lành"])];
  const templates = [
    template("ha-vy", "Hạ Vy", { featured: true, vibes: ["Chữa lành", "Dịu dàng"], extra: { image_url: "/api/templates/ha-vy/image" } }),
    template("lac-duong", "Lạc Dương", { vibes: ["Tình đầu"], installed: 1 }),
    template("ghost", "Đã xoá", { installed: 99 }),
  ];
  const items = buildItems(cards, templates);
  assert.deepEqual(
    items.map((i) => i.key),
    ["card-1", "card-2", "template-ha-vy", "template-ghost"],
  );
  assert.deepEqual(items[0]?.tags, ["ngôn tình", "tình đầu"]);
  assert.equal(items[2]?.kind, "template");
  assert.equal(items[2]?.cardId, null);
  assert.equal(items[2]?.imageUrl, "/api/templates/ha-vy/image");
  assert.equal(items[2]?.role, "Vai của Hạ Vy");
  // Installed into a card the list no longer has: shown as a template that knows its card.
  assert.equal(items[3]?.cardId, 99);
});

test("buildVibes: base vibes, template vibes, then shared tags; capped", () => {
  const cards = [card(1, "A", ["Mùa thu", "biển"]), card(2, "B", ["mùa thu"]), card(3, "C", ["biển", "mùa thu"])];
  const templates = [template("x", "X", { vibes: ["Cổ trang", "\u2728 Dịu Dàng"] })];
  const items = buildItems(cards, templates);
  assert.deepEqual(buildVibes(items, templates), [
    "chữa lành",
    "dịu dàng",
    "bí ẩn nội tâm",
    "tình đầu",
    "cổ trang",
    "mùa thu",
    "biển",
  ]);
  assert.equal(buildVibes(items, templates, 3).length, 3);
});

test("filterByVibe: normalized compare, null shows all", () => {
  const items = buildItems([card(1, "A", ["\u2728 Chữa lành"]), card(2, "B", ["Bí ẩn"])], []);
  assert.equal(filterByVibe(items, null).length, 2);
  assert.deepEqual(
    filterByVibe(items, "Chữa Lành").map((i) => i.name),
    ["A"],
  );
  assert.deepEqual(filterByVibe(items, "tình đầu"), []);
});

test("F22/F46: no featured character any more: logic.ts has no featuredTemplate, withoutHero, heroImageUrl", () => {
  const src = readFileSync(new URL("./logic.ts", import.meta.url), "utf8");
  for (const name of ["featuredTemplate", "withoutHero", "heroImageUrl"]) assert.doesNotMatch(src, new RegExp(`\\b${name}\\b`), name);
  const page = readFileSync(new URL("./ExplorePage.tsx", import.meta.url), "utf8");
  assert.doesNotMatch(page, /explore-featured/);
});

test("defensive extras: role on card rows, image url and credit on templates", () => {
  assert.equal(cardRole(card(1, "A", [])), "");
  assert.equal(cardRole(card(1, "A", [], { role: "  Chủ tiệm sách " })), "Chủ tiệm sách");
  assert.equal(cardRole(card(1, "A", [], { role: 5 })), "");
  assert.equal(templateImageUrl(template("a", "A")), null);
  assert.equal(templateImageUrl(template("a", "A", { extra: { image_url: "" } })), null);
  assert.equal(templateImageCredit(template("a", "A", { extra: { image_credit: { title: "T" } } })), null);
  assert.deepEqual(
    templateImageCredit(
      template("a", "A", {
        extra: {
          image_credit: { title: "Da Lat", creator: "Tuong Lam Photos", licence: "CC BY-SA 4.0", source_url: "https://x", licence_url: null },
        },
      }),
    ),
    { title: "Da Lat", creator: "Tuong Lam Photos", licence: "CC BY-SA 4.0", licence_url: null, source_url: "https://x", changes: null },
  );
});

test("fillForReader: names and a capitalised 'Bạn' at sentence starts", () => {
  assert.equal(
    fillForReader("Tiệm của {{char}}. {{user}} mới ghé tiệm, {{user}} ngồi cạnh cửa sổ.", "Hạ Vy", "vi"),
    "Tiệm của Hạ Vy. Bạn mới ghé tiệm, bạn ngồi cạnh cửa sổ.",
  );
  assert.equal(fillForReader("{{user}} là khách.", "A", "vi"), "Bạn là khách.");
  assert.equal(
    fillForReader("Rain.\n{{ user }} and {{char}} meet; {{char}} looks at {{user}}.", "Morwenna", "en"),
    "Rain.\nYou and Morwenna meet; Morwenna looks at you.",
  );
  assert.equal(fillForReader("Lạc Dương và {{user}} đều là sinh viên.", "Lạc Dương", "vi"), "Lạc Dương và bạn đều là sinh viên.");
});

test("shortText: first paragraph, cut at a word", () => {
  assert.equal(shortText("Ngắn gọn.\n\nĐoạn hai."), "Ngắn gọn.");
  const long = "Một hai ba bốn năm sáu bảy tám chín mười ".repeat(10);
  const out = shortText(long, 40);
  assert.ok(out.endsWith("…"));
  assert.ok(out.length <= 41);
  assert.ok(!out.includes("  "));
});

test("creator attribution: handle, templates, private label", () => {
  assert.equal(byHandle("ngocanh"), "bởi @ngocanh");
  assert.equal(byHandle("@ngocanh "), "bởi @ngocanh");
  assert.equal(byHandle(""), null);
  assert.equal(byHandle(null), null);
  assert.equal(creatorLine({ template: true, handle: "ban" }), TEMPLATE_CREDIT);
  assert.equal(creatorLine({ template: false, handle: "ban" }), "bởi @ban");
  assert.equal(creatorLine({ template: false, handle: null }), null);

  assert.equal(isTemplateCard({ lyris: { template: "ha-vy" } }), true);
  assert.equal(isTemplateCard({ lyris: { template: "  " } }), false);
  assert.equal(isTemplateCard({ lyris: "x" }), false);
  assert.equal(isTemplateCard({}), false);
  assert.equal(isTemplateCard(null), false);

  assert.deepEqual([...installedTemplateIds([template("a", "A", { installed: 3 }), template("b", "B")])], [3]);

  assert.equal(isPrivate(undefined), true);
  assert.equal(isPrivate("private"), true);
  assert.equal(isPrivate("unlisted"), false);
  assert.equal(isPrivate("public"), false);
  assert.equal(PRIVATE_LABEL, "Riêng tư");
});

test("buildItems: creator line for own cards, installed templates and templates", () => {
  const cards = [
    card(1, "Của tôi", [], { creator_handle: "ban" }),
    card(2, "Cài từ mẫu", [], { creator_handle: "ban" }),
    card(3, "Không rõ", [], { creator_handle: null }),
  ];
  const items = buildItems(cards, [template("mau", "Cài từ mẫu", { installed: 2 }), template("moi", "Mới")]);
  assert.deepEqual(
    items.map((i) => i.creator),
    ["bởi @ban", TEMPLATE_CREDIT, null, TEMPLATE_CREDIT],
  );
});

test("isInstalledTemplate: one rule for the editor and the lists (installed_card_id wins over the tag)", () => {
  const installed = installedTemplateIds([template("lac-duong", "Lạc Dương", { installed: 7 })]);
  // Legacy seed card adopted by name: no tag, but GET /api/templates reports it installed.
  assert.equal(isInstalledTemplate(7, {}, installed), true);
  assert.equal(creatorLine({ template: isInstalledTemplate(7, {}, installed), handle: "ban" }), TEMPLATE_CREDIT);
  // A tagged card that is not the installed one reads "bởi @handle", as in the Studio list.
  assert.equal(isInstalledTemplate(9, { lyris: { template: "lac-duong" } }, installed), false);
  assert.equal(isInstalledTemplate(null, { lyris: { template: "lac-duong" } }, installed), false);
  // Templates could not be loaded: the tag decides.
  assert.equal(isInstalledTemplate(9, { lyris: { template: "lac-duong" } }, null), true);
  assert.equal(isInstalledTemplate(7, {}, null), false);
});

test("creditLine: templates never say Riêng tư; own private cards do", () => {
  assert.equal(creditLine({ template: false, handle: "ban", visibility: "private" }), "bởi @ban · Riêng tư");
  assert.equal(creditLine({ template: false, handle: "ban", visibility: undefined }), "bởi @ban · Riêng tư");
  assert.equal(creditLine({ template: false, handle: "ban", visibility: "public" }), "bởi @ban");
  assert.equal(creditLine({ template: true, handle: "ban", visibility: "private" }), TEMPLATE_CREDIT);
  assert.equal(creditLine({ template: false, handle: null, visibility: "unlisted" }), "");
  assert.equal(privateLabelFor({ template: true, visibility: "private" }), null);
  assert.equal(privateLabelFor({ template: false, visibility: null }), PRIVATE_LABEL);
});

test("teaserOf: reader-facing, short, empty when no description", () => {
  assert.equal(teaserOf("", "Hạ Vy", "vi"), "");
  assert.equal(teaserOf("{{char}} giữ tiệm sách cho {{user}}.", "Hạ Vy", "vi"), "Hạ Vy giữ tiệm sách cho bạn.");
  const long = "Một câu rất dài ".repeat(20);
  const t = teaserOf(long, "X", "vi");
  assert.ok(t.length <= TEASER_CHARS + 1 && t.endsWith("…"));
});

test("itemRoute / templateEntryRoute: a tap opens the character's profile", () => {
  assert.deepEqual(itemRoute({ cardId: 4, slug: null }), { name: "character", target: { kind: "card", id: 4 }, start: false });
  assert.deepEqual(itemRoute({ cardId: null, slug: "ha-vy" }), {
    name: "character",
    target: { kind: "template", slug: "ha-vy" },
    start: false,
  });
  assert.equal(itemRoute({ cardId: null, slug: null }), null);
  assert.deepEqual(templateEntryRoute({ slug: "ha-vy", installed_card_id: 7 }, true), {
    name: "character",
    target: { kind: "card", id: 7 },
    start: true,
  });
  assert.deepEqual(templateEntryRoute({ slug: "ha-vy", installed_card_id: null }, true), {
    name: "character",
    target: { kind: "template", slug: "ha-vy" },
    start: true,
  });
});

test("sharedItems: others' public characters, newest first, never your own", async () => {
  const { sharedItems } = await import("./logic.ts");
  const pc = (id: number, handle: string, updated: string | null, extra: Record<string, unknown> = {}) => ({
    id,
    uid: `u${id}`,
    visibility: "public" as const,
    name: `Nhân vật ${id}`,
    role: " Pháp sư ",
    gender: "female" as const,
    language: "vi" as const,
    style_profile: "viet_hien_dai",
    description: "{{char}} chờ {{user}} ở bến tàu.",
    tags: ["Chữa lành \u{2728}", "chữa lành"],
    avatar_url: null,
    updated_at: updated,
    creator_handle: handle,
    creator_name: handle,
    creator_avatar_url: null,
    ...extra,
  });
  const items = sharedItems(
    [pc(1, "mai", "2026-11-10T00:00:00Z"), pc(2, "MinhThu.Viet", "2026-11-12T00:00:00Z"), pc(3, "khoa", "2026-11-13T00:00:00Z"), pc(4, "mai", null)],
    "@minhthu.viet",
  );
  assert.deepEqual(
    items.map((i) => i.cardId),
    [3, 1, 4],
  );
  const first = items[0]!;
  assert.equal(first.kind, "shared");
  assert.equal(first.key, "shared-3");
  assert.equal(first.creator, "bởi @khoa");
  assert.equal(first.role, "Pháp sư");
  assert.deepEqual(first.tags, ["chữa lành"]);
  assert.equal(first.teaser, "Nhân vật 3 chờ bạn ở bến tàu.");
  assert.equal(sharedItems([], null).length, 0);
  assert.equal(sharedItems([pc(5, "mai", null)], null).length, 1);
});

test("every character has exactly one cell, Hạ Vy too (featured or not, installed or not)", () => {
  const hv = template("ha-vy", "Hạ Vy", { featured: true, installed: 8, extra: { image_url: "/api/templates/ha-vy/image" } });
  const other = template("x", "X");
  const cards = [card(8, "Hạ Vy", [], { avatar_url: "/api/cards/8/avatar?v=a.png" }), card(7, "Tần Dương", [])];
  const installed = buildItems(cards, [hv, other]);
  assert.deepEqual(installed.map((i) => i.name), ["Hạ Vy", "Tần Dương", "X"]);
  assert.equal(installed.filter((i) => i.name === "Hạ Vy").length, 1);
  assert.equal(installed[0]?.imageUrl, "/api/cards/8/avatar?v=a.png", "your own picture of the installed template");
  const fresh = buildItems([card(7, "Tần Dương", [])], [template("ha-vy", "Hạ Vy", { featured: true }), other]);
  assert.deepEqual(fresh.map((i) => i.name), ["Tần Dương", "Hạ Vy", "X"]);
  assert.equal(new Set(fresh.map((i) => i.key)).size, fresh.length);
});

test("exploreGrid: one list — your cards, templates not installed, then others' public characters", async () => {
  const { exploreGrid, sharedItems } = await import("./logic.ts");
  const mine = buildItems([card(1, "A", ["biển"])], [template("x", "X", { vibes: ["Cổ trang"] })]);
  const others = sharedItems(
    [
      {
        id: 7,
        uid: "u7",
        visibility: "public" as const,
        name: "Lục Bắc Uyên",
        role: "Tổng giám đốc",
        gender: "male" as const,
        language: "vi" as const,
        style_profile: "viet_hien_dai",
        description: "{{char}} chờ {{user}}.",
        tags: ["Bí ẩn"],
        avatar_url: null,
        updated_at: "2026-11-15T00:00:00Z",
        creator_handle: "mai",
        creator_name: "mai",
        creator_avatar_url: null,
      },
    ],
    null,
  );
  const grid = exploreGrid(mine, others);
  assert.deepEqual(
    grid.map((i) => i.kind),
    ["card", "template", "shared"],
  );
  assert.equal(grid[2]?.creator, "bởi @mai");
  // Each character once, even if the same shared card were passed twice.
  assert.equal(exploreGrid(mine, [...others, ...others]).length, 3);
  assert.deepEqual(exploreGrid(mine, []), mine);
  // Vibe chips take the shared characters' tags too ("bí ẩn" is on a card and a shared character only).
  const withTag = buildItems([card(2, "B", ["Bí ẩn"])], []);
  assert.ok(!buildVibes(withTag, []).includes("bí ẩn"));
  assert.ok(buildVibes(exploreGrid(withTag, others), []).includes("bí ẩn"));
  assert.ok(filterByVibe(grid, "bí ẩn").some((i) => i.kind === "shared"));
});
