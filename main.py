"""
Application entry point for PyQtGLMeshViewer.
"""
import os
import sys

from PyQt5.QtWidgets import QApplication

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.main_window import MainWindow


def main():
    """Launch the desktop application."""
    app = QApplication(sys.argv)
    app.setApplicationName("PyQtGLMeshViewer")
    app.setOrganizationName("OpenAI")

    window = MainWindow()
    window.show()

    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if os.path.exists(file_path):
            window.open_model_file(file_path)
        else:
            print(f"Warning: file does not exist: {file_path}")

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
