"""
Shader 管理器
编译和链接 GLSL 着色器程序
"""
from OpenGL.GL import *
import os


class Shader:
    """着色器程序管理器"""
    
    def __init__(self, vertex_path, fragment_path):
        """
        初始化着色器程序
        
        Args:
            vertex_path: 顶点着色器文件路径
            fragment_path: 片段着色器文件路径
        """
        self.program_id = self._compile_shader_program(vertex_path, fragment_path)
    
    def _compile_shader_program(self, vertex_path, fragment_path):
        """编译着色器程序"""
        # 读取着色器源码
        with open(vertex_path, 'r', encoding='utf-8') as f:
            vertex_source = f.read()
        
        with open(fragment_path, 'r', encoding='utf-8') as f:
            fragment_source = f.read()
        
        # 编译顶点着色器
        vertex_shader = glCreateShader(GL_VERTEX_SHADER)
        glShaderSource(vertex_shader, vertex_source)
        glCompileShader(vertex_shader)
        
        # 检查编译错误
        if not glGetShaderiv(vertex_shader, GL_COMPILE_STATUS):
            error = glGetShaderInfoLog(vertex_shader).decode()
            raise RuntimeError(f"Vertex shader compilation failed:\n{error}")
        
        # 编译片段着色器
        fragment_shader = glCreateShader(GL_FRAGMENT_SHADER)
        glShaderSource(fragment_shader, fragment_source)
        glCompileShader(fragment_shader)
        
        # 检查编译错误
        if not glGetShaderiv(fragment_shader, GL_COMPILE_STATUS):
            error = glGetShaderInfoLog(fragment_shader).decode()
            raise RuntimeError(f"Fragment shader compilation failed:\n{error}")
        
        # 链接着色器程序
        program = glCreateProgram()
        glAttachShader(program, vertex_shader)
        glAttachShader(program, fragment_shader)
        glLinkProgram(program)
        
        # 检查链接错误
        if not glGetProgramiv(program, GL_LINK_STATUS):
            error = glGetProgramInfoLog(program).decode()
            raise RuntimeError(f"Shader program linking failed:\n{error}")
        
        # 删除着色器对象
        glDeleteShader(vertex_shader)
        glDeleteShader(fragment_shader)
        
        return program
    
    def use(self):
        """激活着色器程序"""
        glUseProgram(self.program_id)
    
    def set_mat4(self, name, value):
        """设置 mat4 uniform 变量"""
        loc = glGetUniformLocation(self.program_id, name)
        glUniformMatrix4fv(loc, 1, GL_FALSE, value)
    
    def set_vec3(self, name, value):
        """设置 vec3 uniform 变量"""
        loc = glGetUniformLocation(self.program_id, name)
        glUniform3f(loc, value[0], value[1], value[2])
    
    def set_float(self, name, value):
        """设置 float uniform 变量"""
        loc = glGetUniformLocation(self.program_id, name)
        glUniform1f(loc, value)
    
    def set_bool(self, name, value):
        """设置 bool uniform 变量"""
        loc = glGetUniformLocation(self.program_id, name)
        glUniform1i(loc, int(value))
    
    def get_location(self, name):
        """获取 uniform 变量位置"""
        return glGetUniformLocation(self.program_id, name)
