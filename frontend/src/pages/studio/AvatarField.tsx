import { useRef } from "react";
import { Avatar } from "../../components/Avatar";
import { Spinner } from "../../components/ui";

export const MAX_AVATAR_BYTES = 8 * 1024 * 1024;
const ACCEPT = "image/png,image/jpeg,image/webp,image/gif";
const SIZE = 96;

/** Client-side check before uploading; null = OK. */
export function avatarFileError(file: File): string | null {
  if (!/^image\/(png|jpe?g|webp|gif)$/i.test(file.type) && !/\.(png|jpe?g|webp|gif)$/i.test(file.name)) {
    return "Ảnh phải là PNG, JPEG, WebP hoặc GIF.";
  }
  if (file.size > MAX_AVATAR_BYTES) return "Ảnh quá lớn (tối đa 8MB).";
  return null;
}

/** Portrait (96px, rounded square) that opens the file picker, with "Đổi ảnh" / "Xoá" under it. */
export function AvatarField({
  name,
  url,
  note,
  busy,
  disabled,
  onPick,
  onRemove,
}: {
  name: string;
  url: string | null;
  /** Small line under the buttons, e.g. "Ảnh từ card PNG, gắn khi lưu". */
  note?: string | null;
  busy: boolean;
  disabled: boolean;
  onPick: (file: File) => void;
  /** Present when there is something to remove. */
  onRemove?: (() => void) | null;
}) {
  const input = useRef<HTMLInputElement>(null);
  const hasImage = Boolean(url || note);
  return (
    <div className="flex w-[96px] shrink-0 flex-col items-center gap-1">
      <button
        type="button"
        onClick={() => input.current?.click()}
        disabled={disabled || busy}
        aria-label={hasImage ? "Đổi ảnh đại diện" : "Chọn ảnh đại diện"}
        title={hasImage ? "Đổi ảnh đại diện" : "Chọn ảnh đại diện"}
        className="relative flex rounded-card leading-none transition-opacity hover:opacity-90 disabled:opacity-70"
      >
        <Avatar name={name || "?"} url={url} size={SIZE} shape="portrait" />
        {busy && (
          <span className="absolute inset-0 flex items-center justify-center rounded-card bg-scrim text-fg">
            <Spinner size={20} label="Đang tải ảnh" />
          </span>
        )}
      </button>
      <div className="flex flex-wrap justify-center">
        <button
          type="button"
          onClick={() => input.current?.click()}
          disabled={disabled || busy}
          className="inline-flex h-8 items-center rounded-full px-2 text-[13px] font-medium text-accent transition-colors hover:text-accent-strong disabled:opacity-50"
        >
          {hasImage ? "Đổi ảnh" : "Thêm ảnh"}
        </button>
        {onRemove && (
          <button
            type="button"
            onClick={onRemove}
            disabled={disabled || busy}
            className="inline-flex h-8 items-center rounded-full px-2 text-[13px] text-muted transition-colors hover:text-danger disabled:opacity-50"
          >
            Xoá
          </button>
        )}
      </div>
      {note && <p className="text-center text-[12px] leading-snug text-muted">{note}</p>}
      <input
        ref={input}
        type="file"
        accept={ACCEPT}
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          e.target.value = "";
          if (file) onPick(file);
        }}
      />
    </div>
  );
}
