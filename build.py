"""Build script for packaging Stellar Wallpaper app into an executable (.exe)."""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def build(onefile: bool = False, clean: bool = True) -> None:
    project_root = Path(__file__).resolve().parent
    dist_dir = project_root / "dist"
    build_dir = project_root / "build"
    icon_path = project_root / "app" / "resources" / "app_icon.ico"
    resources_dir = project_root / "app" / "resources"

    if clean:
        print("--> Cleaning build and dist directories...")
        shutil.rmtree(build_dir, ignore_errors=True)
        shutil.rmtree(dist_dir, ignore_errors=True)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--windowed",  # No console window
        "--name=StellarWallpaper",
        f"--add-data={resources_dir};app/resources",
        "--collect-all=pyside6_modern_widgets",
        "--hidden-import=PySide6.QtSvg",
        "--hidden-import=PySide6.QtWidgets",
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtGui",
        "--hidden-import=sqlite3",
        "--exclude-module=PySide6.QtNetwork",
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
        if onefile:
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
    parser = argparse.ArgumentParser(description="Package Stellar Wallpaper App into EXE")
    parser.add_argument("--onefile", action="store_true", help="Package into a single standalone .exe file")
    parser.add_argument("--no-clean", action="store_true", help="Do not clean build/dist before building")
    args = parser.parse_args()

    build(onefile=args.onefile, clean=not args.no_clean)
