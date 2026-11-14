"""Gói coin (docs/coins.md §4.1, PO chốt 2026-11-14). Bảng nằm trong code, không trong DB; giá chỉ để hiện.

Chế độ thử (§4.2): Lyris chưa bán coin. Giá là "Giá dự kiến" khi ra mắt; không có thanh toán, không có kênh liên hệ để
mua (`CONTACT = None`). Mã nạp do chủ máy tặng, không bán.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Pack:
    id: str
    coins: int  # tổng, đã cộng tặng thêm
    bonus: int
    price_vnd: int


PACKS: tuple[Pack, ...] = (
    Pack("p100", 100, 0, 10_000),
    Pack("p550", 550, 50, 50_000),
    Pack("p1200", 1_200, 200, 100_000),
    Pack("p2500", 2_500, 500, 200_000),
)
PACK_IDS: tuple[str, ...] = tuple(p.id for p in PACKS)
TEST_MODE = True
CONTACT: None = None


def pack(pack_id: str) -> Pack | None:
    return next((p for p in PACKS if p.id == pack_id), None)


__all__ = ["CONTACT", "PACKS", "PACK_IDS", "TEST_MODE", "Pack", "pack"]
