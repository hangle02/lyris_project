import { createContext } from "react";

/**
 * Avatar URL of the current story's character. App provides it around the message list so the DM
 * thread can show the real image without threading a prop through every layer.
 */
export const CharacterAvatarContext = createContext<string | null>(null);
