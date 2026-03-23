"""
Control panel for file operations and rendering options.
"""
import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QLabel,
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
    """Sidebar with model and scene controls."""

    STANDARD_VIEWS = [
        ("Isometric", "isometric"),
        ("Front", "front"),
        ("Back", "back"),
        ("Left", "left"),
        ("Right", "right"),
        ("Top", "top"),
        ("Bottom", "bottom"),
    ]

    def __init__(self, gl_widget, parent=None):
        super().__init__(parent)
        self.gl_widget = gl_widget
        self.current_file_path = None
        self.data_type = None
        self._create_ui()

    def _create_ui(self):
        """Create the sidebar layout."""
        layout = QVBoxLayout()
        self.setLayout(layout)

        file_group = QGroupBox("File")
        file_layout = QVBoxLayout()
        self.load_button = QPushButton("Open File...")
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

        self.apply_standard_view_button = QPushButton("Apply View")
        self.apply_standard_view_button.clicked.connect(self._on_standard_view_apply)
        scene_layout.addWidget(self.apply_standard_view_button)

        self.axes_checkbox = QCheckBox("Show Axes")
        self.axes_checkbox.setChecked(True)
        self.axes_checkbox.toggled.connect(self._on_axes_toggled)
        scene_layout.addWidget(self.axes_checkbox)

        self.grid_checkbox = QCheckBox("Show Grid")
        self.grid_checkbox.setChecked(False)
        self.grid_checkbox.toggled.connect(self._on_grid_toggled)
        scene_layout.addWidget(self.grid_checkbox)

        self.screenshot_button = QPushButton("Export Screenshot...")
        self.screenshot_button.clicked.connect(self._on_save_screenshot)
        scene_layout.addWidget(self.screenshot_button)

        scene_group.setLayout(scene_layout)
        layout.addWidget(scene_group)

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

        self.pc_group.setLayout(pc_layout)
        self.pc_group.setVisible(False)
        layout.addWidget(self.pc_group)

        info_group = QGroupBox("Model Info")
        info_layout = QVBoxLayout()
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(170)
        self.info_text.setText("No model loaded.")
        info_layout.addWidget(self.info_text)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        help_group = QGroupBox("Shortcuts")
        help_layout = QVBoxLayout()
        help_text = QLabel(
            "F / R: Fit View\n"
            "W: Toggle Wireframe\n"
            "1 / 3 / 7: Front / Right / Top\n"
            "Esc: Close Window\n"
            "Left Drag: Orbit\n"
            "Right Drag: Pan\n"
            "Wheel: Zoom"
        )
        help_layout.addWidget(help_text)
        help_group.setLayout(help_layout)
        layout.addWidget(help_group)

        layout.addStretch()

    def _call_main_window(self, method_name, *args):
        """Invoke a method on the top-level window if present."""
        window = self.window()
        if hasattr(window, method_name):
            return getattr(window, method_name)(*args)
        return None

    def set_scene_state(self, show_axes, show_grid, view_name=None):
        """Synchronize scene UI state."""
        self.axes_checkbox.blockSignals(True)
        self.axes_checkbox.setChecked(bool(show_axes))
        self.axes_checkbox.blockSignals(False)

        self.grid_checkbox.blockSignals(True)
        self.grid_checkbox.setChecked(bool(show_grid))
        self.grid_checkbox.blockSignals(False)

        if view_name:
            self.set_standard_view(view_name)

    def set_standard_view(self, view_name):
        """Select a standard view in the combo box."""
        index = self.standard_view_combo.findData(view_name)
        if index >= 0:
            self.standard_view_combo.blockSignals(True)
            self.standard_view_combo.setCurrentIndex(index)
            self.standard_view_combo.blockSignals(False)

    def _on_load_file(self):
        """Open a file dialog and load the selected file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open 3D Model",
            "",
            "3D Models (*.obj *.stl *.ply *.xyz);;All Files (*)",
        )
        if not file_path:
            return

        if self._call_main_window('open_model_file', file_path) is None:
            self.load_file(file_path)

    def load_file(self, file_path):
        """Load a supported file path into the viewport."""
        try:
            ext = os.path.splitext(file_path)[1].lower()

            if ext in {'.obj', '.stl', '.ply'}:
                try:
                    data = MeshLoader.load(file_path)
                    if ext == '.ply' and (data['indices'] is None or len(data['indices']) == 0):
                        point_data = PointCloudLoader.load(file_path)
                        return self._load_point_cloud_data(point_data, file_path)
                    return self._load_mesh_data(data, file_path)
                except Exception:
                    if ext == '.ply':
                        data = PointCloudLoader.load(file_path)
                        return self._load_point_cloud_data(data, file_path)
                    raise

            if ext == '.xyz':
                data = PointCloudLoader.load(file_path)
                return self._load_point_cloud_data(data, file_path)

            raise ValueError(f"Unsupported file format: {ext}")
        except Exception as error:
            QMessageBox.critical(self, "Load Failed", f"Could not load file:\n{error}")
            return False

    def _load_mesh_data(self, data, file_path):
        """Load mesh data into the viewport."""
        if not self.gl_widget.load_mesh_data(
            data['vertices'],
            data['indices'],
            data['normals'],
            data['colors'],
        ):
            return False

        self.gl_widget.fit_view()
        self.current_file_path = file_path
        self.data_type = 'mesh'
        self.mesh_group.setVisible(True)
        self.pc_group.setVisible(False)
        self._update_info_text(data, 'mesh')
        return True

    def _load_point_cloud_data(self, data, file_path):
        """Load point-cloud data into the viewport."""
        if not self.gl_widget.load_point_cloud_data(data['points'], data['colors']):
            return False

        self.gl_widget.fit_view()
        self.current_file_path = file_path
        self.data_type = 'point_cloud'
        self.mesh_group.setVisible(False)
        self.pc_group.setVisible(True)
        self._update_info_text(data, 'point_cloud')
        return True

    def _update_info_text(self, data, data_type):
        """Refresh the model information summary."""
        lines = []
        if self.current_file_path:
            lines.append(f"File: {os.path.basename(self.current_file_path)}")
            lines.append(f"Path: {self.current_file_path}")

        if data_type == 'mesh':
            lines.append("Type: Mesh")
            lines.append(f"Vertices: {len(data['vertices']):,}")
            lines.append(f"Faces: {len(data['indices']):,}")
            lines.append("Colors: Vertex Color" if data['colors'] is not None else "Colors: Uniform")
        else:
            lines.append("Type: Point Cloud")
            lines.append(f"Points: {len(data['points']):,}")
            lines.append("Colors: RGB/Height-based" if data['colors'] is not None else "Colors: Uniform")

        self.info_text.setText("\n".join(lines))

    def _on_fit_view(self):
        """Fit the current scene into the viewport."""
        if self._call_main_window('fit_view') is None:
            self.gl_widget.fit_view()

    def _on_standard_view_apply(self):
        """Apply the selected standard view."""
        view_name = self.standard_view_combo.currentData()
        if self._call_main_window('set_standard_view', view_name) is None:
            self.gl_widget.set_standard_view(view_name)

    def _on_axes_toggled(self, checked):
        """Toggle axes visibility."""
        if self._call_main_window('set_show_axes', checked) is None:
            self.gl_widget.set_show_axes(checked)

    def _on_grid_toggled(self, checked):
        """Toggle grid visibility."""
        if self._call_main_window('set_show_grid', checked) is None:
            self.gl_widget.set_show_grid(checked)

    def _on_save_screenshot(self):
        """Export a screenshot through the main window when possible."""
        if self._call_main_window('export_screenshot') is None:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Screenshot",
                "viewer_screenshot.png",
                "PNG Image (*.png)",
            )
            if file_path:
                if not file_path.lower().endswith('.png'):
                    file_path += '.png'
                if not self.gl_widget.capture_viewport(file_path):
                    QMessageBox.critical(self, "Save Failed", "Could not save the screenshot.")

    def _on_mesh_render_mode_changed(self, index):
        """Update mesh render mode."""
        modes = ['surface', 'wireframe', 'surface+wireframe']
        if index < len(modes):
            self.gl_widget.set_render_mode(modes[index])

    def _on_mesh_color_mode_changed(self, index):
        """Update mesh color mode."""
        modes = ['uniform', 'vertex']
        if index < len(modes):
            self.gl_widget.set_color_mode(modes[index])

    def _on_pc_color_mode_changed(self, index):
        """Update point-cloud color mode."""
        if not self.current_file_path or self.data_type != 'point_cloud':
            return

        try:
            data = PointCloudLoader.load(self.current_file_path)
            if index == 1:
                data['colors'] = PointCloudLoader._height_based_colors(data['points'])
            self.gl_widget.load_point_cloud_data(data['points'], data['colors'])
            self.gl_widget.fit_view()
        except Exception as error:
            QMessageBox.warning(self, "Warning", f"Could not update point cloud colors:\n{error}")

    def _on_point_size_changed(self, value):
        """Update point size."""
        size = value / 10.0
        self.point_size_label.setText(f"Point Size: {size:.1f}")
        self.gl_widget.set_point_size(size)

    def _on_line_width_changed(self, value):
        """Update mesh wireframe line width."""
        width = value / 10.0
        self.line_width_label.setText(f"Line Width: {width:.1f}")
        self.gl_widget.set_line_width(width)
