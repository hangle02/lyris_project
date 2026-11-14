# Thưởng sáng tác theo bảng xếp hạng "Nhân vật hot" (thay thưởng mốc người chơi)

- **Ngày:** 2026-11-14 · **Ai quyết:** người dùng (1A 2C 3A 4A 5A, [raw](../raw/2026-11-14-f44-bang-xep-hang-tra-loi.md), ý gốc
  [raw](../raw/2026-11-14-f44-bang-xep-hang.md)) + thiết kế (các điểm ghi "(tạm chọn)")
- **Thay:** [moc-nguoi-choi-sang-tac](moc-nguoi-choi-sang-tac.md) (phần định nghĩa "người chơi" của trang đó vẫn dùng)

## Bối cảnh

F44 bản cũ thưởng +100/+300/+600 khi nhân vật công khai đạt 10/50/100 người chơi. Chủ dự án muốn đổi: thưởng khi nhân vật
"leo lên bảng xếp hạng top 100/50/10 nhân vật hot" (100/200/300 coin, mỗi nhân vật một lần), làm bảng xếp hạng nhân vật, và
thưởng nhỏ (khoảng 50) khi lần đầu công khai nhân vật. Rồi chốt: 1A thay hẳn thưởng mốc; 2C hot = tổng người chơi từ trước
tới nay; 3A mỗi bậc một lần, cộng dồn; 4A mục "Nhân vật hot" trong Khám phá, top 100, cập nhật mỗi giờ; 5A +50 một lần mỗi tài
khoản khi nhân vật công khai đủ 24 giờ và có ≥ 1 người chơi khác. Thêm: bỏ khung Hạ Vy to ở Khám phá, thay bằng bảng xếp hạng,
và có thanh tìm kiếm ([kham-pha-tim-kiem-bo-khung-noi-bat](kham-pha-tim-kiem-bo-khung-noi-bat.md)).

## Lựa chọn

- **Thay hẳn** thưởng mốc 10/50/100 (PO 1A). Dòng sổ mốc đã trả giữ nguyên, vẫn hiện trong lịch sử ví; không trừ vào thưởng
  xếp hạng, không tính vào trần (tạm chọn).
- **Người chơi** giữ định nghĩa cũ: tài khoản khác, không phải người tạo, không phải chủ máy, ≥ 3 câu trả lời đã trả coin ở ≥ 2
  ngày coin (tạm chọn, từ [moc-nguoi-choi-sang-tac](moc-nguoi-choi-sang-tac.md)).
- **Hot = tổng người chơi từ trước tới nay** (PO 2C). Bằng nhau: đạt số đó sớm hơn đứng trước, rồi id nhỏ hơn (tạm chọn).
- **Lên bảng** khi: nhân vật gốc đang công khai, người tạo đang hoạt động, ≥ 1 người chơi (tạm chọn). Nhân vật của chủ máy có
  hạng nhưng không có coin.
- **Bậc** top 100 / 50 / 10 → +100 / +200 / +300, mỗi bậc một lần cho mỗi nhân vật, cộng dồn (PO 3A).
- **Bậc top N chỉ đạt khi các nhân vật được xếp hạng thuộc ít nhất N người tạo khác nhau** (tạm chọn; bản đầu đếm nhân vật,
  đổi sau rà soát 2026-11-14, xem "Sau rà soát").
- **Người chơi bị tạm khoá không được đếm** (bảng, trình sửa, điều kiện +50) tới khi mở khoá (tạm chọn).
- **Trần 600 coin thưởng xếp hạng mỗi 7 ngày coin cho mỗi người tạo**; vượt thì chờ, không mất (tạm chọn).
- **Cập nhật mỗi giờ, tính khi cần** (PO 4A + tạm chọn): tính lại khi lần tính cuối cũ hơn 60 phút, lúc mở bảng hay mở app
  (checkin). Thưởng trả trong cùng transaction với lần tính.
- **Công khai lần đầu +50** (PO 5A): một lần mỗi tài khoản, nhân vật công khai **liên tục** ≥ 24 giờ và có ≥ 1 người chơi. Về
  Riêng tư thì đếm lại từ đầu (tạm chọn). Không tính vào trần 600.
- **Sổ coin không thêm `kind`** (tạm chọn): ghi `kind = 'creator_milestone'` với `idem_key` `rank:<X>:<N>` / `first_public:<id>`,
  nhãn theo tiền tố `idem_key`. Migration `0014_hot_board.sql` chỉ thêm bảng.
- Bảng xếp hạng chỉ hiện trường công khai (tên, ảnh, @handle, số người chơi), như "Nhân vật được chia sẻ".

## Vì sao

- Bảng xếp hạng cho người chơi một chỗ tìm nhân vật đáng chơi, và cho người sáng tác một mục tiêu nhìn thấy được.
- "Bảng có nhân vật của ≥ N người tạo": Lyris chạy trên một máy với vài chục thành viên. Không có điều kiện này, nhân vật có 1
  người chơi đã ở top 10 và người tạo nhận 600 coin, nhiều hơn quà đăng nhập của 10 ngày. Đếm người tạo (không đếm nhân vật) để
  một người không tự lấp bảng bằng nhiều nhân vật của chính mình.
- Trần 600 coin/7 ngày: giữ đúng vai trò của trần mốc 10 cũ. Xoá rồi đăng lại, hay "Nhân bản" rồi công khai, là nhân vật mới đếm
  người chơi lại từ 0 với cùng nhóm bạn; mỗi lần có thể lấy lại tới 600 coin. 600 bằng đúng một nhân vật lên thẳng top 10, nên
  người tạo thật không bị chặn ở nhân vật đầu tiên. Chủ máy vẫn thấy mọi thưởng trong "Nhật ký".
- 24 giờ liên tục + ≥ 1 người chơi: chặn bật công khai rồi tắt ngay để lấy +50 (PO 5A).
- Không thêm `kind` cho sổ: `CHECK` của SQLite không sửa được nếu không dựng lại bảng; dựng lại sổ chỉ thêm (có trigger) trên DB
  thật của chủ dự án là việc rủi ro (bài học "app chạy `--reload`", [learned.md](../learned.md)).
- Tính khi cần thay vì việc nền theo giờ: app không có bộ hẹn giờ; tính lúc có người xem hay mở app là đủ để bảng không bao giờ
  cũ hơn 60 phút khi có người nhìn, và thưởng vẫn được trả.

## Khi build (2026-11-14, tạm chọn)

- **Lỗi khi trả thưởng không chặn bảng:** ghi bậc và trả thưởng nằm trong SAVEPOINT riêng bên trong lần tính bảng (sau rà soát:
  mỗi dòng một SAVEPOINT). Lỗi (lỗi DB, `IdemConflict`) chỉ cuộn lại dòng lỗi: bảng vẫn cập nhật, bậc vẫn được ghi, dòng lỗi trả ở
  lần tính sau. Lỗi khi tính bảng
  thì giữ bảng cũ. `GET /api/explore/hot` và checkin không bao giờ 500 vì việc này (`CoinService.refresh_hot`).
- **Lúc bật Công khai** (`card_public_since`) được ghi/xoá ngay trong `Repo.create_card`, `Repo.update_card` và
  `reports.unpublish_card` (cùng transaction), để không đường đổi Công khai nào bị sót. Không dùng trigger SQL: migration chỉ thêm.
- **Sự kiện `creator_rank_reached`** có `paid = true` khi bậc được trả ngay trong cùng lần tính; bậc chờ trả sau chỉ có
  `coins_granted {source: creator_rank}`.
- **Bot:** `environment/seed-creator-players.py` tính lại bảng ngay sau khi dựng người chơi (như lần tính mỗi giờ), vì app đã
  tính bảng lúc bot mở app.

## Sau rà soát đối kháng (2026-11-14, tạm chọn)

- **Đếm người tạo, không đếm nhân vật:** với "bảng có ≥ N nhân vật", một thành viên công khai 10 nhân vật, nhờ một bạn chơi mỗi
  nhân vật 3 câu ở 2 ngày, thì cả 10 nhân vật ở top 10 và mỗi nhân vật +300 (3.000 coin sau 5 tuần). Giờ bậc top N cần nhân vật
  của ≥ N người tạo khác nhau (`hot.ranked_creators`).
- **Người chơi bị tạm khoá không được đếm:** khoá tài khoản phụ là cách tự nhiên của chủ máy để chặn leo bảng; trước đây khoá rồi
  mà hạng và bậc không đổi.
- **Một dòng thưởng lỗi không chặn dòng khác:** ghi bậc, mỗi dòng trả bậc, mỗi dòng +50 có SAVEPOINT riêng. Bậc đạt lúc trả lỗi
  vẫn được ghi (`waiting`), nên không mất nếu nhân vật rớt hạng trước lần tính sau.
- **Đọc bảng còn mới không giữ khoá ghi:** `CoinService.refresh_hot` kiểm "đã cũ chưa" bằng một lần đọc trước khi mở transaction.
- **Trình sửa nói vì sao chưa có coin:** `creator.board_creators` và câu "Thưởng top {N} chỉ có khi bảng có nhân vật của ít nhất
  {N} người tạo khác nhau (hiện có {k})."; bậc tiếp theo chọn theo hạng hiện tại (hạng 7 trên bảng 60 người tạo: top 100, vì
  top 50 và top 10 đã nhận). `#/explore/hot` thêm câu "Thưởng top N chỉ có khi bảng có nhân vật của ít nhất N người tạo khác nhau."
- **Dải ở Khám phá luôn có** (trừ lúc đang tìm): là lối vào duy nhất của `#/explore/hot`; bảng rỗng thì một dòng "Chưa có nhân
  vật nào trên bảng xếp hạng.", chưa tải được thì chỉ tiêu đề và nút.
- **Tìm theo đầu từ:** mỗi từ gõ phải khớp phần đầu một từ ("ha" ra "Hạ", "Hải", không ra "thành", "nhà"); dấu câu tách từ.
- **Không đổi:** nhân vật bị xoá thì bậc đang chờ mất cùng nhân vật (đã ghi ở docs/coins.md §5.4). Tìm chỉ trong các nhân vật
  Khám phá đã tải (nhân vật được chia sẻ: 200 nhân vật mới sửa nhất, như lưới), đủ cho một máy vài chục thành viên.

## Đã cân nhắc

- Giữ cả thưởng mốc lẫn thưởng xếp hạng (1B): PO chọn thay hẳn.
- Hot theo người chơi trong 7 ngày (2A) hay tổng lượt trò chuyện (2B): PO chọn tổng người chơi từ trước tới nay.
- Chỉ nhận bậc cao nhất (3B): PO chọn cộng dồn.
- Một tab riêng trên thanh điều hướng (4B): PO chọn mục trong Khám phá.
- Trả +50 ngay khi bật công khai (5B): dễ lách bằng bật rồi tắt.
- Không có điều kiện "bảng có ≥ N": máy nhỏ thì công khai gần như chắc chắn được 600 coin.
- Đếm nhân vật (`ranked ≥ N`, bản đầu): một người tự lấp bảng được bằng nhiều nhân vật của mình.
- Mỗi bậc cần số người chơi tối thiểu (top 10 cần ≥ 10 người chơi): vẫn lách được bằng nhiều tài khoản chơi; khó giải thích hơn.
- Trần theo số lần (như mốc 10 cũ: 3 lần/7 ngày): bậc có giá khác nhau (100/200/300), trần theo coin dễ hiểu hơn.

## Nguồn

- [docs/coins.md §2.2, §5](../../docs/coins.md)
- [F44](../features/F44-thuong-sang-tac.md), [F46](../features/F46-bang-xep-hang-nhan-vat-hot.md), [hot-ranking](../screens/hot-ranking.md)
