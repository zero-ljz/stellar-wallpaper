"""Asynchronous image and thumbnail loading service with caching and concurrency control."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot
from PySide6.QtGui import QImage, QPixmap

from .api_client import api_client
from .cache_manager import cache_mgr


class ImageLoader(QObject):
    """Central manager for async image and thumbnail loading with thread pool."""

    image_loaded = Signal(str, QPixmap)  # url, pixmap
    _internal_image_ready = Signal(str, QImage)  # key, QImage across threads

    def __init__(self, max_threads: int = 6, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.pool = QThreadPool.globalInstance()
        self.pool.setMaxThreadCount(max_threads)
        self._lock = threading.Lock()
        self._callbacks: dict[str, list[Callable[[QPixmap], None]]] = {}
        self._internal_image_ready.connect(self._handle_internal_image_ready)

    def load_thumbnail(
        self,
        url: str,
        local_path: str = "",
        callback: Callable[[QPixmap], None] | None = None,
    ) -> None:
        """Loads thumbnail asynchronously from local file, cache, or remote URL."""
        if not url and not local_path:
            if callback:
                callback(QPixmap())
            return

        key = url or local_path
        if callback:
            with self._lock:
                if key not in self._callbacks:
                    self._callbacks[key] = []
                self._callbacks[key].append(callback)

        emitter = self

        class ThumbTask(QRunnable):
            def __init__(self, u: str, lp: str, k: str) -> None:
                super().__init__()
                self.u = u
                self.lp = lp
                self.k = k
                self.setAutoDelete(True)

            def run(self) -> None:
                try:
                    # 1. Local path
                    if self.lp and Path(self.lp).exists():
                        img = QImage(self.lp)
                        if not img.isNull():
                            emitter._internal_image_ready.emit(self.k, img)
                            return

                    # 2. Cached thumbnail
                    if self.u:
                        cached = cache_mgr.get_thumb_path(self.u)
                        if cached.exists() and cached.stat().st_size > 0:
                            img = QImage(str(cached))
                            if not img.isNull():
                                emitter._internal_image_ready.emit(self.k, img)
                                return

                        # 3. Download to cache
                        ok = api_client.download_image(self.u, cached)
                        if ok and cached.exists():
                            img = QImage(str(cached))
                            if not img.isNull():
                                emitter._internal_image_ready.emit(self.k, img)
                                return

                    emitter._internal_image_ready.emit(self.k, QImage())
                except Exception:
                    try:
                        emitter._internal_image_ready.emit(self.k, QImage())
                    except Exception:
                        pass

        task = ThumbTask(url, local_path, key)
        self.pool.start(task)

    def load_full_image(
        self,
        url: str,
        local_path: str = "",
        callback: Callable[[QPixmap], None] | None = None,
    ) -> None:
        """Loads full resolution image asynchronously."""
        if not url and not local_path:
            if callback:
                callback(QPixmap())
            return

        key = f"full_{url or local_path}"
        if callback:
            with self._lock:
                if key not in self._callbacks:
                    self._callbacks[key] = []
                self._callbacks[key].append(callback)

        emitter = self

        class FullTask(QRunnable):
            def __init__(self, u: str, lp: str, k: str) -> None:
                super().__init__()
                self.u = u
                self.lp = lp
                self.k = k
                self.setAutoDelete(True)

            def run(self) -> None:
                try:
                    if self.lp and Path(self.lp).exists():
                        img = QImage(self.lp)
                        if not img.isNull():
                            emitter._internal_image_ready.emit(self.k, img)
                            return

                    if self.u:
                        cached = cache_mgr.get_wallpaper_path(self.u)
                        if cached.exists() and cached.stat().st_size > 0:
                            img = QImage(str(cached))
                            if not img.isNull():
                                emitter._internal_image_ready.emit(self.k, img)
                                return

                        ok = api_client.download_image(self.u, cached)
                        if ok and cached.exists():
                            img = QImage(str(cached))
                            if not img.isNull():
                                emitter._internal_image_ready.emit(self.k, img)
                                return

                    emitter._internal_image_ready.emit(self.k, QImage())
                except Exception:
                    try:
                        emitter._internal_image_ready.emit(self.k, QImage())
                    except Exception:
                        pass

        task = FullTask(url, local_path, key)
        self.pool.start(task)

    @Slot(str, QImage)
    def _handle_internal_image_ready(self, key: str, img: QImage) -> None:
        """Receives QImage on the main GUI thread, converts to QPixmap and executes UI callbacks."""
        try:
            pixmap = QPixmap.fromImage(img) if not img.isNull() else QPixmap()
            self.image_loaded.emit(key, pixmap)
            with self._lock:
                callbacks = self._callbacks.pop(key, [])
            for cb in callbacks:
                try:
                    cb(pixmap)
                except Exception:
                    pass
        except RuntimeError:
            pass  # Suppress cleanup race during app teardown


# Global singleton instance
image_loader = ImageLoader()
