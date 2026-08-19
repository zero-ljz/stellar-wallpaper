"""Wallpaper Scheduler and auto-rotation manager."""

from __future__ import annotations

import random
import threading
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QThread, QTimer, Signal

from ..config import config
from .api_client import api_client, get_full_image_url
from .database import db
from .wallpaper_setter import wallpaper_setter


class WallpaperSwitchWorker(QThread):
    """Background worker for fetching, downloading and setting wallpaper."""

    stage_changed = Signal(str)
    download_progress = Signal(int, int, int)  # current, total, percent
    finished_success = Signal(dict)
    finished_error = Signal(str)

    def __init__(
        self,
        source: str = "categories",
        category_ids: list[str] | None = None,
        specific_item: dict[str, Any] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.source = source
        self.category_ids = category_ids or config.selected_categories
        self.specific_item = specific_item
        self._is_cancelled = False

    def cancel(self) -> None:
        self._is_cancelled = True

    def run(self) -> None:
        try:
            # 1. Determine which wallpaper to apply
            if self.specific_item:
                item = dict(self.specific_item)
                img_url = get_full_image_url(item) or item.get("thumb_url") or ""
                local_path = item.get("local_path")
                
                # Check if already on disk
                if not local_path or not Path(local_path).exists():
                    self.stage_changed.emit("正在下载壁纸...")
                    from .cache_manager import cache_mgr
                    target_path = cache_mgr.get_wallpaper_path(img_url or str(random.random()))
                    
                    def on_progress(cur: int, tot: int, pct: int) -> None:
                        if not self._is_cancelled:
                            self.download_progress.emit(cur, tot, pct)

                    ok = api_client.download_image(img_url, target_path, on_progress, lambda: self._is_cancelled)
                    if not ok or not target_path.exists():
                        self.finished_error.emit("壁纸下载失败，请检查网络连接")
                        return
                    item["local_path"] = str(target_path)
            elif self.source == "favorites":
                self.stage_changed.emit("正在从收藏夹抽取壁纸...")
                fav = db.get_random_favorite()
                if not fav:
                    self.finished_error.emit("收藏夹为空，无法从收藏夹轮播")
                    return
                item = fav
                local_path = item.get("local_path")
                img_url = get_full_image_url(item)
                if not local_path or not Path(local_path).exists():
                    self.stage_changed.emit("正在下载收藏壁纸...")
                    from .cache_manager import cache_mgr
                    target_path = cache_mgr.get_wallpaper_path(img_url or "fav")

                    def on_progress(cur: int, tot: int, pct: int) -> None:
                        if not self._is_cancelled:
                            self.download_progress.emit(cur, tot, pct)

                    ok = api_client.download_image(img_url, target_path, on_progress, lambda: self._is_cancelled)
                    if not ok:
                        self.finished_error.emit("下载收藏壁纸失败")
                        return
                    item["local_path"] = str(target_path)
            else:
                # Source is category pool
                self.stage_changed.emit("正在获取精选壁纸信息...")
                
                def on_progress(cur: int, tot: int, pct: int) -> None:
                    if not self._is_cancelled:
                        self.download_progress.emit(cur, tot, pct)

                item = api_client.fetch_random_from_category_pool(
                    self.category_ids,
                    progress_callback=on_progress,
                    cancel_check=lambda: self._is_cancelled,
                )
                if not item or not item.get("local_path") or not Path(item["local_path"]).exists():
                    self.finished_error.emit("获取壁纸失败，请重试")
                    return

            if self._is_cancelled:
                return

            # 2. Set Wallpaper via Windows API
            self.stage_changed.emit("正在应用到 Windows 桌面...")
            style = config.wallpaper_style
            local_file = item["local_path"]
            
            success = wallpaper_setter.apply_wallpaper(local_file, style)
            if not success:
                self.finished_error.emit("设置 Windows 壁纸失败")
                return

            # 3. Record in Database & Config
            db.add_history(item)
            config.last_wallpaper = item

            self.stage_changed.emit("壁纸更换成功！")
            self.finished_success.emit(item)
        except Exception as e:
            self.finished_error.emit(f"更换壁纸发生异常: {e}")


class WallpaperScheduler(QObject):
    """Coordinates automatic wallpaper rotation and manual triggers."""

    countdown_tick = Signal(int, int)  # remaining_seconds, total_seconds
    status_changed = Signal(bool)  # is_running
    stage_changed = Signal(str)  # current status text
    download_progress = Signal(int, int, int)  # cur, total, percent
    wallpaper_applied = Signal(dict)  # wallpaper metadata
    error_occurred = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setInterval(1000)  # 1 second tick
        self._timer.timeout.connect(self._on_tick)

        self._is_running = False
        self._total_seconds = config.auto_switch_interval
        self._remaining_seconds = self._total_seconds
        self._current_worker: WallpaperSwitchWorker | None = None
        self._retiring_workers: set[WallpaperSwitchWorker] = set()

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start_if_enabled(self) -> None:
        """Starts auto-switch if enabled in config and timer not already running."""
        if config.auto_switch_enabled and not self._is_running:
            self.start()

    def start(self) -> None:
        """Starts the auto rotation timer."""
        self._total_seconds = max(10, config.auto_switch_interval)
        self._remaining_seconds = self._total_seconds
        self._is_running = True
        config.auto_switch_enabled = True
        if not self._timer.isActive():
            self._timer.start()
        self.status_changed.emit(True)
        self.countdown_tick.emit(self._remaining_seconds, self._total_seconds)

    def stop(self) -> None:
        """Stops the auto rotation timer."""
        self._is_running = False
        config.auto_switch_enabled = False
        self._timer.stop()
        self.status_changed.emit(False)

    def reset_timer(self) -> None:
        """Resets countdown to full interval."""
        self._total_seconds = max(10, config.auto_switch_interval)
        self._remaining_seconds = self._total_seconds
        self.countdown_tick.emit(self._remaining_seconds, self._total_seconds)

    def set_interval(self, seconds: int) -> None:
        """Updates rotation interval."""
        config.auto_switch_interval = seconds
        self._total_seconds = seconds
        self._remaining_seconds = seconds
        self.countdown_tick.emit(self._remaining_seconds, self._total_seconds)

    def _on_tick(self) -> None:
        if not self._is_running:
            return

        self._remaining_seconds -= 1
        self.countdown_tick.emit(self._remaining_seconds, self._total_seconds)

        if self._remaining_seconds <= 0:
            self._remaining_seconds = self._total_seconds
            self.trigger_switch(source=config.auto_switch_source)

    def trigger_switch(
        self,
        source: str = "categories",
        category_ids: list[str] | None = None,
        specific_item: dict[str, Any] | None = None,
    ) -> None:
        """Triggers a wallpaper switch immediately and safely without destroying running threads."""
        if self._current_worker and self._current_worker.isRunning():
            old_worker = self._current_worker
            self._retiring_workers.add(old_worker)
            try:
                old_worker.stage_changed.disconnect()
                old_worker.download_progress.disconnect()
                old_worker.finished_success.disconnect()
                old_worker.finished_error.disconnect()
            except Exception:
                pass
            old_worker.finished.connect(lambda w=old_worker: self._cleanup_worker(w))
            old_worker.cancel()

        # Reset timer counter after a manual or auto switch
        self._remaining_seconds = self._total_seconds

        worker = WallpaperSwitchWorker(
            source=source,
            category_ids=category_ids or config.selected_categories,
            specific_item=specific_item,
        )
        self._current_worker = worker

        worker.stage_changed.connect(self.stage_changed.emit)
        worker.download_progress.connect(self.download_progress.emit)
        worker.finished_success.connect(self._on_switch_success)
        worker.finished_error.connect(self._on_switch_error)
        worker.finished.connect(lambda w=worker: self._cleanup_worker(w))
        worker.start()

    def _cleanup_worker(self, worker: WallpaperSwitchWorker) -> None:
        self._retiring_workers.discard(worker)
        if self._current_worker is worker:
            self._current_worker = None
        worker.deleteLater()

    def _on_switch_success(self, item: dict[str, Any]) -> None:
        self.wallpaper_applied.emit(item)

    def _on_switch_error(self, err_msg: str) -> None:
        self.error_occurred.emit(err_msg)


# Global singleton instance
scheduler = WallpaperScheduler()
