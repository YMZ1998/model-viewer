from PyQt5.QtGui import QColor, QPalette


DEFAULT_THEME_NAME = "midnight_blue"

THEMES = {
    "midnight_blue": {
        "label": "Midnight Blue",
        "window": "#1e222b",
        "window_alt": "#1b2029",
        "panel": "#202632",
        "panel_alt": "#171c24",
        "base": "#151922",
        "base_alt": "#1c212c",
        "border": "#313847",
        "border_soft": "#3a4253",
        "text": "#e6e8ec",
        "text_muted": "#9eabbf",
        "disabled": "#7f8899",
        "accent": "#3d7eff",
        "accent_hover": "#4a88ff",
        "accent_soft": "#334f84",
        "accent_text": "#ffffff",
        "pill_bg": "#263246",
        "pill_border": "#344767",
        "pill_text": "#bdd1ff",
        "viewport": "#11151d",
        "slider": "#76a3ff",
    },
    "graphite_orange": {
        "label": "Graphite Orange",
        "window": "#232323",
        "window_alt": "#1d1d1d",
        "panel": "#2a2a2a",
        "panel_alt": "#181818",
        "base": "#141414",
        "base_alt": "#222222",
        "border": "#3b3b3b",
        "border_soft": "#4a4a4a",
        "text": "#f0f0f0",
        "text_muted": "#b4b4b4",
        "disabled": "#7d7d7d",
        "accent": "#ff8a3d",
        "accent_hover": "#ff9a57",
        "accent_soft": "#6b4428",
        "accent_text": "#ffffff",
        "pill_bg": "#443326",
        "pill_border": "#6d4a2c",
        "pill_text": "#ffd2ae",
        "viewport": "#101010",
        "slider": "#ff9e57",
    },
    "studio_light": {
        "label": "Studio Light",
        "window": "#eef2f7",
        "window_alt": "#e6ebf2",
        "panel": "#ffffff",
        "panel_alt": "#f5f8fc",
        "base": "#ffffff",
        "base_alt": "#edf2f8",
        "border": "#cfd7e3",
        "border_soft": "#b9c5d6",
        "text": "#1d2532",
        "text_muted": "#5f6f84",
        "disabled": "#9aa7b8",
        "accent": "#2d66f6",
        "accent_hover": "#3b74ff",
        "accent_soft": "#dce7ff",
        "accent_text": "#ffffff",
        "pill_bg": "#e7eefc",
        "pill_border": "#bfd0fb",
        "pill_text": "#2c57c3",
        "viewport": "#d9e2ef",
        "slider": "#4b80ff",
    },
    "engineering_green": {
        "label": "Engineering Green",
        "window": "#1d2421",
        "window_alt": "#18201c",
        "panel": "#222d28",
        "panel_alt": "#161d19",
        "base": "#111713",
        "base_alt": "#1d2621",
        "border": "#33413a",
        "border_soft": "#43544b",
        "text": "#e3ece6",
        "text_muted": "#9cb4a5",
        "disabled": "#74877c",
        "accent": "#39b87f",
        "accent_hover": "#49cb90",
        "accent_soft": "#264f3e",
        "accent_text": "#ffffff",
        "pill_bg": "#203c32",
        "pill_border": "#2d614e",
        "pill_text": "#b7ecd2",
        "viewport": "#0f1411",
        "slider": "#58d49f",
    },
}


def get_theme_names():
    return list(THEMES.keys())


def get_theme_label(theme_name):
    theme = THEMES.get(theme_name, THEMES[DEFAULT_THEME_NAME])
    return theme["label"]


def _palette_color(value):
    return QColor(value)


def _build_stylesheet(theme):
    return """
        QWidget {{
            background: {window};
            color: {text};
            font-size: 13px;
        }}
        QMainWindow, QMenuBar, QMenu, QStatusBar, QToolBar {{
            background: {window_alt};
        }}
        QMenuBar {{
            border-bottom: 1px solid {border};
        }}
        QMenuBar::item {{
            padding: 6px 10px;
            background: transparent;
        }}
        QMenuBar::item:selected, QMenu::item:selected {{
            background: {base_alt};
            border-radius: 4px;
        }}
        QMenu {{
            border: 1px solid {border};
            padding: 6px;
        }}
        QMenu::item {{
            padding: 7px 26px 7px 12px;
            border-radius: 4px;
        }}
        QToolBar {{
            border: none;
            border-bottom: 1px solid {border};
            spacing: 6px;
            padding: 6px 8px;
        }}
        QToolButton, QPushButton {{
            background: {panel};
            border: 1px solid {border_soft};
            border-radius: 6px;
            padding: 7px 12px;
        }}
        QToolButton:hover, QPushButton:hover {{
            background: {base_alt};
            border-color: {accent};
        }}
        QToolButton:checked, QPushButton:checked {{
            background: {accent};
            border-color: {accent_hover};
            color: {accent_text};
        }}
        QPushButton[role="primary"] {{
            background: {accent};
            border-color: {accent_hover};
            color: {accent_text};
            font-weight: 600;
        }}
        QPushButton[role="primary"]:hover {{
            background: {accent_hover};
        }}
        QGroupBox {{
            background: {panel};
            border: 1px solid {border};
            border-radius: 10px;
            margin-top: 12px;
            padding-top: 14px;
            font-weight: 600;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
            color: {text};
        }}
        QLineEdit, QComboBox, QTextEdit, QListWidget, QAbstractSpinBox {{
            background: {base};
            border: 1px solid {border_soft};
            border-radius: 6px;
            padding: 6px 8px;
            selection-background-color: {accent};
            selection-color: {accent_text};
        }}
        QTextEdit, QListWidget {{
            padding: 8px;
        }}
        QListWidget::item {{
            padding: 6px 8px;
            border-radius: 6px;
        }}
        QListWidget::item:selected {{
            background: {accent_soft};
            color: {text};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 22px;
        }}
        QCheckBox {{
            spacing: 8px;
        }}
        QSlider::groove:horizontal {{
            height: 6px;
            border-radius: 3px;
            background: {border};
        }}
        QSlider::handle:horizontal {{
            width: 16px;
            margin: -6px 0;
            border-radius: 8px;
            background: {slider};
        }}
        QScrollArea, QScrollArea > QWidget > QWidget {{
            border: none;
            background: transparent;
        }}
        QSplitter::handle {{
            background: {window_alt};
        }}
        QLabel[role="sectionTitle"] {{
            font-size: 12px;
            color: {text_muted};
            font-weight: 600;
            text-transform: uppercase;
        }}
        QLabel[role="summaryTitle"] {{
            font-size: 18px;
            font-weight: 700;
            color: {text};
        }}
        QLabel[role="summaryMeta"] {{
            color: {text_muted};
        }}
        QLabel[role="statusPill"] {{
            background: {pill_bg};
            border: 1px solid {pill_border};
            border-radius: 10px;
            padding: 3px 8px;
            color: {pill_text};
            font-size: 12px;
            font-weight: 600;
        }}
        QStatusBar {{
            border-top: 1px solid {border};
            min-height: 24px;
        }}
        QStatusBar QLabel {{
            color: {text_muted};
        }}
        QOpenGLWidget#viewportWidget {{
            border: 1px solid {border};
            border-radius: 12px;
            background: {viewport};
        }}
        QWidget#sidePanel {{
            background: {panel_alt};
        }}
        QWidget#summaryCard {{
            background: {panel};
            border: 1px solid {border};
            border-radius: 12px;
        }}
        """.format(**theme)


def apply_theme(app, theme_name=DEFAULT_THEME_NAME):
    """Apply a named application theme."""
    theme = THEMES.get(theme_name, THEMES[DEFAULT_THEME_NAME])
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.Window, _palette_color(theme["window"]))
    palette.setColor(QPalette.WindowText, _palette_color(theme["text"]))
    palette.setColor(QPalette.Base, _palette_color(theme["base"]))
    palette.setColor(QPalette.AlternateBase, _palette_color(theme["base_alt"]))
    palette.setColor(QPalette.ToolTipBase, _palette_color(theme["panel"]))
    palette.setColor(QPalette.ToolTipText, _palette_color(theme["text"]))
    palette.setColor(QPalette.Text, _palette_color(theme["text"]))
    palette.setColor(QPalette.Button, _palette_color(theme["panel"]))
    palette.setColor(QPalette.ButtonText, _palette_color(theme["text"]))
    palette.setColor(QPalette.BrightText, _palette_color(theme["accent_text"]))
    palette.setColor(QPalette.Highlight, _palette_color(theme["accent"]))
    palette.setColor(QPalette.HighlightedText, _palette_color(theme["accent_text"]))
    palette.setColor(QPalette.Link, _palette_color(theme["accent"]))
    palette.setColor(QPalette.Disabled, QPalette.Text, _palette_color(theme["disabled"]))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, _palette_color(theme["disabled"]))
    app.setPalette(palette)
    app.setStyleSheet(_build_stylesheet(theme))
    return theme_name if theme_name in THEMES else DEFAULT_THEME_NAME
