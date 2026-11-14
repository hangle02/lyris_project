import { useEffect, useId, useState, useRef } from "react";
import { api, friendlyOf, isAbortError } from "../../api/client";
import type { FriendlyError } from "../../lib/friendlyError";
import { AutoTextarea } from "../../components/AutoTextarea";
import { ChoiceGroup } from "../../components/ui";
import { formatElapsed, useElapsed } from "../../components/elapsed";
import { Button, CONTROL_CLASS, Chip, Modal, Select, Spinner, cx } from "../../components/ui";
import type { CardDraftResult, Gender, Language, StyleProfileInfo } from "../../types";
import { Field, Notice } from "./ui";

const MAX_IDEA_CHARS = 2000;

const EXAMPLES: { language: Language; label: string; text: string }[] = [
  {
    language: "vi",
    label: "Sư tỷ Thanh Vân Tông",
    text: "Sư tỷ lạnh lùng của Thanh Vân Tông, ngoài lạnh trong nóng, luôn âm thầm bảo vệ {{user}} là sư đệ mới nhập môn.",
  },
  {
    language: "vi",
    label: "Kiến trúc sư ở Sài Gòn",
    text: "Kiến trúc sư 27 tuổi ở Sài Gòn, ít nói, sáng nào cũng ghé quán cà phê nơi {{user}} làm thêm và gọi đúng một ly bạc xỉu.",
  },
  {
    language: "vi",
    label: "Thanh mai trúc mã về nước",
    text: "Tổng tài trẻ vừa về nước, là thanh mai trúc mã từng bị {{user}} từ chối năm mười tám tuổi.",
  },
  {
    language: "en",
    label: "Night-shift librarian",
    text: "A grumpy night-shift librarian in a rainy port town who secretly leaves book recommendations for {{user}}.",
  },
];

type GenderChoice = Gender | "auto";

function Elapsed({ startedAt }: { startedAt: number }) {
  const sec = useElapsed(startedAt);
  return <span className="tabular-nums">{formatElapsed(sec)}</span>;
}

/**
 * "AI viết nháp": one line of idea -> a full unsaved card. Shows the time waited while the model
 * writes (usually 1-2 minutes) and can be cancelled. Calls `onDone` with the draft.
 */
export function DraftDialog({ onClose, onDone }: { onClose: () => void; onDone: (r: CardDraftResult) => void }) {
  const ideaId = useId();
  const [idea, setIdea] = useState("");
  const [language, setLanguage] = useState<Language>("vi");
  const [gender, setGender] = useState<GenderChoice>("auto");
  const [style, setStyle] = useState<string>("auto");
  const [styles, setStyles] = useState<StyleProfileInfo[] | null>(null);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [error, setError] = useState<FriendlyError | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    let alive = true;
    api
      .listStyles()
      .then((s) => alive && setStyles(s))
      .catch(() => alive && setStyles([]));
    return () => {
      alive = false;
      abortRef.current?.abort();
    };
  }, []);

  const running = startedAt !== null;
  const trimmed = idea.trim();
  const tooLong = idea.length > MAX_IDEA_CHARS;

  const run = async () => {
    if (running || !trimmed || tooLong) return;
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setError(null);
    setStartedAt(Date.now());
    try {
      const result = await api.draftCard(
        {
          idea: trimmed,
          language,
          gender: gender === "auto" ? null : gender,
          style_profile: style === "auto" ? null : style,
        },
        ctrl.signal,
      );
      if (ctrl.signal.aborted) return;
      onDone(result);
    } catch (e) {
      if (isAbortError(e) || ctrl.signal.aborted) return;
      setError(friendlyOf(e));
    } finally {
      // A cancelled run already reset the state (and a new run may have started since).
      if (abortRef.current === ctrl) {
        abortRef.current = null;
        setStartedAt(null);
      }
    }
  };

  const cancel = () => {
    abortRef.current?.abort();
    abortRef.current = null;
    setStartedAt(null);
  };

  const close = () => {
    cancel();
    onClose();
  };

  return (
    <Modal
      open
      title="AI viết nháp nhân vật"
      description={running ? undefined : "Một hai câu ý tưởng thành một card đầy đủ. Bản nháp chưa lưu cho tới khi bạn duyệt."}
      onClose={close}
      size="md"
      footer={
        running ? (
          <Button size="sm" onClick={cancel}>
            Huỷ viết nháp
          </Button>
        ) : (
          <>
            <Button variant="ghost" size="sm" onClick={close}>
              Đóng
            </Button>
            <Button variant="primary" size="sm" onClick={() => void run()} disabled={!trimmed || tooLong}>
              Viết nháp
            </Button>
          </>
        )
      }
    >
      {running ? (
        <div className="flex flex-col gap-3 py-2" role="status" aria-live="polite">
          <p className="flex items-center gap-3 text-[16px] font-medium text-fg">
            <Spinner size={20} className="text-accent" />
            <span>
              Đang viết nháp · <Elapsed startedAt={startedAt} />
            </span>
          </p>
          <p className="text-[14px] leading-snug text-muted">
            Thường mất 1-2 phút. Bạn sẽ duyệt và sửa trong form trước khi lưu.
          </p>
          <p className="line-clamp-3 rounded-control bg-surface-2 px-4 py-3 text-[14px] leading-snug text-muted italic">“{trimmed}”</p>
        </div>
      ) : (
        <div className="flex flex-col gap-5">
          {error && <Notice tone="error" lines={[error.text]} technical={error.technical} />}
          <Field
            label="Ý tưởng"
            htmlFor={ideaId}
            hint="Thân phận, tính cách, quan hệ với {{user}} (nhân vật của bạn), bối cảnh."
            extra={
              idea.length > MAX_IDEA_CHARS * 0.8 ? (
                <span className={cx("text-[12px] tabular-nums", tooLong ? "text-danger" : "text-muted")}>
                  {idea.length}/{MAX_IDEA_CHARS}
                </span>
              ) : undefined
            }
          >
            <AutoTextarea
              id={ideaId}
              value={idea}
              onChange={(e) => setIdea(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                  e.preventDefault();
                  void run();
                }
              }}
              maxHeight={220}
              style={{ minHeight: "5.5em" }}
              placeholder="Ví dụ: cậu bạn thanh mai trúc mã học cùng lớp, ngoài mặt hay trêu chọc nhưng rất quan tâm {{user}}…"
              className={CONTROL_CLASS}
            />
          </Field>
          <div className="flex flex-col gap-2">
            <p className="text-[13px] text-muted">Hoặc bắt đầu từ một ví dụ:</p>
            <div className="flex flex-wrap gap-2">
              {EXAMPLES.map((ex) => (
                <Chip
                  key={ex.text}
                  size="sm"
                  title={ex.text}
                  selected={idea === ex.text}
                  onClick={() => {
                    setIdea(ex.text);
                    setLanguage(ex.language);
                  }}
                >
                  {ex.label}
                </Chip>
              ))}
            </div>
          </div>

          <div className="grid gap-5 sm:grid-cols-2">
            <ChoiceGroup<Language>
              label="Ngôn ngữ của card"
              value={language}
              onChange={setLanguage}
              options={[
                { value: "vi", label: "Tiếng Việt" },
                { value: "en", label: "English" },
              ]}
            />
            <ChoiceGroup<GenderChoice>
              label="Giới tính"
              value={gender}
              onChange={setGender}
              options={[
                { value: "auto", label: "AI chọn" },
                { value: "male", label: "Nam" },
                { value: "female", label: "Nữ" },
                { value: "other", label: "Khác" },
              ]}
            />
          </div>
          <Select
            label="Bộ văn phong"
            hint="Văn phong, xưng hô và bối cảnh văn hoá mà nhân vật sẽ theo."
            value={style}
            onChange={setStyle}
            disabled={styles === null}
            options={[{ value: "auto", label: "Để AI chọn" }, ...(styles ?? []).map((s) => ({ value: s.name, label: s.title }))]}
          />
          <p className="text-[13px] text-muted">Ctrl/⌘ + Enter để bắt đầu.</p>
        </div>
      )}
    </Modal>
  );
}
