# Coin F44: các điểm tạm chọn khi build

- **Ngày:** 2026-11-14 · **Ai quyết:** AI khi build F44 (mọi điểm dưới đây là **tạm chọn**, PO đổi được)

> **2026-11-14 22:15:** F44 được làm lại ([xep-hang-nhan-vat-hot](xep-hang-nhan-vat-hot.md)). Còn đúng: đếm người chơi qua story
> và bản sao, khoá sổ thêm uid khi id bị dùng lại (áp dụng cho `rank:`), `creator` chỉ có trong JSON khi có giá trị, sự kiện ghi
> tách, cách bot dựng người chơi. Hết hiệu lực: trần mốc 10, `settle_milestones`/`settle_creator`, dòng "Mốc tiếp theo".

## Bối cảnh

Khi build [F44](../features/F44-thuong-sang-tac.md) theo [docs/coins.md §5](../../docs/coins.md) và quyết định
[moc-nguoi-choi-sang-tac](moc-nguoi-choi-sang-tac.md), vài chỗ thiết kế chưa nói rõ. Ghi lại để PO thấy.

## Lựa chọn

- **Đếm qua story và bản sao, không chỉ qua `coin_holds.origin_card_id`:** một câu trả lời được tính cho X khi giữ chỗ
  `charged` có `origin_card_id = X` VÀ story của chính người đó đang trỏ tới một bản sao có `origin_card_id = X`. Lý do:
  SQLite dùng lại id của nhân vật lớn nhất vừa bị xoá, nên nhân vật mới có thể mang id cũ; bản sao của nhân vật đã xoá có
  `origin_card_id` NULL nên giữ chỗ cũ không bao giờ được đếm cho nhân vật mới. Người chơi xoá story trước khi đủ 3 câu thì
  các câu trong story đó không còn được cộng dồn.
- **Khoá sổ khi id được dùng lại:** khoá vẫn là `milestone:<X>:<m>`. Riêng trường hợp khoá đó đã có trong sổ (id X đã từng
  thuộc một nhân vật đã xoá), khoá thành `milestone:<X>:<m>:<uid của nhân vật mới>` để không đụng dòng cũ.
- **Trần mốc 10 đếm trong sổ** (`coin_ledger`, `kind = 'creator_milestone'`, `milestone = 10`, ngày coin từ hôm nay − 6),
  nên lần thưởng của nhân vật đã xoá vẫn tính vào trần. Các mốc 10 đang chờ được trả theo thứ tự nhân vật có người chơi
  thứ 10 trước.
- **Khi nào chạy lại `settle`:** sau mỗi lần trừ coin có người chơi mới đủ điều kiện; mỗi lần `POST /api/coins/checkin`
  của người tạo (không chỉ lần đầu ngày, vì chạy lại không đổi gì); khi lưu nhân vật ở trạng thái Công khai
  (`PUT /api/cards/{id}`); khi chủ máy mở khoá người tạo. Coin tắt (`LYRIS_COINS=0`): không trả, mốc chờ tới khi bật lại.
- **Chủ máy ẩn nhân vật** (F35) chỉ là chuyển về Riêng tư, nên "đang công khai" là đủ điều kiện; người tạo bật Công khai lại
  thì mốc được trả.
- **Người tạo là chủ máy:** mốc chỉ được ghi (`outcome = 'owner'`) khi nhân vật đang công khai, như người tạo thường.
  `GET /api/cards/{id}` của chủ máy (và khi coin tắt) có `next_reward: null`; dòng trong trình sửa không hứa coin:
  "3 người chơi · Mốc tiếp theo: 10 người chơi", đạt hết thì chỉ "120 người chơi".
- **`creator` chỉ có trong JSON khi có giá trị:** card riêng tư, bản sao và card của người khác không có khoá `creator`
  (hình dạng `CardOut` cũ giữ nguyên).
- **Dòng trong trình sửa** có thêm một câu giải thích nhỏ: "Người chơi là tài khoản khác đã trò chuyện với nhân vật này ít
  nhất 3 câu trả lời, ở 2 ngày khác nhau." (trang [card-editor](../screens/card-editor.md) đã nói ý này).
- **Sự kiện `creator_milestone_reached`** và `coins_granted{source: creator_milestone}` được ghi **tách** (không gắn tài
  khoản, thiết bị, story), vì chúng xảy ra trong request của người chơi khác; vẫn tôn trọng việc người tạo tắt chia sẻ.
- **Bot:** người chơi cần câu trả lời ở 2 ngày coin, HTTP API không dựng được trong một lượt bot, nên
  `environment/seed-creator-players.py` dựng 12 người chơi trong DB tạm của bot bằng chính code của app (giữ chỗ hôm qua và
  hôm nay, `note_charged`). Không sửa `fake-server.py`.

## Nguồn

- [docs/coins.md §5, §7, §11](../../docs/coins.md), [F44](../features/F44-thuong-sang-tac.md)
- Code: `backend/lyris/coins/creator.py`, `backend/lyris/coins/wallet.py`, `backend/tests/test_coins_creator.py`
