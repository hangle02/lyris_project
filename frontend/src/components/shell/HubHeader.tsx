import { useEffect, useRef, useState } from "react";
import { reloadAccountOnRecovery } from "../../hooks/accountLogic";
import { getAccountSnapshot, refreshAccount, useAccount } from "../../hooks/useAccount";
import { useHealth } from "../../hooks/useHealth";
import { useWallet } from "../../hooks/useWallet";
import { COIN_COPY } from "../../lib/coinCopy";
import { formatCoinNumber, noteWalletFrom, showsCoins } from "../../lib/coins";
import { initialOverlayOpen } from "../../lib/overlayParam";
import { routeHref } from "../../lib/router";
import { ThemeToggle } from "../../theme";
import { Avatar } from "../Avatar";
import { Wordmark } from "../brand";
import { IconCoin } from "../icons";
import { cx } from "../ui/logic";
import { AccountSheet } from "./AccountSheet";
import { SHELL_CONTAINER } from "./layout";
import { usePersonaSettings } from "./usePersonaSettings";

/**
 * Header of the hub tabs (DESIGN.md §5.1, docs/accounts.md §5): the Lyris wordmark on the left; the
 * theme switch and the account avatar (opens the "Tài khoản" sheet) on the right. Glass, sticky,
 * below the iPhone status bar. The machine status lives in that sheet; the avatar only carries a
 * small red dot when the machine cannot answer, so failing replies have a visible reason (plain
 * words in its label and tooltip, Phase 3b).
 *
 * F42 (docs/coins.md §10.1): a member sees a small coin chip before the theme switch (balance, opens
 * "Ví coin"). The owner and a server with coins off have no chip.
 */
export function HubHeader() {
  const health = useHealth();
  const accountState = useAccount();
  const personaState = usePersonaSettings();
  const [open, setOpen] = useState(() => initialOverlayOpen("system") || initialOverlayOpen("about"));

  const level = health.level;
  const down = level === "down";
  const account = accountState.account;

  // The backend became reachable while no account is loaded (e.g. the first load failed while it was
  // starting): load it now, so the avatar and the hub invite appear without a navigation.
  const prevLevel = useRef<string | null>(null);
  useEffect(() => {
    const previous = prevLevel.current;
    prevLevel.current = level;
    if (reloadAccountOnRecovery(previous, level, getAccountSnapshot())) void refreshAccount();
  }, [level]);

  const openSheet = () => {
    personaState.reload();
    void accountState.refresh();
    setOpen(true);
  };

  return (
    <header className="glass sticky top-0 z-30 pt-safe">
      <div className={cx(SHELL_CONTAINER, "flex h-14 items-center gap-2")}>
        <a href={routeHref({ name: "hub" })} className="-ml-1 flex min-h-11 min-w-11 shrink-0 items-center rounded-control px-1 pb-0.5">
          <Wordmark size={27} />
        </a>
        <div className="ml-auto flex shrink-0 items-center gap-0.5">
          <CoinChip />
          <ThemeToggle />
          <button
            type="button"
            onClick={openSheet}
            aria-label={
              (account ? `Tài khoản: ${account.display_name}. ` : "") +
              (down ? "Nhân vật tạm thời chưa trả lời được. " : "") +
              "Mở tài khoản"
            }
            title={down ? health.label : account ? `${account.display_name} (@${account.handle})` : "Tài khoản"}
            className="relative inline-flex h-11 w-11 items-center justify-center rounded-full transition-colors duration-150 hover:bg-surface-2"
          >
            <Avatar name={account?.display_name ?? "?"} url={account?.avatar_url} size={32} />
            {down && (
              <span
                aria-hidden="true"
                className="absolute top-1.5 right-1.5 h-2.5 w-2.5 rounded-full bg-danger ring-2 ring-bg"
              />
            )}
          </button>
        </div>
      </div>
      <AccountSheet
        open={open}
        onClose={() => setOpen(false)}
        healthLevel={level}
        accountState={accountState}
        personaState={personaState}
        initialView={initialOverlayOpen("about") ? "about" : "main"}
      />
    </header>
  );
}

/** The member's balance on the hub header; a 44px tap area around a 32px pill. */
function CoinChip() {
  const { wallet } = useWallet();
  if (!showsCoins(wallet) || !wallet) return null;
  const n = formatCoinNumber(wallet.balance);
  return (
    <a
      href="#/coins"
      onClick={() => noteWalletFrom("header")}
      aria-label={COIN_COPY.chipLabel(n)}
      title={COIN_COPY.walletTitle}
      className="group inline-flex h-11 min-w-11 shrink-0 items-center justify-center rounded-full px-0.5"
    >
      <span className="inline-flex h-8 items-center gap-1.5 rounded-full bg-surface-2 pr-3 pl-2 text-[14px] font-semibold text-fg tabular-nums transition-colors duration-150 group-hover:bg-surface-3">
        <IconCoin className="text-[17px] text-accent-2" />
        {n}
      </span>
    </a>
  );
}
