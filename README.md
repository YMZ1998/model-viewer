# PyQtGLMeshViewer

基于 PyQt5 和 OpenGL Core Profile 3.3 的 3D 模型查看器，支持 Mesh 和 Point Cloud 的交互式可视化。

## 功能特性

### 支持的文件格式

- **Mesh**: `.obj`, `.stl`, `.ply`
- **Point Cloud**: `.ply`, `.xyz`

### Mesh 渲染模式

- **Surface**: 表面渲染（Phong 光照）
- **Wireframe**: 线框渲染
- **Surface + Wireframe**: 表面+线框组合渲染

### Mesh 颜色模式

- **Uniform**: 统一颜色
- **Vertex Color**: 顶点颜色

### Point Cloud 渲染模式

- **RGB**: 使用原始 RGB 颜色
- **Height-based**: 基于高度的颜色映射（热力图）
- **可调 point size**: 可调节点大小

### OpenGL 特性

- 使用 OpenGL Core Profile 3.3
- VAO / VBO / EBO 缓冲区管理
- GLSL 着色器程序
- 启用深度测试
- 支持窗口大小调整

### 交互操作

- **鼠标左键拖动**: 旋转（Trackball）
- **鼠标右键拖动**: 平移
- **鼠标滚轮**: 缩放
- **R 键**: 重置视角
- **W 键**: 切换线框模式
- **Esc 键**: 退出

### GUI 界面

- PyQt5 主窗口
- 左侧 OpenGL 渲染窗口
- 右侧控制面板
- 菜单栏：文件打开、退出
- 实时模型信息显示

## 项目结构

```
PyQtGLMeshViewer/
├── main.py                 # 程序入口
├── requirements.txt        # 依赖配置
├── README.md              # 说明文档
├── gui/                   # GUI 模块
│   ├── __init__.py
│   ├── main_window.py     # 主窗口
│   ├── gl_widget.py       # OpenGL 渲染窗口部件
│   └── control_panel.py   # 控制面板
├── gl/                    # OpenGL 核心模块
│   ├── __init__.py
│   ├── shader.py          # 着色器管理
│   ├── buffers.py         # 缓冲区管理
│   ├── camera.py          # 相机系统
│   └── renderer.py        # 渲染器
├── io/                    # 文件IO模块
│   ├── __init__.py
│   ├── mesh_loader.py     # Mesh 加载器
│   └── point_loader.py    # Point Cloud 加载器
├── math/                  # 数学工具
│   ├── __init__.py
│   ├── transform.py       # 变换矩阵
│   └── trackball.py       # Trackball 控制
└── shaders/               # GLSL 着色器
    ├── mesh.vert          # Mesh 顶点着色器
    ├── mesh.frag          # Mesh 片段着色器
    ├── point.vert         # Point 顶点着色器
    └── point.frag         # Point 片段着色器
```

## 安装

### 环境要求

- Python 3.9+
- pip

### 安装依赖

```bash
pip install -r requirements.txt
```

或手动安装：

```bash
pip install PyQt5>=5.15.0 PyOpenGL>=3.1.5 PyOpenGL-accelerate>=3.1.5 numpy>=1.21.0
```

## 使用方法

### 方式 1: 通过 GUI 打开文件

```bash
python main.py
```

启动后使用菜单栏"文件"->"打开文件..."或点击控制面板的"打开文件..."按钮选择模型文件。

### 方式 2: 命令行指定文件

```bash
python main.py path/to/your/model.obj
```

## 模块说明

### gui/main_window.py
主窗口，包含菜单栏、状态栏、OpenGL 渲染窗口和控制面板。

### gui/gl_widget.py
OpenGL 渲染窗口部件，继承自 QOpenGLWidget，处理 OpenGL 初始化、渲染和用户交互。

### gui/control_panel.py
控制面板，包含文件操作按钮、渲染设置控件和模型信息显示。

### gl/shader.py
着色器管理器，负责编译和链接 GLSL 着色器程序。

### gl/buffers.py
OpenGL 缓冲区管理，封装 VAO/VBO/EBO 操作。

### gl/camera.py
相机系统，管理视图和投影矩阵。

### gl/renderer.py
OpenGL 渲染器，管理 Mesh 和 Point Cloud 的渲染逻辑。

### io/mesh_loader.py
Mesh 文件加载器，支持 .obj .stl .ply 格式。

### io/point_loader.py
Point Cloud 文件加载器，支持 .ply .xyz 格式。

### math/transform.py
变换矩阵工具，提供视图变换、投影变换等矩阵计算。

### math/trackball.py
Trackball 相机控制，实现虚拟球面旋转交互。

### shaders/
GLSL 着色器文件，包含 Mesh 和 Point Cloud 的顶点和片段着色器。

## 使用示例

### 查看 Mesh 文件

```bash
python main.py examples/bunny.obj
```

在 GUI 中可以：
- 切换渲染模式（Surface/Wireframe/Surface+Wireframe）
- 切换颜色模式（Uniform/Vertex Color）

### 查看 Point Cloud 文件

```bash
python main.py examples/scan.ply
```

在 GUI 中可以：
- 切换颜色模式（RGB/Height-based）
- 调整点大小

## 快捷键

- **R**: 重置视角
- **W**: 切换线框模式
- **Esc**: 退出程序
- **鼠标左键拖动**: 旋转模型
- **鼠标右键拖动**: 平移视角
- **鼠标滚轮**: 缩放

## 技术栈

- **PyQt5**: GUI 框架
- **PyOpenGL**: OpenGL 绑定
- **NumPy**: 数值计算
- **GLSL**: 着色器语言 (OpenGL ES 3.3)

## 许可证

MIT License

## 开发者

资深 Python 图形与可视化系统工程师

## 更新日志

### v1.0.0
- 初始版本
- 支持 Mesh 和 Point Cloud 可视化
- 实现多种渲染模式和颜色模式
- 完整的 GUI 控制面板
- Trackball 相机控制
- 键盘和鼠标交互支持
- OpenGL Core Profile 3.3 实现
