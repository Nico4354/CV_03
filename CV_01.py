from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GL import shaders
import glfw
import numpy as np
import ctypes
import os

# ---------- VARIABLES GLOBALES DE CÁMARA E INTERACCIÓN ----------
rotation_x = 0.0
rotation_y = 0.0
scale = 1.0
mouse_button_pressed = False
last_mouse_x = 0
last_mouse_y = 0
pan_x = 0.0
pan_y = 0.0
middle_mouse_pressed = False
window_width = 800
window_height = 600

# Controla si se ven los ejes
show_axes = True 

# Variable para la lista de visualización del STL
stl_display_list = None

# ---------- FUNCIONES AUXILIARES ----------

def load_stl(file_path):
    """
    Carga un archivo STL (ASCII) simple y crea una Display List de OpenGL.
    """
    global stl_display_list
    vertices = []
    normals = []
    
    current_normal = (0, 0, 0)
    
    try:
        with open(file_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if not parts:
                    continue
                    
                if parts[0] == 'facet' and parts[1] == 'normal':
                    current_normal = (float(parts[2]), float(parts[3]), float(parts[4]))
                elif parts[0] == 'vertex':
                    v = (float(parts[1]), float(parts[2]), float(parts[3]))
                    vertices.append((current_normal, v))
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo {file_path}")
        return

    # Crear Display List
    stl_display_list = glGenLists(1)
    glNewList(stl_display_list, GL_COMPILE)
    
    glBegin(GL_TRIANGLES)
    for normal, vertex in vertices:
        glNormal3f(*normal)
        glVertex3f(*vertex)
    glEnd()
    
    glEndList()
    print(f"Modelo STL cargado: {len(vertices)//3} triángulos.")


def draw_axes(length=10.0):
    """Dibuja líneas para los ejes X (Rojo), Y (Verde), Z (Azul)"""
    glDisable(GL_TEXTURE_2D) 
    glLineWidth(3.0)

    glBegin(GL_LINES)
    # Eje X - ROJO
    glColor3f(1.0, 0.0, 0.0) 
    glVertex3f(-length, 0, 0) 
    glVertex3f(length, 0, 0)

    # Eje Y - VERDE
    glColor3f(0.0, 1.0, 0.0)
    glVertex3f(0, -length, 0)
    glVertex3f(0, length, 0)

    # Eje Z - AZUL
    glColor3f(0.0, 0.0, 1.0)
    glVertex3f(0, 0, -length)
    glVertex3f(0, 0, length)
    glEnd()

    glLineWidth(1.0) 
    glColor3f(1.0, 1.0, 1.0) 

# ---------- TRANSFORMACIONES (INPUTS) ----------
def key_callback(window, key, scancode, action, mods):
    global rotation_x, rotation_y, scale, show_axes
    
    if action == glfw.PRESS or action == glfw.REPEAT:
        # Movimiento
        if key == glfw.KEY_UP: rotation_x += 5.0
        elif key == glfw.KEY_DOWN: rotation_x -= 5.0
        elif key == glfw.KEY_LEFT: rotation_y -= 5.0
        elif key == glfw.KEY_RIGHT: rotation_y += 5.0
        # Zoom
        elif key == glfw.KEY_EQUAL: scale += 0.1
        elif key == glfw.KEY_MINUS: scale -= 0.1
        
        # Ocultar/Mostrar ejes (Tecla 'A')
        elif key == glfw.KEY_A and action == glfw.PRESS:
            show_axes = not show_axes
            print(f"Ejes visibles: {show_axes}")

def mouse_button_callback(window, button, action, mods):
    global mouse_button_pressed, middle_mouse_pressed
    if button == glfw.MOUSE_BUTTON_LEFT:
        mouse_button_pressed = (action == glfw.PRESS)
    elif button == glfw.MOUSE_BUTTON_MIDDLE:
        middle_mouse_pressed = (action == glfw.PRESS)

def scroll_callback(window, xoffset, yoffset):
    global scale
    scale += yoffset * 0.1
    if scale < 0.1:
        scale = 0.1

def mouse_move_callback(window, x, y):
    global last_mouse_x, last_mouse_y
    global rotation_x, rotation_y, pan_x, pan_y
    if mouse_button_pressed:
        dx = x - last_mouse_x
        dy = y - last_mouse_y
        rotation_y += dx * 0.2
        rotation_x += dy * 0.2
    elif middle_mouse_pressed:
        dx = x - last_mouse_x
        dy = y - last_mouse_y
        pan_x += dx * 0.01
        pan_y -= dy * 0.01
    last_mouse_x = x
    last_mouse_y = y

def framebuffer_size_callback(window, width, height):
    global window_width, window_height
    window_width = width
    window_height = height
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    aspect = width / height if height != 0 else 1.0
    glOrtho(-5 * aspect, 5 * aspect, -5, 5, 1, 100) # Aumenté el plano lejano a 100
    glMatrixMode(GL_MODELVIEW)


# ---------- MODELO 3D ----------
def draw_model():
    glLoadIdentity()
    gluLookAt(0, 0, 10, 0, 0, 0, 0, 1, 0)
    
    # Transformaciones globales (Cámara/Mouse)
    glTranslatef(pan_x, pan_y, 0)
    glRotatef(rotation_x, 1, 0, 0)
    glRotatef(rotation_y, 0, 1, 0)
    glScalef(scale, scale, scale)

    # --- EJES (Estos se quedan igual para orientarte) ---
    global show_axes
    if show_axes:
        glDisable(GL_DEPTH_TEST) 
        draw_axes(15.0) 
        glEnable(GL_DEPTH_TEST)

    # --- DIBUJAR MODELO STL ---
    if stl_display_list:
        glPushMatrix()
        
        # --- CORRECCIÓN DE ORIENTACIÓN ---
        # Rotamos -90 grados en X para que el eje Z (altura de GeoGebra) 
        # coincida con el eje Y (altura de OpenGL).
        glRotatef(-90, 1, 0, 0) 
        
        # Ajuste de escala
        glScalef(0.1, 0.1, 0.1) 
        
        # Color base del modelo
        glColor3f(0.7, 0.7, 0.8) 
        
        glCallList(stl_display_list)
        glPopMatrix()

# ---------- SHADER DE FONDO ANIMADO ----------
_gradient_prog = None
_gradient_vao = None
_uniform_time = None
_uniform_res = None

def create_gradient_shader():
    global _gradient_prog, _gradient_vao, _uniform_time, _uniform_res
    vert_src = """
    #version 330 core
    layout(location = 0) in vec2 a_pos;
    layout(location = 1) in vec2 a_uv;
    out vec2 v_uv;
    void main() {
        v_uv = a_uv;
        gl_Position = vec4(a_pos, 0.0, 1.0);
    }
    """
    frag_src = """
    #version 330 core
    in vec2 v_uv;
    out vec4 fragColor;
    uniform float u_time;
    uniform vec2 u_resolution;
    void main() {
        vec2 uv = v_uv;
        float wave = sin((uv.y * 10.0 + u_time*1.2) + sin(uv.x * 6.0 + u_time*0.7)*0.8) * 0.5 + 0.5;
        float gradient = uv.y;
        vec3 top = vec3(0.70, 1.00, 0.20);
        vec3 mid1 = vec3(0.25, 0.85, 0.20);
        vec3 mid2 = vec3(0.05, 0.75, 0.45);
        vec3 bot = vec3(0.00, 0.30, 0.10);
        float g = smoothstep(0.0, 1.0, gradient);
        float pulse = 0.15 * sin(u_time * 0.9 + uv.x*3.0);
        vec3 color = mix(top, mid1, smoothstep(0.0, 0.35, g + pulse));
        color = mix(color, mid2, smoothstep(0.25, 0.7, g + wave*0.15 + pulse));
        color = mix(color, bot, smoothstep(0.6, 1.0, g + wave*0.25));
        float curve = smoothstep(0.0, 1.0, 1.0 - pow(abs(uv.x - 0.5)*1.8, 1.2));
        color *= mix(0.95, 1.05, curve);
        fragColor = vec4(color, 1.0);
    }
    """
    try:
        vert = shaders.compileShader(vert_src, GL_VERTEX_SHADER)
        frag = shaders.compileShader(frag_src, GL_FRAGMENT_SHADER)
        prog = shaders.compileProgram(vert, frag)
    except Exception as e:
        print("Shader Error:", e)
        return

    quad = np.array([
        -1.0, -1.0, 0.0, 0.0,
         1.0, -1.0, 1.0, 0.0,
         1.0,  1.0, 1.0, 1.0,
        -1.0, -1.0, 0.0, 0.0,
         1.0,  1.0, 1.0, 1.0,
        -1.0,  1.0, 0.0, 1.0
    ], dtype=np.float32)
    vao = glGenVertexArrays(1)
    vbo = glGenBuffers(1)
    glBindVertexArray(vao)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, quad.nbytes, quad, GL_STATIC_DRAW)
    stride = 4 * quad.itemsize
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
    glEnableVertexAttribArray(1)
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(2 * quad.itemsize))
    glBindBuffer(GL_ARRAY_BUFFER, 0)
    glBindVertexArray(0)
    _gradient_prog = prog
    _gradient_vao = vao
    _uniform_time = glGetUniformLocation(prog, "u_time")
    _uniform_res = glGetUniformLocation(prog, "u_resolution")

def init_gradient_shader():
    create_gradient_shader()

def draw_animated_gradient():
    global _gradient_prog, _gradient_vao, _uniform_time, _uniform_res
    if _gradient_prog is None: return
    depth_enabled = glIsEnabled(GL_DEPTH_TEST)
    glDisable(GL_DEPTH_TEST)
    glDepthMask(GL_FALSE)
    glUseProgram(_gradient_prog)
    t = glfw.get_time()
    vp = glGetIntegerv(GL_VIEWPORT)
    width, height = vp[2], vp[3]
    if _uniform_time != -1: glUniform1f(_uniform_time, float(t))
    if _uniform_res != -1: glUniform2f(_uniform_res, float(width), float(height))
    glBindVertexArray(_gradient_vao)
    glDrawArrays(GL_TRIANGLES, 0, 6)
    glBindVertexArray(0)
    glUseProgram(0)
    glDepthMask(GL_TRUE)
    if depth_enabled:
        glEnable(GL_DEPTH_TEST)

# ---------- MAIN ----------
def main():
    if not glfw.init(): 
        return
    
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_COMPAT_PROFILE)

    window = glfw.create_window(800, 600, "Visor 3D STL - Proyecto Final", None, None)
    if not window:
        glfw.terminate()
        return
    glfw.make_context_current(window)

    init_gradient_shader()

    # Configuración básica de OpenGL
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)   # Activar iluminación para ver el relieve
    glEnable(GL_LIGHT0)     # Activar luz por defecto
    glEnable(GL_COLOR_MATERIAL) # Permitir que glColor afecte al material
    
    # Configurar luz
    glLightfv(GL_LIGHT0, GL_POSITION, (10, 10, 10, 1))
    
    glClearColor(0, 0, 0, 1)

    # Cargar el modelo STL
    base_dir = os.path.dirname(__file__)
    stl_path = os.path.join(base_dir, "Final.stl")
    load_stl(stl_path)

    # Configurar proyección inicial
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    aspect = 800 / 600
    glOrtho(-5 * aspect, 5 * aspect, -5, 5, 1, 100)
    glMatrixMode(GL_MODELVIEW)

    glfw.set_framebuffer_size_callback(window, framebuffer_size_callback)
    glfw.set_key_callback(window, key_callback)
    glfw.set_scroll_callback(window, scroll_callback)
    glfw.set_mouse_button_callback(window, mouse_button_callback)
    glfw.set_cursor_pos_callback(window, mouse_move_callback)

    while not glfw.window_should_close(window):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        draw_animated_gradient()

        glUseProgram(0)
        draw_model()
        
        glfw.swap_buffers(window)
        glfw.poll_events()

    glfw.terminate()

if __name__ == "__main__":
    main()