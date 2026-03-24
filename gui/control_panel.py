import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSlider,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from model_io.mesh_loader import MeshLoader
from model_io.point_loader import PointCloudLoader


class ControlPanel(QWidget):
    STANDARD_VIEWS = [
        ("Isometric", "isometric"), ("Front", "front"), ("Back", "back"),
        ("Left", "left"), ("Right", "right"), ("Top", "top"), ("Bottom", "bottom"),
    ]
    PROJECTION_MODES = [("Perspective", "perspective"), ("Orthographic", "orthographic")]
    VISUAL_PRESETS = [
        ("Studio Dark", "studio_dark"),
        ("Studio Light", "studio_light"),
        ("Blueprint", "blueprint"),
        ("Inspection Lab", "inspection_lab"),
    ]
    SECTION_AXES = [("X Axis", "x"), ("Y Axis", "y"), ("Z Axis", "z")]
    PICK_MODES = [("Auto", "auto"), ("Point", "point"), ("Face", "face")]
    PICK_PREFERENCES = [("Balanced", "balanced"), ("Prefer Point", "prefer_point"), ("Prefer Face", "prefer_face")]
    ACTION_MODES = [("Select", "select"), ("Distance", "distance"), ("Angle", "angle"), ("Face Area", "face_area")]

    def __init__(self, gl_widget, parent=None):
        super().__init__(parent)
        self.gl_widget = gl_widget
        self.current_file_path = None
        self.data_type = None
        self._group_ids = []
        self._measurement_ids = []
        self._create_ui()
        self.gl_widget.inspection_state_changed.connect(self.update_inspection_state)
        self.gl_widget.status_message.connect(self._on_status_message)

    def _create_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.summary_card = QWidget()
        self.summary_card.setObjectName("summaryCard")
        summary_layout = QVBoxLayout(self.summary_card)
        summary_layout.setContentsMargins(14, 14, 14, 14)
        summary_layout.setSpacing(4)
        self.summary_title = QLabel("Inspection Workspace")
        self.summary_title.setProperty("role", "summaryTitle")
        self.summary_file_label = QLabel("No model loaded")
        self.summary_file_label.setProperty("role", "summaryMeta")
        self.summary_mode_label = QLabel("Browse mode")
        self.summary_mode_label.setProperty("role", "statusPill")
        summary_layout.addWidget(self.summary_title)
        summary_layout.addWidget(self.summary_file_label)
        summary_layout.addWidget(self.summary_mode_label)
        layout.addWidget(self.summary_card)

        file_group = QGroupBox("File")
        file_layout = QVBoxLayout()
        self.load_button = QPushButton("Open File...")
        self.load_button.setProperty("role", "primary")
        self.load_button.clicked.connect(self._on_load_file)
        file_layout.addWidget(self.load_button)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        scene_group = QGroupBox("Scene")
        scene_layout = QVBoxLayout()
        self.fit_view_button = QPushButton("Fit View")
        self.fit_view_button.clicked.connect(self._on_fit_view)
        scene_layout.addWidget(self.fit_view_button)
        scene_layout.addWidget(QLabel("Standard View:"))
        self.standard_view_combo = QComboBox()
        for label, view_name in self.STANDARD_VIEWS:
            self.standard_view_combo.addItem(label, view_name)
        scene_layout.addWidget(self.standard_view_combo)
        scene_layout.addWidget(QLabel("Projection:"))
        self.projection_combo = QComboBox()
        for label, mode in self.PROJECTION_MODES:
            self.projection_combo.addItem(label, mode)
        self.projection_combo.currentIndexChanged.connect(self._on_projection_changed)
        scene_layout.addWidget(self.projection_combo)
        scene_layout.addWidget(QLabel("Visual Preset:"))
        self.visual_preset_combo = QComboBox()
        for label, preset in self.VISUAL_PRESETS:
            self.visual_preset_combo.addItem(label, preset)
        self.visual_preset_combo.currentIndexChanged.connect(self._on_visual_preset_changed)
        scene_layout.addWidget(self.visual_preset_combo)
        self.apply_standard_view_button = QPushButton("Apply View")
        self.apply_standard_view_button.clicked.connect(self._on_standard_view_apply)
        scene_layout.addWidget(self.apply_standard_view_button)
        self.axes_checkbox = QCheckBox("Show Axes")
        self.axes_checkbox.setChecked(True)
        self.axes_checkbox.toggled.connect(self._on_axes_toggled)
        scene_layout.addWidget(self.axes_checkbox)
        self.grid_checkbox = QCheckBox("Show Grid")
        self.grid_checkbox.toggled.connect(self._on_grid_toggled)
        scene_layout.addWidget(self.grid_checkbox)
        self.screenshot_button = QPushButton("Export Screenshot...")
        self.screenshot_button.clicked.connect(self._on_save_screenshot)
        scene_layout.addWidget(self.screenshot_button)
        scene_group.setLayout(scene_layout)
        layout.addWidget(scene_group)

        section_group = QGroupBox("Section Plane")
        section_layout = QVBoxLayout()
        self.section_plane_checkbox = QCheckBox("Enable Section Plane")
        self.section_plane_checkbox.toggled.connect(self._on_section_plane_enabled_toggled)
        section_layout.addWidget(self.section_plane_checkbox)
        section_layout.addWidget(QLabel("Section Axis:"))
        self.section_plane_axis_combo = QComboBox()
        for label, axis in self.SECTION_AXES:
            self.section_plane_axis_combo.addItem(label, axis)
        self.section_plane_axis_combo.currentIndexChanged.connect(self._on_section_plane_axis_changed)
        section_layout.addWidget(self.section_plane_axis_combo)
        self.section_plane_offset_label = QLabel("Offset: 0.00")
        self.section_plane_offset_slider = QSlider(Qt.Horizontal)
        self.section_plane_offset_slider.setMinimum(-100)
        self.section_plane_offset_slider.setMaximum(100)
        self.section_plane_offset_slider.setValue(0)
        self.section_plane_offset_slider.valueChanged.connect(self._on_section_plane_offset_changed)
        section_layout.addWidget(self.section_plane_offset_label)
        section_layout.addWidget(self.section_plane_offset_slider)
        self.section_plane_invert_checkbox = QCheckBox("Invert Cut Direction")
        self.section_plane_invert_checkbox.toggled.connect(self._on_section_plane_inverted_toggled)
        section_layout.addWidget(self.section_plane_invert_checkbox)
        self.section_plane_reset_button = QPushButton("Reset Section Plane")
        self.section_plane_reset_button.clicked.connect(self._on_section_plane_reset)
        section_layout.addWidget(self.section_plane_reset_button)
        section_group.setLayout(section_layout)
        layout.addWidget(section_group)

        inspect_group = QGroupBox("Inspect")
        inspect_layout = QVBoxLayout()
        self.inspection_mode_checkbox = QCheckBox("Enable Inspection Mode")
        self.inspection_mode_checkbox.toggled.connect(self.gl_widget.set_inspection_mode)
        inspect_layout.addWidget(self.inspection_mode_checkbox)
        inspect_layout.addWidget(QLabel("Pick Mode:"))
        self.pick_mode_combo = QComboBox()
        for label, value in self.PICK_MODES:
            self.pick_mode_combo.addItem(label, value)
        self.pick_mode_combo.currentIndexChanged.connect(self._on_pick_mode_changed)
        inspect_layout.addWidget(self.pick_mode_combo)
        inspect_layout.addWidget(QLabel("Auto Pick Preference:"))
        self.pick_preference_combo = QComboBox()
        for label, value in self.PICK_PREFERENCES:
            self.pick_preference_combo.addItem(label, value)
        self.pick_preference_combo.currentIndexChanged.connect(self._on_pick_preference_changed)
        inspect_layout.addWidget(self.pick_preference_combo)
        inspect_layout.addWidget(QLabel("Tool:"))
        self.action_mode_combo = QComboBox()
        for label, value in self.ACTION_MODES:
            self.action_mode_combo.addItem(label, value)
        self.action_mode_combo.currentIndexChanged.connect(self._on_action_mode_changed)
        inspect_layout.addWidget(self.action_mode_combo)
        self.export_report_button = QPushButton("Export Inspection Report...")
        self.export_report_button.setProperty("role", "primary")
        self.export_report_button.clicked.connect(lambda: self._call_main_window('export_inspection_report'))
        inspect_layout.addWidget(self.export_report_button)
        inspect_group.setLayout(inspect_layout)
        layout.addWidget(inspect_group)

        geometry_group = QGroupBox("Inspection Layers")
        geometry_layout = QVBoxLayout()
        self.bounding_box_checkbox = QCheckBox("Show Bounding Box")
        self.bounding_box_checkbox.toggled.connect(self.gl_widget.set_show_bounding_box)
        geometry_layout.addWidget(self.bounding_box_checkbox)
        self.model_center_checkbox = QCheckBox("Show Model Center")
        self.model_center_checkbox.toggled.connect(self.gl_widget.set_show_model_center)
        geometry_layout.addWidget(self.model_center_checkbox)
        self.vertex_normals_checkbox = QCheckBox("Show Vertex Normals")
        self.vertex_normals_checkbox.toggled.connect(self.gl_widget.set_show_vertex_normals)
        geometry_layout.addWidget(self.vertex_normals_checkbox)
        self.face_normals_checkbox = QCheckBox("Show Face Normals")
        self.face_normals_checkbox.toggled.connect(self.gl_widget.set_show_face_normals)
        geometry_layout.addWidget(self.face_normals_checkbox)
        geometry_group.setLayout(geometry_layout)
        layout.addWidget(geometry_group)

        group_group = QGroupBox("Groups")
        group_layout = QVBoxLayout()
        self.group_list = QListWidget()
        self.group_list.currentRowChanged.connect(self._on_group_selected)
        group_layout.addWidget(self.group_list)
        add_group = QPushButton("Add Group")
        add_group.clicked.connect(self._on_add_group)
        rename_group = QPushButton("Rename Group")
        rename_group.clicked.connect(self._on_rename_group)
        delete_group = QPushButton("Delete Group")
        delete_group.clicked.connect(self._on_delete_group)
        toggle_group = QPushButton("Toggle Group Visibility")
        toggle_group.clicked.connect(self._on_toggle_group_visibility)
        group_buttons_row = QHBoxLayout()
        group_buttons_row.addWidget(add_group)
        group_buttons_row.addWidget(rename_group)
        group_layout.addLayout(group_buttons_row)
        group_layout.addWidget(delete_group)
        group_layout.addWidget(toggle_group)
        group_group.setLayout(group_layout)
        layout.addWidget(group_group)

        measurement_group = QGroupBox("Measurements")
        measurement_layout = QVBoxLayout()
        self.measurement_list = QListWidget()
        self.measurement_list.currentRowChanged.connect(self._on_measurement_selected)
        measurement_layout.addWidget(self.measurement_list)
        toggle_item = QPushButton("Toggle Item Visibility")
        toggle_item.clicked.connect(self._on_toggle_measurement_visibility)
        delete_item = QPushButton("Delete Item")
        delete_item.clicked.connect(self._on_delete_measurement)
        measurement_layout.addWidget(toggle_item)
        measurement_layout.addWidget(delete_item)
        measurement_group.setLayout(measurement_layout)
        layout.addWidget(measurement_group)

        self.mesh_group = QGroupBox("Mesh Settings")
        mesh_layout = QVBoxLayout()
        mesh_layout.addWidget(QLabel("Render Mode:"))
        self.mesh_render_combo = QComboBox()
        self.mesh_render_combo.addItems(["Surface", "Wireframe", "Surface+Wireframe"])
        self.mesh_render_combo.currentIndexChanged.connect(self._on_mesh_render_mode_changed)
        mesh_layout.addWidget(self.mesh_render_combo)
        mesh_layout.addWidget(QLabel("Color Mode:"))
        self.mesh_color_combo = QComboBox()
        self.mesh_color_combo.addItems(["Uniform", "Vertex Color"])
        self.mesh_color_combo.currentIndexChanged.connect(self._on_mesh_color_mode_changed)
        mesh_layout.addWidget(self.mesh_color_combo)
        self.mesh_opacity_label = QLabel("Opacity: 1.00")
        self.mesh_opacity_slider = QSlider(Qt.Horizontal)
        self.mesh_opacity_slider.setMinimum(5)
        self.mesh_opacity_slider.setMaximum(100)
        self.mesh_opacity_slider.setValue(100)
        self.mesh_opacity_slider.valueChanged.connect(self._on_mesh_opacity_changed)
        mesh_layout.addWidget(self.mesh_opacity_label)
        mesh_layout.addWidget(self.mesh_opacity_slider)
        self.backface_culling_checkbox = QCheckBox("Cull Back Faces")
        self.backface_culling_checkbox.toggled.connect(self._on_backface_culling_toggled)
        mesh_layout.addWidget(self.backface_culling_checkbox)
        self.line_width_label = QLabel("Line Width: 2.0")
        self.line_width_slider = QSlider(Qt.Horizontal)
        self.line_width_slider.setMinimum(10)
        self.line_width_slider.setMaximum(50)
        self.line_width_slider.setValue(20)
        self.line_width_slider.valueChanged.connect(self._on_line_width_changed)
        mesh_layout.addWidget(self.line_width_label)
        mesh_layout.addWidget(self.line_width_slider)
        self.mesh_group.setLayout(mesh_layout)
        self.mesh_group.setVisible(False)
        layout.addWidget(self.mesh_group)

        self.pc_group = QGroupBox("Point Cloud Settings")
        pc_layout = QVBoxLayout()
        pc_layout.addWidget(QLabel("Color Mode:"))
        self.pc_color_combo = QComboBox()
        self.pc_color_combo.addItems(["RGB", "Height-based"])
        self.pc_color_combo.currentIndexChanged.connect(self._on_pc_color_mode_changed)
        pc_layout.addWidget(self.pc_color_combo)
        self.point_size_label = QLabel("Point Size: 2.0")
        self.point_size_slider = QSlider(Qt.Horizontal)
        self.point_size_slider.setMinimum(5)
        self.point_size_slider.setMaximum(100)
        self.point_size_slider.setValue(20)
        self.point_size_slider.valueChanged.connect(self._on_point_size_changed)
        pc_layout.addWidget(self.point_size_label)
        pc_layout.addWidget(self.point_size_slider)
        self.point_opacity_label = QLabel("Opacity: 1.00")
        self.point_opacity_slider = QSlider(Qt.Horizontal)
        self.point_opacity_slider.setMinimum(5)
        self.point_opacity_slider.setMaximum(100)
        self.point_opacity_slider.setValue(100)
        self.point_opacity_slider.valueChanged.connect(self._on_point_opacity_changed)
        pc_layout.addWidget(self.point_opacity_label)
        pc_layout.addWidget(self.point_opacity_slider)
        self.pc_group.setLayout(pc_layout)
        self.pc_group.setVisible(False)
        layout.addWidget(self.pc_group)

        stats_group = QGroupBox("Stats")
        stats_layout = QVBoxLayout()
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setMaximumHeight(120)
        self.stats_text.setPlaceholderText("Model statistics appear here.")
        stats_layout.addWidget(self.stats_text)
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        selection_group = QGroupBox("Selection")
        selection_layout = QVBoxLayout()
        self.selection_text = QTextEdit()
        self.selection_text.setReadOnly(True)
        self.selection_text.setMaximumHeight(120)
        self.selection_text.setPlaceholderText("Selection details appear here.")
        selection_layout.addWidget(self.selection_text)
        selection_group.setLayout(selection_layout)
        layout.addWidget(selection_group)

        info_group = QGroupBox("Model Info")
        info_layout = QVBoxLayout()
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(150)
        self.info_text.setText("No model loaded.")
        info_layout.addWidget(self.info_text)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        help_group = QGroupBox("Shortcuts")
        help_layout = QVBoxLayout()
        help_layout.addWidget(QLabel(
            "F / R: Fit View\nW: Toggle Wireframe\n1 / 3 / 7: Front / Right / Top\n"
            "Inspection Mode: Left Click Pick\nRight Drag: Pan\nWheel: Zoom"
        ))
        help_group.setLayout(help_layout)
        layout.addWidget(help_group)
        layout.addStretch()

    def _call_main_window(self, method_name, *args):
        window = self.window()
        if hasattr(window, method_name):
            return getattr(window, method_name)(*args)
        return None

    def _on_status_message(self, message):
        self._call_main_window('show_status_message', message, 3000)

    def set_scene_state(self, show_axes, show_grid, view_name=None):
        for widget, value in ((self.axes_checkbox, show_axes), (self.grid_checkbox, show_grid)):
            widget.blockSignals(True)
            widget.setChecked(bool(value))
            widget.blockSignals(False)
        if view_name:
            self.set_standard_view(view_name)

    def set_standard_view(self, view_name):
        index = self.standard_view_combo.findData(view_name)
        if index >= 0:
            self.standard_view_combo.blockSignals(True)
            self.standard_view_combo.setCurrentIndex(index)
            self.standard_view_combo.blockSignals(False)

    def update_inspection_state(self, snapshot):
        if not snapshot:
            return
        self.summary_mode_label.setText("Inspect mode" if snapshot.get('inspection_mode') else "Browse mode")
        for widget, key in (
            (self.inspection_mode_checkbox, 'inspection_mode'),
            (self.bounding_box_checkbox, 'show_bounding_box'),
            (self.model_center_checkbox, 'show_model_center'),
            (self.vertex_normals_checkbox, 'show_vertex_normals'),
            (self.face_normals_checkbox, 'show_face_normals'),
        ):
            widget.blockSignals(True)
            widget.setChecked(bool(snapshot.get(key)))
            widget.blockSignals(False)
        self._set_combo_data(self.pick_mode_combo, snapshot.get('pick_mode'))
        self._set_combo_data(self.pick_preference_combo, snapshot.get('pick_preference'))
        self._set_combo_data(self.action_mode_combo, snapshot.get('action_mode'))
        self._set_combo_data(self.projection_combo, snapshot.get('projection_mode'))
        self._set_combo_data(self.visual_preset_combo, snapshot.get('visual_preset'))
        self._set_combo_data(self.section_plane_axis_combo, snapshot.get('section_plane_axis'))
        self._set_combo_text(self.mesh_render_combo, {
            'surface': "Surface",
            'wireframe': "Wireframe",
            'surface+wireframe': "Surface+Wireframe",
        }.get(snapshot.get('render_mode')))
        self._set_combo_text(self.mesh_color_combo, {
            'uniform': "Uniform",
            'vertex': "Vertex Color",
        }.get(snapshot.get('color_mode')))
        mesh_opacity = float(snapshot.get('mesh_opacity', 1.0))
        self.mesh_opacity_slider.blockSignals(True)
        self.mesh_opacity_slider.setValue(int(round(mesh_opacity * 100.0)))
        self.mesh_opacity_slider.blockSignals(False)
        self.mesh_opacity_label.setText(f"Opacity: {mesh_opacity:.2f}")
        point_opacity = float(snapshot.get('point_opacity', 1.0))
        self.point_opacity_slider.blockSignals(True)
        self.point_opacity_slider.setValue(int(round(point_opacity * 100.0)))
        self.point_opacity_slider.blockSignals(False)
        self.point_opacity_label.setText(f"Opacity: {point_opacity:.2f}")
        point_size = float(snapshot.get('point_size', 2.0))
        self.point_size_slider.blockSignals(True)
        self.point_size_slider.setValue(int(round(point_size * 10.0)))
        self.point_size_slider.blockSignals(False)
        self.point_size_label.setText(f"Point Size: {point_size:.1f}")
        line_width = float(snapshot.get('line_width', 2.0))
        self.line_width_slider.blockSignals(True)
        self.line_width_slider.setValue(int(round(line_width * 10.0)))
        self.line_width_slider.blockSignals(False)
        self.line_width_label.setText(f"Line Width: {line_width:.1f}")
        self.backface_culling_checkbox.blockSignals(True)
        self.backface_culling_checkbox.setChecked(bool(snapshot.get('backface_culling', False)))
        self.backface_culling_checkbox.blockSignals(False)
        section_plane_enabled = bool(snapshot.get('section_plane_enabled', False))
        section_plane_offset = float(snapshot.get('section_plane_offset_ratio', 0.0))
        self.section_plane_checkbox.blockSignals(True)
        self.section_plane_checkbox.setChecked(section_plane_enabled)
        self.section_plane_checkbox.blockSignals(False)
        self.section_plane_offset_slider.blockSignals(True)
        self.section_plane_offset_slider.setValue(int(round(section_plane_offset * 100.0)))
        self.section_plane_offset_slider.blockSignals(False)
        self.section_plane_offset_label.setText(f"Offset: {section_plane_offset:+.2f}")
        self.section_plane_invert_checkbox.blockSignals(True)
        self.section_plane_invert_checkbox.setChecked(bool(snapshot.get('section_plane_inverted', False)))
        self.section_plane_invert_checkbox.blockSignals(False)
        self.section_plane_axis_combo.setEnabled(section_plane_enabled)
        self.section_plane_offset_slider.setEnabled(section_plane_enabled)
        self.section_plane_invert_checkbox.setEnabled(section_plane_enabled)
        self._refresh_group_list(snapshot)
        self._refresh_measurement_list(snapshot)
        self._refresh_stats(snapshot.get('stats', {}))
        self._refresh_selection(snapshot.get('selection', {}), snapshot.get('pending_pick_count', 0))

    def _set_combo_data(self, combo, value):
        index = combo.findData(value)
        if index >= 0:
            combo.blockSignals(True)
            combo.setCurrentIndex(index)
            combo.blockSignals(False)

    def _set_combo_text(self, combo, value):
        if not value:
            return
        index = combo.findText(value)
        if index >= 0:
            combo.blockSignals(True)
            combo.setCurrentIndex(index)
            combo.blockSignals(False)

    def _refresh_group_list(self, snapshot):
        self.group_list.blockSignals(True)
        self.group_list.clear()
        self._group_ids = []
        current_group_id = snapshot.get('current_group_id')
        for group in snapshot.get('groups', []):
            text = f"{group['name']} ({group['item_count']})"
            if not group.get('visible', True):
                text += " [Hidden]"
            if group['group_id'] == current_group_id:
                text = f"* {text}"
            item = QListWidgetItem(text)
            self.group_list.addItem(item)
            self._group_ids.append(group['group_id'])
        if current_group_id in self._group_ids:
            self.group_list.setCurrentRow(self._group_ids.index(current_group_id))
        self.group_list.blockSignals(False)

    def _refresh_measurement_list(self, snapshot):
        self.measurement_list.blockSignals(True)
        self.measurement_list.clear()
        self._measurement_ids = []
        current_group_id = snapshot.get('current_group_id')
        selection = snapshot.get('selection', {})
        selected_measurement_id = selection.get('object_id') if selection.get('selection_type') == 'measurement' else None
        for measurement in snapshot.get('measurements', []):
            if measurement['group_id'] != current_group_id:
                continue
            text = f"{measurement['name']} | {measurement['measurement_type']} = {measurement['value']:.4f}"
            if not measurement.get('visible', True):
                text += " [Hidden]"
            item = QListWidgetItem(text)
            self.measurement_list.addItem(item)
            self._measurement_ids.append(measurement['item_id'])
        if selected_measurement_id in self._measurement_ids:
            self.measurement_list.setCurrentRow(self._measurement_ids.index(selected_measurement_id))
        self.measurement_list.blockSignals(False)

    def _refresh_stats(self, stats):
        if not stats:
            self.stats_text.setText("No model loaded.")
            return
        bbox = stats.get('bbox_size', [0, 0, 0])
        lines = [
            f"Type: {stats.get('data_type') or 'N/A'}",
            f"Vertices/Points: {stats.get('vertex_count', 0):,}",
            f"Faces: {stats.get('face_count', 0):,}",
            f"BBox: {bbox[0]:.4f}, {bbox[1]:.4f}, {bbox[2]:.4f}",
            f"Scene Radius: {stats.get('scene_radius', 0.0):.4f}",
        ]
        self.stats_text.setText("\n".join(lines))

    def _refresh_selection(self, selection, pending_pick_count):
        if not selection or not selection.get('selection_type'):
            text = "Nothing selected."
        else:
            text = f"Type: {selection.get('selection_type')}\nLabel: {selection.get('label')}\nData: {selection.get('data')}"
        if pending_pick_count:
            text += f"\nPending Picks: {pending_pick_count}"
        self.selection_text.setText(text)

    def _on_load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open 3D Model", "", "3D Models (*.obj *.stl *.ply *.xyz);;All Files (*)")
        if file_path:
            if self._call_main_window('open_model_file', file_path) is None:
                self.load_file(file_path)

    def load_file(self, file_path):
        try:
            ext = os.path.splitext(file_path)[1].lower()
            if ext in {'.obj', '.stl', '.ply'}:
                try:
                    data = MeshLoader.load(file_path)
                    if ext == '.ply' and (data['indices'] is None or len(data['indices']) == 0):
                        return self._load_point_cloud_data(PointCloudLoader.load(file_path), file_path)
                    return self._load_mesh_data(data, file_path)
                except Exception:
                    if ext == '.ply':
                        return self._load_point_cloud_data(PointCloudLoader.load(file_path), file_path)
                    raise
            if ext == '.xyz':
                return self._load_point_cloud_data(PointCloudLoader.load(file_path), file_path)
            raise ValueError(f"Unsupported file format: {ext}")
        except Exception as error:
            QMessageBox.critical(self, "Load Failed", f"Could not load file:\n{error}")
            return False

    def _load_mesh_data(self, data, file_path):
        if not self.gl_widget.load_mesh_data(data['vertices'], data['indices'], data['normals'], data['colors']):
            return False
        self.gl_widget.set_model_path(file_path)
        self.gl_widget.fit_view()
        self.current_file_path = file_path
        self.data_type = 'mesh'
        self.mesh_group.setVisible(True)
        self.pc_group.setVisible(False)
        self._update_info_text(data, 'mesh')
        self.summary_file_label.setText(os.path.basename(file_path))
        return True

    def _load_point_cloud_data(self, data, file_path):
        if not self.gl_widget.load_point_cloud_data(data['points'], data['colors']):
            return False
        self.gl_widget.set_model_path(file_path)
        self.gl_widget.fit_view()
        self.current_file_path = file_path
        self.data_type = 'point_cloud'
        self.mesh_group.setVisible(False)
        self.pc_group.setVisible(True)
        self._update_info_text(data, 'point_cloud')
        self.summary_file_label.setText(os.path.basename(file_path))
        return True

    def _update_info_text(self, data, data_type):
        lines = []
        if self.current_file_path:
            lines.extend([f"File: {os.path.basename(self.current_file_path)}", f"Path: {self.current_file_path}"])
        if data_type == 'mesh':
            lines.extend([f"Type: Mesh", f"Vertices: {len(data['vertices']):,}", f"Faces: {len(data['indices']):,}", "Colors: Vertex Color" if data['colors'] is not None else "Colors: Uniform"])
        else:
            lines.extend([f"Type: Point Cloud", f"Points: {len(data['points']):,}", "Colors: RGB/Height-based" if data['colors'] is not None else "Colors: Uniform"])
        self.info_text.setText("\n".join(lines))

    def _on_fit_view(self):
        if self._call_main_window('fit_view') is None:
            self.gl_widget.fit_view()

    def _on_standard_view_apply(self):
        view_name = self.standard_view_combo.currentData()
        if self._call_main_window('set_standard_view', view_name) is None:
            self.gl_widget.set_standard_view(view_name)

    def _on_axes_toggled(self, checked):
        if self._call_main_window('set_show_axes', checked) is None:
            self.gl_widget.set_show_axes(checked)

    def _on_grid_toggled(self, checked):
        if self._call_main_window('set_show_grid', checked) is None:
            self.gl_widget.set_show_grid(checked)

    def _on_projection_changed(self, index):
        projection_mode = self.projection_combo.itemData(index)
        if self._call_main_window('set_projection_mode', projection_mode) is None:
            self.gl_widget.set_projection_mode(projection_mode)

    def _on_visual_preset_changed(self, index):
        preset_name = self.visual_preset_combo.itemData(index)
        if self._call_main_window('set_visual_preset', preset_name) is None:
            self.gl_widget.set_visual_preset(preset_name)

    def _on_section_plane_enabled_toggled(self, checked):
        self.section_plane_axis_combo.setEnabled(bool(checked))
        self.section_plane_offset_slider.setEnabled(bool(checked))
        self.section_plane_invert_checkbox.setEnabled(bool(checked))
        if self._call_main_window('set_section_plane_enabled', checked) is None:
            self.gl_widget.set_section_plane_enabled(checked)

    def _on_section_plane_axis_changed(self, index):
        axis = self.section_plane_axis_combo.itemData(index)
        if self._call_main_window('set_section_plane_axis', axis) is None:
            self.gl_widget.set_section_plane_axis(axis)

    def _on_section_plane_offset_changed(self, value):
        offset_ratio = value / 100.0
        self.section_plane_offset_label.setText(f"Offset: {offset_ratio:+.2f}")
        if self._call_main_window('set_section_plane_offset_ratio', offset_ratio) is None:
            self.gl_widget.set_section_plane_offset_ratio(offset_ratio)

    def _on_section_plane_inverted_toggled(self, checked):
        if self._call_main_window('set_section_plane_inverted', checked) is None:
            self.gl_widget.set_section_plane_inverted(checked)

    def _on_section_plane_reset(self):
        if self._call_main_window('reset_section_plane') is None:
            self.gl_widget.reset_section_plane()

    def _on_pick_mode_changed(self, index):
        self.gl_widget.set_inspection_pick_mode(self.pick_mode_combo.itemData(index))

    def _on_pick_preference_changed(self, index):
        self.gl_widget.set_inspection_pick_preference(self.pick_preference_combo.itemData(index))

    def _on_action_mode_changed(self, index):
        self.gl_widget.set_inspection_action_mode(self.action_mode_combo.itemData(index))

    def _on_save_screenshot(self):
        if self._call_main_window('export_screenshot') is None:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save Screenshot", "viewer_screenshot.png", "PNG Image (*.png)")
            if file_path and not self.gl_widget.capture_viewport(file_path if file_path.lower().endswith('.png') else f"{file_path}.png"):
                QMessageBox.critical(self, "Save Failed", "Could not save the screenshot.")

    def _current_group_id(self):
        row = self.group_list.currentRow()
        return self._group_ids[row] if 0 <= row < len(self._group_ids) else None

    def _current_measurement_id(self):
        row = self.measurement_list.currentRow()
        return self._measurement_ids[row] if 0 <= row < len(self._measurement_ids) else None

    def _on_add_group(self):
        name, ok = QInputDialog.getText(self, "New Group", "Group name:")
        if ok:
            self.gl_widget.create_group(name or "New Group")

    def _on_rename_group(self):
        group_id = self._current_group_id()
        if not group_id:
            return
        name, ok = QInputDialog.getText(self, "Rename Group", "New name:")
        if ok and not self.gl_widget.rename_group(group_id, name):
            QMessageBox.warning(self, "Rename Failed", "Could not rename the selected group.")

    def _on_delete_group(self):
        group_id = self._current_group_id()
        if group_id:
            self.gl_widget.delete_group(group_id)

    def _on_toggle_group_visibility(self):
        group_id = self._current_group_id()
        if not group_id:
            return
        snapshot = self.gl_widget.get_inspection_state_snapshot()
        group = next((item for item in snapshot.get('groups', []) if item['group_id'] == group_id), None)
        if group:
            self.gl_widget.set_group_visible(group_id, not group.get('visible', True))

    def _on_group_selected(self, row):
        if 0 <= row < len(self._group_ids):
            self.gl_widget.set_current_group(self._group_ids[row])

    def _on_measurement_selected(self, row):
        if 0 <= row < len(self._measurement_ids):
            self.gl_widget.select_measurement_item(self._measurement_ids[row])

    def _on_toggle_measurement_visibility(self):
        item_id = self._current_measurement_id()
        if not item_id:
            return
        snapshot = self.gl_widget.get_inspection_state_snapshot()
        measurement = next((item for item in snapshot.get('measurements', []) if item['item_id'] == item_id), None)
        if measurement:
            self.gl_widget.set_measurement_visible(item_id, not measurement.get('visible', True))

    def _on_delete_measurement(self):
        item_id = self._current_measurement_id()
        if item_id:
            self.gl_widget.delete_measurement(item_id)

    def _on_mesh_render_mode_changed(self, index):
        modes = ['surface', 'wireframe', 'surface+wireframe']
        if index < len(modes):
            self.gl_widget.set_render_mode(modes[index])

    def _on_mesh_color_mode_changed(self, index):
        modes = ['uniform', 'vertex']
        if index < len(modes):
            self.gl_widget.set_color_mode(modes[index])

    def _on_pc_color_mode_changed(self, index):
        if not self.current_file_path or self.data_type != 'point_cloud':
            return
        try:
            data = PointCloudLoader.load(self.current_file_path)
            if index == 1:
                data['colors'] = PointCloudLoader._height_based_colors(data['points'])
            self.gl_widget.load_point_cloud_data(data['points'], data['colors'])
            self.gl_widget.set_model_path(self.current_file_path)
            self.gl_widget.fit_view()
        except Exception as error:
            QMessageBox.warning(self, "Warning", f"Could not update point cloud colors:\n{error}")

    def _on_point_size_changed(self, value):
        size = value / 10.0
        self.point_size_label.setText(f"Point Size: {size:.1f}")
        if self._call_main_window('set_point_size', size) is None:
            self.gl_widget.set_point_size(size)

    def _on_line_width_changed(self, value):
        width = value / 10.0
        self.line_width_label.setText(f"Line Width: {width:.1f}")
        if self._call_main_window('set_line_width', width) is None:
            self.gl_widget.set_line_width(width)

    def _on_mesh_opacity_changed(self, value):
        opacity = value / 100.0
        self.mesh_opacity_label.setText(f"Opacity: {opacity:.2f}")
        if self._call_main_window('set_mesh_opacity', opacity) is None:
            self.gl_widget.set_mesh_opacity(opacity)

    def _on_point_opacity_changed(self, value):
        opacity = value / 100.0
        self.point_opacity_label.setText(f"Opacity: {opacity:.2f}")
        if self._call_main_window('set_point_opacity', opacity) is None:
            self.gl_widget.set_point_opacity(opacity)

    def _on_backface_culling_toggled(self, checked):
        if self._call_main_window('set_backface_culling', checked) is None:
            self.gl_widget.set_backface_culling(checked)
