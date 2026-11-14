import { forwardRef, useState } from "react";
import type { MouseEvent } from "react";
import { LegalDialog } from "../../components/LegalDocument";
import { Checkbox } from "../../components/ui";
import { CONSENT_PARTS } from "../../lib/compliance";
import type { LegalDoc } from "../../types";

const LINK =
  "font-semibold text-fg underline decoration-line-strong underline-offset-4 transition-colors duration-150 hover:decoration-accent";

/**
 * "Tôi đồng ý với Điều khoản và Chính sách quyền riêng tư" (docs/compliance.md §3), required at signup
 * and owner setup. The two names open the text in a dialog over the form, so nothing typed is lost;
 * they are real links too ("#/terms", "#/privacy") for a new tab.
 */
export const ConsentField = forwardRef<
  HTMLInputElement,
  { checked: boolean; onChange: (checked: boolean) => void; error?: string; disabled?: boolean }
>(function ConsentField({ checked, onChange, error, disabled }, ref) {
  const [reading, setReading] = useState<LegalDoc | null>(null);
  const open = (doc: LegalDoc) => (e: MouseEvent<HTMLAnchorElement>) => {
    // A plain tap reads in place; a modified click (new tab) keeps the browser's behaviour.
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
    e.preventDefault();
    setReading(doc);
  };
  return (
    <>
      <Checkbox
        ref={ref}
        checked={checked}
        onChange={onChange}
        error={error}
        disabled={disabled}
        label={
          <>
            {CONSENT_PARTS.before}
            <a href="#/terms" onClick={open("terms")} className={LINK}>
              {CONSENT_PARTS.terms}
            </a>
            {CONSENT_PARTS.middle}
            <a href="#/privacy" onClick={open("privacy")} className={LINK}>
              {CONSENT_PARTS.privacy}
            </a>
          </>
        }
      />
      <LegalDialog doc={reading} onClose={() => setReading(null)} />
    </>
  );
});

/** "Quyền riêng tư · Điều khoản" under the sign-in forms. */
export function LegalLinks() {
  return (
    <p className="flex flex-wrap items-center gap-x-1 text-[13px] text-muted">
      <a href="#/privacy" className="inline-flex min-h-11 items-center px-1 underline decoration-line-strong underline-offset-2 transition-colors duration-150 hover:text-fg">
        Quyền riêng tư
      </a>
      <span aria-hidden="true">·</span>
      <a href="#/terms" className="inline-flex min-h-11 items-center px-1 underline decoration-line-strong underline-offset-2 transition-colors duration-150 hover:text-fg">
        Điều khoản
      </a>
    </p>
  );
}
