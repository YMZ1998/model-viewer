#version 330 core

in vec3 Color;

out vec4 FragColor;

uniform float pointSize;

void main()
{
    // 计算点的圆形形状
    vec2 coord = gl_PointCoord - vec2(0.5);
    if (length(coord) > 0.5) {
        discard;
    }
    
    FragColor = vec4(Color, 1.0);
}