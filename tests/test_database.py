"""Unit tests for SQLite database manager."""

import tempfile
from pathlib import Path

from app.core.database import DatabaseManager


def test_database_history_crud():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = Path(tmpdir) / "test.db"
        db = DatabaseManager(db_file)

        assert db.count_history() == 0

        # Add history item
        item = {
            "id": "1001",
            "title": "测试4K风景",
            "url": "http://example.com/pic1-preview.jpg",
            "download_url": "http://example.com/pic1-original.jpg",
            "category_id": "36",
            "category_name": "4K专区",
            "resolution": "3840x2160",
            "tag": "风景_森林",
            "local_path": "C:/tmp/pic1.jpg",
        }
        hid = db.add_history(item)
        assert hid > 0
        assert db.count_history() == 1

        history = db.get_history()
        assert len(history) == 1
        assert history[0]["title"] == "测试4K风景"
        assert history[0]["category_name"] == "4K专区"
        assert history[0]["url"] == "http://example.com/pic1-original.jpg"

        # Clear history
        db.clear_history()
        assert db.count_history() == 0
        db.close()


def test_database_favorites_crud():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = Path(tmpdir) / "test.db"
        db = DatabaseManager(db_file)

        assert db.count_favorites() == 0

        item = {
            "id": "2001",
            "title": "二次元动漫美图",
            "url": "http://example.com/anime-preview.jpg",
            "download_url": "http://example.com/anime-original.jpg",
            "category_id": "26",
            "category_name": "动漫卡通",
            "resolution": "1920x1080",
        }

        ok = db.add_favorite(item)
        assert ok is True
        assert db.count_favorites() == 1
        assert db.is_favorite("2001") is True
        assert db.is_favorite("9999") is False

        favs = db.get_favorites()
        assert len(favs) == 1
        assert favs[0]["title"] == "二次元动漫美图"
        assert favs[0]["url"] == "http://example.com/anime-original.jpg"

        # Random favorite
        rand_fav = db.get_random_favorite()
        assert rand_fav is not None
        assert rand_fav["wallpaper_id"] == "2001"

        # Remove
        removed = db.remove_favorite("2001")
        assert removed is True
        assert db.count_favorites() == 0
        assert db.is_favorite("2001") is False
        db.close()
