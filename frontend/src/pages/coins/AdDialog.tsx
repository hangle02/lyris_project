import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { ApiError, api, errorMessage, errorTechnical } from "../../api/client";
import { IconCoin } from "../../components/icons";
import { Button, InlineAlert, Modal } from "../../components/ui";
import { walletStore } from "../../hooks/useWallet";
import { COIN_COPY } from "../../lib/coinCopy";
import {
  AD_START,
  adErrorText,
  adReducer,
  claimLocked,
  closeAction,
  countdownLive,
  secondsLeft,
} from "./missionsLogic";

/** A picture that ships with Lyris (a template character), served by the app itself: nothing from outside. */
const PROMO_IMAGE = "/api/templates/ha-vy/image";

/**
 * "Quảng cáo mẫu" (F45, docs/coins.md §6.2, wiki/screens/missions.md): says plainly it is a sample ad of Lyris itself,
 * counts down, and unlocks "Nhận 5 coin" when the time is up. The server checks the time again (its own clock). Closing
 * before the claim tells the server to cancel that view. Full screen on phones, a 420px dialog from 640px.
 */
export function AdDialog({
  open,
  onClose,
  onClaimed,
}: {
  open: boolean;
  onClose: () => void;
  onClaimed: (amount: number) => void;
}) {
  const [state, dispatch] = useReducer(adReducer, AD_START);
  const [now, setNow] = useState(() => Date.now());
  const [run, setRun] = useState(0);
  const [live, setLive] = useState("");
  const stateRef = useRef(state);
  stateRef.current = state;

  // Start a view each time the dialog opens (or "Xem" again after an expired view).
  useEffect(() => {
    if (!open) return;
    let alive = true;
    dispatch({ type: "reset" });
    setLive("");
    api
      .startAd()
      .then((res) => {
        if (!alive) return;
        const at = Date.now();
        setNow(at); // the countdown starts from this moment ("Còn 15 giây"), not from when the dialog opened
        dispatch({ type: "started", adId: res.ad_id, seconds: res.seconds, now: at });
      })
      .catch((e: unknown) => {
        if (!alive) return;
        const code = e instanceof ApiError ? e.code : null;
        dispatch({ type: "failed", text: adErrorText(code, errorMessage(e)), technical: errorTechnical(e) });
      });
    return () => {
      alive = false;
    };
  }, [open, run]);

  // Tick while counting (the server keeps the real time; this only unlocks the button).
  useEffect(() => {
    if (!open || state.phase !== "counting") return;
    const t = window.setInterval(() => {
      const at = Date.now();
      setNow(at);
      dispatch({ type: "tick", now: at });
    }, 250);
    return () => window.clearInterval(t);
  }, [open, state.phase]);

  const left = secondsLeft(state, now);
  useEffect(() => {
    if (state.phase !== "counting") return;
    const said = countdownLive(left);
    if (said) setLive(said);
  }, [left, state.phase]);

  const close = useCallback(() => {
    const action = closeAction(stateRef.current);
    if (action.kind === "cancel") void api.cancelAd(action.adId).catch(() => {});
    onClose();
  }, [onClose]);

  const claim = async () => {
    const s = stateRef.current;
    if (s.phase !== "ready" && !(s.phase === "counting" && !claimLocked(s, Date.now()))) return;
    if (s.phase === "counting") dispatch({ type: "tick", now: Date.now() });
    dispatch({ type: "claim" });
    try {
      const res = await api.claimAd(s.adId);
      walletStore.set(res.wallet);
      dispatch({ type: "claimed", amount: res.amount });
      onClaimed(res.amount);
    } catch (e) {
      const code = e instanceof ApiError ? e.code : null;
      if (code === "ad_not_finished") dispatch({ type: "notFinished", now: Date.now() });
      else if (code === "ad_expired") dispatch({ type: "expired" });
      else dispatch({ type: "failed", text: adErrorText(code, errorMessage(e)), technical: errorTechnical(e) });
    }
  };

  const locked = claimLocked(state, now);
  const shownLeft = state.phase === "counting" ? left : 0;
  const done = state.phase === "ready" || state.phase === "claiming" || state.phase === "claimed";

  return (
    <Modal
      open={open}
      onClose={close}
      title={COIN_COPY.adTitle}
      description={COIN_COPY.adHonest}
      size="sm"
      className="max-sm:h-dvh max-sm:max-h-dvh max-sm:rounded-none sm:max-w-[420px]"
      footer={
        <>
          <Button size="sm" variant="secondary" onClick={close}>
            {COIN_COPY.close}
          </Button>
          {state.phase === "expired" ? (
            <Button size="sm" variant="primary" onClick={() => setRun((n) => n + 1)}>
              {COIN_COPY.watch}
            </Button>
          ) : (
            <Button
              size="sm"
              variant="primary"
              icon={<IconCoin />}
              disabled={locked}
              loading={state.phase === "claiming"}
              onClick={() => void claim()}
            >
              {COIN_COPY.adClaim}
            </Button>
          )}
        </>
      }
    >
      <div className="flex min-h-full flex-col justify-center gap-4">
        <figure className="overflow-hidden rounded-card border border-line bg-surface-2">
          <div aria-hidden="true" className="flex flex-col gap-3 border-b border-line bg-bg px-4 py-4">
            <div className="flex items-center gap-2">
              <img
                src={PROMO_IMAGE}
                alt=""
                draggable={false}
                className="size-8 shrink-0 rounded-full object-cover"
              />
              <span className="text-[14px] font-semibold text-fg">{COIN_COPY.adPromoName}</span>
            </div>
            <p className="font-story text-[15px] leading-relaxed text-muted italic">{COIN_COPY.adPromoNarration}</p>
            <p className="w-fit max-w-full rounded-card border border-edge bg-surface px-4 py-2.5 font-story text-[15px] font-medium text-dialogue">
              {COIN_COPY.adPromoLine}
            </p>
            <p className="rounded-r-control border-l-[3px] border-accent bg-[color-mix(in_oklab,var(--color-accent)_8%,var(--color-surface))] px-3.5 py-2.5 font-story text-[15px] leading-normal text-thought italic">
              {COIN_COPY.adPromoThought}
            </p>
          </div>
          <figcaption className="flex flex-col gap-1 px-4 py-3">
            <span className="text-[16px] leading-snug font-semibold text-fg">{COIN_COPY.adPromoTitle}</span>
            <span className="text-[14px] leading-relaxed text-prose">{COIN_COPY.adPromoText}</span>
          </figcaption>
        </figure>
        {state.phase === "expired" || state.phase === "error" ? (
          <InlineAlert
            tone="error"
            text={state.text}
            technical={state.phase === "error" ? state.technical : undefined}
          />
        ) : (
          <div className="flex flex-col gap-2">
            <p
              aria-hidden="true"
              data-ad-countdown
              className="text-[15px] leading-snug font-medium text-fg tabular-nums"
            >
              {state.phase === "starting"
                ? COIN_COPY.adStarting
                : done
                  ? COIN_COPY.adReady
                  : COIN_COPY.adLeft(shownLeft)}
            </p>
            <AdProgress state={state} now={now} />
            {state.phase === "counting" && state.note && (
              <p className="text-[14px] leading-snug text-muted">{state.note}</p>
            )}
          </div>
        )}
        <p role="status" aria-live="polite" className="sr-only">
          {done ? COIN_COPY.adReady : live}
        </p>
      </div>
    </Modal>
  );
}

/** A thin bar that fills as the sample ad plays. */
function AdProgress({ state, now }: { state: ReturnType<typeof adReducer>; now: number }) {
  const startRef = useRef<{ adId: number; at: number; span: number } | null>(null);
  let pct = 0;
  if (state.phase === "counting") {
    if (!startRef.current || startRef.current.adId !== state.adId || startRef.current.at + startRef.current.span !== state.endsAt) {
      startRef.current = { adId: state.adId, at: now, span: Math.max(1, state.endsAt - now) };
    }
    const { at, span } = startRef.current;
    pct = Math.min(100, Math.max(0, ((now - at) / span) * 100));
  } else if (state.phase !== "starting") {
    pct = 100;
  }
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-3" aria-hidden="true">
      <div
        className="h-full rounded-full bg-accent-2 transition-[width] duration-300 ease-linear motion-reduce:transition-none"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}
