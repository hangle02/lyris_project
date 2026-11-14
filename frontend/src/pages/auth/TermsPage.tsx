import { useEffect, useState } from "react";
import { api, errorMessage, errorTechnical } from "../../api/client";
import { LegalDialog } from "../../components/LegalDocument";
import { Button, InlineAlert } from "../../components/ui";
import { refreshAuth, signOut, useAuth } from "../../hooks/useAuth";
import { TERMS_ACCEPT, TERMS_SCREEN_INTRO, TERMS_SCREEN_POINTS, TERMS_SCREEN_TITLE } from "../../lib/compliance";
import type { LegalDoc } from "../../types";
import { AuthLayout } from "./AuthLayout";

/**
 * Asked once (docs/compliance.md §3): an account made before the Terms existed, or before they
 * changed, agrees here before the app opens. The texts open in a dialog; "Đăng xuất" is the way out.
 */
export function TermsPage() {
  const auth = useAuth();
  const version = auth.state?.legal_version ?? "";
  const [reading, setReading] = useState<LegalDoc | null>(null);
  const [busy, setBusy] = useState<"accept" | "out" | null>(null);
  const [error, setError] = useState<{ text: string; technical: string | null } | null>(null);

  useEffect(() => {
    document.title = `${TERMS_SCREEN_TITLE} · Lyris`;
  }, []);

  const accept = async () => {
    setBusy("accept");
    setError(null);
    try {
      await api.acceptTerms(version);
      await refreshAuth();
    } catch (e) {
      // 409: the texts changed meanwhile; ask the gate for the new version and try again.
      if ((e as { status?: number }).status === 409) void refreshAuth();
      setError({ text: errorMessage(e), technical: errorTechnical(e) });
      setBusy(null);
    }
  };

  const leave = async () => {
    setBusy("out");
    try {
      await signOut(false);
    } catch (e) {
      setError({ text: errorMessage(e), technical: errorTechnical(e) });
      setBusy(null);
    }
  };

  const link = (doc: LegalDoc, label: string) => (
    <a
      href={`#/${doc}`}
      onClick={(e) => {
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
        e.preventDefault();
        setReading(doc);
      }}
      className="font-semibold text-fg underline decoration-line-strong underline-offset-4 transition-colors duration-150 hover:decoration-accent"
    >
      {label}
    </a>
  );

  return (
    <AuthLayout title={TERMS_SCREEN_TITLE} intro={TERMS_SCREEN_INTRO}>
      <ul className="flex flex-col gap-2.5 rounded-card border border-edge bg-surface px-5 py-4 text-[14px] leading-snug text-prose">
        {TERMS_SCREEN_POINTS.map((p) => (
          <li key={p} className="flex gap-2.5">
            <span aria-hidden="true" className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
            <span>{p}</span>
          </li>
        ))}
      </ul>
      <p className="text-[14px] leading-relaxed text-muted">
        Đọc đầy đủ: {link("terms", "Điều khoản sử dụng")} và {link("privacy", "Chính sách quyền riêng tư")}.
      </p>
      <div className="flex flex-col gap-3">
        <Button variant="primary" block loading={busy === "accept"} disabled={busy !== null || !version} onClick={() => void accept()}>
          {TERMS_ACCEPT}
        </Button>
        <Button variant="ghost" block loading={busy === "out"} disabled={busy !== null} onClick={() => void leave()}>
          Đăng xuất
        </Button>
        {error && <InlineAlert tone="error" text={error.text} technical={error.technical} />}
      </div>
      <LegalDialog doc={reading} onClose={() => setReading(null)} />
    </AuthLayout>
  );
}
