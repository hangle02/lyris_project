# Tự train model (LoRA)

- **Trạng thái:** Chưa làm · **Phase:** Phase 5
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

- [ ] Chỉ chat của tài khoản có `training_opt_in = 1` vào dataset.
- [ ] `build_dataset.py` gộp, lọc, chia 90/10; đọc tay 100 mẫu.
- [ ] `train.sh` chạy hết trên máy 24GB không swap nặng.
- [ ] `deploy.sh` tạo được `lyris-v1` trong Ollama.
- [ ] Harness: `lyris-v1` bằng hoặc hơn base ở godmodding, format, xưng hô.
- [ ] Trong app chọn model theo story và có A/B mù khi tạo lại.

## Liên quan

- **Code:** [`training/toy/`](../../training/toy/), [`backend/lyris/db/migrations/0008_auth.sql`](../../backend/lyris/db/migrations/0008_auth.sql)
- **Tài liệu:** [plan.md §8, Phase 0, Phase 5](../../docs/plan.md)
- **Quyết định:** [lam-app-truoc-fine-tune-sau](../decisions/lam-app-truoc-fine-tune-sau.md), [lora-khong-train-tu-dau](../decisions/lora-khong-train-tu-dau.md), [du-lieu-train-co-dong-y](../decisions/du-lieu-train-co-dong-y.md)
