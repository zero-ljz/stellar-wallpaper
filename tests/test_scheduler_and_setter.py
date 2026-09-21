import sys
from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication
from app.constants import WALLPAPER_STYLES
from app.core.wallpaper_setter import WallpaperSetter
from app.core.scheduler import WallpaperScheduler
from app.config import config


def get_qapp():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    return app


def test_wallpaper_setter_style_validation():
    # Verify all style registry pairs
    for style_key in ["fill", "fit", "stretch", "tile", "center", "span"]:
        style_info = WALLPAPER_STYLES[style_key]
        assert "style" in style_info
        assert "tile" in style_info


def test_scheduler_interval_logic():
    _app = get_qapp()
    sched = WallpaperScheduler()
    sched.stop()
    assert sched.is_running is False

    sched.set_interval(600)
    assert config.auto_switch_interval == 600
    assert sched._total_seconds == 600

    sched.start()
    assert sched.is_running is True

    sched.stop()
    assert sched.is_running is False


def test_scheduler_startup_state_restore():
    _app = get_qapp()
    sched = WallpaperScheduler()

    # 1. Manually start -> config.auto_switch_enabled should be True
    sched.start()
    assert sched.is_running is True
    assert config.auto_switch_enabled is True

    # 2. Shutdown (simulating app close) -> should NOT reset config.auto_switch_enabled to False
    sched.shutdown()
    assert sched.is_running is False
    assert config.auto_switch_enabled is True

    # 3. Next startup: start_if_enabled() -> should restore running state
    sched.start_if_enabled()
    assert sched.is_running is True

    # 4. User explicitly stops auto-rotation -> config.auto_switch_enabled becomes False
    sched.stop()
    assert sched.is_running is False
    assert config.auto_switch_enabled is False

    # 5. Next startup with disabled setting: start_if_enabled() -> should remain stopped
    sched.start_if_enabled()
    assert sched.is_running is False


def test_wallpaper_setter_cross_platform(monkeypatch, tmp_path):
    img_file = tmp_path / "test.jpg"
    img_file.write_text("fake image content")

    # Non-existent file should return False
    assert WallpaperSetter.apply_wallpaper(tmp_path / "nonexistent.jpg") is False

    if sys.platform == "darwin":
        # On macOS, verify it invokes osascript
        called_scripts = []

        def mock_run(cmd, capture_output=True, text=True, check=False):
            called_scripts.append(cmd)
            res = MagicMock()
            res.returncode = 0
            res.stdout = "/path/to/wallpaper.jpg"
            res.stderr = ""
            return res

        monkeypatch.setattr("subprocess.run", mock_run)
        ok = WallpaperSetter.apply_wallpaper(img_file)
        assert ok is True
        assert len(called_scripts) > 0
        assert "osascript" in called_scripts[0][0]

        # Test current wallpaper query
        cur = WallpaperSetter.get_current_wallpaper_path()
        assert cur == "/path/to/wallpaper.jpg"

        # Test macOS startup plist creation/deletion
        plist_path = tmp_path / "com.stellar.wallpaper.plist"
        monkeypatch.setattr(
            WallpaperSetter,
            "_get_macos_launch_agent_path",
            staticmethod(lambda: plist_path),
        )

        assert WallpaperSetter.is_startup_enabled() is False
        assert WallpaperSetter.set_startup(True) is True
        assert plist_path.exists()
        assert WallpaperSetter.is_startup_enabled() is True
        assert WallpaperSetter.set_startup(False) is True
        assert not plist_path.exists()
        assert WallpaperSetter.is_startup_enabled() is False

