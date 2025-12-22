"""
控制面板
包含文件操作和渲染设置控件
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QComboBox, QSlider, QTextEdit, QGroupBox,
                             QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt
import os

from model_io.mesh_loader import MeshLoader
from model_io.point_loader import PointCloudLoader


class ControlPanel(QWidget):
    """控制面板"""
    
    def __init__(self, gl_widget, parent=None):
        """
        初始化控制面板
        
        Args:
            gl_widget: GLWidget 实例
            parent: 父窗口
        """
        super().__init__(parent)
        
        self.gl_widget = gl_widget
        self.current_file_path = None
        self.data_type = None  # 'mesh' or 'point_cloud'
        
        self._create_ui()
    
    def _create_ui(self):
        """创建用户界面"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # === 文件操作 ===
        file_group = QGroupBox("文件")
        file_layout = QVBoxLayout()
        
        self.load_button = QPushButton("打开文件...")
        self.load_button.clicked.connect(self._on_load_file)
        file_layout.addWidget(self.load_button)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # === Mesh 设置 ===
        self.mesh_group = QGroupBox("Mesh 设置")
        mesh_layout = QVBoxLayout()
        
        # 渲染模式
        mesh_render_label = QLabel("渲染模式:")
        self.mesh_render_combo = QComboBox()
        self.mesh_render_combo.addItems(["Surface", "Wireframe", "Surface+Wireframe"])
        self.mesh_render_combo.currentIndexChanged.connect(self._on_mesh_render_mode_changed)
        mesh_layout.addWidget(mesh_render_label)
        mesh_layout.addWidget(self.mesh_render_combo)
        
        # 颜色模式
        mesh_color_label = QLabel("颜色模式:")
        self.mesh_color_combo = QComboBox()
        self.mesh_color_combo.addItems(["Uniform", "Vertex Color"])
        self.mesh_color_combo.currentIndexChanged.connect(self._on_mesh_color_mode_changed)
        mesh_layout.addWidget(mesh_color_label)
        mesh_layout.addWidget(self.mesh_color_combo)
        
        self.mesh_group.setLayout(mesh_layout)
        self.mesh_group.setVisible(False)
        layout.addWidget(self.mesh_group)
        
        # === Point Cloud 设置 ===
        self.pc_group = QGroupBox("Point Cloud 设置")
        pc_layout = QVBoxLayout()
        
        # 颜色模式
        pc_color_label = QLabel("颜色模式:")
        self.pc_color_combo = QComboBox()
        self.pc_color_combo.addItems(["RGB", "Height-based"])
        self.pc_color_combo.currentIndexChanged.connect(self._on_pc_color_mode_changed)
        pc_layout.addWidget(pc_color_label)
        pc_layout.addWidget(self.pc_color_combo)
        
        # 点大小
        point_size_label = QLabel(f"点大小: {2.0:.1f}")
        self.point_size_label = point_size_label
        self.point_size_slider = QSlider(Qt.Horizontal)
        self.point_size_slider.setMinimum(5)
        self.point_size_slider.setMaximum(100)
        self.point_size_slider.setValue(20)  # 2.0 * 10
        self.point_size_slider.valueChanged.connect(self._on_point_size_changed)
        pc_layout.addWidget(point_size_label)
        pc_layout.addWidget(self.point_size_slider)
        
        self.pc_group.setLayout(pc_layout)
        self.pc_group.setVisible(False)
        layout.addWidget(self.pc_group)
        
        # === 模型信息 ===
        info_group = QGroupBox("模型信息")
        info_layout = QVBoxLayout()
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(150)
        self.info_text.setText("未加载模型")
        info_layout.addWidget(self.info_text)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # === 快捷键提示 ===
        help_group = QGroupBox("快捷键")
        help_layout = QVBoxLayout()
        
        help_text = QLabel(
            "R: 重置视角\n"
            "W: 切换线框\n"
            "Esc: 退出\n\n"
            "鼠标左键: 旋转\n"
            "鼠标右键: 平移\n"
            "鼠标滚轮: 缩放"
        )
        help_layout.addWidget(help_text)
        
        help_group.setLayout(help_layout)
        layout.addWidget(help_group)
        
        # 添加弹性空间
        layout.addStretch()
    
    def _on_load_file(self):
        """加载文件按钮点击"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择模型文件",
            "",
            "3D Models (*.obj *.stl *.ply *.xyz);;Mesh Files (*.obj *.stl *.ply);;Point Cloud Files (*.ply *.xyz);;All Files (*)"
        )
        
        if file_path:
            self.load_file(file_path)
    
    def load_file(self, file_path):
        """
        加载文件
        
        Args:
            file_path: 文件路径
        """
        try:
            ext = os.path.splitext(file_path)[1].lower()
            
            # 判断文件类型
            if ext in ['.obj', '.stl', '.ply']:
                # 尝试作为 Mesh 加载
                try:
                    data = MeshLoader.load(file_path)
                    self._load_mesh_data(data, file_path)
                    return
                except Exception as e:
                    if ext == '.ply':
                        # 如果是 PLY 文件，尝试作为点云加载
                        try:
                            data = PointCloudLoader.load(file_path)
                            self._load_point_cloud_data(data, file_path)
                            return
                        except:
                            pass
                    raise e
            
            elif ext in ['.xyz']:
                data = PointCloudLoader.load(file_path)
                self._load_point_cloud_data(data, file_path)
                return
            
            else:
                raise ValueError(f"不支持的文件格式: {ext}")
        
        except Exception as e:
            # 显示错误对话框
            QMessageBox.critical(self, "加载失败", f"无法加载文件:\n{str(e)}")
            return
    
    def _load_mesh_data(self, data, file_path):
        """加载 Mesh 数据"""
        print(f"加载 Mesh 数据: {len(data['vertices'])} 顶点, {len(data['indices'])} 面")
        self.gl_widget.load_mesh_data(
            data['vertices'],
            data['indices'],
            data['normals'],
            data['colors']
        )
        
        # 重置视角以适应模型
        self.gl_widget.renderer.reset_view()
        
        self.current_file_path = file_path
        self.data_type = 'mesh'
        
        # 更新UI
        self.mesh_group.setVisible(True)
        self.pc_group.setVisible(False)
        self._update_info_text(data, 'mesh')
    
    def _load_point_cloud_data(self, data, file_path):
        """加载 Point Cloud 数据"""
        print(f"加载 Point Cloud 数据: {len(data['points'])} 点")
        self.gl_widget.load_point_cloud_data(
            data['points'],
            data['colors']
        )
        
        # 重置视角以适应模型
        self.gl_widget.renderer.reset_view()
        
        self.current_file_path = file_path
        self.data_type = 'point_cloud'
        
        # 更新UI
        self.mesh_group.setVisible(False)
        self.pc_group.setVisible(True)
        self._update_info_text(data, 'point_cloud')
    
    def _update_info_text(self, data, data_type):
        """更新信息文本"""
        lines = []
        
        if self.current_file_path:
            lines.append(f"文件: {os.path.basename(self.current_file_path)}")
            lines.append(f"路径: {self.current_file_path}")
        
        if data_type == 'mesh':
            lines.append(f"类型: Mesh")
            lines.append(f"顶点数: {len(data['vertices']):,}")
            lines.append(f"面数: {len(data['indices']):,}")
            if data['colors'] is not None:
                lines.append("颜色: Vertex Color")
            else:
                lines.append("颜色: Uniform")
        elif data_type == 'point_cloud':
            lines.append(f"类型: Point Cloud")
            lines.append(f"点数: {len(data['points']):,}")
            if data['colors'] is not None:
                lines.append("颜色: RGB/Height-based")
            else:
                lines.append("颜色: Uniform")
        
        self.info_text.setText("\n".join(lines))
    
    def _on_mesh_render_mode_changed(self, index):
        """Mesh 渲染模式改变"""
        modes = ['surface', 'wireframe', 'surface+wireframe']
        if index < len(modes):
            self.gl_widget.set_render_mode(modes[index])
    
    def _on_mesh_color_mode_changed(self, index):
        """Mesh 颜色模式改变"""
        modes = ['uniform', 'vertex']
        if index < len(modes):
            self.gl_widget.set_color_mode(modes[index])
    
    def _on_pc_color_mode_changed(self, index):
        """Point Cloud 颜色模式改变"""
        # 注意：对于 Point Cloud，我们通过重新加载数据来改变颜色模式
        if self.current_file_path and self.data_type == 'point_cloud':
            try:
                data = PointCloudLoader.load(self.current_file_path)
                if index == 1:  # Height-based
                    data['colors'] = PointCloudLoader._height_based_colors(data['points'])
                self.gl_widget.load_point_cloud_data(data['points'], data['colors'])
            except Exception as e:
                QMessageBox.warning(self, "警告", f"无法更新颜色模式:\n{str(e)}")
    
    def _on_point_size_changed(self, value):
        """点大小改变"""
        size = value / 10.0
        self.point_size_label.setText(f"点大小: {size:.1f}")
        self.gl_widget.set_point_size(size)
