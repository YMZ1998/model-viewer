"""
变换矩阵工具
提供视图变换、投影变换等矩阵计算
"""
import numpy as np


def perspective(fovy, aspect, near, far):
    """
    创建透视投影矩阵
    
    Args:
        fovy: 垂直视场角（度）
        aspect: 宽高比
        near: 近裁剪面
        far: 远裁剪面
    
    Returns:
        4x4 投影矩阵
    """
    f = 1.0 / np.tan(np.radians(fovy) / 2.0)
    
    mat = np.zeros((4, 4), dtype=np.float32)
    mat[0, 0] = f / aspect
    mat[1, 1] = f
    mat[2, 2] = (far + near) / (near - far)
    mat[2, 3] = (2.0 * far * near) / (near - far)
    mat[3, 2] = -1.0
    
    return mat


def orthographic(left, right, bottom, top, near, far):
    """
    创建正交投影矩阵

    Args:
        left, right: 左右边界
        bottom, top: 上下边界
        near, far: 近平面和远平面

    Returns:
        4x4 投影矩阵
    """
    width = right - left
    height = top - bottom
    depth = far - near

    mat = np.identity(4, dtype=np.float32)
    mat[0, 0] = 2.0 / width if abs(width) > 1e-8 else 1.0
    mat[1, 1] = 2.0 / height if abs(height) > 1e-8 else 1.0
    mat[2, 2] = -2.0 / depth if abs(depth) > 1e-8 else -1.0
    mat[0, 3] = -(right + left) / width if abs(width) > 1e-8 else 0.0
    mat[1, 3] = -(top + bottom) / height if abs(height) > 1e-8 else 0.0
    mat[2, 3] = -(far + near) / depth if abs(depth) > 1e-8 else 0.0
    return mat


def look_at(eye, center, up):
    """
    创建视图矩阵（LookAt）
    
    Args:
        eye: 相机位置
        center: 目标位置
        up: 上向量
    
    Returns:
        4x4 视图矩阵
    """
    eye = np.array(eye, dtype=np.float32)
    center = np.array(center, dtype=np.float32)
    up = np.array(up, dtype=np.float32)
    
    # 计算相机坐标系
    f = center - eye
    f = f / np.linalg.norm(f)
    
    s = np.cross(f, up)
    s = s / np.linalg.norm(s)
    
    u = np.cross(s, f)
    
    # 构建矩阵
    mat = np.identity(4, dtype=np.float32)
    mat[0, :3] = s
    mat[1, :3] = u
    mat[2, :3] = -f
    
    # 平移部分
    mat[0, 3] = -np.dot(s, eye)
    mat[1, 3] = -np.dot(u, eye)
    mat[2, 3] = np.dot(f, eye)
    
    return mat


def rotation_matrix(angle, axis):
    """
    创建旋转矩阵（Rodrigues公式）
    
    Args:
        angle: 旋转角度（弧度）
        axis: 旋转轴（归一化向量）
    
    Returns:
        4x4 旋转矩阵
    """
    axis = np.array(axis, dtype=np.float32)
    axis = axis / np.linalg.norm(axis)
    
    x, y, z = axis
    c = np.cos(angle)
    s = np.sin(angle)
    t = 1 - c
    
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


def translation_matrix(tx, ty, tz):
    """
    创建平移矩阵
    
    Args:
        tx, ty, tz: 平移量
    
    Returns:
        4x4 平移矩阵
    """
    mat = np.identity(4, dtype=np.float32)
    mat[0, 3] = tx
    mat[1, 3] = ty
    mat[2, 3] = tz
    return mat


def scale_matrix(sx, sy, sz):
    """
    创建缩放矩阵
    
    Args:
        sx, sy, sz: 缩放因子
    
    Returns:
        4x4 缩放矩阵
    """
    mat = np.identity(4, dtype=np.float32)
    mat[0, 0] = sx
    mat[1, 1] = sy
    mat[2, 2] = sz
    return mat


def normalize(v):
    """归一化向量"""
    norm = np.linalg.norm(v)
    if norm == 0:
        return v
    return v / norm
