from PyQt5.QtGui import QColor, QPalette


def apply_theme(app):
    """Apply a polished dark desktop theme."""
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#1e222b"))
    palette.setColor(QPalette.WindowText, QColor("#e6e8ec"))
    palette.setColor(QPalette.Base, QColor("#151922"))
    palette.setColor(QPalette.AlternateBase, QColor("#1c212c"))
    palette.setColor(QPalette.ToolTipBase, QColor("#232937"))
    palette.setColor(QPalette.ToolTipText, QColor("#eef2f7"))
    palette.setColor(QPalette.Text, QColor("#dde3ec"))
    palette.setColor(QPalette.Button, QColor("#252b37"))
    palette.setColor(QPalette.ButtonText, QColor("#e6e8ec"))
    palette.setColor(QPalette.BrightText, QColor("#ffffff"))
    palette.setColor(QPalette.Highlight, QColor("#3d7eff"))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.Link, QColor("#79a6ff"))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor("#7f8899"))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#7f8899"))
    app.setPalette(palette)

    app.setStyleSheet(
        """
        QWidget {
            background: #1e222b;
            color: #e6e8ec;
            font-size: 13px;
        }
        QMainWindow, QMenuBar, QMenu, QStatusBar, QToolBar {
            background: #1b2029;
        }
        QMenuBar {
            border-bottom: 1px solid #313847;
        }
        QMenuBar::item {
            padding: 6px 10px;
            background: transparent;
        }
        QMenuBar::item:selected, QMenu::item:selected {
            background: #2d3443;
            border-radius: 4px;
        }
        QMenu {
            border: 1px solid #313847;
            padding: 6px;
        }
        QMenu::item {
            padding: 7px 26px 7px 12px;
            border-radius: 4px;
        }
        QToolBar {
            border: none;
            border-bottom: 1px solid #313847;
            spacing: 6px;
            padding: 6px 8px;
        }
        QToolButton, QPushButton {
            background: #2a3140;
            border: 1px solid #3a4253;
            border-radius: 6px;
            padding: 7px 12px;
        }
        QToolButton:hover, QPushButton:hover {
            background: #343d50;
            border-color: #4b5b7c;
        }
        QToolButton:checked, QPushButton:checked {
            background: #3d7eff;
            border-color: #4b88ff;
            color: white;
        }
        QPushButton[role="primary"] {
            background: #3d7eff;
            border-color: #4b88ff;
            color: white;
            font-weight: 600;
        }
        QPushButton[role="primary"]:hover {
            background: #4a88ff;
        }
        QGroupBox {
            background: #202632;
            border: 1px solid #313847;
            border-radius: 10px;
            margin-top: 12px;
            padding-top: 14px;
            font-weight: 600;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
            color: #f3f6fb;
        }
        QLineEdit, QComboBox, QTextEdit, QListWidget, QAbstractSpinBox {
            background: #151922;
            border: 1px solid #343c4b;
            border-radius: 6px;
            padding: 6px 8px;
            selection-background-color: #3d7eff;
        }
        QTextEdit, QListWidget {
            padding: 8px;
        }
        QListWidget::item {
            padding: 6px 8px;
            border-radius: 6px;
        }
        QListWidget::item:selected {
            background: #334f84;
        }
        QComboBox::drop-down {
            border: none;
            width: 22px;
        }
        QCheckBox {
            spacing: 8px;
        }
        QSlider::groove:horizontal {
            height: 6px;
            border-radius: 3px;
            background: #2f3746;
        }
        QSlider::handle:horizontal {
            width: 16px;
            margin: -6px 0;
            border-radius: 8px;
            background: #76a3ff;
        }
        QScrollArea, QScrollArea > QWidget > QWidget {
            border: none;
            background: transparent;
        }
        QSplitter::handle {
            background: #222834;
        }
        QLabel[role="sectionTitle"] {
            font-size: 12px;
            color: #9eabbf;
            font-weight: 600;
            text-transform: uppercase;
        }
        QLabel[role="summaryTitle"] {
            font-size: 18px;
            font-weight: 700;
            color: #f5f7fb;
        }
        QLabel[role="summaryMeta"] {
            color: #9eabbf;
        }
        QLabel[role="statusPill"] {
            background: #263246;
            border: 1px solid #344767;
            border-radius: 10px;
            padding: 3px 8px;
            color: #bdd1ff;
            font-size: 12px;
            font-weight: 600;
        }
        QStatusBar {
            border-top: 1px solid #313847;
            min-height: 24px;
        }
        QStatusBar QLabel {
            color: #aab4c4;
        }
        QOpenGLWidget#viewportWidget {
            border: 1px solid #313847;
            border-radius: 12px;
            background: #11151d;
        }
        QWidget#sidePanel {
            background: #171c24;
        }
        QWidget#summaryCard {
            background: #202632;
            border: 1px solid #313847;
            border-radius: 12px;
        }
        """
    )
