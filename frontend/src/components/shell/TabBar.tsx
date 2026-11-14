import type { ReactNode } from "react";
import { routeHref, tabOf, useRoute } from "../../lib/router";
import type { TabName } from "../../lib/router";
import { IconCompass, IconHeartFilled, IconSparkles } from "../icons";
import { cx } from "../ui/logic";

function SideTab({ tab, active, label, icon }: { tab: TabName; active: boolean; label: string; icon: ReactNode }) {
  return (
    <a
      href={routeHref({ name: tab })}
      aria-current={active ? "page" : undefined}
      className={cx(
        "flex h-full min-w-0 flex-col items-center justify-center gap-1 rounded-full text-[12px] leading-none transition-colors duration-150",
        active ? "font-semibold text-fg" : "font-medium text-muted hover:text-fg",
      )}
    >
      <span aria-hidden="true" className="text-[22px] leading-none">
        {icon}
      </span>
      {label}
    </a>
  );
}

/**
 * Floating glass pill with the three main tabs (DESIGN.md §5.2, docs/design-impl.md §5): Khám phá,
 * the raised gradient orb of Tương tác in the middle, Studio. 16px above the bottom safe area, 90%
 * wide up to 420px. Active tab by ink brightness and weight, not by a coloured pill. Pages under it
 * reserve room with `pb-tabbar`.
 */
export function TabBar() {
  const current = tabOf(useRoute());
  const hubActive = current === "hub";
  return (
    <nav
      aria-label="Điều hướng chính"
      className="pointer-events-none fixed inset-x-0 bottom-0 z-30 flex justify-center pb-[calc(16px+env(safe-area-inset-bottom))]"
    >
      <div className="glass-strong pointer-events-auto grid h-16 w-[90%] max-w-[420px] grid-cols-3 rounded-full shadow-float">
        <SideTab tab="explore" active={current === "explore"} label="Khám phá" icon={<IconCompass />} />
        <a
          href={routeHref({ name: "hub" })}
          aria-current={hubActive ? "page" : undefined}
          className={cx(
            "group relative flex h-full flex-col items-center justify-end pb-2 text-[12px] leading-none transition-colors duration-150",
            hubActive ? "font-semibold text-fg" : "font-medium text-muted hover:text-fg",
          )}
        >
          <span
            aria-hidden="true"
            className={cx(
              "absolute -top-3 left-1/2 flex h-[52px] w-[52px] -translate-x-1/2 items-center justify-center rounded-full",
              "bg-grad-orb text-[24px] text-on-orb shadow-orb transition-[filter,transform] duration-150",
              "group-hover:brightness-105 group-active:scale-[0.96] motion-reduce:group-active:scale-100",
            )}
          >
            <IconHeartFilled />
          </span>
          Tương tác
        </a>
        <SideTab tab="studio" active={current === "studio"} label="Studio" icon={<IconSparkles />} />
      </div>
    </nav>
  );
}
