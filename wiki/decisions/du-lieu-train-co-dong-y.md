# Dữ liệu train chỉ lấy từ tài khoản đã đồng ý

- **Ngày:** 2026-11-14 · **Ai quyết:** thiết kế

## Bối cảnh

Phase 5 dùng chat thật để train; nay có nhiều tài khoản.

## Lựa chọn

Chỉ lấy chat từ tài khoản có training_opt_in = 1 (mặc định chỉ chủ máy). Trạng thái: Chưa làm (Phase 5).

## Vì sao

Story của thành viên không được vào dataset nếu họ chưa đồng ý.

## Đã cân nhắc

Lấy mọi chat trên máy.

## Nguồn

- [docs/plan.md](../../docs/plan.md) Phase 5
- [docs/auth.md](../../docs/auth.md) §0, §11
