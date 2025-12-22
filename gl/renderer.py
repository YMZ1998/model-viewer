"""
OpenGL 渲染器
管理 Mesh 和 Point Cloud 的渲染
"""
from OpenGL.GL import *
import numpy as np
import os

from gl.shader import Shader
from gl.buffers import VertexArray, VertexBuffer, IndexBuffer
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
        
        # 着色器程序（将在 initialize 中创建）
        self.mesh_shader = None
        self.point_shader = None
        
        # 渲染状态
        self.data_type = None  # 'mesh' or 'point_cloud'
        self.render_mode = 'surface'  # 'surface', 'wireframe', 'surface+wireframe'
        self.color_mode = 'uniform'  # 'uniform', 'vertex'
        self.point_size = 2.0
        
        # OpenGL 对象
        self.vao = None
        self.vbo = None
        self.ebo = None
        self.edge_ebo = None
        
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
        glEnable(GL_CULL_FACE)
        glCullFace(GL_BACK)
        
        # 设置背景色
        glClearColor(0.8, 0.8, 0.8, 1.0)
        
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
        self._cleanup_resources()
        
        self.data_type = 'mesh'
        self.vertices = vertices.astype(np.float32)
        self.indices = indices.flatten().astype(np.uint32)
        
        # 处理法向量
        if normals is not None:
            self.normals = normals.astype(np.float32)
        else:
            self.normals = self._compute_normals(vertices, indices)
        
        # 处理颜色
        if colors is not None:
            self.colors = colors.astype(np.float32)
        else:
            self.colors = np.full_like(vertices, 0.7, dtype=np.float32)
        
        # 准备边数据（用于线框模式）
        self._prepare_mesh_edges(indices)
        
        # 创建 OpenGL 缓冲区（如果已初始化）
        if self.initialized:
            self._create_mesh_buffers()
    
    def load_point_cloud_data(self, points, colors=None):
        """
        加载 Point Cloud 数据
        
        Args:
            points: 点坐标 (N, 3)
            colors: 点颜色 (N, 3)
        """
        self._cleanup_resources()
        
        self.data_type = 'point_cloud'
        self.vertices = points.astype(np.float32)
        
        # 处理颜色
        if colors is not None:
            self.colors = colors.astype(np.float32)
        else:
            # 默认灰色
            self.colors = np.full_like(points, 0.7, dtype=np.float32)
        
        # 创建 OpenGL 缓冲区（如果已初始化）
        if self.initialized:
            self._create_point_buffers()
    
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
        edges = set()
        for tri in indices:
            edges.add(tuple(sorted([tri[0], tri[1]])))
            edges.add(tuple(sorted([tri[1], tri[2]])))
            edges.add(tuple(sorted([tri[2], tri[0]])))
        
        self.edges = np.array(list(edges), dtype=np.uint32).flatten()
    
    def _create_mesh_buffers(self):
        """创建 Mesh 缓冲区"""
        # 确保着色器已创建
        if self.mesh_shader is None:
            shader_dir = os.path.join(os.path.dirname(__file__), '..', 'shaders')
            self.mesh_shader = Shader(
                os.path.join(shader_dir, 'mesh.vert'),
                os.path.join(shader_dir, 'mesh.frag')
            )
        
        self.vao = VertexArray()
        self.vao.bind()
        
        # 合并顶点属性数据 (position + normal + color)
        vertex_data = np.hstack([
            self.vertices,
            self.normals,
            self.colors
        ]).astype(np.float32)
        
        self.vbo = VertexBuffer(vertex_data)
        self.ebo = IndexBuffer(self.indices)
        
        # 添加顶点属性
        stride = 9 * 4  # 9 floats * 4 bytes
        self.vao.add_buffer(self.vbo, 0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))  # position
        self.vao.add_buffer(self.vbo, 1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(3 * 4))  # normal
        self.vao.add_buffer(self.vbo, 2, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(6 * 4))  # color
        
        # 边缓冲区（线框模式）
        if self.edges is not None:
            self.edge_ebo = IndexBuffer(self.edges)
        
        self.vao.unbind()
    
    def _create_point_buffers(self):
        """创建 Point Cloud 缓冲区"""
        # 确保着色器已创建
        if self.point_shader is None:
            shader_dir = os.path.join(os.path.dirname(__file__), '..', 'shaders')
            self.point_shader = Shader(
                os.path.join(shader_dir, 'point.vert'),
                os.path.join(shader_dir, 'point.frag')
            )
        
        self.vao = VertexArray()
        self.vao.bind()
        
        # 合并顶点属性数据 (position + color)
        vertex_data = np.hstack([
            self.vertices,
            self.colors
        ]).astype(np.float32)
        
        self.vbo = VertexBuffer(vertex_data)
        
        # 添加顶点属性
        stride = 6 * 4  # 6 floats * 4 bytes
        self.vao.add_buffer(self.vbo, 0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))  # position
        self.vao.add_buffer(self.vbo, 1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(3 * 4))  # color
        
        self.vao.unbind()
    
    def render(self):
        """渲染场景"""
        if not self.initialized:
            self.initialize()
        
        # 清除缓冲区
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        if self.data_type is None or self.vao is None or self.mesh_shader is None or self.point_shader is None:
            return
        
        # 设置相机矩阵
        view = self.camera.get_view_matrix()
        projection = self.camera.get_projection_matrix()
        model = self.camera.get_model_matrix() @ self.trackball.get_matrix()
        
        print(f"渲染 {self.data_type}, VAO: {self.vao is not None}, 顶点数: {len(self.vertices) if self.vertices is not None else 0}")
        
        if self.data_type == 'mesh':
            self._render_mesh(view, projection, model)
        elif self.data_type == 'point_cloud':
            self._render_point_cloud(view, projection, model)
    
    def _render_mesh(self, view, projection, model):
        """渲染 Mesh"""
        try:
            self.vao.bind()
            self.ebo.bind()
            
            # 激活着色器
            self.mesh_shader.use()
            
            # 设置变换矩阵
            self.mesh_shader.set_mat4("model", model)
            self.mesh_shader.set_mat4("view", view)
            self.mesh_shader.set_mat4("projection", projection)
            
            # 设置光照参数
            self.mesh_shader.set_vec3("lightPos", [2.0, 2.0, 2.0])
            self.mesh_shader.set_vec3("viewPos", self.camera.position)
            self.mesh_shader.set_vec3("lightColor", [1.0, 1.0, 1.0])
            self.mesh_shader.set_bool("useVertexColor", self.color_mode == 'vertex')
            
            if self.render_mode == 'surface':
                # 渲染表面
                glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
                glDrawElements(GL_TRIANGLES, self.ebo.count, GL_UNSIGNED_INT, None)
            elif self.render_mode == 'wireframe':
                # 渲染线框
                if self.edge_ebo:
                    self.edge_ebo.bind()
                    glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
                    glLineWidth(1.0)
                    glDrawElements(GL_LINES, self.edge_ebo.count, GL_UNSIGNED_INT, None)
                    self.ebo.bind()  # 恢复原来的 EBO
            elif self.render_mode == 'surface+wireframe':
                # 先渲染表面
                glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
                glDrawElements(GL_TRIANGLES, self.ebo.count, GL_UNSIGNED_INT, None)
                
                # 再渲染线框
                if self.edge_ebo:
                    self.edge_ebo.bind()
                    glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
                    glLineWidth(1.0)
                    glDrawElements(GL_LINES, self.edge_ebo.count, GL_UNSIGNED_INT, None)
                    self.ebo.bind()  # 恢复原来的 EBO
            
            self.vao.unbind()
        except Exception as e:
            print(f"渲染 Mesh 时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def _render_point_cloud(self, view, projection, model):
        """渲染 Point Cloud"""
        try:
            self.vao.bind()
            
            # 激活着色器
            self.point_shader.use()
            
            # 设置变换矩阵
            self.point_shader.set_mat4("model", model)
            self.point_shader.set_mat4("view", view)
            self.point_shader.set_mat4("projection", projection)
            
            # 设置点大小
            self.point_shader.set_float("pointSize", self.point_size)
            
            # 渲染点
            glEnable(GL_PROGRAM_POINT_SIZE)
            glDrawArrays(GL_POINTS, 0, len(self.vertices))
            glDisable(GL_PROGRAM_POINT_SIZE)
            
            self.vao.unbind()
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
            distance = size * 1.5  # 给一些边距
            self.camera.position = np.array([center[0], center[1], center[2] + distance], dtype=np.float32)
            self.camera.target = center.astype(np.float32)
            self.camera.scale = 1.0
    
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
    
    def _cleanup_resources(self):
        """清理资源"""
        if self.vao:
            self.vao.delete()
            self.vao = None
        if self.vbo:
            self.vbo.delete()
            self.vbo = None
        if self.ebo:
            self.ebo.delete()
            self.ebo = None
        if self.edge_ebo:
            self.edge_ebo.delete()
            self.edge_ebo = None
        
        self.vertices = None
        self.indices = None
        self.normals = None
        self.colors = None
        self.edges = None
