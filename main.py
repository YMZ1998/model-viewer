"""
PyQtGLMeshViewer
基于 PyQt5 和 OpenGL Core Profile 3.3 的 3D 模型查看器

支持格式:
  Mesh: .obj .stl .ply
  Point Cloud: .ply .xyz

快捷键:
  R - 重置视角
  W - 切换线框模式
  Esc - 退出
  鼠标左键 - 旋转
  鼠标右键 - 平移
  鼠标滚轮 - 缩放
"""
import sys
import os
from PyQt5.QtWidgets import QApplication

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.main_window import MainWindow


def main():
    """主函数"""
    print("="*60)
    print("PyQtGLMeshViewer - 3D Mesh & Point Cloud Viewer")
    print("="*60)
    print("支持格式:")
    print("  Mesh: .obj .stl .ply")
    print("  Point Cloud: .ply .xyz")
    print()
    print("快捷键:")
    print("  R - 重置视角")
    print("  W - 切换线框模式")
    print("  Esc - 退出")
    print()
    print("鼠标操作:")
    print("  左键拖动 - 旋转")
    print("  右键拖动 - 平移")
    print("  滚轮 - 缩放")
    print("="*60)
    print()
    
    # 创建应用
    app = QApplication(sys.argv)
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    # 如果命令行提供了文件路径，直接加载
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if os.path.exists(file_path):
            print(f"加载文件: {file_path}")
            try:
                window.control_panel.load_file(file_path)
            except Exception as e:
                print(f"加载文件时出错: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"警告: 文件不存在: {file_path}")
    
    # 运行应用
    print("开始运行应用...")
    result = app.exec_()
    print(f"应用退出，返回值: {result}")
    sys.exit(result)


if __name__ == "__main__":
    main()
