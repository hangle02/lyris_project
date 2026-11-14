import { COIN_COPY } from "../lib/coinCopy";
import { navigate } from "../lib/router";
import { noteMissionsFrom } from "../pages/coins/missionsLogic";
import { noteTopUpFrom } from "../pages/coins/topupLogic";
import { IconCoin } from "./icons";
import { Button } from "./ui";

/**
 * F42 (docs/coins.md §10.3): in place of the banner above a locked composer (Story, DM, Studio test
 * chat) when a member has fewer than 6 usable coins: "Bạn đã hết coin", the price of a reply, and the
 * two ways to get coins. The text being typed stays in the (disabled) input.
 */
export function CoinsOutBlock({ className }: { className?: string }) {
  return (
    <div className={className ?? "mx-auto w-full max-w-[720px] px-4 pb-2"}>
      <div
        role="status"
        aria-labelledby="coins-out-title"
        className="flex flex-col gap-3 rounded-card border border-line bg-surface px-4 py-3 sm:flex-row sm:items-center"
      >
        <div className="flex min-w-0 flex-1 items-start gap-3">
          <IconCoin className="mt-0.5 shrink-0 text-[22px] text-accent-2" />
          <div className="min-w-0">
            <p id="coins-out-title" className="text-[15px] leading-snug font-semibold text-fg">
              {COIN_COPY.outTitle}
            </p>
            <p className="text-[14px] leading-snug text-muted">{COIN_COPY.outText}</p>
          </div>
        </div>
        <div className="flex shrink-0 gap-2">
          <Button
            size="sm"
            variant="primary"
            className="max-sm:flex-1"
            onClick={() => {
              noteTopUpFrom("composer");
              navigate("#/coins/top-up");
            }}
          >
            {COIN_COPY.topUp}
          </Button>
          <Button
            size="sm"
            variant="secondary"
            className="max-sm:flex-1"
            onClick={() => {
              noteMissionsFrom("composer");
              navigate("#/missions");
            }}
          >
            {COIN_COPY.missions}
          </Button>
        </div>
      </div>
    </div>
  );
}
