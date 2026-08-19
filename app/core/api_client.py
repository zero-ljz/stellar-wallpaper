"""API Client for 360 Official Wallpaper endpoints with async downloading."""

from __future__ import annotations

import json
import random
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

from ..constants import (
    API_360_CATEGORY,
    API_360_ORDER,
    API_360_SEARCH,
    API_BING_ARCHIVE,
    API_BING_BASE,
    API_PICSUM_BASE,
    CATEGORIES,
    CATEGORY_MAP,
    DEFAULT_USER_AGENT,
)
from .cache_manager import cache_mgr
from .database import db


def format_360_item(item: dict[str, Any], default_cat_name: str = "壁纸") -> dict[str, Any]:
    """Format and enrich raw 360 wallpaper API item with clean titles and category metadata."""
    cat_id = str(item.get("class_id") or item.get("category_id") or "")
    cat_name = CATEGORY_MAP.get(cat_id, default_cat_name)
    item["category_id"] = cat_id
    item["category_name"] = cat_name
    item["download_url"] = item.get("download_url") or item.get("url") or ""

    raw_tag = item.get("tag", "") or ""
    if not item.get("title") or "_category_" in item.get("title", "") or "_360Wallpaper_" in item.get("title", ""):
        cleaned = raw_tag.replace("_360Wallpaper_", "").replace("_category_", " ").replace("_", " ")
        parts = [p.strip() for p in cleaned.split() if p.strip() and p.strip() != "全部"]
        if parts:
            item["title"] = " · ".join(parts[:3])
        else:
            item["title"] = f"{cat_name} #{item.get('id', '')}"
    return item


def format_bing_item(img: dict[str, Any]) -> dict[str, Any]:
    """Format and enrich Bing daily wallpaper API item."""
    urlbase = img.get("urlbase", "")
    url_raw = img.get("url", "")

    if urlbase:
        full_url = f"https://cn.bing.com{urlbase}_UHD.jpg"
        thumb_url = f"https://cn.bing.com{urlbase}_800x480.jpg"
    else:
        full_url = f"https://cn.bing.com{url_raw}" if url_raw.startswith("/") else url_raw
        thumb_url = full_url

    title = img.get("title") or ""
    copyright_str = img.get("copyright") or ""
    if not title:
        title = copyright_str.split("(")[0].strip() or "必应每日壁纸"

    date_str = img.get("enddate") or img.get("startdate") or ""
    if len(date_str) == 8:
        formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    else:
        formatted_date = date_str

    hsh = img.get("hsh", "") or str(abs(hash(full_url)))
    wid = f"bing_{date_str}_{hsh[:8]}"

    return {
        "id": wid,
        "wallpaper_id": wid,
        "title": title,
        "tag": copyright_str,
        "category_id": "bing",
        "category_name": "必应壁纸",
        "resolution": "3840×2160 4K",
        "url": full_url,
        "download_url": full_url,
        "url_thumb": thumb_url,
        "url_mid": thumb_url,
        "thumb_url": thumb_url,
        "copyright": copyright_str,
        "date": formatted_date,
    }


def format_bing_archive_item(item: dict[str, Any]) -> dict[str, Any]:
    """Format and enrich historical Bing archive wallpaper item."""
    date_str = item.get("date", "")
    clean_date = date_str.replace("-", "")
    title = item.get("title") or item.get("caption") or "必应历史精选壁纸"
    subtitle = item.get("subtitle") or ""
    copyright_str = item.get("copyright") or ""
    tag_str = f"{subtitle} · {copyright_str}".strip(" · ") if subtitle else copyright_str

    bing_url = item.get("bing_url") or ""
    thumb_url = item.get("url") or bing_url
    wid = f"bing_hist_{clean_date}"

    return {
        "id": wid,
        "wallpaper_id": wid,
        "title": title,
        "tag": tag_str,
        "description": item.get("description", ""),
        "category_id": "bing",
        "category_name": "必应壁纸",
        "resolution": "3840×2160 4K",
        "url": bing_url or thumb_url,
        "download_url": bing_url or thumb_url,
        "url_thumb": thumb_url,
        "url_mid": thumb_url,
        "thumb_url": thumb_url,
        "copyright": copyright_str,
        "date": date_str,
    }


def format_picsum_item(photo: dict[str, Any]) -> dict[str, Any]:
    """Format and enrich Lorem Picsum photos item."""
    photo_id = str(photo.get("id", ""))
    author = photo.get("author", "Lorem Picsum")
    width = int(photo.get("width") or 2560)
    height = int(photo.get("height") or 1440)
    # Picsum's list API reports the source image dimensions. Keep the download
    # URL at those dimensions too, otherwise the displayed resolution describes
    # the source while users receive a cropped 2560x1440 image.
    high_res_url = photo.get("download_url") or f"https://picsum.photos/id/{photo_id}/{width}/{height}"
    thumb_url = f"https://picsum.photos/id/{photo_id}/500/280"
    wid = f"picsum_{photo_id}"

    return {
        "id": wid,
        "wallpaper_id": wid,
        "title": f"摄影大片 · {author}",
        "tag": f"摄影师: {author}",
        "category_id": "picsum",
        "category_name": "Picsum 图库",
        "resolution": f"{width}×{height}",
        "url": high_res_url,
        "download_url": high_res_url,
        "url_thumb": thumb_url,
        "url_mid": thumb_url,
        "thumb_url": thumb_url,
        "author": author,
        "original_url": photo.get("url", ""),
    }


def get_full_image_url(item: dict[str, Any]) -> str:
    """Return the best available full-resolution image URL for any source."""
    download_url = item.get("download_url")
    if download_url:
        return str(download_url)

    # Favorites/history created before native Picsum downloads were introduced
    # only contain the old fixed 2560x1440 URL. Rebuild the native-size URL from
    # the metadata so those saved records also benefit from the fix.
    category_id = str(item.get("category_id") or item.get("class_id") or "")
    wallpaper_id = str(item.get("wallpaper_id") or item.get("id") or "")
    resolution = str(item.get("resolution") or "")
    if category_id == "picsum" or wallpaper_id.startswith("picsum_"):
        match = re.search(r"(\d+)\s*[x×]\s*(\d+)", resolution, re.IGNORECASE)
        photo_id = wallpaper_id.removeprefix("picsum_")
        if match and photo_id:
            width, height = match.groups()
            return f"https://picsum.photos/id/{photo_id}/{width}/{height}"

    return str(item.get("url") or item.get("url_mid") or "")


class WallpaperApiClient:
    """Handles communication with 360, Bing (Daily & Historical Archive), and Picsum wallpaper endpoints."""

    def __init__(self, timeout: int = 15) -> None:
        self.timeout = timeout
        self.user_agent = DEFAULT_USER_AGENT
        self._bing_archive_cache: list[dict[str, Any]] | None = None
        self._recent_random_ids: list[str] = []

    def _record_recent_random(self, wid: str) -> None:
        """Track recently selected wallpaper IDs in memory."""
        if not wid:
            return
        if wid in self._recent_random_ids:
            self._recent_random_ids.remove(wid)
        self._recent_random_ids.append(wid)
        if len(self._recent_random_ids) > 100:
            self._recent_random_ids = self._recent_random_ids[-100:]

    def _is_recently_used(self, item: dict[str, Any]) -> bool:
        """Check if an item was recently randomized or set in history database."""
        wid = str(item.get("id") or item.get("wallpaper_id") or "")
        url = get_full_image_url(item)
        if wid and wid in self._recent_random_ids:
            return True
        try:
            recent_history = db.get_history(limit=50)
            for h in recent_history:
                if (wid and str(h.get("wallpaper_id", "")) == wid) or (url and h.get("url") == url):
                    return True
        except Exception:
            pass
        return False

    def _create_request(self, url: str, referer: str | None = None) -> urllib.request.Request:
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "*/*",
        }
        if referer:
            headers["Referer"] = referer
        elif "360.cn" in url:
            headers["Referer"] = "http://wallpaper.apc.360.cn/"
        elif "bing.com" in url or "cn.bing.com" in url:
            headers["Referer"] = "https://cn.bing.com/"

        return urllib.request.Request(url, headers=headers)

    def _load_bing_historical_wallpapers(self, mkt: str = "zh-CN") -> list[dict[str, Any]]:
        """Fetch and merge both official latest Bing wallpapers and multi-year historical archive."""
        if self._bing_archive_cache is not None and len(self._bing_archive_cache) > 0:
            return self._bing_archive_cache

        official_items: list[dict[str, Any]] = []
        try:
            url = f"{API_BING_BASE}?format=js&idx=0&n=8&mkt={mkt}"
            req = self._create_request(url)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                content = resp.read().decode("utf-8")
                data = json.loads(content)
                for img in data.get("images", []):
                    official_items.append(format_bing_item(img))
        except Exception as e:
            print(f"Failed to fetch official Bing daily wallpapers: {e}")

        archive_items: list[dict[str, Any]] = []
        try:
            req = self._create_request(API_BING_ARCHIVE)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                content = resp.read().decode("utf-8")
                data = json.loads(content)
                if isinstance(data, list):
                    for raw in data:
                        archive_items.append(format_bing_archive_item(raw))
        except Exception as e:
            print(f"Failed to fetch Bing historical archive from {API_BING_ARCHIVE}: {e}")

        seen_dates = set()
        combined: list[dict[str, Any]] = []

        # 1. Official latest days first
        for it in official_items:
            d = it.get("date")
            if d and d not in seen_dates:
                seen_dates.add(d)
                combined.append(it)

        # 2. Historical archive days
        for it in archive_items:
            d = it.get("date")
            if d and d not in seen_dates:
                seen_dates.add(d)
                combined.append(it)
            elif not d:
                combined.append(it)

        # Sort descending by date
        combined.sort(key=lambda x: str(x.get("date", "")), reverse=True)

        self._bing_archive_cache = combined
        return self._bing_archive_cache

    def get_bing_wallpapers(
        self,
        start: int = 0,
        count: int = 24,
        mkt: str = "zh-CN",
    ) -> dict[str, Any]:
        """Fetch Bing wallpapers with full historical archive and pagination support."""
        all_items = self._load_bing_historical_wallpapers(mkt=mkt)
        total = len(all_items)
        sliced = all_items[start : start + count]

        return {
            "total": total,
            "items": sliced,
            "start": start,
            "count": count,
        }

    def get_picsum_wallpapers(
        self,
        start: int = 0,
        count: int = 24,
        sort_order: str = "asc",
    ) -> dict[str, Any]:
        """Fetch Lorem Picsum photos with pagination and sorting support (asc / desc / random)."""
        import math
        total_picsum = 993
        total_pages = max(1, math.ceil(total_picsum / max(1, count)))
        page = (start // max(1, count)) + 1

        if sort_order == "desc":
            target_page = max(1, total_pages - page + 1)
            url = f"{API_PICSUM_BASE}/v2/list?page={target_page}&limit={count}"
        elif sort_order == "random":
            random_page = random.randint(1, total_pages)
            url = f"{API_PICSUM_BASE}/v2/list?page={random_page}&limit={count}"
        else:
            # Default "asc" (正序)
            url = f"{API_PICSUM_BASE}/v2/list?page={page}&limit={count}"

        req = self._create_request(url)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                content = resp.read().decode("utf-8")
                raw_list = json.loads(content)
                if sort_order == "desc":
                    raw_list.reverse()
                elif sort_order == "random":
                    random.shuffle(raw_list)

                items = [format_picsum_item(photo) for photo in raw_list]

                return {
                    "total": total_picsum,
                    "items": items,
                    "start": start,
                    "count": count,
                }
        except Exception as e:
            print(f"Error fetching Picsum photos page {page}: {e}")
            return {"total": 0, "items": [], "start": start, "count": count, "error": str(e)}

    def get_category_wallpapers(
        self,
        category_id: str,
        start: int = 0,
        count: int = 24,
        sort_order: str = "asc",
    ) -> dict[str, Any]:
        """Fetch wallpapers by category ID (routes seamlessly to 360, Bing, or Picsum)."""
        cid = str(category_id)
        if cid == "bing":
            return self.get_bing_wallpapers(start=start, count=count)
        elif cid == "picsum":
            return self.get_picsum_wallpapers(start=start, count=count, sort_order=sort_order)
        elif cid == "latest":
            return self.get_latest_wallpapers(start=start, count=count)

        # Official 360 category endpoints
        url = f"{API_360_CATEGORY}&cid={cid}&start={start}&count={count}&from=360chrome"
        req = self._create_request(url)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                content = resp.read().decode("utf-8")
                data = json.loads(content)
                items = data.get("data", [])
                total = int(data.get("total", len(items)))

                cat_name = CATEGORY_MAP.get(cid, "壁纸")
                for item in items:
                    format_360_item(item, default_cat_name=cat_name)

                return {
                    "total": total,
                    "items": items,
                    "start": start,
                    "count": count,
                }
        except Exception as e:
            print(f"Error fetching 360 category {cid}: {e}")
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
        """Search wallpapers across categories and keywords."""
        lower_kw = keyword.strip().lower()

        if "必应" in lower_kw or "bing" in lower_kw:
            return self.get_bing_wallpapers(start, count)
        if "picsum" in lower_kw or "摄影" in lower_kw:
            return self.get_picsum_wallpapers(start, count)

        # Check direct category match
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

    def fetch_random_from_bing(
        self,
        progress_callback: Callable[[int, int, int], None] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> dict[str, Any] | None:
        """Fetches a random HD wallpaper directly from the Bing multi-year historical archive with deduplication."""
        all_items = self._load_bing_historical_wallpapers()
        if not all_items:
            return None

        # Prioritize wallpapers not recently applied or randomized
        fresh_items = [it for it in all_items if not self._is_recently_used(it)]
        candidates = fresh_items if fresh_items else all_items

        shuffled = list(candidates)
        random.shuffle(shuffled)
        for item in shuffled[:5]:
            img_url = get_full_image_url(item)
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
                self._record_recent_random(item.get("id", ""))
                return item

        return None

    def fetch_random_from_picsum(
        self,
        progress_callback: Callable[[int, int, int], None] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> dict[str, Any] | None:
        """Fetches a random HD photo from Lorem Picsum repository across all 42 pages with deduplication."""
        # Total 42 pages (993 photos)
        random_page = random.randint(1, 42)
        res = self.get_picsum_wallpapers(start=(random_page - 1) * 24, count=24)
        items = res.get("items", [])
        if not items:
            res = self.get_picsum_wallpapers(start=0, count=24)
            items = res.get("items", [])

        if not items:
            return None

        fresh_items = [it for it in items if not self._is_recently_used(it)]
        candidates = fresh_items if fresh_items else items

        shuffled = list(candidates)
        random.shuffle(shuffled)
        for item in shuffled[:4]:
            img_url = get_full_image_url(item)
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
                self._record_recent_random(item.get("id", ""))
                return item

        return None

    def fetch_random_from_360(
        self,
        category_id: str | None = None,
        progress_callback: Callable[[int, int, int], None] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> dict[str, Any] | None:
        """Fetches a random HD wallpaper across thousands of items in 360 category pool with deduplication."""
        if not category_id or str(category_id) in ("bing", "picsum"):
            category_id = "36"

        category_name = CATEGORY_MAP.get(str(category_id), "4K专区")

        # Sample across large range (up to index 2000+) instead of just 150 items
        for _attempt in range(3):
            random_start = random.randint(0, 1500)
            if str(category_id) == "latest":
                page = self.get_latest_wallpapers(start=random_start, count=24)
            else:
                page = self.get_category_wallpapers(category_id, start=random_start, count=24)
            items = page.get("items", [])

            if not items and random_start > 0:
                if str(category_id) == "latest":
                    page = self.get_latest_wallpapers(start=0, count=24)
                else:
                    page = self.get_category_wallpapers(category_id, start=0, count=24)
                items = page.get("items", [])

            if not items:
                continue

            fresh_items = [it for it in items if not self._is_recently_used(it)]
            candidates = fresh_items if fresh_items else items

            shuffled = list(candidates)
            random.shuffle(shuffled)
            for item in shuffled[:3]:
                img_url = get_full_image_url(item) or item.get("url_thumb")
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
                    self._record_recent_random(item.get("id", ""))
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
        an HD wallpaper directly from Bing, Picsum, or 360 official repository.
        """
        if not category_ids:
            category_ids = [c["id"] for c in CATEGORIES]

        selected_cat_id = str(random.choice(category_ids))
        if selected_cat_id == "bing":
            return self.fetch_random_from_bing(
                progress_callback=progress_callback,
                cancel_check=cancel_check,
            )
        elif selected_cat_id == "picsum":
            return self.fetch_random_from_picsum(
                progress_callback=progress_callback,
                cancel_check=cancel_check,
            )
        else:
            return self.fetch_random_from_360(
                selected_cat_id,
                progress_callback=progress_callback,
                cancel_check=cancel_check,
            )


# Global singleton instance
api_client = WallpaperApiClient()

