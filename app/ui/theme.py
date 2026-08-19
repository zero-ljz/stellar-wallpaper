import sys
from pathlib import Path
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication

# Directory for UI SVG icons
def _get_icons_dir() -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        icons_path = Path(sys._MEIPASS) / "app" / "resources" / "icons"
        if icons_path.exists():
            return icons_path.as_posix()
    return (Path(__file__).resolve().parent.parent / "resources" / "icons").as_posix()


ICONS_DIR = _get_icons_dir()


def _get_font_file_path() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        font_path = Path(sys._MEIPASS) / "app" / "resources" / "fonts" / "MiSans-Regular.ttf"
        if font_path.exists():
            return font_path
    return Path(__file__).resolve().parent.parent / "resources" / "fonts" / "MiSans-Regular.ttf"


def load_application_fonts() -> str:
    """Loads MiSans-Regular.ttf into Qt font database and returns registered family name."""
    font_path = _get_font_file_path()
    if font_path.exists():
        font_id = QFontDatabase.addApplicationFont(str(font_path))
        if font_id != -1:
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                return families[0]
    return "MiSans"


# Windows 11 Fluent Light Palette with Enhanced Text Contrast
COLOR_ACCENT = "#0078D4"          # Fluent Blue
COLOR_ACCENT_HOVER = "#1084D9"
COLOR_ACCENT_PRESSED = "#0067B8"
COLOR_ACCENT_LIGHT = "#EFF6FF"

COLOR_BG = "#F8F9FA"              # Soft clean window background
COLOR_SURFACE = "#FFFFFF"         # Card / surface background
COLOR_SURFACE_HOVER = "#F9FAFB"
COLOR_BORDER = "#E2E8F0"          # Delicate subtle card border
COLOR_BORDER_STRONG = "#CBD5E1"

# Deep, solid high-contrast text colors to eliminate faintness
COLOR_TEXT_MAIN = "#0B0F19"       # Deep crisp obsidian dark text (100% solid)
COLOR_TEXT_MUTED = "#334155"      # High readability solid slate text (not faded)
COLOR_TEXT_HINT = "#475569"       # Clear tertiary text

COLOR_SUCCESS = "#10B981"
COLOR_SUCCESS_BG = "#ECFDF5"
COLOR_DANGER = "#EF4444"
COLOR_DANGER_BG = "#FEF2F2"


def force_window_light_mode(hwnd: int) -> None:
    """Explicitly forces Windows DWM to render light mode on the given window handle."""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import byref, c_int, sizeof
            dark_value = c_int(0)  # 0 = Light mode (False)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                ctypes.c_void_p(hwnd),
                20,  # DWMWA_USE_IMMERSIVE_DARK_MODE
                byref(dark_value),
                sizeof(dark_value),
            )
        except Exception:
            pass


def apply_fusion_light_theme(app: QApplication) -> None:
    """Applies Fusion style with high-DPI crystal-clear font rendering and tuned Windows 11 Light Palette."""
    app.setStyle("Fusion")

    # High-DPI screen (3.2K / 4K with 150%/200% scaling) optimal font setup:
    # 1. Use natural Normal weight (400) to avoid algorithmic faux-bold smudging on single-weight fonts.
    # 2. Use PreferNoHinting to preserve true vector outline curves without 96-DPI integer grid distortion.
    font_family = load_application_fonts()
    app_font = QFont(font_family)
    app_font.setPointSize(10)
    app_font.setWeight(QFont.Weight.Normal)
    app_font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    app_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias | QFont.StyleStrategy.PreferQuality)
    app.setFont(app_font)

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(COLOR_BG))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(COLOR_TEXT_MAIN))
    palette.setColor(QPalette.ColorRole.Base, QColor(COLOR_SURFACE))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#F1F5F9"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(COLOR_SURFACE))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(COLOR_TEXT_MAIN))
    palette.setColor(QPalette.ColorRole.Text, QColor(COLOR_TEXT_MAIN))
    palette.setColor(QPalette.ColorRole.Button, QColor(COLOR_SURFACE))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(COLOR_TEXT_MAIN))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(COLOR_ACCENT))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(COLOR_TEXT_HINT))
    app.setPalette(palette)

    app.setStyleSheet(get_global_stylesheet(font_family))


def get_global_stylesheet(font_family: str = "MiSans") -> str:
    return f"""
/* Global Typography and Base */
QWidget {{
    font-family: "{font_family}", "Segoe UI", "Microsoft YaHei UI", sans-serif;
    font-size: 13px;
    font-weight: normal;
    color: {COLOR_TEXT_MAIN};
}}

/* All Dialogs and Message Boxes - Pure Fusion Light Mode */
QDialog, QMessageBox, QFileDialog, QInputDialog {{
    background-color: #FFFFFF;
    color: {COLOR_TEXT_MAIN};
}}

QDialog QLabel, QMessageBox QLabel, QFileDialog QLabel {{
    background: transparent;
    border: none;
    color: {COLOR_TEXT_MAIN};
}}

QDialogButtonBox {{
    background-color: transparent;
    border: none;
}}

QDialogButtonBox QPushButton, QMessageBox QPushButton {{
    background-color: {COLOR_ACCENT};
    color: #FFFFFF;
    border: 1px solid {COLOR_ACCENT};
    border-radius: 6px;
    padding: 6px 18px;
    font-weight: bold;
    font-size: 13px;
    min-width: 75px;
    min-height: 24px;
}}

QDialogButtonBox QPushButton:hover, QMessageBox QPushButton:hover {{
    background-color: {COLOR_ACCENT_HOVER};
    border-color: {COLOR_ACCENT_HOVER};
}}

QDialogButtonBox QPushButton:pressed, QMessageBox QPushButton:pressed {{
    background-color: {COLOR_ACCENT_PRESSED};
    border-color: {COLOR_ACCENT_PRESSED};
}}

/* All text labels and titles must have NO border */
QLabel, QLabel:hover, QLabel:focus, QLabel:disabled {{
    background: transparent;
    border: none;
    outline: none;
    color: {COLOR_TEXT_MAIN};
}}

/* Smooth ScrollBar Styling */
QScrollBar:vertical {{
    width: 6px;
    background: transparent;
    margin: 2px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: #CBD5E1;
    min-height: 28px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical:hover {{
    background: #94A3B8;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    height: 6px;
    background: transparent;
    margin: 2px;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal {{
    background: #CBD5E1;
    min-width: 28px;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal:hover {{
    background: #94A3B8;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* Scroll Areas & Viewports */
QScrollArea,
QAbstractScrollArea,
QScrollArea > QWidget,
QScrollArea > QWidget > QWidget,
QScrollArea #qt_scrollarea_viewport {{
    border: none;
    background: transparent;
    background-color: transparent;
}}

/* Respect and restore pyside6-modern-widgets CustomTitleBar native buttons */
#CustomTitleBar QPushButton {{
    border: none;
    background-color: transparent;
    border-radius: 4px;
    padding: 0px;
    margin: 0px;
    min-width: 30px;
    min-height: 30px;
    max-width: 30px;
    max-height: 30px;
}}
#CustomTitleBar QPushButton:hover {{
    background-color: rgba(0, 0, 0, 0.08);
}}
#CustomTitleBar QPushButton:pressed {{
    background-color: rgba(0, 0, 0, 0.15);
}}

/* Modern Buttons */
QPushButton {{
    background-color: {COLOR_SURFACE};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 600;
    color: {COLOR_TEXT_MAIN};
}}
QPushButton:hover {{
    background-color: {COLOR_SURFACE_HOVER};
    border-color: {COLOR_BORDER_STRONG};
}}
QPushButton:pressed {{
    background-color: #F1F5F9;
    border-color: #94A3B8;
}}
QPushButton:disabled {{
    background-color: #F8FAFC;
    color: {COLOR_TEXT_HINT};
    border-color: {COLOR_BORDER};
}}

/* Primary Hero Buttons */
QPushButton[class="PrimaryButton"] {{
    background-color: {COLOR_ACCENT};
    color: #FFFFFF;
    border: 1px solid {COLOR_ACCENT};
    border-radius: 6px;
    font-weight: 700;
    padding: 8px 20px;
}}
QPushButton[class="PrimaryButton"]:hover {{
    background-color: {COLOR_ACCENT_HOVER};
    border-color: {COLOR_ACCENT_HOVER};
}}
QPushButton[class="PrimaryButton"]:pressed {{
    background-color: {COLOR_ACCENT_PRESSED};
    border-color: {COLOR_ACCENT_PRESSED};
}}
QPushButton[class="PrimaryButton"]:disabled {{
    background-color: #93C5FD;
    border-color: #93C5FD;
    color: #FFFFFF;
}}

/* Pill Category Filter Chips (Modern Fluent 2 Style) */
QPushButton[class="CategoryPill"] {{
    background-color: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 17px;
    padding: 6px 15px;
    font-size: 13px;
    font-weight: 600;
    color: #1E293B;
}}
QPushButton[class="CategoryPill"]:hover {{
    background-color: #F1F5F9;
    border-color: #CBD5E1;
    color: #0F172A;
}}
QPushButton[class="CategoryPill"]:checked {{
    background-color: {COLOR_ACCENT};
    border: 1px solid {COLOR_ACCENT_PRESSED};
    color: #FFFFFF;
    font-weight: 700;
}}
QPushButton[class="CategoryPill"]:checked:hover {{
    background-color: {COLOR_ACCENT_HOVER};
    border-color: {COLOR_ACCENT};
    color: #FFFFFF;
}}

/* Category Navigation Arrow Buttons */
QPushButton[class="CategoryNavArrow"] {{
    background-color: transparent;
    border: none;
    border-radius: 6px;
    font-size: 18px;
    font-weight: bold;
    color: {COLOR_TEXT_MUTED};
    padding: 0px;
}}
QPushButton[class="CategoryNavArrow"]:hover {{
    background-color: #F1F5F9;
    color: {COLOR_TEXT_MAIN};
}}
QPushButton[class="CategoryNavArrow"]:pressed {{
    background-color: #E2E8F0;
}}
QPushButton[class="CategoryNavArrow"]:disabled {{
    color: #CBD5E1;
    background-color: transparent;
}}

/* Time Interval Segment Chips in Scheduler */
QPushButton[class="IntervalChip"] {{
    background-color: {COLOR_SURFACE};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 9px 14px;
    font-size: 13px;
    font-weight: 600;
    color: {COLOR_TEXT_MAIN};
    text-align: center;
}}
QPushButton[class="IntervalChip"]:hover {{
    background-color: #F8FAFC;
    border-color: {COLOR_BORDER_STRONG};
}}
QPushButton[class="IntervalChip"]:checked {{
    background-color: {COLOR_ACCENT_LIGHT};
    border: 1.5px solid {COLOR_ACCENT};
    color: {COLOR_ACCENT};
    font-weight: 700;
}}

/* Text Input Fields */
QLineEdit {{
    background-color: {COLOR_SURFACE};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 7px 12px;
    color: {COLOR_TEXT_MAIN};
    font-size: 13px;
    font-weight: 600;
}}
QLineEdit:hover {{
    border-color: {COLOR_BORDER_STRONG};
}}
QLineEdit:focus {{
    border: 1.5px solid {COLOR_ACCENT};
    background-color: #FFFFFF;
}}

/* Modern Sleek ComboBox (下拉框) */
QComboBox {{
    background-color: {COLOR_SURFACE};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 6px 32px 6px 12px;
    color: {COLOR_TEXT_MAIN};
    font-size: 13px;
    font-weight: 600;
    min-height: 22px;
}}
QComboBox:hover {{
    background-color: #F8FAFC;
    border-color: {COLOR_BORDER_STRONG};
}}
QComboBox:focus {{
    border: 1.5px solid {COLOR_ACCENT};
    background-color: #FFFFFF;
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border: none;
    background: transparent;
}}
QComboBox::down-arrow {{
    image: url({ICONS_DIR}/chevron-down.svg);
    width: 12px;
    height: 12px;
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: #FFFFFF;
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 4px;
    outline: none;
    font-weight: 600;
    selection-background-color: {COLOR_ACCENT_LIGHT};
    selection-color: {COLOR_ACCENT};
}}
QComboBox QAbstractItemView::item {{
    min-height: 30px;
    padding: 4px 10px;
    border-radius: 4px;
}}
QComboBox QAbstractItemView::item:hover {{
    background-color: #F1F5F9;
    color: {COLOR_ACCENT};
}}

/* Modern SpinBox (数值调节框) */
QSpinBox {{
    background-color: {COLOR_SURFACE};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 6px 26px 6px 10px;
    color: {COLOR_TEXT_MAIN};
    font-size: 13px;
    font-weight: 600;
    min-height: 20px;
}}
QSpinBox:hover {{
    background-color: #F8FAFC;
    border-color: {COLOR_BORDER_STRONG};
}}
QSpinBox:focus {{
    border: 1.5px solid {COLOR_ACCENT};
    background-color: #FFFFFF;
}}
QSpinBox::up-button, QSpinBox::down-button {{
    subcontrol-origin: border;
    width: 22px;
    background: transparent;
    border: none;
}}
QSpinBox::up-button {{
    subcontrol-position: top right;
    border-top-right-radius: 6px;
}}
QSpinBox::down-button {{
    subcontrol-position: bottom right;
    border-bottom-right-radius: 6px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: {COLOR_ACCENT_LIGHT};
}}
QSpinBox::up-arrow {{
    image: url({ICONS_DIR}/chevron-up.svg);
    width: 10px;
    height: 10px;
}}
QSpinBox::down-arrow {{
    image: url({ICONS_DIR}/chevron-down.svg);
    width: 10px;
    height: 10px;
}}

/* CheckBoxes with Crisp SVG Graphics */
QCheckBox {{
    spacing: 8px;
    color: {COLOR_TEXT_MAIN};
    background: transparent;
    border: none;
    font-size: 13px;
    font-weight: 600;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: none;
    background: transparent;
}}
QCheckBox::indicator:unchecked {{
    image: url({ICONS_DIR}/checkbox-unchecked.svg);
}}
QCheckBox::indicator:checked {{
    image: url({ICONS_DIR}/checkbox-checked.svg);
}}

/* RadioButtons with Crisp SVG Graphics */
QRadioButton {{
    spacing: 8px;
    color: {COLOR_TEXT_MAIN};
    background: transparent;
    border: none;
    font-size: 13px;
    font-weight: 600;
}}
QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: none;
    background: transparent;
}}
QRadioButton::indicator:unchecked {{
    image: url({ICONS_DIR}/radio-unchecked.svg);
}}
QRadioButton::indicator:checked {{
    image: url({ICONS_DIR}/radio-checked.svg);
}}

/* Sliders */
QSlider::groove:horizontal {{
    height: 4px;
    background: #E2E8F0;
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {COLOR_ACCENT};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: #FFFFFF;
    border: 2px solid {COLOR_ACCENT};
    width: 16px;
    margin-top: -6px;
    margin-bottom: -6px;
    border-radius: 8px;
}}
QSlider::handle:horizontal:hover {{
    background: #EFF6FF;
}}

/* Progress Bar */
QProgressBar {{
    border: none;
    background-color: #E2E8F0;
    border-radius: 3px;
    height: 6px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {COLOR_ACCENT};
    border-radius: 3px;
}}

/* Tooltips */
QToolTip {{
    background-color: #1E293B;
    color: #F8FAFC;
    border: none;
    border-radius: 4px;
    padding: 5px 8px;
    font-size: 12px;
    font-weight: 600;
}}

/* Context Menus - Modern Windows 11 Fluent Style */
QMenu {{
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 6px;
}}
QMenu::item {{
    padding: 8px 24px 8px 38px;
    border-radius: 6px;
    color: #0B0F19;
    font-size: 13px;
    margin: 2px 2px;
}}
QMenu::item:selected {{
    background-color: #EFF6FF;
    color: #0078D4;
}}
QMenu::icon {{
    left: 12px;
}}
QMenu::separator {{
    height: 1px;
    background: #E2E8F0;
    margin: 4px 6px;
}}
"""
