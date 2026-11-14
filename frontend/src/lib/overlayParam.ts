// "?open=system" / "?open=heart" / "?open=profile" trên URL (phần search, trước dấu #) mở sẵn một lớp phủ khi tải trang.
// Chỉ dùng để chụp ảnh kiểm tra (giống "?theme="): không lưu, không đổi hash, không ảnh hưởng điều hướng.

export type OverlayName = "system" | "heart" | "settings" | "profile" | "events" | "about";

const OVERLAYS: readonly OverlayName[] = ["system", "heart", "settings", "profile", "events", "about"];

/** Lớp phủ được yêu cầu trong chuỗi search ("?open=heart"), hoặc null nếu không có / không hợp lệ. */
export function overlayFromSearch(search: string): OverlayName | null {
  let value: string | null;
  try {
    value = new URLSearchParams(search).get("open");
  } catch {
    return null;
  }
  if (value === null) return null;
  const v = value.trim().toLowerCase();
  return (OVERLAYS as readonly string[]).includes(v) ? (v as OverlayName) : null;
}

/** True khi URL hiện tại yêu cầu mở sẵn lớp phủ `name` (an toàn khi không có window). */
export function initialOverlayOpen(name: OverlayName): boolean {
  if (typeof window === "undefined") return false;
  return overlayFromSearch(window.location.search) === name;
}

/** Giá trị "?tab=" (chữ thường, đã cắt khoảng trắng) nếu nằm trong `allowed`, không thì null. */
export function tabFromSearch<T extends string>(search: string, allowed: readonly T[]): T | null {
  let value: string | null;
  try {
    value = new URLSearchParams(search).get("tab");
  } catch {
    return null;
  }
  if (value === null) return null;
  const v = value.trim().toLowerCase();
  return (allowed as readonly string[]).includes(v) ? (v as T) : null;
}

/** Tab mở sẵn theo "?tab=" của URL hiện tại (chỉ để chụp ảnh kiểm tra), hoặc `fallback`. */
export function initialTab<T extends string>(allowed: readonly T[], fallback: T): T {
  if (typeof window === "undefined") return fallback;
  return tabFromSearch(window.location.search, allowed) ?? fallback;
}
