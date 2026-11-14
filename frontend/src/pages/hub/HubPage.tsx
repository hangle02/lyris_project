import { useCallback, useEffect, useMemo, useState } from "react";
import { api, errorMessage } from "../../api/client";
import { Avatar } from "../../components/Avatar";
import { IconHeartFilled, IconMapPin, IconPlus, IconSearch } from "../../components/icons";
import { SHELL_CONTAINER } from "../../components/shell/layout";
import { Badge, Button, Card, Chip, EmptyState, Skeleton, TextField } from "../../components/ui";
import { cx } from "../../components/ui/logic";
import { navigate, routeHref } from "../../lib/router";
import { AccountInvite } from "../profile/AccountInvite";
import type { StoryOut } from "../../types";
import { foldText, formatStoryTime, greetingFor, matchesStory, previewOf, sortByActivity, storyChips } from "./logic";

/** Re-renders every minute so "23:15 / Hôm qua" and the greeting follow the clock. */
function useMinuteClock(): Date {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 60_000);
    return () => window.clearInterval(id);
  }, []);
  return now;
}

function ModeBadge({ mode }: { mode: StoryOut["mode"] }) {
  return mode === "dm" ? (
    <Badge solid tone="gold">
      DM
    </Badge>
  ) : (
    <Badge solid tone="accent">
      Story
    </Badge>
  );
}

function StoryRow({ story, now }: { story: StoryOut; now: Date }) {
  const when = formatStoryTime(story.updated_at ?? story.created_at, now);
  const preview = previewOf(story);
  const role = (story.card_role ?? "").trim();
  const { emotion, location } = storyChips(story);
  const title = story.title.trim();
  const showTitle = title !== "" && foldText(title) !== foldText(story.card_name) && foldText(title) !== foldText(role);

  return (
    <li>
      <a
        href={story.id !== null ? routeHref({ name: "chat", storyId: story.id }) : undefined}
        className="flex gap-3.5 px-4 py-3.5 transition-colors duration-150 hover:bg-surface-2 sm:px-5"
      >
        <span className="pt-0.5 pb-1.5">
          <Avatar
            name={story.card_name}
            url={story.card_avatar_url}
            size={48}
            shape="portrait"
            badge={<ModeBadge mode={story.mode} />}
          />
        </span>
        <span className="flex min-w-0 flex-1 flex-col gap-0.5">
          <span className="flex items-baseline gap-3">
            <span className="min-w-0 truncate text-[16px] leading-snug font-semibold text-fg">{story.card_name}</span>
            {when && (
              <time
                dateTime={story.updated_at ?? story.created_at ?? undefined}
                className="ml-auto shrink-0 text-[13px] text-muted tabular-nums"
              >
                {when}
              </time>
            )}
          </span>
          {(role || showTitle) && (
            <span className="truncate text-[13px] leading-snug">
              {role && <span className="text-accent-2">{role}</span>}
              {role && showTitle && <span className="text-muted"> · </span>}
              {showTitle && <span className="text-muted">{title}</span>}
            </span>
          )}
          <span
            className={cx(
              "truncate pt-0.5 font-story text-[14px] leading-snug italic",
              preview ? "text-muted" : "text-faint",
            )}
          >
            {preview ?? "Chưa có lời nào, story đang chờ bạn mở đầu."}
          </span>
          {(emotion || location) && (
            // One line: the emotion stays whole, the place truncates.
            <span className="flex min-w-0 gap-1.5 pt-1.5">
              {emotion && (
                <Chip
                  size="sm"
                  icon={<IconHeartFilled style={{ color: `var(--color-emo-${emotion.key})` }} />}
                  title={`Cảm xúc nổi bật: ${emotion.text}`}
                >
                  <span className="tabular-nums">{emotion.text}</span>
                </Chip>
              )}
              {location && (
                <span className="flex min-w-0">
                  <Chip size="sm" icon={<IconMapPin />} title={location}>
                    {location}
                  </Chip>
                </span>
              )}
            </span>
          )}
        </span>
      </a>
    </li>
  );
}

function RowSkeleton() {
  return (
    <li className="flex gap-3.5 px-4 py-3.5 sm:px-5">
      <Skeleton width={48} height={48} className="rounded-[14px]" />
      <span className="flex min-w-0 flex-1 flex-col gap-2 pt-1">
        <span className="flex gap-3">
          <Skeleton shape="text" width="38%" height={14} />
          <Skeleton shape="text" width={40} height={12} className="ml-auto" />
        </span>
        <Skeleton shape="text" width="30%" height={12} />
        <Skeleton shape="text" width="82%" height={12} />
      </span>
    </li>
  );
}

/**
 * Tương tác, layer 1 (DESIGN.md page 1, docs/design-impl.md §6.1): a greeting for the time of day,
 * the search box, and the stories newest first; each row opens the full-screen chat.
 */
export function HubPage() {
  const now = useMinuteClock();
  const [stories, setStories] = useState<StoryOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const list = await api.listStories();
      setStories(sortByActivity(list));
      setError(null);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    // Back from another tab or app: the newest message may have changed.
    const onVis = () => {
      if (document.visibilityState === "visible") void load();
    };
    document.addEventListener("visibilitychange", onVis);
    return () => document.removeEventListener("visibilitychange", onVis);
  }, [load]);

  const visible = useMemo(
    () => (stories ?? []).filter((s) => matchesStory({ ...s, location: storyChips(s).location }, query)),
    [stories, query],
  );

  const total = stories?.length ?? 0;
  const greeting = greetingFor(now.getHours());

  let list;
  if (stories === null && error) {
    list = (
      <Card padding="md" role="alert" className="flex flex-col items-start gap-3">
        <p className="text-[15px] leading-snug text-fg">Không tải được danh sách story.</p>
        <p className="text-[14px] leading-snug text-muted [overflow-wrap:anywhere]">{error}</p>
        <Button size="sm" onClick={() => void load()} loading={loading}>
          Thử lại
        </Button>
      </Card>
    );
  } else if (stories === null) {
    list = (
      <Card padding="none" aria-busy="true" className="overflow-hidden">
        <span className="sr-only">Đang tải story…</span>
        <ul className="divide-y divide-line">
          <RowSkeleton />
          <RowSkeleton />
          <RowSkeleton />
        </ul>
      </Card>
    );
  } else if (total === 0) {
    list = (
      <EmptyState
        text="Chưa có story nào. Chọn một nhân vật ở Khám phá để bắt đầu."
        action={
          <Button variant="primary" size="sm" onClick={() => navigate({ name: "explore" })}>
            Mở Khám phá
          </Button>
        }
      />
    );
  } else if (visible.length === 0) {
    list = (
      <EmptyState
        text={`Không có story nào khớp “${query.trim()}”.`}
        action={
          <Button size="sm" variant="secondary" onClick={() => setQuery("")}>
            Xoá tìm kiếm
          </Button>
        }
      />
    );
  } else {
    list = (
      <Card padding="none" className="overflow-hidden">
        <ul className="divide-y divide-line">
          {visible.map((s) => (
            <StoryRow key={s.id ?? s.title} story={s} now={now} />
          ))}
        </ul>
      </Card>
    );
  }

  return (
    <div className={cx(SHELL_CONTAINER, "pt-6 sm:pt-10")}>
      {/* The one serif moment besides the wordmark: the time-of-day greeting is the screen's title. */}
      <h1 className="font-brand text-[28px] leading-[1.15] font-semibold text-balance text-fg italic sm:text-[32px]">
        {greeting}
      </h1>

      <AccountInvite className="mt-5 sm:mt-6" />

      {total > 0 && (
        <div className="mt-5 flex items-center gap-2 sm:mt-6">
          <TextField
            label="Tìm story"
            hideLabel
            type="search"
            icon={<IconSearch />}
            value={query}
            onChange={setQuery}
            placeholder={`Tìm trong ${total} story`}
            enterKeyHint="search"
            autoComplete="off"
            className="min-w-0 flex-1"
          />
          <Button icon={<IconPlus />} onClick={() => navigate({ name: "explore" })} aria-label="Story mới: chọn nhân vật ở Khám phá">
            <span className="sm:hidden">Mới</span>
            <span className="hidden sm:inline">Story mới</span>
          </Button>
        </div>
      )}

      <section aria-label="Story của bạn" className="mt-4 sm:mt-5">
        {list}
        {stories !== null && error && (
          <p role="status" className="mt-3 text-[13px] text-muted">
            Chưa làm mới được danh sách: {error}
          </p>
        )}
      </section>
    </div>
  );
}
