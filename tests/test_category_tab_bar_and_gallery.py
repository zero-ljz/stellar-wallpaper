"""Tests for CategoryTabBar, GalleryPage, FavoritesPage, and HistoryPage responsiveness."""

import sys

from PySide6.QtWidgets import QApplication

from app.constants import CATEGORIES
from app.ui.components.category_tab_bar import CategoryTabBar
from app.ui.pages.favorites_page import FavoritesPage
from app.ui.pages.gallery_page import GalleryPage
from app.ui.pages.history_page import HistoryPage


def get_qapp():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    return app


def test_category_tab_bar_initialization_and_selection():
    _app = get_qapp()
    default_tab_bar = CategoryTabBar()
    assert default_tab_bar.get_current_category_id() == "bing"

    tab_bar = CategoryTabBar(categories=CATEGORIES, default_cat_id="36")
    assert tab_bar.get_current_category_id() == "36"

    selected = []
    tab_bar.category_selected.connect(
        lambda cid, name, desc: selected.append((cid, name, desc))
    )

    tab_bar.select_category("9")
    assert tab_bar.get_current_category_id() == "9"
    assert len(selected) == 1
    assert selected[0][0] == "9"
    assert selected[0][1] == "风景大片"

    tab_bar.select_category("bing")
    assert tab_bar.get_current_category_id() == "bing"
    assert len(selected) == 2
    assert selected[1][0] == "bing"
    assert selected[1][1] == "必应壁纸"

    tab_bar.select_category("picsum")
    assert tab_bar.get_current_category_id() == "picsum"
    assert len(selected) == 3
    assert selected[2][0] == "picsum"
    assert selected[2][1] == "Picsum 图库"

    tab_bar.clear_selection()
    for btn in tab_bar._buttons.values():
        assert not btn.isChecked()


def test_gallery_page_column_calculation():
    _app = get_qapp()
    page = GalleryPage(auto_load=False)
    assert page._current_cat_id == "bing"
    assert page.cat_tab_bar.get_current_category_id() == "bing"

    # Test column calculations at different viewport widths
    page.grid_scroll.resize(600, 600)
    cols_600 = page._calculate_cols()
    assert cols_600 == 2

    page.grid_scroll.resize(1200, 800)
    cols_1200 = page._calculate_cols()
    assert cols_1200 == 4

    page.grid_scroll.resize(1800, 1000)
    cols_1800 = page._calculate_cols()
    assert cols_1800 == 6
    assert cols_1800 > cols_1200 > cols_600


def test_gallery_batch_selection_is_preserved_across_pages(monkeypatch):
    _app = get_qapp()
    monkeypatch.setattr(
        "app.ui.components.wallpaper_card.WallpaperCard._load_thumbnail",
        lambda _self: None,
    )
    page = GalleryPage(auto_load=False)
    first_page = [
        {"id": "1", "download_url": "https://example.com/1.jpg"},
        {"id": "2", "download_url": "https://example.com/2.jpg"},
    ]
    page._on_page_loaded({"items": first_page, "total": 4})

    assert page.batch_mode_btn.isEnabled()
    page._set_batch_mode(True)
    page._toggle_select_current_page()
    assert len(page._selected_items) == 2
    assert page.download_selected_btn.text() == "下载所选 (2)"
    assert all(card.is_selected() for card in page._cards)

    page._clear_grid()
    second_page = [
        {"id": "3", "download_url": "https://example.com/3.jpg"},
        {"id": "4", "download_url": "https://example.com/4.jpg"},
    ]
    page._current_page = 2
    page._on_page_loaded({"items": second_page, "total": 4})
    page._cards[0].set_selected(True, emit=True)

    assert len(page._selected_items) == 3
    assert page.download_selected_btn.text() == "下载所选 (3)"
    page._set_batch_mode(False)
    assert not page._selected_items


def test_gallery_empty_page_disables_batch_download(monkeypatch):
    _app = get_qapp()
    page = GalleryPage(auto_load=False)
    page._on_page_loaded({"items": [], "total": 0})

    assert not page.batch_mode_btn.isEnabled()
    assert not page.download_selected_btn.isEnabled()


def test_favorites_batch_selection_supports_pages_and_select_all(monkeypatch):
    _app = get_qapp()
    monkeypatch.setattr(
        "app.ui.components.wallpaper_card.WallpaperCard._load_thumbnail",
        lambda _self: None,
    )
    favorites = [
        {"id": str(index), "download_url": f"https://example.com/{index}.jpg"}
        for index in range(1, 5)
    ]
    monkeypatch.setattr(
        "app.ui.pages.favorites_page.db.count_favorites", lambda: len(favorites)
    )

    def get_favorites(limit=None, offset=0):
        if limit is None:
            return list(favorites)
        return favorites[offset : offset + limit]

    monkeypatch.setattr("app.ui.pages.favorites_page.db.get_favorites", get_favorites)

    page = FavoritesPage()
    page._page_size = 2
    page.load_page(1)
    page._set_batch_mode(True)
    page._toggle_select_current_page()

    assert len(page._selected_items) == 2
    assert page.download_selected_btn.text() == "下载所选 (2)"

    page.load_page(2)
    page._cards[0].set_selected(True, emit=True)
    assert len(page._selected_items) == 3

    page._toggle_select_all()
    assert len(page._selected_items) == 4
    assert page.select_all_btn.text() == "取消全选"
    assert all(card.is_selected() for card in page._cards)

    page._toggle_select_all()
    assert not page._selected_items
    assert page.select_all_btn.text() == "全选全部收藏"


def test_favorites_and_history_column_calculation():
    _app = get_qapp()
    fav_page = FavoritesPage()
    fav_page.scroll.resize(1200, 800)
    assert fav_page._calculate_cols() == 4

    hist_page = HistoryPage()
    hist_page.scroll.resize(1200, 800)
    assert hist_page._calculate_cols() == 4
