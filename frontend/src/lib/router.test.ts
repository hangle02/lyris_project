import { test } from "node:test";
import assert from "node:assert/strict";
import { characterRoute, legacyRedirect, parseRoute, routeHref, sameRoute, tabOf, templateRoute, toHash } from "./router.ts";
import type { Route } from "./router.ts";

const HUB: Route = { name: "hub" };

test("parseRoute: hub is the start screen", () => {
  for (const h of ["", "#", "#/", "/", "#/chat", "#/chat/", "chat"]) {
    assert.deepEqual(parseRoute(h), HUB, h);
  }
});

test("parseRoute: explore", () => {
  assert.deepEqual(parseRoute("#/explore"), { name: "explore" });
  assert.deepEqual(parseRoute("#/explore/"), { name: "explore" });
  assert.deepEqual(parseRoute("explore"), { name: "explore" });
  assert.deepEqual(parseRoute("#/explore/3"), HUB);
});

test("parseRoute: chat with a story id", () => {
  assert.deepEqual(parseRoute("#/chat/12"), { name: "chat", storyId: 12 });
  assert.deepEqual(parseRoute("#/chat/12/"), { name: "chat", storyId: 12 });
  assert.deepEqual(parseRoute("/chat/7"), { name: "chat", storyId: 7 });
  assert.deepEqual(parseRoute("chat/7"), { name: "chat", storyId: 7 });
});

test("parseRoute: bad story ids go to the hub", () => {
  for (const bad of ["abc", "0", "-3", "1.5", "1e3", "0x10", " 4", "99999999999999999999"]) {
    assert.deepEqual(parseRoute(`#/chat/${bad}`), HUB, bad);
  }
});

test("parseRoute: studio and card editor", () => {
  assert.deepEqual(parseRoute("#/studio"), { name: "studio" });
  assert.deepEqual(parseRoute("#/studio/"), { name: "studio" });
  assert.deepEqual(parseRoute("#/studio/new"), { name: "card", cardId: null });
  assert.deepEqual(parseRoute("#/studio/12"), { name: "card", cardId: 12 });
  assert.deepEqual(parseRoute("#/studio/oops"), { name: "studio" });
});

test("parseRoute: personas and new story", () => {
  assert.deepEqual(parseRoute("#/personas"), { name: "personas" });
  assert.deepEqual(parseRoute("#/new-story"), { name: "newStory", cardId: null });
  assert.deepEqual(parseRoute("#/new-story?card=12"), { name: "newStory", cardId: 12 });
  assert.deepEqual(parseRoute("#/new-story?card=x"), { name: "newStory", cardId: null });
  assert.deepEqual(parseRoute("#/new-story?foo=1&card=5"), { name: "newStory", cardId: 5 });
});

test("parseRoute: my profile", () => {
  assert.deepEqual(parseRoute("#/me"), { name: "profile", handle: null });
  assert.deepEqual(parseRoute("#/me/"), { name: "profile", handle: null });
  assert.deepEqual(parseRoute("me"), { name: "profile", handle: null });
  assert.deepEqual(parseRoute("#/me?tab=persona"), { name: "profile", handle: null });
  assert.deepEqual(parseRoute("#/me/3"), HUB);
});

test("parseRoute: someone's profile by handle", () => {
  assert.deepEqual(parseRoute("#/u/ban"), { name: "profile", handle: "ban" });
  assert.deepEqual(parseRoute("#/u/hoa.ly_99/"), { name: "profile", handle: "hoa.ly_99" });
  // Handles ignore case; "@" is optional (also percent-encoded).
  assert.deepEqual(parseRoute("#/u/Hoa.Ly"), { name: "profile", handle: "hoa.ly" });
  assert.deepEqual(parseRoute("#/u/@ban"), { name: "profile", handle: "ban" });
  assert.deepEqual(parseRoute("#/u/%40ban"), { name: "profile", handle: "ban" });
});

test("parseRoute: bad handles go to the hub", () => {
  for (const h of ["#/u", "#/u/", "#/u/a b", "#/u/x-y", "#/u/%E1%BA%A1", "#/u/" + "a".repeat(31), "#/u/ban/cards", "#/u/@"]) {
    assert.deepEqual(parseRoute(h), HUB, h);
  }
});

test("parseRoute: unknown paths go to the hub", () => {
  for (const h of ["#/nope", "#/studio/12/extra", "#/personas/3", "#/new-story/2", "#/%E0%A4%A", "#//", "#/chat/1/2"]) {
    assert.deepEqual(parseRoute(h), HUB, h);
  }
});

test("routeHref round-trips through parseRoute", () => {
  const routes: Route[] = [
    { name: "hub" },
    { name: "explore" },
    { name: "chat", storyId: 3 },
    { name: "studio" },
    { name: "card", cardId: null },
    { name: "card", cardId: 12 },
    { name: "personas" },
    { name: "newStory", cardId: null },
    { name: "newStory", cardId: 12 },
    { name: "profile", handle: null },
    { name: "profile", handle: "ban" },
    { name: "profile", handle: "hoa.ly_99" },
  ];
  for (const r of routes) assert.deepEqual(parseRoute(routeHref(r)), r);
  assert.equal(routeHref({ name: "hub" }), "#/");
  assert.equal(routeHref({ name: "card", cardId: 12 }), "#/studio/12");
  assert.equal(routeHref({ name: "newStory", cardId: 12 }), "#/new-story?card=12");
  assert.equal(routeHref({ name: "profile", handle: null }), "#/me");
  assert.equal(routeHref({ name: "profile", handle: "hoa.ly" }), "#/u/hoa.ly");
});

test("routeHref: a chat without a story links to the hub", () => {
  assert.equal(routeHref({ name: "chat", storyId: null }), "#/");
  assert.deepEqual(parseRoute(routeHref({ name: "chat", storyId: null })), HUB);
});

test("tabOf: tab bar only on hub, explore and the studio list", () => {
  assert.equal(tabOf({ name: "hub" }), "hub");
  assert.equal(tabOf({ name: "explore" }), "explore");
  assert.equal(tabOf({ name: "studio" }), "studio");
  assert.equal(tabOf({ name: "chat", storyId: 1 }), null);
  assert.equal(tabOf({ name: "card", cardId: null }), null);
  assert.equal(tabOf({ name: "personas" }), null);
  assert.equal(tabOf({ name: "newStory", cardId: 2 }), null);
  assert.equal(tabOf({ name: "profile", handle: null }), null);
});

test("toHash and sameRoute", () => {
  assert.equal(toHash("#/studio"), "#/studio");
  assert.equal(toHash("/studio"), "#/studio");
  assert.equal(toHash("studio"), "#/studio");
  assert.equal(toHash({ name: "personas" }), "#/personas");
  assert.equal(toHash({ name: "hub" }), "#/");
  assert.ok(sameRoute(parseRoute("#/chat/4/"), { name: "chat", storyId: 4 }));
  assert.ok(sameRoute(parseRoute("#/chat"), { name: "hub" }));
  assert.ok(!sameRoute({ name: "studio" }, { name: "card", cardId: null }));
});

test("parseRoute: character profile of a card", () => {
  const card = (id: number, start = false): Route => ({ name: "character", target: { kind: "card", id }, start });
  assert.deepEqual(parseRoute("#/character/12"), card(12));
  assert.deepEqual(parseRoute("#/character/12/"), card(12));
  assert.deepEqual(parseRoute("character/7"), card(7));
  assert.deepEqual(parseRoute("#/character/12?start=1"), card(12, true));
  assert.deepEqual(parseRoute("#/character/12?start=true"), card(12, true));
  assert.deepEqual(parseRoute("#/character/12?start=0"), card(12));
  assert.deepEqual(parseRoute("#/character/12?x=1&start=1"), card(12, true));
});

test("parseRoute: character profile of a template", () => {
  const tpl = (slug: string, start = false): Route => ({ name: "character", target: { kind: "template", slug }, start });
  assert.deepEqual(parseRoute("#/character/template/ha-vy"), tpl("ha-vy"));
  assert.deepEqual(parseRoute("#/character/template/Ha-Vy/"), tpl("ha-vy"));
  assert.deepEqual(parseRoute("#/character/template/morwenna_penrose?start=1"), tpl("morwenna_penrose", true));
});

test("parseRoute: bad character links go to the hub", () => {
  for (const h of [
    "#/character",
    "#/character/",
    "#/character/0",
    "#/character/abc",
    "#/character/1.5",
    "#/character/12/extra",
    "#/character/template",
    "#/character/template/",
    "#/character/template/-x",
    "#/character/template/a b",
    "#/character/template/%E1%BA%A1",
    "#/character/template/ha-vy/more",
    "#/character/template/" + "a".repeat(65),
  ]) {
    assert.deepEqual(parseRoute(h), HUB, h);
  }
});

test("routeHref: character routes round-trip", () => {
  const routes: Route[] = [
    characterRoute(3),
    characterRoute(3, true),
    templateRoute("ha-vy"),
    templateRoute("ta-van-lan", true),
  ];
  for (const r of routes) assert.deepEqual(parseRoute(routeHref(r)), r);
  assert.equal(routeHref(characterRoute(12)), "#/character/12");
  assert.equal(routeHref(characterRoute(12, true)), "#/character/12?start=1");
  assert.equal(routeHref(templateRoute("ha-vy")), "#/character/template/ha-vy");
  assert.equal(routeHref(templateRoute("ha-vy", true)), "#/character/template/ha-vy?start=1");
  assert.equal(tabOf(characterRoute(1)), null);
});

test("legacyRedirect: old new-story links open the character profile with the sheet", () => {
  assert.deepEqual(legacyRedirect(parseRoute("#/new-story?card=12")), characterRoute(12, true));
  assert.equal(routeHref(legacyRedirect(parseRoute("#/new-story?card=12")) as Route), "#/character/12?start=1");
  assert.deepEqual(legacyRedirect(parseRoute("#/new-story")), { name: "explore" });
  assert.deepEqual(legacyRedirect(parseRoute("#/new-story?card=x")), { name: "explore" });
  assert.equal(legacyRedirect(parseRoute("#/studio/3")), null);
  assert.equal(legacyRedirect(characterRoute(3)), null);
});

test("parseRoute: Phase 4b sign-in and admin routes", () => {
  assert.deepEqual(parseRoute("#/login"), { name: "login" });
  assert.deepEqual(parseRoute("#/login/"), { name: "login" });
  assert.deepEqual(parseRoute("#/signup"), { name: "signup", code: null });
  assert.deepEqual(parseRoute("#/signup?code=LYR-7KQ2-M9XD-4TPA"), { name: "signup", code: "7KQ2M9XD4TPA" });
  assert.deepEqual(parseRoute("#/signup?code=lyr-7kq2-m9xd-4tpa"), { name: "signup", code: "7KQ2M9XD4TPA" });
  assert.deepEqual(parseRoute("#/signup?code=LYR%2D7KQ2%2DM9XD%2D4TPA"), { name: "signup", code: "7KQ2M9XD4TPA" });
  // A code that is not one: the page opens with an empty field.
  assert.deepEqual(parseRoute("#/signup?code=hello"), { name: "signup", code: null });
  assert.deepEqual(parseRoute("#/signup?code=7KQ2-M9XD-4TPU"), { name: "signup", code: null });
  assert.deepEqual(parseRoute("#/admin"), { name: "admin" });
  for (const h of ["#/login/x", "#/signup/x", "#/admin/3"]) assert.deepEqual(parseRoute(h), HUB, h);
});

test("routeHref: Phase 4b routes round-trip, and have no tab bar", () => {
  const routes: Route[] = [{ name: "login" }, { name: "signup", code: null }, { name: "signup", code: "7KQ2M9XD4TPA" }, { name: "admin" }];
  for (const r of routes) {
    assert.deepEqual(parseRoute(routeHref(r)), r);
    assert.equal(tabOf(r), null);
  }
  assert.equal(routeHref({ name: "signup", code: "7KQ2M9XD4TPA" }), "#/signup?code=LYR-7KQ2-M9XD-4TPA");
  assert.equal(routeHref({ name: "admin" }), "#/admin");
});
