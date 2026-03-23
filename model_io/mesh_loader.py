"""
Mesh 文件加载器
支持 .obj .stl .ply 格式
"""
import numpy as np
import struct
import os
try:
    import plyfile
except ImportError:  # 可选依赖
    plyfile = None


class MeshLoader:
    """Mesh 加载器"""
    
    @staticmethod
    def load(file_path):
        """
        加载 Mesh 文件
        
        Args:
            file_path: 文件路径
        
        Returns:
            dict: {
                'vertices': numpy array (N, 3),
                'indices': numpy array (M, 3),
                'normals': numpy array (N, 3) or None,
                'colors': numpy array (N, 3) or None
            }
        """
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.obj':
            return MeshLoader._load_obj(file_path)
        elif ext == '.stl':
            return MeshLoader._load_stl(file_path)
        elif ext == '.ply':
            return MeshLoader._load_ply_mesh(file_path)
        else:
            raise ValueError(f"Unsupported mesh format: {ext}")
    
    @staticmethod
    def _load_ply_mesh(file_path):
        """使用plyfile库加载PLY Mesh文件"""
        if plyfile is None:
            return MeshLoader._load_ply_mesh_legacy(file_path)

        try:
            # 使用plyfile库读取PLY文件
            plydata = plyfile.PlyData.read(file_path)
            
            # 获取顶点数据
            vertex_data = plydata['vertex']
            num_vertices = vertex_data.count
            
            # 提取顶点坐标
            x = vertex_data.data['x'] if 'x' in vertex_data.data.dtype.names else np.zeros(num_vertices)
            y = vertex_data.data['y'] if 'y' in vertex_data.data.dtype.names else np.zeros(num_vertices)
            z = vertex_data.data['z'] if 'z' in vertex_data.data.dtype.names else np.zeros(num_vertices)
            vertices = np.column_stack((x, y, z)).astype(np.float32)
            
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
            
            # 提取面数据（如果存在）
            indices = np.array([], dtype=np.uint32)
            if 'face' in plydata:
                face_data = plydata['face']
                faces = []
                for face in face_data.data['vertex_indices']:
                    # 确保face是一个数组
                    if isinstance(face, np.ndarray):
                        face_array = face
                    else:
                        # 如果face不是数组，假设它是一个元组或列表
                        face_array = np.array(face)
                    
                    # 三角化多边形面
                    for i in range(1, len(face_array) - 1):
                        faces.append([face_array[0], face_array[i], face_array[i+1]])
                indices = np.array(faces, dtype=np.uint32)
            
            # 计算法向量
            normals = None
            if len(indices) > 0:
                normals = MeshLoader._compute_normals(vertices, indices)
            
            print(f"PLY文件加载完成: 顶点={len(vertices)}, 面={len(indices)}, 有颜色={colors is not None}")
            
            return {
                'vertices': vertices,
                'indices': indices,
                'normals': normals,
                'colors': colors
            }
        except Exception as e:
            print(f"使用plyfile库加载PLY文件失败: {e}")
            import traceback
            traceback.print_exc()
            # 回退到原来的实现
            return MeshLoader._load_ply_mesh_legacy(file_path)
    
    @staticmethod
    def _load_ply_mesh_legacy(file_path):
        """加载 PLY Mesh 文件（原始实现）"""
        vertices = []
        indices = []
        colors = []
        has_color = False
        
        with open(file_path, 'rb') as f:
            # 读取头部
            line = f.readline().decode('ascii').strip()
            if line != 'ply':
                raise ValueError("Not a PLY file")
            
            format_binary = False
            vertex_count = 0
            face_count = 0
            
            # 读取头部信息
            while True:
                line = f.readline().decode('ascii').strip()
                if line.startswith('format'):
                    if 'binary' in line:
                        format_binary = True
                elif line.startswith('element vertex'):
                    vertex_count = int(line.split()[-1])
                elif line.startswith('element face'):
                    face_count = int(line.split()[-1])
                elif line.startswith('property'):
                    prop_name = line.split()[-1].lower()
                    if prop_name in {'red', 'green', 'blue', 'r', 'g', 'b'}:
                        has_color = True
                elif line == 'end_header':
                    break
            
            print(f"PLY文件信息: 顶点数={vertex_count}, 面数={face_count}, 格式={'binary' if format_binary else 'ascii'}, 有颜色={has_color}")
            
            # 读取顶点
            for i in range(vertex_count):
                if format_binary:
                    v = struct.unpack('fff', f.read(12))
                    vertices.append(v)
                    if has_color:
                        try:
                            c = struct.unpack('BBB', f.read(3))
                            colors.append([c[0]/255.0, c[1]/255.0, c[2]/255.0])
                        except:
                            # 如果读取颜色失败，使用默认颜色
                            colors.append([0.7, 0.7, 0.7])
                else:
                    line = f.readline().decode('ascii').strip().split()
                    vertices.append([float(line[0]), float(line[1]), float(line[2])])
                    if has_color and len(line) >= 6:
                        colors.append([float(line[3])/255.0, float(line[4])/255.0, float(line[5])/255.0])
            
            # 读取面
            for i in range(face_count):
                if format_binary:
                    try:
                        count = struct.unpack('B', f.read(1))[0]
                        face = struct.unpack(f'{count}I', f.read(4 * count))
                        if count >= 3:
                            for j in range(1, count - 1):
                                indices.append([face[0], face[j], face[j+1]])
                    except Exception as e:
                        print(f"读取面数据时出错: {e}")
                        # 跳过这个面
                        continue
                else:
                    try:
                        line = f.readline().decode('ascii').strip().split()
                        count = int(line[0])
                        face = [int(line[k+1]) for k in range(count)]
                        for j in range(1, count - 1):
                            indices.append([face[0], face[j], face[j+1]])
                    except Exception as e:
                        print(f"读取面数据时出错: {e}")
                        # 跳过这个面
                        continue
        
        if not vertices:
            raise ValueError("PLY文件中没有找到顶点数据")
        
        vertices = np.array(vertices, dtype=np.float32)
        indices = np.array(indices, dtype=np.uint32) if indices else np.array([], dtype=np.uint32)
        normals = MeshLoader._compute_normals(vertices, indices) if len(indices) > 0 else None
        
        result = {
            'vertices': vertices,
            'indices': indices,
            'normals': normals,
            'colors': np.array(colors, dtype=np.float32) if colors else None
        }
        
        print(f"PLY加载完成: 顶点={len(vertices)}, 面={len(indices)}, 有颜色={result['colors'] is not None}")
        return result
    
    @staticmethod
    def _load_obj(file_path):
        """加载 OBJ 文件"""
        vertices = []
        normals = []
        indices = []
        
        vertex_normals = []
        has_normals = False
        
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split()
                if not parts:
                    continue
                
                if parts[0] == 'v':
                    # 顶点坐标
                    vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
                
                elif parts[0] == 'vn':
                    # 顶点法向量
                    vertex_normals.append([float(parts[1]), float(parts[2]), float(parts[3])])
                    has_normals = True
                
                elif parts[0] == 'f':
                    # 面索引
                    face_indices = []
                    for i in range(1, len(parts)):
                        vertex_data = parts[i].split('/')
                        # OBJ 索引从1开始
                        face_indices.append(int(vertex_data[0]) - 1)
                    
                    # 三角化（如果是多边形）
                    for i in range(1, len(face_indices) - 1):
                        indices.append([face_indices[0], face_indices[i], face_indices[i+1]])
        
        vertices = np.array(vertices, dtype=np.float32)
        indices = np.array(indices, dtype=np.uint32)
        
        # 处理法向量
        if has_normals and len(vertex_normals) == len(vertices):
            normals = np.array(vertex_normals, dtype=np.float32)
        else:
            normals = MeshLoader._compute_normals(vertices, indices)
        
        return {
            'vertices': vertices,
            'indices': indices,
            'normals': normals,
            'colors': None
        }
    
    @staticmethod
    def _load_stl(file_path):
        """加载 STL 文件（支持二进制和ASCII）"""
        with open(file_path, 'rb') as f:
            header = f.read(80)
            # 检查是否为二进制格式
            if header.startswith(b'solid'):
                # 可能是ASCII格式
                f.seek(0)
                try:
                    return MeshLoader._load_stl_ascii(file_path)
                except:
                    pass
            
            # 二进制格式
            f.seek(80)
            num_triangles = struct.unpack('I', f.read(4))[0]
            
            vertices_list = []
            indices = []
            vertex_map = {}
            vertex_count = 0
            
            for i in range(num_triangles):
                # 读取法向量（暂时跳过）
                f.read(12)
                
                # 读取3个顶点
                tri_vertices = []
                for j in range(3):
                    v = struct.unpack('fff', f.read(12))
                    v_tuple = tuple(v)
                    
                    if v_tuple not in vertex_map:
                        vertex_map[v_tuple] = vertex_count
                        vertices_list.append(v)
                        vertex_count += 1
                    
                    tri_vertices.append(vertex_map[v_tuple])
                
                indices.append(tri_vertices)
                # 跳过属性字节
                f.read(2)
            
            vertices = np.array(vertices_list, dtype=np.float32)
            indices = np.array(indices, dtype=np.uint32)
            normals = MeshLoader._compute_normals(vertices, indices)
            
            return {
                'vertices': vertices,
                'indices': indices,
                'normals': normals,
                'colors': None
            }
    
    @staticmethod
    def _load_stl_ascii(file_path):
        """加载 ASCII STL 文件"""
        vertices_list = []
        indices = []
        vertex_map = {}
        vertex_count = 0
        
        with open(file_path, 'r') as f:
            current_vertices = []
            for line in f:
                line = line.strip()
                if line.startswith('vertex'):
                    parts = line.split()
                    v = (float(parts[1]), float(parts[2]), float(parts[3]))
                    
                    if v not in vertex_map:
                        vertex_map[v] = vertex_count
                        vertices_list.append(v)
                        vertex_count += 1
                    
                    current_vertices.append(vertex_map[v])
                    
                    if len(current_vertices) == 3:
                        indices.append(current_vertices)
                        current_vertices = []
        
        vertices = np.array(vertices_list, dtype=np.float32)
        indices = np.array(indices, dtype=np.uint32)
        normals = MeshLoader._compute_normals(vertices, indices)
        
        return {
            'vertices': vertices,
            'indices': indices,
            'normals': normals,
            'colors': None
        }
    
    @staticmethod
    def _compute_normals(vertices, indices):
        """计算顶点法向量"""
        normals = np.zeros_like(vertices)
        
        # 计算每个面的法向量并累加到顶点
        for tri in indices:
            v0, v1, v2 = vertices[tri]
            edge1 = v1 - v0
            edge2 = v2 - v0
            face_normal = np.cross(edge1, edge2)
            
            normals[tri[0]] += face_normal
            normals[tri[1]] += face_normal
            normals[tri[2]] += face_normal
        
        # 归一化
        norms = np.linalg.norm(normals, axis=1, keepdims=True)
        norms[norms == 0] = 1
        normals = normals / norms
        
        return normals
