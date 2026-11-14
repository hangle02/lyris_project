import { useEffect, useMemo, useState } from "react";
import { api, errorMessage, errorTechnical } from "../api/client";
import { useIsOwner } from "../hooks/useAuth";
import {
  affectsNextTurn,
  formFromStory,
  LANGUAGE_OPTIONS,
  labelOf,
  POV_OPTIONS,
  RELATIONSHIP_OPTIONS,
  settingsPatch,
  SHOW_THOUGHTS_LABEL,
  showThoughtsHint,
  suggestPronouns,
  THOUGHT_STYLE_OPTIONS,
  validateSettingsForm,
} from "../lib/storyOptions";
import type { StorySettingsForm } from "../lib/storyOptions";
import type { StoryDetail, StoryOut, StoryPatch, StyleProfileInfo, SystemInfo } from "../types";
import { ChoiceGroup, TextArea, TextField } from "./ui";
import { PronounFields } from "./PronounFields";
import { Button, Disclosure, ErrorDetails, Modal, Select, Toggle } from "./ui";
import type { SelectOption } from "./ui";

interface Props {
  story: StoryOut;
  /** A reply is streaming or a message action is running: deleting is blocked (the server would refuse). */
  busy: boolean;
  onClose: () => void;
  /** Saves the patch; rejects on failure (the panel shows the error and stays open). */
  onSave: (patch: StoryPatch) => Promise<void>;
  /** Deletes the story; rejects on failure (e.g. 409 while a reply is being generated). */
  onDelete: () => Promise<void>;
}

interface Context {
  detail: StoryDetail | null;
  profile: StyleProfileInfo | null;
}

type ModelList =
  | { state: "loading" }
  | { state: "ready"; models: SystemInfo["models"] }
  | { state: "unavailable"; reason: string };

/** "qwen2.5:7b (7.6B, Q4_K_M, 4.7 GB)": the Ollama facts that tell two models apart. */
function modelLabel(m: SystemInfo["models"][number]): string {
  const facts = [m.parameter_size, m.quantization, m.size_gb !== null ? `${m.size_gb.toFixed(1)} GB` : null].filter(
    (f): f is string => !!f,
  );
  return facts.length ? `${m.name} (${facts.join(", ")})` : m.name;
}

/** Story settings from the chat header: everything the story can still change, and deleting it. */
export function StorySettingsPanel({ story, busy, onClose, onSave, onDelete }: Props) {
  const [form, setForm] = useState<StorySettingsForm>(() => formFromStory(story));
  const [model, setModel] = useState(story.model_name);
  const [models, setModels] = useState<ModelList>({ state: "loading" });
  const [ctx, setCtx] = useState<Context>({ detail: null, profile: null });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<{ text: string; technical: string | null } | null>(null);
  /** "Nâng cao" (the model picker, Phase 3b): folded; opens by itself when the story's model is unusual. */
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const isOwner = useIsOwner();
  const [deleting, setDeleting] = useState(false);
  const storyId = story.id;

  // Card/persona genders and the card's style profile, for pronoun suggestions. Optional.
  useEffect(() => {
    if (storyId === null) return;
    let cancelled = false;
    void (async () => {
      try {
        const [detail, styles] = await Promise.all([api.getStory(storyId), api.listStyles().catch(() => [])]);
        if (cancelled) return;
        setCtx({ detail, profile: styles.find((s) => s.name === detail.card.style_profile) ?? null });
      } catch {
        // Suggestions are a convenience; the form works without them.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [storyId]);

  // Ollama's models, for the model picker: read once "Nâng cao" is opened.
  useEffect(() => {
    if (!advancedOpen) return;
    const ctrl = new AbortController();
    api
      .getSystem(ctrl.signal)
      .then((sys) => {
        const list = Array.isArray(sys.models) ? sys.models.filter((m) => m && typeof m.name === "string") : [];
        if (!sys.ollama_reachable) {
          setModels({ state: "unavailable", reason: "Không kết nối được Ollama nên chưa đổi được model." });
        } else if (list.length === 0) {
          setModels({ state: "unavailable", reason: "Ollama chưa có model nào." });
        } else {
          setModels({ state: "ready", models: list });
        }
      })
      .catch((e: unknown) => {
        if (ctrl.signal.aborted) return;
        setModels({ state: "unavailable", reason: `Không đọc được danh sách model. ${errorMessage(e)}` });
      });
    return () => ctrl.abort();
  }, [advancedOpen]);

  const suggestFor = (f: StorySettingsForm) =>
    ctx.detail
      ? suggestPronouns({
          profile: ctx.profile,
          language: f.language,
          pov: f.pov,
          cardGender: ctx.detail.card.gender,
          cardName: ctx.detail.card.name,
          personaGender: ctx.detail.persona.gender,
          personaName: ctx.detail.persona.name,
        })
      : null;

  const suggestion = suggestFor(form);
  const patch = useMemo<StoryPatch>(() => {
    const p = settingsPatch(story, form);
    return model !== story.model_name ? { ...p, model_name: model } : p;
  }, [story, form, model]);
  const dirty = Object.keys(patch).length > 0;
  const problems = validateSettingsForm(form);

  /** Language/POV changes carry the pronouns along when they still match the old suggestion. */
  const update = (next: Partial<StorySettingsForm>) => {
    setForm((cur) => {
      const merged = { ...cur, ...next };
      if ((next.language !== undefined || next.pov !== undefined) && !next.narration_pronouns) {
        const before = suggestFor(cur);
        const after = suggestFor(merged);
        const untouched =
          before !== null &&
          before.character === cur.narration_pronouns.character.trim() &&
          before.player === cur.narration_pronouns.player.trim();
        if (after && untouched) merged.narration_pronouns = { ...after };
      }
      return merged;
    });
  };

  const save = async () => {
    if (!dirty || problems.length > 0 || saving) return;
    setSaving(true);
    setError(null);
    try {
      await onSave(patch);
      onClose();
    } catch (e) {
      setError({ text: errorMessage(e), technical: errorTechnical(e) });
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    if (busy || deleting) return;
    setDeleting(true);
    setError(null);
    try {
      await onDelete();
    } catch (e) {
      setError({ text: errorMessage(e), technical: errorTechnical(e) });
      setDeleting(false);
    }
  };

  const languageWarning =
    ctx.detail && form.language !== ctx.detail.card.language
      ? `Nhân vật được viết bằng ${labelOf(LANGUAGE_OPTIONS, ctx.detail.card.language).toLowerCase()}; nhân vật sẽ phải tự chuyển ngôn ngữ.`
      : undefined;

  const modelOptions: SelectOption<string>[] =
    models.state === "ready"
      ? [
          ...models.models.map((m) => ({ value: m.name, label: modelLabel(m) })),
          ...(models.models.some((m) => m.name === story.model_name)
            ? []
            : [{ value: story.model_name, label: `${story.model_name} (không có trong Ollama)`, disabled: true }]),
        ]
      : [{ value: story.model_name, label: story.model_name }];

  const locked = saving || deleting;
  const nextTurnNote = affectsNextTurn(patch) || patch.model_name !== undefined;

  return (
    <Modal
      open
      onClose={onClose}
      title="Thiết lập story"
      description={`${story.card_name} và ${story.persona_name}`}
      size="md"
      dismissible={!locked}
      footer={
        <>
          {error && (
            <div role="alert" className="w-full">
              <p className="text-[14px] leading-snug text-danger">{error.text}</p>
              <ErrorDetails technical={error.technical} />
            </div>
          )}
          {!error && dirty && problems.length > 0 && (
            <p className="w-full text-[13px] leading-snug text-warn">{problems.join(" ")}</p>
          )}
          {!error && dirty && problems.length === 0 && nextTurnNote && (
            <p className="w-full text-[13px] leading-snug text-muted">
              Áp dụng từ lượt trả lời sau; các lượt đã có giữ nguyên.
            </p>
          )}
          <Button size="sm" variant="ghost" onClick={onClose} disabled={locked}>
            Huỷ
          </Button>
          <Button
            size="sm"
            variant="primary"
            onClick={() => void save()}
            disabled={!dirty || problems.length > 0 || deleting}
            loading={saving}
          >
            Lưu
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-6 pt-1">
        <TextField
          label="Tiêu đề"
          value={form.title}
          onChange={(title) => update({ title })}
          maxLength={120}
          disabled={saving}
        />
        <TextArea
          label="Bối cảnh"
          value={form.scenario}
          onChange={(scenario) => update({ scenario })}
          placeholder="Nơi chốn, thời điểm, hoàn cảnh hai người đang ở…"
          disabled={saving}
        />
        <ChoiceGroup
          label="Ngôn ngữ"
          options={LANGUAGE_OPTIONS}
          value={form.language}
          onChange={(language) => update({ language })}
          hint={languageWarning}
          disabled={saving}
        />
        <ChoiceGroup
          label="Kiểu quan hệ"
          options={RELATIONSHIP_OPTIONS}
          value={form.relationship_type}
          onChange={(relationship_type) => update({ relationship_type })}
          disabled={saving}
        />
        <ChoiceGroup
          label="Ngôi kể"
          options={POV_OPTIONS}
          value={form.pov}
          onChange={(pov) => update({ pov })}
          disabled={saving}
        />
        <PronounFields
          value={form.narration_pronouns}
          onChange={(narration_pronouns) => update({ narration_pronouns })}
          characterName={story.card_name}
          personaName={story.persona_name}
          pov={form.pov}
          suggestion={suggestion}
          disabled={saving}
        />
        <ChoiceGroup
          label="Suy nghĩ của nhân vật ở Story"
          options={THOUGHT_STYLE_OPTIONS}
          value={form.thought_style}
          onChange={(thought_style) => update({ thought_style })}
          disabled={saving}
        />
        <Toggle
          label={SHOW_THOUGHTS_LABEL}
          description={showThoughtsHint(story.card_name)}
          checked={form.show_thoughts}
          onChange={(show_thoughts) => update({ show_thoughts })}
          disabled={saving}
          className="-mt-2"
        />

        {/* Changing a story's model is the owner's (docs/auth.md §1.1): a member's stories use the default. */}
        {isOwner && <Disclosure
          title="Nâng cao"
          open={advancedOpen}
          onToggle={setAdvancedOpen}
        >
          <Select
            label="Model trả lời"
            value={model}
            onChange={setModel}
            options={modelOptions}
            disabled={saving || models.state !== "ready"}
            hint={
              models.state === "loading"
                ? "Đang đọc danh sách model từ Ollama…"
                : models.state === "unavailable"
                  ? models.reason
                  : "Model Ollama viết các lượt trả lời của story này."
            }
          />
        </Disclosure>}

        <section aria-label="Xoá story" className="mt-2 rounded-card border border-danger/40 p-4">
          {confirmDelete ? (
            <div role="alertdialog" aria-label="Xác nhận xoá story" className="flex flex-col gap-3">
              <p className="text-[14px] leading-snug text-fg">
                Xoá vĩnh viễn “{story.title}” cùng toàn bộ tin nhắn, đánh giá và lịch sử sửa? Dữ liệu này cũng dùng
                để train sau này. Không hoàn tác được.
              </p>
              {busy && (
                <p className="text-[13px] leading-snug text-warn">
                  Nhân vật đang trả lời. Hãy đợi xong hoặc bấm Dừng rồi mới xoá.
                </p>
              )}
              <div className="flex flex-wrap justify-end gap-2">
                <Button size="sm" variant="ghost" onClick={() => setConfirmDelete(false)} disabled={deleting}>
                  Huỷ
                </Button>
                <Button
                  size="sm"
                  variant="danger"
                  onClick={() => void remove()}
                  disabled={busy}
                  loading={deleting}
                  autoFocus
                >
                  Xoá vĩnh viễn
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex flex-wrap items-center gap-3">
              <p className="min-w-0 flex-1 text-[13px] leading-snug text-muted">
                Xoá story này và mọi tin nhắn của nó. Nhân vật và persona vẫn giữ nguyên.
              </p>
              <Button size="sm" variant="danger" onClick={() => setConfirmDelete(true)} disabled={saving}>
                Xoá story…
              </Button>
            </div>
          )}
        </section>
      </div>
    </Modal>
  );
}
