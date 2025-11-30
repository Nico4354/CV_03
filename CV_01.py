from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GL import shaders
import glfw
import numpy as np
from PIL import Image
import ctypes

# ---------- VARIABLES GLOBALES ----------
rotation_x = 0.0
rotation_y = 0.0
scale = 1.0
mouse_button_pressed = False
last_mouse_x = 0
last_mouse_y = 0
wall_texture_id = None  # textura de paredes
roof_texture_id = None  # textura para todos los tejados
pan_x = 0.0
pan_y = 0.0
middle_mouse_pressed = False


# ---------- TEXTURA ----------
def load_texture(path):
    global wall_texture_id
    img = Image.open(path).transpose(Image.FLIP_TOP_BOTTOM)
    img_data = img.convert("RGBA").tobytes()
    width, height = img.size

    wall_texture_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, wall_texture_id)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0,
                 GL_RGBA, GL_UNSIGNED_BYTE, img_data)
    glGenerateMipmap(GL_TEXTURE_2D)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glBindTexture(GL_TEXTURE_2D, 0)

def load_roof_texture(path):
    global roof_texture_id
    img = Image.open(path).transpose(Image.FLIP_TOP_BOTTOM)
    img_data = img.convert("RGBA").tobytes()
    width, height = img.size

    roof_texture_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, roof_texture_id)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0,
                 GL_RGBA, GL_UNSIGNED_BYTE, img_data)
    glGenerateMipmap(GL_TEXTURE_2D)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glBindTexture(GL_TEXTURE_2D, 0)

# ---------- CUBO CON TEXTURA ----------
def draw_cube(x, y, z, width, height, depth):
    global wall_texture_id
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, wall_texture_id)

    glBegin(GL_QUADS)
    # Frente
    glTexCoord2f(0, 0); glVertex3f(x, y, z)
    glTexCoord2f(1, 0); glVertex3f(x + width, y, z)
    glTexCoord2f(1, 1); glVertex3f(x + width, y + height, z)
    glTexCoord2f(0, 1); glVertex3f(x, y + height, z)
    # Atrás
    glTexCoord2f(0, 0); glVertex3f(x, y, z - depth)
    glTexCoord2f(1, 0); glVertex3f(x + width, y, z - depth)
    glTexCoord2f(1, 1); glVertex3f(x + width, y + height, z - depth)
    glTexCoord2f(0, 1); glVertex3f(x, y + height, z - depth)
    # Izquierda
    glTexCoord2f(0, 0); glVertex3f(x, y, z)
    glTexCoord2f(1, 0); glVertex3f(x, y, z - depth)
    glTexCoord2f(1, 1); glVertex3f(x, y + height, z - depth)
    glTexCoord2f(0, 1); glVertex3f(x, y + height, z)
    # Derecha
    glTexCoord2f(0, 0); glVertex3f(x + width, y, z)
    glTexCoord2f(1, 0); glVertex3f(x + width, y, z - depth)
    glTexCoord2f(1, 1); glVertex3f(x + width, y + height, z - depth)
    glTexCoord2f(0, 1); glVertex3f(x + width, y + height, z)
    # Abajo
    glTexCoord2f(0, 0); glVertex3f(x, y, z)
    glTexCoord2f(1, 0); glVertex3f(x + width, y, z)
    glTexCoord2f(1, 1); glVertex3f(x + width, y, z - depth)
    glTexCoord2f(0, 1); glVertex3f(x, y, z - depth)
    # Arriba
    glTexCoord2f(0, 0); glVertex3f(x, y + height, z)
    glTexCoord2f(1, 0); glVertex3f(x + width, y + height, z)
    glTexCoord2f(1, 1); glVertex3f(x + width, y + height, z - depth)
    glTexCoord2f(0, 1); glVertex3f(x, y + height, z - depth)
    glEnd()

    glBindTexture(GL_TEXTURE_2D, 0)
    glDisable(GL_TEXTURE_2D)

# ---------- PIRÁMIDE (techos rojos) ----------
def draw_pyramid(x, y, z, base_width, base_depth, height):
    global roof_texture_id
    if roof_texture_id:
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, roof_texture_id)
    else:
        glDisable(GL_TEXTURE_2D)
        glColor3f(1, 0.5, 0.5)  # color por defecto

    # Lados triangulares
    glBegin(GL_TRIANGLES)
    glTexCoord2f(0.5, 1); glVertex3f(x, y + height, z - base_depth/2)
    glTexCoord2f(1, 0); glVertex3f(x + base_width/2, y, z)
    glTexCoord2f(0, 0); glVertex3f(x - base_width/2, y, z)

    glTexCoord2f(0.5, 1); glVertex3f(x, y + height, z - base_depth/2)
    glTexCoord2f(1, 0); glVertex3f(x + base_width/2, y, z)
    glTexCoord2f(0, 0); glVertex3f(x + base_width/2, y, z - base_depth)

    glTexCoord2f(0.5, 1); glVertex3f(x, y + height, z - base_depth/2)
    glTexCoord2f(1, 0); glVertex3f(x - base_width/2, y, z)
    glTexCoord2f(0, 0); glVertex3f(x - base_width/2, y, z - base_depth)

    glTexCoord2f(0.5, 1); glVertex3f(x, y + height, z - base_depth/2)
    glTexCoord2f(1, 0); glVertex3f(x + base_width/2, y, z - base_depth)
    glTexCoord2f(0, 0); glVertex3f(x - base_width/2, y, z - base_depth)
    glEnd()

    # Base
    glBegin(GL_QUADS)
    glTexCoord2f(0, 0); glVertex3f(x + base_width/2, y, z)
    glTexCoord2f(1, 0); glVertex3f(x - base_width/2, y, z)
    glTexCoord2f(1, 1); glVertex3f(x - base_width/2, y, z - base_depth)
    glTexCoord2f(0, 1); glVertex3f(x + base_width/2, y, z - base_depth)
    glEnd()

    if roof_texture_id:
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_TEXTURE_2D)

# ---------- VENTANAS Y PUERTAS ----------
def draw_windows_and_doors():
    glColor3f(0, 0, 0)
    glBegin(GL_QUADS)
    glVertex3f(-1.5, -2.0, 0.1)
    glVertex3f(-0.5, -2.0, 0.1)
    glVertex3f(-0.5, -1.0, 0.1)
    glVertex3f(-1.5, -1.0, 0.1)
    glEnd()
    glBegin(GL_QUADS)
    glVertex3f(-1.0, 0.0, 0.1)
    glVertex3f(-0.5, 0.0, 0.1)
    glVertex3f(-0.5, 0.5, 0.1)
    glVertex3f(-1.0, 0.5, 0.1)
    glEnd()

# ---------- TRANSFORMACIONES ----------
def key_callback(window, key, scancode, action, mods):
    global rotation_x, rotation_y, scale
    if action == glfw.PRESS or action == glfw.REPEAT:
        if key == glfw.KEY_UP: rotation_x += 5.0
        elif key == glfw.KEY_DOWN: rotation_x -= 5.0
        elif key == glfw.KEY_LEFT: rotation_y -= 5.0
        elif key == glfw.KEY_RIGHT: rotation_y += 5.0
        elif key == glfw.KEY_EQUAL: scale += 0.1
        elif key == glfw.KEY_MINUS: scale -= 0.1

def mouse_button_callback(window, button, action, mods):
    global mouse_button_pressed, middle_mouse_pressed
    if button == glfw.MOUSE_BUTTON_LEFT:
        mouse_button_pressed = (action == glfw.PRESS)
    elif button == glfw.MOUSE_BUTTON_MIDDLE:
        middle_mouse_pressed = (action == glfw.PRESS)

def scroll_callback(window, xoffset, yoffset):
    global scale
    scale += yoffset * 0.1  # yoffset es positivo o negativo según la dirección del scroll
    if scale < 0.1:         # evita que el modelo desaparezca
        scale = 0.1

def mouse_move_callback(window, x, y):
    global last_mouse_x, last_mouse_y
    global rotation_x, rotation_y, pan_x, pan_y
    if mouse_button_pressed:  # rotación
        dx = x - last_mouse_x
        dy = y - last_mouse_y
        rotation_y += dx * 0.2
        rotation_x += dy * 0.2
    elif middle_mouse_pressed:  # desplazamiento
        dx = x - last_mouse_x
        dy = y - last_mouse_y
        pan_x += dx * 0.01  # ajusta velocidad
        pan_y -= dy * 0.01  # invertir eje Y
    last_mouse_x = x
    last_mouse_y = y
# ---------- MODELO 3D ----------
def draw_model():
    glLoadIdentity()
    gluLookAt(0, 0, 10, 0, 0, 0, 0, 1, 0)
    glTranslatef(pan_x, pan_y, 0)  # aplica el desplazamiento con el click central
    glTranslatef(0, -1, 0)
    glRotatef(rotation_x, 1, 0, 0)
    glRotatef(rotation_y, 0, 1, 0)
    glScalef(scale, scale, scale)

    # Paredes con textura
    draw_cube(-1.5, -2.0, 0, 3, 4, 2)
    draw_cube(-1.0, 2.0, 0, 2, 2, 1.5)
    draw_cube(1.5, -2.0, -1, 3, 2, 2)
    draw_cube(0.5, 0.0, -0.5, 1.5, 1.5, 1)

    # Techos rojos
    glColor3f(1, 0.5, 0.5)
    draw_pyramid(0, 4.0, 0, 2, 1.5, 1.5)
    draw_pyramid(3.0, 0.0, -1, 3, 2, 1.0)
    draw_pyramid(1.25, 1.5, -0.5, 1.5, 1, 0.8)

    # Ventanas y puertas
    draw_windows_and_doors()

    # Wireframe encima
    glEnable(GL_POLYGON_OFFSET_LINE)
    glPolygonOffset(-1, -1)
    glColor3f(0, 0, 0)
    glLineWidth(2)
    glPushMatrix()
    glScalef(1.01, 1.01, 1.01)
    glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
    draw_cube(-1.5, -2.0, 0, 3, 4, 2)
    draw_cube(-1.0, 2.0, 0, 2, 2, 1.5)
    draw_pyramid(0, 4.0, 0, 2, 1.5, 1.5)
    draw_cube(1.5, -2.0, -1, 3, 2, 2)
    draw_pyramid(3.0, 0.0, -1, 3, 2, 1.0)
    draw_cube(0.5, 0.0, -0.5, 1.5, 1.5, 1)
    draw_pyramid(1.25, 1.5, -0.5, 1.5, 1, 0.8)
    glPopMatrix()
    glDisable(GL_POLYGON_OFFSET_LINE)
    glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

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
    vert = shaders.compileShader(vert_src, GL_VERTEX_SHADER)
    frag = shaders.compileShader(frag_src, GL_FRAGMENT_SHADER)
    prog = shaders.compileProgram(vert, frag)
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
# ---------- MAIN ---------- 
def main():
    if not glfw.init(): 
        return
    window = glfw.create_window(800, 600, "Modelo 3D con Textura", None, None)
    if not window:
        glfw.terminate()
        return
    glfw.make_context_current(window)

    # Inicializar shader de fondo
    init_gradient_shader()

    glEnable(GL_DEPTH_TEST)
    glClearColor(0, 0, 0, 1)
    load_roof_texture(r"D:\nicol\Documentos\Python\Tarea 3 CV\tejado.jpg")

    load_texture(r"D:\nicol\Documentos\Python\Tarea 3 CV\image.jpg")

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(-5, 5, -5, 5, 1, 20)
    glMatrixMode(GL_MODELVIEW)

    glfw.set_key_callback(window, key_callback)
    glfw.set_scroll_callback(window, scroll_callback)
    glfw.set_mouse_button_callback(window, mouse_button_callback)
    glfw.set_cursor_pos_callback(window, mouse_move_callback)

    while not glfw.window_should_close(window):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # --- FONDO DEGRADADO ---
        draw_animated_gradient()

        # --- MODELO 3D ---
        glUseProgram(0)  # desactivar cualquier shader activo antes de dibujar tu modelo
        glEnable(GL_TEXTURE_2D)  # si usas texturas
        glColor3f(1.0, 1.0, 1.0)  # asegura que lo blanco se vea blanco
        draw_model()
        glDisable(GL_TEXTURE_2D)

        glfw.swap_buffers(window)
        glfw.poll_events()

    glfw.terminate()


if __name__ == "__main__":
    main()
