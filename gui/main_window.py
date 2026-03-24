import os
from datetime import datetime

from PyQt5.QtWidgets import (
    QAction,
    QActionGroup,
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from gui.app_settings import MAX_RECENT_FILES, ViewerSettings, create_qsettings
from gui.control_panel import ControlPanel
from gui.gl_widget import GLWidget
from gui.theme import DEFAULT_THEME_NAME, apply_theme, get_theme_label, get_theme_names


class MainWindow(QMainWindow):
    SUPPORTED_EXTENSIONS = {'.obj', '.stl', '.ply', '.xyz'}
    STANDARD_VIEW_LABELS = {
        'front': 'Front',
        'back': 'Back',
        'left': 'Left',
        'right': 'Right',
        'top': 'Top',
        'bottom': 'Bottom',
        'isometric': 'Isometric',
    }
    INSPECT_ACTIONS = {
        'select': 'Select',
        'distance': 'Distance',
        'angle': 'Angle',
        'face_area': 'Face Area',
    }
    PICK_PREFERENCES = {
        'balanced': 'Balanced',
        'prefer_point': 'Prefer Point',
        'prefer_face': 'Prefer Face',
    }
    PROJECTION_LABELS = {
        'perspective': 'Perspective',
        'orthographic': 'Orthographic',
    }
    VISUAL_PRESET_LABELS = {
        'studio_dark': 'Studio Dark',
        'studio_light': 'Studio Light',
        'blueprint': 'Blueprint',
        'inspection_lab': 'Inspection Lab',
    }
    SECTION_AXIS_LABELS = {
        'x': 'X',
        'y': 'Y',
        'z': 'Z',
    }
    THEME_LABELS = dict((name, get_theme_label(name)) for name in get_theme_names())

    def __init__(self):
        super().__init__()
        self.settings = create_qsettings()
        self.viewer_settings = ViewerSettings.from_qsettings(self.settings)
        self.recent_files = list(self.viewer_settings.recent_files)
        self.show_axes = self.viewer_settings.show_axes
        self.show_grid = self.viewer_settings.show_grid
        self.projection_mode = self.viewer_settings.projection_mode
        self.visual_preset = self.viewer_settings.visual_preset
        self.section_plane_enabled = self.viewer_settings.section_plane_enabled
        self.section_plane_axis = self.viewer_settings.section_plane_axis
        self.section_plane_offset_ratio = self.viewer_settings.section_plane_offset_ratio
        self.section_plane_inverted = self.viewer_settings.section_plane_inverted
        self.mesh_opacity = self.viewer_settings.mesh_opacity
        self.point_opacity = self.viewer_settings.point_opacity
        self.backface_culling = self.viewer_settings.backface_culling
        self.point_size = self.viewer_settings.point_size
        self.line_width = self.viewer_settings.line_width
        self.show_bounding_box = self.viewer_settings.show_bounding_box
        self.show_model_center = self.viewer_settings.show_model_center
        self.show_vertex_normals = self.viewer_settings.show_vertex_normals
        self.show_face_normals = self.viewer_settings.show_face_normals
        self.pick_preference = self.viewer_settings.pick_preference
        self.current_theme = self.viewer_settings.theme_name or DEFAULT_THEME_NAME
        self.current_standard_view = 'isometric'
        self.current_file_path = None

        self.setWindowTitle("PyQtGLMeshViewer")
        self.setGeometry(100, 100, 1400, 860)
        self.setAcceptDrops(True)

        self._create_central_widget()
        self._create_menu_bar()
        self._create_toolbar()
        self._create_status_bar()

        self.gl_widget.status_message.connect(self.show_status_message)
        self.gl_widget.inspection_state_changed.connect(self._sync_inspect_actions)

        self.set_theme(self.current_theme)
        self.set_show_axes(self.show_axes)
        self.set_show_grid(self.show_grid)
        self.set_projection_mode(self.projection_mode)
        self.set_visual_preset(self.visual_preset)
        self.set_section_plane_axis(self.section_plane_axis, save=False)
        self.set_section_plane_offset_ratio(self.section_plane_offset_ratio, save=False)
        self.set_section_plane_inverted(self.section_plane_inverted, save=False)
        self.set_section_plane_enabled(self.section_plane_enabled)
        self.set_show_bounding_box(self.show_bounding_box)
        self.set_show_model_center(self.show_model_center)
        self.set_show_vertex_normals(self.show_vertex_normals)
        self.set_show_face_normals(self.show_face_normals)
        self.set_mesh_opacity(self.mesh_opacity)
        self.set_point_opacity(self.point_opacity)
        self.set_backface_culling(self.backface_culling)
        self.set_point_size(self.point_size)
        self.set_line_width(self.line_width)
        self.set_pick_preference(self.pick_preference)
        self.control_panel.set_standard_view(self.current_standard_view)

    def _create_central_widget(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        splitter = QSplitter()
        splitter.setChildrenCollapsible(False)

        self.gl_widget = GLWidget()
        self.gl_widget.setObjectName("viewportWidget")
        splitter.addWidget(self.gl_widget)

        self.control_panel = ControlPanel(self.gl_widget)
        self.control_panel.setObjectName("sidePanel")

        panel_scroll = QScrollArea()
        panel_scroll.setWidgetResizable(True)
        panel_scroll.setWidget(self.control_panel)
        panel_scroll.setMinimumWidth(360)
        splitter.addWidget(panel_scroll)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([1020, 380])

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        layout.addWidget(splitter)

    def _create_menu_bar(self):
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

        report_action = QAction("Export Inspection Report...", self)
        report_action.triggered.connect(self.export_inspection_report)
        file_menu.addAction(report_action)

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

        self.show_axes_action = QAction("Show Axes", self, checkable=True)
        self.show_axes_action.toggled.connect(self.set_show_axes)
        view_menu.addAction(self.show_axes_action)

        self.show_grid_action = QAction("Show Grid", self, checkable=True)
        self.show_grid_action.toggled.connect(self.set_show_grid)
        view_menu.addAction(self.show_grid_action)

        projection_menu = view_menu.addMenu("Projection")
        self.projection_action_group = QActionGroup(self)
        self.projection_action_group.setExclusive(True)
        self.projection_actions = {}
        for key, label in self.PROJECTION_LABELS.items():
            action = QAction(label, self, checkable=True)
            action.triggered.connect(lambda checked=False, value=key: self.set_projection_mode(value))
            self.projection_action_group.addAction(action)
            projection_menu.addAction(action)
            self.projection_actions[key] = action

        visual_preset_menu = view_menu.addMenu("Visual Preset")
        self.visual_preset_action_group = QActionGroup(self)
        self.visual_preset_action_group.setExclusive(True)
        self.visual_preset_actions = {}
        for key, label in self.VISUAL_PRESET_LABELS.items():
            action = QAction(label, self, checkable=True)
            action.triggered.connect(lambda checked=False, value=key: self.set_visual_preset(value))
            self.visual_preset_action_group.addAction(action)
            visual_preset_menu.addAction(action)
            self.visual_preset_actions[key] = action

        section_menu = view_menu.addMenu("Section Plane")
        self.section_plane_action = QAction("Enable Section Plane", self, checkable=True)
        self.section_plane_action.toggled.connect(self.set_section_plane_enabled)
        section_menu.addAction(self.section_plane_action)
        reset_section_action = QAction("Reset Section Plane", self)
        reset_section_action.triggered.connect(self.reset_section_plane)
        section_menu.addAction(reset_section_action)

        theme_menu = view_menu.addMenu("Theme")
        self.theme_action_group = QActionGroup(self)
        self.theme_action_group.setExclusive(True)
        self.theme_actions = {}
        for theme_name, label in self.THEME_LABELS.items():
            action = QAction(label, self, checkable=True)
            action.triggered.connect(lambda checked=False, value=theme_name: self.set_theme(value))
            self.theme_action_group.addAction(action)
            theme_menu.addAction(action)
            self.theme_actions[theme_name] = action

        inspect_menu = menubar.addMenu("Inspect")
        self.inspect_mode_action = QAction("Inspection Mode", self, checkable=True)
        self.inspect_mode_action.toggled.connect(self.gl_widget.set_inspection_mode)
        inspect_menu.addAction(self.inspect_mode_action)
        inspect_menu.addSeparator()

        action_menu = inspect_menu.addMenu("Tool")
        self.inspect_action_group = QActionGroup(self)
        self.inspect_action_group.setExclusive(True)
        self.inspect_action_actions = {}
        for key, label in self.INSPECT_ACTIONS.items():
            action = QAction(label, self, checkable=True)
            action.triggered.connect(lambda checked=False, value=key: self.gl_widget.set_inspection_action_mode(value))
            self.inspect_action_group.addAction(action)
            action_menu.addAction(action)
            self.inspect_action_actions[key] = action
        self.inspect_action_actions['select'].setChecked(True)

        pick_pref_menu = inspect_menu.addMenu("Auto Pick Preference")
        self.pick_preference_group = QActionGroup(self)
        self.pick_preference_group.setExclusive(True)
        self.pick_preference_actions = {}
        for key, label in self.PICK_PREFERENCES.items():
            action = QAction(label, self, checkable=True)
            action.triggered.connect(lambda checked=False, value=key: self.set_pick_preference(value))
            self.pick_preference_group.addAction(action)
            pick_pref_menu.addAction(action)
            self.pick_preference_actions[key] = action

        inspect_menu.addSeparator()

        self.show_bounding_box_action = QAction("Show Bounding Box", self, checkable=True)
        self.show_bounding_box_action.toggled.connect(self.set_show_bounding_box)
        inspect_menu.addAction(self.show_bounding_box_action)

        self.show_model_center_action = QAction("Show Model Center", self, checkable=True)
        self.show_model_center_action.toggled.connect(self.set_show_model_center)
        inspect_menu.addAction(self.show_model_center_action)

        self.show_vertex_normals_action = QAction("Show Vertex Normals", self, checkable=True)
        self.show_vertex_normals_action.toggled.connect(self.set_show_vertex_normals)
        inspect_menu.addAction(self.show_vertex_normals_action)

        self.show_face_normals_action = QAction("Show Face Normals", self, checkable=True)
        self.show_face_normals_action.toggled.connect(self.set_show_face_normals)
        inspect_menu.addAction(self.show_face_normals_action)

        inspect_menu.addSeparator()

        export_inspect_action = QAction("Export Inspection Report...", self)
        export_inspect_action.triggered.connect(self.export_inspection_report)
        inspect_menu.addAction(export_inspect_action)

        help_menu = menubar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _create_toolbar(self):
        self.toolbar = QToolBar("Main Toolbar", self)
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)
        self.addToolBar(self.toolbar)

        open_action = QAction("Open", self)
        open_action.triggered.connect(self._on_open_file)
        self.toolbar.addAction(open_action)

        fit_action = QAction("Fit", self)
        fit_action.triggered.connect(self.fit_view)
        self.toolbar.addAction(fit_action)

        self.toolbar_projection_action = QAction("Ortho", self)
        self.toolbar_projection_action.setCheckable(True)
        self.toolbar_projection_action.toggled.connect(
            lambda checked: self.set_projection_mode('orthographic' if checked else 'perspective')
        )
        self.toolbar.addAction(self.toolbar_projection_action)

        screenshot_action = QAction("Screenshot", self)
        screenshot_action.triggered.connect(self.export_screenshot)
        self.toolbar.addAction(screenshot_action)

        self.toolbar.addSeparator()

        self.toolbar_inspect_action = QAction("Inspect", self)
        self.toolbar_inspect_action.setCheckable(True)
        self.toolbar_inspect_action.toggled.connect(self.gl_widget.set_inspection_mode)
        self.toolbar.addAction(self.toolbar_inspect_action)

        report_action = QAction("Export Report", self)
        report_action.triggered.connect(self.export_inspection_report)
        self.toolbar.addAction(report_action)

        self.toolbar.addSeparator()

        self.toolbar_theme_action = QAction("Next Theme", self)
        self.toolbar_theme_action.triggered.connect(self.cycle_theme)
        self.toolbar.addAction(self.toolbar_theme_action)

    def _create_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.file_status_label = QLabel("No file loaded")
        self.mode_status_label = QLabel("Browse")
        self.mode_status_label.setProperty("role", "statusPill")
        self.pick_status_label = QLabel("Pick: Balanced")
        self.pick_status_label.setProperty("role", "statusPill")
        self.projection_status_label = QLabel("Projection: " + self.PROJECTION_LABELS.get(self.projection_mode, 'Perspective'))
        self.projection_status_label.setProperty("role", "statusPill")
        self.visual_status_label = QLabel("Visual: " + self.VISUAL_PRESET_LABELS.get(self.visual_preset, 'Studio Dark'))
        self.visual_status_label.setProperty("role", "statusPill")
        self.section_status_label = QLabel("Section: Off")
        self.section_status_label.setProperty("role", "statusPill")
        self.theme_status_label = QLabel("Theme: " + self.THEME_LABELS.get(self.current_theme, self.THEME_LABELS[DEFAULT_THEME_NAME]))
        self.theme_status_label.setProperty("role", "statusPill")

        self.status_bar.addPermanentWidget(self.file_status_label)
        self.status_bar.addPermanentWidget(self.mode_status_label)
        self.status_bar.addPermanentWidget(self.pick_status_label)
        self.status_bar.addPermanentWidget(self.projection_status_label)
        self.status_bar.addPermanentWidget(self.visual_status_label)
        self.status_bar.addPermanentWidget(self.section_status_label)
        self.status_bar.addPermanentWidget(self.theme_status_label)
        self.status_bar.showMessage("Ready")

    def show_status_message(self, message, timeout=3000):
        self.status_bar.showMessage(message, timeout)

    def _save_settings(self):
        self.viewer_settings.recent_files = list(self.recent_files)
        self.viewer_settings.show_axes = self.show_axes
        self.viewer_settings.show_grid = self.show_grid
        self.viewer_settings.projection_mode = self.projection_mode
        self.viewer_settings.visual_preset = self.visual_preset
        self.viewer_settings.section_plane_enabled = self.section_plane_enabled
        self.viewer_settings.section_plane_axis = self.section_plane_axis
        self.viewer_settings.section_plane_offset_ratio = self.section_plane_offset_ratio
        self.viewer_settings.section_plane_inverted = self.section_plane_inverted
        self.viewer_settings.mesh_opacity = self.mesh_opacity
        self.viewer_settings.point_opacity = self.point_opacity
        self.viewer_settings.backface_culling = self.backface_culling
        self.viewer_settings.point_size = self.point_size
        self.viewer_settings.line_width = self.line_width
        self.viewer_settings.show_bounding_box = self.show_bounding_box
        self.viewer_settings.show_model_center = self.show_model_center
        self.viewer_settings.show_vertex_normals = self.show_vertex_normals
        self.viewer_settings.show_face_normals = self.show_face_normals
        self.viewer_settings.pick_preference = self.pick_preference
        self.viewer_settings.theme_name = self.current_theme
        self.viewer_settings.save(self.settings)

    def _update_recent_files_menu(self):
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
        self.viewer_settings.recent_files = list(self.recent_files)
        self.viewer_settings.add_recent_file(file_path)
        self.recent_files = list(self.viewer_settings.recent_files[:MAX_RECENT_FILES])
        self._save_settings()
        self._update_recent_files_menu()

    def _remove_recent_file(self, file_path):
        original_length = len(self.recent_files)
        self.viewer_settings.recent_files = list(self.recent_files)
        self.viewer_settings.remove_recent_file(file_path)
        self.recent_files = list(self.viewer_settings.recent_files)
        if len(self.recent_files) != original_length:
            self._save_settings()
            self._update_recent_files_menu()

    def closeEvent(self, event):
        self._save_settings()
        super().closeEvent(event)

    def _on_open_file(self):
        self.control_panel._on_load_file()

    def open_model_file(self, file_path, from_recent=False):
        if not file_path:
            return False

        if not os.path.exists(file_path):
            QMessageBox.warning(self, "File Not Found", "The file does not exist:\n" + file_path)
            if from_recent:
                self._remove_recent_file(file_path)
            return False

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            QMessageBox.warning(self, "Unsupported File", "Unsupported file format: " + ext)
            return False

        success = self.control_panel.load_file(file_path)
        if success:
            self.current_file_path = file_path
            self._add_recent_file(file_path)
            self.file_status_label.setText(os.path.basename(file_path))
            self.setWindowTitle("PyQtGLMeshViewer - " + os.path.basename(file_path))
            self.show_status_message("Loaded: " + file_path, 4000)
        elif from_recent:
            self._remove_recent_file(file_path)
        return success

    def fit_view(self):
        self.gl_widget.fit_view()
        self.show_status_message("Fit view", 2000)

    def set_standard_view(self, view_name):
        if view_name not in self.STANDARD_VIEW_LABELS:
            return
        self.current_standard_view = view_name
        self.gl_widget.set_standard_view(view_name)
        self.control_panel.set_standard_view(view_name)
        self.show_status_message("View: " + self.STANDARD_VIEW_LABELS[view_name], 2000)

    def _sync_checkable_action(self, action, value):
        action.blockSignals(True)
        action.setChecked(bool(value))
        action.blockSignals(False)

    def set_show_axes(self, show):
        self.show_axes = bool(show)
        self.gl_widget.set_show_axes(self.show_axes)
        self._sync_checkable_action(self.show_axes_action, self.show_axes)
        self.control_panel.set_scene_state(self.show_axes, self.show_grid, self.current_standard_view)
        self._save_settings()

    def set_show_grid(self, show):
        self.show_grid = bool(show)
        self.gl_widget.set_show_grid(self.show_grid)
        self._sync_checkable_action(self.show_grid_action, self.show_grid)
        self.control_panel.set_scene_state(self.show_axes, self.show_grid, self.current_standard_view)
        self._save_settings()

    def set_projection_mode(self, mode):
        if mode not in self.PROJECTION_LABELS:
            return
        self.projection_mode = mode
        self.gl_widget.set_projection_mode(mode)
        projection_action = self.projection_actions.get(mode)
        if projection_action is not None:
            projection_action.blockSignals(True)
            projection_action.setChecked(True)
            projection_action.blockSignals(False)
        self.toolbar_projection_action.blockSignals(True)
        self.toolbar_projection_action.setChecked(mode == 'orthographic')
        self.toolbar_projection_action.blockSignals(False)
        self.projection_status_label.setText("Projection: " + self.PROJECTION_LABELS[mode])
        self._save_settings()
        self.show_status_message("Projection: " + self.PROJECTION_LABELS[mode], 2000)

    def set_visual_preset(self, preset_name):
        if preset_name not in self.VISUAL_PRESET_LABELS:
            return
        self.visual_preset = preset_name
        self.gl_widget.set_visual_preset(preset_name)
        preset_action = self.visual_preset_actions.get(preset_name)
        if preset_action is not None:
            preset_action.blockSignals(True)
            preset_action.setChecked(True)
            preset_action.blockSignals(False)
        self.visual_status_label.setText("Visual: " + self.VISUAL_PRESET_LABELS[preset_name])
        self._save_settings()
        self.show_status_message("Visual preset: " + self.VISUAL_PRESET_LABELS[preset_name], 2000)

    def _update_section_plane_status(self):
        if not self.section_plane_enabled:
            self.section_status_label.setText("Section: Off")
            return
        axis_label = self.SECTION_AXIS_LABELS.get(self.section_plane_axis, self.section_plane_axis.upper())
        direction = "Inv" if self.section_plane_inverted else "Std"
        self.section_status_label.setText(f"Section: {axis_label} {self.section_plane_offset_ratio:+.2f} {direction}")

    def set_section_plane_enabled(self, enabled):
        self.section_plane_enabled = bool(enabled)
        self.gl_widget.set_section_plane_enabled(self.section_plane_enabled)
        self._sync_checkable_action(self.section_plane_action, self.section_plane_enabled)
        self._update_section_plane_status()
        self._save_settings()

    def set_section_plane_axis(self, axis, save=True):
        if axis not in self.SECTION_AXIS_LABELS:
            return
        self.section_plane_axis = axis
        self.gl_widget.set_section_plane_axis(axis)
        self._update_section_plane_status()
        if save:
            self._save_settings()

    def set_section_plane_offset_ratio(self, offset_ratio, save=True):
        self.section_plane_offset_ratio = max(-1.0, min(1.0, float(offset_ratio)))
        self.gl_widget.set_section_plane_offset_ratio(self.section_plane_offset_ratio)
        self._update_section_plane_status()
        if save:
            self._save_settings()

    def set_section_plane_inverted(self, inverted, save=True):
        self.section_plane_inverted = bool(inverted)
        self.gl_widget.set_section_plane_inverted(self.section_plane_inverted)
        self._update_section_plane_status()
        if save:
            self._save_settings()

    def reset_section_plane(self):
        self.section_plane_enabled = False
        self.section_plane_axis = 'z'
        self.section_plane_offset_ratio = 0.0
        self.section_plane_inverted = False
        self.gl_widget.reset_section_plane()
        self._sync_checkable_action(self.section_plane_action, False)
        self._update_section_plane_status()
        self._save_settings()
        self.show_status_message("Section plane reset", 2000)

    def set_show_bounding_box(self, show):
        self.show_bounding_box = bool(show)
        self.gl_widget.set_show_bounding_box(show)
        self._sync_checkable_action(self.show_bounding_box_action, self.show_bounding_box)
        self._save_settings()

    def set_show_model_center(self, show):
        self.show_model_center = bool(show)
        self.gl_widget.set_show_model_center(show)
        self._sync_checkable_action(self.show_model_center_action, self.show_model_center)
        self._save_settings()

    def set_show_vertex_normals(self, show):
        self.show_vertex_normals = bool(show)
        self.gl_widget.set_show_vertex_normals(show)
        self._sync_checkable_action(self.show_vertex_normals_action, self.show_vertex_normals)
        self._save_settings()

    def set_show_face_normals(self, show):
        self.show_face_normals = bool(show)
        self.gl_widget.set_show_face_normals(show)
        self._sync_checkable_action(self.show_face_normals_action, self.show_face_normals)
        self._save_settings()

    def set_mesh_opacity(self, opacity):
        self.mesh_opacity = float(opacity)
        self.gl_widget.set_mesh_opacity(self.mesh_opacity)
        self._save_settings()

    def set_point_opacity(self, opacity):
        self.point_opacity = float(opacity)
        self.gl_widget.set_point_opacity(self.point_opacity)
        self._save_settings()

    def set_backface_culling(self, enabled):
        self.backface_culling = bool(enabled)
        self.gl_widget.set_backface_culling(self.backface_culling)
        self._save_settings()

    def set_point_size(self, size):
        self.point_size = float(size)
        self.gl_widget.set_point_size(self.point_size)
        self._save_settings()

    def set_line_width(self, width):
        self.line_width = float(width)
        self.gl_widget.set_line_width(self.line_width)
        self._save_settings()

    def set_theme(self, theme_name):
        if theme_name not in self.THEME_LABELS:
            return
        self.current_theme = apply_theme(QApplication.instance(), theme_name)
        self.theme_status_label.setText("Theme: " + self.THEME_LABELS[self.current_theme])
        theme_action = self.theme_actions.get(self.current_theme)
        if theme_action is not None:
            theme_action.blockSignals(True)
            theme_action.setChecked(True)
            theme_action.blockSignals(False)
        self._save_settings()
        self.show_status_message("Theme: " + self.THEME_LABELS[self.current_theme], 2000)

    def cycle_theme(self):
        theme_names = list(self.THEME_LABELS.keys())
        if not theme_names:
            return
        current_index = theme_names.index(self.current_theme) if self.current_theme in theme_names else -1
        next_theme = theme_names[(current_index + 1) % len(theme_names)]
        self.set_theme(next_theme)

    def set_pick_preference(self, preference):
        if preference not in self.PICK_PREFERENCES:
            return
        self.pick_preference = preference
        self.gl_widget.set_inspection_pick_preference(preference)
        self.pick_status_label.setText("Pick: " + self.PICK_PREFERENCES[preference])
        action = self.pick_preference_actions.get(preference)
        if action is not None:
            action.blockSignals(True)
            action.setChecked(True)
            action.blockSignals(False)
        self._save_settings()

    def export_screenshot(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Screenshot",
            "viewer_screenshot_" + timestamp + ".png",
            "PNG Image (*.png)",
        )
        if not file_path:
            return False

        if not file_path.lower().endswith('.png'):
            file_path += '.png'

        if self.gl_widget.capture_viewport(file_path):
            self.show_status_message("Screenshot saved: " + file_path, 4000)
            return True

        QMessageBox.critical(self, "Export Failed", "Could not save the screenshot.")
        return False

    def export_inspection_report(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Inspection Report",
            "inspection_report_" + timestamp,
            "Inspection Report (*.json *.png);;All Files (*)",
        )
        if not base_path:
            return False

        root, _ = os.path.splitext(base_path)
        result = self.gl_widget.export_inspection_report(root or base_path)
        if result:
            self.show_status_message("Inspection report saved: " + result['json_path'], 5000)
            return True

        QMessageBox.critical(self, "Export Failed", "Could not export inspection PNG + JSON.")
        return False

    def _sync_inspect_actions(self, snapshot):
        if not snapshot:
            return

        self._sync_checkable_action(self.inspect_mode_action, snapshot.get('inspection_mode', False))
        self._sync_checkable_action(self.toolbar_inspect_action, snapshot.get('inspection_mode', False))
        self._sync_checkable_action(self.show_bounding_box_action, snapshot.get('show_bounding_box', False))
        self._sync_checkable_action(self.show_model_center_action, snapshot.get('show_model_center', False))
        self._sync_checkable_action(self.show_vertex_normals_action, snapshot.get('show_vertex_normals', False))
        self._sync_checkable_action(self.show_face_normals_action, snapshot.get('show_face_normals', False))
        self._sync_checkable_action(self.section_plane_action, snapshot.get('section_plane_enabled', False))

        self.mode_status_label.setText("Inspect" if snapshot.get('inspection_mode', False) else "Browse")

        pick_preference = snapshot.get('pick_preference', self.pick_preference)
        if pick_preference in self.pick_preference_actions:
            self.pick_preference_actions[pick_preference].blockSignals(True)
            self.pick_preference_actions[pick_preference].setChecked(True)
            self.pick_preference_actions[pick_preference].blockSignals(False)
            self.pick_status_label.setText("Pick: " + self.PICK_PREFERENCES[pick_preference])

        action_mode = snapshot.get('action_mode', 'select')
        if action_mode in self.inspect_action_actions:
            self.inspect_action_actions[action_mode].blockSignals(True)
            self.inspect_action_actions[action_mode].setChecked(True)
            self.inspect_action_actions[action_mode].blockSignals(False)

        projection_mode = snapshot.get('projection_mode', self.projection_mode)
        if projection_mode in self.projection_actions:
            self.projection_actions[projection_mode].blockSignals(True)
            self.projection_actions[projection_mode].setChecked(True)
            self.projection_actions[projection_mode].blockSignals(False)
            self.toolbar_projection_action.blockSignals(True)
            self.toolbar_projection_action.setChecked(projection_mode == 'orthographic')
            self.toolbar_projection_action.blockSignals(False)
            self.projection_status_label.setText("Projection: " + self.PROJECTION_LABELS[projection_mode])

        visual_preset = snapshot.get('visual_preset', self.visual_preset)
        if visual_preset in self.visual_preset_actions:
            self.visual_preset_actions[visual_preset].blockSignals(True)
            self.visual_preset_actions[visual_preset].setChecked(True)
            self.visual_preset_actions[visual_preset].blockSignals(False)
            self.visual_status_label.setText("Visual: " + self.VISUAL_PRESET_LABELS[visual_preset])

        self.section_plane_enabled = bool(snapshot.get('section_plane_enabled', self.section_plane_enabled))
        self.section_plane_axis = snapshot.get('section_plane_axis', self.section_plane_axis)
        self.section_plane_offset_ratio = float(snapshot.get('section_plane_offset_ratio', self.section_plane_offset_ratio))
        self.section_plane_inverted = bool(snapshot.get('section_plane_inverted', self.section_plane_inverted))
        self._update_section_plane_status()

        theme_action = self.theme_actions.get(self.current_theme)
        if theme_action is not None:
            theme_action.blockSignals(True)
            theme_action.setChecked(True)
            theme_action.blockSignals(False)
        self.theme_status_label.setText("Theme: " + self.THEME_LABELS.get(self.current_theme, self.THEME_LABELS[DEFAULT_THEME_NAME]))

    def _on_about(self):
        QMessageBox.about(
            self,
            "About PyQtGLMeshViewer",
            "PyQtGLMeshViewer\n\n"
            "A desktop viewer for meshes and point clouds with inspection tooling.\n\n"
            "Features:\n"
            "- Drag and drop, recent files, fit view, standard views\n"
            "- Multiple desktop themes\n"
            "- Perspective/orthographic projection switch\n"
            "- Background and lighting visual presets\n"
            "- Interactive section plane with axis, offset, and invert controls\n"
            "- Axes, grid, screenshot export\n"
            "- Mesh and point-cloud opacity controls\n"
            "- Back-face culling, point size, line width tuning\n"
            "- Inspection mode with point/face picking\n"
            "- Distance, angle, face-area measurements\n"
            "- Bounding box, center, normals, grouped report export",
        )
