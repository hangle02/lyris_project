# F54 — Lưu ảnh trên object storage (S3)

- **Trạng thái:** xem `memory/features.json` · **Phase:** Máy chủ (sau khi nộp bài)
- **Giai đoạn:** Kế hoạch
- **Màn hình:** Studio (`#/studio/{id}`), persona (`#/personas`), Tài khoản (`#/me`): không đổi chữ.

## Là gì

Ảnh đại diện, ảnh bìa, ảnh persona nằm trên kho S3-compatible thay vì ổ đĩa của một máy. Route ảnh cũ giữ nguyên kiểm
quyền rồi chuyển hướng tới CDN (ảnh công khai) hoặc URL ký 5 phút (ảnh riêng). Thiết kế: [docs/server.md §9](../../docs/server.md).

## Hoạt động thế nào

- `BlobStore`: `FilesystemBlobStore` (bản tự chạy, `LYRIS_AVATARS_DIR`) và `S3BlobStore` (bản host, `LYRIS_BLOB=s3`).
- `normalize_image` (Pillow) giữ nguyên: PNG, xoay EXIF, bỏ metadata, ≤ 768×768 hoặc 1500×500.
- Xoá ảnh là job `blob_delete` sau commit.
- Ảnh người khác thấy được (nhân vật công khai, avatar/ảnh bìa tài khoản) qua job `image_scan` **trước khi** công khai
  (F60): so hash CSAM bằng một API đồng bộ (PhotoDNA Cloud hoặc nhà cung cấp quét hash có hợp đồng) + bộ phân loại ảnh
  nhạy cảm của Lyris. Công cụ quét CSAM của Cloudflare chỉ quét ảnh đã phục vụ qua CDN (sau khi công khai) nên chỉ là
  lớp thứ hai, không phải cổng.
- `302` tới URL ký của ảnh riêng mang `Cache-Control: private, no-store`, để trình duyệt không dùng lại URL đã hết hạn.

## Done when

- [ ] Unit: `FilesystemBlobStore` và `S3BlobStore` (S3 giả trong bộ nhớ) qua cùng bộ test `put/get/delete/presign` (`test_blobstore_contract`).
- [ ] Unit: tải avatar nhân vật → object `avatars/card/{id}-{8 hex}.png` là PNG ≤ 768×768, không còn EXIF (`test_avatar_upload_goes_to_blobstore`).
- [ ] Unit: `GET /api/cards/{id}/avatar?v=…` của nhân vật công khai → 302 tới URL CDN; nhân vật riêng của người khác → 404; của mình → 302 tới URL ký hết hạn ≤ 300 s, response có `Cache-Control: private, no-store` (`test_avatar_redirect_public_private`).
- [ ] Unit: xoá tài khoản → xếp job `blob_delete` cho mọi ảnh của tài khoản sau commit; transaction rollback → 0 job (`test_account_delete_enqueues_blob_delete`).
- [ ] Unit: nhân vật bật Công khai có avatar → job `image_scan` gọi API so hash giả **trước khi** nhân vật vào danh sách công khai; kết quả `flagged` → nhân vật không có trong danh sách nhân vật công khai tới khi staff duyệt; API so hash lỗi/hết giờ → nhân vật cũng chưa công khai (không mở khi chưa quét) (`test_public_avatar_scan_gate`).
- [ ] Bot: với `LYRIS_BLOB=s3` trỏ S3 giả, đổi avatar ở `#/studio/{id}` rồi mở `#/explore`: thẻ nhân vật có `<img>` tải được (`naturalWidth > 0`).

## Tests

- `backend/tests/test_blobstore.py::test_blobstore_contract`
- `backend/tests/test_blobstore.py::test_avatar_upload_goes_to_blobstore`
- `backend/tests/test_blobstore.py::test_avatar_redirect_public_private`
- `backend/tests/test_blobstore.py::test_account_delete_enqueues_blob_delete`
- `backend/tests/test_image_scan.py::test_public_avatar_scan_gate`
- bot: avatar qua kho ảnh S3

## Liên quan

- **Tài liệu:** [docs/server.md §9](../../docs/server.md), [docs/auth.md §4.6](../../docs/auth.md), [docs/compliance.md §4](../../docs/compliance.md)
- **Code hiện tại:** [`studio/avatars.py`](../../backend/lyris/studio/avatars.py), [`api/routes_studio.py`](../../backend/lyris/api/routes_studio.py), [`compliance/account_data.py`](../../backend/lyris/compliance/account_data.py)
- **Tính năng:** [F38](F38-gui-hinh-anh.md) (gửi ảnh trong chat dùng cùng kho), [F60](F60-kiem-duyet-chan.md)
