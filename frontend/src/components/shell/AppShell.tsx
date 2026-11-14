import type { ReactNode } from "react";
import { cx } from "../ui/logic";
import { HubHeader } from "./HubHeader";
import { TabBar } from "./TabBar";

export interface AppShellProps {
  children: ReactNode;
  /** The floating tab bar (hub, explore, studio list). Content then keeps `pb-tabbar` free at the bottom. */
  showTabBar: boolean;
}

/**
 * Frame of the hub tabs: the glass HubHeader on top, the page in normal document flow (the page
 * itself scrolls, so iOS shows its own scroll bar and rubber band), and the floating TabBar. Pages
 * put their content in SHELL_CONTAINER and start with an h1.
 */
export function AppShell({ children, showTabBar }: AppShellProps) {
  return (
    <div className="min-h-dvh bg-bg">
      <HubHeader />
      <main className={cx(showTabBar ? "pb-tabbar" : "pb-safe")}>{children}</main>
      {showTabBar && <TabBar />}
    </div>
  );
}
