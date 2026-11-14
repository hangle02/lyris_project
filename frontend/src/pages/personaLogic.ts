// Pure helpers of the persona page (tested in personaLogic.test.ts). No React, no DOM.
import type { Gender, Persona, PersonaOut } from "../types.ts";

const GENDER: Record<Gender, string> = { female: "Nữ", male: "Nam", other: "Khác" };

/** "3 story", or "chưa có story" for 0. */
export function storyCountLabel(n: number): string {
  return n > 0 ? `${n} story` : "chưa có story";
}

/**
 * The persona new stories use, as the backend picks it: the saved default when it still exists,
 * else the first persona; null for an empty list.
 */
export function defaultPersonaId(personas: readonly Pick<PersonaOut, "id">[], savedId: number | null | undefined): number | null {
  const saved = savedId == null ? undefined : personas.find((p) => p.id === savedId);
  return (saved ?? personas[0])?.id ?? null;
}

/** Meta line of a persona card: "Nữ · 3 story · Mặc định". */
export function personaMeta(p: Pick<PersonaOut, "gender" | "story_count">, isDefault: boolean): string {
  return [GENDER[p.gender] ?? GENDER.other, storyCountLabel(p.story_count), isDefault ? "Mặc định" : null]
    .filter(Boolean)
    .join(" · ");
}

/**
 * Body of POST/PUT /api/personas: only the Persona fields (never avatar_url / story_count), with the
 * name on one line and the description trimmed. `avatar` is the file name the server last returned.
 */
export function personaBody(p: Persona, avatar: string | null): Persona {
  return {
    id: p.id,
    uid: p.uid ?? null,
    name: p.name.replace(/\s+/g, " ").trim(),
    gender: p.gender,
    description: p.description.trim(),
    avatar,
  };
}

/** Replace one persona in the list in place (avatar change); unknown ids are left out. */
export function replacePersona(list: readonly PersonaOut[] | null, out: PersonaOut): PersonaOut[] {
  return (list ?? []).map((p) => (p.id === out.id ? out : p));
}
