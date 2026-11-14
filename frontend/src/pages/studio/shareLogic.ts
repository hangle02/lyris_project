// "Công khai" switch of the Studio editor and the visibility badge of the Studio list (docs/auth.md
// §4.3, §4.5, §7.3). Pure, tested in shareLogic.test.ts.
import type { BadgeTone } from "../../components/ui/Chip.tsx";
import type { Visibility } from "../../types.ts";

export const PUBLIC_LABEL = "Công khai";
export const PRIVATE_LABEL = "Riêng tư";

function nameOf(name: string): string {
  return name.trim() || "nhân vật này";
}

/** Templates ship with Lyris for everyone: the switch is hidden for them (the server refuses anyway). */
export function canShare(opts: { template: boolean }): boolean {
  return !opts.template;
}

export function isPublic(visibility: Visibility | null | undefined): boolean {
  return visibility === "public";
}

/**
 * What the switch promises. Only "not in the profile": the character may still tell what it knows
 * while chatting (§4.5), so it never says others cannot learn the secrets.
 */
export function shareDescription(name: string): string {
  const n = nameOf(name);
  return (
    `Người khác trên Lyris này thấy ${n} ở Khám phá và bắt đầu story riêng với ${n}. ` +
    `Họ không sửa được, và không xem được bí mật, mục tiêu hay sổ thế giới trong hồ sơ. ` +
    `Khi trò chuyện, ${n} vẫn có thể tự kể ra điều mình biết. Story của bạn luôn riêng tư.`
  );
}

/** The reminder after turning a public character back to private (null otherwise). */
export function unshareNote(name: string, opts: { checked: boolean; savedPublic: boolean }): string | null {
  if (opts.checked || !opts.savedPublic) return null;
  return `Story mà người khác đã bắt đầu vẫn tiếp tục với ${nameOf(name)} như lúc họ bắt đầu.`;
}

/** Studio list badge: "Công khai" (accent) when shared, "Riêng tư" otherwise; none for a template. */
export function visibilityBadge(opts: { template: boolean; visibility: Visibility | null | undefined }): { label: string; tone: BadgeTone } | null {
  if (opts.template) return null;
  return isPublic(opts.visibility) ? { label: PUBLIC_LABEL, tone: "accent" } : { label: PRIVATE_LABEL, tone: "neutral" };
}
