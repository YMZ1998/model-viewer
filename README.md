# PyQtGLMeshViewer

A desktop viewer for **3D meshes** and **point clouds**, built with **PyQt5 + OpenGL**, now including an **engineering inspection workbench**.

## Features

- Supported formats
  - Mesh: `.obj`, `.stl`, `.ply`
  - Point cloud: `.ply`, `.xyz`
- Core viewing tools
  - Orbit, pan, zoom
  - Fit view
  - Standard views: `Front`, `Back`, `Left`, `Right`, `Top`, `Bottom`, `Isometric`
  - Projection toggle: `Perspective` / `Orthographic`
- Visual presets
  - `Studio Dark`
  - `Studio Light`
  - `Blueprint`
  - `Inspection Lab`
- Section tools
  - Interactive section plane
  - Axis switch: `X` / `Y` / `Z`
  - Offset slider with invert direction
- Scene helpers
  - World axes
  - Ground grid
  - Bounding box
  - Model center marker
  - Vertex normals
  - Face normals
- Render controls
  - Mesh surface / wireframe / surface+wireframe
  - Mesh opacity control
  - Point-cloud opacity control
  - Back-face culling toggle
  - Point size and wireframe line width controls
- Desktop conveniences
  - Drag-and-drop file loading
  - Recent files
  - Multiple UI themes
  - Screenshot export to PNG
- Inspection workbench
  - Inspection mode toggle
  - Point / face / measurement item picking
  - Selection highlight and property panel
  - Distance measurement
  - Angle measurement
  - Single-triangle face area measurement
  - Measurement grouping, rename, delete, show/hide
  - Inspection report export as `PNG + JSON`

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

- Browse mode
  - Left drag: orbit
  - Right drag: pan
  - Mouse wheel: zoom
- Inspection mode
  - Left click: pick / create measurement
  - Right drag: pan
  - Mouse wheel: zoom

## Inspection Workflow

1. Open a mesh or point cloud model.
2. Enable **Inspection Mode** from the sidebar or `Inspect` menu.
3. Choose a tool:
   - `Select`: pick point / face / measurement item
   - `Distance`: click two points
   - `Angle`: click three points, with the second point as the vertex
   - `Face Area`: click one triangle face
4. Use the **Groups** panel to organize results.
5. Use **Inspection Layers** to toggle bounding box, center, and normals.
6. Export a report to generate:
   - `report_name.png`
   - `report_name.json`

## Manual Smoke Checklist

- File loading
  - Open `.obj`, `.stl`, `.ply`, `.xyz`
  - Drag a file into the window
  - Open a recent file entry
- View behavior
  - Fit view works after loading
  - `Front / Right / Top / Isometric` switch correctly
  - `Perspective / Orthographic` toggle keeps navigation usable
  - Section plane clips the model and updates preview immediately
  - Pan stays usable after zooming in closely
- Render tuning
  - Mesh opacity updates immediately and persists across restart
  - Point-cloud opacity updates immediately and persists across restart
  - Back-face culling toggles immediately on meshes
  - Visual preset switches background and lighting immediately
- Inspection mode
  - `Select` can pick points
  - `Select` can pick faces on a mesh
  - Empty click does not leave stale state
- Measurements
  - `Distance` creates one item after two clicks
  - `Angle` creates one item after three clicks
  - `Face Area` creates one item after one face click
  - New measurements enter the current group
- Group management
  - Add, rename, delete groups
  - Toggle group visibility
  - Toggle individual measurement visibility
- Geometry overlays
  - Bounding box toggles immediately
  - Model center toggles immediately
  - Vertex normals toggle immediately
  - Face normals toggle immediately
- Export
  - Screenshot export writes a PNG
  - Inspection report writes both PNG and JSON
  - JSON includes model path, timestamp, camera state, groups, and measurements

## Project Structure

```text
model-viewer/
├── main.py
├── gui/
│   ├── app_settings.py
│   ├── main_window.py
│   ├── gl_widget.py
│   ├── control_panel.py
│   └── theme.py
├── gl/
│   ├── renderer.py
│   └── camera.py
├── inspection/
│   └── models.py
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

## Notes

- The current inspection workflow is **single-model only**.
- Measurement units are reported as **model units**.
- Face area currently applies to **one picked triangle face**.
- Measurement groups are **session-only** unless exported in a report.

## License

MIT
