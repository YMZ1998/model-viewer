"""
OpenGL 渲染器
管理 Mesh 和 Point Cloud 的渲染
"""
from OpenGL.GL import *
import numpy as np
# import os  # 不再需要

from gl.camera import Camera
from math_utils.trackball import Trackball


class Renderer:
    """OpenGL 渲染器"""
    
    def __init__(self, width=800, height=600):
        """
        初始化渲染器
        
        Args:
            width: 窗口宽度
            height: 窗口高度
        """
        self.camera = Camera(width, height)
        self.trackball = Trackball()
        
        # 渲染状态
        self.data_type = None  # 'mesh' or 'point_cloud'
        self.render_mode = 'surface'  # 'surface', 'wireframe', 'surface+wireframe'
        self.color_mode = 'uniform'  # 'uniform', 'vertex'
        self.point_size = 2.0
        self.line_width = 2.0  # 线框模式线条宽度
        
        # 数据
        self.vertices = None
        self.indices = None
        self.normals = None
        self.colors = None
        self.edges = None
        
        self.initialized = False
    
    def initialize(self):
        """初始化 OpenGL 设置"""
        # 启用深度测试
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)
        
        # 启用面剔除
        # glEnable(GL_CULL_FACE)
        # glCullFace(GL_BACK)
        
        # 设置背景色
        glClearColor(0.2, 0.2, 0.2, 1.0)
        
        # 启用光照
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        
        # 设置光源
        glLightfv(GL_LIGHT0, GL_POSITION, [2.0, 2.0, 2.0, 1.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [1.0, 1.0, 1.0, 1.0])
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.2, 0.2, 0.2, 1.0])
        
        # 启用颜色材质
        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        
        self.initialized = True
    
    def load_mesh_data(self, vertices, indices, normals=None, colors=None):
        """
        加载 Mesh 数据
        
        Args:
            vertices: 顶点坐标 (N, 3)
            indices: 三角面索引 (M, 3)
            normals: 顶点法向量 (N, 3)
            colors: 顶点颜色 (N, 3)
        """
        try:
            print(f"load_mesh_data调用: 顶点数={len(vertices)}, 面数={len(indices)}")
            
            self.data_type = 'mesh'
            self.vertices = vertices.astype(np.float32)
            self.indices = indices.flatten().astype(np.uint32) if len(indices) > 0 else np.array([], dtype=np.uint32)
            
            # 处理法向量
            if normals is not None and len(normals) > 0:
                self.normals = normals.astype(np.float32)
            else:
                if len(indices) > 0:
                    self.normals = self._compute_normals(vertices, indices)
                else:
                    # 如果没有面数据，创建默认法向量
                    self.normals = np.zeros_like(vertices, dtype=np.float32)
            
            # 处理颜色 - 如果没有颜色数据，则生成随机颜色
            if colors is not None and len(colors) > 0:
                self.colors = colors.astype(np.float32)
            else:
                # 生成美观的随机颜色
                print("未提供颜色数据，生成随机颜色")
                # 使用局部随机数生成器，避免污染全局随机状态
                rng = np.random.default_rng(42)
                self.colors = rng.random((len(vertices), 3), dtype=np.float32)
            
            # 准备边数据（用于线框模式）
            if len(indices) > 0:
                self._prepare_mesh_edges(indices)
            else:
                self.edges = None
            print(f"边数据生成完成: 边数={len(self.edges) if self.edges is not None else 0}")
        except Exception as e:
            print(f"加载mesh数据时出错: {e}")
            import traceback
            traceback.print_exc()
            # 重置状态
            self.data_type = None
            self.vertices = None
            self.indices = None
            self.normals = None
            self.colors = None
            self.edges = None
    
    def load_point_cloud_data(self, points, colors=None):
        """
        加载 Point Cloud 数据
        
        Args:
            points: 点坐标 (N, 3)
            colors: 点颜色 (N, 3)
        """
        self.data_type = 'point_cloud'
        self.vertices = points.astype(np.float32)
        
        # 处理颜色 - 如果没有颜色数据，则生成随机颜色
        if colors is not None and len(colors) > 0:
            self.colors = colors.astype(np.float32)
        else:
            # 生成美观的随机颜色
            print("未提供点云颜色数据，生成随机颜色")
            # 使用局部随机数生成器，避免污染全局随机状态
            rng = np.random.default_rng(42)
            self.colors = rng.random((len(points), 3), dtype=np.float32)
    
    def _compute_normals(self, vertices, indices):
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
        
        return normals.astype(np.float32)
    
    def _prepare_mesh_edges(self, indices):
        """准备 Mesh 边数据"""
        try:
            edges = set()
            # 确保indices是二维数组
            if len(indices.shape) == 1:
                # 如果是一维数组，重塑为(N, 3)
                indices = indices.reshape(-1, 3)
            
            for tri in indices:
                # 确保tri是一个数组
                if not isinstance(tri, (list, np.ndarray)):
                    continue
                # 如果tri长度不足3，跳过
                if len(tri) < 3:
                    continue
                    
                edges.add(tuple(sorted([int(tri[0]), int(tri[1])])))
                edges.add(tuple(sorted([int(tri[1]), int(tri[2])])))
                edges.add(tuple(sorted([int(tri[2]), int(tri[0])])))
            
            self.edges = np.array(list(edges), dtype=np.uint32).flatten() if edges else None
        except Exception as e:
            print(f"准备边数据时出错: {e}")
            self.edges = None
    
    def render(self):
        """渲染场景"""
        if not self.initialized:
            self.initialize()
        
        # 清除缓冲区
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        if self.data_type is None:
            print(f"无法渲染: data_type={self.data_type}")
            return

        # 设置相机矩阵
        view = self.camera.get_view_matrix()
        projection = self.camera.get_projection_matrix()
        model = self.camera.get_model_matrix() @ self.trackball.get_matrix()
        
        # 设置OpenGL变换矩阵
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        # 应用视图和模型变换
        modelview = view @ model
        glMultMatrixf(modelview.T.flatten())
        
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glMultMatrixf(projection.T.flatten())
        
        print(f"渲染 {self.data_type}, 顶点数: {len(self.vertices) if self.vertices is not None else 0}")
        
        if self.data_type == 'mesh':
            self._render_mesh()
        elif self.data_type == 'point_cloud':
            self._render_point_cloud()
    
    def _render_mesh(self):
        """渲染 Mesh（使用固定管线）"""
        try:
            print("开始渲染mesh...")
            
            if self.render_mode == 'surface':
                # 渲染表面
                print("渲染表面模式")
                glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
                # 启用光照
                glEnable(GL_LIGHTING)
                self._draw_mesh_elements()
            elif self.render_mode == 'wireframe':
                # 渲染线框
                print("渲染线框模式")
                glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
                glLineWidth(self.line_width)
                # 禁用光照，使用顶点颜色
                glDisable(GL_LIGHTING)
                self._draw_wireframe_elements()
            elif self.render_mode == 'surface+wireframe':
                # 先渲染表面
                print("渲染表面+线框模式")
                glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
                # 启用光照
                glEnable(GL_LIGHTING)
                self._draw_mesh_elements()
                
                # 再渲染线框
                # 保存当前状态
                glPushAttrib(GL_ALL_ATTRIB_BITS)
                
                # 禁用光照，使用纯色
                glDisable(GL_LIGHTING)
                glColor3f(0.0, 0.0, 0.0)  # 黑色线框
                
                glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
                glLineWidth(self.line_width)
                self._draw_wireframe_elements()
                
                # 恢复状态
                glPopAttrib()
            
            print("mesh渲染完成")
        except Exception as e:
            print(f"渲染 Mesh 时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def _draw_mesh_elements(self):
        """绘制Mesh元素（使用立即模式）"""
        glBegin(GL_TRIANGLES)
        for i in range(0, len(self.indices), 3):
            # 获取三个顶点索引
            i0, i1, i2 = self.indices[i], self.indices[i+1], self.indices[i+2]
            
            # 绘制第一个顶点
            if self.normals is not None:
                glNormal3fv(self.normals[i0])
            if self.colors is not None and self.color_mode == 'vertex':
                glColor3fv(self.colors[i0])
            glVertex3fv(self.vertices[i0])
            
            # 绘制第二个顶点
            if self.normals is not None:
                glNormal3fv(self.normals[i1])
            if self.colors is not None and self.color_mode == 'vertex':
                glColor3fv(self.colors[i1])
            glVertex3fv(self.vertices[i1])
            
            # 绘制第三个顶点
            if self.normals is not None:
                glNormal3fv(self.normals[i2])
            if self.colors is not None and self.color_mode == 'vertex':
                glColor3fv(self.colors[i2])
            glVertex3fv(self.vertices[i2])
        glEnd()
    
    def _draw_wireframe_elements(self):
        """绘制线框元素（使用立即模式）"""
        if self.edges is not None:
            # 使用边数据绘制线框
            glBegin(GL_LINES)
            for i in range(0, len(self.edges), 2):
                i0, i1 = self.edges[i], self.edges[i+1]
                
                # 绘制第一个顶点
                if self.colors is not None and self.color_mode == 'vertex':
                    glColor3fv(self.colors[i0])
                glVertex3fv(self.vertices[i0])
                
                # 绘制第二个顶点
                if self.colors is not None and self.color_mode == 'vertex':
                    glColor3fv(self.colors[i1])
                glVertex3fv(self.vertices[i1])
            glEnd()
        else:
            # 如果没有边数据，则使用三角面的边绘制线框
            glBegin(GL_LINES)
            for i in range(0, len(self.indices), 3):
                # 获取三个顶点索引
                i0, i1, i2 = self.indices[i], self.indices[i+1], self.indices[i+2]
                
                # 绘制三条边
                # 边1: i0 - i1
                if self.colors is not None and self.color_mode == 'vertex':
                    glColor3fv(self.colors[i0])
                glVertex3fv(self.vertices[i0])
                if self.colors is not None and self.color_mode == 'vertex':
                    glColor3fv(self.colors[i1])
                glVertex3fv(self.vertices[i1])
                
                # 边2: i1 - i2
                if self.colors is not None and self.color_mode == 'vertex':
                    glColor3fv(self.colors[i1])
                glVertex3fv(self.vertices[i1])
                if self.colors is not None and self.color_mode == 'vertex':
                    glColor3fv(self.colors[i2])
                glVertex3fv(self.vertices[i2])
                
                # 边3: i2 - i0
                if self.colors is not None and self.color_mode == 'vertex':
                    glColor3fv(self.colors[i2])
                glVertex3fv(self.vertices[i2])
                if self.colors is not None and self.color_mode == 'vertex':
                    glColor3fv(self.colors[i0])
                glVertex3fv(self.vertices[i0])
            glEnd()
    
    def _render_point_cloud(self):
        """渲染 Point Cloud（使用固定管线）"""
        try:
            # 设置点大小
            glPointSize(self.point_size)
            
            # 渲染点
            glBegin(GL_POINTS)
            for i in range(len(self.vertices)):
                if self.colors is not None:
                    glColor3fv(self.colors[i])
                glVertex3fv(self.vertices[i])
            glEnd()
        except Exception as e:
            print(f"渲染 Point Cloud 时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def resize(self, width, height):
        """窗口大小改变"""
        self.camera.set_aspect_ratio(width, height)
        glViewport(0, 0, width, height)
    
    def rotate_view(self, start_x, start_y, end_x, end_y, width, height):
        """旋转视角"""
        rotation = self.trackball.rotate(start_x, start_y, end_x, end_y, width, height)
        self.trackball.apply_rotation(rotation)
    
    def pan_view(self, dx, dy):
        """平移视角"""
        self.camera.pan(dx, dy)
    
    def zoom_view(self, factor):
        """缩放视角"""
        self.camera.zoom(factor)
    
    def reset_view(self):
        """重置视角"""
        self.camera.reset()
        self.trackball.reset()
        
        # 如果有模型数据，根据模型大小调整相机位置
        if self.vertices is not None and len(self.vertices) > 0:
            # 计算模型的边界框
            min_pos = np.min(self.vertices, axis=0)
            max_pos = np.max(self.vertices, axis=0)
            center = (min_pos + max_pos) / 2.0
            size = np.max(max_pos - min_pos)
            
            # 设置相机位置，使其能够看到整个模型
            # 计算合适的距离，考虑视角角度以确保模型完整显示
            fov_rad = np.radians(self.camera.fov)
            distance = (size / 2) / np.tan(fov_rad / 2)
            distance *= 1.5  # 给一些边距
            
            # 将相机放置在模型中心的前方，正对模型中心
            self.camera.position = np.array([center[0], center[1], center[2] + distance], dtype=np.float32)
            self.camera.target = center.astype(np.float32)
            self.camera.scale = 1.0
            
            print(f"重置视角: 相机位置={self.camera.position}, 目标={self.camera.target}, 模型中心={center}, 模型大小={size}")
    
    def set_render_mode(self, mode):
        """设置渲染模式"""
        if mode in ['surface', 'wireframe', 'surface+wireframe']:
            self.render_mode = mode
    
    def set_color_mode(self, mode):
        """设置颜色模式"""
        if mode in ['uniform', 'vertex']:
            self.color_mode = mode
    
    def set_point_size(self, size):
        """设置点大小"""
        self.point_size = max(0.5, min(10.0, size))