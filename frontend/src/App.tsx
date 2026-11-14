import { useEffect, useState } from "react";
import { AppShell } from "./components/shell";
import { refreshAuth, startAuth, useAuth } from "./hooks/useAuth";
import { gateOf, isAuthRoute, rememberNext } from "./lib/auth";
import type { Gate } from "./lib/auth";
import { legacyRedirect, replaceRoute, routeHref, useRoute } from "./lib/router";
import type { Route } from "./lib/router";
import { AdminPage } from "./pages/admin/AdminPage";
import { AuthSplash, ForcePasswordPage, LoginPage, SetupPage, SignupPage } from "./pages/auth";
import { CharacterPage } from "./pages/character/CharacterPage";
import { ChatPage } from "./pages/chat/ChatPage";
import { ExplorePage } from "./pages/explore/ExplorePage";
import { HubPage } from "./pages/hub/HubPage";
import { PersonasPage } from "./pages/PersonasPage";
import { ProfilePage } from "./pages/profile";
import { CardEditorPage, CardListPage } from "./pages/studio";

/** Browser tab title per screen; the chat sets its own (the character's name). */
function titleOf(route: Route): string | null {
  switch (route.name) {
    case "hub":
      return "Lyris";
    case "explore":
      return "Khám phá · Lyris";
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
    case "signup":
      return <SignupPage code={route.name === "signup" ? route.code : null} />;
    case "login":
      return <LoginPage />;
    default:
      return <AppRoutes route={route} isOwner={auth.state.account?.role === "owner"} />;
  }
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
  }
}
