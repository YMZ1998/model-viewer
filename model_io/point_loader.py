"""
Point Cloud 文件加载器
支持 .ply .xyz 格式
"""
import numpy as np
import struct
import os
try:
    import plyfile
except ImportError:  # 可选依赖
    plyfile = None


class PointCloudLoader:
    """Point Cloud 加载器"""
    
    @staticmethod
    def load(file_path):
        """
        加载 Point Cloud 文件
        
        Args:
            file_path: 文件路径
        
        Returns:
            dict: {
                'points': numpy array (N, 3),
                'colors': numpy array (N, 3) or None
            }
        """
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.ply':
            return PointCloudLoader._load_ply(file_path)
        elif ext == '.xyz':
            return PointCloudLoader._load_xyz(file_path)
        else:
            raise ValueError(f"Unsupported point cloud format: {ext}")
    
    @staticmethod
    def _load_ply(file_path):
        """使用plyfile库加载PLY点云文件"""
        if plyfile is None:
            return PointCloudLoader._load_ply_legacy(file_path)

        try:
            # 使用plyfile库读取PLY文件
            plydata = plyfile.PlyData.read(file_path)
            
            # 获取顶点数据
            vertex_data = plydata['vertex']
            num_points = vertex_data.count
            
            # 提取点坐标
            x = vertex_data.data['x'] if 'x' in vertex_data.data.dtype.names else np.zeros(num_points)
            y = vertex_data.data['y'] if 'y' in vertex_data.data.dtype.names else np.zeros(num_points)
            z = vertex_data.data['z'] if 'z' in vertex_data.data.dtype.names else np.zeros(num_points)
            points = np.column_stack((x, y, z)).astype(np.float32)
            
            # 提取颜色数据（如果存在）
            colors = None
            if 'red' in vertex_data.data.dtype.names and 'green' in vertex_data.data.dtype.names and 'blue' in vertex_data.data.dtype.names:
                r = vertex_data.data['red']
                g = vertex_data.data['green']
                b = vertex_data.data['blue']
                # 检查颜色值范围，如果是0-255则需要归一化
                if r.max() > 1.0 or g.max() > 1.0 or b.max() > 1.0:
                    colors = np.column_stack((r/255.0, g/255.0, b/255.0)).astype(np.float32)
                else:
                    colors = np.column_stack((r, g, b)).astype(np.float32)
            
            # 如果没有颜色，使用高度映射
            if colors is None:
                colors = PointCloudLoader._height_based_colors(points)
            
            print(f"PLY点云文件加载完成: 点数={len(points)}, 有颜色={colors is not None}")
            
            return {
                'points': points,
                'colors': colors
            }
        except Exception as e:
            print(f"使用plyfile库加载PLY文件失败: {e}")
            # 回退到原来的实现
            return PointCloudLoader._load_ply_legacy(file_path)
    
    @staticmethod
    def _load_ply_legacy(file_path):
        """加载 PLY 点云文件（原始实现）"""
        points = []
        colors = []
        has_color = False
        
        with open(file_path, 'rb') as f:
            # 读取头部
            line = f.readline().decode('ascii').strip()
            if line != 'ply':
                raise ValueError("Not a PLY file")
            
            format_binary = False
            point_count = 0
            properties = []
            
            while True:
                try:
                    line = f.readline().decode('ascii').strip()
                    if line.startswith('format'):
                        if 'binary' in line:
                            format_binary = True
                    elif line.startswith('element vertex'):
                        point_count = int(line.split()[-1])
                    elif line.startswith('property'):
                        properties.append(line.split()[-1])
                        if 'red' in line or 'r' == line.split()[-1]:
                            has_color = True
                    elif line == 'end_header':
                        break
                except Exception as e:
                    print(f"读取PLY头部时出错: {e}")
                    break
            
            print(f"PLY点云文件信息: 点数={point_count}, 格式={'binary' if format_binary else 'ascii'}, 有颜色={has_color}")
            
            # 读取点数据
            for i in range(point_count):
                try:
                    if format_binary:
                        # 读取 x, y, z
                        p = struct.unpack('fff', f.read(12))
                        points.append(p)
                        
                        if has_color:
                            # 读取 r, g, b
                            try:
                                c = struct.unpack('BBB', f.read(3))
                                colors.append([c[0]/255.0, c[1]/255.0, c[2]/255.0])
                            except:
                                # 如果读取颜色失败，使用默认颜色
                                colors.append([0.7, 0.7, 0.7])
                    else:
                        line = f.readline().decode('ascii').strip().split()
                        if len(line) >= 3:
                            points.append([float(line[0]), float(line[1]), float(line[2])])
                            
                            if has_color and len(line) >= 6:
                                colors.append([float(line[3])/255.0, float(line[4])/255.0, float(line[5])/255.0])
                except Exception as e:
                    print(f"读取点{i}时出错: {e}")
                    # 跳过这个点
                    continue
        
        if not points:
            raise ValueError("PLY文件中没有找到点数据")
        
        points = np.array(points, dtype=np.float32)
        colors = np.array(colors, dtype=np.float32) if colors else None
        
        # 如果没有颜色，使用高度映射
        if colors is None:
            colors = PointCloudLoader._height_based_colors(points)
        
        print(f"PLY点云加载完成: 点数={len(points)}, 有颜色={colors is not None}")
        return {
            'points': points,
            'colors': colors
        }
    
    @staticmethod
    def _load_xyz(file_path):
        """加载 XYZ 点云文件"""
        points = []
        colors = []
        has_color = False
        
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split()
                if len(parts) >= 3:
                    points.append([float(parts[0]), float(parts[1]), float(parts[2])])
                    
                    if len(parts) >= 6:
                        # 包含 RGB 信息
                        has_color = True
                        # 假设 RGB 是 0-255 范围
                        colors.append([float(parts[3])/255.0, float(parts[4])/255.0, float(parts[5])/255.0])
        
        points = np.array(points, dtype=np.float32)
        
        if has_color and colors:
            colors = np.array(colors, dtype=np.float32)
        else:
            colors = PointCloudLoader._height_based_colors(points)
        
        return {
            'points': points,
            'colors': colors
        }
    
    @staticmethod
    def _height_based_colors(points):
        """基于高度生成颜色映射"""
        if len(points) == 0:
            return None
        
        # 使用 Z 坐标
        z_values = points[:, 2]
        z_min, z_max = z_values.min(), z_values.max()
        
        if z_max - z_min > 1e-6:
            normalized = (z_values - z_min) / (z_max - z_min)
        else:
            normalized = np.ones_like(z_values) * 0.5
        
        # 热力图配色
        colors = np.zeros((len(points), 3), dtype=np.float32)
        
        for i, t in enumerate(normalized):
            if t < 0.25:
                # 蓝到青
                ratio = t / 0.25
                colors[i] = [0, ratio, 1]
            elif t < 0.5:
                # 青到绿
                ratio = (t - 0.25) / 0.25
                colors[i] = [0, 1, 1 - ratio]
            elif t < 0.75:
                # 绿到黄
                ratio = (t - 0.5) / 0.25
                colors[i] = [ratio, 1, 0]
            else:
                # 黄到红
                ratio = (t - 0.75) / 0.25
                colors[i] = [1, 1 - ratio, 0]
        
        return colors