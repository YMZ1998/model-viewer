# PyQtGLMeshViewer

基于 **PyQt5 + OpenGL** 的轻量级 3D 模型查看器，支持 Mesh 与 Point Cloud 的交互式浏览。

## 功能概览

- 支持格式：
  - Mesh：`.obj` / `.stl` / `.ply`
  - Point Cloud：`.ply` / `.xyz`
- 渲染模式：
  - Mesh：`Surface` / `Wireframe` / `Surface+Wireframe`
  - Point Cloud：`RGB` / `Height-based`
- 交互能力：旋转、平移、缩放、重置视角
- 实时控制：点大小、线宽、颜色模式、渲染模式

## 项目结构

```text
model-viewer/
├── main.py
├── requirements.txt
├── README.md
├── gui/
│   ├── main_window.py
│   ├── gl_widget.py
│   └── control_panel.py
├── gl/
│   ├── renderer.py
│   ├── camera.py
│   ├── shader.py
│   └── buffers.py
├── model_io/
│   ├── mesh_loader.py
│   └── point_loader.py
├── math_utils/
│   ├── transform.py
│   └── trackball.py
└── shaders/
    ├── mesh.vert
    ├── mesh.frag
    ├── point.vert
    └── point.frag
```

> 注：当前渲染路径使用固定管线（Immediate Mode）进行绘制；`gl/shader.py` 与 `shaders/` 为后续可扩展资源。

## 安装

```bash
pip install -r requirements.txt
```

可选（推荐）安装更稳健的 PLY 解析依赖：

```bash
pip install plyfile
```

## 运行

### 1) 启动 GUI

```bash
python main.py
```

### 2) 启动时直接加载文件

```bash
python main.py test_cube.obj
```

## 操作说明

- 鼠标左键拖动：旋转
- 鼠标右键拖动：平移
- 鼠标滚轮：缩放
- `R`：重置视角
- `W`：切换线框模式（Mesh）
- `Esc`：退出

## 常见问题（FAQ）

1. **窗口打开后无法显示模型？**
   - 请确认显卡/驱动支持 OpenGL。
   - Linux 下可尝试安装/更新系统 OpenGL 运行库。

2. **PLY 文件加载失败？**
   - 程序会优先按 Mesh 读取，失败后会尝试按 Point Cloud 读取（仅 `.ply`）。
   - 可先使用样例文件 `test_cube.ply` 验证运行环境。

3. **点大小或线宽调节不生效？**
   - 点大小仅对 Point Cloud 生效。
   - 线宽仅对 Mesh 的 Wireframe 相关模式生效。

## 开发说明

建议在提交前至少运行：

```bash
python -m compileall -q .
```

## License

MIT
