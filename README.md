# PyQtGLMeshViewer

A lightweight desktop viewer for **3D meshes** and **point clouds**, built with **PyQt5 + OpenGL**.

## Features

- Supported formats
  - Mesh: `.obj`, `.stl`, `.ply`
  - Point cloud: `.ply`, `.xyz`
- Core viewing tools
  - Orbit, pan, zoom
  - Fit view
  - Standard views: `Front`, `Back`, `Left`, `Right`, `Top`, `Bottom`, `Isometric`
- Display helpers
  - World axes
  - Ground grid
  - Mesh surface / wireframe / surface+wireframe
  - Point size and wireframe line width controls
- Desktop conveniences
  - Drag-and-drop file loading
  - Recent files
  - Screenshot export to PNG

## Install

```bash
pip install -r requirements.txt
```

Optional but recommended for more robust PLY parsing:

```bash
pip install plyfile
```

## Run

Launch the viewer:

```bash
python main.py
```

Open a file directly:

```bash
python main.py airplane.ply
```

## Shortcuts

- `F` / `R`: Fit view
- `W`: Toggle mesh wireframe mode
- `1`: Front view
- `3`: Right view
- `7`: Top view
- `Ctrl+O`: Open file
- `Ctrl+S`: Export screenshot
- `Esc`: Close window

Mouse:

- Left drag: orbit
- Right drag: pan
- Mouse wheel: zoom

## Project Structure

```text
model-viewer/
├── main.py
├── gui/
│   ├── main_window.py
│   ├── gl_widget.py
│   └── control_panel.py
├── gl/
│   ├── renderer.py
│   └── camera.py
├── model_io/
│   ├── mesh_loader.py
│   └── point_loader.py
└── math_utils/
    ├── transform.py
    └── trackball.py
```

## Development Check

```bash
python -m compileall -q .
```

## License

MIT
