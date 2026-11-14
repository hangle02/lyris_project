import type { ReactNode } from "react";
import { IconChevronLeft } from "../icons";
import { cx } from "../ui/logic";

export interface SubpageHeaderProps {
  /** Where the back chevron goes (a hash such as "#/"). */
  backHref: string;
  /** Accessible name of the back link, e.g. "Về Tương tác". */
  backLabel: string;
  /** Screen title (the page's h1). */
  title: ReactNode;
  /** One muted line under the title (status, context). */
  subtitle?: ReactNode;
  /** Right side: the screen's actions (at most one primary). */
  children?: ReactNode;
  /**
   * Width of the inner row, matching the page's column: "narrow" 720px (single-column pages: new
   * story, personas), "medium" 960px (character profile), "wide" 1200px, "fluid" full width (pages with a side panel). Default narrow.
   */
  width?: "narrow" | "medium" | "wide" | "fluid";
}

const WIDTH = { narrow: "max-w-[720px]", medium: "max-w-[960px]", wide: "max-w-[1200px]", fluid: null } as const;

/**
 * Top bar of every full-screen subpage without the tab bar (card editor, personas, new story): a
 * back chevron, the screen's h1 with a status line, actions on the right. Solid ground with a
 * hairline, no glass (glass is kept for the hub header, tab bar and chat header). Safe-area aware.
 */
export function SubpageHeader({ backHref, backLabel, title, subtitle, children, width = "narrow" }: SubpageHeaderProps) {
  return (
    <header className="z-20 shrink-0 border-b border-line bg-bg pt-safe">
      <div className={cx("mx-auto flex h-14 w-full items-center gap-1 pr-4 pl-1.5 sm:pl-2.5", WIDTH[width])}>
        <a
          href={backHref}
          aria-label={backLabel}
          title={backLabel}
          className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-[22px] text-muted transition-colors duration-150 hover:bg-surface-2 hover:text-fg"
        >
          <IconChevronLeft />
        </a>
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-[18px] leading-tight font-semibold text-fg sm:text-[20px]">{title}</h1>
          {subtitle && <div className="mt-0.5 truncate text-[13px] leading-tight text-muted">{subtitle}</div>}
        </div>
        {children && <div className="flex shrink-0 items-center gap-2">{children}</div>}
      </div>
    </header>
  );
}
