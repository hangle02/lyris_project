import { useEffect, useRef, useState } from "react";
import { api, errorMessage, errorTechnical } from "../../api/client";
import { Button, Checkbox, Field, InlineAlert, Modal, TextArea } from "../../components/ui";
import { cx } from "../../components/ui/logic";
import {
  cleanNote,
  noteCounter,
  REPORT_NOTE_MAX,
  REPORT_REASONS,
  REPORT_CARD_HINT,
  REPORT_SHARE_HINT,
  REPORT_SHARE_LABEL,
  reportSheetText,
} from "../../lib/compliance";
import type { Message, ReportReason } from "../../types";

/**
 * "Báo cáo" on a character's reply, or on a public character's profile (docs/compliance.md §2, §7): a
 * reason (required), a short note (optional, ≤ 300), and for a reply a box, off by default, to send
 * the reply's text to the owner for review. Without it only the reason and the note are kept. The
 * server records the report for the numbers itself: nothing extra is sent from here.
 */
export function ReportSheet({
  message = null,
  cardId = null,
  characterName,
  onClose,
  onDone,
}: {
  /** The reply being reported; null = not a reply. */
  message?: Message | null;
  /** The public character being reported (its profile); null = not a character. */
  cardId?: number | null;
  characterName: string;
  onClose: () => void;
  onDone: () => void;
}) {
  const isCard = message === null && cardId !== null;
  const open = message !== null || cardId !== null;
  const [reason, setReason] = useState<ReportReason | null>(null);
  const [note, setNote] = useState("");
  const [share, setShare] = useState(false);
  const [sending, setSending] = useState(false);
  const [missing, setMissing] = useState(false);
  const [error, setError] = useState<{ text: string; technical: string | null } | null>(null);
  const firstRef = useRef<HTMLButtonElement>(null);

  // Every opening starts empty.
  const openId = message ? `m${message.id}` : cardId !== null ? `c${cardId}` : null;
  useEffect(() => {
    if (openId === null) return;
    setReason(null);
    setNote("");
    setShare(false);
    setSending(false);
    setMissing(false);
    setError(null);
  }, [openId]);

  const send = async () => {
    if (sending || !open || (message !== null && message.id === null)) return;
    if (reason === null) {
      setMissing(true);
      firstRef.current?.focus();
      return;
    }
    setSending(true);
    setError(null);
    try {
      if (isCard && cardId !== null) await api.reportCard(cardId, { reason, note: cleanNote(note) });
      else if (message && message.id !== null) await api.reportMessage(message.id, { reason, note: cleanNote(note), share_text: share });
      onDone();
    } catch (e) {
      setError({ text: errorMessage(e), technical: errorTechnical(e) });
      setSending(false);
    }
  };

  const text = reportSheetText(isCard ? "character" : "message", characterName);

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={text.title}
      description={text.description}
      size="sm"
      dismissible={!sending}
      initialFocusRef={firstRef}
      footer={
        <>
          <Button size="sm" variant="ghost" onClick={onClose} disabled={sending} className="max-sm:h-11">
            Huỷ
          </Button>
          <Button size="sm" variant="primary" onClick={() => void send()} loading={sending} className="max-sm:h-11">
            Gửi báo cáo
          </Button>
        </>
      }
    >
      <form
        className="flex flex-col gap-5"
        onSubmit={(e) => {
          e.preventDefault();
          void send();
        }}
      >
        <Field label="Lý do" error={missing && reason === null ? "Hãy chọn một lý do." : undefined}>
          <div role="radiogroup" aria-label="Lý do" className="flex flex-wrap gap-2">
            {REPORT_REASONS.map((r, i) => {
              const on = reason === r.value;
              return (
                <button
                  key={r.value}
                  ref={i === 0 ? firstRef : undefined}
                  type="button"
                  role="radio"
                  aria-checked={on}
                  disabled={sending}
                  onClick={() => {
                    setReason(r.value);
                    setMissing(false);
                  }}
                  className={cx(
                    "inline-flex min-h-11 items-center rounded-full border px-4 text-[14px] font-medium transition-colors duration-150 sm:min-h-9",
                    on ? "border-accent bg-accent/15 text-fg" : "border-line bg-surface-2 text-fg hover:bg-surface-3",
                    "disabled:opacity-60",
                  )}
                >
                  {r.label}
                </button>
              );
            })}
          </div>
        </Field>
        <TextArea
          label="Ghi chú (không bắt buộc)"
          value={note}
          onChange={setNote}
          maxLength={REPORT_NOTE_MAX}
          placeholder="Điều gì chưa ổn?"
          maxHeight={160}
          hint={noteCounter(note)}
          disabled={sending}
        />
        {isCard ? (
          <p className="text-[13px] leading-snug text-muted">{REPORT_CARD_HINT}</p>
        ) : (
          <Checkbox label={REPORT_SHARE_LABEL} hint={REPORT_SHARE_HINT} checked={share} onChange={setShare} disabled={sending} />
        )}
        {error && <InlineAlert tone="error" text={error.text} technical={error.technical} />}
      </form>
    </Modal>
  );
}
