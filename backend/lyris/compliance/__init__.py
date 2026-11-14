"""Tuân thủ khi ra mắt (docs/compliance.md).

- `legal`: Điều khoản + Chính sách quyền riêng tư (docs/legal/), phiên bản, lưu lần đồng ý.
- `reports`: báo cáo lời trả lời của AI (bảng `content_reports`).
- `account_data`: xoá tài khoản và xuất dữ liệu cá nhân.

Route: `lyris.api.routes_compliance`. Module con import riêng (tránh vòng import với lyris.auth / lyris.db).
"""
