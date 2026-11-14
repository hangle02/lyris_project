"""Endpoint sổ thế giới (Phase 4, docs/phase4.md §8). Mọi route lọc theo account hiện tại: card/story của
account khác coi như không có (404); mục không thuộc card trong path, hoặc đã xoá, cũng 404.

- GET    /api/cards/{card_id}/lore                     LoreEntryOut[] theo position, id
- POST   /api/cards/{card_id}/lore                     LoreEntryIn -> LoreEntryOut (409 khi quá 500 mục)
- PUT    /api/cards/{card_id}/lore/{entry_id}          LoreEntryIn -> LoreEntryOut
- PATCH  /api/cards/{card_id}/lore/{entry_id}          LorePatch -> LoreEntryOut (bật/tắt, đổi chỗ)
- DELETE /api/cards/{card_id}/lore/{entry_id}          {"deleted": 1}
- POST   /api/cards/{card_id}/lore/import              LoreImportRequest -> LoreImportResult
- POST   /api/cards/{card_id}/lore/import-book         {"dry_run"} -> LoreImportResult
- GET    /api/cards/{card_id}/lore/summary             LoreSummary (hồ sơ nhân vật)
- GET    /api/stories/{story_id}/lore                  StoryLore (ngăn "Cảm xúc & ký ức")

Không khoá story khi sửa sổ thế giới: lượt đang chạy đã dựng prompt xong, lượt sau dùng bản mới.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from lyris.api.deps import CurrentAccount, account_id_of, current_account
from lyris.db.repo import Repo
from lyris.lore.service import LoreService
from lyris.models import (
    LoreBookImportRequest,
    LoreEntryIn,
    LoreEntryOut,
    LoreImportRequest,
    LoreImportResult,
    LorePatch,
    LoreSummary,
    StoryLore,
)

# Phase 4b: mặc định là cấm — mọi route ở đây cần đăng nhập (docs/auth.md §2.5).
router = APIRouter(prefix="/api", dependencies=[Depends(current_account)])


def lore_service(request: Request) -> LoreService:
    lore: LoreService = request.app.state.lore
    return lore


def _repo(request: Request) -> Repo:
    repo: Repo = request.app.state.repo
    return repo


@router.get("/cards/{card_id}/lore", response_model=list[LoreEntryOut])
async def list_lore(request: Request, card_id: int, account: CurrentAccount) -> list[LoreEntryOut]:
    return lore_service(request).list_entries(card_id, account_id=account_id_of(account))


@router.post("/cards/{card_id}/lore", response_model=LoreEntryOut)
async def create_lore(request: Request, card_id: int, body: LoreEntryIn, account: CurrentAccount) -> LoreEntryOut:
    return lore_service(request).create(card_id, body, account_id=account_id_of(account))


@router.post("/cards/{card_id}/lore/import", response_model=LoreImportResult)
async def import_lore(
    request: Request, card_id: int, body: LoreImportRequest, account: CurrentAccount
) -> LoreImportResult:
    return lore_service(request).import_world_md(
        card_id,
        body.text,
        dry_run=body.dry_run,
        delete_missing=body.delete_missing,
        account_id=account_id_of(account),
    )


@router.post("/cards/{card_id}/lore/import-book", response_model=LoreImportResult)
async def import_card_book(
    request: Request, card_id: int, account: CurrentAccount, body: LoreBookImportRequest | None = None
) -> LoreImportResult:
    dry_run = body.dry_run if body is not None else False
    return lore_service(request).import_card_book(card_id, dry_run=dry_run, account_id=account_id_of(account))


@router.get("/cards/{card_id}/lore/summary", response_model=LoreSummary)
async def lore_summary(request: Request, card_id: int, account: CurrentAccount) -> LoreSummary:
    return lore_service(request).summary(card_id, account_id=account_id_of(account))


@router.put("/cards/{card_id}/lore/{entry_id}", response_model=LoreEntryOut)
async def update_lore(
    request: Request, card_id: int, entry_id: int, body: LoreEntryIn, account: CurrentAccount
) -> LoreEntryOut:
    return lore_service(request).update(card_id, entry_id, body, account_id=account_id_of(account))


@router.patch("/cards/{card_id}/lore/{entry_id}", response_model=LoreEntryOut)
async def patch_lore(
    request: Request, card_id: int, entry_id: int, body: LorePatch, account: CurrentAccount
) -> LoreEntryOut:
    return lore_service(request).patch(card_id, entry_id, body, account_id=account_id_of(account))


@router.delete("/cards/{card_id}/lore/{entry_id}")
async def delete_lore(request: Request, card_id: int, entry_id: int, account: CurrentAccount) -> dict[str, int]:
    lore_service(request).delete(card_id, entry_id, account_id=account_id_of(account))
    return {"deleted": 1}


@router.get("/stories/{story_id}/lore", response_model=StoryLore)
async def story_lore(request: Request, story_id: int, account: CurrentAccount) -> StoryLore:
    account_id = account_id_of(account)
    story = _repo(request).get_story(story_id, account_id=account_id)  # 404 nếu không có / của account khác
    return lore_service(request).story_lore(story, account_id=account_id)


__all__ = ["lore_service", "router"]
