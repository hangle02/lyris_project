import type { ReactNode } from "react";
import { ChoiceGroup } from "../../components/ui";
import { IconCheck, IconPlus, IconTrash } from "../../components/icons";
import { Button, IconButton, cx } from "../../components/ui";
import {
  GENDER_LABEL,
  MAX_ALT_GREETINGS,
  MAX_NAME_CHARS,
  MAX_ROLE_CHARS,
  MAX_TAGS,
  MAX_TEXT_CHARS,
  normalizeTerm,
  readNarrationOverride,
  suggestNarration,
  withNarrationOverride,
} from "../../lib/cardForm";
import type { CardHint } from "../../lib/cardForm";
import type { Option } from "../../lib/storyOptions";
import type { AddressTerms, CharacterCard, Gender, Language, StyleProfileInfo } from "../../types";
import { EmotionSection } from "./EmotionSection";
import { SIGNATURE_MAX_CHARS, SIGNATURE_MAX_LINES, signatureText, withSignatureText } from "../../lib/signatureLines";
import { ChipInput, Notice, Section, TextAreaField, TextField, UserPlaceholderBadge } from "./ui";

export type CardUpdater = (fn: (c: CharacterCard) => CharacterCard) => void;

interface Props {
  card: CharacterCard;
  update: CardUpdater;
  styles: StyleProfileInfo[];
  hints: CardHint[];
  disabled: boolean;
  /** Avatar picker (rendered beside the name). */
  avatar: ReactNode;
  /** Phase 4: the "Thế giới" section (saved on its own), placed before the creator's notes. */
  world?: ReactNode;
  /** Phase 4b: the "Công khai" switch, right under the name and role (absent for templates). */
  share?: ReactNode;
}

const GENDER_OPTIONS: Option<Gender>[] = [
  { value: "male", label: "Nam" },
  { value: "female", label: "Nữ" },
  { value: "other", label: "Khác" },
];

const LANGUAGE_OPTIONS: Option<Language>[] = [
  { value: "vi", label: "Tiếng Việt" },
  { value: "en", label: "English" },
];

function StylePicker({
  value,
  styles,
  onChange,
  disabled,
}: {
  value: string;
  styles: StyleProfileInfo[];
  onChange: (name: string) => void;
  disabled: boolean;
}) {
  const known = styles.some((s) => s.name === value);
  return (
    <div className="flex min-w-0 flex-col gap-2">
      <span id="style-picker-label" className="text-[14px] leading-tight font-medium text-fg">
        Bộ văn phong
      </span>
      {styles.length === 0 ? (
        <p className="rounded-control bg-surface-2 px-3.5 py-2.5 text-[14px] text-muted">
          Đang tải danh sách style… ({value || "chưa chọn"})
        </p>
      ) : (
        <div role="radiogroup" aria-labelledby="style-picker-label" className="grid gap-2 sm:grid-cols-2">
          {styles.map((s) => {
            const active = s.name === value;
            return (
              <button
                key={s.name}
                type="button"
                role="radio"
                aria-checked={active}
                disabled={disabled}
                onClick={() => onChange(s.name)}
                className={cx(
                  "flex min-h-11 items-start gap-3 rounded-control px-3.5 py-3 text-left transition-colors disabled:opacity-60",
                  active ? "bg-accent/15 ring-1 ring-accent/60 ring-inset" : "bg-surface-2 hover:bg-surface-3",
                )}
              >
                <span className="min-w-0 flex-1">
                  <span className="block text-[15px] leading-tight font-medium text-fg">{s.title}</span>
                  {s.description && <span className="mt-1 block text-[13px] leading-snug text-muted">{s.description}</span>}
                </span>
                <IconCheck aria-hidden="true" className={cx("mt-0.5 shrink-0 text-[16px] text-accent", !active && "invisible")} />
              </button>
            );
          })}
        </div>
      )}
      <p className="text-[13px] leading-snug text-muted">
        Văn phong, cách đặt tên, xưng hô mặc định và đại từ dẫn truyện. Xưng hô riêng của card luôn được ưu tiên.
      </p>
      {!known && styles.length > 0 && value && (
        <p className="text-[13px] text-warn">Style “{value}” không có trên máy chủ; hãy chọn một style ở trên.</p>
      )}
    </div>
  );
}

function AddressSection({
  card,
  update,
  profile,
  hints,
  disabled,
}: {
  card: CharacterCard;
  update: CardUpdater;
  profile: StyleProfileInfo | null;
  hints: CardHint[];
  disabled: boolean;
}) {
  const t = card.address_terms;
  const lang: Language = card.language;
  const setTerms = (patch: Partial<AddressTerms>) =>
    update((c) => ({ ...c, address_terms: { ...c.address_terms, ...patch } }));
  const narration = suggestNarration(profile, lang, card.gender, card.name);
  const examples = profile?.address_examples ?? [];
  const name = card.name.trim() || "nhân vật";

  return (
    <Section
      id="sec-address"
      title="Xưng hô"
      hint={
        <>
          Chỉ dùng trong <b className="font-medium text-fg">lời thoại</b> và <b className="font-medium text-fg">Thought</b>. Phần
          dẫn truyện gọi {name} bằng tên hoặc đại từ{narration ? ` “${narration}”` : ""}, không dùng xưng hô.
        </>
      }
    >
      {examples.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="text-[14px] leading-tight font-medium text-fg">Gợi ý từ {profile?.title ?? "style profile"}</p>
          <div className="flex flex-wrap gap-2">
            {examples.map((ex, i) => {
              const self = normalizeTerm(ex.self, lang);
              const player = normalizeTerm(ex.player, lang);
              const active = self === t.self_term && player === t.player_term;
              return (
                <button
                  key={`${ex.self}-${ex.player}-${i}`}
                  type="button"
                  disabled={disabled}
                  aria-pressed={active}
                  onClick={() => setTerms({ self_term: self, player_term: player })}
                  title={ex.note ? `${ex.self} / ${ex.player}: ${ex.note}` : `${ex.self} / ${ex.player}`}
                  className={cx(
                    "flex min-h-11 max-w-full flex-col justify-center rounded-control px-3.5 py-2 text-left transition-colors disabled:opacity-60",
                    active ? "bg-accent/15 ring-1 ring-accent/60 ring-inset" : "bg-surface-2 hover:bg-surface-3",
                  )}
                >
                  <span className="text-[15px] leading-tight font-medium text-fg">
                    {ex.self} / {ex.player}
                  </span>
                  {ex.note && <span className="mt-0.5 max-w-[16rem] truncate text-[12px] text-muted">{ex.note}</span>}
                </button>
              );
            })}
          </div>
        </div>
      )}

      <div className="grid gap-5 sm:grid-cols-2">
        <TextField
          label="Nhân vật tự xưng"
          value={t.self_term}
          onChange={(v) => setTerms({ self_term: v })}
          onBlur={() => {
            const n = normalizeTerm(t.self_term, lang);
            if (n !== t.self_term) setTerms({ self_term: n });
          }}
          placeholder={lang === "vi" ? "ví dụ: tớ, anh, ta" : "e.g. I"}
          hint="Một từ, viết thường. Không liệt kê nhiều lựa chọn."
          disabled={disabled}
        />
        <TextField
          label="Gọi người chơi"
          value={t.player_term}
          onChange={(v) => setTerms({ player_term: v })}
          onBlur={() => {
            const n = normalizeTerm(t.player_term, lang);
            if (n !== t.player_term) setTerms({ player_term: n });
          }}
          placeholder={lang === "vi" ? "ví dụ: cậu, em, ngươi" : "e.g. you"}
          hint="Cách nhân vật gọi {{user}} khi nói chuyện."
          disabled={disabled}
        />
      </div>
      <ChipInput
        label="Tên gọi thân mật cho người chơi"
        values={t.nicknames}
        onChange={(v) => setTerms({ nicknames: v })}
        placeholder="ví dụ: Vãn Vãn, A Vãn"
        hint="Biệt danh nhân vật dùng khi gọi {{user}} lúc thân mật. Gõ rồi Enter hoặc dấu phẩy."
        max={12}
        disabled={disabled}
      />
      <TextAreaField
        label="Xưng hô với người khác"
        value={t.others}
        onChange={(v) => setTerms({ others: v })}
        placeholder="ví dụ: với bố mẹ xưng con; với bạn cùng lớp xưng tôi, gọi bằng tên"
        disabled={disabled}
        maxChars={MAX_TEXT_CHARS}
      />
      {hints.length > 0 && <Notice tone="warn" lines={hints.map((h) => h.text)} />}
    </Section>
  );
}

function AlternateGreetings({
  values,
  onChange,
  disabled,
}: {
  values: string[];
  onChange: (v: string[]) => void;
  disabled: boolean;
}) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <p className="min-w-0 flex-1 text-[14px] leading-tight font-medium text-fg">
          Các lời mở đầu khác <span className="font-normal text-muted tabular-nums">({values.length})</span>
        </p>
        <Button
          variant="ghost"
          size="sm"
          icon={<IconPlus />}
          disabled={disabled || values.length >= MAX_ALT_GREETINGS}
          onClick={() => onChange([...values, ""])}
          className="-mr-2"
        >
          Thêm
        </Button>
      </div>
      {values.length === 0 && (
        <p className="-mt-2 text-[13px] leading-snug text-muted">
          Khi tạo story, bạn chọn một trong lời mở đầu chính và các bản ở đây.
        </p>
      )}
      {values.map((g, i) => (
        <div key={i} className="flex items-start gap-1">
          <div className="min-w-0 flex-1">
            <TextAreaField
              label={`Lời mở đầu ${i + 2}`}
              value={g}
              onChange={(v) => onChange(values.map((x, j) => (j === i ? v : x)))}
              placeholder="Một tình huống mở đầu khác…"
              userPlaceholder
              minRows={3}
              disabled={disabled}
              maxChars={MAX_TEXT_CHARS}
            />
          </div>
          <IconButton
            label={`Xoá lời mở đầu ${i + 2}`}
            icon={<IconTrash />}
            size="sm"
            disabled={disabled}
            onClick={() => onChange(values.filter((_, j) => j !== i))}
            className="mt-7 -mr-2 hover:text-danger"
          />
        </div>
      ))}
    </div>
  );
}

/** The whole card form, grouped in sections. Pure view: state lives in CardEditorPage. */
export function CardForm({ card, update, styles, hints, disabled, avatar, world, share }: Props) {
  const set = <K extends keyof CharacterCard>(key: K, value: CharacterCard[K]) =>
    update((c) => ({ ...c, [key]: value }));
  const profile = styles.find((s) => s.name === card.style_profile) ?? null;
  const vi = card.language === "vi";
  const styleNarration = suggestNarration(profile, card.language, card.gender, card.name);
  const narrationOverride = readNarrationOverride(card);
  const narration = vi && narrationOverride.trim() ? narrationOverride.trim() : styleNarration;
  const addressHints = hints.filter((h) => h.field === "address");
  const greetingHints = hints.filter((h) => h.field === "greeting");
  const roleLong = card.role.replace(/\s+/g, " ").trim().length > MAX_ROLE_CHARS;

  return (
    <div className="flex flex-col gap-4">
      <Section id="sec-basic" title="Cơ bản">
        <div className="flex items-start gap-4">
          {avatar}
          <div className="flex min-w-0 flex-1 flex-col gap-4">
            <TextField
              label="Tên nhân vật"
              required
              value={card.name}
              onChange={(v) => set("name", v)}
              placeholder={vi ? "ví dụ: Hạ Vy" : "e.g. Elias Hart"}
              maxLength={MAX_NAME_CHARS * 2}
              disabled={disabled}
            />
            <TextField
              label="Vai trò"
              value={card.role}
              onChange={(v) => set("role", v)}
              placeholder={vi ? "ví dụ: Chủ tiệm sách mùa thu" : "e.g. Night-shift librarian"}
              maxLength={MAX_ROLE_CHARS * 2}
              error={roleLong ? `Tối đa ${MAX_ROLE_CHARS} ký tự.` : undefined}
              hint="Một dòng ngắn hiện dưới tên trong danh sách."
              disabled={disabled}
            />
          </div>
        </div>
        {share}
        <ChoiceGroup label="Giới tính" value={card.gender} onChange={(g) => set("gender", g)} options={GENDER_OPTIONS} disabled={disabled} />
        <ChoiceGroup
          label="Ngôn ngữ của card"
          value={card.language}
          onChange={(l) => set("language", l)}
          options={LANGUAGE_OPTIONS}
          disabled={disabled}
          hint={
            narration
              ? `Ngôn ngữ mặc định cho story mới. Dẫn truyện sẽ gọi ${card.name.trim() || "nhân vật"} (${GENDER_LABEL[
                  card.gender
                ].toLowerCase()}) là “${narration}”.`
              : "Ngôn ngữ mặc định cho story mới."
          }
        />
        <StylePicker value={card.style_profile} styles={styles} onChange={(s) => set("style_profile", s)} disabled={disabled} />
        <TextField
          label="Đại từ dẫn truyện cho nhân vật (tuỳ chọn)"
          value={narrationOverride}
          onChange={(v) => update((c) => withNarrationOverride(c, v))}
          placeholder={styleNarration ? `mặc định của văn phong: “${styleNarration}”` : "ví dụ: hắn"}
          maxLength={20}
          hint="Ví dụ “hắn” thay cho “anh”. Story mới tạo với card này sẽ dùng sẵn; vẫn đổi được trong thiết lập story."
          disabled={disabled}
        />
        <ChipInput
          label="Tag"
          values={card.tags}
          onChange={(v) => set("tags", v)}
          placeholder="ví dụ: học đường, ngọt, chữa lành"
          hint="Để bạn tìm và lọc; nhân vật không đọc phần này."
          max={MAX_TAGS}
          normalize={(s) => s.toLocaleLowerCase("vi-VN")}
          disabled={disabled}
        />
      </Section>

      <Section
        id="sec-character"
        title="Tính cách và bí mật"
        hint={
          <>
            Mỗi phần 1-3 câu là đủ; viết dài làm nhân vật dễ quên luật. Nhắc tới nhân vật của người chơi bằng{" "}
            <UserPlaceholderBadge />.
          </>
        }
      >
        <TextAreaField
          label="Mô tả"
          value={card.description}
          onChange={(v) => set("description", v)}
          placeholder="Tuổi, thân phận hoặc nghề, quan hệ với {{user}}. Ví dụ: 18 tuổi, lớp trưởng, bạn thanh mai trúc mã của {{user}}."
          userPlaceholder
          maxChars={MAX_TEXT_CHARS}
          disabled={disabled}
        />
        <TextAreaField
          label="Tính cách"
          value={card.personality}
          onChange={(v) => set("personality", v)}
          placeholder="Ví dụ: ngoài lạnh trong nóng, kiệm lời nhưng tinh ý; hay trêu {{user}} để che giấu sự quan tâm."
          userPlaceholder
          maxChars={MAX_TEXT_CHARS}
          disabled={disabled}
        />
        <TextAreaField
          label="Ngoại hình"
          value={card.appearance}
          onChange={(v) => set("appearance", v)}
          placeholder="Ví dụ: cao, tóc đen hơi rối, hay mặc áo sơ mi trắng xắn tay."
          maxChars={MAX_TEXT_CHARS}
          disabled={disabled}
        />
        <TextAreaField
          label="Hoàn cảnh"
          value={card.background}
          onChange={(v) => set("background", v)}
          placeholder="Quá khứ và những gì đã xảy ra giữa nhân vật và {{user}}."
          userPlaceholder
          maxChars={MAX_TEXT_CHARS}
          disabled={disabled}
        />
        <div className="grid gap-5 sm:grid-cols-2">
          <TextAreaField
            label="Mục tiêu"
            value={card.goals}
            onChange={(v) => set("goals", v)}
            placeholder="Điều nhân vật muốn, ví dụ: muốn {{user}} thi đỗ cùng trường đại học."
            userPlaceholder
            maxChars={MAX_TEXT_CHARS}
            disabled={disabled}
          />
          <TextAreaField
            label="Bí mật"
            value={card.secrets}
            onChange={(v) => set("secrets", v)}
            placeholder="Điều nhân vật giấu, chỉ lộ qua Thought. Ví dụ: đã thích {{user}} từ năm mười tuổi."
            userPlaceholder
            maxChars={MAX_TEXT_CHARS}
            disabled={disabled}
          />
        </div>
        <TextAreaField
          label="Cách nói"
          value={card.speech_style}
          onChange={(v) => set("speech_style", v)}
          placeholder="Ví dụ: câu ngắn, hay trêu chọc, ít khi nói thẳng cảm xúc; thỉnh thoảng gọi tên thân mật."
          maxChars={MAX_TEXT_CHARS}
          disabled={disabled}
        />
        <TextAreaField
          label="Lời nói đặc trưng (tuỳ chọn)"
          value={signatureText(card)}
          onChange={(v) => update((c) => withSignatureText(c, v))}
          placeholder={vi ? "Ai đợi cậu. Tớ tiện đường thôi.\nĂn xong rồi hẵng ôn tiếp." : "Tea first, questions later.\nYou're on my rocks, so you're my problem."}
          hint={`Hai hoặc ba câu nói thể hiện rõ tính cách, mỗi câu một dòng (tối đa ${SIGNATURE_MAX_LINES} dòng, ${SIGNATURE_MAX_CHARS} ký tự mỗi dòng). Hiện trên trang nhân vật; để trống thì Lyris tự chọn từ ví dụ thoại.`}
          userPlaceholder
          minRows={2}
          disabled={disabled}
        />
      </Section>

      <EmotionSection card={card} update={update} disabled={disabled} />

      <AddressSection card={card} update={update} profile={profile} hints={addressHints} disabled={disabled} />

      <Section
        id="sec-opening"
        title="Mở đầu"
        hint={
          <>
            Lời mở đầu viết ở ngôi thứ ba, có 1-2 dòng [Thought: …], dừng ở chỗ chờ <UserPlaceholderBadge /> đáp. Không viết lời hay
            hành động thay người chơi.
          </>
        }
      >
        <TextAreaField
          label="Bối cảnh mặc định"
          value={card.scenario}
          onChange={(v) => set("scenario", v)}
          placeholder="Ví dụ: Chiều thứ sáu, thư viện trường sắp đóng cửa; {{user}} ngủ gục trên bàn sau tuần ôn thi."
          hint="Điền sẵn khi tạo story mới; mỗi story có thể sửa riêng."
          userPlaceholder
          maxChars={MAX_TEXT_CHARS}
          disabled={disabled}
        />
        <TextAreaField
          label="Lời mở đầu"
          value={card.greeting}
          onChange={(v) => set("greeting", v)}
          placeholder={
            vi
              ? 'Lạc Dương gõ nhẹ lên mặt bàn.\n\n"Dậy đi, thư viện sắp đóng cửa rồi."\n\n[Thought: Cậu ấy ngủ say thật. Mình đứng đây nhìn bao lâu rồi nhỉ.]\n\nAnh kéo ghế ngồi xuống cạnh {{user}}...'
              : 'Elias taps the desk.\n\n"Wake up, the library is closing."\n\n[Thought: She looks exhausted. How long have I been standing here?]'
          }
          userPlaceholder
          minRows={6}
          maxHeight={480}
          maxChars={MAX_TEXT_CHARS}
          disabled={disabled}
        />
        {greetingHints.length > 0 && <Notice tone="warn" lines={greetingHints.map((h) => h.text)} />}
        <AlternateGreetings values={card.alternate_greetings} onChange={(v) => set("alternate_greetings", v)} disabled={disabled} />
        <TextAreaField
          label="Ví dụ thoại"
          value={card.example_dialogues}
          onChange={(v) => set("example_dialogues", v)}
          placeholder={'{{user}}: Cậu đợi tớ à?\n{{char}}: "Ai đợi cậu. Tớ tiện đường thôi."'}
          hint="Tuỳ chọn. Dùng {{char}}: và {{user}}: ở đầu dòng; để trống một dòng giữa các đoạn."
          userPlaceholder
          minRows={3}
          maxChars={MAX_TEXT_CHARS}
          disabled={disabled}
        />
      </Section>

      {world}

      <Section id="sec-notes" title="Ghi chú của người tạo" hint="Chỉ bạn thấy, nhân vật không bao giờ đọc. Ghi nguồn, ý tưởng, việc cần sửa…">
        <TextAreaField
          label="Ghi chú"
          value={card.creator_notes}
          onChange={(v) => set("creator_notes", v)}
          placeholder="Ví dụ: lấy cảm hứng từ truyện X; nhớ thử lại lời mở đầu số 2."
          maxChars={MAX_TEXT_CHARS}
          disabled={disabled}
        />
      </Section>
    </div>
  );
}
