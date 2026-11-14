import { useEffect } from "react";
import type { MouseEvent } from "react";
import { Wordmark } from "../../components/brand";
import { IconChevronLeft } from "../../components/icons";
import { LegalContent, legalTitle } from "../../components/LegalDocument";
import { PRIVACY_LABEL, TERMS_LABEL } from "../../lib/compliance";
import { navigate } from "../../lib/router";
import { previousRouteName } from "../../lib/track";
import type { LegalDoc } from "../../types";
import { ThemeToggle } from "../../theme";

/**
 * "#/privacy" and "#/terms" (docs/compliance.md §3): open to everyone, signed in or not, also before
 * the owner setup. A reading page: 680px column, 16px/1.65 text, the wordmark on top so a visitor
 * from a shared link knows where they are. "Quay lại" goes back inside the app when there is a page
 * to go back to; otherwise to "#/" (the hub, or the sign-in page when signed out).
 */
export function LegalPage({ doc }: { doc: LegalDoc }) {
  const title = legalTitle(doc);
  const other: LegalDoc = doc === "privacy" ? "terms" : "privacy";

  useEffect(() => {
    document.title = `${title} · Lyris`;
    window.scrollTo(0, 0);
  }, [title]);

  const back = (e: MouseEvent<HTMLAnchorElement>) => {
    if (previousRouteName() !== null && window.history.length > 1) {
      e.preventDefault();
      window.history.back();
    }
  };

  return (
    <div className="min-h-dvh bg-bg">
      <header className="sticky top-0 z-20 border-b border-line bg-bg pt-safe">
        <div className="mx-auto flex h-14 w-full max-w-[720px] items-center gap-1 pr-2 pl-1.5 sm:pl-2.5">
          <a
            href="#/"
            onClick={back}
            className="inline-flex h-11 shrink-0 items-center gap-1 rounded-full pr-3 pl-2 text-[15px] font-medium text-muted transition-colors duration-150 hover:bg-surface-2 hover:text-fg"
          >
            <IconChevronLeft aria-hidden="true" className="text-[20px]" />
            Quay lại
          </a>
          <div className="ml-auto flex items-center gap-1">
            <ThemeToggle />
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-[720px] px-5 pt-6 pb-[max(3rem,env(safe-area-inset-bottom))] sm:px-6 sm:pt-10">
        <div className="mb-6 flex flex-col gap-3">
          <Wordmark size={28} />
          <h1 className="text-[24px] leading-tight font-semibold text-fg sm:text-[28px]">{title}</h1>
        </div>
        <article lang="vi" className="max-w-[680px]">
          <LegalContent key={doc} doc={doc} />
        </article>
        <nav aria-label="Văn bản khác" className="mt-10 flex flex-wrap gap-x-5 border-t border-line pt-4 text-[14px]">
          <a
            href={`#/${other}`}
            onClick={(e) => {
              e.preventDefault();
              navigate(`#/${other}`);
            }}
            className="inline-flex min-h-11 items-center text-muted underline decoration-line-strong underline-offset-2 transition-colors duration-150 hover:text-fg"
          >
            {other === "privacy" ? PRIVACY_LABEL : TERMS_LABEL}
          </a>
        </nav>
      </main>
    </div>
  );
}
