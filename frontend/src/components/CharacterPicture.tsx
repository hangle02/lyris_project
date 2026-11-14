import { useEffect, useState } from "react";
import { Avatar } from "./Avatar";
import { cx } from "./ui/logic";

/**
 * A character's picture filling its frame (the parent sets the size, ratio and corners): the card's
 * avatar or a template's scene picture, else the first letter of the name on a flat tone (also when
 * the image fails to load). Decorative: the name is always printed next to it.
 */
export function CharacterPicture({
  url,
  name,
  className,
  eager = false,
}: {
  url: string | null;
  name: string;
  className?: string;
  /** Load right away (the profile's main picture) instead of lazily (grid cards). */
  eager?: boolean;
}) {
  const [broken, setBroken] = useState(false);
  useEffect(() => setBroken(false), [url]);
  return (
    <div className={cx("relative overflow-hidden bg-surface-3", className)}>
      {url && !broken ? (
        <img
          src={url}
          alt=""
          loading={eager ? "eager" : "lazy"}
          decoding="async"
          draggable={false}
          onError={() => setBroken(true)}
          // Crop toward the top: portraits keep the face when a tall photo fills a wide frame.
          className="absolute inset-0 h-full w-full object-cover object-[50%_22%]"
        />
      ) : (
        <span className="absolute inset-0 flex">
          <Avatar name={name} fill />
        </span>
      )}
    </div>
  );
}
