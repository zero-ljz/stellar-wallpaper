"""SQLite database storage for Wallpaper History and Favorites."""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from ..constants import DB_PATH


class DatabaseManager:
    """Manages SQLite storage for wallpaper history and favorites."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or DB_PATH
        self._local = threading.local()
        self._lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "connection") or self._local.connection is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self._local.connection = conn
        return self._local.connection

    def close(self) -> None:
        if hasattr(self._local, "connection") and self._local.connection is not None:
            try:
                self._local.connection.close()
            except Exception:
                pass
            self._local.connection = None

    def _init_db(self) -> None:
        with self._lock:
            conn = self._get_connection()
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        wallpaper_id TEXT,
                        title TEXT,
                        url TEXT,
                        thumb_url TEXT,
                        local_path TEXT,
                        category_id TEXT,
                        category_name TEXT,
                        resolution TEXT,
                        tag TEXT,
                        applied_at TEXT
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS favorites (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        wallpaper_id TEXT UNIQUE,
                        title TEXT,
                        url TEXT,
                        thumb_url TEXT,
                        local_path TEXT,
                        category_id TEXT,
                        category_name TEXT,
                        resolution TEXT,
                        tag TEXT,
                        created_at TEXT
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_history_applied_at ON history(applied_at DESC)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_favorites_created_at ON favorites(created_at DESC)")

    # History operations
    def add_history(self, item: dict[str, Any]) -> int:
        with self._lock:
            conn = self._get_connection()
            with conn:
                cur = conn.execute(
                    """
                    INSERT INTO history (
                        wallpaper_id, title, url, thumb_url, local_path,
                        category_id, category_name, resolution, tag, applied_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(item.get("id") or item.get("wallpaper_id") or ""),
                        item.get("title") or item.get("tag") or "壁纸",
                        item.get("url") or "",
                        item.get("thumb_url") or item.get("url_thumb") or item.get("url") or "",
                        item.get("local_path") or "",
                        str(item.get("category_id") or item.get("class_id") or ""),
                        item.get("category_name") or "",
                        item.get("resolution") or "",
                        item.get("tag") or "",
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
                return cur.lastrowid or 0

    def get_history(self, limit: int | None = None, offset: int = 0) -> list[dict[str, Any]]:
        conn = self._get_connection()
        if limit is not None and limit > 0:
            cur = conn.execute(
                """
                SELECT * FROM history ORDER BY id DESC LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
        else:
            cur = conn.execute("SELECT * FROM history ORDER BY id DESC")
        return [dict(row) for row in cur.fetchall()]

    def clear_history(self) -> None:
        with self._lock:
            conn = self._get_connection()
            with conn:
                conn.execute("DELETE FROM history")

    def count_history(self) -> int:
        conn = self._get_connection()
        cur = conn.execute("SELECT COUNT(*) FROM history")
        return cur.fetchone()[0]

    # Favorites operations
    def add_favorite(self, item: dict[str, Any]) -> bool:
        with self._lock:
            conn = self._get_connection()
            try:
                wid = str(item.get("wallpaper_id") or item.get("id") or item.get("url") or "")
                with conn:
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO favorites (
                            wallpaper_id, title, url, thumb_url, local_path,
                            category_id, category_name, resolution, tag, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            wid,
                            item.get("title") or item.get("tag") or "壁纸",
                            item.get("url") or "",
                            item.get("thumb_url") or item.get("url_thumb") or item.get("url") or "",
                            item.get("local_path") or "",
                            str(item.get("category_id") or item.get("class_id") or ""),
                            item.get("category_name") or "",
                            item.get("resolution") or "",
                            item.get("tag") or "",
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        ),
                    )
                return True
            except Exception as e:
                print(f"Failed to add favorite: {e}")
                return False

    def remove_favorite(self, wallpaper_id_or_url: str = "", url: str = "") -> bool:
        keys = [str(k).strip() for k in (wallpaper_id_or_url, url) if str(k).strip()]
        if not keys:
            return False
        with self._lock:
            conn = self._get_connection()
            with conn:
                placeholders = " OR ".join(["wallpaper_id = ? OR url = ? OR id = ?"] * len(keys))
                params = []
                for k in keys:
                    params.extend([k, k, k])
                cur = conn.execute(f"DELETE FROM favorites WHERE {placeholders}", params)
                return cur.rowcount > 0

    def is_favorite(self, wallpaper_id_or_url: str = "", url: str = "") -> bool:
        keys = [str(k).strip() for k in (wallpaper_id_or_url, url) if str(k).strip()]
        if not keys:
            return False
        conn = self._get_connection()
        placeholders = " OR ".join(["wallpaper_id = ? OR url = ? OR id = ?"] * len(keys))
        params = []
        for k in keys:
            params.extend([k, k, k])
        cur = conn.execute(f"SELECT 1 FROM favorites WHERE {placeholders} LIMIT 1", params)
        return cur.fetchone() is not None

    def get_favorites(self, limit: int | None = None, offset: int = 0) -> list[dict[str, Any]]:
        conn = self._get_connection()
        if limit is not None and limit > 0:
            cur = conn.execute(
                """
                SELECT * FROM favorites ORDER BY id DESC LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
        else:
            cur = conn.execute("SELECT * FROM favorites ORDER BY id DESC")
        items = []
        for row in cur.fetchall():
            d = dict(row)
            wid = d.get("wallpaper_id")
            if wid:
                d["id"] = wid
            items.append(d)
        return items

    def get_random_favorite(self) -> dict[str, Any] | None:
        conn = self._get_connection()
        cur = conn.execute("SELECT * FROM favorites ORDER BY RANDOM() LIMIT 1")
        row = cur.fetchone()
        if not row:
            return None
        d = dict(row)
        wid = d.get("wallpaper_id")
        if wid:
            d["id"] = wid
        return d

    def count_favorites(self) -> int:
        conn = self._get_connection()
        cur = conn.execute("SELECT COUNT(*) FROM favorites")
        return cur.fetchone()[0]


# Global singleton instance
db = DatabaseManager()
