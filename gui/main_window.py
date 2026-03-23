"""
Main application window for the model viewer.
"""
import os
from datetime import datetime

from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtWidgets import (
    QAction,
    QActionGroup,
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QWidget,
)

from gui.control_panel import ControlPanel
from gui.gl_widget import GLWidget


class MainWindow(QMainWindow):
    """Primary application window."""

    SUPPORTED_EXTENSIONS = {'.obj', '.stl', '.ply', '.xyz'}
    MAX_RECENT_FILES = 10
    STANDARD_VIEW_LABELS = {
        'front': 'Front',
        'back': 'Back',
        'left': 'Left',
        'right': 'Right',
        'top': 'Top',
        'bottom': 'Bottom',
        'isometric': 'Isometric',
    }

    def __init__(self):
        super().__init__()

        self.settings = QSettings("OpenAI", "PyQtGLMeshViewer")
        self.recent_files = self._load_recent_files()
        self.show_axes = self.settings.value("view/show_axes", True, type=bool)
        self.show_grid = self.settings.value("view/show_grid", False, type=bool)
        self.current_standard_view = 'isometric'

        self.setWindowTitle("PyQtGLMeshViewer - 3D Model Viewer")
        self.setGeometry(100, 100, 1280, 800)
        self.setAcceptDrops(True)

        self._create_central_widget()
        self._create_menu_bar()
        self._create_status_bar()

        self.set_show_axes(self.show_axes)
        self.set_show_grid(self.show_grid)
        self.control_panel.set_standard_view(self.current_standard_view)

    def _create_central_widget(self):
        """Create the main content area."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QHBoxLayout()
        central_widget.setLayout(layout)

        self.gl_widget = GLWidget()
        layout.addWidget(self.gl_widget, 3)

        self.control_panel = ControlPanel(self.gl_widget)
        layout.addWidget(self.control_panel, 1)

    def _create_menu_bar(self):
        """Create the window menu bar."""
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")

        open_action = QAction("Open File...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open_file)
        file_menu.addAction(open_action)

        self.recent_files_menu = file_menu.addMenu("Recent Files")
        self._update_recent_files_menu()

        file_menu.addSeparator()

        screenshot_action = QAction("Export Screenshot...", self)
        screenshot_action.setShortcut("Ctrl+S")
        screenshot_action.triggered.connect(self.export_screenshot)
        file_menu.addAction(screenshot_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menubar.addMenu("View")

        fit_action = QAction("Fit View", self)
        fit_action.setShortcut("F")
        fit_action.triggered.connect(self.fit_view)
        view_menu.addAction(fit_action)

        view_menu.addSeparator()

        standard_views_menu = view_menu.addMenu("Standard Views")
        self.standard_view_action_group = QActionGroup(self)
        for view_name, label in self.STANDARD_VIEW_LABELS.items():
            action = QAction(label, self)
            action.triggered.connect(lambda checked=False, name=view_name: self.set_standard_view(name))
            if view_name == 'front':
                action.setShortcut("1")
            elif view_name == 'right':
                action.setShortcut("3")
            elif view_name == 'top':
                action.setShortcut("7")
            self.standard_view_action_group.addAction(action)
            standard_views_menu.addAction(action)

        view_menu.addSeparator()

        self.show_axes_action = QAction("Show Axes", self)
        self.show_axes_action.setCheckable(True)
        self.show_axes_action.toggled.connect(self.set_show_axes)
        view_menu.addAction(self.show_axes_action)

        self.show_grid_action = QAction("Show Grid", self)
        self.show_grid_action.setCheckable(True)
        self.show_grid_action.toggled.connect(self.set_show_grid)
        view_menu.addAction(self.show_grid_action)

        help_menu = menubar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _create_status_bar(self):
        """Create the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _load_recent_files(self):
        """Load recent files from settings."""
        recent_files = self.settings.value("recent_files", [])
        if isinstance(recent_files, str):
            recent_files = [recent_files] if recent_files else []
        if recent_files is None:
            recent_files = []
        return [path for path in recent_files if isinstance(path, str) and path]

    def _save_settings(self):
        """Persist settings to disk."""
        self.settings.setValue("recent_files", self.recent_files)
        self.settings.setValue("view/show_axes", self.show_axes)
        self.settings.setValue("view/show_grid", self.show_grid)

    def _update_recent_files_menu(self):
        """Refresh the recent-files submenu."""
        self.recent_files_menu.clear()

        if not self.recent_files:
            empty_action = QAction("No Recent Files", self)
            empty_action.setEnabled(False)
            self.recent_files_menu.addAction(empty_action)
            return

        for file_path in self.recent_files:
            action = QAction(file_path, self)
            action.triggered.connect(lambda checked=False, path=file_path: self.open_model_file(path, from_recent=True))
            self.recent_files_menu.addAction(action)

    def _add_recent_file(self, file_path):
        """Insert a file into the recent-files list."""
        normalized_path = os.path.normpath(file_path)
        self.recent_files = [path for path in self.recent_files if os.path.normpath(path) != normalized_path]
        self.recent_files.insert(0, file_path)
        self.recent_files = self.recent_files[:self.MAX_RECENT_FILES]
        self._save_settings()
        self._update_recent_files_menu()

    def _remove_recent_file(self, file_path):
        """Remove a file from the recent list."""
        normalized_path = os.path.normpath(file_path)
        original_length = len(self.recent_files)
        self.recent_files = [path for path in self.recent_files if os.path.normpath(path) != normalized_path]
        if len(self.recent_files) != original_length:
            self._save_settings()
            self._update_recent_files_menu()

    def _extract_supported_path(self, event):
        """Return the first supported local file path from a drag/drop event."""
        mime_data = event.mimeData()
        if not mime_data.hasUrls():
            return None

        for url in mime_data.urls():
            if not url.isLocalFile():
                continue
            path = url.toLocalFile()
            ext = os.path.splitext(path)[1].lower()
            if ext in self.SUPPORTED_EXTENSIONS:
                return path
        return None

    def dragEnterEvent(self, event):
        """Accept supported model files."""
        if self._extract_supported_path(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Open a dropped model file."""
        file_path = self._extract_supported_path(event)
        if not file_path:
            event.ignore()
            return
        self.open_model_file(file_path)
        event.acceptProposedAction()

    def closeEvent(self, event):
        """Persist settings on close."""
        self._save_settings()
        super().closeEvent(event)

    def _on_open_file(self):
        """Show the file picker."""
        self.control_panel._on_load_file()

    def open_model_file(self, file_path, from_recent=False):
        """Open a model and update recent-file state."""
        if not file_path:
            return False

        if not os.path.exists(file_path):
            QMessageBox.warning(self, "File Not Found", f"The file does not exist:\n{file_path}")
            if from_recent:
                self._remove_recent_file(file_path)
            return False

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            QMessageBox.warning(self, "Unsupported File", f"Unsupported file format: {ext}")
            return False

        success = self.control_panel.load_file(file_path)
        if success:
            self._add_recent_file(file_path)
            self.status_bar.showMessage(f"Loaded: {file_path}", 4000)
        elif from_recent:
            self._remove_recent_file(file_path)

        return success

    def fit_view(self):
        """Fit the current scene into view."""
        self.gl_widget.fit_view()
        self.status_bar.showMessage("Fit view", 2000)

    def set_standard_view(self, view_name):
        """Switch to a standard view."""
        if view_name not in self.STANDARD_VIEW_LABELS:
            return
        self.current_standard_view = view_name
        self.gl_widget.set_standard_view(view_name)
        self.control_panel.set_standard_view(view_name)
        self.status_bar.showMessage(f"View: {self.STANDARD_VIEW_LABELS[view_name]}", 2000)

    def set_show_axes(self, show):
        """Toggle axes visibility and persist the preference."""
        self.show_axes = bool(show)
        self.gl_widget.set_show_axes(self.show_axes)

        self.show_axes_action.blockSignals(True)
        self.show_axes_action.setChecked(self.show_axes)
        self.show_axes_action.blockSignals(False)

        self.control_panel.set_scene_state(self.show_axes, self.show_grid, self.current_standard_view)
        self._save_settings()

    def set_show_grid(self, show):
        """Toggle grid visibility and persist the preference."""
        self.show_grid = bool(show)
        self.gl_widget.set_show_grid(self.show_grid)

        self.show_grid_action.blockSignals(True)
        self.show_grid_action.setChecked(self.show_grid)
        self.show_grid_action.blockSignals(False)

        self.control_panel.set_scene_state(self.show_axes, self.show_grid, self.current_standard_view)
        self._save_settings()

    def export_screenshot(self):
        """Export the current viewport to a PNG file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"viewer_screenshot_{timestamp}.png"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Screenshot",
            default_name,
            "PNG Image (*.png)",
        )
        if not file_path:
            return False

        if not file_path.lower().endswith('.png'):
            file_path += '.png'

        success = self.gl_widget.capture_viewport(file_path)
        if success:
            self.status_bar.showMessage(f"Screenshot saved: {file_path}", 4000)
            return True

        QMessageBox.critical(self, "Export Failed", "Could not save the screenshot.")
        return False

    def _on_about(self):
        """Show the About dialog."""
        QMessageBox.about(
            self,
            "About PyQtGLMeshViewer",
            "PyQtGLMeshViewer\n\n"
            "A lightweight desktop viewer for meshes and point clouds.\n\n"
            "Features:\n"
            "- Drag and drop loading\n"
            "- Recent files\n"
            "- Fit view and standard views\n"
            "- Axes and ground grid\n"
            "- Screenshot export",
        )
