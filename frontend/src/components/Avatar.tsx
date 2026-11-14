import { useEffect, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import { cx, initialFontSize, initialOf, portraitRadius } from "./ui/logic";

export { initialOf };

interface Props {
  name: string;
  url?: string | null;
  /** Side in px (default 28). Ignored when `fill` is set. */
  size?: number;
  /** circle (default): people in rows and headers; portrait: rounded square (story cards, 48px+). */
  shape?: "circle" | "portrait";
  /** Fill the parent box (e.g. a 3:4 explore card); the parent sets size and corner radius. */
  fill?: boolean;
  /** Corner slot, bottom right (e.g. <Badge solid>DM</Badge>). Not clipped by the avatar. */
  badge?: ReactNode;
  className?: string;
}

/**
 * Character or persona picture: the uploaded image, or the first letter of the name on a flat
 * tone when there is none (or it fails to load). No gradient, no illustration. The picture is
 * decorative (the name is always printed nearby); the badge stays readable to screen readers.
 */
export function Avatar({ name, url, size = 28, shape = "circle", fill = false, badge, className = "" }: Props) {
  const [broken, setBroken] = useState(false);
  useEffect(() => setBroken(false), [url]);

  const radius = fill ? undefined : shape === "circle" ? "9999px" : `${portraitRadius(size)}px`;
  const box: CSSProperties = fill
    ? { containerType: "inline-size" }
    : { width: size, height: size, borderRadius: radius, fontSize: initialFontSize(size) };
  const showImage = Boolean(url) && !broken;

  const face = (
    <span
      aria-hidden="true"
      className={cx(
        "shrink-0 items-center justify-center overflow-hidden bg-surface-3 select-none",
        fill ? "flex h-full w-full" : "inline-flex",
        !showImage && "leading-none font-semibold text-accent",
        badge ? "" : className,
      )}
      style={box}
    >
      {showImage ? (
        <img
          src={url ?? undefined}
          alt=""
          width={fill ? undefined : size}
          height={fill ? undefined : size}
          loading="lazy"
          decoding="async"
          draggable={false}
          onError={() => setBroken(true)}
          className="h-full w-full object-cover"
        />
      ) : (
        <span style={fill ? { fontSize: "clamp(28px, 28cqi, 72px)" } : undefined}>{initialOf(name)}</span>
      )}
    </span>
  );

  if (!badge) return face;
  return (
    <span className={cx("relative inline-flex shrink-0", fill && "h-full w-full", className)}>
      {face}
      <span className="absolute -right-1.5 -bottom-1.5 flex">{badge}</span>
    </span>
  );
}
