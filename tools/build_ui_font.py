"""Build a WenKai subset for the text shipped with the application."""

import ast
import io
from importlib.metadata import distribution
from pathlib import Path
from xml.etree import ElementTree

from fontTools import subset
from fontTools.ttLib import TTFont


def collect_characters(project_root: Path) -> set[int]:
    characters = set(range(32, 127))
    for path in [project_root / "main.py", *(project_root / "app").rglob("*.py")]:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        for node in ast.walk(tree):
            # This also visits the literal parts of formatted strings.
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                characters.update(ord(char) for char in node.value if char.isprintable())

    catalogs = distribution("pyside6-modern-widgets").locate_file("pyside6_modern_widgets/translations")
    for catalog in sorted(catalogs.glob("*.ts")):
        for text in ElementTree.parse(catalog).iterfind(".//message/translation"):
            characters.update(ord(char) for char in "".join(text.itertext()) if char.isprintable())
    return characters


def build_ui_font(project_root: Path, source: Path, destination: Path) -> None:
    characters = collect_characters(project_root)
    options = subset.Options()
    # Keep the source font's shaping, hinting, names, and license metadata.
    options.layout_features = ["*"]
    options.name_IDs = ["*"]
    options.name_languages = ["*"]
    options.name_legacy = True

    buffer = io.BytesIO()
    with TTFont(source, recalcTimestamp=False) as font:
        supported = characters & font.getBestCmap().keys()
        subsetter = subset.Subsetter(options=options)
        subsetter.populate(unicodes=supported)
        subsetter.subset(font)
        font.save(buffer)

    with TTFont(buffer) as generated:
        if supported - generated.getBestCmap().keys():
            raise ValueError("The UI font subset lost characters supported by the source font")

    data = buffer.getvalue()
    if not destination.is_file() or destination.read_bytes() != data:
        destination.write_bytes(data)
    print(f"UI font: {len(supported)} characters, {len(data):,} bytes", flush=True)
