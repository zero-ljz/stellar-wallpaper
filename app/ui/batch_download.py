"""Reusable background worker for batch wallpaper downloads."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal

from ..core.download_manager import download_wallpaper, wallpaper_download_key


class BatchDownloadWorker(QThread):
    """Download a snapshot of wallpaper items without blocking the UI."""

    item_finished = Signal(int, int, str)  # processed, total, title
    batch_completed = Signal(
        int, int, int, bool
    )  # downloaded, skipped, failed, cancelled

    def __init__(
        self,
        items: list[dict[str, Any]],
        save_dir: Path,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        unique_items: dict[str, dict[str, Any]] = {}
        for item in items:
            unique_items.setdefault(wallpaper_download_key(item), dict(item))
        self.items = list(unique_items.values())
        self.save_dir = save_dir

    def run(self) -> None:
        downloaded = 0
        skipped = 0
        failed = 0
        processed = 0
        cancelled = False

        for item in self.items:
            if self.isInterruptionRequested():
                cancelled = True
                break
            try:
                result = download_wallpaper(
                    item, self.save_dir, self.isInterruptionRequested
                )
            except Exception:  # noqa: BLE001 - one bad item must not abort the batch
                failed += 1
                processed += 1
                self.item_finished.emit(processed, len(self.items), "下载失败")
                continue
            if result.status == "cancelled":
                cancelled = True
                break
            if result.status == "downloaded":
                downloaded += 1
            elif result.status == "skipped":
                skipped += 1
            else:
                failed += 1
            processed += 1
            title = str(
                item.get("title")
                or item.get("wallpaper_id")
                or item.get("id")
                or "壁纸"
            )
            if len(title) > 36:
                title = f"{title[:36]}..."
            self.item_finished.emit(processed, len(self.items), title)

        self.batch_completed.emit(downloaded, skipped, failed, cancelled)
