import { useCallback, useEffect, useId, useRef, useState } from "react";
import { ApiError, api, errorMessage, errorTechnical } from "../../api/client";
import { IconCoin } from "../../components/icons";
import { SubpageHeader } from "../../components/shell/SubpageHeader";
import { Button, CONTROL_CLASS, Card, Field, InlineAlert, Modal, Skeleton, cx } from "../../components/ui";
import { refreshWallet, useWallet, walletStore } from "../../hooks/useWallet";
import { COIN_COPY } from "../../lib/coinCopy";
import { formatCoins } from "../../lib/coins";
import { replaceRoute } from "../../lib/router";
import { track } from "../../lib/track";
import {
  checkCodeInput,
  formatVnd,
  knownPacks,
  packBonus,
  packCode,
  packDialogTitle,
  packTitle,
  redeemErrorText,
  redeemedText,
  takeTopUpFrom,
} from "./topupLogic";
import type { CoinPack } from "./topupLogic";

type PacksState =
  | { kind: "loading" }
  | { kind: "ready"; packs: CoinPack[] }
  | { kind: "error"; text: string; technical: string | null };

/** One planned pack: coins, the bonus (when there is one) and the planned price. Same height as its row. */
function PackCard({ pack, onOpen }: { pack: CoinPack; onOpen: (p: CoinPack) => void }) {
  const bonus = packBonus(pack);
  return (
    <li className="flex min-w-0">
      <button
        type="button"
        onClick={() => onOpen(pack)}
        aria-haspopup="dialog"
        className="flex w-full min-w-0 flex-col items-start gap-1 rounded-card border border-edge bg-surface p-4 text-left transition-colors duration-150 hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      >
        <span className="flex items-center gap-1.5 text-[18px] leading-tight font-semibold text-fg tabular-nums">
          <IconCoin aria-hidden="true" className="shrink-0 text-[18px] text-accent-2" />
          {packTitle(pack)}
        </span>
        <span className="min-h-5 text-[13px] leading-snug font-medium text-accent-2">{bonus ?? ""}</span>
        <span className="mt-auto pt-2 text-[16px] leading-tight font-semibold text-fg tabular-nums">{formatVnd(pack.price_vnd)}</span>
        <span className="text-[12px] leading-tight text-muted">{COIN_COPY.packPrice}</span>
      </button>
    </li>
  );
}

/**
 * "Nạp coin" (`#/coins/top-up`, F43, docs/coins.md §4, wiki/screens/top-up.md). Test mode: Lyris sells nothing; the
 * member types a top-up code the manager gave them. The planned packs only open a "Giá dự kiến" note with "Đóng" (no
 * payment, no contact button: a priced pack must not become a way to sell coins outside the app).
 */
export function TopUpPage() {
  const { wallet } = useWallet();
  const [packs, setPacks] = useState<PacksState>({ kind: "loading" });
  const [code, setCode] = useState("");
  const [sending, setSending] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const [open, setOpen] = useState<CoinPack | null>(null);
  const tracked = useRef(false);
  const codeId = useId();

  const loadPacks = useCallback(async () => {
    setPacks({ kind: "loading" });
    try {
      const out = await api.coinPacks();
      setPacks({ kind: "ready", packs: knownPacks(out.packs) });
    } catch (e) {
      setPacks({ kind: "error", text: errorMessage(e), technical: errorTechnical(e) });
    }
  }, []);

  useEffect(() => {
    document.title = `${COIN_COPY.topUpTitle} · Lyris`;
    refreshWallet();
    void loadPacks();
  }, [loadPacks]);

  useEffect(() => {
    if (tracked.current) return;
    tracked.current = true;
    track("topup_viewed", { from: takeTopUpFrom() });
  }, []);

  // Coins turned off on this server: there is nothing to top up.
  useEffect(() => {
    if (wallet && !wallet.enabled) replaceRoute({ name: "hub" });
  }, [wallet]);

  const redeem = async () => {
    if (sending) return;
    setDone(null);
    const checked = checkCodeInput(code);
    if (!checked.ok) {
      setProblem(checked.text);
      return;
    }
    setSending(true);
    setProblem(null);
    try {
      const res = await api.redeemCode(checked.code);
      walletStore.set(res.wallet);
      setCode("");
      setDone(redeemedText(res.amount));
    } catch (e) {
      const status = e instanceof ApiError ? e.status : 0;
      const errCode = e instanceof ApiError ? e.code : null;
      setProblem(redeemErrorText(status, errCode, errorMessage(e)));
    } finally {
      setSending(false);
    }
  };

  const openPack = (p: CoinPack) => {
    track("topup_pack_selected", { pack: packCode(p) });
    setOpen(p);
  };

  const owner = wallet?.unlimited === true;

  return (
    <div className="min-h-dvh bg-bg">
      <SubpageHeader backHref="#/coins" backLabel={COIN_COPY.topUpBack} title={COIN_COPY.topUpTitle}>
        {wallet && !owner && (
          <span className="text-[13px] text-muted tabular-nums" aria-live="polite">
            {formatCoins(wallet.balance)}
          </span>
        )}
      </SubpageHeader>
      <main className="mx-auto flex w-full max-w-[720px] flex-col gap-6 px-4 pt-5 pb-[max(2rem,env(safe-area-inset-bottom))]">
        {owner ? (
          <Card className="flex flex-col gap-3">
            <div className="flex items-center gap-3">
              <IconCoin className="shrink-0 text-[24px] text-accent-2" />
              <p className="text-[15px] leading-snug text-fg">{COIN_COPY.ownerNote}</p>
            </div>
            <a href="#/admin" className="self-start text-[15px] font-medium text-accent underline-offset-4 hover:underline">
              {COIN_COPY.ownerTopUpLink}
            </a>
          </Card>
        ) : (
          <>
            <InlineAlert tone="info" text={COIN_COPY.topUpTestMode} />
            <form
              noValidate
              onSubmit={(e) => {
                e.preventDefault();
                void redeem();
              }}
            >
              <Field
                label={COIN_COPY.codeLabel}
                htmlFor={codeId}
                error={problem ?? undefined}
                errorId={`${codeId}-error`}
                hintId={`${codeId}-done`}
                hint={done ? <span className="font-medium text-ok">{done}</span> : undefined}
              >
                <div className="flex min-w-0 gap-2">
                  <input
                    id={codeId}
                    aria-label={COIN_COPY.codeLabel}
                    aria-invalid={problem ? true : undefined}
                    aria-describedby={problem ? `${codeId}-error` : done ? `${codeId}-done` : undefined}
                    className={cx(CONTROL_CLASS, "flex-1 uppercase placeholder:normal-case")}
                    value={code}
                    onChange={(e) => {
                      setCode(e.target.value);
                      setProblem(null);
                      setDone(null);
                    }}
                    placeholder={COIN_COPY.codePlaceholder}
                    autoComplete="off"
                    autoCapitalize="characters"
                    autoCorrect="off"
                    spellCheck={false}
                    maxLength={40}
                    disabled={sending}
                  />
                  <Button type="submit" variant="primary" loading={sending} className="shrink-0">
                    {COIN_COPY.redeem}
                  </Button>
                </div>
              </Field>
              <p role="status" aria-live="polite" className="sr-only">
                {done ?? ""}
              </p>
            </form>
            <section aria-labelledby="topup-packs" className="flex flex-col gap-3">
              <h2 id="topup-packs" className="text-[16px] font-semibold text-fg">
                {COIN_COPY.packsHeading}
              </h2>
              {packs.kind === "loading" ? (
                <div aria-busy="true" className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  {[0, 1, 2, 3].map((i) => (
                    <Skeleton key={i} shape="card" height={132} />
                  ))}
                </div>
              ) : packs.kind === "error" ? (
                <InlineAlert
                  tone="error"
                  text={`${COIN_COPY.packsError} ${packs.text}`}
                  technical={packs.technical}
                  onRetry={() => void loadPacks()}
                  actionLabel={COIN_COPY.retry}
                />
              ) : (
                <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  {packs.packs.map((p) => (
                    <PackCard key={p.id} pack={p} onOpen={openPack} />
                  ))}
                </ul>
              )}
            </section>
          </>
        )}
      </main>
      <Modal
        open={open !== null}
        onClose={() => setOpen(null)}
        title={open ? packDialogTitle(open) : ""}
        size="sm"
        footer={
          <Button size="sm" variant="primary" onClick={() => setOpen(null)}>
            {COIN_COPY.close}
          </Button>
        }
      >
        <p className="text-[15px] leading-relaxed text-prose">{COIN_COPY.packDialogText}</p>
      </Modal>
    </div>
  );
}
