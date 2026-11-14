-- Sổ coin chỉ thêm cũng chặn DELETE (rà soát bảo mật coin 2026-11-14): 0012 chỉ chặn UPDATE, nên một lệnh
-- `DELETE FROM coin_ledger` làm số dư ví lệch khỏi tổng sổ. Dòng sổ chỉ mất khi xoá tài khoản (ON DELETE CASCADE,
-- docs/compliance.md §4): lúc đó dòng `accounts` đã bị xoá nên điều kiện WHEN không còn đúng và cascade chạy được.
-- Chỉ thêm trigger, không đổi bảng, không xoá dữ liệu.
CREATE TRIGGER coin_ledger_no_delete
BEFORE DELETE ON coin_ledger
WHEN EXISTS (SELECT 1 FROM accounts WHERE id = OLD.account_id)
BEGIN SELECT RAISE(ABORT, 'coin_ledger chỉ thêm, không sửa'); END;
