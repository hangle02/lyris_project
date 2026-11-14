# App iOS/Android bằng Capacitor bọc frontend React hiện có

- **Ngày:** 2026-11-14 · **Ai quyết:** AI chọn (PO giao: "bạn xem cái nào tối ưu và mượt mà nhất thì chọn"); PO đổi được

## Bối cảnh

Lyris cần lên App Store và Google Play ([F55](../features/F55-app-ios-android.md)). Frontend hiện có là React 18 + Vite + TS,
ưu tiên điện thoại, đã có PWA, bot e2e, luật chữ và thiết kế theo `DESIGN.md`. Đội: PO + AI, chỉ có React/TS.

## Lựa chọn

**Capacitor** bọc chính `frontend/`, assets đóng gói trong app (không tải web từ xa), thêm plugin native: Keychain/Keystore
cho token, StoreKit 2, Play Billing, Sign in with Apple, push, haptics, chia sẻ, deep link. API qua `Bearer` token.

**Ngưỡng đổi** (đo mỗi bản phát hành trên **iPhone 11** và **Samsung Galaxy A15 bản 4 GB RAM, Android 14**, ghi số phiên
bản Android System WebView; trượt 2 bản liên tiếp sau khi tối ưu → mở lại quyết định):
mở nguội tới hub p75 ≤ 2,0 s · cuộn story 300 tin ≥ 95 % khung hình ≤ 16,7 ms · delta SSE tới lúc chữ hiện p95 ≤ 50 ms ·
gõ phím tới lúc chữ hiện p95 ≤ 50 ms · bộ nhớ ≤ 300 MB · phiên không crash ≥ 99,5 %.

**Đo bằng:** mốc `performance.mark` và Event Timing API gửi lên RUM (GlitchTip hoặc PostHog tự chạy) cho mở nguội, delta
SSE tới lúc vẽ, phím tới lúc vẽ; Xcode Instruments (Animation Hitches, Allocations) và Android `FrameMetrics` /
`dumpsys gfxinfo` / `dumpsys meminfo` cho khung hình và bộ nhớ; Xcode Organizer và Android vitals cho crash.

**Hướng đổi nếu trượt:** chuyển **cả app** sang React Native/Expo, dùng lại phần logic thuần `src/lib/*.ts`. Không ghép
một màn React Native vào trong app Capacitor: hai runtime, hai điều hướng, hai trạng thái đăng nhập, không đáng với đội
nhỏ (sửa sau phản biện, [docs/server.md §21](../../docs/server.md) điểm 22).

## Vì sao

- Một codebase cho web, iOS, Android; mọi tính năng đã qua bộ chấm chạy ngay trong app; bot e2e và `copyWords.test.ts` dùng lại.
- Lyris là app chữ: phần nặng nhất là hiện chữ chảy từ server (25–60 token/s), WebView làm tốt; `lib/sse.ts` dùng lại nguyên.
- Đội hiện tại làm được: bản TestFlight đầu ~2–3 tuần, so với ~2–3 tháng (React Native) và ~4–6 tháng (Swift + Kotlin).
- Rủi ro App Store 4.2 ("chỉ là website") giảm bằng đóng gói assets và các phần native thật (IAP, Sign in with Apple, push,
  haptics, Keychain, chia sẻ).

## Đã cân nhắc

- **React Native / Expo:** cảm giác native hơn, nhưng phải viết lại mọi màn hình và giữ web riêng; `fetch` stream cần thêm thư viện.
- **Swift + Kotlin native:** mượt nhất, nhưng ba codebase và cần thêm hai kỹ sư.
- **Chỉ PWA / TWA:** không có IAP trên iOS, khó được duyệt, push trên iOS hạn chế.

## Nguồn

- [raw/2026-11-14-server-lon-appstore-tra-loi.md](../raw/2026-11-14-server-lon-appstore-tra-loi.md)
- [docs/server.md §16](../../docs/server.md)
