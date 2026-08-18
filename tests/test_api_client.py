"""Unit tests for API client and caching."""

from app.core.api_client import WallpaperApiClient
from app.core.cache_manager import CacheManager
from app.constants import CATEGORIES


def test_api_client_category():
    client = WallpaperApiClient()
    # Test fetching 4K category
    res = client.get_category_wallpapers("36", start=0, count=5)
    assert "items" in res
    assert len(res["items"]) > 0
    first = res["items"][0]
    assert "url" in first or "url_thumb" in first
    assert first.get("category_name") == "4K专区"


def test_api_client_search():
    client = WallpaperApiClient()
    res = client.search_wallpapers("风景", start=0, count=5)
    assert "items" in res
    assert len(res["items"]) > 0


def test_api_client_random():
    client = WallpaperApiClient()
    res = client.fetch_random_from_360("36")
    assert res is not None
    assert "url" in res
    assert res.get("category_id") == "36"
    assert res.get("local_path") is not None


def test_api_client_latest():
    client = WallpaperApiClient()
    latest = client.get_latest_wallpapers(start=0, count=3)
    assert "items" in latest
    assert len(latest["items"]) > 0


def test_api_client_pool():
    client = WallpaperApiClient()
    res = client.fetch_random_from_category_pool(["36", "9"])
    assert res is not None
    assert "url" in res
    assert res.get("category_id") in ["36", "9"]



def test_cache_manager_hash():
    mgr = CacheManager()
    h1 = mgr.get_url_hash("http://example.com/test.jpg")
    h2 = mgr.get_url_hash("http://example.com/test.jpg")
    assert h1 == h2
    assert len(h1) == 32

