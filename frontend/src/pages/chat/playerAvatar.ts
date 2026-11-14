import { createContext, useEffect, useMemo, useState } from "react";
import { api } from "../../api/client";
import type { PersonaOut } from "../../types";
import { personaFace } from "./chatLogic";
import type { PlayerFace } from "./chatLogic";

export type { PlayerFace };

/**
 * The persona the player uses in the open story (name + avatar). The chat page provides it around
 * the message list so the DM thread can show it beside the player's own bubbles; null elsewhere
 * (no avatar column on that side).
 */
export const PlayerAvatarContext = createContext<PlayerFace | null>(null);

/**
 * Face of the story's persona: the story row's name at once, the avatar once GET /api/personas
 * answers. A failed fetch keeps the initial letter (the avatar is decoration, not worth an error).
 */
export function usePersonaFace(personaId: number | null, fallbackName: string): PlayerFace | null {
  const [personas, setPersonas] = useState<PersonaOut[] | null>(null);

  useEffect(() => {
    if (personaId === null) return;
    let alive = true;
    api
      .listPersonas()
      .then((list) => alive && setPersonas(list))
      .catch(() => undefined);
    return () => {
      alive = false;
    };
  }, [personaId]);

  return useMemo(
    () => (personaId === null ? null : personaFace(personas, personaId, fallbackName)),
    [personas, personaId, fallbackName],
  );
}
