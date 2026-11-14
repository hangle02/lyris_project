import { forwardRef, useCallback, useImperativeHandle, useLayoutEffect, useRef } from "react";
import type { TextareaHTMLAttributes } from "react";

interface Props extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  value: string;
  /** Max height in px before the textarea scrolls. */
  maxHeight?: number;
}

/** Textarea that grows with its content up to maxHeight. */
export const AutoTextarea = forwardRef<HTMLTextAreaElement, Props>(function AutoTextarea(
  { value, maxHeight = 240, style, ...rest },
  ref,
) {
  const inner = useRef<HTMLTextAreaElement>(null);
  useImperativeHandle(ref, () => inner.current as HTMLTextAreaElement);

  const resize = useCallback(() => {
    const el = inner.current;
    if (!el) return;
    el.style.height = "auto";
    const h = Math.min(el.scrollHeight, maxHeight);
    el.style.height = `${h}px`;
    el.style.overflowY = el.scrollHeight > maxHeight ? "auto" : "hidden";
  }, [maxHeight]);

  useLayoutEffect(resize, [value, resize]);

  return <textarea ref={inner} value={value} rows={1} style={{ resize: "none", ...style }} {...rest} />;
});
