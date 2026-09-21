"""Render the responsive WebP set for every image slot from assets-src/*.jpg.

Usage:  python scripts/render_images.py
Needs Pillow >= 10 with AVIF support (pip install "pillow>=10.0"; add
pillow-avif-plugin only if the AVIF save fails).

Each slot = one source photo, one aspect ratio, a focal point (fractions of the
source, used to place the crop) and the rendition widths the templates request in
srcset. Output: static/assets/images/<slot>-<width>.avif and .webp (the templates
use <picture>: AVIF first, WebP fallback). Re-run after replacing a source photo;
nothing else needs to change. EXIF is dropped on output.
"""

from __future__ import annotations

import pathlib
import sys

try:
    from PIL import Image, ImageOps, features
except ImportError:  # pragma: no cover
    sys.exit("Pillow saknas: pip install pillow")

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "assets-src"
OUT = ROOT / "static" / "assets" / "images"
QUALITY_WEBP = 70
QUALITY_AVIF = 56  # AVIF is served first via <picture>; WebP is the fallback

# name: (source file, (ratio_w, ratio_h), (focal_x, focal_y), widths)
SLOTS: dict[str, tuple[str, tuple[int, int], tuple[float, float], tuple[int, ...]]] = {
    "hero-rorlaggning": (
        "hero-rorlaggning.jpg",
        (3, 2),
        (0.5, 0.50),
        (768, 1280, 1920),
    ),
    "galleri-isolering": (
        "galleri-isolering.jpg",
        (1, 1),
        (0.5, 0.52),
        (768, 1024, 1536),
    ),
    "galleri-maskinstyrning": (
        "galleri-maskinstyrning.jpg",
        (1, 1),
        (0.5, 0.47),
        (480, 768, 1024),
    ),
    "galleri-kabelror": (
        "galleri-kabelror.jpg",
        (1, 1),
        (0.5, 0.625),
        (480, 768, 1024),
    ),
    "galleri-avloppsror": (
        "galleri-avloppsror.jpg",
        (2, 1),
        (0.5, 0.53),
        (768, 1152, 1536),
    ),
    "om-hytten": ("om-hytten.jpg", (4, 5), (0.5, 0.50), (480, 768, 960)),
}


def crop_to_ratio(
    im: Image.Image, ratio: tuple[int, int], focal: tuple[float, float]
) -> Image.Image:
    rw, rh = ratio
    w, h = im.size
    target = rw / rh
    if w / h > target:  # too wide → trim width
        cw, ch = round(h * target), h
    else:  # too tall → trim height
        cw, ch = w, round(w / target)
    fx, fy = focal
    x0 = min(max(round(w * fx - cw / 2), 0), w - cw)
    y0 = min(max(round(h * fy - ch / 2), 0), h - ch)
    return im.crop((x0, y0, x0 + cw, y0 + ch))


OG = ("hero-rorlaggning.jpg", (1200, 630), (0.5, 0.50))  # link-preview image, JPEG


def render_og(src_dir: pathlib.Path, brand_dir: pathlib.Path) -> pathlib.Path | None:
    """1200x630 JPEG for og:image (LinkedIn/Slack previews want JPEG or PNG)."""
    file, (w, h), focal = OG
    path = src_dir / file
    if not path.is_file():
        print(f"  saknas: {path}")
        return None
    brand_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(path) as raw:
        im = ImageOps.exif_transpose(raw).convert("RGB")
        im = crop_to_ratio(im, (w, h), focal).resize((w, h), Image.LANCZOS)
        out = brand_dir / "og-image.jpg"
        im.save(out, "JPEG", quality=82, optimize=True, progressive=True)
    print(f"  {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}  {w}x{h}")
    return out


def main(
    src_dir: pathlib.Path = SRC,
    out_dir: pathlib.Path = OUT,
    brand_dir: pathlib.Path = ROOT / "static" / "assets" / "brand",
) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    render_og(src_dir, brand_dir)
    avif_ok = features.check("avif")
    if not avif_ok:
        print(
            "  AVIF saknas i denna Pillow - bara WebP renderas "
            "(pip install pillow-avif-plugin)"
        )
    for name, (src, ratio, focal, widths) in SLOTS.items():
        path = src_dir / src
        if not path.is_file():
            print(f"  saknas: {path}")
            continue
        with Image.open(path) as raw:
            im = ImageOps.exif_transpose(raw).convert("RGB")
            im = crop_to_ratio(im, ratio, focal)
            for w in widths:
                if w > im.width:
                    print(
                        f"  {name}-{w}: källan är bara {im.width}px bred "
                        "- renderar ändå (uppskalning)"
                    )
                target = (w, round(w * im.height / im.width))
                small = im.resize(target, Image.LANCZOS)
                out_webp = out_dir / f"{name}-{w}.webp"
                small.save(out_webp, "WEBP", quality=QUALITY_WEBP, method=6)
                kb = out_webp.stat().st_size // 1024
                line = f"  {name}-{w}  {target[0]}x{target[1]}  webp {kb} KB"
                if avif_ok:
                    out_avif = out_dir / f"{name}-{w}.avif"
                    small.save(out_avif, "AVIF", quality=QUALITY_AVIF, speed=4)
                    line += f"  avif {out_avif.stat().st_size // 1024} KB"
                print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
