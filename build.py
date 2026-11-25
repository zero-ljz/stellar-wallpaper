"""Build a standalone Stellar Wallpaper release with PyInstaller."""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def find_7zip() -> str:
    executable = shutil.which("7z")
    if executable:
        return executable
    for variable in ("ProgramW6432", "ProgramFiles", "ProgramFiles(x86)"):
        if directory := os.environ.get(variable):
            candidate = Path(directory) / "7-Zip" / "7z.exe"
            if candidate.is_file():
                return str(candidate)
    raise SystemExit("The --archive build requires 7-Zip. Install it or add 7z to PATH.")


def build(onefile: bool = False, clean: bool = True, archive: bool = False) -> None:
    if archive and (onefile or sys.platform != "win32"):
        raise SystemExit("--archive builds a Windows portable archive and cannot be used with --onefile.")

    project_root = Path(__file__).resolve().parent
    dist_dir = project_root / "dist"
    build_dir = project_root / "build"
    output_dir = dist_dir
    if archive:
        seven_zip = find_7zip()
        build_dir /= "portable"
        output_dir = build_dir / "dist"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--distpath",
        str(output_dir),
        "--workpath",
        str(build_dir),
    ]
    if clean:
        cmd.append("--clean")
    if not archive and sys.platform == "win32" and (project_root / "upx.exe").is_file():
        cmd.extend(["--upx-dir", str(project_root)])
    cmd.extend([str(project_root / "packaging" / "stellar_wallpaper.spec"), "--"])
    if onefile:
        cmd.append("--onefile")
    if archive:
        cmd.append("--no-upx")
    env = {**os.environ, "PYINSTALLER_CONFIG_DIR": str(build_dir / "pyi_config")}
    result = subprocess.run(cmd, cwd=project_root, env=env, check=False)
    if result.returncode:
        sys.exit(result.returncode)

    if archive:
        dist_dir.mkdir(parents=True, exist_ok=True)
        output = dist_dir / "StellarWallpaper.7z"
        # Write a new archive so rebuilding cannot leave obsolete files in it.
        with TemporaryDirectory(dir=dist_dir) as temporary:
            staged_archive = Path(temporary) / output.name
            result = subprocess.run(
                [seven_zip, "a", "-mx=9", "-myx=9", str(staged_archive), "StellarWallpaper"],
                cwd=output_dir,
                check=False,
            )
            if result.returncode:
                sys.exit(result.returncode)
            staged_archive.replace(output)
    elif sys.platform == "darwin":
        output = dist_dir / "StellarWallpaper.app"
    elif onefile:
        suffix = ".exe" if sys.platform == "win32" else ""
        output = dist_dir / f"StellarWallpaper{suffix}"
    else:
        output = dist_dir / "StellarWallpaper"
    print(f"Build succeeded: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Package Stellar Wallpaper App")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--onefile", action="store_true", help="Package into a single standalone file")
    mode.add_argument("--archive", action="store_true", help="Package into a Windows portable 7z archive")
    parser.add_argument("--no-clean", action="store_true", help="Reuse PyInstaller's build cache")
    args = parser.parse_args()

    build(onefile=args.onefile, clean=not args.no_clean, archive=args.archive)
