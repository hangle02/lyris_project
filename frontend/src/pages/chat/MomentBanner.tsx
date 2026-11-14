import { Badge } from "../../components/ui";
import type { Moment } from "../../types";
import { momentLine } from "./chatLogic";

/**
 * Slim line under the chat header with the current emotional beat (extras.moment), e.g.
 * "Khoảnh khắc: Đón nhận sự quan tâm dịu dàng từ Hạ Vy" and its effect "+Thương mến".
 */
export function MomentBanner({ moment }: { moment: Moment }) {
  const { text, effect } = momentLine(moment);
  return (
    <div className="border-t border-line bg-bg/50">
      <p className="mx-auto flex max-w-[720px] flex-wrap items-center gap-x-2 gap-y-1 px-4 py-2 text-[13px] leading-snug text-muted">
        <span className="min-w-0">
          <span className="font-semibold text-accent-2">Khoảnh khắc:</span> <span className="text-fg">{text}</span>
        </span>
        {effect && <Badge tone="gold">{effect}</Badge>}
      </p>
    </div>
  );
}
