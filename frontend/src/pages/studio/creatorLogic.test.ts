// F44 làm lại (docs/coins.md §5.7, wiki/screens/card-editor.md): the players and ranking lines under the
// "Công khai" switch of the Studio editor.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { creatorBlock } from "./creatorLogic.ts";
import type { CreatorProgress } from "./creatorLogic.ts";
import { COIN_COPY, allCoinStrings } from "../../lib/coinCopy.ts";

const p = (over: Partial<CreatorProgress>): CreatorProgress => ({
  players: 12,
  rank: 7,
  next_tier: 50,
  next_reward: 200,
  waiting_coins: 0,
  board_creators: 100,
  ...over,
});

test("players and rank on 'Nhân vật hot', or not on the board yet", () => {
  assert.equal(creatorBlock(p({}))?.head, "12 người chơi · Hạng 7 Nhân vật hot");
  assert.equal(creatorBlock(p({ players: 1200, rank: 1 }))?.head, "1.200 người chơi · Hạng 1 Nhân vật hot");
  assert.equal(creatorBlock(p({ players: 3, rank: null }))?.head, "3 người chơi · Chưa có trên bảng Nhân vật hot");
  assert.equal(creatorBlock(p({ players: 0, rank: null }))?.head, "0 người chơi · Chưa có trên bảng Nhân vật hot");
});

test("the next reward tier with its coins; all three reached", () => {
  assert.equal(creatorBlock(p({}))?.reward, "Bậc thưởng tiếp theo: top 50 (+200 coin)");
  assert.equal(creatorBlock(p({ rank: null, next_tier: 100, next_reward: 100 }))?.reward, "Bậc thưởng tiếp theo: top 100 (+100 coin)");
  assert.equal(creatorBlock(p({ next_tier: 10, next_reward: 300 }))?.reward, "Bậc thưởng tiếp theo: top 10 (+300 coin)");
  assert.equal(creatorBlock(p({ next_tier: null, next_reward: null }))?.reward, "Đã nhận đủ thưởng xếp hạng");
});

test("no coins for this creator (the managing account, coins off): the tier without coins", () => {
  assert.equal(creatorBlock(p({ next_reward: null }))?.reward, "Bậc tiếp theo: top 50");
  assert.equal(creatorBlock(p({}), { rewards: false })?.reward, "Bậc tiếp theo: top 50");
  assert.equal(creatorBlock(p({ next_tier: null, next_reward: null }), { rewards: false })?.reward, null);
});

test("the next tier pays only once the board has characters of N creators: say so, with how many there are now", () => {
  assert.equal(creatorBlock(p({}))?.rule, null, "100 creators: top 50 can pay");
  assert.equal(
    creatorBlock(p({ rank: 1, next_tier: 10, next_reward: 300, board_creators: 1 }))?.rule,
    "Thưởng top 10 chỉ có khi bảng có nhân vật của ít nhất 10 người tạo khác nhau (hiện có 1).",
  );
  assert.equal(
    creatorBlock(p({ rank: 7, next_tier: 100, next_reward: 100, board_creators: 60 }))?.rule,
    "Thưởng top 100 chỉ có khi bảng có nhân vật của ít nhất 100 người tạo khác nhau (hiện có 60).",
  );
  assert.equal(creatorBlock(p({ next_tier: 10, next_reward: 300, board_creators: 10 }))?.rule, null);
  assert.equal(creatorBlock(p({ next_tier: null, next_reward: null, board_creators: 1 }))?.rule, null, "all reached");
  // No coins for this creator (managing account, coins off): nothing promised, no rule.
  assert.equal(creatorBlock(p({ next_tier: 10, next_reward: null, board_creators: 1 }))?.rule, null);
  assert.equal(creatorBlock(p({ next_tier: 10, board_creators: 1 }), { rewards: false })?.rule, null);
});

test("rewards waiting under the weekly cap", () => {
  assert.equal(creatorBlock(p({}))?.waiting, null);
  assert.equal(
    creatorBlock(p({ waiting_coins: 300 }))?.waiting,
    "Thưởng đang chờ: +300 coin (tối đa 600 coin mỗi 7 ngày)",
  );
  assert.equal(creatorBlock(p({ waiting_coins: 600 }), { rewards: false })?.waiting, null);
});

test("a private, unsaved or other people's character has no block; no 'Mốc tiếp theo' anywhere", () => {
  assert.equal(creatorBlock(null), null);
  assert.equal(creatorBlock(undefined), null);
  const all = allCoinStrings().join("\n");
  assert.doesNotMatch(all, /Mốc tiếp theo/);
  assert.doesNotMatch(readFileSync(new URL("./creatorLogic.ts", import.meta.url), "utf8"), /Mốc tiếp theo/);
  assert.doesNotMatch(readFileSync(new URL("./CardEditorPage.tsx", import.meta.url), "utf8"), /Mốc tiếp theo/);
  assert.equal(
    COIN_COPY.creatorHint,
    "Người chơi là tài khoản khác đã trò chuyện với nhân vật này ít nhất 3 câu trả lời, ở 2 ngày khác nhau. Bảng xếp hạng cập nhật mỗi giờ.",
  );
});

test("the creator words are member coin words: no technical or owner words", () => {
  for (const bad of [/chủ máy/i, /token/i, /credits/i, /model/i, /ollama/i]) {
    const b = creatorBlock(p({ waiting_coins: 300 }));
    assert.doesNotMatch([b?.head, b?.reward, b?.waiting].join("\n"), bad);
  }
});
