"""Build script for packaging Stellar Wallpaper app into an executable (.exe on Windows, .app on macOS)."""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from app.constants import APP_ID


def build(onefile: bool = False, clean: bool = True) -> None:
    project_root = Path(__file__).resolve().parent
    dist_dir = project_root / "dist"
    build_dir = project_root / "build"
    resources_dir = project_root / "app" / "resources"

    # Select icon based on platform
    if sys.platform == "darwin":
        icon_path = resources_dir / "app_icon.icns"
        if not icon_path.exists():
            png_path = resources_dir / "app_icon.png"
            if png_path.exists():
                subprocess.run(
                    ["sips", "-s", "format", "icns", str(png_path), "--out", str(icon_path)],
                    check=False,
                )
    else:
        icon_path = resources_dir / "app_icon.ico"

    if clean:
        print("--> Cleaning build and dist directories...")
        shutil.rmtree(build_dir, ignore_errors=True)
        shutil.rmtree(dist_dir, ignore_errors=True)

    pyi_config_dir = build_dir / "pyi_config"
    pyi_config_dir.mkdir(parents=True, exist_ok=True)
    os.environ["PYINSTALLER_CONFIG_DIR"] = str(pyi_config_dir)

    # PyInstaller data separator: ';' on Windows, ':' on macOS/Linux
    sep = os.pathsep

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--windowed",  # No console window
        "--name=StellarWallpaper",
        f"--add-data={resources_dir}{sep}app/resources",
        "--collect-all=pyside6_modern_widgets",
        "--hidden-import=PySide6.QtSvg",
        "--hidden-import=PySide6.QtWidgets",
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtGui",
        "--hidden-import=PySide6.QtNetwork",
        "--hidden-import=sqlite3",
        "--exclude-module=PySide6.QtQml",
        "--exclude-module=PySide6.QtQuick",
        "--exclude-module=PySide6.QtQuick3D",
        "--exclude-module=PySide6.QtPdf",
        "--exclude-module=PySide6.QtWebEngine",
        "--exclude-module=PySide6.QtWebEngineCore",
        "--exclude-module=PySide6.QtWebEngineWidgets",
        "--exclude-module=PySide6.QtMultimedia",
        "--exclude-module=PySide6.QtSql",
        "--exclude-module=PySide6.QtTest",
        "--exclude-module=PySide6.QtXml",
    ]

    if sys.platform == "darwin":
        cmd.append(f"--osx-bundle-identifier={APP_ID}")

    if icon_path.exists():
        cmd.append(f"--icon={icon_path}")

    if onefile:
        cmd.append("--onefile")
        print("--> Packaging mode: Single Executable (--onefile)...")
    else:
        cmd.append("--onedir")
        print("--> Packaging mode: Directory (--onedir, recommended for fast launch)...")

    cmd.append(str(project_root / "main.py"))

    print(f"--> Running PyInstaller: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=project_root)

    if result.returncode == 0:
        print("\n========================================================")
        print("  Build Succeeded!")
        if sys.platform == "darwin":
            app_bundle = dist_dir / "StellarWallpaper.app"
            if app_bundle.exists():
                print(f"  macOS App Bundle created at: {app_bundle}")
            else:
                print(f"  Output directory: {dist_dir}")
        elif onefile:
            exe_file = dist_dir / "StellarWallpaper.exe"
            print(f"  Executable created at: {exe_file}")
        else:
            exe_file = dist_dir / "StellarWallpaper" / "StellarWallpaper.exe"
            # Delete opengl32sw.dll to save space
            opengl_dll = dist_dir / "StellarWallpaper" / "_internal" / "PySide6" / "opengl32sw.dll"
            if opengl_dll.exists():
                opengl_dll.unlink()
                print("  Removed opengl32sw.dll (saved extra space)")

            print(f"  Directory created at: {dist_dir / 'StellarWallpaper'}")
            print(f"  Executable: {exe_file}")
        print("========================================================")
    else:
        print(f"\n--> Build failed with code {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Package Stellar Wallpaper App")
    parser.add_argument("--onefile", action="store_true", help="Package into a single standalone file")
    parser.add_argument("--no-clean", action="store_true", help="Do not clean build/dist before building")
    args = parser.parse_args()

    build(onefile=args.onefile, clean=not args.no_clean)
