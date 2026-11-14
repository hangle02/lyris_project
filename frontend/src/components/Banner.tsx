import { InlineAlert } from "./ui/InlineAlert";
import type { InlineAlertProps } from "./ui/InlineAlert";

/** Notice above the chat composer: the foundation InlineAlert in the chat's 720px column. */
export function Banner(props: Omit<InlineAlertProps, "className">) {
  return (
    <div className="mx-auto w-full max-w-[720px] px-4 pb-2">
      <InlineAlert {...props} />
    </div>
  );
}
