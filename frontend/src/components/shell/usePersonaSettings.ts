import { useCallback, useEffect, useMemo, useState } from "react";
import { api, errorMessage } from "../../api/client";
import type { AppSettings, PersonaOut } from "../../types";

export interface PersonaSettingsState {
  /** null while loading (or after a failed first load). */
  personas: PersonaOut[] | null;
  settings: AppSettings | null;
  /** Error of the last load, null when it worked. */
  error: string | null;
  /** The persona new stories use: the saved default, else the first persona (as the backend does). */
  activePersona: PersonaOut | null;
  reload: () => void;
  /** PUT /api/settings with only the changed fields (the server keeps the rest); rejects with a readable message. */
  save: (patch: Partial<AppSettings>) => Promise<void>;
}

/** Personas and app settings (default persona, default chat model) shared by the hub header and its modal. */
export function usePersonaSettings(): PersonaSettingsState {
  const [personas, setPersonas] = useState<PersonaOut[] | null>(null);
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let alive = true;
    void (async () => {
      try {
        const [p, s] = await Promise.all([
          api.listPersonas(),
          // Settings are optional for the header: without them the first persona is the default.
          api.getSettings().catch(() => null),
        ]);
        if (!alive) return;
        setPersonas(p);
        setSettings(s);
        setError(null);
      } catch (e) {
        if (alive) setError(errorMessage(e));
      }
    })();
    return () => {
      alive = false;
    };
  }, [tick]);

  const reload = useCallback(() => setTick((n) => n + 1), []);

  const save = useCallback(
    async (patch: Partial<AppSettings>) => {
      // Send only the patch: the backend merges unset fields. Resending the whole local copy would
      // wipe the saved model when the settings failed to load, overwrite a newer value from another
      // tab, or re-check a saved model that Ollama no longer lists. JSON drops undefined keys.
      try {
        const saved = await api.putSettings(patch as AppSettings);
        setSettings(saved);
      } catch (e) {
        throw new Error(errorMessage(e));
      }
    },
    [],
  );

  const activePersona = useMemo(() => {
    if (!personas || personas.length === 0) return null;
    const wanted = settings?.default_persona_id ?? null;
    return personas.find((p) => p.id === wanted) ?? personas[0] ?? null;
  }, [personas, settings]);

  return { personas, settings, error, activePersona, reload, save };
}
