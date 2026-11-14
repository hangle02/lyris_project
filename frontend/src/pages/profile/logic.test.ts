import { test } from "node:test";
import assert from "node:assert/strict";
import type { CardSummary, TemplateInfo } from "../../types.ts";
import {
  BIO_MAX,
  atHandle,
  bioError,
  charCount,
  cleanBio,
  cleanDisplayName,
  createdCards,
  displayNameError,
  handleError,
  handleFromName,
  isValidHandle,
  normalizeHandle,
  profileOwnership,
  profileStats,
  sameHandle,
  serverErrorField,
  validateProfile,
  visibilityLabel,
} from "./logic.ts";

test("normalizeHandle: trims, drops a leading @, lowercases", () => {
  assert.equal(normalizeHandle("  @Hoa.Ly "), "hoa.ly");
  assert.equal(normalizeHandle("@@ban"), "ban");
  assert.equal(normalizeHandle("ban@"), "ban@");
  assert.equal(normalizeHandle(""), "");
});

test("handleError: valid handles", () => {
  for (const h of ["ban", "hoa.ly", "ngoc_anh", "a_b.c_1", "abc", "x".repeat(30), "_ban_", "1990", "a..b"]) {
    assert.equal(handleError(h), null, h);
    assert.ok(isValidHandle(h), h);
  }
});

test("handleError: each rule has its own message", () => {
  assert.equal(handleError(""), "Hãy đặt một handle.");
  assert.match(handleError("ngoc anh") ?? "", /khoảng trắng/);
  assert.match(handleError("ngọc") ?? "", /có dấu/);
  assert.match(handleError("đức") ?? "", /có dấu/);
  assert.match(handleError("hoa-ly") ?? "", /a-z, số 0-9/);
  assert.match(handleError("hoa@ly") ?? "", /a-z, số 0-9/);
  assert.match(handleError("ab") ?? "", /ít nhất 3/);
  assert.match(handleError("x".repeat(31)) ?? "", /tối đa 30/);
  assert.match(handleError(".ban") ?? "", /dấu chấm/);
  assert.match(handleError("ban.") ?? "", /dấu chấm/);
});

test("handleError: uppercase is rejected before normalizing, accepted after", () => {
  assert.notEqual(handleError("Ban"), null);
  assert.equal(handleError(normalizeHandle("Ban")), null);
});

test("display name: required, at most 60 characters, spaces collapsed", () => {
  assert.equal(cleanDisplayName("  Ngọc   Anh "), "Ngọc Anh");
  assert.equal(displayNameError("   "), "Hãy nhập tên hiển thị.");
  assert.equal(displayNameError("Ngọc Anh"), null);
  assert.equal(displayNameError("ữ".repeat(60)), null);
  assert.match(displayNameError("a".repeat(61)) ?? "", /tối đa 60/);
});

test("bio: counted in code points, at most 500", () => {
  assert.equal(charCount("ữ\u{1F600}"), 2);
  assert.equal(cleanBio("  dòng một   \n\ndòng hai  \n\n"), "dòng một\n\ndòng hai");
  assert.equal(bioError("x".repeat(BIO_MAX)), null);
  assert.match(bioError("x".repeat(BIO_MAX + 1)) ?? "", /tối đa 500 ký tự \(đang có 501\)/);
  assert.equal(bioError(`${"x".repeat(BIO_MAX)}   \n`), null);
});

test("handleFromName: folds Vietnamese to a valid handle", () => {
  assert.equal(handleFromName("Ngọc Anh"), "ngoc_anh");
  assert.equal(handleFromName("Đỗ Đức Hoà"), "do_duc_hoa");
  assert.equal(handleFromName("  Lan  (Mây) "), "lan_may");
  assert.equal(handleFromName("Bạn"), "ban");
  assert.equal(handleFromName("A"), null);
  assert.equal(handleFromName("!!!"), null);
  const long = handleFromName("Nguyễn Thị Minh Khai Phương Thảo Hồng");
  assert.ok(long !== null && long.length <= 30 && !long.endsWith("_"), long ?? "");
});

test("serverErrorField: routes 422 messages to their field", () => {
  assert.equal(serverErrorField("Handle @ban đã có người dùng."), "handle");
  assert.equal(serverErrorField("Dữ liệu không hợp lệ: handle: String should have at least 3 characters"), "handle");
  assert.equal(serverErrorField("Tên hiển thị không được để trống."), "display_name");
  assert.equal(serverErrorField("Giới thiệu dài quá 500 ký tự."), "bio");
  assert.equal(serverErrorField("Máy chủ báo lỗi (HTTP 500)."), null);
});

test("validateProfile: one message per failing field", () => {
  assert.deepEqual(validateProfile({ display_name: "Ngọc Anh", handle: "@Ngoc_Anh", bio: "" }), {});
  const errs = validateProfile({ display_name: " ", handle: "a", bio: "x".repeat(600) });
  assert.deepEqual(Object.keys(errs).sort(), ["bio", "display_name", "handle"]);
});

test("sameHandle and atHandle", () => {
  assert.ok(sameHandle("Ban", "@ban"));
  assert.ok(!sameHandle("ban", "ban2"));
  assert.ok(!sameHandle(null, "ban"));
  assert.equal(atHandle("ban"), "@ban");
});

test("visibilityLabel", () => {
  assert.equal(visibilityLabel("private"), "Riêng tư");
  assert.equal(visibilityLabel(undefined), "Riêng tư");
  assert.equal(visibilityLabel("unlisted"), "Không công khai");
  assert.equal(visibilityLabel("public"), "Công khai");
});

function card(id: number, extra: Partial<CardSummary> = {}): CardSummary {
  return {
    id,
    uid: null,
    visibility: "private",
    creator_handle: "ban",
    creator_name: "Bạn",
    name: `Card ${id}`,
    gender: "female",
    language: "vi",
    style_profile: "viet_hien_dai",
    description: "",
    tags: [],
    avatar_url: null,
    story_count: 0,
    updated_at: `2026-11-1${id}T00:00:00Z`,
    ...extra,
  };
}

function template(installed: number | null): TemplateInfo {
  return { slug: `t${installed}`, featured: false, vibes: [], card: {} as TemplateInfo["card"], installed_card_id: installed };
}

test("createdCards: own cards newest first, no installed templates, no other creators", () => {
  const cards = [card(1), card(2), card(3, { creator_handle: "khac" }), card(4, { creator_handle: null }), card(5, { creator_handle: "BAN" })];
  const out = createdCards(cards, [template(2), template(null)], "ban");
  assert.deepEqual(
    out.map((c) => c.id),
    [5, 4, 1],
  );
  // Without a known handle every non-template card counts.
  assert.deepEqual(
    createdCards(cards, [template(2)], null).map((c) => c.id),
    [5, 4, 3, 1],
  );
});

test("profileStats: real counts, grid count wins for cards", () => {
  const acc = { card_count: 7, story_count: 0, persona_count: 2 };
  assert.deepEqual(
    profileStats(acc).map((s) => [s.key, s.value, s.label]),
    [
      ["cards", 7, "nhân vật"],
      ["stories", 0, "story"],
      ["personas", 2, "persona"],
    ],
  );
  assert.equal(profileStats(acc, 3)[0]?.value, 3);
});

test("profileOwnership: #/me and the own handle are the owner's profile", () => {
  assert.deepEqual(profileOwnership(null, null, null), { own: true, follow: null });
  assert.deepEqual(profileOwnership(null, "ban", null), { own: true, follow: null });
  assert.deepEqual(profileOwnership("Ban", "ban", null), { own: true, follow: null });
  assert.deepEqual(profileOwnership("hoa", "ban", null), { own: false, follow: null });
  assert.deepEqual(profileOwnership("ban", null, null), { own: false, follow: null });
});

test("profileOwnership: a rename on #/u/<old> keeps the own profile and follows to the new handle", () => {
  // Regression: after saving handle "hoa" on #/u/ban the page asked the server for @ban (404).
  assert.deepEqual(profileOwnership("ban", "hoa", "ban"), { own: true, follow: "hoa" });
  assert.deepEqual(profileOwnership("ban", "Hoa", "@Ban"), { own: true, follow: "hoa" });
  // Another account's handle never counts as own.
  assert.deepEqual(profileOwnership("lan", "hoa", "ban"), { own: false, follow: null });
});
