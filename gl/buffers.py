"""
OpenGL 缓冲区管理
VAO/VBO/EBO 封装
"""
from OpenGL.GL import *
import numpy as np


class VertexBuffer:
    """顶点缓冲区对象 (VBO)"""
    
    def __init__(self, data, target=GL_ARRAY_BUFFER, usage=GL_STATIC_DRAW):
        """
        初始化 VBO
        
        Args:
            data: 顶点数据 (numpy array)
            target: 缓冲区目标
            usage: 缓冲区使用方式
        """
        self.buffer_id = glGenBuffers(1)
        self.target = target
        self.usage = usage
        
        glBindBuffer(self.target, self.buffer_id)
        glBufferData(self.target, data.nbytes, data, self.usage)
        glBindBuffer(self.target, 0)
    
    def bind(self):
        """绑定 VBO"""
        glBindBuffer(self.target, self.buffer_id)
    
    def unbind(self):
        """解绑 VBO"""
        glBindBuffer(self.target, 0)
    
    def delete(self):
        """删除 VBO"""
        glDeleteBuffers(1, [self.buffer_id])


class IndexBuffer:
    """索引缓冲区对象 (EBO)"""
    
    def __init__(self, indices, usage=GL_STATIC_DRAW):
        """
        初始化 EBO
        
        Args:
            indices: 索引数据 (numpy array)
            usage: 缓冲区使用方式
        """
        self.buffer_id = glGenBuffers(1)
        self.count = len(indices)
        self.usage = usage
        
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.buffer_id)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, self.usage)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
    
    def bind(self):
        """绑定 EBO"""
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.buffer_id)
    
    def unbind(self):
        """解绑 EBO"""
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
    
    def delete(self):
        """删除 EBO"""
        glDeleteBuffers(1, [self.buffer_id])


class VertexArray:
    """顶点数组对象 (VAO)"""
    
    def __init__(self):
        """初始化 VAO"""
        self.vao_id = glGenVertexArrays(1)
        self.buffers = []
        self.is_bound = False
    
    def bind(self):
        """绑定 VAO"""
        glBindVertexArray(self.vao_id)
        self.is_bound = True
    
    def unbind(self):
        """解绑 VAO"""
        glBindVertexArray(0)
        self.is_bound = False
    
    def add_buffer(self, buffer, index, size, dtype=GL_FLOAT, normalized=GL_FALSE, stride=0, offset=None):
        """
        添加顶点属性缓冲区
        
        Args:
            buffer: VertexBuffer 对象
            index: 属性索引
            size: 属性大小 (vec3 = 3)
            dtype: 数据类型
            normalized: 是否标准化
            stride: 步长
            offset: 偏移量
        """
        if not self.is_bound:
            raise RuntimeError("VAO must be bound before adding buffers")
        
        buffer.bind()
        glVertexAttribPointer(index, size, dtype, normalized, stride, offset or ctypes.c_void_p(0))
        glEnableVertexAttribArray(index)
        buffer.unbind()
        
        self.buffers.append(buffer)
    
    def delete(self):
        """删除 VAO 和相关缓冲区"""
        for buffer in self.buffers:
            buffer.delete()
        glDeleteVertexArrays(1, [self.vao_id])
