import { forwardRef } from "react";
import { Avatar } from "../../components/Avatar";
import { IconChevronLeft, IconHeart, IconSettings } from "../../components/icons";
import { cx, IconButton, SegmentedControl, Skeleton } from "../../components/ui";
import type { SegmentOption } from "../../components/ui";
import type { Mode, StoryExtras, StoryOut, ThoughtStyle } from "../../types";
import { characterRoute, routeHref } from "../../lib/router";
import { showThoughtsOf } from "../../lib/storyOptions";
import { headerSubtitle, headerSubtitleText, sceneLine } from "./chatLogic";
import { MomentBanner } from "./MomentBanner";
import { ThoughtMenu } from "./ThoughtMenu";

const MODES: SegmentOption<Mode>[] = [
  { value: "story", label: "Story" },
  { value: "dm", label: "DM" },
];

interface Props {
  /** null while the story loads. */
  story: StoryOut | null;
  extras: StoryExtras;
  /** Mode and thought style are locked (a reply is streaming, a save is running). */
  modeDisabled: boolean;
  onBack: () => void;
  onChangeMode: (mode: Mode) => void;
  onChangeThoughtStyle: (style: ThoughtStyle) => void;
  /** Phase 4 (B): "Đọc suy nghĩ của nhân vật", saved at once. */
  onChangeShowThoughts: (show: boolean) => void;
  showThoughtsSaving: boolean;
  onOpenHeart: () => void;
  onOpenSettings: () => void;
}

/**
 * Sticky glass header of the roleplay workspace. Phone: the identity row (back, avatar, name and
 * place, heart, settings) with the Story/DM switch and the thought menu on a second row; from
 * 640px everything sits on one row. The moment banner hangs under it when the story has one.
 */
export const ChatHeader = forwardRef<HTMLElement, Props>(function ChatHeader(
  {
    story,
    extras,
    modeDisabled,
    onBack,
    onChangeMode,
    onChangeThoughtStyle,
    onChangeShowThoughts,
    showThoughtsSaving,
    onOpenHeart,
    onOpenSettings,
  },
  ref,
) {
  return (
    <header ref={ref} className="glass absolute inset-x-0 top-0 z-20 border-b border-line pt-safe">
      {/* From 1024px the row is wider than the 720px reading column, so the name, role and scene
          are not squeezed by the mode switch and the buttons. */}
      <div className="mx-auto flex max-w-[720px] flex-wrap items-center gap-x-1 px-2 sm:flex-nowrap sm:gap-x-2 sm:px-4 lg:max-w-[960px]">
        <IconButton label="Về danh sách story" icon={<IconChevronLeft />} onClick={onBack} />
        <div className="flex h-14 min-w-0 flex-1 items-center gap-2.5">
          {story ? (
            // The character's profile (read only for someone else's character, Phase 4b).
            <a
              href={routeHref(characterRoute(story.card_id))}
              title={`Hồ sơ của ${story.card_name}`}
              className="-ml-1 flex min-w-0 flex-1 items-center gap-2.5 rounded-control py-1 pl-1 outline-none focus-visible:outline-2 focus-visible:outline-accent"
            >
              <Avatar name={story.card_name} url={story.card_avatar_url} size={32} />
              <div className="min-w-0 flex-1">
                <h1 className="truncate text-[16px] leading-tight font-semibold text-fg">{story.card_name}</h1>
                <Subtitle sub={headerSubtitle(story, extras)} hasScene={sceneLine(extras) !== ""} />
              </div>
            </a>
          ) : (
            <>
              <Skeleton shape="circle" height={32} />
              <div className="flex min-w-0 flex-col gap-1.5">
                <h1 className="sr-only">Đang mở story</h1>
                <Skeleton shape="text" width={96} height={14} />
                <Skeleton shape="text" width={140} height={12} />
              </div>
            </>
          )}
        </div>

        {story && (
          <div className="order-last flex h-12 basis-full items-center justify-between gap-2 px-2 sm:order-none sm:h-14 sm:basis-auto sm:justify-end sm:px-0">
            <SegmentedControl
              label="Chế độ hiển thị"
              size="sm"
              options={MODES}
              value={story.mode}
              onChange={onChangeMode}
              disabled={modeDisabled}
            />
            <ThoughtMenu
              value={story.thought_style}
              disabled={modeDisabled}
              onChange={onChangeThoughtStyle}
              showThoughts={showThoughtsOf(story)}
              onChangeShowThoughts={onChangeShowThoughts}
              showThoughtsSaving={showThoughtsSaving}
              characterName={story.card_name}
            />
          </div>
        )}

        <IconButton
          label="Cảm xúc & ký ức"
          icon={<IconHeart />}
          onClick={onOpenHeart}
          disabled={!story}
          aria-haspopup="dialog"
        />
        <IconButton
          label="Thiết lập story"
          icon={<IconSettings />}
          onClick={onOpenSettings}
          disabled={!story}
          aria-haspopup="dialog"
        />
      </div>
      {extras.moment && <MomentBanner moment={extras.moment} />}
    </header>
  );
});

/**
 * Role in gold (DESIGN.md: the character's title), then "place · time" (or the story title). Each
 * part truncates on its own: the role takes at most 45%, the scene the rest. On a phone the scene
 * alone is shown when there is one, and so on a tablet (below 1024px the row shares 720px with the
 * mode switch, and both parts would be cut); the role stays on the hub row and in the tooltip.
 */
function Subtitle({ sub, hasScene }: { sub: { role: string | null; detail: string }; hasScene: boolean }) {
  const text = headerSubtitleText(sub);
  if (!text) return null;
  const both = !!sub.role && !!sub.detail;
  // Below 1024px the row is 720px wide and also holds the mode switch: role and scene would both be cut.
  const hideRole = both && hasScene;
  return (
    <p className="flex min-w-0 text-[13px] leading-snug whitespace-nowrap text-muted" title={text}>
      {sub.role && (
        <span
          className={cx(
            "min-w-0 truncate font-medium text-accent-2",
            both && "max-w-[45%] shrink-0",
            hideRole && "max-lg:hidden",
          )}
        >
          {sub.role}
        </span>
      )}
      {both && (
        <span aria-hidden="true" className={cx("shrink-0 whitespace-pre", hideRole && "max-lg:hidden")}>
          {" · "}
        </span>
      )}
      {sub.detail && <span className="min-w-0 flex-1 truncate">{sub.detail}</span>}
    </p>
  );
}
