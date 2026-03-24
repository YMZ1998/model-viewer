import ctypes
import json
import os
from datetime import datetime

import numpy as np
from OpenGL.GL import *
from PyQt5.QtGui import QImage

from gl.camera import Camera
from inspection.models import InspectionGroup, MeasurementItem, SelectionState
from math_utils.trackball import Trackball


class Renderer:
    STANDARD_VIEWS = {
        'front': (np.array([0.0, 0.0, 1.0], dtype=np.float32), np.array([0.0, 1.0, 0.0], dtype=np.float32)),
        'back': (np.array([0.0, 0.0, -1.0], dtype=np.float32), np.array([0.0, 1.0, 0.0], dtype=np.float32)),
        'left': (np.array([-1.0, 0.0, 0.0], dtype=np.float32), np.array([0.0, 1.0, 0.0], dtype=np.float32)),
        'right': (np.array([1.0, 0.0, 0.0], dtype=np.float32), np.array([0.0, 1.0, 0.0], dtype=np.float32)),
        'top': (np.array([0.0, 1.0, 0.0], dtype=np.float32), np.array([0.0, 0.0, -1.0], dtype=np.float32)),
        'bottom': (np.array([0.0, -1.0, 0.0], dtype=np.float32), np.array([0.0, 0.0, 1.0], dtype=np.float32)),
        'isometric': (np.array([1.0, 1.0, 1.0], dtype=np.float32) / np.sqrt(3.0), np.array([0.0, 1.0, 0.0], dtype=np.float32)),
    }
    VISUAL_PRESETS = {
        'studio_dark': {
            'background': (0.12, 0.13, 0.16, 1.0),
            'ambient': (0.24, 0.24, 0.26, 1.0),
            'diffuse': (1.0, 1.0, 1.0, 1.0),
            'position': (2.5, 2.5, 2.0, 1.0),
        },
        'studio_light': {
            'background': (0.88, 0.91, 0.95, 1.0),
            'ambient': (0.52, 0.52, 0.52, 1.0),
            'diffuse': (0.94, 0.94, 0.94, 1.0),
            'position': (2.0, 3.0, 2.0, 1.0),
        },
        'blueprint': {
            'background': (0.08, 0.16, 0.24, 1.0),
            'ambient': (0.18, 0.24, 0.30, 1.0),
            'diffuse': (0.86, 0.95, 1.0, 1.0),
            'position': (1.5, 2.8, 2.4, 1.0),
        },
        'inspection_lab': {
            'background': (0.15, 0.16, 0.15, 1.0),
            'ambient': (0.30, 0.32, 0.30, 1.0),
            'diffuse': (1.0, 0.98, 0.92, 1.0),
            'position': (3.2, 2.2, 1.6, 1.0),
        },
    }

    def __init__(self, width=800, height=600):
        self.camera = Camera(width, height)
        self.trackball = Trackball()
        self.data_type = None
        self.render_mode = 'surface'
        self.color_mode = 'uniform'
        self.mesh_opacity = 1.0
        self.point_opacity = 1.0
        self.backface_culling = False
        self.visual_preset = 'studio_dark'
        self.section_plane_enabled = False
        self.section_plane_axis = 'z'
        self.section_plane_offset_ratio = 0.0
        self.section_plane_inverted = False
        self.point_size = 2.0
        self.line_width = 2.0
        self.vertices = None
        self.indices = None
        self.triangle_indices = None
        self.normals = None
        self.colors = None
        self.edges = None
        self.face_normals = None
        self.face_centers = None
        self.face_areas = None
        self.model_path = None
        self.model_center_offset = np.zeros(3, dtype=np.float32)
        self.model_bbox_min = np.array([-1.0, -1.0, -1.0], dtype=np.float32)
        self.model_bbox_max = np.array([1.0, 1.0, 1.0], dtype=np.float32)
        self.scene_radius = 1.0
        self.show_axes = True
        self.show_grid = False
        self.show_bounding_box = False
        self.show_model_center = False
        self.show_vertex_normals = False
        self.show_face_normals = False
        self.inspection_mode = False
        self.pick_preference = 'balanced'
        self.gpu_dirty = False
        self.helper_dirty = True
        self.vertex_vbo = None
        self.normal_vbo = None
        self.color_vbo = None
        self.index_ebo = None
        self.edge_ebo = None
        self.index_count = 0
        self.edge_count = 0
        self.axes_vbo = None
        self.axes_color_vbo = None
        self.axes_count = 0
        self.grid_vbo = None
        self.grid_color_vbo = None
        self.grid_count = 0
        self.groups = {}
        self.group_order = []
        self.measurement_items = {}
        self.current_group_id = None
        self.selection_state = SelectionState()
        self._group_counter = 0
        self._measurement_counter = 0
        self.initialized = False
        self._reset_inspection_state()

    def initialize(self):
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        glShadeModel(GL_SMOOTH)
        self.initialized = True
        self._apply_visual_preset()
        self._update_helper_buffers()

    def _apply_visual_preset(self):
        preset = self.VISUAL_PRESETS.get(self.visual_preset, self.VISUAL_PRESETS['studio_dark'])
        glClearColor(*preset['background'])
        glLightfv(GL_LIGHT0, GL_POSITION, preset['position'])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, preset['diffuse'])
        glLightfv(GL_LIGHT0, GL_AMBIENT, preset['ambient'])

    def _delete_buffer(self, buffer_id):
        if buffer_id is not None:
            glDeleteBuffers(1, [buffer_id])
        return None

    def _release_geometry_buffers(self):
        self.vertex_vbo = self._delete_buffer(self.vertex_vbo)
        self.normal_vbo = self._delete_buffer(self.normal_vbo)
        self.color_vbo = self._delete_buffer(self.color_vbo)
        self.index_ebo = self._delete_buffer(self.index_ebo)
        self.edge_ebo = self._delete_buffer(self.edge_ebo)
        self.index_count = 0
        self.edge_count = 0

    def _release_helper_buffers(self):
        self.axes_vbo = self._delete_buffer(self.axes_vbo)
        self.axes_color_vbo = self._delete_buffer(self.axes_color_vbo)
        self.grid_vbo = self._delete_buffer(self.grid_vbo)
        self.grid_color_vbo = self._delete_buffer(self.grid_color_vbo)
        self.axes_count = 0
        self.grid_count = 0

    def _upload_buffer(self, target, data):
        data = np.ascontiguousarray(data)
        buffer_id = glGenBuffers(1)
        glBindBuffer(target, buffer_id)
        glBufferData(target, data.nbytes, data, GL_STATIC_DRAW)
        glBindBuffer(target, 0)
        return buffer_id

    def _upload_line_buffers(self, vertices, colors):
        return self._upload_buffer(GL_ARRAY_BUFFER, vertices), self._upload_buffer(GL_ARRAY_BUFFER, colors), int(len(vertices))

    def _upload_current_data(self):
        if not self.initialized or self.vertices is None or len(self.vertices) == 0:
            return
        self._release_geometry_buffers()
        self.vertex_vbo = self._upload_buffer(GL_ARRAY_BUFFER, self.vertices.astype(np.float32))
        if self.normals is not None and len(self.normals) == len(self.vertices):
            self.normal_vbo = self._upload_buffer(GL_ARRAY_BUFFER, self.normals.astype(np.float32))
        if self.colors is not None and len(self.colors) == len(self.vertices):
            self.color_vbo = self._upload_buffer(GL_ARRAY_BUFFER, self._build_display_colors())
        if self.indices is not None and len(self.indices) > 0:
            self.index_ebo = self._upload_buffer(GL_ELEMENT_ARRAY_BUFFER, self.indices.astype(np.uint32))
            self.index_count = int(len(self.indices))
        if self.edges is not None and len(self.edges) > 0:
            self.edge_ebo = self._upload_buffer(GL_ELEMENT_ARRAY_BUFFER, self.edges.astype(np.uint32))
            self.edge_count = int(len(self.edges))
        self.gpu_dirty = False

    def _build_display_colors(self):
        """Build RGBA colors for the current geometry upload."""
        colors = np.asarray(self.colors, dtype=np.float32)
        if colors.ndim != 2 or colors.shape[1] not in {3, 4}:
            return colors.astype(np.float32)

        if self.data_type == 'mesh':
            alpha = self.mesh_opacity
        elif self.data_type == 'point_cloud':
            alpha = self.point_opacity
        else:
            alpha = 1.0

        if colors.shape[1] == 3:
            alpha_column = np.full((len(colors), 1), alpha, dtype=np.float32)
            return np.hstack([colors[:, :3], alpha_column]).astype(np.float32)

        display_colors = colors.astype(np.float32).copy()
        display_colors[:, 3] = alpha
        return display_colors

    def _nice_step(self, raw_step):
        raw_step = max(raw_step, 1e-3)
        exponent = np.floor(np.log10(raw_step))
        fraction = raw_step / (10 ** exponent)
        if fraction <= 1.0:
            nice_fraction = 1.0
        elif fraction <= 2.0:
            nice_fraction = 2.0
        elif fraction <= 5.0:
            nice_fraction = 5.0
        else:
            nice_fraction = 10.0
        return float(nice_fraction * (10 ** exponent))

    def _build_axes_geometry(self):
        length = max(1.0, self.scene_radius * 1.1)
        vertices = np.array([[0, 0, 0], [length, 0, 0], [0, 0, 0], [0, length, 0], [0, 0, 0], [0, 0, length]], dtype=np.float32)
        colors = np.array([[1, .2, .2], [1, .2, .2], [.2, 1, .2], [.2, 1, .2], [.2, .4, 1], [.2, .4, 1]], dtype=np.float32)
        return vertices, colors

    def _build_grid_geometry(self):
        half_extent = max(1.0, self.scene_radius * 1.2)
        step = self._nice_step((half_extent * 2.0) / 10.0)
        line_count = int(np.ceil(half_extent / step))
        full_extent = line_count * step
        vertices, colors = [], []
        base_color = np.array([0.35, 0.35, 0.35], dtype=np.float32)
        center_color = np.array([0.45, 0.45, 0.45], dtype=np.float32)
        for index in range(-line_count, line_count + 1):
            offset = index * step
            color = center_color if index == 0 else base_color
            vertices.extend([[-full_extent, 0, offset], [full_extent, 0, offset], [offset, 0, -full_extent], [offset, 0, full_extent]])
            colors.extend([color, color, color, color])
        return np.array(vertices, dtype=np.float32), np.array(colors, dtype=np.float32)

    def _update_helper_buffers(self):
        if not self.initialized:
            self.helper_dirty = True
            return
        self._release_helper_buffers()
        axes_vertices, axes_colors = self._build_axes_geometry()
        self.axes_vbo, self.axes_color_vbo, self.axes_count = self._upload_line_buffers(axes_vertices, axes_colors)
        grid_vertices, grid_colors = self._build_grid_geometry()
        self.grid_vbo, self.grid_color_vbo, self.grid_count = self._upload_line_buffers(grid_vertices, grid_colors)
        self.helper_dirty = False

    def _center_vertices(self, vertices):
        vertices = np.asarray(vertices, dtype=np.float32)
        if len(vertices) == 0:
            self.model_center_offset = np.zeros(3, dtype=np.float32)
            self.model_bbox_min = np.array([-1, -1, -1], dtype=np.float32)
            self.model_bbox_max = np.array([1, 1, 1], dtype=np.float32)
            self.scene_radius = 1.0
            self.helper_dirty = True
            return vertices
        min_pos, max_pos = np.min(vertices, axis=0), np.max(vertices, axis=0)
        center = (min_pos + max_pos) / 2.0
        centered = vertices - center
        self.model_center_offset = center.astype(np.float32)
        self.model_bbox_min = np.min(centered, axis=0).astype(np.float32)
        self.model_bbox_max = np.max(centered, axis=0).astype(np.float32)
        self.scene_radius = max(float(np.linalg.norm(centered, axis=1).max()), 1.0)
        self.helper_dirty = True
        return centered.astype(np.float32)

    def _compute_normals(self, vertices, triangle_indices):
        normals = np.zeros_like(vertices, dtype=np.float32)
        if triangle_indices is None or len(triangle_indices) == 0:
            return normals
        for tri in triangle_indices:
            v0, v1, v2 = vertices[tri]
            face_normal = np.cross(v1 - v0, v2 - v0)
            normals[tri[0]] += face_normal
            normals[tri[1]] += face_normal
            normals[tri[2]] += face_normal
        norms = np.linalg.norm(normals, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return (normals / norms).astype(np.float32)

    def _compute_face_data(self):
        if self.triangle_indices is None or len(self.triangle_indices) == 0 or self.vertices is None:
            self.face_centers = self.face_normals = self.face_areas = None
            return
        v0 = self.vertices[self.triangle_indices[:, 0]]
        v1 = self.vertices[self.triangle_indices[:, 1]]
        v2 = self.vertices[self.triangle_indices[:, 2]]
        cross = np.cross(v1 - v0, v2 - v0)
        norms = np.linalg.norm(cross, axis=1, keepdims=True)
        self.face_centers = ((v0 + v1 + v2) / 3.0).astype(np.float32)
        self.face_normals = (cross / np.where(norms == 0, 1.0, norms)).astype(np.float32)
        self.face_areas = (0.5 * norms[:, 0]).astype(np.float32)

    def _prepare_mesh_edges(self, triangle_indices):
        edges = set()
        for tri in triangle_indices:
            i0, i1, i2 = map(int, tri[:3])
            edges.add(tuple(sorted((i0, i1))))
            edges.add(tuple(sorted((i1, i2))))
            edges.add(tuple(sorted((i2, i0))))
        self.edges = np.array(list(edges), dtype=np.uint32).flatten() if edges else None

    def _reset_inspection_state(self):
        self.groups = {}
        self.group_order = []
        self.measurement_items = {}
        self.current_group_id = None
        self.selection_state = SelectionState()
        self._group_counter = 0
        self._measurement_counter = 0
        self.create_group("Default", make_current=True)

    def set_model_path(self, file_path):
        self.model_path = file_path

    def load_mesh_data(self, vertices, indices, normals=None, colors=None):
        triangles = np.asarray(indices, dtype=np.uint32).reshape(-1, 3) if len(indices) > 0 else np.zeros((0, 3), dtype=np.uint32)
        self.data_type = 'mesh'
        self.vertices = self._center_vertices(vertices)
        self.triangle_indices = triangles
        self.indices = triangles.flatten().astype(np.uint32)
        self.normals = normals.astype(np.float32) if normals is not None and len(normals) == len(self.vertices) else self._compute_normals(self.vertices, triangles)
        self.colors = colors.astype(np.float32) if colors is not None and len(colors) > 0 else np.tile(np.array([0.8, 0.8, 0.8], dtype=np.float32), (len(self.vertices), 1))
        self._prepare_mesh_edges(triangles)
        self._compute_face_data()
        self._reset_inspection_state()
        self.gpu_dirty = True
        if self.initialized:
            self._upload_current_data()
            self._update_helper_buffers()

    def load_point_cloud_data(self, points, colors=None):
        self.data_type = 'point_cloud'
        self.vertices = self._center_vertices(points)
        self.indices = self.triangle_indices = self.normals = self.edges = None
        self.face_normals = self.face_centers = self.face_areas = None
        self.colors = colors.astype(np.float32) if colors is not None and len(colors) > 0 else np.random.default_rng(42).random((len(points), 3), dtype=np.float32)
        self._reset_inspection_state()
        self.gpu_dirty = True
        if self.initialized:
            self._upload_current_data()
            self._update_helper_buffers()

    def _fit_distance(self):
        return (self.scene_radius / np.sin(np.radians(self.camera.fov) / 2.0)) * 1.1

    def _update_clip_planes(self, distance=None):
        distance = max(float(distance if distance is not None else np.linalg.norm(self.camera.position - self.camera.target)), 1e-3)
        self.camera.near = max(0.001, min(self.scene_radius * 0.01, distance * 0.25))
        self.camera.far = max(self.camera.near + 100.0, distance + self.scene_radius * 4.0)

    def _apply_camera_distance(self, distance):
        self.camera.scale = 1.0
        self.camera.ortho_scale = max(self.scene_radius * 1.15, 1.0)
        self._update_clip_planes(distance)

    def fit_view(self):
        self.camera.reset()
        self.camera.set_projection_mode(self.camera.projection_mode)
        self.trackball.reset()
        distance = self._fit_distance()
        self.camera.position = np.array([0.0, 0.0, distance], dtype=np.float32)
        self.camera.target = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.camera.up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        self._apply_camera_distance(distance)

    def reset_view(self):
        self.fit_view()

    def set_standard_view(self, view_name):
        if view_name not in self.STANDARD_VIEWS:
            return
        direction, up = self.STANDARD_VIEWS[view_name]
        self.trackball.reset()
        distance = self._fit_distance()
        self.camera.position = direction * distance
        self.camera.target = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.camera.up = up.astype(np.float32)
        self._apply_camera_distance(distance)

    def set_projection_mode(self, mode):
        if mode not in {'perspective', 'orthographic'}:
            return
        if mode == self.camera.projection_mode:
            return
        offset = self.camera.position - self.camera.target
        distance = np.linalg.norm(offset)
        direction = offset / distance if distance > 1e-6 else np.array([0.0, 0.0, 1.0], dtype=np.float32)
        if mode == 'orthographic':
            self.camera.sync_ortho_scale_from_distance()
        else:
            target_distance = max(self.camera.ortho_scale / np.tan(np.radians(self.camera.fov) / 2.0), 1e-3)
            self.camera.position = self.camera.target + direction * target_distance
            distance = target_distance
        self.camera.set_projection_mode(mode)
        self._update_clip_planes(distance)

    def set_visual_preset(self, preset_name):
        if preset_name not in self.VISUAL_PRESETS:
            return
        self.visual_preset = preset_name
        if self.initialized:
            self._apply_visual_preset()

    def set_section_plane_enabled(self, enabled):
        self.section_plane_enabled = bool(enabled)

    def set_section_plane_axis(self, axis):
        if axis in {'x', 'y', 'z'}:
            self.section_plane_axis = axis

    def set_section_plane_offset_ratio(self, ratio):
        self.section_plane_offset_ratio = max(-1.0, min(1.0, float(ratio)))

    def set_section_plane_inverted(self, inverted):
        self.section_plane_inverted = bool(inverted)

    def reset_section_plane(self):
        self.section_plane_enabled = False
        self.section_plane_axis = 'z'
        self.section_plane_offset_ratio = 0.0
        self.section_plane_inverted = False

    def set_show_axes(self, show):
        self.show_axes = bool(show)

    def set_show_grid(self, show):
        self.show_grid = bool(show)

    def set_show_bounding_box(self, show):
        self.show_bounding_box = bool(show)

    def set_show_model_center(self, show):
        self.show_model_center = bool(show)

    def set_show_vertex_normals(self, show):
        self.show_vertex_normals = bool(show)

    def set_show_face_normals(self, show):
        self.show_face_normals = bool(show)

    def set_inspection_mode(self, enabled):
        self.inspection_mode = bool(enabled)

    def set_pick_preference(self, preference):
        if preference in {'balanced', 'prefer_point', 'prefer_face'}:
            self.pick_preference = preference

    def _next_group_id(self):
        self._group_counter += 1
        return f"group-{self._group_counter}"

    def _next_measurement_id(self):
        self._measurement_counter += 1
        return f"measurement-{self._measurement_counter}"

    def create_group(self, name=None, make_current=True):
        group_id = self._next_group_id()
        group = InspectionGroup(group_id=group_id, name=(name or f"Group {self._group_counter}").strip() or f"Group {self._group_counter}")
        self.groups[group_id] = group
        self.group_order.append(group_id)
        if make_current or self.current_group_id is None:
            self.current_group_id = group_id
        return group_id

    def rename_group(self, group_id, new_name):
        group = self.groups.get(group_id)
        if not group or not (new_name or "").strip():
            return False
        group.name = new_name.strip()
        return True

    def delete_group(self, group_id):
        if group_id not in self.groups:
            return False
        for item_id in list(self.groups[group_id].item_ids):
            self.delete_measurement(item_id)
        self.groups.pop(group_id, None)
        self.group_order = [value for value in self.group_order if value != group_id]
        self.current_group_id = self.group_order[0] if self.group_order else None
        if self.current_group_id is None:
            self.create_group("Default", make_current=True)
        return True

    def set_current_group(self, group_id):
        if group_id in self.groups:
            self.current_group_id = group_id
            return True
        return False

    def set_group_visible(self, group_id, visible):
        if group_id not in self.groups:
            return False
        self.groups[group_id].visible = bool(visible)
        return True

    def _set_measurement_highlight(self, item_id):
        for measurement in self.measurement_items.values():
            measurement.highlighted = measurement.item_id == item_id

    def clear_selection(self):
        self.selection_state = SelectionState()
        self._set_measurement_highlight(None)

    def select_measurement_item(self, item_id):
        item = self.measurement_items.get(item_id)
        if not item:
            return False
        self._set_measurement_highlight(item_id)
        self.selection_state = SelectionState(selection_type='measurement', object_id=item_id, label=item.name, data={
            'measurement_type': item.measurement_type, 'value': float(item.value), 'unit': item.unit, 'group_id': item.group_id, 'visible': bool(item.visible),
        })
        return True

    def delete_measurement(self, item_id):
        item = self.measurement_items.pop(item_id, None)
        if not item:
            return False
        if item.group_id in self.groups:
            self.groups[item.group_id].item_ids = [value for value in self.groups[item.group_id].item_ids if value != item_id]
        if self.selection_state.selection_type == 'measurement' and self.selection_state.object_id == item_id:
            self.clear_selection()
        return True

    def set_measurement_visible(self, item_id, visible):
        if item_id not in self.measurement_items:
            return False
        self.measurement_items[item_id].visible = bool(visible)
        return True

    def _current_group_id_or_default(self, group_id=None):
        if group_id and group_id in self.groups:
            return group_id
        if self.current_group_id in self.groups:
            return self.current_group_id
        return self.create_group("Default", make_current=True)

    def _create_measurement_item(self, group_id, name, measurement_type, value, points=None, vertex_ids=None, face_id=None, extra=None):
        group_id = self._current_group_id_or_default(group_id)
        item_id = self._next_measurement_id()
        item = MeasurementItem(item_id=item_id, group_id=group_id, name=name, measurement_type=measurement_type, value=float(value),
                               points=[list(map(float, point)) for point in (points or [])], vertex_ids=[int(i) for i in (vertex_ids or [])],
                               face_id=int(face_id) if face_id is not None else None, extra=extra or {})
        self.measurement_items[item_id] = item
        self.groups[group_id].item_ids.append(item_id)
        self.select_measurement_item(item_id)
        return item_id

    def create_distance_measurement(self, group_id, point_a, point_b, vertex_ids=None):
        point_a, point_b = np.asarray(point_a, dtype=np.float32), np.asarray(point_b, dtype=np.float32)
        return self._create_measurement_item(group_id, f"Distance {self._measurement_counter + 1}", 'distance', np.linalg.norm(point_b - point_a), [point_a.tolist(), point_b.tolist()], vertex_ids or [])

    def create_angle_measurement(self, group_id, point_a, vertex, point_b, vertex_ids=None):
        point_a, vertex, point_b = np.asarray(point_a, dtype=np.float32), np.asarray(vertex, dtype=np.float32), np.asarray(point_b, dtype=np.float32)
        va, vb = point_a - vertex, point_b - vertex
        na, nb = np.linalg.norm(va), np.linalg.norm(vb)
        value = 0.0 if na < 1e-8 or nb < 1e-8 else np.degrees(np.arccos(np.clip(np.dot(va, vb) / (na * nb), -1.0, 1.0)))
        return self._create_measurement_item(group_id, f"Angle {self._measurement_counter + 1}", 'angle', value, [point_a.tolist(), vertex.tolist(), point_b.tolist()], vertex_ids or [], extra={'vertex_index': int(vertex_ids[1]) if vertex_ids and len(vertex_ids) > 1 else None})

    def create_face_area_measurement(self, group_id, face_id):
        if self.triangle_indices is None or self.face_areas is None or face_id < 0 or face_id >= len(self.triangle_indices):
            return None
        tri = self.triangle_indices[face_id]
        return self._create_measurement_item(group_id, f"Area {self._measurement_counter + 1}", 'face_area', float(self.face_areas[face_id]),
                                             [point.tolist() for point in self.vertices[tri]], [int(index) for index in tri], int(face_id))

    def _get_model_matrix(self):
        return self.camera.get_model_matrix() @ self.trackball.get_matrix()

    def _get_mvp_matrix(self):
        return self.camera.get_projection_matrix() @ self.camera.get_view_matrix() @ self._get_model_matrix()

    def _project_points(self, points):
        if points is None or len(points) == 0:
            return np.zeros((0, 3), dtype=np.float32)
        points = np.asarray(points, dtype=np.float32)
        if points.ndim == 1:
            points = points.reshape(1, 3)
        points_h = np.concatenate([points, np.ones((len(points), 1), dtype=np.float32)], axis=1)
        clip = (self._get_mvp_matrix() @ points_h.T).T
        valid = np.abs(clip[:, 3]) > 1e-8
        result = np.full((len(points), 3), np.inf, dtype=np.float32)
        if not np.any(valid):
            return result
        ndc = clip[valid, :3] / clip[valid, 3:4]
        result[valid] = np.column_stack([
            (ndc[:, 0] * 0.5 + 0.5) * self.camera.width,
            (1.0 - (ndc[:, 1] * 0.5 + 0.5)) * self.camera.height,
            ndc[:, 2] * 0.5 + 0.5,
        ]).astype(np.float32)
        return result

    def _screen_ray_object(self, screen_x, screen_y):
        width, height = max(1, self.camera.width), max(1, self.camera.height)
        ndc_x = (2.0 * float(screen_x) / width) - 1.0
        ndc_y = 1.0 - (2.0 * float(screen_y) / height)
        inv = np.linalg.inv(self._get_mvp_matrix())
        near_clip = np.array([ndc_x, ndc_y, -1.0, 1.0], dtype=np.float32)
        far_clip = np.array([ndc_x, ndc_y, 1.0, 1.0], dtype=np.float32)
        near_obj, far_obj = inv @ near_clip, inv @ far_clip
        near_obj = near_obj[:3] / max(near_obj[3], 1e-8)
        far_obj = far_obj[:3] / max(far_obj[3], 1e-8)
        direction = far_obj - near_obj
        norm = np.linalg.norm(direction)
        return near_obj.astype(np.float32), (direction / max(norm, 1e-8)).astype(np.float32)

    def _pick_measurement_item(self, screen_x, screen_y):
        threshold, best, best_distance = 14.0, None, np.inf
        for item in self.measurement_items.values():
            group = self.groups.get(item.group_id)
            if group is None or not group.visible or not item.visible:
                continue
            anchors = [np.asarray(point, dtype=np.float32) for point in item.points]
            if item.measurement_type == 'distance' and len(item.points) >= 2:
                anchors.append((np.asarray(item.points[0]) + np.asarray(item.points[1])) / 2.0)
            elif item.measurement_type == 'angle' and len(item.points) >= 3:
                anchors.append(np.asarray(item.points[1], dtype=np.float32))
            elif item.measurement_type == 'face_area' and len(item.points) >= 3:
                anchors.append(np.mean(np.asarray(item.points, dtype=np.float32), axis=0))
            projected = self._project_points(np.asarray(anchors, dtype=np.float32)) if anchors else np.zeros((0, 3), dtype=np.float32)
            if len(projected) == 0:
                continue
            distances = np.linalg.norm(projected[:, :2] - np.array([screen_x, screen_y], dtype=np.float32), axis=1)
            index = int(np.argmin(distances))
            if distances[index] < threshold and distances[index] < best_distance:
                best_distance, best = float(distances[index]), item
        if best is None:
            return None
        self.select_measurement_item(best.item_id)
        return {'selection_type': 'measurement', 'item_id': best.item_id, 'name': best.name, 'measurement_type': best.measurement_type}

    def _pick_point_screen(self, screen_x, screen_y, apply_selection=True):
        if self.vertices is None or len(self.vertices) == 0:
            return None
        projected = self._project_points(self.vertices)
        mask = np.isfinite(projected[:, 0]) & np.isfinite(projected[:, 1])
        if not np.any(mask):
            return None
        screen_points, depths = projected[mask, :2], projected[mask, 2]
        source_indices = np.nonzero(mask)[0]
        distances = np.linalg.norm(screen_points - np.array([screen_x, screen_y], dtype=np.float32), axis=1)
        candidate_mask = distances <= max(10.0, self.point_size * 2.5)
        if not np.any(candidate_mask):
            return None
        candidate_indices = source_indices[candidate_mask]
        candidate_distances = distances[candidate_mask]
        candidate_depths = depths[candidate_mask]
        best_local = int(np.argmin(candidate_distances + candidate_depths * 0.25))
        vertex_id = int(candidate_indices[best_local])
        position = self.vertices[vertex_id]
        result = {
            'selection_type': 'point',
            'vertex_id': vertex_id,
            'position': position.copy(),
            'screen_distance': float(candidate_distances[best_local]),
            'depth': float(candidate_depths[best_local]),
        }
        if apply_selection:
            self._set_measurement_highlight(None)
            self.selection_state = SelectionState(selection_type='point', object_id=vertex_id, label=f"Point {vertex_id}", data={'position': [float(value) for value in position]})
        return result

    @staticmethod
    def _ray_triangle_intersection(origin, direction, triangle):
        epsilon = 1e-8
        v0, v1, v2 = triangle
        edge1, edge2 = v1 - v0, v2 - v0
        h = np.cross(direction, edge2)
        a = np.dot(edge1, h)
        if -epsilon < a < epsilon:
            return None
        f = 1.0 / a
        s = origin - v0
        u = f * np.dot(s, h)
        if u < 0.0 or u > 1.0:
            return None
        q = np.cross(s, edge1)
        v = f * np.dot(direction, q)
        if v < 0.0 or u + v > 1.0:
            return None
        distance = f * np.dot(edge2, q)
        return distance if distance > epsilon else None

    def _pick_face_ray(self, screen_x, screen_y, apply_selection=True):
        if self.data_type != 'mesh' or self.triangle_indices is None or len(self.triangle_indices) == 0:
            return None
        origin, direction = self._screen_ray_object(screen_x, screen_y)
        best_face_id, best_distance = None, np.inf
        for face_id, tri in enumerate(self.triangle_indices):
            distance = self._ray_triangle_intersection(origin, direction, self.vertices[tri])
            if distance is not None and distance < best_distance:
                best_face_id, best_distance = face_id, distance
        if best_face_id is None:
            return None
        triangle = self.triangle_indices[best_face_id]
        center = self.face_centers[best_face_id] if self.face_centers is not None else np.mean(self.vertices[triangle], axis=0)
        projected_center = self._project_points(np.asarray(center, dtype=np.float32))[0]
        result = {
            'selection_type': 'face',
            'face_id': int(best_face_id),
            'vertex_ids': [int(index) for index in triangle],
            'points': self.vertices[triangle].copy(),
            'center': center.copy(),
            'ray_distance': float(best_distance),
            'depth': float(projected_center[2]) if np.isfinite(projected_center[2]) else 1.0,
        }
        if apply_selection:
            self._set_measurement_highlight(None)
            self.selection_state = SelectionState(selection_type='face', object_id=int(best_face_id), label=f"Face {best_face_id}", data={
                'face_id': int(best_face_id), 'vertex_ids': [int(index) for index in triangle], 'center': [float(value) for value in center],
                'area': float(self.face_areas[best_face_id]) if self.face_areas is not None else 0.0,
            })
        return result

    def _apply_pick_result(self, result):
        if result is None:
            self.clear_selection()
            return None
        if result['selection_type'] == 'point':
            vertex_id = int(result['vertex_id'])
            position = np.asarray(result['position'], dtype=np.float32)
            self._set_measurement_highlight(None)
            self.selection_state = SelectionState(
                selection_type='point',
                object_id=vertex_id,
                label=f"Point {vertex_id}",
                data={'position': [float(value) for value in position]},
            )
        elif result['selection_type'] == 'face':
            face_id = int(result['face_id'])
            center = np.asarray(result.get('center', [0.0, 0.0, 0.0]), dtype=np.float32)
            self._set_measurement_highlight(None)
            self.selection_state = SelectionState(
                selection_type='face',
                object_id=face_id,
                label=f"Face {face_id}",
                data={
                    'face_id': face_id,
                    'vertex_ids': [int(index) for index in result['vertex_ids']],
                    'center': [float(value) for value in center],
                    'area': float(self.face_areas[face_id]) if self.face_areas is not None and 0 <= face_id < len(self.face_areas) else 0.0,
                },
            )
        return result

    def _auto_pick_geometry(self, screen_x, screen_y):
        point_result = self._pick_point_screen(screen_x, screen_y, apply_selection=False)
        face_result = self._pick_face_ray(screen_x, screen_y, apply_selection=False) if self.data_type == 'mesh' else None
        if point_result is None:
            return face_result
        if face_result is None:
            return point_result

        threshold = max(10.0, self.point_size * 2.5)
        normalized = point_result['screen_distance'] / max(threshold, 1e-6)
        cutoff_map = {
            'prefer_point': 1.0,
            'balanced': 0.58,
            'prefer_face': 0.33,
        }
        if normalized <= cutoff_map.get(self.pick_preference, 0.58):
            return point_result

        if point_result['depth'] + 0.015 < face_result.get('depth', 1.0):
            return point_result
        return face_result

    def pick_at(self, screen_x, screen_y, pick_kind):
        if self.vertices is None or pick_kind not in {'point', 'face', 'auto'}:
            self.clear_selection()
            return None
        if pick_kind == 'auto':
            result = self._pick_measurement_item(screen_x, screen_y)
            if result is None:
                result = self._apply_pick_result(self._auto_pick_geometry(screen_x, screen_y))
        elif pick_kind == 'point':
            result = self._apply_pick_result(self._pick_point_screen(screen_x, screen_y, apply_selection=False))
        else:
            result = self._apply_pick_result(self._pick_face_ray(screen_x, screen_y, apply_selection=False))
        if result is None:
            self.clear_selection()
        return result

    def _draw_line_buffer(self, vertex_vbo, color_vbo, count, line_width=1.0):
        if vertex_vbo is None or color_vbo is None or count == 0:
            return
        glLineWidth(line_width)
        glEnableClientState(GL_VERTEX_ARRAY)
        glBindBuffer(GL_ARRAY_BUFFER, vertex_vbo)
        glVertexPointer(3, GL_FLOAT, 0, ctypes.c_void_p(0))
        glEnableClientState(GL_COLOR_ARRAY)
        glBindBuffer(GL_ARRAY_BUFFER, color_vbo)
        glColorPointer(3, GL_FLOAT, 0, ctypes.c_void_p(0))
        glDrawArrays(GL_LINES, 0, count)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_COLOR_ARRAY)

    def _render_helpers(self):
        if not self.show_axes and not self.show_grid and not self.section_plane_enabled:
            return
        glPushAttrib(GL_ALL_ATTRIB_BITS)
        glDisable(GL_LIGHTING)
        if self.show_grid:
            self._draw_line_buffer(self.grid_vbo, self.grid_color_vbo, self.grid_count, 1.0)
        if self.show_axes:
            self._draw_line_buffer(self.axes_vbo, self.axes_color_vbo, self.axes_count, 2.0)
        if self.section_plane_enabled:
            self._render_section_plane_overlay()
        glPopAttrib()

    def _draw_lines_immediate(self, vertices, color, width=1.0):
        if vertices is None or len(vertices) == 0:
            return
        glLineWidth(width)
        glColor3f(*color)
        glBegin(GL_LINES)
        for vertex in vertices:
            glVertex3f(*vertex)
        glEnd()

    def _draw_points_immediate(self, points, color, size=6.0):
        if points is None or len(points) == 0:
            return
        glPointSize(size)
        glColor3f(*color)
        glBegin(GL_POINTS)
        for point in points:
            glVertex3f(*point)
        glEnd()

    def _draw_line_strip(self, points, color, width=1.0):
        if points is None or len(points) == 0:
            return
        glLineWidth(width)
        glColor3f(*color)
        glBegin(GL_LINE_STRIP)
        for point in points:
            glVertex3f(*point)
        glEnd()

    def _draw_triangle_overlay(self, triangle_points, color, alpha=0.18, width=2.0):
        if triangle_points is None or len(triangle_points) != 3:
            return
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(color[0], color[1], color[2], alpha)
        glBegin(GL_TRIANGLES)
        for point in triangle_points:
            glVertex3f(*point)
        glEnd()

    def _section_axis_index(self):
        return {'x': 0, 'y': 1, 'z': 2}.get(self.section_plane_axis, 2)

    def _section_plane_extent(self):
        axis_index = self._section_axis_index()
        minimum = self.model_bbox_min[axis_index]
        maximum = self.model_bbox_max[axis_index]
        center = (minimum + maximum) * 0.5
        half_extent = max((maximum - minimum) * 0.5, 1e-3)
        return center, half_extent

    def _section_plane_position(self):
        center, half_extent = self._section_plane_extent()
        return float(center + self.section_plane_offset_ratio * half_extent)

    def _section_plane_normal(self):
        normal = np.zeros(3, dtype=np.float64)
        normal[self._section_axis_index()] = -1.0 if self.section_plane_inverted else 1.0
        return normal

    def _section_plane_equation(self):
        normal = self._section_plane_normal()
        position = self._section_plane_position()
        axis_index = self._section_axis_index()
        point = np.zeros(3, dtype=np.float64)
        point[axis_index] = position
        d_term = -float(np.dot(normal, point))
        return [float(normal[0]), float(normal[1]), float(normal[2]), d_term]

    def _section_plane_color(self):
        return {'x': (1.0, 0.35, 0.35), 'y': (0.35, 1.0, 0.45), 'z': (0.35, 0.55, 1.0)}.get(self.section_plane_axis, (0.9, 0.9, 0.9))

    def _render_section_plane_overlay(self):
        if self.vertices is None or len(self.vertices) == 0:
            return
        axis_index = self._section_axis_index()
        position = self._section_plane_position()
        padding = max(self.scene_radius * 0.04, 0.02)
        minimum = self.model_bbox_min - padding
        maximum = self.model_bbox_max + padding
        color = self._section_plane_color()

        if axis_index == 0:
            corners = np.array([
                [position, minimum[1], minimum[2]],
                [position, maximum[1], minimum[2]],
                [position, maximum[1], maximum[2]],
                [position, minimum[1], maximum[2]],
            ], dtype=np.float32)
        elif axis_index == 1:
            corners = np.array([
                [minimum[0], position, minimum[2]],
                [maximum[0], position, minimum[2]],
                [maximum[0], position, maximum[2]],
                [minimum[0], position, maximum[2]],
            ], dtype=np.float32)
        else:
            corners = np.array([
                [minimum[0], minimum[1], position],
                [maximum[0], minimum[1], position],
                [maximum[0], maximum[1], position],
                [minimum[0], maximum[1], position],
            ], dtype=np.float32)

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(color[0], color[1], color[2], 0.12)
        glBegin(GL_QUADS)
        for corner in corners:
            glVertex3f(*corner)
        glEnd()

        glLineWidth(1.5)
        glColor3f(*color)
        glBegin(GL_LINE_LOOP)
        for corner in corners:
            glVertex3f(*corner)
        glEnd()

    def _enable_section_plane(self):
        if not self.section_plane_enabled or self.vertices is None or len(self.vertices) == 0:
            glDisable(GL_CLIP_PLANE0)
            return
        glClipPlane(GL_CLIP_PLANE0, self._section_plane_equation())
        glEnable(GL_CLIP_PLANE0)

    def _disable_section_plane(self):
        glDisable(GL_CLIP_PLANE0)
        # glLineWidth(width)
        # glColor3f(*color)
        glBegin(GL_LINE_LOOP)
        # for point in triangle_points:
        #     glVertex3f(*point)
        glEnd()

    def _render_bounding_box(self):
        minimum, maximum = self.model_bbox_min, self.model_bbox_max
        corners = np.array([
            [minimum[0], minimum[1], minimum[2]], [maximum[0], minimum[1], minimum[2]], [maximum[0], maximum[1], minimum[2]], [minimum[0], maximum[1], minimum[2]],
            [minimum[0], minimum[1], maximum[2]], [maximum[0], minimum[1], maximum[2]], [maximum[0], maximum[1], maximum[2]], [minimum[0], maximum[1], maximum[2]],
        ], dtype=np.float32)
        edges = np.array([
            corners[0], corners[1], corners[1], corners[2], corners[2], corners[3], corners[3], corners[0],
            corners[4], corners[5], corners[5], corners[6], corners[6], corners[7], corners[7], corners[4],
            corners[0], corners[4], corners[1], corners[5], corners[2], corners[6], corners[3], corners[7],
        ], dtype=np.float32)
        self._draw_lines_immediate(edges, (1.0, 0.85, 0.15), width=1.5)

    def _build_normal_segments(self, points, normals, max_count=1500):
        if points is None or normals is None or len(points) == 0:
            return np.zeros((0, 3), dtype=np.float32)
        step = max(1, int(np.ceil(len(points) / max_count)))
        points, normals = points[::step], normals[::step]
        length = max(self.scene_radius * 0.08, 0.02)
        segments = np.empty((len(points) * 2, 3), dtype=np.float32)
        segments[0::2], segments[1::2] = points, points + normals * length
        return segments

    def _visible_measurements(self):
        for group_id in self.group_order:
            group = self.groups.get(group_id)
            if group is None or not group.visible:
                continue
            for item_id in group.item_ids:
                item = self.measurement_items.get(item_id)
                if item and item.visible:
                    yield item

    def _measurement_color(self, item):
        if item.highlighted or (self.selection_state.selection_type == 'measurement' and self.selection_state.object_id == item.item_id):
            return (1.0, 0.55, 0.1)
        return {'distance': (1.0, 0.9, 0.2), 'angle': (0.2, 0.9, 1.0)}.get(item.measurement_type, (1.0, 0.3, 1.0))

    def _render_measurements(self):
        for item in self._visible_measurements():
            color = self._measurement_color(item)
            points = np.asarray(item.points, dtype=np.float32)
            if item.measurement_type == 'distance' and len(points) >= 2:
                self._draw_lines_immediate(np.array([points[0], points[1]], dtype=np.float32), color, width=2.0)
                self._draw_points_immediate(points[:2], color, size=8.0)
            elif item.measurement_type == 'angle' and len(points) >= 3:
                self._draw_lines_immediate(np.array([points[1], points[0], points[1], points[2]], dtype=np.float32), color, width=2.0)
                self._draw_points_immediate(points[:3], color, size=8.0)
                va, vb = points[0] - points[1], points[2] - points[1]
                na, nb = np.linalg.norm(va), np.linalg.norm(vb)
                if na > 1e-8 and nb > 1e-8:
                    da, db = va / na, vb / nb
                    normal = np.cross(da, db)
                    normal /= max(np.linalg.norm(normal), 1e-8)
                    tangent = np.cross(normal, da)
                    tangent /= max(np.linalg.norm(tangent), 1e-8)
                    radius = min(na, nb) * 0.35
                    arc = [points[1] + (np.cos(t) * da + np.sin(t) * tangent) * radius for t in np.linspace(0.0, np.radians(item.value), 24)]
                    self._draw_line_strip(np.asarray(arc, dtype=np.float32), color, width=1.5)
            elif item.measurement_type == 'face_area' and len(points) >= 3:
                self._draw_triangle_overlay(points[:3], color, alpha=0.2, width=2.0)

    def _render_selection(self):
        if self.selection_state.selection_type == 'point':
            point = np.asarray(self.selection_state.data.get('position', []), dtype=np.float32)
            if len(point) == 3:
                self._draw_points_immediate(np.array([point], dtype=np.float32), (1.0, 0.35, 0.1), size=11.0)
        elif self.selection_state.selection_type == 'face':
            face_id = self.selection_state.data.get('face_id')
            if self.triangle_indices is not None and face_id is not None and 0 <= face_id < len(self.triangle_indices):
                self._draw_triangle_overlay(self.vertices[self.triangle_indices[int(face_id)]], (1.0, 0.45, 0.1), alpha=0.28, width=2.5)

    def _render_inspection_overlays(self):
        if self.vertices is None or len(self.vertices) == 0:
            return
        glPushAttrib(GL_ALL_ATTRIB_BITS)
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        if self.show_bounding_box:
            self._render_bounding_box()
        if self.show_model_center:
            self._draw_points_immediate(np.array([[0.0, 0.0, 0.0]], dtype=np.float32), (1.0, 1.0, 1.0), size=9.0)
        if self.show_vertex_normals and self.data_type == 'mesh' and self.normals is not None:
            self._draw_lines_immediate(self._build_normal_segments(self.vertices, self.normals, max_count=2000), (0.1, 1.0, 0.8), width=1.0)
        if self.show_face_normals and self.data_type == 'mesh' and self.face_normals is not None and self.face_centers is not None:
            self._draw_lines_immediate(self._build_normal_segments(self.face_centers, self.face_normals, max_count=1500), (1.0, 0.4, 0.4), width=1.0)
        self._render_measurements()
        self._render_selection()
        glPopAttrib()

    def render(self):
        if not self.initialized:
            self.initialize()
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        if self.gpu_dirty:
            self._upload_current_data()
        if self.helper_dirty:
            self._update_helper_buffers()
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glMultMatrixf(self.camera.get_projection_matrix().T.flatten())
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glMultMatrixf((self.camera.get_view_matrix() @ self._get_model_matrix()).T.flatten())
        self._enable_section_plane()
        if self.data_type == 'mesh':
            self._render_mesh()
        elif self.data_type == 'point_cloud':
            self._render_point_cloud()
        self._disable_section_plane()
        self._render_helpers()
        self._render_inspection_overlays()

    def _render_mesh(self):
        use_transparency = self.mesh_opacity < 0.999 and self.render_mode in {'surface', 'surface+wireframe'}
        if self.backface_culling:
            glEnable(GL_CULL_FACE)
            glCullFace(GL_BACK)
        else:
            glDisable(GL_CULL_FACE)
        if self.color_mode == 'uniform':
            glColor4f(0.8, 0.8, 0.8, self.mesh_opacity)
        if self.render_mode == 'surface':
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
            glEnable(GL_LIGHTING)
            if use_transparency:
                glEnable(GL_BLEND)
                glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
                glDepthMask(GL_FALSE)
            self._draw_mesh_elements()
            if use_transparency:
                glDepthMask(GL_TRUE)
                glDisable(GL_BLEND)
        elif self.render_mode == 'wireframe':
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
            glLineWidth(self.line_width)
            glDisable(GL_LIGHTING)
            self._draw_wireframe_elements()
        elif self.render_mode == 'surface+wireframe':
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
            glEnable(GL_LIGHTING)
            if use_transparency:
                glEnable(GL_BLEND)
                glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
                glDepthMask(GL_FALSE)
            self._draw_mesh_elements()
            if use_transparency:
                glDepthMask(GL_TRUE)
                glDisable(GL_BLEND)
            glPushAttrib(GL_ALL_ATTRIB_BITS)
            glDisable(GL_LIGHTING)
            glColor3f(0.0, 0.0, 0.0)
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
            glLineWidth(self.line_width)
            self._draw_wireframe_elements()
            glPopAttrib()
        glDisable(GL_CULL_FACE)

    def _draw_mesh_elements(self):
        if self.vertex_vbo is None or self.index_ebo is None or self.index_count == 0:
            return
        glEnableClientState(GL_VERTEX_ARRAY)
        glBindBuffer(GL_ARRAY_BUFFER, self.vertex_vbo)
        glVertexPointer(3, GL_FLOAT, 0, ctypes.c_void_p(0))
        if self.normal_vbo is not None:
            glEnableClientState(GL_NORMAL_ARRAY)
            glBindBuffer(GL_ARRAY_BUFFER, self.normal_vbo)
            glNormalPointer(GL_FLOAT, 0, ctypes.c_void_p(0))
        else:
            glDisableClientState(GL_NORMAL_ARRAY)
        if self.color_mode == 'vertex' and self.color_vbo is not None:
            glEnableClientState(GL_COLOR_ARRAY)
            glBindBuffer(GL_ARRAY_BUFFER, self.color_vbo)
            glColorPointer(4, GL_FLOAT, 0, ctypes.c_void_p(0))
        else:
            glDisableClientState(GL_COLOR_ARRAY)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.index_ebo)
        glDrawElements(GL_TRIANGLES, self.index_count, GL_UNSIGNED_INT, ctypes.c_void_p(0))
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_NORMAL_ARRAY)
        glDisableClientState(GL_COLOR_ARRAY)

    def _draw_wireframe_elements(self):
        if self.vertex_vbo is None:
            return
        edge_buffer = self.edge_ebo if self.edge_ebo is not None and self.edge_count > 0 else self.index_ebo
        edge_count = self.edge_count if self.edge_ebo is not None and self.edge_count > 0 else self.index_count
        primitive = GL_LINES if self.edge_ebo is not None and self.edge_count > 0 else GL_TRIANGLES
        if edge_buffer is None or edge_count == 0:
            return
        glEnableClientState(GL_VERTEX_ARRAY)
        glBindBuffer(GL_ARRAY_BUFFER, self.vertex_vbo)
        glVertexPointer(3, GL_FLOAT, 0, ctypes.c_void_p(0))
        if self.color_mode == 'vertex' and self.color_vbo is not None:
            glEnableClientState(GL_COLOR_ARRAY)
            glBindBuffer(GL_ARRAY_BUFFER, self.color_vbo)
            glColorPointer(4, GL_FLOAT, 0, ctypes.c_void_p(0))
        else:
            glDisableClientState(GL_COLOR_ARRAY)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, edge_buffer)
        glDrawElements(primitive, edge_count, GL_UNSIGNED_INT, ctypes.c_void_p(0))
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_COLOR_ARRAY)

    def _render_point_cloud(self):
        if self.vertex_vbo is None:
            return
        use_transparency = self.point_opacity < 0.999
        glDisable(GL_LIGHTING)
        if use_transparency:
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glDepthMask(GL_FALSE)
        glPointSize(self.point_size)
        glEnableClientState(GL_VERTEX_ARRAY)
        glBindBuffer(GL_ARRAY_BUFFER, self.vertex_vbo)
        glVertexPointer(3, GL_FLOAT, 0, ctypes.c_void_p(0))
        if self.color_vbo is not None:
            glEnableClientState(GL_COLOR_ARRAY)
            glBindBuffer(GL_ARRAY_BUFFER, self.color_vbo)
            glColorPointer(4, GL_FLOAT, 0, ctypes.c_void_p(0))
        else:
            glDisableClientState(GL_COLOR_ARRAY)
            glColor4f(0.85, 0.85, 0.85, self.point_opacity)
        glDrawArrays(GL_POINTS, 0, len(self.vertices))
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_COLOR_ARRAY)
        if use_transparency:
            glDepthMask(GL_TRUE)
            glDisable(GL_BLEND)

    def resize(self, width, height):
        self.camera.set_aspect_ratio(width, height)
        glViewport(0, 0, width, height)

    def rotate_view(self, start_x, start_y, end_x, end_y, width, height):
        self.trackball.apply_rotation(self.trackball.rotate(start_x, start_y, end_x, end_y, width, height))

    def pan_view(self, dx, dy):
        self.camera.pan(dx, dy)

    def zoom_view(self, factor):
        self.camera.zoom(factor)
        self._update_clip_planes()

    def set_render_mode(self, mode):
        if mode in {'surface', 'wireframe', 'surface+wireframe'}:
            self.render_mode = mode

    def set_color_mode(self, mode):
        if mode in {'uniform', 'vertex'}:
            self.color_mode = mode

    def set_mesh_opacity(self, opacity):
        """Set mesh opacity in the range [0.05, 1.0]."""
        self.mesh_opacity = max(0.05, min(1.0, float(opacity)))
        if self.data_type == 'mesh' and self.colors is not None:
            self.gpu_dirty = True

    def set_point_opacity(self, opacity):
        """Set point-cloud opacity in the range [0.05, 1.0]."""
        self.point_opacity = max(0.05, min(1.0, float(opacity)))
        if self.data_type == 'point_cloud' and self.colors is not None:
            self.gpu_dirty = True

    def set_backface_culling(self, enabled):
        self.backface_culling = bool(enabled)

    def set_point_size(self, size):
        self.point_size = max(0.5, min(10.0, float(size)))

    def set_line_width(self, width):
        self.line_width = max(0.5, min(10.0, float(width)))

    def get_camera_state(self):
        return {
            'position': [float(value) for value in self.camera.position],
            'target': [float(value) for value in self.camera.target],
            'up': [float(value) for value in self.camera.up],
            'fov': float(self.camera.fov),
            'projection_mode': self.camera.projection_mode,
            'ortho_scale': float(self.camera.ortho_scale),
            'near': float(self.camera.near),
            'far': float(self.camera.far),
            'trackball_matrix': self.trackball.get_matrix().astype(float).tolist(),
        }

    def _stats_snapshot(self):
        bbox_size = (self.model_bbox_max - self.model_bbox_min).astype(np.float32)
        return {
            'data_type': self.data_type,
            'vertex_count': int(len(self.vertices)) if self.vertices is not None else 0,
            'face_count': int(len(self.triangle_indices)) if self.triangle_indices is not None else 0,
            'point_count': int(len(self.vertices)) if self.data_type == 'point_cloud' and self.vertices is not None else 0,
            'bbox_size': [float(value) for value in bbox_size],
            'scene_radius': float(self.scene_radius),
            'model_center_offset': [float(value) for value in self.model_center_offset],
        }

    def get_inspection_state_snapshot(self):
        groups = []
        measurements = []
        for group_id in self.group_order:
            group = self.groups.get(group_id)
            if group is None:
                continue
            groups.append({'group_id': group.group_id, 'name': group.name, 'visible': bool(group.visible), 'item_count': len(group.item_ids), 'is_current': group.group_id == self.current_group_id})
            for item_id in group.item_ids:
                item = self.measurement_items.get(item_id)
                if item:
                    measurements.append({'item_id': item.item_id, 'group_id': item.group_id, 'name': item.name, 'measurement_type': item.measurement_type, 'value': float(item.value), 'unit': item.unit, 'visible': bool(item.visible), 'highlighted': bool(item.highlighted)})
        return {
            'inspection_mode': bool(self.inspection_mode),
            'pick_preference': self.pick_preference,
            'render_mode': self.render_mode,
            'color_mode': self.color_mode,
            'projection_mode': self.camera.projection_mode,
            'visual_preset': self.visual_preset,
            'section_plane_enabled': bool(self.section_plane_enabled),
            'section_plane_axis': self.section_plane_axis,
            'section_plane_offset_ratio': float(self.section_plane_offset_ratio),
            'section_plane_inverted': bool(self.section_plane_inverted),
            'mesh_opacity': float(self.mesh_opacity),
            'point_opacity': float(self.point_opacity),
            'point_size': float(self.point_size),
            'line_width': float(self.line_width),
            'backface_culling': bool(self.backface_culling),
            'show_bounding_box': bool(self.show_bounding_box),
            'show_model_center': bool(self.show_model_center),
            'show_vertex_normals': bool(self.show_vertex_normals),
            'show_face_normals': bool(self.show_face_normals),
            'current_group_id': self.current_group_id,
            'groups': groups,
            'measurements': measurements,
            'selection': {'selection_type': self.selection_state.selection_type, 'object_id': self.selection_state.object_id, 'label': self.selection_state.label, 'data': self.selection_state.data},
            'stats': self._stats_snapshot(),
        }

    def export_inspection_report(self, base_path, screenshot_path=None):
        root, _ = os.path.splitext(base_path)
        root = root or base_path
        png_path, json_path = screenshot_path or f"{root}.png", f"{root}.json"
        groups_payload = []
        for group_id in self.group_order:
            group = self.groups.get(group_id)
            if group is None:
                continue
            items = []
            for item_id in group.item_ids:
                item = self.measurement_items.get(item_id)
                if item:
                    items.append({
                        'item_id': item.item_id, 'name': item.name, 'type': item.measurement_type, 'value': float(item.value), 'unit': item.unit,
                        'visible': bool(item.visible), 'points': item.points, 'vertex_ids': item.vertex_ids, 'face_id': item.face_id, 'extra': item.extra,
                    })
            if items:
                groups_payload.append({'group_id': group.group_id, 'name': group.name, 'visible': bool(group.visible), 'items': items})
        payload = {
            'model_path': self.model_path,
            'export_time': datetime.now().isoformat(timespec='seconds'),
            'camera_state': self.get_camera_state(),
            'stats': self._stats_snapshot(),
            'section_plane': {
                'enabled': bool(self.section_plane_enabled),
                'axis': self.section_plane_axis,
                'offset_ratio': float(self.section_plane_offset_ratio),
                'inverted': bool(self.section_plane_inverted),
            },
            'selection': {'selection_type': self.selection_state.selection_type, 'object_id': self.selection_state.object_id, 'label': self.selection_state.label, 'data': self.selection_state.data},
            'groups': groups_payload,
            'screenshot_path': png_path,
        }
        with open(json_path, 'w', encoding='utf-8') as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        return {'png_path': png_path, 'json_path': json_path}

    def capture_viewport(self, path, width, height):
        if width <= 0 or height <= 0:
            return False
        try:
            glPixelStorei(GL_PACK_ALIGNMENT, 1)
            data = glReadPixels(0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE)
            if data is None:
                return False
            return QImage(data, width, height, QImage.Format_RGBA8888).mirrored(False, True).copy().save(path, "PNG")
        except Exception:
            return False
