import { useState } from "react";
import { Button, Card } from "../../components/ui";
import { cx } from "../../components/ui/logic";
import { useAccount } from "../../hooks/useAccount";
import { EditProfileSheet } from "./EditProfileSheet";

/**
 * Top of the hub until the account is set up (docs/accounts.md §5, `profile_completed = false`):
 * one line of invitation and a button that opens "Sửa profile". Never blocks the app; gone once
 * the profile is saved. Shows nothing while the account loads or when it cannot be read.
 */
export function AccountInvite({ className }: { className?: string }) {
  const { account } = useAccount();
  const [open, setOpen] = useState(false);

  // Keep the sheet mounted while open: saving flips profile_completed and would unmount it mid-close.
  if (!account || (account.profile_completed && !open)) return null;

  return (
    <>
      {!account.profile_completed && (
        <Card
          padding="sm"
          className={cx("flex items-center gap-3 sm:gap-4", className)}
        >
          <div className="min-w-0 flex-1">
            <h2 className="text-[16px] leading-snug font-semibold text-fg">Đặt tên cho tài khoản của bạn</h2>
            <p className="mt-0.5 text-[14px] leading-snug text-muted">
              Tên và @handle hiện trên profile và trên nhân vật bạn tạo.
            </p>
          </div>
          <Button size="sm" variant="secondary" onClick={() => setOpen(true)} className="shrink-0">
            Đặt tên
          </Button>
        </Card>
      )}
      <EditProfileSheet open={open} onClose={() => setOpen(false)} />
    </>
  );
}
