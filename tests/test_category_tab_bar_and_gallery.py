"""Tests for CategoryTabBar, GalleryPage, FavoritesPage, and HistoryPage responsiveness."""

import sys
from collections import defaultdict
from itertools import pairwise

from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QApplication

from app.config import config
from app.constants import CATEGORIES
from app.core.database import DatabaseManager
from app.core.scheduler import scheduler
from app.core.wallpaper_setter import wallpaper_setter
from app.ui.components.category_tab_bar import CategoryTabBar
from app.ui.components.wallpaper_card import WallpaperCard
from app.ui.main_window import MainWindow
from app.ui.pages.favorites_page import FavoritesPage
from app.ui.pages.gallery_page import GalleryPage


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


def assert_grid_rows(grid):
    rows = defaultdict(list)
    for card in grid.cards:
        rows[card.y()].append(card)
    assert rows
    for upper, lower in pairwise(sorted(rows)):
        assert lower - upper == WallpaperCard.HEIGHT + grid.spacing
    for cards in rows.values():
        for left, right in pairwise(cards):
            assert right.x() - left.x() == WallpaperCard.WIDTH + grid.spacing
    assert max(rows) + WallpaperCard.HEIGHT <= grid.content.height()
    assert grid.verticalScrollBar().maximum() + grid.viewport().height() >= grid.content.height()
    return len(rows[min(rows)])


def test_gallery_page_column_calculation(monkeypatch):
    app = get_qapp()
    monkeypatch.setattr(WallpaperCard, "_load_thumbnail", lambda _card: None)
    page = GalleryPage(auto_load=False)
    assert page._current_cat_id == "bing"
    assert page.cat_tab_bar.get_current_category_id() == "bing"

    page.show()
    try:
        page._on_page_loaded({"items": [{"id": str(index)} for index in range(24)]})
        for width, columns in ((650, 2), (1200, 4), (1800, 6), (650, 2)):
            page.resize(width, 800)
            app.processEvents()
            assert assert_grid_rows(page.grid_scroll) == columns
    finally:
        page.close()


def test_gallery_grid_keeps_card_rows_separate_when_results_arrive(monkeypatch):
    app = get_qapp()
    monkeypatch.setattr(
        "app.ui.components.wallpaper_card.WallpaperCard._load_thumbnail",
        lambda _self: None,
    )
    page = GalleryPage(auto_load=False)
    page.resize(1010, 800)
    page.show()
    try:
        app.processEvents()
        items = [{"id": str(index)} for index in range(24)]
        page._on_page_loaded({"items": items})
        # An asynchronous result must have valid row positions immediately,
        # including before the next round of Qt layout events.
        assert assert_grid_rows(page.grid_scroll) == 3
        app.processEvents()

        scrollbar = page.grid_scroll.verticalScrollBar()
        assert scrollbar.maximum() > 0
        assert assert_grid_rows(page.grid_scroll) == 3
        scrollbar.setValue(scrollbar.maximum())
        assert not page.grid_scroll.cards[-1].visibleRegion().isEmpty()
    finally:
        page.close()


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
    assert all(card.is_selected() for card in page.grid_scroll.cards)

    page.grid_scroll.set_cards([])
    second_page = [
        {"id": "3", "download_url": "https://example.com/3.jpg"},
        {"id": "4", "download_url": "https://example.com/4.jpg"},
    ]
    page._current_page = 2
    page._on_page_loaded({"items": second_page, "total": 4})
    page.grid_scroll.cards[0].set_selected(True, emit=True)

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
    page.scroll.cards[0].set_selected(True, emit=True)
    assert len(page._selected_items) == 3

    page._toggle_select_all()
    assert len(page._selected_items) == 4
    assert page.select_all_btn.text() == "取消全选"
    assert all(card.is_selected() for card in page.scroll.cards)

    page._toggle_select_all()
    assert not page._selected_items
    assert page.select_all_btn.text() == "全选全部收藏"


def test_gallery_and_history_keep_rows_separate_after_applying_wallpaper(monkeypatch, tmp_path):
    app = get_qapp()
    database = DatabaseManager(tmp_path / "wallpaper.db")
    monkeypatch.setattr("app.core.scheduler.db", database)
    monkeypatch.setattr("app.ui.pages.history_page.db", database)
    monkeypatch.setattr(GalleryPage, "load_page", lambda *_args: None)
    monkeypatch.setattr(WallpaperCard, "_load_thumbnail", lambda _card: None)
    monkeypatch.setattr(wallpaper_setter, "apply_wallpaper", lambda *_args: True)
    monkeypatch.setitem(config._config, "tray_notifications", False)
    monkeypatch.setitem(config._config, "last_wallpaper", None)
    monkeypatch.setitem(config._config, "auto_switch_enabled", False)

    local_path = tmp_path / "wallpaper.jpg"
    local_path.touch()
    items = [{"id": str(index), "local_path": str(local_path)} for index in range(24)]
    for item in items:
        database.add_history(item)

    window = MainWindow()
    window.resize(1250, 840)
    window.show()
    try:
        app.processEvents()
        gallery = window.gallery_page
        gallery._on_page_loaded({"items": items})
        app.processEvents()
        scrollbar = gallery.grid_scroll.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum() // 2)
        scroll_position = scrollbar.value()
        before = [card.geometry() for card in gallery.grid_scroll.cards]

        applied = QSignalSpy(scheduler.wallpaper_applied)
        gallery.grid_scroll.cards[0].apply_btn.click()
        assert applied.count() or applied.wait(3000)
        QTest.qWait(20)
        assert scrollbar.value() == scroll_position
        assert [card.geometry() for card in gallery.grid_scroll.cards] == before
        assert_grid_rows(gallery.grid_scroll)

        window._select_navigation_page(4)
        app.processEvents()
        assert_grid_rows(window.history_page.scroll)
    finally:
        window.notification.hide()
        window.tray_icon.hide()
        window._is_quitting = True
        window.close()
        window.deleteLater()
        database.close()
