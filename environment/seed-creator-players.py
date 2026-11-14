"""② ENVIRONMENT — F44, F46: dựng sẵn "người chơi" cho một nhân vật công khai trong DB TẠM của bot.

Chạy (luôn bằng Python của backend; bot `environment/e2e.mjs` tự gọi, không cần chạy tay):

    backend/.venv/bin/python environment/seed-creator-players.py --db reports/bot/lyris.db --card 42 --players 12

Vì sao có file này: người chơi chỉ được tính khi có ≥ 3 câu trả lời đã trả coin ở ≥ 2 NGÀY coin khác nhau
(docs/coins.md §5.1), nên HTTP API của app không dựng được trong một lượt bot. File này tạo `--players` thành viên, mỗi
người một story bằng bản sao của nhân vật, 2 câu trả lời đã trả coin hôm qua và 1 câu hôm nay, đi qua đúng code của app
(`copy_public_card`, `create_story_for`, `holds.open_hold` / `charge_hold`, `creator.note_charged`). Xong thì tính lại
bảng "Nhân vật hot" ngay (`hot.compute`, như lần tính mỗi giờ: app đã tính bảng lúc bot mở app, bảng chỉ tự tính lại sau
60 phút), nên nhân vật này có hạng ngay. Không có tin nhắn hay LLM nào.

An toàn: chỉ chạy trên DB tạm của bot (thư mục có dấu `.lyris-bot-data` do fake-server.py tạo), không bao giờ `data/`.
In ra một dòng JSON: {"card": id, "players": n, "creator_players": n, "rank": hạng trên bảng hay null}.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if Path(sys.prefix).resolve() != (BACKEND / ".venv").resolve():
    sys.exit("seed-creator-players.py chỉ chạy bằng backend/.venv/bin/python (không dùng Python của hệ thống).")
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from lyris.auth import clock  # noqa: E402
from lyris.auth import store as auth_store  # noqa: E402
from lyris.coins import creator, holds, hot  # noqa: E402
from lyris.db.connection import connect  # noqa: E402
from lyris.db.repo import Repo, new_uid  # noqa: E402
from lyris.models import Persona  # noqa: E402
from lyris.studio.stories import create_story_for  # noqa: E402

MARKER = ".lyris-bot-data"
PRICE = 6


def _safe_db(path: Path) -> Path:
    path = path.resolve()
    forbidden = (ROOT / "data").resolve()
    if path == forbidden or forbidden in path.parents:
        raise SystemExit(f"Từ chối: {path} nằm trong data/ (DB thật của người dùng).")
    if not (path.parent / MARKER).exists():
        raise SystemExit(f"Từ chối: {path.parent} không có dấu {MARKER} (không phải DB tạm của bot).")
    if not path.exists():
        raise SystemExit(f"Không thấy {path}.")
    return path


def seed(db: Path, card_id: int, players: int, prefix: str) -> dict[str, int]:
    conn = connect(db)
    try:
        repo = Repo(conn)
        owner = repo.owner_account()
        assert owner.id is not None
        today = clock.now()
        days = [today - timedelta(days=1), today - timedelta(days=1), today]
        for i in range(1, players + 1):
            with repo.transaction():
                acc = auth_store.insert_member(
                    conn, uid=new_uid(), handle=f"{prefix}{i:02d}", display_name=f"Người chơi {i}", invited_by=owner.id
                )
                persona = repo.create_persona(Persona(name=f"Người chơi {i}", gender="female"), account_id=acc)
                assert persona.id is not None
                copy = repo.copy_public_card(card_id, account_id=acc)
                assert copy.id is not None
                story = create_story_for(repo, copy.id, persona.id, model_name="gemma4:12b", account_id=acc)
                assert story.id is not None
                for moment in days:
                    hold_id = holds.open_hold(
                        conn, acc, story_id=story.id, char_key=card_id, origin_card_id=card_id, mode="story",
                        kind="send", amount=PRICE, now=moment,
                    )
                    holds.charge_hold(conn, hold_id, message_id=None, story_id=story.id, card_id=copy.id, now=moment)
                    creator.note_charged(conn, hold_id, now=moment)
        counted = creator.player_count(conn, card_id)
        hot.compute(conn)
        rank = hot.card_rank(conn, card_id)
    finally:
        conn.close()
    return {"card": card_id, "players": players, "creator_players": counted, "rank": rank}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--card", required=True, type=int)
    parser.add_argument("--players", type=int, default=12)
    parser.add_argument("--prefix", default="nguoichoi")
    args = parser.parse_args()
    print(json.dumps(seed(_safe_db(args.db), args.card, args.players, args.prefix)), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
