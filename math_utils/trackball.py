"""
Trackball 相机控制
实现虚拟球面旋转交互
"""
import numpy as np
from math_utils.transform import normalize


class Trackball:
    """虚拟球面相机控制器"""
    
    def __init__(self, radius=1.0):
        """
        初始化 Trackball
        
        Args:
            radius: 虚拟球半径
        """
        self.radius = radius
        self.rotation = np.identity(4, dtype=np.float32)
    
    def project_to_sphere(self, x, y, width, height):
        """
        将屏幕坐标投影到虚拟球面
        
        Args:
            x, y: 屏幕坐标
            width, height: 窗口大小
        
        Returns:
            球面上的3D坐标
        """
        # 归一化到 [-1, 1]
        x = (2.0 * x - width) / width
        y = (height - 2.0 * y) / height
        
        # 计算Z坐标
        d = np.sqrt(x * x + y * y)
        
        if d < self.radius * 0.70710678118654752440:  # sqrt(2)/2
            # 在球面上
            z = np.sqrt(self.radius * self.radius - d * d)
        else:
            # 在球面外，投影到双曲面
            t = self.radius / 1.41421356237309504880
            z = t * t / d
        
        v = np.array([x, y, z], dtype=np.float32)
        return normalize(v)
    
    def rotate(self, start_x, start_y, end_x, end_y, width, height):
        """
        根据鼠标拖动计算旋转
        
        Args:
            start_x, start_y: 起始位置
            end_x, end_y: 结束位置
            width, height: 窗口大小
        
        Returns:
            旋转矩阵
        """
        # 投影到球面
        v1 = self.project_to_sphere(start_x, start_y, width, height)
        v2 = self.project_to_sphere(end_x, end_y, width, height)
        
        # 计算旋转轴和角度
        axis = np.cross(v1, v2)
        axis_length = np.linalg.norm(axis)
        
        if axis_length < 1e-6:
            return np.identity(4, dtype=np.float32)
        
        axis = axis / axis_length
        angle = np.arcsin(min(1.0, axis_length))
        
        # 构建旋转矩阵
        return self._axis_angle_to_matrix(axis, angle)
    
    def _axis_angle_to_matrix(self, axis, angle):
        """
        轴角表示转换为旋转矩阵
        
        Args:
            axis: 旋转轴（归一化）
            angle: 旋转角（弧度）
        
        Returns:
            4x4 旋转矩阵
        """
        c = np.cos(angle)
        s = np.sin(angle)
        t = 1 - c
        
        x, y, z = axis
        
        mat = np.identity(4, dtype=np.float32)
        mat[0, 0] = t * x * x + c
        mat[0, 1] = t * x * y - s * z
        mat[0, 2] = t * x * z + s * y
        
        mat[1, 0] = t * x * y + s * z
        mat[1, 1] = t * y * y + c
        mat[1, 2] = t * y * z - s * x
        
        mat[2, 0] = t * x * z - s * y
        mat[2, 1] = t * y * z + s * x
        mat[2, 2] = t * z * z + c
        
        return mat
    
    def apply_rotation(self, rotation_matrix):
        """
        应用旋转到当前状态
        
        Args:
            rotation_matrix: 4x4 旋转矩阵
        """
        self.rotation = rotation_matrix @ self.rotation
    
    def reset(self):
        """重置旋转"""
        self.rotation = np.identity(4, dtype=np.float32)
    
    def get_matrix(self):
        """获取当前旋转矩阵"""
        return self.rotation.copy()
