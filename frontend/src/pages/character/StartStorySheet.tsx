import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AI_DISCLAIMER } from "../../lib/compliance";
import type { FormEvent, ReactNode, RefObject } from "react";
import { api, errorMessage, errorTechnical } from "../../api/client";
import { Avatar } from "../../components/Avatar";
import { IconPlus } from "../../components/icons";
import { PronounFields } from "../../components/PronounFields";
import { StoryReply } from "../../components/Prose";
import { Button, ChoiceGroup, Disclosure, Field, InlineAlert, Modal, Skeleton, TextArea, TextField, Toggle } from "../../components/ui";
import { cx } from "../../components/ui/logic";
import { routeHref } from "../../lib/router";
import {
  fillPlaceholders,
  GENDER_LABELS,
  greetingAt,
  LANGUAGE_OPTIONS,
  labelOf,
  MODE_OPTIONS,
  POV_OPTIONS,
  RELATIONSHIP_OPTIONS,
  SHOW_THOUGHTS_LABEL,
  showThoughtsHint,
  suggestPronouns,
  THOUGHT_STYLE_OPTIONS,
} from "../../lib/storyOptions";
import { splitSegments } from "../../lib/text";
import type { CharacterCard, Gender, PersonaOut, StoryOut, StorySettings, StyleProfileInfo } from "../../types";
import { defaultPersonaId } from "../personaLogic";
import { ENTER_LABEL } from "./logic";
import { createRequest, draftFromDefaults, draftProblems, greetingChoices, mergeSettings, rebaseDraft } from "./startLogic";
import type { StoryDraft } from "./startLogic";

const GENDER_OPTIONS: { value: Gender; label: string }[] = [
  { value: "female", label: GENDER_LABELS.female },
  { value: "male", label: GENDER_LABELS.male },
  { value: "other", label: GENDER_LABELS.other },
];

interface Props {
  open: boolean;
  onClose: () => void;
  /** The character's full card (a template's card before it is installed). */
  card: CharacterCard;
  /** Saved card id; null for a template that is not installed yet. */
  cardId: number | null;
  /** Installs the template (or returns the saved id); called before the first request needing an id. */
  ensureCardId: () => Promise<number>;
  styles: StyleProfileInfo[];
  /** Called with the new story; the page opens it. */
  onCreated: (story: StoryOut) => void;
  /** Phase 4b: one 13px line for someone else's character ("Bạn chơi với … như bây giờ…"). */
  note?: string | null;
}

interface Failure {
  text: string;
  technical: string | null;
}

function failure(e: unknown): Failure {
  return { text: errorMessage(e), technical: errorTechnical(e) };
}

/** Radio pill for small choices (greeting): a tone step, selected = accent tint with an accent ring. */
function RadioPill({ on, onClick, children }: { on: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={on}
      onClick={onClick}
      className={cx(
        "inline-flex min-h-9 max-w-full items-center rounded-full px-3.5 text-[14px] font-medium transition-colors duration-150 max-sm:min-h-11",
        on ? "bg-accent/15 text-fg ring-1 ring-inset ring-accent/60" : "bg-surface-2 text-muted hover:bg-surface-3 hover:text-fg",
      )}
    >
      {children}
    </button>
  );
}

/** One persona as a native radio (arrow keys move between them), avatar, name, gender and a line about them. */
function PersonaOption({
  persona,
  name,
  checked,
  onPick,
  inputRef,
}: {
  persona: PersonaOut;
  name: string;
  checked: boolean;
  onPick: () => void;
  inputRef?: RefObject<HTMLInputElement>;
}) {
  return (
    <label
      className={cx(
        "relative flex min-h-14 cursor-pointer items-center gap-3 rounded-control px-3 py-2 transition-colors duration-150",
        "has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-accent",
        checked ? "bg-accent/12 ring-1 ring-inset ring-accent/60" : "hover:bg-surface-2",
      )}
    >
      <input ref={inputRef} type="radio" name={name} checked={checked} onChange={onPick} className="sr-only" />
      <Avatar name={persona.name} url={persona.avatar_url} size={40} />
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[15px] leading-snug font-semibold text-fg">{persona.name}</span>
        <span className="block truncate text-[13px] leading-snug text-muted">
          {GENDER_LABELS[persona.gender]}
          {persona.description.trim() ? ` · ${persona.description.trim()}` : ""}
        </span>
      </span>
      <span
        aria-hidden="true"
        className={cx(
          "flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2",
          checked ? "border-accent" : "border-line-strong",
        )}
      >
        {checked && <span className="h-2.5 w-2.5 rounded-full bg-accent" />}
      </span>
    </label>
  );
}

/** A persona in a few fields, without leaving the sheet. */
function QuickPersona({ startOpen, onCreated }: { startOpen: boolean; onCreated: (p: PersonaOut) => void }) {
  const [open, setOpen] = useState(startOpen);
  const [name, setName] = useState("");
  const [gender, setGender] = useState<Gender>("female");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<Failure | null>(null);

  if (!open) {
    return (
      <Button size="sm" variant="ghost" icon={<IconPlus />} onClick={() => setOpen(true)} className="max-sm:h-11">
        Tạo persona mới
      </Button>
    );
  }

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const n = name.trim();
    if (!n || saving) return;
    setSaving(true);
    setError(null);
    try {
      const created = await api.createPersona({ id: null, name: n, gender, description: description.trim() });
      onCreated(created);
      setOpen(false);
      setName("");
      setDescription("");
    } catch (err) {
      setError(failure(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <form
      aria-label="Tạo persona mới"
      onSubmit={(e) => void submit(e)}
      className="flex w-full flex-col gap-4 rounded-card border border-edge bg-bg p-4"
    >
      <TextField label="Tên persona" value={name} onChange={setName} maxLength={80} disabled={saving} />
      <ChoiceGroup label="Giới tính" options={GENDER_OPTIONS} value={gender} onChange={setGender} disabled={saving} />
      <TextArea
        label="Mô tả (tuỳ chọn)"
        value={description}
        onChange={setDescription}
        placeholder="Tuổi, nghề nghiệp, tính cách, quan hệ với nhân vật…"
        disabled={saving}
      />
      {error && <InlineAlert tone="error" text={error.text} technical={error.technical} />}
      <div className="flex justify-end gap-2">
        {!startOpen && (
          <Button size="sm" variant="ghost" onClick={() => setOpen(false)} disabled={saving}>
            Huỷ
          </Button>
        )}
        <Button size="sm" type="submit" disabled={!name.trim()} loading={saving}>
          Tạo persona
        </Button>
      </div>
    </form>
  );
}

/**
 * "Bước vào câu chuyện" (bottom sheet on phones, dialog from 640px): pick the persona (the default one
 * preselected), optionally open "Tuỳ chỉnh story" for the settings the old new-story page had, then
 * start. A template is installed only when a request needs its card id.
 */
export function StartStorySheet({ open, onClose, card, cardId, ensureCardId, styles, onCreated, note = null }: Props) {
  const [personas, setPersonas] = useState<PersonaOut[] | null>(null);
  const [listError, setListError] = useState<Failure | null>(null);
  const [personaId, setPersonaId] = useState<number | null>(null);
  const [customizing, setCustomizing] = useState(false);
  const [draft, setDraft] = useState<StoryDraft | null>(null);
  const [loadingDefaults, setLoadingDefaults] = useState(false);
  const [defaultsError, setDefaultsError] = useState<Failure | null>(null);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<Failure | null>(null);
  const defaultsReq = useRef(0);
  // The defaults the current draft started from and the persona they were for. The sheet stays
  // mounted while closed, so a reopen with the same persona keeps the draft as the user left it, and a
  // persona change keeps what the user changed (see rebaseDraft).
  const draftBase = useRef<{ personaId: number; base: StoryDraft } | null>(null);
  const draftRef = useRef<StoryDraft | null>(null);
  draftRef.current = draft;
  // Focus starts on the chosen persona (the sheet's question). On the first open the list is still
  // loading when the overlay places focus, so it moves there once the list arrives, unless the
  // person has already started typing in a field.
  const checkedRadio = useRef<HTMLInputElement>(null);
  const focusedOnLoad = useRef(false);
  const radioName = `persona-${cardId ?? "template"}`;

  const loadPersonas = useCallback(async () => {
    setListError(null);
    try {
      const [list, settings] = await Promise.all([api.listPersonas(), api.getSettings().catch(() => null)]);
      setPersonas(list);
      setPersonaId((cur) => (cur !== null && list.some((p) => p.id === cur) ? cur : defaultPersonaId(list, settings?.default_persona_id)));
    } catch (e) {
      setListError(failure(e));
    }
  }, []);

  useEffect(() => {
    if (open && personas === null) void loadPersonas();
  }, [open, personas, loadPersonas]);

  useEffect(() => {
    if (!open) {
      focusedOnLoad.current = false;
      return;
    }
    if (focusedOnLoad.current || personas === null || personaId === null) return;
    focusedOnLoad.current = true;
    const radio = checkedRadio.current;
    const active = document.activeElement;
    const typing = active instanceof HTMLInputElement ? active.type !== "radio" : active instanceof HTMLTextAreaElement;
    if (radio && !typing && radio.closest("[role=dialog]")?.contains(active)) radio.focus({ preventScroll: true });
  }, [open, personas, personaId]);

  const persona = useMemo(() => personas?.find((p) => p.id === personaId) ?? null, [personas, personaId]);
  const profile = useMemo(() => styles.find((s) => s.name === card.style_profile) ?? null, [styles, card.style_profile]);

  const suggestWith = useCallback(
    (who: PersonaOut | null | undefined, s: StorySettings) =>
      who
        ? suggestPronouns({
            profile,
            language: s.language,
            pov: s.pov,
            cardGender: card.gender,
            cardName: card.name,
            personaGender: who.gender,
            personaName: who.name,
          })
        : null,
    [card.gender, card.name, profile],
  );
  const suggestionFor = useCallback((s: StorySettings) => suggestWith(persona, s), [suggestWith, persona]);

  // "Tuỳ chỉnh story" open + a persona: the defaults POST /api/stories would use (they depend on both).
  // With a draft already there (another persona picked), the user's changes are carried over.
  const loadDefaults = useCallback(
    async (pId: number) => {
      const req = ++defaultsReq.current;
      setLoadingDefaults(true);
      setDefaultsError(null);
      try {
        const id = await ensureCardId();
        const defaults = await api.storyDefaults(id, pId);
        if (req !== defaultsReq.current) return;
        const fresh = draftFromDefaults(defaults, card.greeting);
        const prev = draftBase.current;
        const before = prev ? personas?.find((p) => p.id === prev.personaId) : null;
        const after = personas?.find((p) => p.id === pId);
        setDraft((cur) =>
          cur && prev
            ? rebaseDraft(cur, prev.base, fresh, suggestWith(before, cur.settings), (s) => suggestWith(after, s))
            : fresh,
        );
        draftBase.current = { personaId: pId, base: fresh };
      } catch (e) {
        if (req !== defaultsReq.current) return;
        // A draft the user already edited stays (starting waits until the defaults load).
        setDefaultsError(failure(e));
      } finally {
        if (req === defaultsReq.current) setLoadingDefaults(false);
      }
    },
    [ensureCardId, card.greeting, personas, suggestWith],
  );

  useEffect(() => {
    if (!open || !customizing || personaId === null) {
      defaultsReq.current++;
      setLoadingDefaults(false);
      return;
    }
    // Reopened (or the disclosure toggled again) with the same persona: keep the draft as it is.
    if (draftRef.current && draftBase.current?.personaId === personaId) return;
    void loadDefaults(personaId);
    // Not on loadDefaults: it changes with the persona list, which alone is no reason to refetch.
  }, [open, customizing, personaId]);

  const updateSettings = (next: Partial<StorySettings>) =>
    setDraft((cur) => (cur ? { ...cur, settings: mergeSettings(cur.settings, next, suggestionFor) } : cur));

  const problems = customizing ? draftProblems(draft) : [];
  const canStart =
    personaId !== null &&
    !creating &&
    !(customizing && (loadingDefaults || !draft || defaultsError)) &&
    problems.length === 0;

  const start = async () => {
    if (!canStart || personaId === null) return;
    setCreating(true);
    setCreateError(null);
    try {
      const id = await ensureCardId();
      const story = await api.createStoryFor(createRequest(id, personaId, customizing ? draft : null));
      onCreated(story);
    } catch (e) {
      setCreateError(failure(e));
      setCreating(false);
    }
  };

  const choices = greetingChoices(card.greeting, card.alternate_greetings);
  const greetingText =
    draft && persona ? fillPlaceholders(greetingAt(card.greeting, card.alternate_greetings, draft.greetingIndex), card.name, persona.name) : "";
  const languageHint =
    draft && draft.settings.language !== card.language
      ? `${card.name} được viết bằng ${labelOf(LANGUAGE_OPTIONS, card.language).toLowerCase()}. Nhân vật sẽ tự chuyển ngôn ngữ; lời mở đầu vẫn giữ nguyên văn.`
      : undefined;

  const footer = (
    <div className="flex w-full flex-col gap-2 sm:items-end">
      {!createError && problems.length > 0 && <p className="text-[13px] leading-snug text-warn">{problems.join(" ")}</p>}
      <Button variant="primary" block onClick={() => void start()} disabled={!canStart} loading={creating} className="sm:w-auto">
        {ENTER_LABEL}
      </Button>
      <p className="text-center text-[12px] leading-snug text-muted sm:text-right">{AI_DISCLAIMER}</p>
    </div>
  );

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Chọn persona"
      description={`Bạn sẽ là ai khi gặp ${card.name}?`}
      dismissible={!creating}
      footer={footer}
      initialFocusRef={checkedRadio}
    >
      <div className="flex flex-col gap-6">
        {note && <p className="-mt-2 text-[13px] leading-snug text-muted">{note}</p>}
        <section aria-label="Persona" className="flex flex-col gap-2">
          {listError && <InlineAlert tone="error" text={listError.text} technical={listError.technical} onRetry={() => void loadPersonas()} />}
          {personas === null ? (
            !listError && (
              <div aria-busy="true" className="flex flex-col gap-2">
                <span className="sr-only">Đang tải persona…</span>
                <Skeleton shape="card" height={56} />
                <Skeleton shape="card" height={56} />
              </div>
            )
          ) : (
            <>
              {personas.length > 0 && (
                <div role="radiogroup" aria-label="Persona" className="flex flex-col gap-1.5">
                  {personas.map((p) => (
                    <PersonaOption
                      key={p.id}
                      persona={p}
                      name={radioName}
                      checked={p.id === personaId}
                      onPick={() => setPersonaId(p.id)}
                      inputRef={p.id === personaId ? checkedRadio : undefined}
                    />
                  ))}
                </div>
              )}
              {personas.length === 0 && (
                <p className="text-[14px] leading-snug text-muted">Bạn chưa có persona nào. Tạo một persona để bước vào story.</p>
              )}
              <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
                <QuickPersona
                  startOpen={personas.length === 0}
                  onCreated={(p) => {
                    setPersonas((list) => [...(list ?? []).filter((x) => x.id !== p.id), p]);
                    setPersonaId(p.id);
                  }}
                />
                <a
                  href={routeHref({ name: "personas" })}
                  className="inline-flex min-h-11 items-center text-[14px] font-medium text-muted underline underline-offset-4 transition-colors duration-150 hover:text-fg"
                >
                  Quản lý persona
                </a>
              </div>
            </>
          )}
        </section>

        <Disclosure
          title="Tuỳ chỉnh story"
          hint="Bối cảnh, chế độ Story hay DM, ngôi kể, cách hiện suy nghĩ."
          open={customizing}
          onToggle={setCustomizing}
          className="border-t border-line pt-3"
        >
          {personaId === null ? (
            <p className="text-[14px] text-muted">Chọn một persona trước.</p>
          ) : defaultsError ? (
            <InlineAlert
              tone="error"
              text={defaultsError.text}
              technical={defaultsError.technical}
              onRetry={() => void loadDefaults(personaId)}
            />
          ) : !draft || !persona ? (
            <div aria-busy="true" className="flex flex-col gap-4">
              <span className="sr-only">Đang chuẩn bị thiết lập…</span>
              <Skeleton height={44} />
              <Skeleton height={96} />
              <Skeleton height={44} />
            </div>
          ) : (
            <div className={cx("flex flex-col gap-6", loadingDefaults && "opacity-60")} aria-busy={loadingDefaults}>
              <TextField
                label="Tiêu đề"
                value={draft.title}
                onChange={(title) => setDraft((d) => (d ? { ...d, title } : d))}
                maxLength={120}
              />
              <TextArea
                label="Bối cảnh"
                value={draft.settings.scenario}
                onChange={(scenario) => updateSettings({ scenario })}
                placeholder="Nơi chốn, thời điểm, hoàn cảnh hai người đang ở…"
                hint="Lấy từ bối cảnh mặc định của nhân vật; sửa tuỳ ý cho story này."
              />
              <Field label="Lời mở đầu">
                <div role="radiogroup" aria-label="Lời mở đầu" className="flex flex-wrap gap-2">
                  {choices.map((g) => (
                    <RadioPill
                      key={g.index}
                      on={draft.greetingIndex === g.index}
                      onClick={() => setDraft((d) => (d ? { ...d, greetingIndex: g.index } : d))}
                    >
                      {g.label}
                    </RadioPill>
                  ))}
                  <RadioPill on={draft.greetingIndex === -1} onClick={() => setDraft((d) => (d ? { ...d, greetingIndex: -1 } : d))}>
                    Không có
                  </RadioPill>
                </div>
                {greetingText.trim() ? (
                  <div className="scroll-thin mt-2 max-h-[32dvh] overflow-y-auto rounded-card border border-edge bg-bg px-4 py-3.5">
                    <StoryReply segments={splitSegments(greetingText)} showThoughts={draft.show_thoughts} />
                  </div>
                ) : (
                  <p className="mt-1 text-[13px] text-muted">Story bắt đầu từ lượt đầu tiên của bạn.</p>
                )}
              </Field>
              <ChoiceGroup
                label="Ngôn ngữ"
                options={LANGUAGE_OPTIONS}
                value={draft.settings.language}
                onChange={(language) => updateSettings({ language })}
                hint={languageHint}
              />
              <ChoiceGroup label="Chế độ mở đầu" options={MODE_OPTIONS} value={draft.settings.mode} onChange={(mode) => updateSettings({ mode })} />
              <ChoiceGroup
                label="Kiểu quan hệ"
                options={RELATIONSHIP_OPTIONS}
                value={draft.settings.relationship_type}
                onChange={(relationship_type) => updateSettings({ relationship_type })}
              />
              <ChoiceGroup label="Ngôi kể" options={POV_OPTIONS} value={draft.settings.pov} onChange={(pov) => updateSettings({ pov })} />
              <PronounFields
                value={draft.settings.narration_pronouns}
                onChange={(narration_pronouns) => updateSettings({ narration_pronouns })}
                characterName={card.name}
                personaName={persona.name}
                pov={draft.settings.pov}
                suggestion={suggestionFor(draft.settings)}
              />
              <ChoiceGroup
                label="Suy nghĩ của nhân vật (Story)"
                options={THOUGHT_STYLE_OPTIONS}
                value={draft.settings.thought_style}
                onChange={(thought_style) => updateSettings({ thought_style })}
              />
              <Toggle
                label={SHOW_THOUGHTS_LABEL}
                description={showThoughtsHint(card.name)}
                checked={draft.show_thoughts}
                onChange={(show_thoughts) => setDraft((d) => (d ? { ...d, show_thoughts } : d))}
                className="-mt-2"
              />
            </div>
          )}
        </Disclosure>

        {createError && <InlineAlert tone="error" text={createError.text} technical={createError.technical} />}
      </div>
    </Modal>
  );
}
