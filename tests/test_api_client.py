"""Unit tests for API client and caching."""

from app.core.api_client import (
    WallpaperApiClient,
    format_360_item,
    format_bing_archive_item,
    format_bing_item,
    format_picsum_item,
    get_full_image_url,
)
from app.core.cache_manager import CacheManager


def test_format_picsum_item_download_matches_displayed_resolution():
    item = format_picsum_item(
        {
            "id": "42",
            "author": "Test Photographer",
            "width": 5000,
            "height": 3333,
            "download_url": "https://picsum.photos/id/42/5000/3333",
        }
    )

    assert item["resolution"] == "5000×3333"
    assert item["url"] == "https://picsum.photos/id/42/5000/3333"
    assert item["download_url"] == item["url"]
    assert item["url_thumb"] == "https://picsum.photos/id/42/500/280"


def test_format_picsum_item_builds_full_resolution_url_when_missing():
    item = format_picsum_item({"id": "7", "width": 4312, "height": 2875})

    assert item["resolution"] == "4312×2875"
    assert item["url"] == "https://picsum.photos/id/7/4312/2875"


def test_all_sources_expose_their_original_download_url():
    item_360 = format_360_item(
        {
            "id": "1",
            "url": "https://example.com/360-original.jpg",
            "url_mid": "https://example.com/360-medium.jpg",
        }
    )
    bing = format_bing_item({"urlbase": "/th?id=OHR.Test_ZH-CN123"})
    bing_archive = format_bing_archive_item(
        {
            "date": "2026-08-19",
            "bing_url": "https://bing.com/th?id=OHR.Test_ZH-CN123_UHD.jpg",
            "url": "https://example.com/bing-thumbnail.jpg",
        }
    )

    assert get_full_image_url(item_360) == "https://example.com/360-original.jpg"
    assert get_full_image_url(bing).endswith("_UHD.jpg")
    assert get_full_image_url(bing_archive).endswith("_UHD.jpg")


def test_full_image_url_prefers_download_url_over_preview_variants():
    item = {
        "download_url": "https://example.com/original.jpg",
        "url": "https://example.com/default.jpg",
        "url_mid": "https://example.com/medium.jpg",
    }

    assert get_full_image_url(item) == "https://example.com/original.jpg"


def test_full_image_url_upgrades_legacy_picsum_record():
    legacy_item = {
        "wallpaper_id": "picsum_42",
        "category_id": "picsum",
        "resolution": "5000×3333",
        "url": "https://picsum.photos/id/42/2560/1440",
    }

    assert get_full_image_url(legacy_item) == "https://picsum.photos/id/42/5000/3333"


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


def test_api_client_bing():
    client = WallpaperApiClient()
    res = client.get_bing_wallpapers(start=0, count=4)
    assert "items" in res
    assert len(res["items"]) > 0
    assert res.get("total", 0) >= 800
    first = res["items"][0]
    assert first.get("category_id") == "bing"
    assert first.get("category_name") == "必应壁纸"
    assert "url" in first
    assert "url_thumb" in first
    assert "title" in first
    assert "date" in first

    # Test pagination further in history (e.g. page 2)
    res_page2 = client.get_bing_wallpapers(start=4, count=4)
    assert len(res_page2["items"]) > 0
    assert res_page2["items"][0]["id"] != first["id"]


def test_api_client_picsum():
    client = WallpaperApiClient()
    # Ascending
    res_asc = client.get_picsum_wallpapers(start=0, count=4, sort_order="asc")
    assert "items" in res_asc
    assert len(res_asc["items"]) > 0
    first_asc = res_asc["items"][0]
    assert first_asc.get("category_id") == "picsum"
    assert first_asc.get("category_name") == "Picsum 图库"
    assert "url" in first_asc
    assert "url_thumb" in first_asc
    assert "author" in first_asc

    # Descending
    res_desc = client.get_picsum_wallpapers(start=0, count=4, sort_order="desc")
    assert "items" in res_desc
    assert len(res_desc["items"]) > 0
    first_desc = res_desc["items"][0]
    assert first_desc.get("category_id") == "picsum"
    # In desc order, the ID is different from asc (e.g. 1084 vs 0)
    assert first_desc.get("id") != first_asc.get("id")

    # Random
    res_rand = client.get_picsum_wallpapers(start=0, count=4, sort_order="random")
    assert "items" in res_rand
    assert len(res_rand["items"]) > 0


def test_api_client_category_routing():
    client = WallpaperApiClient()
    bing_res = client.get_category_wallpapers("bing", start=0, count=2)
    assert len(bing_res["items"]) > 0
    assert bing_res["items"][0]["category_id"] == "bing"

    picsum_res = client.get_category_wallpapers("picsum", start=0, count=2)
    assert len(picsum_res["items"]) > 0
    assert picsum_res["items"][0]["category_id"] == "picsum"


def test_api_client_search_routing():
    client = WallpaperApiClient()
    res_bing = client.search_wallpapers("必应", start=0, count=2)
    assert len(res_bing["items"]) > 0
    assert res_bing["items"][0]["category_id"] == "bing"

    res_picsum = client.search_wallpapers("picsum", start=0, count=2)
    assert len(res_picsum["items"]) > 0
    assert res_picsum["items"][0]["category_id"] == "picsum"


def test_api_client_random_bing():
    client = WallpaperApiClient()
    res = client.fetch_random_from_bing()
    assert res is not None
    assert res.get("category_id") == "bing"
    assert res.get("local_path") is not None


def test_api_client_random_picsum():
    client = WallpaperApiClient()
    res = client.fetch_random_from_picsum()
    assert res is not None
    assert res.get("category_id") == "picsum"
    assert res.get("local_path") is not None


def test_cache_manager_hash():
    mgr = CacheManager()
    h1 = mgr.get_url_hash("http://example.com/test.jpg")
    h2 = mgr.get_url_hash("http://example.com/test.jpg")
    assert h1 == h2
    assert len(h1) == 32
