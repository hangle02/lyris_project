import { useCallback, useEffect, useMemo, useState } from "react";
import { api, errorMessage, errorTechnical } from "../../api/client";
import { IconChevronLeft, IconCoin } from "../../components/icons";
import { SHELL_CONTAINER } from "../../components/shell/layout";
import { TypingDots } from "../../components/TypingDots";
import { Button, ErrorDetails, Skeleton } from "../../components/ui";
import { cx } from "../../components/ui/logic";
import { useAuthAccount } from "../../hooks/useAuth";
import { useWallet } from "../../hooks/useWallet";
import { navigate, routeHref } from "../../lib/router";
import { previousRouteName, track } from "../../lib/track";
import { HotRowLink } from "./HotRows";
import { HOT_COPY, hotFrom, hotView, rewardNote, updatedLabel } from "./hotLogic";
import type { HotBoard } from "./hotLogic";

type Load = { kind: "loading" } | { kind: "ready"; board: HotBoard } | { kind: "error"; text: string; technical: string | null };

function RowsSkeleton() {
  return (
    <ul aria-hidden="true" className="divide-y divide-line overflow-hidden rounded-card bg-surface">
      {Array.from({ length: 8 }, (_, i) => (
        <li key={i} className="flex min-h-16 items-center gap-3 px-3 py-2.5 sm:px-4">
          <Skeleton shape="text" width={24} height={14} />
          <Skeleton shape="circle" width={44} height={44} />
          <span className="flex flex-1 flex-col gap-2">
            <Skeleton shape="text" width="55%" height={14} />
            <Skeleton shape="text" width="35%" height={12} />
          </span>
        </li>
      ))}
    </ul>
  );
}

/**
 * "Nhân vật hot" (`#/explore/hot`, F46, wiki/screens/hot-ranking.md): the 100 public characters with the most players
 * of all time, computed at most once an hour. Each row opens the character's profile. Members (coins on) see the
 * creator reward line (F44). The Khám phá tab stays lit.
 */
export function HotPage() {
  const [load, setLoad] = useState<Load>({ kind: "loading" });
  const { wallet } = useWallet();
  const me = useAuthAccount();

  const fetchBoard = useCallback(async () => {
    setLoad({ kind: "loading" });
    try {
      setLoad({ kind: "ready", board: await api.getHotBoard(100) });
    } catch (e) {
      setLoad({ kind: "error", text: errorMessage(e), technical: errorTechnical(e) });
    }
  }, []);

  useEffect(() => {
    void fetchBoard();
  }, [fetchBoard]);

  useEffect(() => {
    track("hot_board_viewed", { from: hotFrom(previousRouteName()) });
  }, []);

  const view = useMemo(() => (load.kind === "ready" ? hotView(load.board) : null), [load]);
  const updated = load.kind === "ready" ? updatedLabel(load.board.updated_at) : null;
  const note = rewardNote(wallet);
  const myHandle = (me?.handle ?? "").toLowerCase();

  return (
    <div className={cx(SHELL_CONTAINER, "flex max-w-[752px] flex-col gap-4 pt-3 sm:gap-5 sm:pt-5")}>
      <div className="-ml-2.5">
        <a
          href={routeHref({ name: "explore" })}
          aria-label={HOT_COPY.back}
          title={HOT_COPY.back}
          className="inline-flex h-11 w-11 items-center justify-center rounded-full text-[22px] text-muted transition-colors duration-150 hover:bg-surface-2 hover:text-fg focus-visible:outline-2 focus-visible:outline-accent"
        >
          <IconChevronLeft />
        </a>
      </div>
      <div className="flex flex-col gap-1">
        <h1 className="text-[24px] leading-tight font-semibold text-fg">{HOT_COPY.title}</h1>
        <p className="text-[15px] leading-snug text-muted">{HOT_COPY.subtitle}</p>
        {updated && (
          <p className="text-[13px] leading-snug text-faint tabular-nums" data-hot-updated>
            {updated}
          </p>
        )}
        {load.kind === "loading" && (
          <p className="pt-1 text-muted" role="status">
            <span className="sr-only">{HOT_COPY.loading}</span>
            <TypingDots />
          </p>
        )}
      </div>

      {note && (
        <p className="flex items-start gap-2.5 rounded-control bg-surface-2 px-3.5 py-3 text-[14px] leading-snug text-prose">
          <IconCoin aria-hidden="true" className="mt-0.5 shrink-0 text-[18px] text-accent-2" />
          <span>{note}</span>
        </p>
      )}

      {load.kind === "loading" && <RowsSkeleton />}

      {load.kind === "error" && (
        <div role="alert" className="flex flex-col items-start gap-3 rounded-card bg-surface p-5">
          <p className="text-[15px] text-fg">{HOT_COPY.error}</p>
          <ErrorDetails technical={load.technical ?? load.text} />
          <Button size="sm" onClick={() => void fetchBoard()}>
            {HOT_COPY.retry}
          </Button>
        </div>
      )}

      {view?.kind === "empty" && (
        <div className="flex flex-col items-start gap-2 rounded-card border border-dashed border-line-strong px-5 py-5">
          <p className="text-[15px] leading-snug font-semibold text-fg">{view.title}</p>
          <p className="text-[14px] leading-snug text-muted">{view.hint}</p>
          <Button className="mt-1" size="sm" variant="primary" onClick={() => navigate(view.action.href)}>
            {view.action.label}
          </Button>
        </div>
      )}

      {view?.kind === "list" && (
        <ol aria-label={HOT_COPY.listLabel} className="divide-y divide-line overflow-hidden rounded-card bg-surface">
          {view.rows.map((row) => (
            <HotRowLink
              key={row.key}
              row={row}
              mine={myHandle !== "" && row.by === `bởi @${myHandle}`}
            />
          ))}
        </ol>
      )}
    </div>
  );
}
