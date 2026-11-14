// F45 (docs/coins.md §6, wiki/screens/missions.md): the sample-ad dialog walks counting → claimable → claimed, the
// "Nhận 5 coin" button stays locked while seconds are left, closing before the claim cancels the view on the server,
// and every mission row shows "x/y" with "Nhận" when claimable and "Đã nhận" when claimed.
import { test } from "node:test";
import assert from "node:assert/strict";
import { COIN_COPY, allCoinStrings } from "../../lib/coinCopy.ts";
import {
  AD_START,
  adErrorText,
  adReducer,
  claimLocked,
  closeAction,
  countdownLive,
  earnedText,
  missionRow,
  noteMissionsFrom,
  secondsLeft,
  takeMissionsFrom,
} from "./missionsLogic.ts";
import type { AdState, Mission, MissionRow, MissionsOut } from "./missionsLogic.ts";

const T0 = 1_000_000;

const mission = (over: Partial<Mission> & Pick<Mission, "id">): Mission => {
  const [target, reward] = ({ ad: [3, 5], characters: [3, 10], turns: [20, 5] } as const)[over.id];
  return { progress: 0, target, reward, claimed: false, claimable: false, remaining: target, ...over };
};

const out = (earned: number, missions: Mission[]): MissionsOut => ({
  coin_day: "2026-11-14",
  earned_today: earned,
  cap: 30,
  missions,
  unlimited: false,
  enabled: true,
});

test("ad dialog: counting → claimable → claiming → claimed, in that order", () => {
  let s: AdState = AD_START;
  assert.equal(s.phase, "starting");
  s = adReducer(s, { type: "started", adId: 7, seconds: 15, now: T0 });
  assert.equal(s.phase, "counting");
  assert.equal(secondsLeft(s, T0), 15);
  assert.equal(secondsLeft(s, T0 + 4_200), 11); // rounds up: never says 0 while time is left
  s = adReducer(s, { type: "tick", now: T0 + 14_999 });
  assert.equal(s.phase, "counting");
  assert.equal(secondsLeft(s, T0 + 14_999), 1);
  s = adReducer(s, { type: "tick", now: T0 + 15_000 });
  assert.equal(s.phase, "ready");
  s = adReducer(s, { type: "claim" });
  assert.equal(s.phase, "claiming");
  s = adReducer(s, { type: "claimed", amount: 5 });
  assert.equal(s.phase, "claimed");
  assert.equal(s.phase === "claimed" && s.amount, 5);
  // A late tick never moves a claimed dialog back.
  assert.equal(adReducer(s, { type: "tick", now: T0 + 99_000 }).phase, "claimed");
  // Out-of-order events are ignored: no claim before the countdown is over.
  const counting = adReducer(AD_START, { type: "started", adId: 8, seconds: 15, now: T0 });
  assert.equal(adReducer(counting, { type: "claim" }), counting);
  assert.equal(adReducer(AD_START, { type: "claimed", amount: 5 }), AD_START);
});

test("'Nhận 5 coin' is locked while more than 0 seconds are left", () => {
  const s = adReducer(AD_START, { type: "started", adId: 1, seconds: 15, now: T0 });
  assert.equal(claimLocked(AD_START, T0), true);
  for (const ms of [0, 1, 5_000, 14_000, 14_999]) assert.equal(claimLocked(s, T0 + ms), true, `${ms}ms`);
  assert.equal(claimLocked(s, T0 + 15_000), false);
  const ready = adReducer(s, { type: "tick", now: T0 + 15_000 });
  assert.equal(claimLocked(ready, T0 + 15_000), false);
  assert.equal(claimLocked(adReducer(ready, { type: "claim" }), T0 + 15_000), true); // sending
  assert.equal(claimLocked(adReducer(adReducer(ready, { type: "claim" }), { type: "claimed", amount: 5 }), T0), true);
  // The server clock said "not yet" (the device clock runs fast): count a few more seconds, locked again.
  const again = adReducer(adReducer(ready, { type: "claim" }), { type: "notFinished", now: T0 + 15_000 });
  assert.equal(again.phase, "counting");
  assert.equal(claimLocked(again, T0 + 15_000), true);
  assert.ok(secondsLeft(again, T0 + 15_000) > 0);
  assert.equal(again.phase === "counting" && again.note, COIN_COPY.adNotFinished);
});

test("closing before the claim cancels the view; after the claim it only closes", () => {
  const counting = adReducer(AD_START, { type: "started", adId: 42, seconds: 15, now: T0 });
  assert.deepEqual(closeAction(counting), { kind: "cancel", adId: 42 });
  const ready = adReducer(counting, { type: "tick", now: T0 + 16_000 });
  assert.deepEqual(closeAction(ready), { kind: "cancel", adId: 42 });
  assert.deepEqual(closeAction(adReducer(ready, { type: "claim" })), { kind: "cancel", adId: 42 });
  const claimed = adReducer(adReducer(ready, { type: "claim" }), { type: "claimed", amount: 5 });
  assert.deepEqual(closeAction(claimed), { kind: "close" });
  assert.deepEqual(closeAction(AD_START), { kind: "close" }); // nothing started yet
  const expired = adReducer(ready, { type: "expired" });
  assert.equal(expired.phase, "expired");
  assert.deepEqual(closeAction(expired), { kind: "close" });
});

test("server refusals become the screen's sentences", () => {
  assert.equal(adErrorText("ad_not_finished", "x"), "Quảng cáo chưa xem xong.");
  assert.equal(adErrorText("ad_expired", "x"), "Lượt xem này đã hết hạn. Hãy xem lại.");
  assert.equal(adErrorText("ad_limit", "x"), "Hôm nay bạn đã xem đủ 3 quảng cáo.");
  assert.equal(adErrorText("mission_cap", "x"), "Đã nhận đủ 30 coin hôm nay. Quay lại sau 0:00 nhé.");
  assert.equal(adErrorText(null, "Mạng chập chờn."), "Mạng chập chờn.");
});

test("countdown: shown every second, read aloud every 5 seconds", () => {
  assert.equal(COIN_COPY.adLeft(15), "Còn 15 giây");
  assert.equal(countdownLive(15), "Còn 15 giây");
  assert.equal(countdownLive(14), null);
  assert.equal(countdownLive(10), "Còn 10 giây");
  assert.equal(countdownLive(0), null);
});

test("mission rows: 'x/y', 'Nhận' when claimable, 'Đã nhận' when claimed, nothing before", () => {
  const data = out(0, [mission({ id: "ad" }), mission({ id: "characters", progress: 2 }), mission({ id: "turns", progress: 7 })]);
  const rows = data.missions.map((m) => missionRow(m, data));
  assert.equal(rows.length, 3);
  const [ad, chars, turns] = rows as [MissionRow, MissionRow, MissionRow];
  assert.equal(ad.title, "Xem quảng cáo");
  assert.equal(ad.progress, "0/3");
  assert.equal(ad.reward, "+5 coin mỗi lần");
  assert.deepEqual(ad.action, { kind: "watch", label: "Xem", disabled: false });
  assert.equal(chars.title, "Trò chuyện với 3 nhân vật khác nhau");
  assert.equal(chars.progress, "2/3");
  assert.equal(chars.reward, "+10 coin");
  assert.equal(chars.action, null);
  assert.equal(turns.title, "Gửi 20 lượt");
  assert.equal(turns.progress, "7/20");
  assert.equal(turns.note, "Không tính 'Tạo lại câu trả lời'.");

  const claimable = missionRow(mission({ id: "characters", progress: 3, remaining: 0, claimable: true }), data);
  assert.deepEqual(claimable.action, { kind: "claim", label: "Nhận", disabled: false });
  const claimed = missionRow(mission({ id: "turns", progress: 20, remaining: 0, claimed: true }), data);
  assert.deepEqual(claimed.action, { kind: "done", label: "Đã nhận" });
  const oneAd = missionRow(mission({ id: "ad", progress: 1, remaining: 2 }), data);
  assert.equal(oneAd.progress, "1/3");
  const allAds = missionRow(mission({ id: "ad", progress: 3, remaining: 0, claimed: true }), data);
  assert.deepEqual(allAds.action, { kind: "done", label: "Đã xem đủ" });
  // 30 coins today: every "Xem" is locked.
  const fullAd = mission({ id: "ad", progress: 1, remaining: 2 });
  const full = out(30, [fullAd]);
  assert.deepEqual(missionRow(fullAd, full).action, { kind: "watch", label: "Xem", disabled: true });
});

test("the summary line and where the screen was opened from", () => {
  assert.equal(earnedText(out(5, [])), "Đã nhận 5/30 coin hôm nay");
  assert.equal(earnedText(out(30, [])), "Đã nhận đủ 30 coin hôm nay. Quay lại sau 0:00 nhé.");
  assert.equal(takeMissionsFrom(), "link");
  noteMissionsFrom("composer");
  assert.equal(takeMissionsFrom(), "composer");
  assert.equal(takeMissionsFrom(), "link");
  noteMissionsFrom("wallet");
  assert.equal(takeMissionsFrom(), "wallet");
});

test("the mission and ad words are in coinCopy (checked for technical words there)", () => {
  const all = allCoinStrings().join("\n");
  for (const words of [
    "Nhiệm vụ hôm nay",
    "Làm mới lúc 0:00",
    "Quảng cáo mẫu",
    "Đây là quảng cáo mẫu của Lyris, chưa phải quảng cáo thật.",
    "Nhận 5 coin",
    "Tài khoản quản lý không tốn coin nên không có nhiệm vụ.",
  ]) {
    assert.ok(all.includes(words), words);
  }
});
