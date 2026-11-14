import { useEffect, useState } from "react";
import { errorMessage } from "../../api/client";
import { Button, InlineAlert } from "../../components/ui";
import { signOut, useAuthAccount } from "../../hooks/useAuth";
import { AuthLayout } from "./AuthLayout";
import { ChangePasswordForm } from "./ChangePasswordForm";
import { FORCE_INTRO } from "./logic";

/**
 * Shown over any hash while the account uses a temporary password (docs/auth.md §7.3): every other
 * API answers 403 until it is changed. "Đăng xuất" leaves without changing it.
 */
export function ForcePasswordPage() {
  const account = useAuthAccount();
  const [leaving, setLeaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    document.title = "Đặt mật khẩu mới · Lyris";
  }, []);

  const leave = async () => {
    setLeaving(true);
    setError(null);
    try {
      await signOut(false);
    } catch (e) {
      setError(errorMessage(e));
      setLeaving(false);
    }
  };

  return (
    <AuthLayout title="Đặt mật khẩu mới" intro={FORCE_INTRO}>
      {account && (
        <p className="-mt-3 text-[14px] text-muted">
          Tài khoản <span className="font-semibold text-fg">@{account.handle}</span>
        </p>
      )}
      <ChangePasswordForm
        currentLabel="Mật khẩu tạm"
        submitLabel="Lưu mật khẩu"
        handle={account?.handle ?? null}
        secondary={
          <Button variant="ghost" onClick={() => void leave()} loading={leaving} className="max-sm:w-full">
            Đăng xuất
          </Button>
        }
      />
      {error && <InlineAlert tone="error" text={error} />}
    </AuthLayout>
  );
}
