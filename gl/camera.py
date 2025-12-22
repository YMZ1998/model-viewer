"""
相机系统
管理视图和投影矩阵
"""
import numpy as np
from math_utils.transform import perspective, look_at, translation_matrix, scale_matrix


class Camera:
    """3D 相机"""
    
    def __init__(self, width=800, height=600):
        """
        初始化相机
        
        Args:
            width: 窗口宽度
            height: 窗口高度
        """
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
        """获取视图矩阵"""
        return look_at(self.position, self.target, self.up)
    
    def get_projection_matrix(self):
        """获取投影矩阵"""
        aspect = self.width / self.height if self.height > 0 else 1.0
        return perspective(self.fov, aspect, self.near, self.far)
    
    def get_model_matrix(self):
        """获取模型矩阵"""
        # 应用缩放
        model = scale_matrix(self.scale, self.scale, self.scale)
        return model
    
    def set_aspect_ratio(self, width, height):
        """设置宽高比"""
        self.width = width
        self.height = height
    
    def zoom(self, factor):
        """缩放"""
        self.scale *= factor
        self.scale = max(0.01, min(100.0, self.scale))
    
    def pan(self, dx, dy):
        """平移"""
        # 计算相机坐标系的右向量和上向量
        forward = self.target - self.position
        forward = forward / np.linalg.norm(forward)
        
        right = np.cross(forward, self.up)
        right = right / np.linalg.norm(right)
        
        up = np.cross(right, forward)
        
        # 平移
        movement = right * dx + up * dy
        self.position += movement
        self.target += movement
    
    def reset(self):
        """重置相机"""
        self.position = np.array([0.0, 0.0, 3.0], dtype=np.float32)
        self.target = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.scale = 1.0
