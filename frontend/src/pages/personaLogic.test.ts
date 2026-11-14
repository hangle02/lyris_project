import { test } from "node:test";
import assert from "node:assert/strict";
import type { PersonaOut } from "../types.ts";
import { defaultPersonaId, personaBody, personaMeta, replacePersona, storyCountLabel } from "./personaLogic.ts";

function persona(id: number, name: string, extra: Partial<PersonaOut> = {}): PersonaOut {
  return { id, name, gender: "female", description: "", story_count: 0, avatar_url: null, ...extra };
}

test("storyCountLabel and personaMeta: real counts, zero in words, default marker", () => {
  assert.equal(storyCountLabel(0), "chưa có story");
  assert.equal(storyCountLabel(1), "1 story");
  assert.equal(storyCountLabel(12), "12 story");
  assert.equal(personaMeta({ gender: "female", story_count: 3 }, true), "Nữ · 3 story · Mặc định");
  assert.equal(personaMeta({ gender: "male", story_count: 0 }, false), "Nam · chưa có story");
  assert.equal(personaMeta({ gender: "other", story_count: 1 }, false), "Khác · 1 story");
});

test("personaBody: only Persona fields, one-line name, trimmed description", () => {
  const out = persona(4, "  Ngọc \n Anh ", {
    uid: "a".repeat(32),
    description: "  18 tuổi.  ",
    avatar: "old.webp",
    story_count: 5,
    avatar_url: "/api/personas/4/avatar?v=old.webp",
  });
  assert.deepEqual(personaBody(out, "new.webp"), {
    id: 4,
    uid: "a".repeat(32),
    name: "Ngọc Anh",
    gender: "female",
    description: "18 tuổi.",
    avatar: "new.webp",
  });
  assert.deepEqual(personaBody({ id: null, name: "Gia Huy", gender: "male", description: "" }, null), {
    id: null,
    uid: null,
    name: "Gia Huy",
    gender: "male",
    description: "",
    avatar: null,
  });
});

test("replacePersona: in place, order kept", () => {
  const list = [persona(1, "A"), persona(2, "B")];
  const next = replacePersona(list, persona(2, "B", { avatar_url: "/x" }));
  assert.deepEqual(
    next.map((p) => [p.id, p.avatar_url]),
    [
      [1, null],
      [2, "/x"],
    ],
  );
  assert.deepEqual(replacePersona(null, persona(1, "A")), []);
});

test("defaultPersonaId: saved default, else the first, null when empty", () => {
  const list = [persona(4, "Gia Huy"), persona(7, "Ngọc Anh")];
  assert.equal(defaultPersonaId(list, 7), 7);
  assert.equal(defaultPersonaId(list, 99), 4);
  assert.equal(defaultPersonaId(list, null), 4);
  assert.equal(defaultPersonaId([], 7), null);
});
