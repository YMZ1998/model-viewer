"""
主窗口
包含 OpenGL 渲染窗口和控制面板
"""
from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QMenuBar, QAction, QStatusBar
from PyQt5.QtCore import Qt
import sys
import os

from gui.gl_widget import GLWidget
from gui.control_panel import ControlPanel


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        """初始化主窗口"""
        super().__init__()
        
        self.setWindowTitle("PyQtGLMeshViewer - 3D Mesh & Point Cloud Viewer")
        self.setGeometry(100, 100, 1280, 800)
        
        self._create_menu_bar()
        self._create_status_bar()
        self._create_central_widget()
    
    def _create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        
        open_action = QAction('打开文件...', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self._on_open_file)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = QAction('关于', self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)
    
    def _create_status_bar(self):
        """创建状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
    
    def _create_central_widget(self):
        """创建中央部件"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QHBoxLayout()
        central_widget.setLayout(layout)
        
        # OpenGL 渲染窗口
        self.gl_widget = GLWidget()
        layout.addWidget(self.gl_widget, 3)
        
        # 控制面板
        self.control_panel = ControlPanel(self.gl_widget)
        layout.addWidget(self.control_panel, 1)
    
    def _on_open_file(self):
        """打开文件菜单项"""
        self.control_panel._on_load_file()
    
    def _on_about(self):
        """关于菜单项"""
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.about(self, "关于 PyQtGLMeshViewer",
                         "PyQtGLMeshViewer v1.0\n\n"
                         "基于 PyQt5 和 OpenGL Core Profile 3.3 的 3D 模型查看器\n"
                         "支持 Mesh (.obj, .stl, .ply) 和 Point Cloud (.ply, .xyz) 格式\n\n"
                         "快捷键:\n"
                         "  R - 重置视角\n"
                         "  W - 切换线框模式\n"
                         "  Esc - 退出\n"
                         "  鼠标左键 - 旋转\n"
                         "  鼠标右键 - 平移\n"
                         "  鼠标滚轮 - 缩放")
