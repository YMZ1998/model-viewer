import os

from PyQt5.QtCore import QPoint, Qt, pyqtSignal
from PyQt5.QtWidgets import QOpenGLWidget


class GLWidget(QOpenGLWidget):
    SUPPORTED_EXTENSIONS = {'.obj', '.stl', '.ply', '.xyz'}
    inspection_state_changed = pyqtSignal(dict)
    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.renderer = None
        self.last_pos = QPoint()
        self.press_pos = QPoint()
        self.mouse_pressed = False
        self.current_button = None
        self.drag_distance = 0
        self._pending_show_axes = True
        self._pending_show_grid = False
        self._pending_show_bounding_box = False
        self._pending_show_model_center = False
        self._pending_show_vertex_normals = False
        self._pending_show_face_normals = False
        self._pending_projection_mode = 'perspective'
        self._pending_visual_preset = 'studio_dark'
        self._pending_section_plane_enabled = False
        self._pending_section_plane_axis = 'z'
        self._pending_section_plane_offset_ratio = 0.0
        self._pending_section_plane_inverted = False
        self._pending_mesh_opacity = 1.0
        self._pending_point_opacity = 1.0
        self._pending_backface_culling = False
        self._pending_point_size = 2.0
        self._pending_line_width = 2.0
        self._inspection_mode = False
        self._inspection_action_mode = 'select'
        self._inspection_pick_mode = 'auto'
        self._inspection_pick_preference = 'balanced'
        self._pending_measurement_picks = []
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAcceptDrops(True)

    def initializeGL(self):
        from gl.renderer import Renderer
        self.renderer = Renderer()
        self.renderer.initialize()
        self.renderer.set_show_axes(self._pending_show_axes)
        self.renderer.set_show_grid(self._pending_show_grid)
        self.renderer.set_show_bounding_box(self._pending_show_bounding_box)
        self.renderer.set_show_model_center(self._pending_show_model_center)
        self.renderer.set_show_vertex_normals(self._pending_show_vertex_normals)
        self.renderer.set_show_face_normals(self._pending_show_face_normals)
        self.renderer.set_projection_mode(self._pending_projection_mode)
        self.renderer.set_visual_preset(self._pending_visual_preset)
        self.renderer.set_section_plane_enabled(self._pending_section_plane_enabled)
        self.renderer.set_section_plane_axis(self._pending_section_plane_axis)
        self.renderer.set_section_plane_offset_ratio(self._pending_section_plane_offset_ratio)
        self.renderer.set_section_plane_inverted(self._pending_section_plane_inverted)
        self.renderer.set_mesh_opacity(self._pending_mesh_opacity)
        self.renderer.set_point_opacity(self._pending_point_opacity)
        self.renderer.set_backface_culling(self._pending_backface_culling)
        self.renderer.set_point_size(self._pending_point_size)
        self.renderer.set_line_width(self._pending_line_width)
        self.renderer.set_inspection_mode(self._inspection_mode)
        self.renderer.set_pick_preference(self._inspection_pick_preference)
        self.renderer.fit_view()
        self._emit_inspection_state()

    def _ensure_renderer_ready(self):
        return self.renderer is not None and self.renderer.initialized

    def _emit_inspection_state(self):
        if not self._ensure_renderer_ready():
            return
        snapshot = self.renderer.get_inspection_state_snapshot()
        snapshot['action_mode'] = self._inspection_action_mode
        snapshot['pick_mode'] = self._inspection_pick_mode
        snapshot['pick_preference'] = self._inspection_pick_preference
        snapshot['pending_pick_count'] = len(self._pending_measurement_picks)
        self.inspection_state_changed.emit(snapshot)

    def _emit_status(self, message):
        self.status_message.emit(message)

    def resizeGL(self, width, height):
        if self._ensure_renderer_ready():
            self.renderer.resize(width, height)

    def paintGL(self):
        if self._ensure_renderer_ready():
            self.renderer.render()

    def mousePressEvent(self, event):
        self.last_pos = event.pos()
        self.press_pos = event.pos()
        self.mouse_pressed = True
        self.current_button = event.button()
        self.drag_distance = 0

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        is_click = self.drag_distance < 4
        if self._inspection_mode and self._ensure_renderer_ready() and event.button() == Qt.LeftButton and is_click:
            self._handle_inspection_click(event.x(), event.y())
        self.mouse_pressed = False
        self.current_button = None
        self.drag_distance = 0

    def mouseMoveEvent(self, event):
        if not self.mouse_pressed or not self._ensure_renderer_ready():
            return
        dx = event.x() - self.last_pos.x()
        dy = event.y() - self.last_pos.y()
        self.drag_distance += abs(dx) + abs(dy)
        if self.current_button == Qt.LeftButton and not self._inspection_mode:
            self.renderer.rotate_view(self.last_pos.x(), self.last_pos.y(), event.x(), event.y(), self.width(), self.height())
            self.update()
        elif self.current_button == Qt.RightButton:
            sensitivity = self.renderer.camera.get_pan_sensitivity(self.height())
            self.renderer.pan_view(-dx * sensitivity, dy * sensitivity)
            self.update()
        self.last_pos = event.pos()

    def wheelEvent(self, event):
        if not self._ensure_renderer_ready():
            return
        self.renderer.zoom_view(1.1 if event.angleDelta().y() > 0 else 0.9)
        self.update()

    def keyPressEvent(self, event):
        if not self._ensure_renderer_ready():
            return super().keyPressEvent(event)
        if event.key() in {Qt.Key_R, Qt.Key_F}:
            self.fit_view()
        elif event.key() == Qt.Key_W and self.renderer.data_type == 'mesh':
            if self.renderer.render_mode == 'surface':
                self.renderer.set_render_mode('wireframe')
            elif self.renderer.render_mode == 'wireframe':
                self.renderer.set_render_mode('surface+wireframe')
            else:
                self.renderer.set_render_mode('surface')
            self.update()
        elif event.key() == Qt.Key_Escape:
            self.window().close()
        else:
            super().keyPressEvent(event)

    def _handle_inspection_click(self, x, y):
        if self._inspection_action_mode == 'select':
            result = self.renderer.pick_at(x, y, self._inspection_pick_mode)
            self._emit_status("Selected inspection object" if result else "Nothing was hit")
        elif self._inspection_action_mode == 'distance':
            result = self.renderer.pick_at(x, y, 'point')
            self._consume_point_pick(result, required_count=2, creator=self._create_distance_from_pending, help_text="Distance: pick the second point")
        elif self._inspection_action_mode == 'angle':
            result = self.renderer.pick_at(x, y, 'point')
            self._consume_point_pick(result, required_count=3, creator=self._create_angle_from_pending, help_text="Angle: pick the next point")
        elif self._inspection_action_mode == 'face_area':
            result = self.renderer.pick_at(x, y, 'face')
            if result and result.get('selection_type') == 'face':
                item_id = self.renderer.create_face_area_measurement(self.renderer.current_group_id, result['face_id'])
                self._emit_status(f"Created face-area measurement {item_id}" if item_id else "Failed to create face-area measurement")
            else:
                self._emit_status("Face area requires picking one triangle")
        self._emit_inspection_state()
        self.update()

    def _consume_point_pick(self, result, required_count, creator, help_text):
        if not result or result.get('selection_type') != 'point':
            self._emit_status("Point was not hit, please try again")
            return
        self._pending_measurement_picks.append(result)
        if len(self._pending_measurement_picks) >= required_count:
            creator()
            self._pending_measurement_picks.clear()
        else:
            self._emit_status(help_text)

    def _create_distance_from_pending(self):
        first, second = self._pending_measurement_picks[:2]
        item_id = self.renderer.create_distance_measurement(self.renderer.current_group_id, first['position'], second['position'], [first['vertex_id'], second['vertex_id']])
        self._emit_status(f"Created distance measurement {item_id}")

    def _create_angle_from_pending(self):
        a, v, b = self._pending_measurement_picks[:3]
        item_id = self.renderer.create_angle_measurement(self.renderer.current_group_id, a['position'], v['position'], b['position'], [a['vertex_id'], v['vertex_id'], b['vertex_id']])
        self._emit_status(f"Created angle measurement {item_id}")

    def _extract_supported_path(self, event):
        mime_data = event.mimeData()
        if not mime_data.hasUrls():
            return None
        for url in mime_data.urls():
            if url.isLocalFile():
                path = url.toLocalFile()
                if os.path.splitext(path)[1].lower() in self.SUPPORTED_EXTENSIONS:
                    return path
        return None

    def dragEnterEvent(self, event):
        if self._extract_supported_path(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        file_path = self._extract_supported_path(event)
        if not file_path:
            event.ignore()
            return
        parent_window = self.window()
        if hasattr(parent_window, 'open_model_file'):
            parent_window.open_model_file(file_path)
        event.acceptProposedAction()

    def set_model_path(self, file_path):
        if self._ensure_renderer_ready():
            self.renderer.set_model_path(file_path)

    def load_mesh_data(self, vertices, indices, normals=None, colors=None):
        if not self._ensure_renderer_ready():
            return False
        self.renderer.load_mesh_data(vertices, indices, normals, colors)
        self._pending_measurement_picks.clear()
        self._emit_inspection_state()
        self.update()
        return True

    def load_point_cloud_data(self, points, colors=None):
        if not self._ensure_renderer_ready():
            return False
        self.renderer.load_point_cloud_data(points, colors)
        self._pending_measurement_picks.clear()
        self._emit_inspection_state()
        self.update()
        return True

    def fit_view(self):
        if not self._ensure_renderer_ready():
            return
        self.renderer.fit_view()
        self.update()

    def set_standard_view(self, view_name):
        if not self._ensure_renderer_ready():
            return
        self.renderer.set_standard_view(view_name)
        self.update()

    def set_projection_mode(self, mode):
        if mode not in {'perspective', 'orthographic'}:
            return
        self._pending_projection_mode = mode
        if self._ensure_renderer_ready():
            self.renderer.set_projection_mode(mode)
            self._emit_inspection_state()
            self.update()

    def set_visual_preset(self, preset_name):
        self._pending_visual_preset = preset_name
        if self._ensure_renderer_ready():
            self.renderer.set_visual_preset(preset_name)
            self._emit_inspection_state()
            self.update()

    def set_section_plane_enabled(self, enabled):
        self._pending_section_plane_enabled = bool(enabled)
        if self._ensure_renderer_ready():
            self.renderer.set_section_plane_enabled(enabled)
            self._emit_inspection_state()
            self.update()

    def set_section_plane_axis(self, axis):
        if axis not in {'x', 'y', 'z'}:
            return
        self._pending_section_plane_axis = axis
        if self._ensure_renderer_ready():
            self.renderer.set_section_plane_axis(axis)
            self._emit_inspection_state()
            self.update()

    def set_section_plane_offset_ratio(self, ratio):
        self._pending_section_plane_offset_ratio = float(ratio)
        if self._ensure_renderer_ready():
            self.renderer.set_section_plane_offset_ratio(ratio)
            self._emit_inspection_state()
            self.update()

    def set_section_plane_inverted(self, inverted):
        self._pending_section_plane_inverted = bool(inverted)
        if self._ensure_renderer_ready():
            self.renderer.set_section_plane_inverted(inverted)
            self._emit_inspection_state()
            self.update()

    def reset_section_plane(self):
        self._pending_section_plane_enabled = False
        self._pending_section_plane_axis = 'z'
        self._pending_section_plane_offset_ratio = 0.0
        self._pending_section_plane_inverted = False
        if self._ensure_renderer_ready():
            self.renderer.reset_section_plane()
            self._emit_inspection_state()
            self.update()

    def set_show_axes(self, show):
        self._pending_show_axes = bool(show)
        if self._ensure_renderer_ready():
            self.renderer.set_show_axes(show)
            self.update()

    def set_show_grid(self, show):
        self._pending_show_grid = bool(show)
        if self._ensure_renderer_ready():
            self.renderer.set_show_grid(show)
            self.update()

    def set_show_bounding_box(self, show):
        self._pending_show_bounding_box = bool(show)
        if self._ensure_renderer_ready():
            self.renderer.set_show_bounding_box(show)
            self._emit_inspection_state()
            self.update()

    def set_show_model_center(self, show):
        self._pending_show_model_center = bool(show)
        if self._ensure_renderer_ready():
            self.renderer.set_show_model_center(show)
            self._emit_inspection_state()
            self.update()

    def set_show_vertex_normals(self, show):
        self._pending_show_vertex_normals = bool(show)
        if self._ensure_renderer_ready():
            self.renderer.set_show_vertex_normals(show)
            self._emit_inspection_state()
            self.update()

    def set_show_face_normals(self, show):
        self._pending_show_face_normals = bool(show)
        if self._ensure_renderer_ready():
            self.renderer.set_show_face_normals(show)
            self._emit_inspection_state()
            self.update()

    def set_inspection_mode(self, enabled):
        self._inspection_mode = bool(enabled)
        self._pending_measurement_picks.clear()
        if self._ensure_renderer_ready():
            self.renderer.set_inspection_mode(enabled)
            self._emit_inspection_state()
            self.update()

    def set_inspection_pick_mode(self, pick_mode):
        if pick_mode in {'auto', 'point', 'face'}:
            self._inspection_pick_mode = pick_mode
            self._pending_measurement_picks.clear()
            self._emit_inspection_state()

    def set_inspection_pick_preference(self, preference):
        if preference in {'balanced', 'prefer_point', 'prefer_face'}:
            self._inspection_pick_preference = preference
            if self._ensure_renderer_ready():
                self.renderer.set_pick_preference(preference)
            self._pending_measurement_picks.clear()
            self._emit_inspection_state()

    def set_inspection_action_mode(self, action_mode):
        if action_mode in {'select', 'distance', 'angle', 'face_area'}:
            self._inspection_action_mode = action_mode
            self._pending_measurement_picks.clear()
            self._emit_inspection_state()

    def get_inspection_state_snapshot(self):
        return self.renderer.get_inspection_state_snapshot() if self._ensure_renderer_ready() else {}

    def create_group(self, name):
        if not self._ensure_renderer_ready():
            return None
        group_id = self.renderer.create_group(name, make_current=True)
        self._emit_inspection_state()
        self.update()
        return group_id

    def rename_group(self, group_id, new_name):
        if self._ensure_renderer_ready() and self.renderer.rename_group(group_id, new_name):
            self._emit_inspection_state()
            return True
        return False

    def delete_group(self, group_id):
        if self._ensure_renderer_ready() and self.renderer.delete_group(group_id):
            self._emit_inspection_state()
            self.update()
            return True
        return False

    def set_current_group(self, group_id):
        if self._ensure_renderer_ready() and self.renderer.set_current_group(group_id):
            self._emit_inspection_state()
            return True
        return False

    def set_group_visible(self, group_id, visible):
        if self._ensure_renderer_ready() and self.renderer.set_group_visible(group_id, visible):
            self._emit_inspection_state()
            self.update()
            return True
        return False

    def select_measurement_item(self, item_id):
        if self._ensure_renderer_ready() and self.renderer.select_measurement_item(item_id):
            self._emit_inspection_state()
            self.update()
            return True
        return False

    def set_measurement_visible(self, item_id, visible):
        if self._ensure_renderer_ready() and self.renderer.set_measurement_visible(item_id, visible):
            self._emit_inspection_state()
            self.update()
            return True
        return False

    def delete_measurement(self, item_id):
        if self._ensure_renderer_ready() and self.renderer.delete_measurement(item_id):
            self._emit_inspection_state()
            self.update()
            return True
        return False

    def capture_viewport(self, path):
        if not self._ensure_renderer_ready():
            return self.grabFramebuffer().save(path, "PNG")
        self.makeCurrent()
        self.renderer.render()
        success = self.renderer.capture_viewport(path, self.width(), self.height())
        self.doneCurrent()
        return success

    def export_inspection_report(self, base_path):
        if not self._ensure_renderer_ready():
            return None
        root, _ = os.path.splitext(base_path)
        root = root or base_path
        png_path = f"{root}.png"
        self.makeCurrent()
        self.renderer.render()
        image_ok = self.renderer.capture_viewport(png_path, self.width(), self.height())
        report_paths = self.renderer.export_inspection_report(root, screenshot_path=png_path) if image_ok else None
        self.doneCurrent()
        return report_paths if image_ok else None

    def set_render_mode(self, mode):
        if self._ensure_renderer_ready():
            self.renderer.set_render_mode(mode)
            self.update()

    def set_color_mode(self, mode):
        if self._ensure_renderer_ready():
            self.renderer.set_color_mode(mode)
            self.update()

    def set_mesh_opacity(self, opacity):
        self._pending_mesh_opacity = float(opacity)
        if self._ensure_renderer_ready():
            self.renderer.set_mesh_opacity(opacity)
            self._emit_inspection_state()
            self.update()

    def set_point_opacity(self, opacity):
        self._pending_point_opacity = float(opacity)
        if self._ensure_renderer_ready():
            self.renderer.set_point_opacity(opacity)
            self._emit_inspection_state()
            self.update()

    def set_backface_culling(self, enabled):
        self._pending_backface_culling = bool(enabled)
        if self._ensure_renderer_ready():
            self.renderer.set_backface_culling(enabled)
            self._emit_inspection_state()
            self.update()

    def set_point_size(self, size):
        self._pending_point_size = float(size)
        if self._ensure_renderer_ready():
            self.renderer.set_point_size(size)
            self._emit_inspection_state()
            self.update()

    def set_line_width(self, width):
        self._pending_line_width = float(width)
        if self._ensure_renderer_ready():
            self.renderer.set_line_width(width)
            self._emit_inspection_state()
            self.update()
