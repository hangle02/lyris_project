import { useEffect, useMemo, useRef, useState } from "react";
import { api, errorMessage, errorTechnical } from "../../api/client";
import { Button, ChoiceGroup, InlineAlert, Modal, TextField } from "../../components/ui";
import type { LoreAudience, LoreCategory, LoreEntry, LoreEntryInput } from "../../types";
import {
  CATEGORY_OPTIONS,
  MAX_LORE_CONTENT,
  MAX_LORE_KEYS,
  MAX_LORE_TITLE,
  SOURCE_LABELS,
  audienceOf,
  cleanInput,
  contentWarnings,
  deletePrompt,
  emptyInput,
  inputOf,
  keyWarnings,
  keysHint,
  knowOptions,
  knownByFor,
  tokenEstimate,
  validateEntry,
} from "./loreLogic";
import { ChipInput, TextAreaField, UserPlaceholderBadge } from "./ui";

interface Props {
  cardId: number;
  characterName: string;
  /** The entry to edit; null for a new one. */
  entry: LoreEntry | null;
  /** "Công cụ nâng cao": priority, the raw "who knows" list, source, slug, size estimate. */
  advanced: boolean;
  onClose: () => void;
  onSaved: (entry: LoreEntry) => void;
  onDeleted: (entryId: number) => void;
}

interface Failure {
  text: string;
  technical: string | null;
}

/**
 * "Mục thế giới" / "Mục mới" (phase4.md §9): name, kind, the words that bring it back, who knows it and
 * the note itself. Saved straight to the server (not with "Lưu nhân vật"); errors stay in the dialog.
 */
export function LoreEntryDialog({ cardId, characterName, entry, advanced, onClose, onSaved, onDeleted }: Props) {
  const [form, setForm] = useState<LoreEntryInput>(() => (entry ? inputOf(entry) : emptyInput()));
  /** known_by as it was when the dialog opened: the "Chỉ {người khác} biết" choice goes back to it. */
  const original = useMemo(() => (entry ? [...entry.known_by] : ["*"]), [entry]);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [error, setError] = useState<Failure | null>(null);
  const [rawKnownBy, setRawKnownBy] = useState(() => form.known_by.join(", "));
  const titleRef = useRef<HTMLInputElement>(null);
  const keepRef = useRef<HTMLButtonElement>(null);
  const name = characterName.trim() || "nhân vật";

  useEffect(() => {
    if (confirmDelete) keepRef.current?.focus();
  }, [confirmDelete]);

  const audience: LoreAudience = audienceOf(form.known_by, characterName);
  const options = knowOptions(characterName, original);
  const problems = validateEntry(form);
  const keyNotes = keyWarnings(form.keys, characterName);
  const contentNotes = contentWarnings(form.content, audience, characterName);
  const busy = saving || deleting;
  const set = (patch: Partial<LoreEntryInput>) => setForm((f) => ({ ...f, ...patch }));

  const save = async () => {
    if (busy || problems.length > 0) return;
    setSaving(true);
    setError(null);
    try {
      const body = cleanInput(form);
      const saved = entry ? await api.updateLore(cardId, entry.id, body) : await api.createLore(cardId, body);
      onSaved(saved);
    } catch (e) {
      setError({ text: errorMessage(e), technical: errorTechnical(e) });
      setSaving(false);
    }
  };

  const remove = async () => {
    if (!entry || busy) return;
    setDeleting(true);
    setError(null);
    try {
      await api.deleteLore(cardId, entry.id);
      onDeleted(entry.id);
    } catch (e) {
      setError({ text: errorMessage(e), technical: errorTechnical(e) });
      setDeleting(false);
      setConfirmDelete(false);
    }
  };

  const footer = confirmDelete && entry ? (
    <div role="alertdialog" aria-label="Xác nhận xoá mục" className="flex w-full flex-col gap-3">
      <p className="text-[14px] leading-snug text-fg">{deletePrompt(entry)}</p>
      <div className="flex flex-wrap justify-end gap-2">
        <Button ref={keepRef} size="sm" variant="ghost" onClick={() => setConfirmDelete(false)} disabled={deleting}>
          Giữ lại
        </Button>
        <Button size="sm" variant="danger" onClick={() => void remove()} loading={deleting}>
          Xoá
        </Button>
      </div>
    </div>
  ) : (
    <>
      {entry && (
        <Button size="sm" variant="danger" onClick={() => setConfirmDelete(true)} disabled={busy} className="mr-auto">
          Xoá mục
        </Button>
      )}
      <Button size="sm" variant="ghost" onClick={onClose} disabled={busy}>
        Huỷ
      </Button>
      <Button size="sm" variant="primary" onClick={() => void save()} loading={saving} disabled={problems.length > 0 || deleting}>
        Lưu
      </Button>
    </>
  );

  return (
    <Modal
      open
      onClose={onClose}
      title={entry ? "Mục thế giới" : "Mục mới"}
      size="md"
      dismissible={!busy}
      initialFocusRef={titleRef}
      footer={footer}
    >
      <div className="flex flex-col gap-6 pt-1">
        {error && <InlineAlert tone="error" text={error.text} technical={error.technical} onDismiss={() => setError(null)} />}
        <TextField
          ref={titleRef}
          label="Tên mục"
          value={form.title}
          onChange={(title) => set({ title })}
          maxLength={MAX_LORE_TITLE}
          placeholder="Ví dụ: Hôn ước hai nhà"
          disabled={busy}
          autoComplete="off"
        />
        <ChoiceGroup<LoreCategory>
          label="Loại"
          options={CATEGORY_OPTIONS}
          value={form.category}
          onChange={(category) => set({ category })}
          disabled={busy}
        />
        <div className="flex flex-col gap-2">
          <ChipInput
            label="Từ khoá gợi nhớ"
            hint={keysHint(characterName)}
            values={form.keys}
            onChange={(keys) => set({ keys })}
            placeholder="Gõ một từ rồi Enter"
            max={MAX_LORE_KEYS}
            disabled={busy}
          />
          {keyNotes.length > 0 && (
            <ul className="flex flex-col gap-1" aria-live="polite">
              {keyNotes.map((n) => (
                <li key={n} className="text-[13px] leading-snug text-warn">
                  {n}
                </li>
              ))}
            </ul>
          )}
        </div>
        <ChoiceGroup<LoreAudience>
          label="Ai biết điều này"
          options={options}
          value={audience}
          onChange={(choice) => {
            const known_by = knownByFor(choice, original);
            set({ known_by });
            setRawKnownBy(known_by.join(", "));
          }}
          disabled={busy}
        />
        <div className="flex flex-col gap-2">
          <TextAreaField
            label="Nội dung"
            hint={
              <>
                Viết như một đoạn ghi chú ngắn. Dùng <UserPlaceholderBadge /> cho bạn và {"{{char}}"} cho {name}.
              </>
            }
            value={form.content}
            onChange={(content) => set({ content })}
            userPlaceholder
            minRows={4}
            maxChars={MAX_LORE_CONTENT}
            disabled={busy}
          />
          {contentNotes.length > 0 && (
            <ul className="flex flex-col gap-1">
              {contentNotes.map((n) => (
                <li key={n} className="text-[13px] leading-snug text-warn">
                  {n}
                </li>
              ))}
            </ul>
          )}
        </div>

        {advanced && (
          <div className="flex flex-col gap-4 rounded-card bg-surface-2 p-4">
            <p className="text-[13px] font-semibold text-muted">Công cụ nâng cao</p>
            <TextField
              label="Độ ưu tiên"
              type="number"
              inputMode="numeric"
              min={-100}
              max={100}
              value={String(form.priority)}
              onChange={(v) => set({ priority: Number(v) || 0 })}
              hint="Từ −100 đến 100. Lớn hơn thì được chọn trước khi không đủ chỗ."
              disabled={busy}
            />
            <TextField
              label="Người biết (danh sách thô)"
              value={rawKnownBy}
              onChange={(v) => {
                setRawKnownBy(v);
                set({ known_by: v.split(",").map((s) => s.trim()).filter(Boolean) });
              }}
              hint="Cách nhau bằng dấu phẩy: *, {{user}}, {{char}} hoặc tên một nhân vật."
              disabled={busy}
            />
            <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-1.5 text-[13px] leading-snug">
              <dt className="text-muted">Nguồn</dt>
              <dd className="text-fg">{SOURCE_LABELS[entry?.source ?? "manual"]}</dd>
              {entry && (
                <>
                  <dt className="text-muted">Slug</dt>
                  <dd className="text-fg [overflow-wrap:anywhere]">{entry.slug}</dd>
                </>
              )}
              <dt className="text-muted">Ước lượng</dt>
              <dd className="text-fg tabular-nums">~{tokenEstimate(form.content)} token mỗi lượt được gợi nhớ</dd>
            </dl>
          </div>
        )}

        {problems.length > 0 && (form.title.trim() !== "" || entry !== null) && (
          <p className="text-[13px] leading-snug text-warn">{problems.join(" ")}</p>
        )}
      </div>
    </Modal>
  );
}
