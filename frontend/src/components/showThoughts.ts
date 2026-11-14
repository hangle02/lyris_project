import { createContext } from "react";

/**
 * Phase 4 (B, phase4.md §12): whether the open story shows the character's thought cards
 * (`Story.show_thoughts`, saved per story on the server). The chat page provides it around the message
 * list; everywhere else (Studio test chat, previews) it stays true: the author always reads thoughts.
 */
export const ShowThoughtsContext = createContext<boolean>(true);
