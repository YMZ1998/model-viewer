"""
Application entry point for PyQtGLMeshViewer.
"""
import importlib
import os
import sys
import traceback

from PyQt5.QtWidgets import QApplication, QMessageBox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.app_settings import ViewerSettings, create_qsettings
from gui.main_window import MainWindow
from gui.theme import apply_theme


def _show_error(message, details=None):
    """Show a startup error dialog when possible."""
    app = QApplication.instance()
    owns_app = app is None
    if owns_app:
        app = QApplication(sys.argv)
    QMessageBox.critical(None, "PyQtGLMeshViewer Startup Error", f"{message}\n\n{details or ''}".strip())
    if owns_app:
        app.quit()


def _check_runtime_dependencies():
    """Validate runtime dependencies before launching the UI."""
    missing = []
    checks = {
        "OpenGL.GL": "PyOpenGL",
    }
    for module_name, package_name in checks.items():
        try:
            importlib.import_module(module_name)
        except Exception:
            missing.append(package_name)
    if missing:
        missing_text = ", ".join(sorted(set(missing)))
        raise RuntimeError(
            "Missing runtime dependency: "
            f"{missing_text}. Please run `python -m pip install -r requirements.txt`."
        )


def main():
    """Launch the desktop application."""
    try:
        _check_runtime_dependencies()

        app = QApplication(sys.argv)
        app.setApplicationName("PyQtGLMeshViewer")
        app.setOrganizationName("OpenAI")
        settings = create_qsettings()
        viewer_settings = ViewerSettings.from_qsettings(settings)
        apply_theme(app, viewer_settings.theme_name)

        window = MainWindow()
        window.show()

        if len(sys.argv) > 1:
            file_path = sys.argv[1]
            if os.path.exists(file_path):
                window.open_model_file(file_path)
            else:
                print(f"Warning: file does not exist: {file_path}")

        sys.exit(app.exec_())
    except Exception as error:
        traceback.print_exc()
        _show_error("Application failed to start.", str(error))
        sys.exit(1)


if __name__ == "__main__":
    main()
