# Chính sách quyền riêng tư của Lyris

Phiên bản: 2026-11-15

Lyris là ứng dụng nhập vai bằng chữ: bạn cùng các nhân vật AI viết nên những story. Trang này nói rõ Lyris lưu gì về bạn, dùng vào việc gì, giữ trong bao lâu và bạn kiểm soát nó thế nào. Chúng tôi viết đúng với những gì ứng dụng đang làm, không hơn.

"Chúng tôi" là đơn vị vận hành máy chủ Lyris mà bạn đang dùng. Liên hệ: **[ĐIỀN EMAIL LIÊN HỆ]** *(nhóm phát triển sẽ điền trước khi ra mắt)*.

## 1. Tóm tắt

- Story, nhân vật, persona và tin nhắn của bạn được lưu trong cơ sở dữ liệu trên máy chủ chạy Lyris. Tài khoản khác không đọc được story của bạn, kể cả quản trị viên trong ứng dụng.
- AI chạy ngay trên máy chủ đó. Lời bạn viết không được gửi cho công ty AI nào khác.
- Lyris ghi lại các thao tác sử dụng (ví dụ "đã bắt đầu một story") để cải thiện sản phẩm. Không bao giờ ghi chữ bạn viết. Bạn tắt được trong Tài khoản.
- Chúng tôi không bán dữ liệu, không chạy quảng cáo, không dùng story của bạn để huấn luyện AI.
- Bạn tải được toàn bộ dữ liệu của mình và xoá tài khoản bất cứ lúc nào.

## 2. Lyris lưu những gì

**Tài khoản.** @handle, tên hiển thị, phần giới thiệu, ảnh đại diện và ảnh bìa (nếu bạn tải lên), mật khẩu (chỉ lưu dạng băm scrypt, không ai đọc lại được), thời điểm tạo tài khoản, lần đăng nhập gần nhất, người đã mời bạn, và thời điểm bạn đồng ý Điều khoản và chính sách này.

**Nội dung bạn tạo.** Persona, nhân vật (kèm ảnh và sổ thế giới), story, mọi tin nhắn của bạn và của nhân vật (cả các bản viết lại), ghi chú và đánh giá bạn để lại, ký ức và tóm tắt mà AI rút ra từ story để nhớ mạch truyện, cài đặt của story.

**Bảo mật đăng nhập.** Mỗi phiên đăng nhập lưu tên thiết bị rút gọn (ví dụ "Safari · iPhone") và địa chỉ IP lúc đăng nhập. Các lần thử đăng nhập (đúng hay sai) lưu @handle đã gõ và IP để chặn đoán mật khẩu.

**Nhật ký máy chủ.** Mỗi lần đăng nhập (đúng hay sai), tạo tài khoản, đổi mật khẩu hay xoá tài khoản, máy chủ ghi một dòng nhật ký gồm @handle, địa chỉ IP và tên thiết bị rút gọn, để người vận hành điều tra khi có người đoán mật khẩu hay lạm dụng. Nhật ký này nằm ở máy chủ (không ở trong ứng dụng), chỉ người vận hành đọc được, và tự xoá sau tối đa 30 ngày.

**Báo cáo nội dung.** Khi bạn báo cáo một câu trả lời của AI: lý do, ghi chú (nếu bạn viết), và **chỉ khi bạn bật "Gửi kèm câu trả lời này"** thì mới lưu một bản chụp của câu trả lời đó để người quản lý xem xét. Khi bạn báo cáo một nhân vật công khai: lý do, ghi chú và nhân vật bị báo cáo. Người quản lý không thấy bạn là ai, không mở được story của bạn, và số liệu sử dụng của lần báo cáo không gắn với tài khoản hay trình duyệt của bạn.

**Dữ liệu sử dụng.** Xem mục 4.

## 3. Ai thấy được gì

- **Story, persona, ký ức, tin nhắn:** chỉ bạn. Trong ứng dụng, quản trị viên không mở được story của người khác.
- **Nhân vật:** mặc định chỉ bạn thấy. Nếu bạn bật "Công khai", người dùng khác đã đăng nhập thấy phần hồ sơ công khai (tên, ảnh, vai trò, mô tả, ngoại hình, lời mở đầu, thẻ...) và có thể bắt đầu story riêng của họ với một bản sao của nhân vật. Tính cách, hoàn cảnh, bí mật, sổ thế giới và ghi chú người tạo không hiện cho họ.
- **Hồ sơ:** @handle, tên hiển thị, ảnh, phần giới thiệu và các nhân vật công khai của bạn hiện cho người dùng khác.
- **Giới hạn thật của "riêng tư":** dữ liệu nằm trong một tệp cơ sở dữ liệu trên máy chủ. Người có quyền truy cập trực tiếp máy chủ đó về mặt kỹ thuật có thể mở tệp này. Chúng tôi không đọc nội dung của bạn, trừ khi bạn tự gửi kèm trong một báo cáo.

## 4. Dữ liệu sử dụng (số liệu ẩn danh)

Để biết Lyris có hữu ích không và sửa chỗ chưa tốt, Lyris ghi lại các sự kiện như: mở ứng dụng, xem trang Khám phá, bắt đầu story, gửi tin nhắn, AI trả lời xong hay bị lỗi, tạo nhân vật, quay lại story cũ. Danh sách đầy đủ nằm trong kế hoạch theo dõi (tracking plan) của dự án.

- **Không bao giờ có chữ.** Không ghi nội dung tin nhắn, tên nhân vật, persona, tên story, @handle, email hay bất kỳ chữ nào bạn gõ. Mỗi sự kiện chỉ có các giá trị cố định: loại thao tác, chế độ (story hay nhắn tin), con số đã làm tròn theo khoảng (ví dụ độ dài tin nhắn "21-80 ký tự"), thời gian AI trả lời.
- **Định danh:** một mã ngẫu nhiên của tài khoản (khi đã đăng nhập) và một mã ngẫu nhiên của trình duyệt (cookie `lyris_anon`). Mã trình duyệt được lưu kèm mọi sự kiện từ trình duyệt đó, kể cả khi đã đăng nhập, để biết các lần ghé thăm của cùng một thiết bị và nối các thao tác trước khi đăng nhập với tài khoản. Vì vậy nếu nhiều tài khoản dùng chung một trình duyệt, số liệu cho thấy chúng dùng chung thiết bị. Không phải tên hay email.
- **Lưu ở đâu:** trong cơ sở dữ liệu của Lyris, tối đa 180 ngày rồi tự xoá.
- **PostHog:** chỉ khi đơn vị vận hành bật kết nối (có khoá PostHog), các sự kiện này được gửi tiếp sang PostHog, một dịch vụ phân tích sản phẩm (máy chủ mặc định ở Hoa Kỳ), để xem biểu đồ. Khi gửi, địa chỉ IP không được gửi kèm và tính năng đoán vị trí theo IP bị tắt. Không bật thì không có gì rời khỏi máy chủ Lyris. Sự kiện của tài khoản chưa đồng ý bản chính sách này chỉ lưu ở máy chủ Lyris, không được gửi sang PostHog.
- **Tắt:** vào Tài khoản và tắt "Chia sẻ dữ liệu sử dụng ẩn danh". Khi tắt, Lyris ngừng ghi sự kiện của bạn và xoá các sự kiện đã lưu của tài khoản, kể cả các thao tác trước khi đăng nhập trên trình duyệt của bạn (sự kiện chưa gửi thì không gửi nữa). Trình duyệt đang dùng được đổi mã và đánh dấu "không chia sẻ" (cookie `lyris_noshare`), nên sau khi bạn đăng xuất, Lyris cũng không ghi gì từ trình duyệt đó. Lyris chỉ giữ một dòng đếm "có người đã tắt", không gắn với ai. Trình duyệt gửi tín hiệu Global Privacy Control (`Sec-GPC: 1`) cũng được coi là đã tắt và không nhận cookie `lyris_anon`.

## 5. Cookie và bộ nhớ trình duyệt

Lyris chỉ dùng cookie của chính mình, không có cookie quảng cáo hay của bên thứ ba:

| Tên | Để làm gì | Thời hạn |
|---|---|---|
| `lyris_session` | Giữ bạn đăng nhập | 30 ngày kể từ lần dùng gần nhất, tối đa 180 ngày |
| `lyris_device` | Nhận ra trình duyệt bạn đã đăng nhập thành công, để không bị khoá nhầm khi có người đoán mật khẩu | 1 năm |
| `lyris_anon` | Mã ngẫu nhiên của trình duyệt cho dữ liệu sử dụng (mục 4). Không đặt khi trình duyệt gửi Global Privacy Control hoặc đã tắt chia sẻ; bị xoá khi bạn tắt chia sẻ hay xoá tài khoản | 1 năm |
| `lyris_noshare` | Ghi nhớ trình duyệt này đã tắt chia sẻ dữ liệu sử dụng (mục 4), để không ghi gì cả khi đã đăng xuất. Bị gỡ khi bạn bật lại | 1 năm |

Ứng dụng cũng lưu vài thứ trong bộ nhớ của trình duyệt (localStorage), chỉ trên thiết bị của bạn: giao diện sáng/tối, bản nháp tin nhắn chưa gửi, story mở gần nhất, lựa chọn hiện suy nghĩ của nhân vật, mã số tài khoản đang đăng nhập.

## 6. Giữ trong bao lâu

- Nội dung và tài khoản: tới khi bạn xoá chúng hoặc xoá tài khoản.
- Dữ liệu sử dụng: 180 ngày.
- Lần thử đăng nhập: 30 ngày. Phiên đăng nhập: tới khi hết hạn hoặc bạn đăng xuất.
- Nhật ký máy chủ (mục 2): tối đa 30 ngày.
- Nếu đơn vị vận hành có sao lưu máy chủ, dữ liệu đã xoá có thể còn trong bản sao lưu cũ cho tới khi bản đó bị thay thế.

## 7. Quyền của bạn

- **Tải dữ liệu:** trong Tài khoản, tải một tệp JSON chứa hồ sơ, persona, nhân vật (kèm sổ thế giới), story kèm toàn bộ tin nhắn và ký ức, báo cáo bạn đã gửi, thiết bị đăng nhập và dữ liệu sử dụng của bạn. Ảnh được ghi bằng tên tệp.
- **Sửa:** đổi tên, @handle, phần giới thiệu, ảnh bất cứ lúc nào; sửa hoặc xoá từng story, nhân vật, persona, tin nhắn.
- **Xoá tài khoản:** trong Tài khoản (cần nhập mật khẩu). Việc xoá diễn ra ngay và không hoàn tác được: mọi story, tin nhắn, ký ức, persona, nhân vật (kể cả nhân vật công khai), ảnh, phiên đăng nhập và lần thử đăng nhập của bạn bị xoá. Những gì còn lại, không gắn với bạn nữa: dữ liệu sử dụng đã ẩn danh (bỏ liên kết với tài khoản, đổi mã trình duyệt và mã lượt dùng sang mã ngẫu nhiên mới, và xoá cookie `lyris_anon` của trình duyệt đang dùng), lý do của các báo cáo bạn đã gửi (ghi chú và bản chụp bị xoá), và bản sao nhân vật công khai của bạn mà người khác đã dùng để bắt đầu story (nằm trong story của họ, không còn ghi tên bạn). Sự kiện đã gửi sang PostHog trước đó: hãy liên hệ chúng tôi để yêu cầu xoá. Dòng nhật ký máy chủ (mục 2) không bị xoá ngay mà tự hết hạn sau tối đa 30 ngày.
- **Tắt dữ liệu sử dụng:** xem mục 4.
- Mọi yêu cầu khác: liên hệ **[ĐIỀN EMAIL LIÊN HỆ]**.

## 8. Trẻ em

Lyris không đặt độ tuổi tối thiểu, nhưng nội dung tình dục bị cấm trên Lyris và mọi nội dung tình dục liên quan tới trẻ vị thành niên bị cấm tuyệt đối. Nếu bạn dưới 16 tuổi, hãy dùng Lyris khi đã được cha mẹ hoặc người giám hộ cho phép. Lyris không cố ý thu thập gì về trẻ em ngoài những gì mô tả ở trên. Cha mẹ hoặc người giám hộ có thể liên hệ chúng tôi để xoá tài khoản của con.

## 9. Bảo mật

Mật khẩu được băm bằng scrypt; phiên đăng nhập chỉ lưu dạng băm của mã phiên; cookie đăng nhập không đọc được từ JavaScript; đăng nhập sai nhiều lần bị chặn tạm thời. Không hệ thống nào an toàn tuyệt đối: hãy dùng mật khẩu riêng cho Lyris.

## 10. Thay đổi chính sách

Khi chính sách này thay đổi đáng kể, chúng tôi đổi số phiên bản ở đầu trang và Lyris sẽ hỏi bạn đồng ý lại một lần.

---

## English

Version: 2026-11-15

Lyris is a text roleplay app: you write stories together with AI characters. This page explains what Lyris stores about you, why, for how long, and how you control it. It describes what the app actually does.

"We" means the operator of the Lyris server you are using. Contact: **[ĐIỀN EMAIL LIÊN HỆ]** *(contact email, to be filled in by the team before launch)*.

### 1. Summary

- Your stories, characters, personas and messages are stored in the database on the server that runs Lyris. Other accounts cannot read your stories, and neither can the in-app administrator.
- The AI runs on that same server. What you write is not sent to any other AI company.
- Lyris records usage actions (for example "started a story") to improve the product. It never records the text you write. You can turn this off in Account.
- We do not sell data, do not show ads, and do not use your stories to train AI.
- You can download all of your data and delete your account at any time.

### 2. What Lyris stores

**Account.** Handle, display name, bio, avatar and banner (if you upload them), password (stored only as a scrypt hash), when the account was created, last sign-in, who invited you, and when you accepted the Terms and this policy.

**Your content.** Personas, characters (with images and world lore), stories, every message from you and from the character (including rewrites), your ratings and notes, the memories and summaries the AI extracts so it can follow the story, and story settings.

**Sign-in security.** Each session stores a short device label (for example "Safari · iPhone") and the IP address at sign-in. Sign-in attempts (successful or not) store the handle typed and the IP, to stop password guessing.

**Server logs.** Each sign-in (successful or not), account creation, password change or account deletion writes one server log line with the handle, IP address and short device label, so the operator can investigate password guessing or abuse. This log lives on the server (not in the app), only the operator can read it, and it is deleted automatically after at most 30 days.

**Content reports.** When you report an AI reply: the reason, your note (if any), and **only if you turn on "Send this reply with the report"** a copy of that reply for the administrator to review. When you report a public character: the reason, your note and the character reported. The administrator does not see who you are and cannot open your story, and the usage event of a report is not linked to your account or browser.

**Usage data.** See section 4.

### 3. Who can see what

- **Stories, personas, memories, messages:** only you. In the app, the administrator cannot open other people's stories.
- **Characters:** private by default. If you make one public, other signed-in users see its public profile (name, image, role, description, appearance, greeting, tags...) and can start their own story with a copy of it. Personality, background, secrets, world lore and creator notes are not shown to them.
- **Profile:** your handle, display name, images, bio and public characters are visible to other users.
- **The real limit of "private":** data lives in a database file on the server. Someone with direct access to that server can technically open the file. We do not read your content, except what you choose to attach to a report.

### 4. Usage data (anonymous statistics)

To learn whether Lyris is useful and what to fix, Lyris records events such as: app opened, Explore viewed, story started, message sent, AI reply finished or failed, character created, old story resumed. The full list is in the project's tracking plan.

- **Never any text.** No message content, character or persona names, story titles, handles, emails or anything you type. Each event only carries fixed values: the kind of action, the mode (story or texting), numbers rounded into ranges (for example message length "21-80 characters"), and AI response times.
- **Identifier:** a random ID of your account (when signed in) and a random ID of your browser (cookie `lyris_anon`). The browser ID is stored with every event from that browser, signed in or not, to tell visits of the same device apart and to link actions before sign-in to the account. So if several accounts share one browser, the data shows that they share a device. Never your name or email.
- **Where:** in the Lyris database, for at most 180 days, then deleted automatically.
- **PostHog:** only if the operator enables it (with a PostHog key) are these events also sent to PostHog, a product analytics service (default servers in the United States), for charts. Your IP address is not sent and IP-based location is disabled. If it is not enabled, nothing leaves the Lyris server. Events of an account that has not accepted this version of the policy stay on the Lyris server and are not sent to PostHog.
- **Turning it off:** in Account, turn off "Chia sẻ dữ liệu sử dụng ẩn danh" (share anonymous usage data). Lyris then stops recording your events and deletes the events already stored for your account, including actions before sign-in on your browser (unsent events are never sent). The current browser gets a new ID and is marked "not sharing" (cookie `lyris_noshare`), so after you sign out Lyris records nothing from that browser either. Lyris keeps only one counter row saying "someone turned this off", not linked to anyone. A browser sending the Global Privacy Control signal (`Sec-GPC: 1`) is treated the same way and never gets the `lyris_anon` cookie.

### 5. Cookies and browser storage

Lyris uses only its own cookies; no advertising or third-party cookies:

| Name | Purpose | Lifetime |
|---|---|---|
| `lyris_session` | Keeps you signed in | 30 days from last use, at most 180 days |
| `lyris_device` | Recognises a browser that signed in successfully, so you are not locked out when someone else guesses your password | 1 year |
| `lyris_anon` | Random browser ID for usage data (section 4). Not set for browsers sending Global Privacy Control or that turned sharing off; cleared when you turn sharing off or delete your account | 1 year |
| `lyris_noshare` | Remembers that this browser turned usage sharing off (section 4), so nothing is recorded after you sign out. Removed when you turn it back on | 1 year |

The app also keeps a few things in your browser's local storage, only on your device: light/dark theme, unsent message drafts, the last story you opened, whether character thoughts are shown, and the ID of the signed-in account.

### 6. How long we keep data

- Content and account: until you delete them or delete your account.
- Usage data: 180 days.
- Sign-in attempts: 30 days. Sessions: until they expire or you sign out.
- Server logs (section 2): at most 30 days.
- If the operator keeps server backups, deleted data may remain in an old backup until that backup is replaced.

### 7. Your rights

- **Download your data:** in Account, download a JSON file with your profile, personas, characters (with world lore), stories with every message and memory, reports you sent, sign-in devices and your usage data. Images are listed by file name.
- **Correct:** change your name, handle, bio and images at any time; edit or delete any story, character, persona or message.
- **Delete your account:** in Account (your password is required). Deletion is immediate and cannot be undone: all your stories, messages, memories, personas, characters (including public ones), images, sessions and sign-in attempts are deleted. What remains, no longer linked to you: anonymised usage data (unlinked from the account, with the browser ID and session IDs replaced by new random ones, and the `lyris_anon` cookie of the current browser cleared), the reasons of reports you sent (notes and reply copies are deleted), and copies of your public characters that other people already used to start their own stories (they stay in those stories, without your name). For events already sent to PostHog, contact us to request deletion. Server log lines (section 2) are not deleted at once; they expire after at most 30 days.
- **Turn off usage data:** see section 4.
- Any other request: contact **[ĐIỀN EMAIL LIÊN HỆ]**.

### 8. Children

Lyris sets no minimum age, but sexual content is prohibited on Lyris and any sexual content involving minors is absolutely prohibited. If you are under 16, use Lyris only with permission from a parent or guardian. Lyris does not knowingly collect anything about children beyond what is described above. A parent or guardian can contact us to delete their child's account.

### 9. Security

Passwords are hashed with scrypt; sessions store only a hash of the session token; the sign-in cookie cannot be read by JavaScript; repeated failed sign-ins are temporarily blocked. No system is perfectly secure: use a password that is unique to Lyris.

### 10. Changes

When this policy changes materially, we update the version at the top and Lyris asks you to accept it again once.
