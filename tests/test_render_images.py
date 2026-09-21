"""The image pipeline renders every slot in both formats from a synthetic source."""

from __future__ import annotations

import importlib.util
import pathlib

import pytest

PIL = pytest.importorskip("PIL")
from PIL import Image, features  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "render_images", ROOT / "scripts" / "render_images.py"
)
render_images = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(render_images)


def test_crop_to_ratio_keeps_focal_point() -> None:
    im = Image.new("RGB", (2048, 1536), (10, 10, 10))
    out = render_images.crop_to_ratio(im, (3, 2), (0.5, 0.5))
    assert out.size == (2048, 1365)
    out = render_images.crop_to_ratio(
        Image.new("RGB", (1536, 2048)), (1, 1), (0.5, 0.9)
    )
    assert out.size == (1536, 1536)


def test_every_slot_renders(tmp_path: pathlib.Path) -> None:
    src = tmp_path / "src"
    out = tmp_path / "out"
    src.mkdir()
    for _, (file, _, _, _) in render_images.SLOTS.items():
        Image.new("RGB", (400, 300), (200, 120, 40)).save(
            src / file, "JPEG", quality=80
        )

    assert render_images.main(src, out) == 0

    for name, (_, ratio, _, widths) in render_images.SLOTS.items():
        for w in widths:
            webp = out / f"{name}-{w}.webp"
            assert webp.is_file(), webp
            with Image.open(webp) as im:
                assert im.width == w
                # a small synthetic source rounds the crop; allow a few px
                assert abs(im.height - round(w * ratio[1] / ratio[0])) <= 3
            if features.check("avif"):
                assert (out / f"{name}-{w}.avif").is_file()


def test_shipped_renditions_match_content_records() -> None:
    """Every image record in app/content.py has all of its renditions on disk."""
    import app.content as content

    records = [content.HERO_IMAGE, content.ABOUT_IMAGE, *content.GALLERY_ITEMS]
    images = ROOT / "static" / "assets" / "images"
    for rec in records:
        for w in rec["widths"]:
            for ext in ("avif", "webp"):
                assert (images / f"{rec['file']}-{w}.{ext}").is_file(), (
                    f"{rec['file']}-{w}.{ext}"
                )
