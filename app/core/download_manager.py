"""Shared helpers for saving original wallpaper files."""

from __future__ import annotations

import re
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

from .api_client import api_client, get_full_image_url
from .cache_manager import cache_mgr

DownloadStatus = Literal["downloaded", "skipped", "failed", "cancelled"]
_SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


@dataclass(frozen=True)
class DownloadResult:
    status: DownloadStatus
    target: Path | None


def wallpaper_download_key(item: dict[str, Any]) -> str:
    """Return a stable key used to deduplicate selected wallpaper items."""
    url = get_full_image_url(item)
    if url:
        return url
    return str(item.get("wallpaper_id") or item.get("id") or id(item))


def build_download_target(item: dict[str, Any], save_dir: Path) -> Path | None:
    """Build a deterministic, Windows-safe path for a wallpaper item."""
    url = get_full_image_url(item)
    if not url:
        return None

    raw_id = str(item.get("wallpaper_id") or item.get("id") or "pic")
    safe_id = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", raw_id).strip(" .")
    safe_id = safe_id[:64] or "pic"
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix not in _SUPPORTED_EXTENSIONS:
        suffix = ".jpg"
    digest = cache_mgr.get_url_hash(url)[:12]
    return save_dir / f"Wallpaper_{safe_id}_{digest}{suffix}"


def download_wallpaper(
    item: dict[str, Any],
    save_dir: Path,
    cancel_check: Callable[[], bool] | None = None,
) -> DownloadResult:
    """Save one wallpaper, preferring cache and never overwriting an existing file."""
    url = get_full_image_url(item)
    target = build_download_target(item, save_dir)
    if not url or target is None:
        return DownloadResult("failed", None)
    if cancel_check and cancel_check():
        return DownloadResult("cancelled", target)

    try:
        save_dir.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.stat().st_size > 0:
            return DownloadResult("skipped", target)

        cached = cache_mgr.get_wallpaper_path(url)
        if cached.exists() and cached.stat().st_size > 0:
            shutil.copy2(cached, target)
            return DownloadResult("downloaded", target)

        ok = api_client.download_image(url, target, cancel_check=cancel_check)
        if ok:
            return DownloadResult("downloaded", target)
        if cancel_check and cancel_check():
            return DownloadResult("cancelled", target)
        return DownloadResult("failed", target)
    except (OSError, shutil.Error):
        return DownloadResult("failed", target)
