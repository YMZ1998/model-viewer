from dataclasses import dataclass, field

from PyQt5.QtCore import QSettings

from gui.theme import DEFAULT_THEME_NAME


SETTINGS_ORGANIZATION = "OpenAI"
SETTINGS_APPLICATION = "PyQtGLMeshViewer"
MAX_RECENT_FILES = 10


@dataclass
class ViewerSettings:
    recent_files: list = field(default_factory=list)
    show_axes: bool = True
    show_grid: bool = False
    projection_mode: str = "perspective"
    visual_preset: str = "studio_dark"
    section_plane_enabled: bool = False
    section_plane_axis: str = "z"
    section_plane_offset_ratio: float = 0.0
    section_plane_inverted: bool = False
    mesh_opacity: float = 1.0
    point_opacity: float = 1.0
    backface_culling: bool = False
    point_size: float = 2.0
    line_width: float = 2.0
    show_bounding_box: bool = False
    show_model_center: bool = False
    show_vertex_normals: bool = False
    show_face_normals: bool = False
    pick_preference: str = "balanced"
    theme_name: str = DEFAULT_THEME_NAME

    @classmethod
    def from_qsettings(cls, qsettings):
        recent_files = qsettings.value("recent_files", [])
        if isinstance(recent_files, str):
            recent_files = [recent_files] if recent_files else []
        if recent_files is None:
            recent_files = []
        return cls(
            recent_files=[path for path in recent_files if isinstance(path, str) and path],
            show_axes=qsettings.value("view/show_axes", True, type=bool),
            show_grid=qsettings.value("view/show_grid", False, type=bool),
            projection_mode=qsettings.value("view/projection_mode", "perspective", type=str),
            visual_preset=qsettings.value("view/visual_preset", "studio_dark", type=str),
            section_plane_enabled=qsettings.value("view/section_plane_enabled", False, type=bool),
            section_plane_axis=qsettings.value("view/section_plane_axis", "z", type=str),
            section_plane_offset_ratio=qsettings.value("view/section_plane_offset_ratio", 0.0, type=float),
            section_plane_inverted=qsettings.value("view/section_plane_inverted", False, type=bool),
            mesh_opacity=qsettings.value("render/mesh_opacity", 1.0, type=float),
            point_opacity=qsettings.value("render/point_opacity", 1.0, type=float),
            backface_culling=qsettings.value("render/backface_culling", False, type=bool),
            point_size=qsettings.value("render/point_size", 2.0, type=float),
            line_width=qsettings.value("render/line_width", 2.0, type=float),
            show_bounding_box=qsettings.value("inspect/show_bounding_box", False, type=bool),
            show_model_center=qsettings.value("inspect/show_model_center", False, type=bool),
            show_vertex_normals=qsettings.value("inspect/show_vertex_normals", False, type=bool),
            show_face_normals=qsettings.value("inspect/show_face_normals", False, type=bool),
            pick_preference=qsettings.value("inspect/pick_preference", "balanced", type=str),
            theme_name=qsettings.value("ui/theme", DEFAULT_THEME_NAME, type=str),
        )

    def save(self, qsettings):
        qsettings.setValue("recent_files", self.recent_files)
        qsettings.setValue("view/show_axes", self.show_axes)
        qsettings.setValue("view/show_grid", self.show_grid)
        qsettings.setValue("view/projection_mode", self.projection_mode)
        qsettings.setValue("view/visual_preset", self.visual_preset)
        qsettings.setValue("view/section_plane_enabled", self.section_plane_enabled)
        qsettings.setValue("view/section_plane_axis", self.section_plane_axis)
        qsettings.setValue("view/section_plane_offset_ratio", self.section_plane_offset_ratio)
        qsettings.setValue("view/section_plane_inverted", self.section_plane_inverted)
        qsettings.setValue("render/mesh_opacity", self.mesh_opacity)
        qsettings.setValue("render/point_opacity", self.point_opacity)
        qsettings.setValue("render/backface_culling", self.backface_culling)
        qsettings.setValue("render/point_size", self.point_size)
        qsettings.setValue("render/line_width", self.line_width)
        qsettings.setValue("inspect/show_bounding_box", self.show_bounding_box)
        qsettings.setValue("inspect/show_model_center", self.show_model_center)
        qsettings.setValue("inspect/show_vertex_normals", self.show_vertex_normals)
        qsettings.setValue("inspect/show_face_normals", self.show_face_normals)
        qsettings.setValue("inspect/pick_preference", self.pick_preference)
        qsettings.setValue("ui/theme", self.theme_name)

    def add_recent_file(self, file_path):
        normalized = file_path.lower()
        self.recent_files = [path for path in self.recent_files if path.lower() != normalized]
        self.recent_files.insert(0, file_path)
        self.recent_files = self.recent_files[:MAX_RECENT_FILES]

    def remove_recent_file(self, file_path):
        normalized = file_path.lower()
        self.recent_files = [path for path in self.recent_files if path.lower() != normalized]


def create_qsettings():
    return QSettings(SETTINGS_ORGANIZATION, SETTINGS_APPLICATION)
