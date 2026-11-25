"""Keep the QtGui plugins needed by the Windows wallpaper app."""

from pathlib import Path

from PyInstaller.utils.hooks.qt import add_qt6_dependencies

hiddenimports, binaries, datas = add_qt6_dependencies(__file__)

# Exclude these before PyInstaller follows their dependencies into Qt PDF and
# Qt Quick. The application uses image files and the native Windows IME.
binaries = [
    (source, destination)
    for source, destination in binaries
    if Path(source).name not in {"qpdf.dll", "qtvirtualkeyboardplugin.dll", "qdirect2d.dll"}
]
