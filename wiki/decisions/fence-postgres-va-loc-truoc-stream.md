# Fence ở Postgres cho lượt chat, kind mới qua bảng tra, lọc đầu ra trước khi stream

- **Ngày:** 2026-11-14 · **Ai quyết:** AI chọn sau phản biện (tạm chọn, PO đổi được)

## Bối cảnh

Phản biện bản thiết kế host ([docs/server.md §21](../../docs/server.md)) chỉ ra ba chỗ sai dữ liệu hoặc vô tác dụng:

- Khoá story ở Redis không nguyên tử với commit Postgres và có thể mất khi Redis failover. Pod chậm lỡ hạn lease thì
  `hold_sweeper` nhả giữ chỗ, rồi `charge_hold` trả `None`, mà code hiện tại (`coins/wallet.py` `charge`) vẫn lưu câu trả
  lời: thành một lượt miễn phí.
- `coin_ledger.kind` và `coin_holds.release_reason` là `CHECK (… IN …)` (`0012_coins.sql`); thêm giá trị ở Postgres cần
  `DROP CONSTRAINT`, trái luật migration chỉ thêm.
- Lọc đầu ra (F60) chạy sau khi stream xong: chữ bị chặn đã hiện trên màn người chơi.

## Lựa chọn

1. **Fence là dòng giữ chỗ coin ở Postgres.** Transaction lưu câu trả lời khoá `coin_holds` `FOR UPDATE`; sweeper dùng
   `FOR UPDATE SKIP LOCKED` nên không nhả giữ chỗ đang được trừ. Chỉ mục "một giữ chỗ mở mỗi tài khoản" là khoá thật;
   khoá Redis chỉ để từ chối sớm. Giữ chỗ đã bị nhả lúc lưu → **vẫn lưu** câu trả lời và trừ thẳng cùng
   `idem_key = chat:{hold_id}` nếu đủ coin; không đủ thì miễn, đếm `lyris_hold_lost_total`, cảnh báo khi > 0,1 %.
   Thời gian nhả khi pod chết: ≤ 40 s (lease 30 s + sweeper 10 s).
2. **Kind/lý do có thể thêm là bảng tra** (`coin_kinds`, `hold_release_reasons`) + khoá ngoại ở Postgres; baseline có sẵn
   `purchase`, `purchase_refund`, `debt_repay`, `queue_full`, `content_filtered`. SQLite giữ nguyên `CHECK`: bản tự chạy
   không bao giờ ghi các giá trị này.
3. **Lọc đầu ra theo đoạn trước khi gửi:** gom tới hết câu hoặc 24 token, chấm cùng ngữ cảnh, chỉ gửi đoạn `safe`; đoạn
   `unsafe` → dừng, gửi câu lảng trong vai, nhả giữ chỗ `content_filtered`. Lưới thứ hai sau `done` dùng sự kiện SSE
   `retract{from_seq}`. SLO mới "chữ đầu tiên hiện" p50 ≤ 2,5 s, p95 ≤ 5 s.

## Vì sao

- (1) Xoá câu trả lời người chơi đã đọc là tệ hơn một lượt miễn phí hiếm gặp, và trái luật "lỗi máy không làm người chơi
  thiệt" ([docs/coins.md §3](../../docs/coins.md)). Fence ở Postgres đúng cả khi Redis mất dữ liệu.
- (2) Không cần dựng lại bảng `coin_ledger` (có trigger chỉ thêm) ở SQLite, không cần ngoại lệ cho
  `test_migrations_additive_only`.
- (3) App Store 1.2 cần lọc có tác dụng; lọc sau khi stream thì người chơi đã thấy chữ.

## Đã cân nhắc

- Không lưu câu trả lời khi giữ chỗ đã bị nhả (đề xuất của phản biện): bác, lý do ở trên.
- Migration dựng lại bảng cho SQLite như một ngoại lệ có kiểm soát: không cần.
- Đệm cả câu trả lời rồi mới gửi: mất cảm giác chữ chảy, TTFT hiển thị tăng 5–15 s.

## Nguồn

- [raw/2026-11-14-server-lon-appstore-tra-loi.md](../raw/2026-11-14-server-lon-appstore-tra-loi.md)
- [docs/server.md §4.3, §5.2, §13, §21](../../docs/server.md)
- Tính năng: [F50](../features/F50-postgres.md), [F51](../features/F51-redis-api-khong-trang-thai.md), [F60](../features/F60-kiem-duyet-chan.md)
