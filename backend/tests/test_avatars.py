from __future__ import annotations

import io
import os
import re
import time
from pathlib import Path

import pytest
from PIL import Image, PngImagePlugin

from lyris.studio.avatars import (
    MAX_AVATAR_BYTES,
    AvatarError,
    avatar_path,
    claim_temp,
    cleanup_temp,
    hold_temp,
    normalize_image,
    remove_avatar,
    save_card_avatar,
)

NAME_RE = re.compile(r"^card-(\d+)-[0-9a-f]{8}\.png$")


def encode(img: Image.Image, fmt: str, **params: object) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format=fmt, **params)
    return buf.getvalue()


def decode(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    img.load()
    return img


# ---------------------------------------------------------------- normalize_image


def test_jpeg_exif_rotation_applied_and_metadata_stripped() -> None:
    img = Image.new("RGB", (100, 50), (200, 30, 30))
    exif = Image.Exif()
    exif[0x0112] = 6  # Orientation: xoay 90 độ
    exif[0x010F] = "Máy ảnh bí mật"  # Make
    data = encode(img, "JPEG", exif=exif.tobytes())

    out = normalize_image(data)
    result = decode(out)
    assert result.format == "PNG"
    assert result.size == (50, 100)
    assert result.mode == "RGB"
    assert not result.getexif()
    assert "exif" not in result.info


def test_png_text_and_icc_removed_alpha_kept() -> None:
    img = Image.new("RGBA", (40, 30), (0, 0, 0, 0))
    img.putpixel((1, 1), (10, 20, 30, 255))
    info = PngImagePlugin.PngInfo()
    info.add_text("chara", "eyJzZWNyZXQiOiAxfQ==")
    info.add_text("Comment", "riêng tư")
    data = encode(img, "PNG", pnginfo=info, icc_profile=b"\x00" * 128)

    out = normalize_image(data)
    for chunk in (b"tEXt", b"iTXt", b"zTXt", b"iCCP", b"eXIf"):
        assert chunk not in out
    result = decode(out)
    assert result.mode == "RGBA" and result.size == (40, 30)
    assert result.getpixel((0, 0))[3] == 0
    assert result.getpixel((1, 1)) == (10, 20, 30, 255)


def test_large_image_fits_in_768_keeping_ratio() -> None:
    out = decode(normalize_image(encode(Image.new("RGB", (2000, 1000), "white"), "PNG")))
    assert out.size == (768, 384)
    tall = decode(normalize_image(encode(Image.new("RGB", (900, 1800), "white"), "JPEG")))
    assert tall.size == (384, 768)


def test_small_image_not_upscaled() -> None:
    out = decode(normalize_image(encode(Image.new("RGB", (64, 48), "blue"), "PNG")))
    assert out.size == (64, 48)


def test_gif_first_frame_and_webp() -> None:
    frames = [Image.new("P", (20, 20), i) for i in (1, 2, 3)]
    gif = io.BytesIO()
    frames[0].save(gif, format="GIF", save_all=True, append_images=frames[1:], duration=50, loop=0)
    out = decode(normalize_image(gif.getvalue()))
    assert out.size == (20, 20) and out.format == "PNG"

    webp = encode(Image.new("RGB", (30, 10), "green"), "WEBP")
    assert decode(normalize_image(webp)).size == (30, 10)


def test_palette_with_transparency_becomes_rgba() -> None:
    img = Image.new("P", (8, 8), 0)
    img.putpalette([0, 0, 0, 255, 0, 0] + [0] * 762)
    img.info["transparency"] = 0
    out = decode(normalize_image(encode(img, "PNG", transparency=0)))
    assert out.mode == "RGBA"
    assert out.getpixel((0, 0))[3] == 0


def test_rejects_bad_input() -> None:
    with pytest.raises(AvatarError, match="rỗng"):
        normalize_image(b"")
    with pytest.raises(AvatarError, match="8MB"):
        normalize_image(b"\x89PNG" + b"\x00" * MAX_AVATAR_BYTES)
    with pytest.raises(AvatarError, match="không hỗ trợ"):
        normalize_image(b"day khong phai anh")
    with pytest.raises(AvatarError, match="không hỗ trợ"):
        normalize_image(encode(Image.new("RGB", (5, 5)), "BMP"))
    png = encode(Image.new("RGB", (300, 300), (1, 2, 3)), "PNG")
    with pytest.raises(AvatarError, match="hỏng"):
        normalize_image(png[: len(png) // 2])
    # AvatarError là ValueError (API đổi thành 422).
    assert issubclass(AvatarError, ValueError)


def test_rejects_decompression_bomb() -> None:
    bomb = encode(Image.new("1", (10000, 5000), 0), "PNG")
    assert len(bomb) < MAX_AVATAR_BYTES
    with pytest.raises(AvatarError, match="quá lớn"):
        normalize_image(bomb)


# ---------------------------------------------------------------- files


def test_save_card_avatar_new_name_each_time(tmp_path: Path) -> None:
    avatars = tmp_path / "avatars"
    data = encode(Image.new("RGB", (10, 10), "red"), "JPEG")
    a = save_card_avatar(avatars, 7, data)
    b = save_card_avatar(avatars, 7, data)
    assert NAME_RE.fullmatch(a) and NAME_RE.fullmatch(b)
    assert a.startswith("card-7-") and a != b
    assert decode((avatars / a).read_bytes()).format == "PNG"
    assert avatar_path(avatars, a) == (avatars / a).resolve()
    assert sorted(p.name for p in avatars.iterdir()) == sorted([a, b])
    with pytest.raises(AvatarError):
        save_card_avatar(avatars, 7, b"rac")
    assert len(list(avatars.iterdir())) == 2


@pytest.mark.parametrize(
    "name",
    ["", "..", "../x.png", "a/b.png", "/etc/passwd", "..\\x.png", ".hidden.png", "x.png\x00", "card-1.jpg", "tmp"],
)
def test_avatar_path_blocks_traversal(tmp_path: Path, name: str) -> None:
    with pytest.raises(AvatarError):
        avatar_path(tmp_path, name)


def test_remove_avatar(tmp_path: Path) -> None:
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"x")
    avatars = tmp_path / "avatars"
    name = save_card_avatar(avatars, 1, encode(Image.new("RGB", (4, 4)), "PNG"))
    remove_avatar(avatars, name)
    assert not (avatars / name).exists()
    remove_avatar(avatars, name)  # đã xoá: không lỗi
    remove_avatar(avatars, None)
    remove_avatar(tmp_path / "khong-co", "card-1-00000000.png")
    remove_avatar(avatars, "../outside.png")
    assert outside.exists()


def test_hold_and_claim_temp(tmp_path: Path) -> None:
    avatars = tmp_path / "avatars"
    token = hold_temp(avatars, encode(Image.new("RGB", (1000, 500), "white"), "PNG"), 7)
    assert re.fullmatch(r"[0-9a-f]{32}", token)
    held = avatars / "tmp" / f"7-{token}.png"
    assert decode(held.read_bytes()).size == (768, 384)

    # Phase 4b (docs/auth.md §4.6): tài khoản khác không lấy được ảnh tạm dù biết token.
    assert claim_temp(avatars, token, 12, 8) is None and held.exists()
    name = claim_temp(avatars, token, 12, 7)
    assert name is not None and NAME_RE.fullmatch(name) and name.startswith("card-12-")
    assert (avatars / name).is_file() and not held.exists()
    assert claim_temp(avatars, token, 12, 7) is None  # dùng một lần

    assert claim_temp(avatars, "f" * 32, 1, 7) is None
    assert claim_temp(avatars, "../../etc/passwd", 1, 7) is None
    assert claim_temp(avatars, "", 1, 7) is None
    with pytest.raises(AvatarError):
        hold_temp(avatars, b"khong phai anh", 7)


def test_cleanup_temp(tmp_path: Path) -> None:
    avatars = tmp_path / "avatars"
    assert cleanup_temp(avatars) == 0  # chưa có thư mục
    png = encode(Image.new("RGB", (4, 4)), "PNG")
    old = hold_temp(avatars, png, 1)
    fresh = hold_temp(avatars, png, 1)
    stale_part = avatars / "tmp" / "abc.png.part"
    stale_part.write_bytes(b"x")
    keep_other = avatars / "tmp" / "ghi-chu.txt"
    keep_other.write_text("không phải ảnh", encoding="utf-8")
    long_ago = time.time() - 2 * 86400
    for path in (avatars / "tmp" / f"1-{old}.png", stale_part, keep_other):
        os.utime(path, (long_ago, long_ago))
    card_file = save_card_avatar(avatars, 3, png)
    os.utime(avatars / card_file, (long_ago, long_ago))

    assert cleanup_temp(avatars) == 2
    assert not (avatars / "tmp" / f"1-{old}.png").exists() and not stale_part.exists()
    assert (avatars / "tmp" / f"1-{fresh}.png").exists()
    assert keep_other.exists()
    assert (avatars / card_file).exists()  # avatar thật không bao giờ bị dọn
    assert claim_temp(avatars, old, 3, 1) is None
    assert cleanup_temp(avatars, max_age_s=0) == 1
