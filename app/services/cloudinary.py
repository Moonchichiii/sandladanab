"""Cloudinary URL builder — zero SDK, zero dependencies."""

from __future__ import annotations

from app.config import settings

_BASE = "https://res.cloudinary.com"


def cloud_url(
    public_id: str,
    *,
    width: int | None = None,
    height: int | None = None,
    crop: str = "fill",
    quality: str = "auto",
    fmt: str = "auto",
    gravity: str = "auto",
) -> str:
    """Build a Cloudinary delivery URL from a public ID.

    No SDK needed — just URL string building. Keeps the dep tree tiny.
    """
    if not settings.cloudinary_cloud:
        # Fallback: treat public_id as a local static path
        return f"/static/assets/images/{public_id}"

    transforms = [
        f"q_{quality}",
        f"f_{fmt}",
    ]
    if width:
        transforms.append(f"w_{width}")
    if height:
        transforms.append(f"h_{height}")
    if width or height:
        transforms.append(f"c_{crop}")
        transforms.append(f"g_{gravity}")

    transform_str = ",".join(transforms)
    cloud = settings.cloudinary_cloud
    return f"{_BASE}/{cloud}/image/upload/{transform_str}/{public_id}"


def srcset(
    public_id: str,
    widths: tuple[int, ...] = (320, 480, 640, 768, 1024, 1280),
    **kwargs: str,
) -> str:
    """Generate a srcset string for responsive images."""
    parts = []
    for w in widths:
        url = cloud_url(public_id, width=w, **kwargs)
        parts.append(f"{url} {w}w")
    return ", ".join(parts)
