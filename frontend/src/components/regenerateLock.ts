import { createContext } from "react";

/**
 * F42 (docs/coins.md §10.3): why "Tạo lại câu trả lời" cannot run because of coins ("Cần 6 coin để tạo
 * lại."), or null. The chat page provides it around the message list; other places leave it null.
 */
export const RegenerateCoinLockContext = createContext<string | null>(null);
