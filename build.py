"""Build a standalone Stellar Wallpaper release with PyInstaller."""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from app.constants import APP_VERSION

MACHO_MAGIC = {
    b"\xfe\xed\xfa\xce", b"\xce\xfa\xed\xfe",  # 32-bit
    b"\xfe\xed\xfa\xcf", b"\xcf\xfa\xed\xfe",  # 64-bit
    b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca",  # Fat
    b"\xca\xfe\xba\xbf", b"\xbf\xba\xfe\xca",  # Fat with 64-bit offsets
}


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


def verify_universal_binary(path: Path) -> None:
    result = subprocess.run(
        ["/usr/bin/lipo", "-archs", str(path)], capture_output=True, text=True, check=True
    )
    if not {"arm64", "x86_64"}.issubset(result.stdout.split()):
        raise SystemExit(f"Universal 2 requires arm64 and x86_64 in {path} (found: {result.stdout.strip()}).")


def package_macos_dmg(app: Path, output: Path) -> None:
    # PyInstaller enforces architecture on extensions, but may accept thin dylibs.
    executable = app / "Contents" / "MacOS" / app.stem
    verify_universal_binary(executable)
    for path in (app / "Contents").rglob("*"):
        if path == executable or path.is_symlink() or not path.is_file():
            continue
        with path.open("rb") as binary:
            is_macho = binary.read(4) in MACHO_MAGIC
        if is_macho:
            verify_universal_binary(path)

    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="stellar-dmg-", dir=output.parent) as temporary:
        root = Path(temporary)
        image_dir = root / "image"
        image_dir.mkdir()
        staged_app = image_dir / app.name
        subprocess.run(["/usr/bin/ditto", str(app), str(staged_app)], check=True)
        subprocess.run(
            ["/usr/bin/codesign", "--verify", "--all-architectures", "--deep", "--strict", str(staged_app)],
            check=True,
        )
        (image_dir / "Applications").symlink_to("/Applications", target_is_directory=True)
        staged_dmg = root / output.name
        subprocess.run(
            [
                "/usr/bin/hdiutil", "create", "-srcfolder", str(image_dir),
                "-volname", app.stem, "-fs", "HFS+", "-format", "ULMO", str(staged_dmg),
            ],
            check=True,
        )
        subprocess.run(["/usr/bin/hdiutil", "verify", str(staged_dmg)], check=True)
        staged_dmg.replace(output)


def build(onefile: bool = False, clean: bool = True, archive: bool = False, *, dmg: bool = False) -> None:
    if archive and (onefile or sys.platform != "win32"):
        raise SystemExit("--archive builds a Windows portable archive and cannot be used with --onefile.")
    if dmg and (onefile or sys.platform != "darwin"):
        raise SystemExit("--dmg requires macOS and cannot be used with --onefile.")

    project_root = Path(__file__).resolve().parent
    dist_dir = project_root / "dist"
    build_dir = project_root / "build"
    output_dir = dist_dir
    if archive:
        seven_zip = find_7zip()
        build_dir /= "portable"
        output_dir = build_dir / "dist"
    elif dmg:
        from PyInstaller.depend.bindepend import get_python_library_path

        python_library = get_python_library_path()
        if python_library is None:
            raise SystemExit("Cannot find the Python shared library. Use a Universal 2 Python build.")
        verify_universal_binary(Path(python_library))
        build_dir /= "macos-universal"
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
    if dmg:
        cmd.append("--universal2")
    env = {**os.environ, "PYINSTALLER_CONFIG_DIR": str(build_dir / "pyi_config")}
    result = subprocess.run(cmd, cwd=project_root, env=env, check=False)
    if result.returncode:
        sys.exit(result.returncode)

    if archive:
        dist_dir.mkdir(parents=True, exist_ok=True)
        output = dist_dir / f"StellarWallpaper-{APP_VERSION}-windows-x64-portable.7z"
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
    elif dmg:
        app = output_dir / "StellarWallpaper.app"
        output = dist_dir / f"{app.stem}-{APP_VERSION}-macos-universal.dmg"
        package_macos_dmg(app, output)
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
    mode.add_argument("--dmg", action="store_true", help="Package into a macOS Universal 2 disk image")
    parser.add_argument("--no-clean", action="store_true", help="Reuse PyInstaller's build cache")
    args = parser.parse_args()

    build(onefile=args.onefile, clean=not args.no_clean, archive=args.archive, dmg=args.dmg)
