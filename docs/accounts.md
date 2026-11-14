# Account, profile và persona (Phase 2c)

> Cập nhật 2026-11-14: đăng nhập, mật khẩu, nhiều tài khoản trên một máy và nhân vật công khai giữa các tài khoản được làm ở **Phase 4b** (`docs/auth.md`), không phải Phase 7. Những chỗ dưới đây nói "Phase 7 thay `current_account`" hay liệt kê đăng nhập trong "Không làm" là thiết kế cũ; `auth.md` thay thế chúng.

Quyết định của người dùng (2026-11-13):
- Tách rõ **account** và **persona**. Một account có nhiều persona. Persona chỉ dùng khi trò chuyện trong story. Account dùng cho mọi tương tác bên ngoài story: tạo nhân vật, tạo story, và sau này bình luận, đăng ảnh, chia sẻ. Profile của account khác profile của persona.
- Hướng tới **cộng đồng** (chia sẻ với người khác như WHIF, cần một máy chủ chung ngoài máy Mac). Bây giờ chỉ làm **account + profile**; bình luận, đăng ảnh, chia sẻ là một phase riêng (Phase 7 trong `plan.md`), có thiết kế riêng trước khi làm.

## 1. Khái niệm

| | Account | Persona |
|---|---|---|
| Là ai | Bạn, người dùng Lyris | Nhân vật bạn đóng trong một story |
| Số lượng | Một account mỗi người | Nhiều persona mỗi account |
| Dùng ở đâu | Header, trang profile, tác giả của nhân vật (Studio, Khám phá, file export), sau này: bình luận, bài đăng, theo dõi | Trong story: prompt, lời của người chơi, đại từ dẫn truyện |
| Thông tin | tên hiển thị, @handle, avatar, ảnh bìa, giới thiệu | tên, giới tính, mô tả, avatar |
| Ai thấy (sau này) | Công khai trên cộng đồng (trừ phần riêng tư) | Chỉ chủ account |

**Story và chat luôn riêng tư, chỉ nằm trên máy của bạn.** Kể cả khi có cộng đồng, không có gì trong story được gửi đi nếu bạn không chủ động chia sẻ một đoạn.

## 2. Chuẩn bị cho cộng đồng ngay từ bây giờ

Để sau này nối với máy chủ chung mà không phải làm lại dữ liệu:
- Mọi bản ghi có thể đồng bộ (account, persona, card, story) có thêm `uid`: chuỗi 32 ký tự hex ngẫu nhiên, không đổi, duy nhất toàn cầu. `id` số nguyên vẫn là khoá chính cục bộ.
- Persona, card, story có `account_id` (chủ sở hữu). Mọi endpoint danh sách và đọc/sửa/xoá đều **lọc theo account hiện tại**: bây giờ luôn là account chủ máy, sau này là account đã đăng nhập. Card của account khác (khi có cộng đồng) chỉ đọc.
- Card có `visibility`: `private` (mặc định), `unlisted`, `public`. Bây giờ chỉ lưu và hiện nhãn "Riêng tư"; nút chia sẻ để Phase 7.
- Backend có một dependency duy nhất `current_account(request)` trả account đang dùng. Hiện không có đăng nhập: luôn là account chủ máy (account đầu tiên). Phase 7 thay phần bên trong dependency này bằng xác thực thật; route không phải đổi.
- `@handle`: 3-30 ký tự `a-z 0-9 _ .`, không bắt đầu hay kết thúc bằng dấu chấm, không phân biệt hoa thường, duy nhất. Bây giờ chỉ duy nhất trên máy; khi lên cộng đồng sẽ phải kiểm tra lại với máy chủ (có thể phải đổi nếu trùng).
- Card export (Character Card V2): `creator` = `@handle` của account tạo card; `extensions.lyris.creator_uid` = `uid` của account.

## 3. Dữ liệu (migration `0005_accounts.sql`)

```sql
CREATE TABLE accounts (
  id INTEGER PRIMARY KEY,
  uid TEXT NOT NULL UNIQUE,
  handle TEXT NOT NULL UNIQUE COLLATE NOCASE,
  display_name TEXT NOT NULL,
  bio TEXT NOT NULL DEFAULT '',
  avatar TEXT,                 -- file trong avatars_dir
  banner TEXT,                 -- file trong avatars_dir
  profile_completed INTEGER NOT NULL DEFAULT 0,  -- 0 cho tới khi người dùng tự đặt tên/handle
  created_at, updated_at
);
ALTER TABLE personas ADD COLUMN account_id INTEGER REFERENCES accounts(id);
ALTER TABLE personas ADD COLUMN uid TEXT;
ALTER TABLE personas ADD COLUMN avatar TEXT;
ALTER TABLE character_cards ADD COLUMN account_id INTEGER REFERENCES accounts(id);
ALTER TABLE character_cards ADD COLUMN uid TEXT;
ALTER TABLE character_cards ADD COLUMN visibility TEXT NOT NULL DEFAULT 'private'
  CHECK (visibility IN ('private','unlisted','public'));
ALTER TABLE stories ADD COLUMN account_id INTEGER REFERENCES accounts(id);
ALTER TABLE stories ADD COLUMN uid TEXT;
-- Tạo account chủ máy (handle 'ban', tên 'Bạn', profile_completed 0), gán mọi bản ghi cũ cho nó,
-- điền uid = lower(hex(randomblob(16))) cho mọi bản ghi cũ; index unique trên các cột uid.
```
Account mặc định không lấy tên tài khoản WHIF hay thông tin cá nhân nào; người dùng tự đặt ở lần mở đầu tiên.

## 4. API

| Method | Path | Ghi chú |
|---|---|---|
| GET | /api/account | account hiện tại + số liệu: `card_count`, `story_count`, `persona_count` |
| PUT | /api/account | `{display_name, handle, bio}`; handle sai luật hoặc trùng → 422 tiếng Việt; lưu thì `profile_completed = 1` |
| PUT/DELETE | /api/account/avatar, /api/account/banner | ảnh raw như avatar card; banner tối đa 1500x500, giữ tỉ lệ |
| GET | /api/account/avatar, /api/account/banner | file, cache theo tên file |
| GET | /api/accounts/{handle} | profile công khai (bây giờ chỉ có account chủ máy): tên, handle, avatar, banner, bio, nhân vật `visibility != private` (bây giờ thường rỗng) |
| PUT/DELETE/GET | /api/personas/{id}/avatar | avatar persona |
| (đổi) | mọi endpoint persona/card/story | lọc theo account hiện tại; tạo mới gán `account_id`, `uid` |
| (đổi) | GET /api/cards, /api/cards/{id}, StoryOut | thêm `creator_handle`, `creator_name`, `visibility`, `uid` |

## 5. Giao diện (theo DESIGN.md, design-impl §10)

- **Header hub, góc phải:** avatar **account** (không còn là persona); chấm đỏ nhỏ khi mất kết nối Ollama giữ nguyên.
- **Bấm avatar → sheet "Tài khoản"**, ba khối:
  1. Account: avatar, tên hiển thị, @handle, nút "Xem profile".
  2. Persona: persona mặc định cho story mới (đổi nhanh), "Quản lý persona".
  3. Máy MacBook M2: như modal hiện tại (kết nối, RAM, pin, model mặc định, KV cache, nguồn ảnh).
- **Trang profile `#/me`** (route `#/u/<handle>` cũng parse được cho sau này):
  - ảnh bìa (ảnh đã tải lên, hoặc mảng màu phẳng `surface-2`, không gradient), avatar lớn chồng lên mép ảnh bìa, tên hiển thị, @handle, giới thiệu, số nhân vật / story / persona (số thật);
  - nút "Sửa profile" (sheet: avatar, ảnh bìa, tên, handle có kiểm tra ngay, giới thiệu);
  - tab "Nhân vật" (lưới như Khám phá, nhân vật do account tạo, nhãn "Riêng tư"), tab "Persona" (chỉ chủ account thấy; thẻ persona có avatar, mô tả, số story; sửa/thêm/xoá ngay tại đây hoặc mở `#/personas`).
  - Không có tab bài đăng hay bình luận (Phase 7).
- **Lần đầu mở sau khi cập nhật** (`profile_completed = 0`): ở đầu hub có một khối mời "Đặt tên cho tài khoản của bạn" với nút mở sheet sửa profile; ẩn khi đã lưu. Không chặn việc dùng app.
- **Persona có avatar.** Hiện ở chọn persona khi tạo story, sheet Tài khoản, trang persona, và cạnh bong bóng của người chơi trong DM.
- **Tác giả nhân vật:** thẻ ở Khám phá và Studio ghi "bởi @handle" cho nhân vật của account; nhân vật mẫu ghi "Mẫu của Lyris".
- Thuật ngữ: "account" hiển thị là **"tài khoản"**, "persona" giữ nguyên "persona", "story" giữ nguyên "story".

## 6. Không làm ở phase này

Đăng nhập, mật khẩu, nhiều account trên một máy, đồng bộ, bình luận, đăng ảnh, theo dõi, thích, báo cáo vi phạm, chia sẻ card ra ngoài. Tất cả thuộc Phase 7 (Cộng đồng), cần: máy chủ chung (hosting, chi phí), xác thực thật, chính sách nội dung (nội dung người lớn, kiểm duyệt, bản quyền nhân vật), quyền riêng tư (chat không bao giờ tự rời máy).
