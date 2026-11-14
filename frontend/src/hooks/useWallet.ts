import { useEffect, useSyncExternalStore } from "react";
import { api } from "../api/client";
import { createWalletStore } from "../lib/coins";
import type { WalletSnapshot } from "../lib/coins";

/**
 * The one shared coin wallet (F42, docs/coins.md §8): header chip, "Tài khoản" sheet, "Ví coin" and
 * the chat composers read it, so a reply, a 402 or a refresh in one place shows everywhere at once.
 */
export const walletStore = createWalletStore(() => api.getWallet());

/** Re-reads GET /api/coins/wallet (after a reply, a 402, a gift, coming back to the tab). */
export function refreshWallet(): void {
  void walletStore.refresh();
}

/** The wallet snapshot; loads it on first use. */
export function useWallet(): WalletSnapshot {
  const snap = useSyncExternalStore(walletStore.subscribe, walletStore.get, walletStore.get);
  useEffect(() => {
    const now = walletStore.get();
    if (!now.wallet && !now.loading) void walletStore.refresh();
  }, []);
  return snap;
}
