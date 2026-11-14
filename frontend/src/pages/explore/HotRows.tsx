import { CharacterPicture } from "../../components/CharacterPicture";
import { cx } from "../../components/ui/logic";
import type { HotRow } from "./hotLogic";

/**
 * One row of the "Nhân vật hot" ranking (wiki/screens/hot-ranking.md): rank, round picture, name, "bởi @handle",
 * "{n} người chơi". The whole row is one link to the character's profile.
 */
export function HotRowLink({ row, mine = false, compact = false }: { row: HotRow; mine?: boolean; compact?: boolean }) {
  return (
    <li>
      <a
        href={row.href}
        aria-label={row.label}
        data-hot-rank={row.rank}
        className={cx(
          "flex items-center gap-3 px-3 transition-colors duration-150 hover:bg-surface-2 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-accent sm:px-4",
          compact ? "min-h-14 py-1.5" : "min-h-16 py-2.5",
          mine && "border-l-[3px] border-accent pl-[9px] sm:pl-[13px]",
        )}
      >
        <span
          aria-hidden="true"
          className={cx(
            "w-8 shrink-0 text-center text-[16px] tabular-nums",
            row.top ? "font-semibold text-accent-2" : "text-muted",
          )}
        >
          {row.rank}
        </span>
        <CharacterPicture url={row.imageUrl} name={row.name} className="h-11 w-11 shrink-0 rounded-full" />
        <span className="flex min-w-0 flex-1 flex-col">
          <span className="truncate text-[15px] leading-snug font-semibold text-fg">{row.name}</span>
          {row.by && <span className="truncate text-[13px] leading-snug text-muted">{row.by}</span>}
        </span>
        <span className="shrink-0 text-[13px] whitespace-nowrap text-muted tabular-nums">{row.players}</span>
      </a>
    </li>
  );
}
