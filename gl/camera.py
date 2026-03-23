"""
Camera utilities for the viewer.
"""
import numpy as np

from math_utils.transform import perspective, look_at


class Camera:
    """Simple orbit-style camera."""

    def __init__(self, width=800, height=600):
        self.position = np.array([0.0, 0.0, 3.0], dtype=np.float32)
        self.target = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.up = np.array([0.0, 1.0, 0.0], dtype=np.float32)

        self.fov = 45.0
        self.near = 0.1
        self.far = 100.0

        self.width = width
        self.height = height
        self.scale = 1.0

    def get_view_matrix(self):
        """Return the camera view matrix."""
        return look_at(self.position, self.target, self.up)

    def get_projection_matrix(self):
        """Return the camera projection matrix."""
        aspect = self.width / self.height if self.height > 0 else 1.0
        return perspective(self.fov, aspect, self.near, self.far)

    def get_model_matrix(self):
        """Return the model transform matrix."""
        return np.identity(4, dtype=np.float32)

    def set_aspect_ratio(self, width, height):
        """Update viewport size."""
        self.width = width
        self.height = height

    def zoom(self, factor):
        """Zoom by dollying the camera toward or away from the target."""
        factor = max(factor, 1e-6)

        offset = self.position - self.target
        distance = np.linalg.norm(offset)
        if distance < 1e-6:
            return

        min_distance = 0.01
        max_distance = 1e6
        new_distance = np.clip(distance / factor, min_distance, max_distance)
        direction = offset / distance
        self.position = self.target + direction * new_distance
        self.scale = 1.0

    def get_pan_sensitivity(self, viewport_height):
        """Return world-space pan distance per screen pixel."""
        viewport_height = max(1, viewport_height)
        distance = np.linalg.norm(self.target - self.position)
        world_height = 2.0 * distance * np.tan(np.radians(self.fov) / 2.0)
        return world_height / viewport_height

    def pan(self, dx, dy):
        """Translate the camera parallel to the view plane."""
        forward = self.target - self.position
        forward_norm = np.linalg.norm(forward)
        if forward_norm < 1e-6:
            return
        forward = forward / forward_norm

        right = np.cross(forward, self.up)
        right_norm = np.linalg.norm(right)
        if right_norm < 1e-6:
            return
        right = right / right_norm

        up = np.cross(right, forward)
        movement = right * dx + up * dy
        self.position += movement
        self.target += movement

    def reset(self):
        """Reset camera to defaults."""
        self.position = np.array([0.0, 0.0, 3.0], dtype=np.float32)
        self.target = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        self.scale = 1.0
