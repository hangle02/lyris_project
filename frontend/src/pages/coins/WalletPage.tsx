import { useCallback, useEffect, useRef, useState } from "react";
import { api, errorMessage, errorTechnical } from "../../api/client";
import { IconCoin } from "../../components/icons";
import { SubpageHeader } from "../../components/shell/SubpageHeader";
import { Button, Card, InlineAlert, Skeleton } from "../../components/ui";
import { cx } from "../../components/ui/logic";
import { refreshWallet, useWallet } from "../../hooks/useWallet";
import { COIN_COPY } from "../../lib/coinCopy";
import {
  composerCoinLock,
  formatCoinNumber,
  formatDelta,
  groupHistory,
  historyTime,
  takeWalletFrom,
} from "../../lib/coins";
import type { CoinHistoryItem } from "../../lib/coins";
import { navigate, replaceRoute } from "../../lib/router";
import { track } from "../../lib/track";
import { noteMissionsFrom } from "./missionsLogic";
import { noteTopUpFrom } from "./topupLogic";

interface HistoryState {
  items: CoinHistoryItem[];
  next: number | null;
  loading: boolean;
  error: { text: string; technical: string | null } | null;
}

/**
 * "Ví coin" (`#/coins`, F42, docs/coins.md §10.2, wiki/screens/coin-wallet.md): the member's balance,
 * the price of a reply, "Nạp coin" / "Nhiệm vụ", and the history (30 rows a page, neighbouring replies
 * of one story on one day folded into one row). The owner sees one line; coins off sends to the hub.
 */
export function WalletPage() {
  const { wallet, error: walletError, loading: walletLoading } = useWallet();
  const [history, setHistory] = useState<HistoryState>({ items: [], next: null, loading: true, error: null });
  const tracked = useRef(false);

  const loadHistory = useCallback(async (before?: number) => {
    setHistory((h) => ({ ...h, loading: true, error: null }));
    try {
      const page = await api.coinHistory(before);
      setHistory((h) => ({
        items: before === undefined ? page.items : [...h.items, ...page.items],
        next: page.next,
        loading: false,
        error: null,
      }));
    } catch (e) {
      setHistory((h) => ({ ...h, loading: false, error: { text: errorMessage(e), technical: errorTechnical(e) } }));
    }
  }, []);

  useEffect(() => {
    document.title = `${COIN_COPY.walletTitle} · Lyris`;
    refreshWallet();
    void loadHistory();
  }, [loadHistory]);

  useEffect(() => {
    if (tracked.current) return;
    tracked.current = true;
    track("wallet_viewed", { from: takeWalletFrom() });
  }, []);

  // Coins turned off on this server: there is no wallet to show.
  useEffect(() => {
    if (wallet && !wallet.enabled) replaceRoute({ name: "hub" });
  }, [wallet]);

  const owner = wallet?.unlimited === true;
  const out = composerCoinLock(wallet).locked;
  const groups = groupHistory(history.items);
  const now = new Date();

  return (
    <div className="min-h-dvh bg-bg">
      <SubpageHeader backHref="#/" backLabel={COIN_COPY.walletBack} title={COIN_COPY.walletTitle} />
      <main className="mx-auto flex w-full max-w-[560px] flex-col gap-6 px-4 pt-5 pb-[max(2rem,env(safe-area-inset-bottom))]">
        {!wallet && walletError ? (
          <InlineAlert tone="error" text={COIN_COPY.loadError} onRetry={refreshWallet} actionLabel={COIN_COPY.retry} />
        ) : !wallet ? (
          <div aria-busy="true" className="flex flex-col gap-4">
            <Skeleton shape="card" height={148} />
            <Skeleton shape="pill" height={44} />
            <Skeleton shape="text" lines={4} height={18} />
          </div>
        ) : owner ? (
          <Card>
            <div className="flex items-center gap-3">
              <IconCoin className="shrink-0 text-[24px] text-accent-2" />
              <p className="text-[15px] leading-snug text-fg">{COIN_COPY.ownerNote}</p>
            </div>
          </Card>
        ) : (
          <>
            <Card className="flex flex-col gap-3">
              <div className="flex items-center gap-2 text-[14px] text-muted">
                <IconCoin className="text-[20px] text-accent-2" />
                {COIN_COPY.balanceCaption}
              </div>
              <p className="flex items-baseline gap-2" aria-live="polite" aria-busy={walletLoading || undefined}>
                <span data-coin-balance className="text-[40px] leading-none font-semibold text-fg tabular-nums">
                  {formatCoinNumber(wallet.balance)}
                </span>
                <span className="text-[16px] text-muted">{COIN_COPY.unit}</span>
              </p>
              <p className="text-[14px] leading-snug text-muted">{COIN_COPY.pricePerReply}</p>
              {out && (
                <p role="status" className="rounded-control bg-surface-2 px-3 py-2 text-[14px] leading-snug text-fg">
                  {COIN_COPY.walletOut}
                </p>
              )}
            </Card>
            <div className="flex gap-3">
              <Button
                variant="primary"
                className="min-w-0 flex-1"
                onClick={() => {
                  noteTopUpFrom("wallet");
                  navigate("#/coins/top-up");
                }}
              >
                {COIN_COPY.topUp}
              </Button>
              <Button
                variant="secondary"
                className="min-w-0 flex-1"
                onClick={() => {
                  noteMissionsFrom("wallet");
                  navigate("#/missions");
                }}
              >
                {COIN_COPY.missions}
              </Button>
            </div>
            <section aria-labelledby="coin-history" className="flex flex-col gap-2">
              <h2 id="coin-history" className="text-[16px] font-semibold text-fg">
                {COIN_COPY.history}
              </h2>
              {history.error && history.items.length === 0 ? (
                <InlineAlert
                  tone="error"
                  text={history.error.text}
                  technical={history.error.technical}
                  onRetry={() => void loadHistory()}
                  actionLabel={COIN_COPY.retry}
                />
              ) : history.loading && history.items.length === 0 ? (
                <div aria-busy="true" className="flex flex-col gap-3 py-2">
                  {[0, 1, 2, 3].map((i) => (
                    <Skeleton key={i} shape="text" height={18} />
                  ))}
                </div>
              ) : groups.length === 0 ? (
                <p className="py-3 text-[14px] text-muted">{COIN_COPY.historyEmpty}</p>
              ) : (
                <ul className="flex flex-col divide-y divide-line rounded-card bg-surface px-4">
                  {groups.map((g) => (
                    <li key={g.key} className="flex min-h-14 items-center gap-3 py-2.5">
                      <span className="flex min-w-0 flex-1 flex-col">
                        <span className="text-[15px] leading-snug text-fg [overflow-wrap:anywhere]">{g.label}</span>
                        <span className="text-[13px] leading-snug text-muted">{historyTime(g.created_at, now)}</span>
                      </span>
                      <span
                        className={cx(
                          "shrink-0 text-[15px] font-semibold tabular-nums",
                          g.delta > 0 ? "text-ok" : "text-muted",
                        )}
                      >
                        {formatDelta(g.delta)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
              {history.error && history.items.length > 0 && (
                <InlineAlert tone="error" text={history.error.text} technical={history.error.technical} />
              )}
              {history.next !== null && (
                <Button
                  variant="ghost"
                  className="self-center"
                  loading={history.loading}
                  onClick={() => void loadHistory(history.next ?? undefined)}
                >
                  {COIN_COPY.more}
                </Button>
              )}
            </section>
          </>
        )}
      </main>
    </div>
  );
}
