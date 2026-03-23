"""
OpenGL renderer for meshes, point clouds, and scene helpers.
"""
import ctypes

import numpy as np
from OpenGL.GL import *
from PyQt5.QtGui import QImage

from gl.camera import Camera
from math_utils.trackball import Trackball


class Renderer:
    """OpenGL renderer."""

    STANDARD_VIEWS = {
        'front': (np.array([0.0, 0.0, 1.0], dtype=np.float32), np.array([0.0, 1.0, 0.0], dtype=np.float32)),
        'back': (np.array([0.0, 0.0, -1.0], dtype=np.float32), np.array([0.0, 1.0, 0.0], dtype=np.float32)),
        'left': (np.array([-1.0, 0.0, 0.0], dtype=np.float32), np.array([0.0, 1.0, 0.0], dtype=np.float32)),
        'right': (np.array([1.0, 0.0, 0.0], dtype=np.float32), np.array([0.0, 1.0, 0.0], dtype=np.float32)),
        'top': (np.array([0.0, 1.0, 0.0], dtype=np.float32), np.array([0.0, 0.0, -1.0], dtype=np.float32)),
        'bottom': (np.array([0.0, -1.0, 0.0], dtype=np.float32), np.array([0.0, 0.0, 1.0], dtype=np.float32)),
        'isometric': (
            np.array([1.0, 1.0, 1.0], dtype=np.float32) / np.sqrt(3.0),
            np.array([0.0, 1.0, 0.0], dtype=np.float32),
        ),
    }

    def __init__(self, width=800, height=600):
        self.camera = Camera(width, height)
        self.trackball = Trackball()

        self.data_type = None
        self.render_mode = 'surface'
        self.color_mode = 'uniform'
        self.point_size = 2.0
        self.line_width = 2.0

        self.vertices = None
        self.indices = None
        self.normals = None
        self.colors = None
        self.edges = None

        self.scene_radius = 1.0
        self.show_axes = True
        self.show_grid = False

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

        self.initialized = False

    def initialize(self):
        """Initialize OpenGL state."""
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)
        glClearColor(0.2, 0.2, 0.2, 1.0)

        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_POSITION, [2.0, 2.0, 2.0, 1.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [1.0, 1.0, 1.0, 1.0])
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.2, 0.2, 0.2, 1.0])

        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)

        self.initialized = True
        self._update_helper_buffers()

    def _delete_buffer(self, buffer_id):
        """Delete a GL buffer if it exists."""
        if buffer_id is not None:
            glDeleteBuffers(1, [buffer_id])
        return None

    def _release_geometry_buffers(self):
        """Release uploaded model geometry buffers."""
        self.vertex_vbo = self._delete_buffer(self.vertex_vbo)
        self.normal_vbo = self._delete_buffer(self.normal_vbo)
        self.color_vbo = self._delete_buffer(self.color_vbo)
        self.index_ebo = self._delete_buffer(self.index_ebo)
        self.edge_ebo = self._delete_buffer(self.edge_ebo)
        self.index_count = 0
        self.edge_count = 0

    def _release_helper_buffers(self):
        """Release scene helper buffers."""
        self.axes_vbo = self._delete_buffer(self.axes_vbo)
        self.axes_color_vbo = self._delete_buffer(self.axes_color_vbo)
        self.grid_vbo = self._delete_buffer(self.grid_vbo)
        self.grid_color_vbo = self._delete_buffer(self.grid_color_vbo)
        self.axes_count = 0
        self.grid_count = 0

    def _upload_buffer(self, target, data):
        """Upload a contiguous numpy array to a GL buffer."""
        contiguous = np.ascontiguousarray(data)
        buffer_id = glGenBuffers(1)
        glBindBuffer(target, buffer_id)
        glBufferData(target, contiguous.nbytes, contiguous, GL_STATIC_DRAW)
        glBindBuffer(target, 0)
        return buffer_id

    def _upload_line_buffers(self, vertices, colors):
        """Upload line vertices and colors."""
        vertex_vbo = self._upload_buffer(GL_ARRAY_BUFFER, vertices.astype(np.float32))
        color_vbo = self._upload_buffer(GL_ARRAY_BUFFER, colors.astype(np.float32))
        return vertex_vbo, color_vbo, int(len(vertices))

    def _upload_current_data(self):
        """Upload current model geometry to GPU buffers."""
        if not self.initialized or self.vertices is None or len(self.vertices) == 0:
            return

        self._release_geometry_buffers()

        self.vertex_vbo = self._upload_buffer(GL_ARRAY_BUFFER, self.vertices.astype(np.float32))

        if self.normals is not None and len(self.normals) == len(self.vertices):
            self.normal_vbo = self._upload_buffer(GL_ARRAY_BUFFER, self.normals.astype(np.float32))

        if self.colors is not None and len(self.colors) == len(self.vertices):
            self.color_vbo = self._upload_buffer(GL_ARRAY_BUFFER, self.colors.astype(np.float32))

        if self.indices is not None and len(self.indices) > 0:
            self.index_ebo = self._upload_buffer(GL_ELEMENT_ARRAY_BUFFER, self.indices.astype(np.uint32))
            self.index_count = int(len(self.indices))

        if self.edges is not None and len(self.edges) > 0:
            self.edge_ebo = self._upload_buffer(GL_ELEMENT_ARRAY_BUFFER, self.edges.astype(np.uint32))
            self.edge_count = int(len(self.edges))

        self.gpu_dirty = False

    def _nice_step(self, raw_step):
        """Round a raw grid step to a readable value."""
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
        """Build world-axis helper geometry."""
        axis_length = max(1.0, self.scene_radius * 1.1)
        vertices = np.array([
            [0.0, 0.0, 0.0], [axis_length, 0.0, 0.0],
            [0.0, 0.0, 0.0], [0.0, axis_length, 0.0],
            [0.0, 0.0, 0.0], [0.0, 0.0, axis_length],
        ], dtype=np.float32)
        colors = np.array([
            [1.0, 0.2, 0.2], [1.0, 0.2, 0.2],
            [0.2, 1.0, 0.2], [0.2, 1.0, 0.2],
            [0.2, 0.4, 1.0], [0.2, 0.4, 1.0],
        ], dtype=np.float32)
        return vertices, colors

    def _build_grid_geometry(self):
        """Build ground-grid helper geometry on the XZ plane."""
        half_extent = max(1.0, self.scene_radius * 1.2)
        step = self._nice_step((half_extent * 2.0) / 10.0)
        line_count = int(np.ceil(half_extent / step))
        full_extent = line_count * step

        vertices = []
        colors = []
        base_color = np.array([0.35, 0.35, 0.35], dtype=np.float32)
        center_color = np.array([0.45, 0.45, 0.45], dtype=np.float32)

        for index in range(-line_count, line_count + 1):
            offset = index * step
            color = center_color if index == 0 else base_color

            vertices.extend([
                [-full_extent, 0.0, offset],
                [full_extent, 0.0, offset],
                [offset, 0.0, -full_extent],
                [offset, 0.0, full_extent],
            ])
            colors.extend([color, color, color, color])

        return np.array(vertices, dtype=np.float32), np.array(colors, dtype=np.float32)

    def _update_helper_buffers(self):
        """Rebuild helper geometry buffers."""
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
        """Center the model around the origin and cache its radius."""
        vertices = np.asarray(vertices, dtype=np.float32)
        if len(vertices) == 0:
            self.scene_radius = 1.0
            self.helper_dirty = True
            return vertices

        min_pos = np.min(vertices, axis=0)
        max_pos = np.max(vertices, axis=0)
        center = (min_pos + max_pos) / 2.0
        centered_vertices = vertices - center

        radius = np.linalg.norm(centered_vertices, axis=1).max()
        self.scene_radius = max(float(radius), 1.0)
        self.helper_dirty = True

        print(f"Model centered at origin: center={center}, radius={self.scene_radius:.3f}")
        return centered_vertices.astype(np.float32)

    def _compute_normals(self, vertices, indices):
        """Compute vertex normals from triangle indices."""
        normals = np.zeros_like(vertices)
        for tri in indices:
            v0, v1, v2 = vertices[tri]
            edge1 = v1 - v0
            edge2 = v2 - v0
            face_normal = np.cross(edge1, edge2)
            normals[tri[0]] += face_normal
            normals[tri[1]] += face_normal
            normals[tri[2]] += face_normal

        norms = np.linalg.norm(normals, axis=1, keepdims=True)
        norms[norms == 0] = 1
        return (normals / norms).astype(np.float32)

    def _prepare_mesh_edges(self, indices):
        """Build a deduplicated edge list for wireframe rendering."""
        try:
            edges = set()
            if len(indices.shape) == 1:
                indices = indices.reshape(-1, 3)

            for tri in indices:
                if not isinstance(tri, (list, np.ndarray)) or len(tri) < 3:
                    continue
                i0, i1, i2 = int(tri[0]), int(tri[1]), int(tri[2])
                edges.add(tuple(sorted((i0, i1))))
                edges.add(tuple(sorted((i1, i2))))
                edges.add(tuple(sorted((i2, i0))))

            self.edges = np.array(list(edges), dtype=np.uint32).flatten() if edges else None
        except Exception as error:
            print(f"Failed to prepare edges: {error}")
            self.edges = None

    def load_mesh_data(self, vertices, indices, normals=None, colors=None):
        """Load mesh data into the renderer."""
        try:
            self.data_type = 'mesh'
            self.vertices = self._center_vertices(vertices)
            self.indices = indices.flatten().astype(np.uint32) if len(indices) > 0 else np.array([], dtype=np.uint32)
            self.normals = normals.astype(np.float32) if normals is not None and len(normals) > 0 else None
            if self.normals is None:
                self.normals = self._compute_normals(self.vertices, indices) if len(indices) > 0 else np.zeros_like(self.vertices)

            if colors is not None and len(colors) > 0:
                self.colors = colors.astype(np.float32)
            else:
                default_color = np.array([0.8, 0.8, 0.8], dtype=np.float32)
                self.colors = np.tile(default_color, (len(self.vertices), 1))

            self._prepare_mesh_edges(indices) if len(indices) > 0 else setattr(self, 'edges', None)

            self.gpu_dirty = True
            if self.initialized:
                self._upload_current_data()
                self._update_helper_buffers()
        except Exception as error:
            print(f"Failed to load mesh data: {error}")
            import traceback
            traceback.print_exc()
            self.data_type = None
            self.vertices = None
            self.indices = None
            self.normals = None
            self.colors = None
            self.edges = None
            self.scene_radius = 1.0
            self.gpu_dirty = False
            self.helper_dirty = True

    def load_point_cloud_data(self, points, colors=None):
        """Load point-cloud data into the renderer."""
        self.data_type = 'point_cloud'
        self.vertices = self._center_vertices(points)
        self.indices = None
        self.normals = None
        self.edges = None

        if colors is not None and len(colors) > 0:
            self.colors = colors.astype(np.float32)
        else:
            rng = np.random.default_rng(42)
            self.colors = rng.random((len(points), 3), dtype=np.float32)

        self.gpu_dirty = True
        if self.initialized:
            self._upload_current_data()
            self._update_helper_buffers()

    def _fit_distance(self):
        """Return a camera distance that fits the current scene."""
        fov_rad = np.radians(self.camera.fov)
        return (self.scene_radius / np.sin(fov_rad / 2.0)) * 1.1

    def _apply_camera_distance(self, distance):
        """Update camera clipping planes for the current fit distance."""
        self.camera.scale = 1.0
        self.camera.near = max(0.1, self.scene_radius * 0.01)
        self.camera.far = max(self.camera.near + 100.0, distance + self.scene_radius * 4.0)

    def fit_view(self):
        """Reset interaction and fit the full scene."""
        self.camera.reset()
        self.trackball.reset()
        distance = self._fit_distance()
        self.camera.position = np.array([0.0, 0.0, distance], dtype=np.float32)
        self.camera.target = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.camera.up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        self._apply_camera_distance(distance)

    def reset_view(self):
        """Backward-compatible alias for fit_view."""
        self.fit_view()

    def set_standard_view(self, view_name):
        """Set a standard orthographic-like camera direction."""
        if view_name not in self.STANDARD_VIEWS:
            return

        direction, up = self.STANDARD_VIEWS[view_name]
        self.trackball.reset()
        distance = self._fit_distance()
        self.camera.position = direction * distance
        self.camera.target = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.camera.up = up.astype(np.float32)
        self._apply_camera_distance(distance)

    def set_show_axes(self, show):
        """Toggle world-axis helper visibility."""
        self.show_axes = bool(show)

    def set_show_grid(self, show):
        """Toggle ground-grid helper visibility."""
        self.show_grid = bool(show)

    def _draw_line_buffer(self, vertex_vbo, color_vbo, count, line_width=1.0):
        """Draw line data from GL buffers."""
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
        """Render axes and grid after the main scene."""
        if not self.show_axes and not self.show_grid:
            return

        glPushAttrib(GL_ALL_ATTRIB_BITS)
        glDisable(GL_LIGHTING)

        if self.show_grid:
            self._draw_line_buffer(self.grid_vbo, self.grid_color_vbo, self.grid_count, 1.0)
        if self.show_axes:
            self._draw_line_buffer(self.axes_vbo, self.axes_color_vbo, self.axes_count, 2.0)

        glPopAttrib()

    def render(self):
        """Render the current scene."""
        if not self.initialized:
            self.initialize()

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        if self.gpu_dirty:
            self._upload_current_data()
        if self.helper_dirty:
            self._update_helper_buffers()

        view = self.camera.get_view_matrix()
        projection = self.camera.get_projection_matrix()
        model = self.camera.get_model_matrix() @ self.trackball.get_matrix()

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glMultMatrixf(projection.T.flatten())

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        modelview = view @ model
        glMultMatrixf(modelview.T.flatten())

        if self.data_type == 'mesh':
            self._render_mesh()
        elif self.data_type == 'point_cloud':
            self._render_point_cloud()

        self._render_helpers()

    def _render_mesh(self):
        """Render mesh geometry."""
        try:
            if self.color_mode == 'uniform':
                glColor3f(0.8, 0.8, 0.8)

            if self.render_mode == 'surface':
                glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
                glEnable(GL_LIGHTING)
                self._draw_mesh_elements()
            elif self.render_mode == 'wireframe':
                glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
                glLineWidth(self.line_width)
                glDisable(GL_LIGHTING)
                self._draw_wireframe_elements()
            elif self.render_mode == 'surface+wireframe':
                glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
                glEnable(GL_LIGHTING)
                self._draw_mesh_elements()

                glPushAttrib(GL_ALL_ATTRIB_BITS)
                glDisable(GL_LIGHTING)
                glColor3f(0.0, 0.0, 0.0)
                glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
                glLineWidth(self.line_width)
                self._draw_wireframe_elements()
                glPopAttrib()
        except Exception as error:
            print(f"Failed to render mesh: {error}")
            import traceback
            traceback.print_exc()

    def _draw_mesh_elements(self):
        """Draw mesh triangles from GL buffers."""
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
            glColorPointer(3, GL_FLOAT, 0, ctypes.c_void_p(0))
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
        """Draw mesh wireframe from edge or triangle buffers."""
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
            glColorPointer(3, GL_FLOAT, 0, ctypes.c_void_p(0))
        else:
            glDisableClientState(GL_COLOR_ARRAY)

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, edge_buffer)
        glDrawElements(primitive, edge_count, GL_UNSIGNED_INT, ctypes.c_void_p(0))

        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_COLOR_ARRAY)

    def _render_point_cloud(self):
        """Render point-cloud geometry."""
        try:
            if self.vertex_vbo is None:
                return

            glDisable(GL_LIGHTING)
            glPointSize(self.point_size)
            glEnableClientState(GL_VERTEX_ARRAY)
            glBindBuffer(GL_ARRAY_BUFFER, self.vertex_vbo)
            glVertexPointer(3, GL_FLOAT, 0, ctypes.c_void_p(0))

            if self.color_vbo is not None:
                glEnableClientState(GL_COLOR_ARRAY)
                glBindBuffer(GL_ARRAY_BUFFER, self.color_vbo)
                glColorPointer(3, GL_FLOAT, 0, ctypes.c_void_p(0))
            else:
                glDisableClientState(GL_COLOR_ARRAY)

            glDrawArrays(GL_POINTS, 0, len(self.vertices))

            glBindBuffer(GL_ARRAY_BUFFER, 0)
            glDisableClientState(GL_VERTEX_ARRAY)
            glDisableClientState(GL_COLOR_ARRAY)
        except Exception as error:
            print(f"Failed to render point cloud: {error}")
            import traceback
            traceback.print_exc()

    def resize(self, width, height):
        """Handle viewport resize."""
        self.camera.set_aspect_ratio(width, height)
        glViewport(0, 0, width, height)

    def rotate_view(self, start_x, start_y, end_x, end_y, width, height):
        """Rotate view using trackball interaction."""
        rotation = self.trackball.rotate(start_x, start_y, end_x, end_y, width, height)
        self.trackball.apply_rotation(rotation)

    def pan_view(self, dx, dy):
        """Pan the camera."""
        self.camera.pan(dx, dy)

    def zoom_view(self, factor):
        """Zoom the camera."""
        self.camera.zoom(factor)

    def set_render_mode(self, mode):
        """Set mesh render mode."""
        if mode in {'surface', 'wireframe', 'surface+wireframe'}:
            self.render_mode = mode

    def set_color_mode(self, mode):
        """Set color mode."""
        if mode in {'uniform', 'vertex'}:
            self.color_mode = mode

    def set_point_size(self, size):
        """Set point size."""
        self.point_size = max(0.5, min(10.0, size))

    def capture_viewport(self, path, width, height):
        """Capture the current OpenGL framebuffer to a PNG file."""
        if width <= 0 or height <= 0:
            return False

        try:
            glPixelStorei(GL_PACK_ALIGNMENT, 1)
            data = glReadPixels(0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE)
            if data is None:
                return False

            image = QImage(data, width, height, QImage.Format_RGBA8888).mirrored(False, True).copy()
            return image.save(path, "PNG")
        except Exception as error:
            print(f"Failed to capture viewport: {error}")
            return False
