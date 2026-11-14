import { useState } from "react";
import { IconEye } from "../../components/icons";
import { cx } from "../../components/ui";
import { spaceAfterHorn } from "../../lib/text";
import { trackInStory } from "../../lib/track";
import { useRevealThoughts } from "./revealThoughts";

interface Props {
  /** The thought, paragraphs separated by blank lines. */
  text: string;
  /** Still being written: shows the caret on the last paragraph. */
  streaming?: boolean;
  /** Smaller type for the DM thread. */
  compact?: boolean;
  className?: string;
}

/**
 * "Tiếng lòng giấu kín": the character's inner thought. A 3px accent edge on a flat accent tint.
 * Blurred by default with "Chạm để lắng nghe"; a tap (or Enter / Space) reveals it, another tap
 * hides it again. With "Luôn hiện suy nghĩ" on it is plain text. Streaming thoughts follow the same rule.
 */
export function ThoughtCard({ text, streaming = false, compact = false, className }: Props) {
  const [always] = useRevealThoughts();
  const [open, setOpen] = useState(false);
  const paras = spaceAfterHorn(text).split(/\n{2,}/).map((p) => p.trim()).filter(Boolean);
  const revealed = always || open;

  const body = (
    <span
      aria-hidden={revealed ? undefined : true}
      className={cx(
        "block font-story italic text-thought transition-[filter,opacity] duration-300 ease-out motion-reduce:transition-none",
        compact ? "text-[15px] leading-normal" : "text-[16px]",
        !revealed && "blur-[3px] opacity-80 select-none",
      )}
    >
      {paras.map((p, i) => (
        <span
          key={i}
          className={cx("block [overflow-wrap:anywhere] whitespace-pre-wrap", i > 0 && "mt-[0.6em]", streaming && i === paras.length - 1 && "caret")}
        >
          {p}
        </span>
      ))}
      {paras.length === 0 && <span className={cx("block", streaming && "caret")}>…</span>}
    </span>
  );

  const shell = cx(
    "relative block w-full rounded-r-control border-l-[3px] border-accent text-left",
    "bg-[color-mix(in_oklab,var(--color-accent)_8%,var(--color-surface))]",
    compact ? "px-3.5 py-2.5" : "px-4 py-3",
    className,
  );

  if (always) {
    return (
      <div className={shell}>
        <span className="sr-only">Suy nghĩ: </span>
        {body}
      </div>
    );
  }

  return (
    <button
      type="button"
      aria-pressed={open}
      onClick={() => {
        // Usage: a thought was opened (in a story only; never its words).
        if (!open) trackInStory("thought_revealed");
        setOpen((o) => !o);
      }}
      className={cx(shell, "group cursor-pointer")}
    >
      <span className="sr-only">{open ? "Suy nghĩ (chạm để giấu lại): " : "Suy nghĩ đang giấu. "}</span>
      {body}
      {!open && (
        <span className="absolute inset-0 flex items-center justify-center">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface px-3 py-1 text-[13px] font-medium text-fg transition-colors group-hover:bg-surface-2">
            <IconEye className="text-[15px] text-accent" />
            Chạm để lắng nghe
          </span>
        </span>
      )}
    </button>
  );
}
