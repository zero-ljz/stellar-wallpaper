"""Tests for CategoryTabBar, GalleryPage, FavoritesPage, and HistoryPage responsiveness."""

import sys
from PySide6.QtWidgets import QApplication
from app.constants import CATEGORIES
from app.ui.components.category_tab_bar import CategoryTabBar
from app.ui.pages.gallery_page import GalleryPage
from app.ui.pages.favorites_page import FavoritesPage
from app.ui.pages.history_page import HistoryPage


def get_qapp():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    return app


def test_category_tab_bar_initialization_and_selection():
    _app = get_qapp()
    tab_bar = CategoryTabBar(categories=CATEGORIES, default_cat_id="36")
    assert tab_bar.get_current_category_id() == "36"

    selected = []
    tab_bar.category_selected.connect(lambda cid, name, desc: selected.append((cid, name, desc)))

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


def test_favorites_and_history_column_calculation():
    _app = get_qapp()
    fav_page = FavoritesPage()
    fav_page.scroll.resize(1200, 800)
    assert fav_page._calculate_cols() == 4

    hist_page = HistoryPage()
    hist_page.scroll.resize(1200, 800)
    assert hist_page._calculate_cols() == 4
