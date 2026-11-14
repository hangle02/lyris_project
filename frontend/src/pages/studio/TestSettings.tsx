import { useId, useState } from "react";
import { ChoiceGroup } from "../../components/ui";
import { IconChevronDown } from "../../components/icons";
import { Button, Select, TextField, cx } from "../../components/ui";
import { LANGUAGE_LABEL } from "../../lib/cardForm";
import type { SettingsOverrides } from "../../lib/cardForm";
import { routeHref } from "../../lib/router";
import type { Language, Mode, Pov, PersonaOut, RelationshipType, StorySettings, ThoughtStyle } from "../../types";

export const RELATIONSHIP_LABEL: Record<RelationshipType, string> = {
  het: "Nam-nữ",
  bl: "Nam-nam",
  gl: "Nữ-nữ",
  none: "Không lãng mạn",
};

const THOUGHT_LABEL: Record<ThoughtStyle, string> = { inline: "Thought lồng", end: "Thought cuối" };

/**
 * Persona + story settings used by "Xem trước prompt" and "Chat thử" (shared, so both show the same
 * thing). Values follow the card's defaults until the user changes one; "Về mặc định" drops overrides.
 */
export function TestSettings({
  personas,
  personaId,
  onPersona,
  settings,
  overrides,
  onOverrides,
  cardLanguage,
  disabled,
}: {
  personas: PersonaOut[] | null;
  personaId: number | null;
  onPersona: (id: number) => void;
  settings: StorySettings | null;
  overrides: SettingsOverrides;
  onOverrides: (o: SettingsOverrides) => void;
  cardLanguage: Language;
  disabled: boolean;
}) {
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const persona = personas?.find((p) => p.id === personaId) ?? null;
  const set = (patch: SettingsOverrides) => onOverrides({ ...overrides, ...patch });
  const touched = Object.values(overrides).some((v) => v !== undefined);

  if (personas !== null && personas.length === 0) {
    return (
      <div className="flex items-start gap-3 rounded-control bg-warn/10 px-4 py-3 text-[14px] leading-snug text-fg">
        <span aria-hidden="true" className="mt-[7px] h-2 w-2 shrink-0 rounded-full bg-warn" />
        <p>
          Chưa có persona nào để thử. Tạo một persona (nhân vật của bạn) ở{" "}
          <a href={routeHref({ name: "personas" })} className="font-medium text-accent underline underline-offset-2">
            trang Persona
          </a>
          .
        </p>
      </div>
    );
  }

  const summary = settings
    ? [
        persona?.name ?? "…",
        LANGUAGE_LABEL[settings.language],
        settings.mode === "story" ? "Story" : "DM",
        RELATIONSHIP_LABEL[settings.relationship_type],
        settings.mode === "story" ? THOUGHT_LABEL[settings.thought_style] : null,
      ]
        .filter(Boolean)
        .join(" · ")
    : "Đang tải…";

  return (
    <div className="rounded-card border border-edge bg-surface">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-controls={panelId}
        className="flex min-h-12 w-full items-center gap-3 rounded-card px-4 py-2 text-left"
      >
        <span className="min-w-0 flex-1">
          <span className="block text-[13px] leading-tight text-muted">Thiết lập thử</span>
          <span className="mt-0.5 block truncate text-[14px] leading-tight font-medium text-fg">{summary}</span>
        </span>
        <IconChevronDown
          aria-hidden="true"
          className={cx("shrink-0 text-[18px] text-muted transition-transform duration-150", open && "rotate-180")}
        />
      </button>
      {open && settings && (
        <div
          id={panelId}
          className="scroll-thin flex max-h-[min(34rem,58dvh)] flex-col gap-4 overflow-y-auto border-t border-line px-4 pt-4 pb-4"
        >
          <Select
            label="Persona (nhân vật của bạn)"
            value={personaId === null ? "" : String(personaId)}
            onChange={(v) => onPersona(Number(v))}
            disabled={disabled || !personas}
            options={(personas ?? [])
              .filter((p) => p.id !== null)
              .map((p) => ({ value: String(p.id), label: p.name }))}
          />
          <div className="grid grid-cols-1 gap-4 min-[420px]:grid-cols-2">
            <ChoiceGroup<Language>
              label="Ngôn ngữ"
              value={settings.language}
              onChange={(v) => set({ language: v, narration_character: undefined, narration_player: undefined })}
              disabled={disabled}
              options={[
                { value: "vi", label: "Tiếng Việt" },
                { value: "en", label: "English" },
              ]}
              hint={settings.language !== cardLanguage ? `Khác ngôn ngữ của card (${LANGUAGE_LABEL[cardLanguage]}).` : undefined}
            />
            <ChoiceGroup<Mode>
              label="Chế độ"
              value={settings.mode}
              onChange={(v) => set({ mode: v })}
              disabled={disabled}
              options={[
                { value: "story", label: "Story" },
                { value: "dm", label: "DM" },
              ]}
            />
          </div>
          <Select<RelationshipType>
            label="Kiểu quan hệ"
            value={settings.relationship_type}
            onChange={(v) => set({ relationship_type: v })}
            disabled={disabled}
            options={(Object.keys(RELATIONSHIP_LABEL) as RelationshipType[]).map((k) => ({
              value: k,
              label: RELATIONSHIP_LABEL[k],
            }))}
          />
          <div className="grid grid-cols-1 gap-4 min-[420px]:grid-cols-2">
            <ChoiceGroup<Pov>
              label="Ngôi kể"
              value={settings.pov}
              onChange={(v) => set({ pov: v })}
              disabled={disabled}
              options={[
                { value: "third", label: "Thứ ba" },
                { value: "first", label: "Thứ nhất" },
              ]}
            />
            <ChoiceGroup<ThoughtStyle>
              label="Suy nghĩ (Thought)"
              value={settings.thought_style}
              onChange={(v) => set({ thought_style: v })}
              disabled={disabled || settings.mode === "dm"}
              options={[
                { value: "inline", label: "Lồng" },
                { value: "end", label: "Ở cuối" },
              ]}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <TextField
              label="Dẫn truyện gọi nhân vật"
              value={settings.narration_pronouns.character}
              onChange={(v) => set({ narration_character: v })}
              disabled={disabled}
              autoComplete="off"
            />
            <TextField
              label={`Gọi ${persona?.name ?? "người chơi"}`}
              value={settings.narration_pronouns.player}
              onChange={(v) => set({ narration_player: v })}
              disabled={disabled}
              autoComplete="off"
            />
          </div>
          <div className="flex items-center justify-between gap-3">
            <p className="text-[13px] leading-snug text-muted">Bối cảnh lấy từ “Bối cảnh mặc định” của card.</p>
            <Button variant="ghost" size="sm" onClick={() => onOverrides({})} disabled={disabled || !touched} className="-mr-2">
              Về mặc định
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
