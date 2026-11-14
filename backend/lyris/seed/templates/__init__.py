"""Nhân vật mẫu đi kèm app (trang Khám Phá): mỗi file `<slug>.json` trong thư mục này là một card đầy đủ
kèm `featured`, `vibes`, `order` và (tuỳ chọn) `image` là ảnh bối cảnh giấy phép mở nằm cạnh file JSON.

Định dạng file:
    {
      "order": 1,                      # thứ tự hiển thị (nhỏ trước; featured luôn đứng đầu)
      "featured": true,
      "vibes": ["Chữa lành", ...],
      "adopt_existing": false,         # true: card trùng tên + style profile đã có trong DB (ví dụ card seed)
                                       #       cũng tính là "đã cài"
      "image": {"file", "title", "creator", "licence", "licence_url", "source_url", "changes"} | null,
      "card": { ...CharacterCard..., "extensions": {"lyris": {"template": "<slug>"}} }
    }

Card cài từ template được nhận ra qua `card.extensions.lyris.template == slug`.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from lyris.models import CharacterCard

TEMPLATES_DIR: Path = Path(__file__).resolve().parent
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
IMAGE_TYPES: dict[str, str] = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
MAX_IMAGE_BYTES = 600 * 1024


class TemplateImage(BaseModel):
    """Ảnh bối cảnh của template và thông tin ghi nguồn (giấy phép mở)."""

    file: str
    title: str
    creator: str
    licence: str
    licence_url: str | None = None
    source_url: str
    changes: str | None = Field(default=None, description="Đã sửa gì so với bản gốc (cắt khung, thu nhỏ...)")


@dataclass(frozen=True)
class Template:
    slug: str
    order: int
    featured: bool
    vibes: list[str]
    adopt_existing: bool
    card: CharacterCard
    image: TemplateImage | None

    @property
    def image_path(self) -> Path | None:
        if self.image is None:
            return None
        path = TEMPLATES_DIR / self.image.file
        return path if path.is_file() else None


class TemplateError(ValueError):
    """File template sai định dạng (lỗi của người viết template, không phải của người dùng)."""


def _parse(slug: str, data: Any) -> Template:
    if not isinstance(data, dict):
        raise TemplateError(f"Template {slug}: phải là một object JSON")
    card_data = data.get("card")
    if not isinstance(card_data, dict):
        raise TemplateError(f"Template {slug}: thiếu trường card")
    card = CharacterCard.model_validate({**card_data, "id": None, "avatar": None})
    ext = dict(card.extensions)
    lyris_ext = ext.get("lyris") if isinstance(ext.get("lyris"), dict) else {}
    ext["lyris"] = {**lyris_ext, "template": slug}
    card = card.model_copy(update={"extensions": ext})

    image: TemplateImage | None = None
    raw_image = data.get("image")
    if raw_image is not None:
        image = TemplateImage.model_validate(raw_image)
        name = Path(image.file).name
        if name != image.file or Path(name).suffix.lower() not in IMAGE_TYPES:
            raise TemplateError(f"Template {slug}: tên file ảnh không hợp lệ ({image.file!r})")

    vibes = data.get("vibes") or []
    if not isinstance(vibes, list) or not all(isinstance(v, str) and v.strip() for v in vibes):
        raise TemplateError(f"Template {slug}: vibes phải là danh sách chuỗi")
    order = data.get("order", 1000)
    if isinstance(order, bool) or not isinstance(order, int):
        raise TemplateError(f"Template {slug}: order phải là số nguyên")
    return Template(
        slug=slug,
        order=order,
        featured=bool(data.get("featured", False)),
        vibes=[v.strip() for v in vibes],
        adopt_existing=bool(data.get("adopt_existing", False)),
        card=card,
        image=image,
    )


@lru_cache(maxsize=1)
def _load_all(directory: str) -> tuple[Template, ...]:
    out: list[Template] = []
    for file in sorted(Path(directory).glob("*.json")):
        slug = file.stem
        if not SLUG_RE.fullmatch(slug):
            raise TemplateError(f"Tên file template không hợp lệ: {file.name}")
        out.append(_parse(slug, json.loads(file.read_text(encoding="utf-8"))))
    out.sort(key=lambda t: (not t.featured, t.order, t.slug))
    return tuple(out)


def load_templates() -> list[Template]:
    """Mọi template, featured trước rồi theo `order`. Đọc file một lần (cache)."""
    return list(_load_all(str(TEMPLATES_DIR)))


def get_template(slug: str) -> Template | None:
    return next((t for t in load_templates() if t.slug == slug), None)


def image_media_type(path: Path) -> str:
    return IMAGE_TYPES.get(path.suffix.lower(), "application/octet-stream")


__all__ = [
    "IMAGE_TYPES",
    "MAX_IMAGE_BYTES",
    "TEMPLATES_DIR",
    "Template",
    "TemplateError",
    "TemplateImage",
    "get_template",
    "image_media_type",
    "load_templates",
]
