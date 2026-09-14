"""Tests for deterministic and fault-tolerant wallpaper downloads."""

from pathlib import Path

from app.core import download_manager
from app.core.download_manager import (
    DownloadResult,
    build_download_target,
    download_wallpaper,
)
from app.ui import batch_download
from app.ui.batch_download import BatchDownloadWorker


def test_build_download_target_is_stable_and_windows_safe(tmp_path: Path) -> None:
    item = {
        "id": "bing:2026/09/11?*",
        "download_url": "https://example.com/wallpaper.png?size=full",
    }

    first = build_download_target(item, tmp_path)
    second = build_download_target(item, tmp_path)

    assert first == second
    assert first is not None
    assert first.parent == tmp_path
    assert first.suffix == ".png"
    assert not any(char in first.name for char in '<>:"/\\|?*')


def test_download_wallpaper_uses_cache_then_skips_existing(
    monkeypatch, tmp_path: Path
) -> None:
    cached = tmp_path / "cached.jpg"
    cached.write_bytes(b"image-data")
    save_dir = tmp_path / "downloads"
    item = {"id": "42", "download_url": "https://example.com/42.jpg"}
    monkeypatch.setattr(
        download_manager.cache_mgr, "get_wallpaper_path", lambda _url: cached
    )
    monkeypatch.setattr(
        download_manager.api_client,
        "download_image",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("network should not be used")
        ),
    )

    first = download_wallpaper(item, save_dir)
    second = download_wallpaper(item, save_dir)

    assert first.status == "downloaded"
    assert first.target is not None and first.target.read_bytes() == b"image-data"
    assert second.status == "skipped"
    assert second.target == first.target


def test_download_wallpaper_reports_missing_url_and_network_failure(
    monkeypatch, tmp_path: Path
) -> None:
    assert download_wallpaper({"id": "missing"}, tmp_path).status == "failed"

    item = {"id": "broken", "download_url": "https://example.com/broken.jpg"}
    monkeypatch.setattr(
        download_manager.cache_mgr,
        "get_wallpaper_path",
        lambda _url: tmp_path / "not-cached.jpg",
    )
    monkeypatch.setattr(
        download_manager.api_client, "download_image", lambda *_args, **_kwargs: False
    )

    assert download_wallpaper(item, tmp_path).status == "failed"


def test_batch_worker_deduplicates_and_continues_after_failure(
    monkeypatch, tmp_path: Path
) -> None:
    items = [
        {"id": "one", "download_url": "https://example.com/one.jpg"},
        {"id": "one-copy", "download_url": "https://example.com/one.jpg"},
        {"id": "two", "download_url": "https://example.com/two.jpg"},
        {"id": "three", "download_url": "https://example.com/three.jpg"},
    ]
    outcomes = iter(
        [
            DownloadResult("downloaded", tmp_path / "one.jpg"),
            RuntimeError("unexpected item failure"),
            DownloadResult("skipped", tmp_path / "three.jpg"),
        ]
    )

    def fake_download(*_args, **_kwargs):
        outcome = next(outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(batch_download, "download_wallpaper", fake_download)
    worker = BatchDownloadWorker(items, tmp_path)
    completed = []
    progress = []
    worker.batch_completed.connect(lambda *args: completed.append(args))
    worker.item_finished.connect(lambda *args: progress.append(args))

    worker.run()

    assert len(worker.items) == 3
    assert completed == [(1, 1, 1, False)]
    assert [entry[0] for entry in progress] == [1, 2, 3]
