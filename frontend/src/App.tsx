import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api/client";
import { AppShell } from "./components/shell";
import { Toast } from "./components/ui";
import { useAccount } from "./hooks/useAccount";
import { refreshWallet, walletStore } from "./hooks/useWallet";
import { refreshAuth, startAuth, useAuth } from "./hooks/useAuth";
import { gateOf, isAuthRoute, rememberNext } from "./lib/auth";
import { dailyToast } from "./lib/coins";
import type { Gate } from "./lib/auth";
import { legacyRedirect, replaceRoute, routeHref, useRoute } from "./lib/router";
import type { Route } from "./lib/router";
import { AdminPage } from "./pages/admin/AdminPage";
import { AuthSplash, ForcePasswordPage, LoginPage, SetupPage, SignupPage, TermsPage } from "./pages/auth";
import { CharacterPage } from "./pages/character/CharacterPage";
import { MissionsPage } from "./pages/coins/MissionsPage";
import { TopUpPage } from "./pages/coins/TopUpPage";
import { WalletPage } from "./pages/coins/WalletPage";
import { ChatPage } from "./pages/chat/ChatPage";
import { ExplorePage } from "./pages/explore/ExplorePage";
import { HotPage } from "./pages/explore/HotPage";
import { HubPage } from "./pages/hub/HubPage";
import { LegalPage } from "./pages/legal/LegalPage";
import { PersonasPage } from "./pages/PersonasPage";
import { ProfilePage } from "./pages/profile";
import { CardEditorPage, CardListPage } from "./pages/studio";
import { displayMode, noteRoute, setTrackingConsent, track } from "./lib/track";

/** Browser tab title per screen; the chat sets its own (the character's name). */
function titleOf(route: Route): string | null {
  switch (route.name) {
    case "hub":
      return "Lyris";
    case "explore":
      return "Khám phá · Lyris";
    case "hot":
      return "Nhân vật hot · Lyris";
    case "studio":
      return "Studio · Lyris";
    case "card":
      return route.cardId === null ? "Nhân vật mới · Lyris" : "Sửa nhân vật · Lyris";
    case "personas":
      return "Persona · Lyris";
    case "newStory":
      return null;
    case "character":
      // The profile sets "<name> · Lyris" once the card is loaded.
      return "Nhân vật · Lyris";
    case "profile":
      return route.handle === null ? "Profile · Lyris" : `@${route.handle} · Lyris`;
    case "chat":
      return null;
    case "login":
      return "Đăng nhập · Lyris";
    case "signup":
      return "Tạo tài khoản · Lyris";
    case "admin":
      return "Quản lý tài khoản · Lyris";
    case "legal":
      // LegalPage sets its own title.
      return null;
    case "coins":
      return "Ví coin · Lyris";
    case "topUp":
      return "Nạp coin · Lyris";
    case "missions":
      return "Nhiệm vụ hôm nay · Lyris";
  }
}

function sessionStore(): Storage | null {
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

/**
 * The sign-in gate (docs/auth.md §7.1): asks /api/auth/me once before drawing any route (ground and
 * wordmark meanwhile), then shows the owner setup, the login or signup page, the forced password
 * change, or the app. Signed out on another hash: that hash is kept ("lyris.next") and the address
 * becomes "#/login"; signed in on "#/login" or "#/signup": the hub.
 */
export default function App() {
  const auth = useAuth();
  const route = useRoute();
  const [retrying, setRetrying] = useState(false);

  useEffect(() => {
    startAuth();
  }, []);

  // Usage tracking (docs/tracking-plan.md §7): the previous screen (for "from" of a profile view).
  useEffect(() => {
    noteRoute(route.name);
  }, [route]);

  // Who may be tracked: signed out (or a temporary password) only sends the pre-sign-in events; a
  // signed-in account waits for its "Chia sẻ dữ liệu sử dụng ẩn danh" choice (TrackingConsent below).
  const account = auth.state?.account ?? null;
  const fullSignIn = account !== null && !account.must_change_password;
  useEffect(() => {
    if (!auth.state) return;
    if (fullSignIn) setTrackingConsent({ signedIn: true });
    else setTrackingConsent({ signedIn: false, optOut: null });
  }, [auth.state, fullSignIn]);

  // "app_opened" once per load, after the first answer of /auth/me.
  const opened = useRef(false);
  useEffect(() => {
    if (!auth.state || opened.current) return;
    opened.current = true;
    let standalone = false;
    try {
      standalone = window.matchMedia("(display-mode: standalone)").matches;
    } catch {
      standalone = false;
    }
    const ios = (navigator as Navigator & { standalone?: boolean }).standalone === true;
    track("app_opened", { display_mode: displayMode(standalone, ios), authed: fullSignIn });
  }, [auth.state, fullSignIn]);

  const gate: Gate | null = auth.state ? gateOf(auth.state, route) : null;

  useEffect(() => {
    if (gate === "login" && route.name !== "login") {
      rememberNext(sessionStore(), window.location.hash);
      replaceRoute({ name: "login" });
    } else if (gate === "app" && isAuthRoute(route)) {
      replaceRoute({ name: "hub" });
    } else if (gate === "app" && route.name === "admin" && auth.state?.account?.role !== "owner") {
      replaceRoute({ name: "hub" });
    }
  }, [gate, route, auth.state]);

  // The legal pages open for everyone, at once (no need to wait for the sign-in answer).
  if (route.name === "legal") return <LegalPage doc={route.doc} />;

  if (!auth.state) {
    return (
      <AuthSplash
        error={auth.status === "error" ? auth.error : null}
        retrying={retrying}
        onRetry={() => {
          setRetrying(true);
          void refreshAuth().finally(() => setRetrying(false));
        }}
      />
    );
  }
  switch (gate) {
    case "setup":
      return <SetupPage needsProfile={auth.state.setup_needs_profile} />;
    case "forceChange":
      return <ForcePasswordPage />;
    case "terms":
      return <TermsPage />;
    case "public":
      // Drawn above (route "legal").
      return null;
    case "signup":
      return <SignupPage code={route.name === "signup" ? route.code : null} />;
    case "login":
      return <LoginPage />;
    default:
      return (
        <>
          <TrackingConsent />
          <CoinCheckin accountId={auth.state.account?.id ?? null} />
          <AppRoutes route={route} isOwner={auth.state.account?.role === "owner"} />
        </>
      );
  }
}

/**
 * Signed in: hands the account's "Chia sẻ dữ liệu sử dụng ẩn danh" choice to the tracker (events wait
 * until it is known; turned off, nothing is sent and what waits is dropped).
 */
function TrackingConsent() {
  const { account } = useAccount();
  const optOut = account ? account.analytics_opt_out === true : null;
  useEffect(() => {
    if (optOut !== null) setTrackingConsent({ optOut });
  }, [optOut]);
  return null;
}

/** Ask again for the daily gift when the tab comes back after this long (the Vietnam day may have changed). */
const CHECKIN_AGAIN_MS = 5 * 60_000;

function dailyKey(accountId: number): string {
  return `lyris.coins.daily.${accountId}`;
}

/**
 * F42 (docs/coins.md §3.4, §8): opening the app is the day's sign-in. POST /api/coins/checkin once per
 * load (and when the tab comes back after a while): the first open of the Vietnam day adds 60 coins and
 * shows "+60 coin cho hôm nay" once. The answer carries the wallet, so the header chip is fresh at once.
 */
function CoinCheckin({ accountId }: { accountId: number | null }) {
  const [toast, setToast] = useState<string | null>(null);
  const last = useRef(0);
  const hideToast = useCallback(() => setToast(null), []);

  useEffect(() => {
    if (accountId === null) return;
    let alive = true;
    const run = () => {
      last.current = Date.now();
      api.checkin().then(
        (res) => {
          if (!alive) return;
          walletStore.set(res.wallet);
          let seen: string | null = null;
          try {
            seen = window.localStorage.getItem(dailyKey(accountId));
          } catch {
            seen = null;
          }
          const text = dailyToast(res, seen);
          if (text) setToast(text);
          try {
            if (res.today > 0) window.localStorage.setItem(dailyKey(accountId), res.coin_day);
          } catch {
            // private mode: the notice may show again next time
          }
        },
        () => {
          if (alive) refreshWallet();
        },
      );
    };
    run();
    const onVisible = () => {
      if (document.visibilityState !== "visible") return;
      if (Date.now() - last.current > CHECKIN_AGAIN_MS) run();
      else refreshWallet();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      alive = false;
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [accountId]);

  return <Toast text={toast} onDone={hideToast} duration={4500} />;
}

/**
 * Routes (docs/design-impl.md §5): the hub tabs (Tương tác "#/", Khám phá, Studio list) inside the
 * AppShell with the floating tab bar; the chat, card editor, personas, character profile and account
 * profile screens full screen without it. Old "#/new-story" links are redirected (lib/router
 * legacyRedirect). Each screen owns its own data; the chat owns all chat state.
 */
function AppRoutes({ route, isOwner }: { route: Route; isOwner: boolean }) {
  const href = routeHref(route);

  // The hub tabs scroll the document: a new screen starts at the top.
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [href]);

  // "#/new-story?card=12" (old links, bookmarks): the character's profile with the start sheet open.
  const redirect = legacyRedirect(route);
  useEffect(() => {
    if (redirect) replaceRoute(redirect);
  }, [redirect]);

  useEffect(() => {
    const title = titleOf(route);
    if (title) document.title = title;
  }, [route]);

  switch (route.name) {
    case "hub":
      return (
        <AppShell showTabBar>
          <HubPage />
        </AppShell>
      );
    case "explore":
      return (
        <AppShell showTabBar>
          <ExplorePage />
        </AppShell>
      );
    case "hot":
      return (
        <AppShell showTabBar>
          <HotPage />
        </AppShell>
      );
    case "studio":
      return (
        <AppShell showTabBar>
          <CardListPage />
        </AppShell>
      );
    case "card":
      // No key: the editor handles cardId changes itself (keeps its state after the first save moves
      // "#/studio/new" to "#/studio/<id>").
      return <CardEditorPage cardId={route.cardId} />;
    case "personas":
      return <PersonasPage />;
    case "newStory":
      return null;
    case "character": {
      // Keyed by the character only: dropping "?start=1" keeps the page (and its open sheet).
      const key = route.target.kind === "card" ? `card-${route.target.id}` : `template-${route.target.slug}`;
      return <CharacterPage key={key} target={route.target} start={route.start} />;
    }
    case "profile":
      // Keyed: "#/me" and "#/u/<handle>" are different people (state must not carry over).
      return <ProfilePage key={route.handle ?? "@me"} handle={route.handle} />;
    case "chat":
      if (route.storyId === null) {
        return (
          <AppShell showTabBar>
            <HubPage />
          </AppShell>
        );
      }
      return <ChatPage key={route.storyId} storyId={route.storyId} />;
    case "admin":
      // A member is sent to the hub by the gate; never mount the page (its requests would be refused).
      return isOwner ? <AdminPage /> : null;
    case "login":
    case "signup":
      // Signed in: the gate moves these to the hub.
      return null;
    case "legal":
      // Drawn by App before the gate.
      return null;
    case "coins":
      return <WalletPage />;
    case "topUp":
      return <TopUpPage />;
    case "missions":
      return <MissionsPage />;
  }
}
