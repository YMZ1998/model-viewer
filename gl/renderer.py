"""
OpenGL renderer.
Manages mesh and point-cloud rendering with a fixed-function pipeline.
"""
import ctypes

from OpenGL.GL import *
import numpy as np

from gl.camera import Camera
from math_utils.trackball import Trackball


class Renderer:
    """OpenGL renderer."""

    def __init__(self, width=800, height=600):
        self.camera = Camera(width, height)
        self.trackball = Trackball()

        self.data_type = None  # 'mesh' or 'point_cloud'
        self.render_mode = 'surface'  # 'surface', 'wireframe', 'surface+wireframe'
        self.color_mode = 'uniform'  # 'uniform', 'vertex'
        self.point_size = 2.0
        self.line_width = 2.0

        self.vertices = None
        self.indices = None
        self.normals = None
        self.colors = None
        self.edges = None
        self.scene_radius = 1.0
        self.gpu_dirty = False
        self.vertex_vbo = None
        self.normal_vbo = None
        self.color_vbo = None
        self.index_ebo = None
        self.edge_ebo = None
        self.index_count = 0
        self.edge_count = 0

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

    def _delete_buffer(self, buffer_id):
        """Delete a GL buffer if it exists."""
        if buffer_id is not None:
            glDeleteBuffers(1, [buffer_id])
        return None

    def _release_gpu_buffers(self):
        """Release uploaded GPU buffers."""
        self.vertex_vbo = self._delete_buffer(self.vertex_vbo)
        self.normal_vbo = self._delete_buffer(self.normal_vbo)
        self.color_vbo = self._delete_buffer(self.color_vbo)
        self.index_ebo = self._delete_buffer(self.index_ebo)
        self.edge_ebo = self._delete_buffer(self.edge_ebo)
        self.index_count = 0
        self.edge_count = 0

    def _upload_buffer(self, target, data):
        """Upload a contiguous numpy array to a GL buffer."""
        contiguous = np.ascontiguousarray(data)
        buffer_id = glGenBuffers(1)
        glBindBuffer(target, buffer_id)
        glBufferData(target, contiguous.nbytes, contiguous, GL_STATIC_DRAW)
        glBindBuffer(target, 0)
        return buffer_id

    def _upload_current_data(self):
        """Upload current geometry to GPU buffers."""
        if not self.initialized or self.vertices is None or len(self.vertices) == 0:
            return

        self._release_gpu_buffers()

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

    def load_mesh_data(self, vertices, indices, normals=None, colors=None):
        """Load mesh data into the renderer."""
        try:
            print(f"Loading mesh: vertices={len(vertices)}, faces={len(indices)}")

            self.data_type = 'mesh'
            self.vertices = self._center_vertices(vertices)
            self.indices = (
                indices.flatten().astype(np.uint32)
                if len(indices) > 0 else np.array([], dtype=np.uint32)
            )

            if normals is not None and len(normals) > 0:
                self.normals = normals.astype(np.float32)
            elif len(indices) > 0:
                self.normals = self._compute_normals(self.vertices, indices)
            else:
                self.normals = np.zeros_like(self.vertices, dtype=np.float32)

            if colors is not None and len(colors) > 0:
                self.colors = colors.astype(np.float32)
            else:
                default_color = np.array([0.8, 0.8, 0.8], dtype=np.float32)
                self.colors = np.tile(default_color, (len(self.vertices), 1))

            if len(indices) > 0:
                self._prepare_mesh_edges(indices)
            else:
                self.edges = None

            self.gpu_dirty = True
            if self.initialized:
                self._upload_current_data()

            print(f"Mesh ready: edges={len(self.edges) if self.edges is not None else 0}")
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

    def _center_vertices(self, vertices):
        """Center the model around the origin and cache its radius."""
        vertices = np.asarray(vertices, dtype=np.float32)

        if len(vertices) == 0:
            self.scene_radius = 1.0
            return vertices

        min_pos = np.min(vertices, axis=0)
        max_pos = np.max(vertices, axis=0)
        center = (min_pos + max_pos) / 2.0
        centered_vertices = vertices - center

        radius = np.linalg.norm(centered_vertices, axis=1).max()
        self.scene_radius = max(float(radius), 1.0)

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
        normals = normals / norms

        return normals.astype(np.float32)

    def _prepare_mesh_edges(self, indices):
        """Build a de-duplicated edge list for wireframe rendering."""
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

    def render(self):
        """Render the current scene."""
        if not self.initialized:
            self.initialize()

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        if self.data_type is None:
            return

        if self.gpu_dirty:
            self._upload_current_data()

        view = self.camera.get_view_matrix()
        projection = self.camera.get_projection_matrix()
        model = self.camera.get_model_matrix() @ self.trackball.get_matrix()

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        modelview = view @ model
        glMultMatrixf(modelview.T.flatten())

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glMultMatrixf(projection.T.flatten())

        if self.data_type == 'mesh':
            self._render_mesh()
        elif self.data_type == 'point_cloud':
            self._render_point_cloud()

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
        """Draw mesh triangles using immediate mode."""
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
        """Draw wireframe edges using immediate mode."""
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

    def reset_view(self):
        """Reset camera and fit the full scene."""
        self.camera.reset()
        self.trackball.reset()

        if self.vertices is None or len(self.vertices) == 0:
            return

        fov_rad = np.radians(self.camera.fov)
        distance = (self.scene_radius / np.sin(fov_rad / 2.0)) * 1.1

        self.camera.position = np.array([0.0, 0.0, distance], dtype=np.float32)
        self.camera.target = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.camera.scale = 1.0

        self.camera.near = max(0.1, self.scene_radius * 0.01)
        self.camera.far = max(self.camera.near + 100.0, distance + self.scene_radius * 4.0)

        print(
            f"Reset view: position={self.camera.position}, target={self.camera.target}, "
            f"radius={self.scene_radius:.3f}, near={self.camera.near:.3f}, far={self.camera.far:.3f}"
        )

    def set_render_mode(self, mode):
        """Set mesh render mode."""
        if mode in ['surface', 'wireframe', 'surface+wireframe']:
            self.render_mode = mode

    def set_color_mode(self, mode):
        """Set color mode."""
        if mode in ['uniform', 'vertex']:
            self.color_mode = mode

    def set_point_size(self, size):
        """Set point size."""
        self.point_size = max(0.5, min(10.0, size))
