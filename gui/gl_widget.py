"""
OpenGL viewport widget.
"""
import os

from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtWidgets import QOpenGLWidget


class GLWidget(QOpenGLWidget):
    """OpenGL rendering widget."""

    SUPPORTED_EXTENSIONS = {'.obj', '.stl', '.ply', '.xyz'}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.renderer = None

        self.last_pos = QPoint()
        self.mouse_pressed = False
        self.current_button = None

        self._pending_show_axes = True
        self._pending_show_grid = False

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAcceptDrops(True)

    def initializeGL(self):
        """Initialize the OpenGL renderer."""
        from gl.renderer import Renderer

        self.renderer = Renderer()
        self.renderer.initialize()
        self.renderer.set_show_axes(self._pending_show_axes)
        self.renderer.set_show_grid(self._pending_show_grid)
        self.renderer.fit_view()

    def _ensure_renderer_ready(self):
        """Return whether the renderer is initialized."""
        return self.renderer is not None and self.renderer.initialized

    def resizeGL(self, width, height):
        """Handle viewport resize."""
        if self._ensure_renderer_ready():
            self.renderer.resize(width, height)

    def paintGL(self):
        """Render the scene."""
        if self._ensure_renderer_ready():
            self.renderer.render()

    def mousePressEvent(self, event):
        """Store the current mouse state."""
        self.last_pos = event.pos()
        self.mouse_pressed = True
        self.current_button = event.button()

    def mouseReleaseEvent(self, event):
        """Clear the drag state."""
        super().mouseReleaseEvent(event)
        self.mouse_pressed = False
        self.current_button = None

    def mouseMoveEvent(self, event):
        """Handle orbit and pan interactions."""
        if not self.mouse_pressed or not self._ensure_renderer_ready():
            return

        dx = event.x() - self.last_pos.x()
        dy = event.y() - self.last_pos.y()
        width, height = self.width(), self.height()

        if self.current_button == Qt.LeftButton:
            self.renderer.rotate_view(
                self.last_pos.x(), self.last_pos.y(),
                event.x(), event.y(),
                width, height,
            )
            self.update()
        elif self.current_button == Qt.RightButton:
            sensitivity = self.renderer.camera.get_pan_sensitivity(height)
            self.renderer.pan_view(-dx * sensitivity, dy * sensitivity)
            self.update()

        self.last_pos = event.pos()

    def wheelEvent(self, event):
        """Handle zoom."""
        if not self._ensure_renderer_ready():
            return
        zoom_factor = 1.1 if event.angleDelta().y() > 0 else 0.9
        self.renderer.zoom_view(zoom_factor)
        self.update()

    def keyPressEvent(self, event):
        """Handle viewport shortcuts."""
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

        parent_window = self.window()
        if hasattr(parent_window, 'open_model_file'):
            parent_window.open_model_file(file_path)
        event.acceptProposedAction()

    def load_mesh_data(self, vertices, indices, normals=None, colors=None):
        """Load mesh data into the renderer."""
        if not self._ensure_renderer_ready():
            return False
        self.renderer.load_mesh_data(vertices, indices, normals, colors)
        self.update()
        return True

    def load_point_cloud_data(self, points, colors=None):
        """Load point-cloud data into the renderer."""
        if not self._ensure_renderer_ready():
            return False
        self.renderer.load_point_cloud_data(points, colors)
        self.update()
        return True

    def fit_view(self):
        """Fit the current scene into view."""
        if not self._ensure_renderer_ready():
            return
        self.renderer.fit_view()
        self.update()

    def set_standard_view(self, view_name):
        """Switch to a standard view direction."""
        if not self._ensure_renderer_ready():
            return
        self.renderer.set_standard_view(view_name)
        self.update()

    def set_show_axes(self, show):
        """Toggle scene axes."""
        self._pending_show_axes = bool(show)
        if not self._ensure_renderer_ready():
            return
        self.renderer.set_show_axes(show)
        self.update()

    def set_show_grid(self, show):
        """Toggle scene grid."""
        self._pending_show_grid = bool(show)
        if not self._ensure_renderer_ready():
            return
        self.renderer.set_show_grid(show)
        self.update()

    def capture_viewport(self, path):
        """Save the current viewport to disk."""
        if not self._ensure_renderer_ready():
            image = self.grabFramebuffer()
            return image.save(path, "PNG")

        self.makeCurrent()
        self.renderer.render()
        success = self.renderer.capture_viewport(path, self.width(), self.height())
        self.doneCurrent()
        return success

    def set_render_mode(self, mode):
        """Set mesh render mode."""
        if not self._ensure_renderer_ready():
            return
        self.renderer.set_render_mode(mode)
        self.update()

    def set_color_mode(self, mode):
        """Set color mode."""
        if not self._ensure_renderer_ready():
            return
        self.renderer.set_color_mode(mode)
        self.update()

    def set_point_size(self, size):
        """Set point size."""
        if not self._ensure_renderer_ready():
            return
        self.renderer.set_point_size(size)
        self.update()

    def set_line_width(self, width):
        """Set mesh wireframe line width."""
        if not self._ensure_renderer_ready():
            return
        self.renderer.line_width = width
        self.update()
