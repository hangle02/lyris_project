import { useId } from "react";
import type { CSSProperties } from "react";
import { Button, cx } from "../../components/ui";
import {
  DEFAULT_INITIAL_RELATIONSHIP,
  EMOTION_HINT,
  EMOTION_KEYS,
  EMOTION_LABEL,
  isDefaultRelationship,
  readInitialRelationship,
  withInitialRelationship,
} from "../../lib/cardForm";
import type { CharacterCard, EmotionKey } from "../../types";
import type { CardUpdater } from "./CardForm";
import { Section } from "./ui";

const THUMB = 24;

/** Width of the coloured fill so its end sits under the centre of the native thumb. */
function fillWidth(value: number): string {
  const v = value / 100;
  return `calc(${value}% + ${(0.5 - v) * THUMB}px)`;
}

const RANGE_CLASS = cx(
  "absolute inset-0 h-11 w-full cursor-pointer appearance-none rounded-full bg-transparent disabled:cursor-not-allowed",
  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent",
  "[&::-webkit-slider-runnable-track]:h-11 [&::-webkit-slider-runnable-track]:bg-transparent",
  "[&::-webkit-slider-thumb]:mt-[10px] [&::-webkit-slider-thumb]:h-6 [&::-webkit-slider-thumb]:w-6 [&::-webkit-slider-thumb]:appearance-none",
  "[&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-surface [&::-webkit-slider-thumb]:bg-fg",
  "[&::-moz-range-track]:bg-transparent [&::-moz-range-thumb]:h-5 [&::-moz-range-thumb]:w-5 [&::-moz-range-thumb]:rounded-full",
  "[&::-moz-range-thumb]:border-2 [&::-moz-range-thumb]:border-surface [&::-moz-range-thumb]:bg-fg",
);

function EmotionSlider({
  emotion,
  value,
  onChange,
  disabled,
}: {
  emotion: EmotionKey;
  value: number;
  onChange: (v: number) => void;
  disabled: boolean;
}) {
  const id = useId();
  const hintId = useId();
  const color = `var(--color-emo-${emotion})`;
  const fill: CSSProperties = { width: fillWidth(value), backgroundColor: color };
  return (
    <div className="flex min-w-0 flex-col">
      <div className="flex items-baseline gap-3">
        <label htmlFor={id} className="min-w-0 flex-1 text-[14px] leading-tight font-medium text-fg">
          {EMOTION_LABEL[emotion]}
        </label>
        <span aria-hidden="true" className="text-[14px] leading-tight text-fg tabular-nums">
          {value}
        </span>
      </div>
      <div className={cx("relative h-11", disabled && "opacity-60")}>
        <div aria-hidden="true" className="absolute inset-x-0 top-1/2 h-2 -translate-y-1/2 overflow-hidden rounded-full bg-surface-3">
          <div className="h-full rounded-full" style={fill} />
        </div>
        <input
          id={id}
          type="range"
          min={0}
          max={100}
          step={1}
          value={value}
          disabled={disabled}
          onChange={(e) => onChange(Number(e.target.value))}
          aria-describedby={hintId}
          aria-valuetext={`${value} trên 100`}
          className={RANGE_CLASS}
        />
      </div>
      <p id={hintId} className="text-[13px] leading-snug text-muted">
        {EMOTION_HINT[emotion]}
      </p>
    </div>
  );
}

/**
 * "Cảm xúc ban đầu": six 0-100 sliders stored at extensions.lyris.initial_relationship, the point a
 * new story's emotion matrix starts from. Other extension data is never touched.
 */
export function EmotionSection({
  card,
  update,
  disabled,
}: {
  card: CharacterCard;
  update: CardUpdater;
  disabled: boolean;
}) {
  const { values } = readInitialRelationship(card);
  const atDefault = isDefaultRelationship(values);
  return (
    <Section
      id="sec-emotions"
      title="Cảm xúc ban đầu"
      hint={`Điểm xuất phát của sáu chỉ số cảm xúc trong mỗi story mới với ${card.name.trim() || "nhân vật này"}, từ 0 đến 100.`}
      aside={
        <Button
          variant="ghost"
          size="sm"
          disabled={disabled || atDefault}
          onClick={() => update((c) => withInitialRelationship(c, DEFAULT_INITIAL_RELATIONSHIP))}
          className="-mt-1.5 -mr-2"
        >
          Về mặc định
        </Button>
      }
    >
      <div className="grid gap-x-8 gap-y-4 sm:grid-cols-2">
        {EMOTION_KEYS.map((k) => (
          <EmotionSlider
            key={k}
            emotion={k}
            value={values[k]}
            disabled={disabled}
            onChange={(v) => update((c) => withInitialRelationship(c, { [k]: v }))}
          />
        ))}
      </div>
    </Section>
  );
}
