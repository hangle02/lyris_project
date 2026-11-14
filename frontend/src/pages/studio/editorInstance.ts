// Which CardEditor instance "#/studio/new" and "#/studio/<id>" should render. A different card id
// remounts the editor (new key), with one exception: the first save of a new card moves the address
// from "#/studio/new" to "#/studio/<new id>", and that same editor keeps going (test chat, tabs).

export interface EditorInstance {
  /** React key of the mounted CardEditor. */
  key: number;
  /** The card id that editor was mounted for (null = new card). */
  cardId: number | null;
}

/** The id an editor adopted after its first save, tagged with that editor's key. */
export interface AdoptedId {
  key: number;
  id: number;
}

/**
 * The editor to render for `cardId`. Keeps the current instance only for the one move from "new" to
 * the id this very instance created; any other change (Nhân bản then Back, another card, back to
 * "new") mounts a fresh editor so its saved id, loaded card and unsaved guard all match the address.
 * Pure: safe to call during render (StrictMode renders twice).
 */
export function nextEditorInstance(
  inst: EditorInstance,
  cardId: number | null,
  adopted: AdoptedId | null,
): EditorInstance {
  if (cardId === inst.cardId) return inst;
  const keep =
    inst.cardId === null && cardId !== null && adopted !== null && adopted.key === inst.key && adopted.id === cardId;
  return { key: keep ? inst.key : inst.key + 1, cardId };
}
