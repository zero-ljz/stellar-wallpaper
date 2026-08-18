"""Disk cache management for wallpaper images and thumbnails."""

from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path

from ..constants import CACHE_DIR, THUMB_CACHE_DIR, WALLPAPER_CACHE_DIR


class CacheManager:
    """Manages cached images and disk space."""

    def __init__(self) -> None:
        self.ensure_dirs()

    def ensure_dirs(self) -> None:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        THUMB_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        WALLPAPER_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def get_url_hash(url: str) -> str:
        return hashlib.md5(url.encode("utf-8")).hexdigest()

    def get_thumb_path(self, url: str) -> Path:
        self.ensure_dirs()
        h = self.get_url_hash(url)
        return THUMB_CACHE_DIR / f"thumb_{h}.jpg"

    def get_wallpaper_path(self, url: str) -> Path:
        self.ensure_dirs()
        h = self.get_url_hash(url)
        return WALLPAPER_CACHE_DIR / f"wp_{h}.jpg"

    def get_cache_size_bytes(self) -> int:
        total = 0
        if not CACHE_DIR.exists():
            return 0
        for dirpath, _, filenames in os.walk(CACHE_DIR):
            for f in filenames:
                fp = Path(dirpath) / f
                try:
                    total += fp.stat().st_size
                except (OSError, FileNotFoundError):
                    pass
        return total

    def get_cache_size_mb_str(self) -> str:
        bytes_val = self.get_cache_size_bytes()
        mb = bytes_val / (1024 * 1024)
        if mb >= 1024:
            return f"{mb / 1024:.2f} GB"
        return f"{mb:.2f} MB"

    def clear_cache(self) -> tuple[int, int]:
        """Clear all cached files, returns (deleted_files_count, freed_bytes)."""
        count = 0
        freed = 0
        if not CACHE_DIR.exists():
            return (0, 0)

        for dirpath, _, filenames in os.walk(CACHE_DIR):
            for f in filenames:
                fp = Path(dirpath) / f
                try:
                    size = fp.stat().st_size
                    fp.unlink()
                    count += 1
                    freed += size
                except (OSError, FileNotFoundError):
                    pass
        self.ensure_dirs()
        return (count, freed)

    def prune_cache_if_needed(self, max_mb: int = 500) -> None:
        """If cache exceeds max_mb, prune oldest files until under limit."""
        max_bytes = max_mb * 1024 * 1024
        current = self.get_cache_size_bytes()
        if current <= max_bytes:
            return

        files: list[tuple[Path, float, int]] = []
        for dirpath, _, filenames in os.walk(CACHE_DIR):
            for f in filenames:
                fp = Path(dirpath) / f
                try:
                    stat = fp.stat()
                    files.append((fp, stat.st_mtime, stat.st_size))
                except (OSError, FileNotFoundError):
                    pass

        # Sort by mtime ascending (oldest first)
        files.sort(key=lambda x: x[1])
        target = int(max_bytes * 0.8)  # prune down to 80% of limit
        for fp, _, size in files:
            if current <= target:
                break
            try:
                fp.unlink()
                current -= size
            except (OSError, FileNotFoundError):
                pass


# Global singleton instance
cache_mgr = CacheManager()
