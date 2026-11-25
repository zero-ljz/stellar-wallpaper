"""Keep the QtGui plugins needed by the wallpaper app."""

import sys
from pathlib import Path

from PyInstaller.utils.hooks.qt import add_qt6_dependencies

hiddenimports, binaries, datas = add_qt6_dependencies(__file__)

# Use image files and native input methods. Exclude these plugins before
# PyInstaller follows their dependencies into Qt PDF and Qt Quick.
unused_plugins = {
    "darwin": {"libqpdf.dylib", "libqtvirtualkeyboardplugin.dylib"},
    "win32": {"qpdf.dll", "qtvirtualkeyboardplugin.dll", "qdirect2d.dll"},
}.get(sys.platform, set())
binaries = [
    (source, destination)
    for source, destination in binaries
    if Path(source).name not in unused_plugins
]
