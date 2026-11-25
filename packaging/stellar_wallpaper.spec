import argparse
import subprocess
import sys
from pathlib import Path

from app.constants import APP_ID, APP_VERSION, MACOS_MIN_VERSION
from tools.build_ui_font import build_ui_font

parser = argparse.ArgumentParser()
parser.add_argument("--onefile", action="store_true")
parser.add_argument("--no-upx", action="store_true")
parser.add_argument("--universal2", action="store_true")
options = parser.parse_args()

packaging_dir = Path(SPECPATH)
project_root = packaging_dir.parent
resources = project_root / "app" / "resources"
is_windows = sys.platform == "win32"
is_macos = sys.platform == "darwin"

icon_path = resources / ("app_icon.icns" if is_macos else "app_icon.ico")
if is_macos and not icon_path.exists():
    icon_path = Path(workpath) / "app_icon.icns"
    subprocess.run(
        ["sips", "-s", "format", "icns", str(resources / "app_icon.png"), "--out", str(icon_path)],
        check=True,
    )
icon = str(icon_path) if icon_path.is_file() else None

font_file = resources / "fonts" / "LXGWWenKaiLite-Regular.ttf"
ui_font = Path(workpath) / font_file.name
build_ui_font(project_root, font_file, ui_font)
datas = [
    (str(resources / "app_icon.ico"), "app/resources"),
    (str(resources / "icons"), "app/resources/icons"),
    (str(ui_font), "app/resources/fonts"),
    (str(font_file.with_name("OFL-LXGWWenKaiLite.txt")), "app/resources/fonts"),
]

analysis = Analysis(
    [str(project_root / "main.py")],
    datas=datas,
    hookspath=[str(packaging_dir / "hooks")] if is_windows or is_macos else [],
    runtime_hooks=[str(packaging_dir / "hooks" / "rthook_macos_ssl.py")] if is_macos else [],
    excludes=[
        # Modern Widgets uses ThreadPoolExecutor. The app never starts a process pool
        # or uses SQLite's command-line entry point.
        "concurrent.futures.process", "sqlite3.__main__",
        "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuick3D", "PySide6.QtPdf",
        "PySide6.QtWebEngine", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
        "PySide6.QtMultimedia", "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtXml",
    ],
)

if is_windows:
    # QWidget rendering uses the Windows raster backend. Windows 10 and 11
    # already ship UCRT and API sets, even if Analysis picks up redistributables.
    binary_names = {destination.lower() for destination, _, _ in analysis.binaries}
    unused_binaries = {"pyside6\\opengl32sw.dll", "ucrtbase.dll"}
    # The bootloader loads the top-level C runtime with Python. PySide6 loads
    # Shiboken (and its C++ runtime) before its Qt extension modules.
    for runtime in ("vcruntime140.dll", "vcruntime140_1.dll"):
        if runtime in binary_names:
            unused_binaries.update({f"pyside6\\{runtime}", f"shiboken6\\{runtime}"})
    if "shiboken6\\msvcp140.dll" in binary_names:
        unused_binaries.add("pyside6\\msvcp140.dll")

    # QtNetwork supplies local IPC. HTTPS downloads use Python's OpenSSL.
    unused_plugin_dirs = {Path("pyside6/plugins/tls"), Path("pyside6/plugins/networkinformation")}
    analysis.binaries = [
        (destination, source, kind)
        for destination, source, kind in analysis.binaries
        if destination.lower() not in unused_binaries
        and not Path(destination).name.lower().startswith(("api-ms-win-", "ext-ms-win-"))
        and Path(destination.lower()).parent not in unused_plugin_dirs
    ]
    qt_translations = Path("PySide6") / "translations"
    analysis.datas = [
        (destination, source, kind)
        for destination, source, kind in analysis.datas
        if Path(destination).parent != qt_translations
        or Path(destination).name in {"qt_zh_CN.qm", "qt_zh_TW.qm", "qtbase_zh_CN.qm", "qtbase_zh_TW.qm"}
    ]

pyz = PYZ(analysis.pure)
name = "StellarWallpaper"
use_upx = not options.no_upx
target_arch = "universal2" if options.universal2 else None
if options.onefile:
    bundle = EXE(
        pyz, analysis.scripts, analysis.binaries, analysis.datas,
        name=name, console=False, icon=icon, upx=use_upx, target_arch=target_arch,
    )
else:
    exe = EXE(
        pyz, analysis.scripts, name=name, console=False, icon=icon,
        exclude_binaries=True, target_arch=target_arch,
    )
    bundle = COLLECT(exe, analysis.binaries, analysis.datas, name=name, upx=use_upx)

if is_macos:
    BUNDLE(
        bundle, name=f"{name}.app", icon=icon, bundle_identifier=APP_ID, version=APP_VERSION,
        info_plist={
            "LSMinimumSystemVersion": MACOS_MIN_VERSION,
            "NSAppleEventsUsageDescription": "星澜壁纸需要通过系统事件来更换桌面壁纸。",
        },
    )
