import { useEffect, useState } from "react";
import { cx } from "../../components/ui/logic";

/**
 * Profile cover, 3:1 like the backend's 1500x500 limit: the uploaded picture, or a flat
 * `surface-2` field when there is none or it fails to load (no gradient, no pattern). Decorative.
 * `collapseEmpty`: without a picture the flat field is a 6:1 strip, so on the profile page an empty
 * cover does not outweigh the avatar and name (the edit sheet keeps 3:1 to show the shape to upload).
 */
export function ProfileBanner({ url, className, collapseEmpty = false }: { url: string | null; className?: string; collapseEmpty?: boolean }) {
  const [broken, setBroken] = useState(false);
  useEffect(() => setBroken(false), [url]);
  const shown = url !== null && !broken;
  return (
    <div
      aria-hidden="true"
      className={cx(
        "relative w-full overflow-hidden bg-surface-2",
        collapseEmpty && !shown ? "aspect-[6/1]" : "aspect-[3/1]",
        className,
      )}
    >
      {shown && (
        <img
          src={url}
          alt=""
          decoding="async"
          draggable={false}
          onError={() => setBroken(true)}
          className="absolute inset-0 h-full w-full object-cover"
        />
      )}
    </div>
  );
}
