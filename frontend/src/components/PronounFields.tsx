import { useId } from "react";
import type { NarrationPronouns, Pov } from "../types";
import { Button } from "./ui/Button";
import { CONTROL_CLASS } from "./ui/fields";

interface Props {
  value: NarrationPronouns;
  onChange: (v: NarrationPronouns) => void;
  characterName: string;
  personaName: string;
  pov: Pov;
  /** Suggested pronouns from the style profile (null while unknown). */
  suggestion: NarrationPronouns | null;
  disabled?: boolean;
}

/** "Đại từ dẫn truyện": how the narration calls the character and the player. */
export function PronounFields({ value, onChange, characterName, personaName, pov, suggestion, disabled }: Props) {
  const charId = useId();
  const playerId = useId();
  const hintId = useId();
  const differs =
    suggestion !== null &&
    (suggestion.character !== value.character.trim() || suggestion.player !== value.player.trim());

  return (
    <fieldset className="flex min-w-0 flex-col gap-2">
      <legend className="mb-2 text-[14px] leading-tight font-medium text-fg">Đại từ dẫn truyện</legend>
      <div className="grid min-w-0 grid-cols-2 gap-3">
        <label htmlFor={charId} className="flex min-w-0 flex-col gap-1.5">
          <span className="truncate text-[13px] text-muted">{characterName || "Nhân vật"}</span>
          <input
            id={charId}
            value={value.character}
            onChange={(e) => onChange({ ...value, character: e.target.value })}
            maxLength={40}
            disabled={disabled}
            placeholder={pov === "first" ? "tôi" : "anh"}
            aria-describedby={hintId}
            className={CONTROL_CLASS}
          />
        </label>
        <label htmlFor={playerId} className="flex min-w-0 flex-col gap-1.5">
          <span className="truncate text-[13px] text-muted">{personaName || "Người chơi"}</span>
          <input
            id={playerId}
            value={value.player}
            onChange={(e) => onChange({ ...value, player: e.target.value })}
            maxLength={40}
            disabled={disabled}
            placeholder="cô"
            aria-describedby={hintId}
            className={CONTROL_CLASS}
          />
        </label>
      </div>
      <p id={hintId} className="text-[13px] leading-snug text-muted">
        Dùng trong phần kể, ngoài lời thoại và Thought.
        {pov === "first" ? " Ngôi thứ nhất: nhân vật tự xưng khi kể." : ""}
      </p>
      {differs && suggestion && (
        <Button
          size="sm"
          variant="secondary"
          disabled={disabled}
          onClick={() => onChange({ ...suggestion })}
          className="self-start"
        >
          Dùng gợi ý: {suggestion.character} / {suggestion.player}
        </Button>
      )}
    </fieldset>
  );
}
