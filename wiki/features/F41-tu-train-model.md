# F41 — Tự train model (LoRA)

- **Trạng thái:** xem `memory/features.json` · **Phase:** Phase 5
- **Giai đoạn:** Kế hoạch
- **Màn hình:** Không có màn hình riêng (chạy nền hoặc ngoài app).

## Là gì

Fine-tune model riêng bằng LoRA từ dữ liệu synthetic, public và chat đã đánh giá, rồi nạp lại vào app. Phase 0 đã thử train đồ chơi trên 12B nhưng không vừa RAM, nên hoãn tới khi app xong.

## Hoạt động thế nào

- Mong muốn: Lyris có model riêng, viết hay hơn model gốc ở văn phong và xưng hô.
- Chỉ dùng chat của người đã đồng ý cho dùng để train.
- Hiện chưa làm. Phase 0 đã thử train đồ chơi (`training/toy/`); 12B không vừa RAM nên hoãn tới khi app xong.

Kỹ thuật:

- Cách làm: LoRA trên model gốc, không train từ đầu.
- Cột `training_opt_in` đã có trong migration `0008_auth.sql`, nhưng chưa có `build_dataset.py`, `train.sh`, `deploy.sh`.

## Done when

- [ ] Unit: chỉ chat của tài khoản có `training_opt_in = 1` vào dataset.
- [ ] Unit: `build_dataset.py` gộp, lọc, chia 90/10.
- [ ] Bot: chủ máy chọn được model theo story trong 'Nâng cao'; 'Tạo lại câu trả lời' có A/B mù giữa hai model.
- [ ] Model thật: `train.sh` chạy hết trên máy 24GB không swap nặng; `deploy.sh` tạo được `lyris-v1` trong Ollama.
- [ ] Model thật: harness: `lyris-v1` bằng hoặc hơn base ở godmodding, format, xưng hô.

## Tests

Chưa có test: tính năng còn là kế hoạch. Viết test cùng lúc với code.

Tên check bot dự kiến (chưa có trong `environment/e2e.mjs`, thêm khi làm): `bot: chọn model theo story và A/B mù`.

## Ngoài Done when

Không chặn ✅ (cần thử tay, dịch vụ thật, hoặc còn là kế hoạch).

- Thử tay: đọc 100 mẫu của dataset trước khi train.

## Liên quan

- **Code:** [`training/toy/`](../../training/toy/), [`backend/lyris/db/migrations/0008_auth.sql`](../../backend/lyris/db/migrations/0008_auth.sql)
- **Tài liệu:** [plan.md §8, Phase 0, Phase 5](../../docs/plan.md)
- **Quyết định:** [lam-app-truoc-fine-tune-sau](../decisions/lam-app-truoc-fine-tune-sau.md), [lora-khong-train-tu-dau](../decisions/lora-khong-train-tu-dau.md), [du-lieu-train-co-dong-y](../decisions/du-lieu-train-co-dong-y.md)
