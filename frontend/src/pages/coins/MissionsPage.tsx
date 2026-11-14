import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, api, errorMessage, errorTechnical } from "../../api/client";
import { IconCoin } from "../../components/icons";
import { SubpageHeader } from "../../components/shell/SubpageHeader";
import { Button, Card, InlineAlert, Skeleton, Toast } from "../../components/ui";
import { refreshWallet, useWallet, walletStore } from "../../hooks/useWallet";
import { COIN_COPY } from "../../lib/coinCopy";
import { formatCoins } from "../../lib/coins";
import { replaceRoute } from "../../lib/router";
import { track } from "../../lib/track";
import { AdDialog } from "./AdDialog";
import { adErrorText, capReached, earnedText, knownMissions, missionRow, takeMissionsFrom } from "./missionsLogic";
import type { MissionRow, MissionsOut } from "./missionsLogic";

type LoadState =
  | { kind: "loading" }
  | { kind: "ready"; data: MissionsOut }
  | { kind: "error"; text: string; technical: string | null };

/** One mission: name, reward, progress ("1/3") and its button (or "Đã nhận"). Same height as its siblings. */
function MissionCard({
  row,
  busy,
  onWatch,
  onClaim,
}: {
  row: MissionRow;
  busy: boolean;
  onWatch: () => void;
  onClaim: () => void;
}) {
  const action = row.action;
  return (
    <li className="flex min-w-0">
      <Card className="flex w-full min-w-0 items-center gap-3" data-mission={row.id}>
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <h2 className="text-[15px] leading-snug font-semibold text-fg [overflow-wrap:anywhere]">{row.title}</h2>
          <p className="flex flex-wrap items-baseline gap-x-2 text-[14px] leading-snug">
            <span className="font-medium text-accent-2">{row.reward}</span>
            <span className="text-faint" aria-hidden="true">
              ·
            </span>
            <span className="text-muted tabular-nums" data-mission-progress>
              {row.progress}
            </span>
          </p>
          {row.note && <p className="text-[13px] leading-snug text-muted">{row.note}</p>}
        </div>
        <div className="shrink-0">
          {action?.kind === "watch" && (
            <Button size="sm" variant="primary" disabled={action.disabled} onClick={onWatch} aria-haspopup="dialog">
              {action.label}
            </Button>
          )}
          {action?.kind === "claim" && (
            <Button size="sm" variant="primary" loading={busy} disabled={action.disabled} onClick={onClaim}>
              {action.label}
            </Button>
          )}
          {action?.kind === "done" && (
            <span className="inline-flex h-9 items-center rounded-full bg-surface-2 px-3 text-[14px] font-medium text-muted max-sm:h-11">
              {action.label}
            </span>
          )}
        </div>
      </Card>
    </li>
  );
}

/**
 * "Nhiệm vụ hôm nay" (`#/missions`, F45, docs/coins.md §6, wiki/screens/missions.md): up to 30 more coins a day — the
 * sample ad (+5, three times), three different characters (+10), 20 turns (+5). Everything starts over at 0:00
 * Vietnam time (the server decides the day). The owner has no missions; coins turned off sends to the hub.
 */
export function MissionsPage() {
  const { wallet } = useWallet();
  const [load, setLoad] = useState<LoadState>({ kind: "loading" });
  const [adOpen, setAdOpen] = useState(false);
  const [claiming, setClaiming] = useState<string | null>(null);
  const [problem, setProblem] = useState<{ text: string; technical: string | null } | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const tracked = useRef(false);

  const reload = useCallback(async (quiet = false) => {
    if (!quiet) setLoad({ kind: "loading" });
    try {
      const data = await api.missions();
      setLoad({ kind: "ready", data });
    } catch (e) {
      if (!quiet) setLoad({ kind: "error", text: errorMessage(e), technical: errorTechnical(e) });
    }
  }, []);

  useEffect(() => {
    document.title = `${COIN_COPY.missionsTitle} · Lyris`;
    refreshWallet();
    void reload();
  }, [reload]);

  useEffect(() => {
    if (tracked.current) return;
    tracked.current = true;
    track("missions_viewed", { from: takeMissionsFrom() });
  }, []);

  // Back to the tab (maybe after 0:00): fresh progress.
  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === "visible") void reload(true);
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => document.removeEventListener("visibilitychange", onVisible);
  }, [reload]);

  useEffect(() => {
    if (wallet && !wallet.enabled) replaceRoute({ name: "hub" });
  }, [wallet]);

  const claim = async (mission: "characters" | "turns") => {
    if (claiming) return;
    setClaiming(mission);
    setProblem(null);
    try {
      const res = await api.claimMission(mission);
      walletStore.set(res.wallet);
      setToast(COIN_COPY.gained(res.amount));
    } catch (e) {
      const code = e instanceof ApiError ? e.code : null;
      setProblem({ text: adErrorText(code, errorMessage(e)), technical: errorTechnical(e) });
    } finally {
      setClaiming(null);
      void reload(true);
    }
  };

  const owner = wallet?.unlimited === true || (load.kind === "ready" && load.data.unlimited);
  const data = load.kind === "ready" ? load.data : null;
  const rows = data ? knownMissions(data.missions).map((m) => missionRow(m, data)) : [];
  const adRow = data ? knownMissions(data.missions).find((m) => m.id === "ad") : undefined;

  return (
    <div className="min-h-dvh bg-bg">
      <SubpageHeader backHref="#/coins" backLabel={COIN_COPY.missionsBack} title={COIN_COPY.missionsTitle}>
        {wallet && !wallet.unlimited && (
          <span className="flex items-center gap-1 text-[13px] text-muted tabular-nums" aria-live="polite">
            <IconCoin aria-hidden="true" className="text-[15px] text-accent-2" />
            {formatCoins(wallet.balance)}
          </span>
        )}
      </SubpageHeader>
      <main className="mx-auto flex w-full max-w-[560px] flex-col gap-4 px-4 pt-5 pb-[max(2rem,env(safe-area-inset-bottom))]">
        {owner ? (
          <Card className="flex items-center gap-3">
            <IconCoin className="shrink-0 text-[24px] text-accent-2" />
            <p className="text-[15px] leading-snug text-fg">{COIN_COPY.ownerMissions}</p>
          </Card>
        ) : load.kind === "loading" ? (
          <div aria-busy="true" className="flex flex-col gap-3">
            <Skeleton shape="card" height={84} />
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} shape="card" height={92} />
            ))}
          </div>
        ) : load.kind === "error" ? (
          <InlineAlert
            tone="error"
            text={`${COIN_COPY.missionsError} ${load.text}`}
            technical={load.technical}
            onRetry={() => void reload()}
            actionLabel={COIN_COPY.retry}
          />
        ) : data ? (
          <>
            <Card className="flex flex-col gap-3">
              <p className="text-[16px] leading-snug font-semibold text-fg" data-missions-earned aria-live="polite">
                {earnedText(data)}
              </p>
              <div
                role="meter"
                aria-label={COIN_COPY.missionsMeter}
                aria-valuemin={0}
                aria-valuemax={data.cap}
                aria-valuenow={Math.min(data.cap, data.earned_today)}
                className="h-2 w-full overflow-hidden rounded-full bg-surface-3"
              >
                <div
                  className="h-full rounded-full bg-accent-2 transition-[width] duration-500 ease-out motion-reduce:transition-none"
                  style={{ width: `${Math.min(100, (data.earned_today / Math.max(1, data.cap)) * 100)}%` }}
                />
              </div>
              <p className="text-[13px] leading-snug text-muted">{COIN_COPY.missionsReset}</p>
            </Card>
            {problem && <InlineAlert tone="error" text={problem.text} technical={problem.technical} />}
            {adRow && adRow.remaining <= 0 && !capReached(data) && (
              <p className="text-[14px] leading-snug text-muted">{COIN_COPY.adLimit}</p>
            )}
            <ul className="grid auto-rows-fr grid-cols-1 gap-3">
              {rows.map((row) => (
                <MissionCard
                  key={row.id}
                  row={row}
                  busy={claiming === row.id}
                  onWatch={() => {
                    setProblem(null);
                    setAdOpen(true);
                  }}
                  onClaim={() => void claim(row.id === "turns" ? "turns" : "characters")}
                />
              ))}
            </ul>
          </>
        ) : null}
      </main>
      <AdDialog
        open={adOpen}
        onClose={() => {
          setAdOpen(false);
          void reload(true);
        }}
        onClaimed={(amount) => {
          setAdOpen(false);
          setToast(COIN_COPY.gained(amount));
          void reload(true);
        }}
      />
      <Toast text={toast} onDone={() => setToast(null)} />
    </div>
  );
}
