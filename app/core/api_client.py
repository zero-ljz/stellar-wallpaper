"""API Client for 360 Official Wallpaper endpoints with async downloading."""

from __future__ import annotations

import json
import random
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

from ..constants import (
    API_360_CATEGORY,
    API_360_ORDER,
    API_360_SEARCH,
    CATEGORIES,
    CATEGORY_MAP,
    DEFAULT_USER_AGENT,
)
from .cache_manager import cache_mgr


def format_360_item(item: dict[str, Any], default_cat_name: str = "壁纸") -> dict[str, Any]:
    """Format and enrich raw 360 wallpaper API item with clean titles and category metadata."""
    cat_id = str(item.get("class_id") or item.get("category_id") or "")
    cat_name = CATEGORY_MAP.get(cat_id, default_cat_name)
    item["category_id"] = cat_id
    item["category_name"] = cat_name

    raw_tag = item.get("tag", "") or ""
    if not item.get("title") or "_category_" in item.get("title", "") or "_360Wallpaper_" in item.get("title", ""):
        cleaned = raw_tag.replace("_360Wallpaper_", "").replace("_category_", " ").replace("_", " ")
        parts = [p.strip() for p in cleaned.split() if p.strip() and p.strip() != "全部"]
        if parts:
            item["title"] = " · ".join(parts[:3])
        else:
            item["title"] = f"{cat_name} #{item.get('id', '')}"
    return item


class WallpaperApiClient:
    """Handles communication with official 360 wallpaper endpoints."""

    def __init__(self, timeout: int = 15) -> None:
        self.timeout = timeout
        self.user_agent = DEFAULT_USER_AGENT

    def _create_request(self, url: str) -> urllib.request.Request:
        return urllib.request.Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "*/*",
                "Referer": "http://wallpaper.apc.360.cn/",
            },
        )

    def get_category_wallpapers(
        self,
        category_id: str,
        start: int = 0,
        count: int = 24,
    ) -> dict[str, Any]:
        """Fetch a page of wallpapers from a specific 360 category."""
        url = f"{API_360_CATEGORY}&cid={category_id}&start={start}&count={count}&from=360chrome"
        req = self._create_request(url)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                content = resp.read().decode("utf-8")
                data = json.loads(content)
                items = data.get("data", [])
                total = int(data.get("total", len(items)))

                cat_name = CATEGORY_MAP.get(str(category_id), "壁纸")
                for item in items:
                    format_360_item(item, default_cat_name=cat_name)

                return {
                    "total": total,
                    "items": items,
                    "start": start,
                    "count": count,
                }
        except Exception as e:
            print(f"Error fetching 360 category {category_id}: {e}")
            return {"total": 0, "items": [], "start": start, "count": count, "error": str(e)}

    def get_latest_wallpapers(
        self,
        start: int = 0,
        count: int = 24,
    ) -> dict[str, Any]:
        """Fetch latest wallpapers ordered by upload time."""
        url = f"{API_360_ORDER}&order=create_time&start={start}&count={count}&from=360chrome"
        req = self._create_request(url)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                content = resp.read().decode("utf-8")
                data = json.loads(content)
                items = data.get("data", [])
                total = int(data.get("total", len(items)))

                for item in items:
                    format_360_item(item, default_cat_name="最新壁纸")

                return {
                    "total": total,
                    "items": items,
                    "start": start,
                    "count": count,
                }
        except Exception as e:
            print(f"Error fetching latest wallpapers: {e}")
            return {"total": 0, "items": [], "start": start, "count": count, "error": str(e)}

    def search_wallpapers(
        self,
        keyword: str,
        start: int = 0,
        count: int = 24,
    ) -> dict[str, Any]:
        """Search wallpapers by keyword or tag."""
        # Check if keyword matches a category directly
        for cat in CATEGORIES:
            if keyword in cat["name"] or cat["name"] in keyword:
                return self.get_category_wallpapers(cat["id"], start, count)

        encoded_kw = urllib.parse.quote(keyword)
        url = f"{API_360_SEARCH}&tags={encoded_kw}&start={start}&count={count}&from=360chrome"
        req = self._create_request(url)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                content = resp.read().decode("utf-8")
                data = json.loads(content)
                items = data.get("data", [])
                total = int(data.get("total", len(items)))

                for item in items:
                    format_360_item(item, default_cat_name=f"搜索: {keyword}")

                return {
                    "total": total,
                    "items": items,
                    "start": start,
                    "count": count,
                }
        except Exception as e:
            print(f"Error searching keyword '{keyword}': {e}")
            return {"total": 0, "items": [], "start": start, "count": count, "error": str(e)}

    def download_image(
        self,
        url: str,
        target_path: Path,
        progress_callback: Callable[[int, int, int], None] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> bool:
        """
        Downloads an image from URL to target_path with chunked streaming and progress callback.
        progress_callback(downloaded_bytes, total_bytes, percentage_0_to_100)
        """
        if not url:
            return False

        target_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = target_path.with_suffix(".tmp")

        try:
            req = self._create_request(url)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                total_size = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 32 * 1024  # 32 KB

                with open(temp_path, "wb") as f:
                    while True:
                        if cancel_check and cancel_check():
                            temp_path.unlink(missing_ok=True)
                            return False

                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break

                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_size > 0:
                            percent = min(100, int(downloaded * 100 / total_size))
                        else:
                            percent = min(99, downloaded // (50 * 1024))

                        if progress_callback:
                            progress_callback(downloaded, total_size, percent)

                # Move temp to final
                if temp_path.exists():
                    temp_path.replace(target_path)
                    if progress_callback:
                        progress_callback(downloaded, total_size or downloaded, 100)
                    return True
                return False
        except Exception as e:
            print(f"Download failed for {url}: {e}")
            temp_path.unlink(missing_ok=True)
            return False

    def fetch_random_from_360(
        self,
        category_id: str | None = None,
        progress_callback: Callable[[int, int, int], None] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> dict[str, Any] | None:
        """
        Fetches a random HD wallpaper directly from 360 official category pool.
        """
        if not category_id:
            category_id = random.choice(CATEGORIES)["id"]

        category_name = CATEGORY_MAP.get(str(category_id), "4K专区")

        # 360 categories have many items; pick a random offset between 0 and 150
        random_start = random.randint(0, 150)
        page = self.get_category_wallpapers(category_id, start=random_start, count=20)
        items = page.get("items", [])

        if not items:
            # Fallback: query from start=0
            page = self.get_category_wallpapers(category_id, start=0, count=20)
            items = page.get("items", [])

        if not items:
            return None

        # Try up to 3 candidate items in case of a CDN download timeout
        shuffled = list(items)
        random.shuffle(shuffled)
        for item in shuffled[:3]:
            img_url = item.get("url") or item.get("url_mid") or item.get("url_thumb")
            if not img_url:
                continue

            target_path = cache_mgr.get_wallpaper_path(img_url)
            success = self.download_image(
                img_url,
                target_path,
                progress_callback=progress_callback,
                cancel_check=cancel_check,
            )

            if success:
                item["local_path"] = str(target_path)
                item["category_id"] = str(category_id)
                item["category_name"] = category_name
                return item

        return None

    def fetch_random_from_category_pool(
        self,
        category_ids: list[str],
        progress_callback: Callable[[int, int, int], None] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> dict[str, Any] | None:
        """
        Picks a random category from the user's selected category IDs and fetches
        an HD wallpaper directly from the 360 official repository.
        """
        if not category_ids:
            category_ids = [c["id"] for c in CATEGORIES]

        selected_cat_id = random.choice(category_ids)
        return self.fetch_random_from_360(
            selected_cat_id,
            progress_callback=progress_callback,
            cancel_check=cancel_check,
        )


# Global singleton instance
api_client = WallpaperApiClient()

