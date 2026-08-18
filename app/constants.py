"""Constants and configuration defaults for the PySide6 Wallpaper Application."""

import os
from pathlib import Path

APP_NAME = "星澜壁纸"
APP_ID = "com.stellar.wallpaper"
APP_VERSION = "1.0.0"

# Application data directories
DEFAULT_APP_DATA_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "StellarWallpaper"
CACHE_DIR = DEFAULT_APP_DATA_DIR / "cache"
THUMB_CACHE_DIR = CACHE_DIR / "thumbs"
WALLPAPER_CACHE_DIR = CACHE_DIR / "wallpapers"
DB_PATH = DEFAULT_APP_DATA_DIR / "wallpaper.db"

# Default save folder for user downloads
DEFAULT_DOWNLOAD_DIR = Path.home() / "Pictures" / "Wallpapers"

# 15 Curated Wallpaper Categories
CATEGORIES = [
    {"id": "36", "name": "4K专区", "desc": "3840×2160 超高清壁纸"},
    {"id": "9", "name": "风景大片", "desc": "壮美自然、山川湖海"},
    {"id": "26", "name": "动漫卡通", "desc": "二次元、精选动漫CG"},
    {"id": "5", "name": "游戏壁纸", "desc": "热门3A游戏、原神、主机"},
    {"id": "12", "name": "汽车天下", "desc": "超级跑车、概念车、越野"},
    {"id": "14", "name": "萌宠动物", "desc": "可爱猫咪、狗狗、野生动物"},
    {"id": "6", "name": "美女模特", "desc": "写真、人像、时尚丽人"},
    {"id": "10", "name": "炫酷时尚", "desc": "霓虹、赛博朋克、抽象艺术"},
    {"id": "15", "name": "小清新", "desc": "治愈系、插画、文艺美图"},
    {"id": "7", "name": "影视剧照", "desc": "经典电影、热门剧集海报"},
    {"id": "30", "name": "爱情美图", "desc": "浪漫唯美、情侣意境"},
    {"id": "11", "name": "明星风尚", "desc": "偶像明星、舞台大片"},
    {"id": "22", "name": "军事天地", "desc": "战机、战舰、装甲武器"},
    {"id": "16", "name": "劲爆体育", "desc": "足球、篮球、极限运动"},
    {"id": "35", "name": "文字控", "desc": "励志短句、唯美意境排版"},
]

CATEGORY_MAP = {c["id"]: c["name"] for c in CATEGORIES}
CATEGORY_NAME_TO_ID = {c["name"]: c["id"] for c in CATEGORIES}

# 360 Official Wallpaper API Endpoints
API_360_BASE = "http://wallpaper.apc.360.cn/index.php"
API_360_CATEGORY = f"{API_360_BASE}?c=WallPaper&a=getAppsByCategory"
API_360_SEARCH = f"{API_360_BASE}?c=WallPaper&a=getAppsByTags"
API_360_ORDER = f"{API_360_BASE}?c=WallPaper&a=getAppsByOrder"

# User-Agent for requests
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)

# Windows Wallpaper Styles
WALLPAPER_STYLES = {
    "fill": {"name": "填充 (Fill)", "style": "10", "tile": "0", "desc": "拉伸以填满屏幕，可能裁剪边缘"},
    "fit": {"name": "适应 (Fit)", "style": "6", "tile": "0", "desc": "完整显示整张图片，可能留黑边"},
    "stretch": {"name": "拉伸 (Stretch)", "style": "2", "tile": "0", "desc": "按屏幕比例完全拉伸变形"},
    "tile": {"name": "平铺 (Tile)", "style": "0", "tile": "1", "desc": "原尺寸重复平铺整个屏幕"},
    "center": {"name": "居中 (Center)", "style": "0", "tile": "0", "desc": "原尺寸居中放置，不拉伸"},
    "span": {"name": "跨屏 (Span)", "style": "22", "tile": "0", "desc": "跨越多个显示器连续展示"},
}

# Scheduler interval options (in seconds)
INTERVAL_OPTIONS = [
    {"label": "1 分钟 (测试用)", "seconds": 60},
    {"label": "5 分钟", "seconds": 300},
    {"label": "15 分钟", "seconds": 900},
    {"label": "30 分钟", "seconds": 1800},
    {"label": "1 小时", "seconds": 3600},
    {"label": "2 小时", "seconds": 7200},
    {"label": "6 小时", "seconds": 21600},
    {"label": "12 小时", "seconds": 43200},
    {"label": "1 天 (24小时)", "seconds": 86400},
]
