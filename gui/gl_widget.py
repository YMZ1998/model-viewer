"""
OpenGL 渲染窗口部件
继承自 QOpenGLWidget
"""
from PyQt5.QtWidgets import QOpenGLWidget
from PyQt5.QtCore import Qt, QPoint
from OpenGL.GL import *

from gl.renderer import Renderer


class GLWidget(QOpenGLWidget):
    """OpenGL 渲染窗口部件"""
    
    def __init__(self, parent=None):
        """
        初始化 GLWidget
        
        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        
        # 渲染器（将在 initializeGL 中初始化）
        self.renderer = None
        
        # 鼠标交互
        self.last_pos = QPoint()
        self.mouse_pressed = False
        self.current_button = None
        
        # 启用鼠标跟踪
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
    
    def initializeGL(self):
        """初始化 OpenGL"""
        # 在 OpenGL 上下文创建后再初始化渲染器
        from gl.renderer import Renderer
        self.renderer = Renderer()
        self.renderer.initialize()
    
    def resizeGL(self, width, height):
        """窗口大小改变"""
        self.renderer.resize(width, height)
    
    def paintGL(self):
        """绘制场景"""
        self.renderer.render()
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        self.last_pos = event.pos()
        self.mouse_pressed = True
        self.current_button = event.button()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        self.mouse_pressed = False
        self.current_button = None
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if not self.mouse_pressed:
            return
        
        dx = event.x() - self.last_pos.x()
        dy = event.y() - self.last_pos.y()
        
        width, height = self.width(), self.height()
        
        if self.current_button == Qt.LeftButton:
            # 左键：旋转
            self.renderer.rotate_view(
                self.last_pos.x(), self.last_pos.y(),
                event.x(), event.y(),
                width, height
            )
            self.update()
        
        elif self.current_button == Qt.RightButton:
            # 右键：平移
            sensitivity = 0.01 / self.renderer.camera.scale
            self.renderer.pan_view(dx * sensitivity, -dy * sensitivity)
            self.update()
        
        self.last_pos = event.pos()
    
    def wheelEvent(self, event):
        """鼠标滚轮事件"""
        # 缩放
        delta = event.angleDelta().y()
        zoom_factor = 1.1 if delta > 0 else 0.9
        self.renderer.zoom_view(zoom_factor)
        self.update()
    
    def keyPressEvent(self, event):
        """键盘按下事件"""
        if event.key() == Qt.Key_R:
            # 重置视角
            self.renderer.reset_view()
            self.update()
        elif event.key() == Qt.Key_W:
            # 切换线框模式
            if self.renderer.data_type == 'mesh':
                if self.renderer.render_mode == 'surface':
                    self.renderer.set_render_mode('wireframe')
                elif self.renderer.render_mode == 'wireframe':
                    self.renderer.set_render_mode('surface+wireframe')
                else:
                    self.renderer.set_render_mode('surface')
                self.update()
        elif event.key() == Qt.Key_Escape:
            # 关闭窗口
            self.window().close()
        else:
            super().keyPressEvent(event)
    
    def load_mesh_data(self, vertices, indices, normals=None, colors=None):
        """加载 Mesh 数据"""
        self.renderer.load_mesh_data(vertices, indices, normals, colors)
        self.update()
    
    def load_point_cloud_data(self, points, colors=None):
        """加载 Point Cloud 数据"""
        self.renderer.load_point_cloud_data(points, colors)
        self.update()
    
    def set_render_mode(self, mode):
        """设置渲染模式"""
        self.renderer.set_render_mode(mode)
        self.update()
    
    def set_color_mode(self, mode):
        """设置颜色模式"""
        self.renderer.set_color_mode(mode)
        self.update()
    
    def set_point_size(self, size):
        """设置点大小"""
        self.renderer.set_point_size(size)
        self.update()
