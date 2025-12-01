from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GL import shaders
from PIL import Image
import glfw
import numpy as np
import ctypes
import os

# ---------- VARIABLES GLOBALES ----------
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
show_axes = True 

# Listas de visualización
stl_walls_list = None
stl_roof_list = None
stl_ground_list = None 

# Identificadores de Textura
wall_texture_id = None
roof_texture_id = None
grass_texture_id = None 

# ---------- FUNCIONES DE CARGA ----------

def load_stl(file_path):
    """
    Carga STL con clasificación inteligente de PASTO.
    Usa un porcentaje de la altura total para encontrar el suelo,
    evitando que el prisma base sea confundido con un techo.
    """
    global stl_walls_list, stl_roof_list, stl_ground_list
    
    all_triangles = []
    min_z = float('inf') 
    max_z = float('-inf') # <--- Necesitamos saber la altura máxima
    
    try:
        with open(file_path, 'r') as f:
            triangle_buffer = [] 
            current_normal = (0, 0, 0)
            
            for line in f:
                parts = line.strip().split()
                if not parts: continue
                    
                if parts[0] == 'facet' and parts[1] == 'normal':
                    nx, ny, nz = float(parts[2]), float(parts[3]), float(parts[4])
                    current_normal = (nx, ny, nz)
                    triangle_buffer = []

                elif parts[0] == 'vertex':
                    v = (float(parts[1]), float(parts[2]), float(parts[3]))
                    triangle_buffer.append(v)
                    # Actualizamos límites de altura
                    if v[2] < min_z: min_z = v[2]
                    if v[2] > max_z: max_z = v[2]
                
                elif parts[0] == 'endfacet':
                    if len(triangle_buffer) == 3:
                        all_triangles.append((current_normal, triangle_buffer))

    except FileNotFoundError:
        print(f"Error: No se encontró {file_path}")
        return

    # --- CLASIFICACIÓN ROBUSTA ---
    walls_geometry = []
    roof_geometry = []
    ground_geometry = []
    
    total_height = max_z - min_z
    # El umbral ahora es el 20% de la altura total. 
    # Todo lo plano que esté en ese 20% inferior será PASTO.
    ground_threshold = min_z + (total_height * 0.20)
    
    print(f"Altura Modelo: {min_z:.2f} a {max_z:.2f}. Umbral Pasto: < {ground_threshold:.2f}")
    
    for normal, verts in all_triangles:
        avg_z = sum([v[2] for v in verts]) / 3.0
        
        # 1. ¿Es una superficie horizontal (plana)?
        if abs(normal[2]) > 0.5: 
            # 2. ¿Está en la parte baja del modelo?
            if avg_z < ground_threshold:
                ground_geometry.append((normal, verts)) # Es el prisma del suelo -> Pasto
            else:
                roof_geometry.append((normal, verts))   # Es alto -> Techo
        else:
            # Es vertical -> Pared (del prisma o de la casa)
            walls_geometry.append((normal, verts))

    # --- GENERACIÓN DE LISTAS ---

    # 1. PAREDES (Span Logic)
    stl_walls_list = glGenLists(1)
    glNewList(stl_walls_list, GL_COMPILE)
    glBegin(GL_TRIANGLES)
    tex_scale = 5.0 
    for normal, verts in walls_geometry:
        glNormal3f(*normal)
        xs = [v[0] for v in verts]; ys = [v[1] for v in verts]; zs = [v[2] for v in verts]
        span_x = max(xs)-min(xs); span_y = max(ys)-min(ys); span_z = max(zs)-min(zs)
        
        # Lógica geométrica para evitar estiramiento en paredes
        if span_x <= span_y and span_x <= span_z: mapping = 'YZ'
        elif span_y <= span_x and span_y <= span_z: mapping = 'XZ'
        else: mapping = 'XY'
             
        for v in verts:
            if mapping == 'YZ': glTexCoord2f(v[1]/tex_scale, v[2]/tex_scale)
            elif mapping == 'XZ': glTexCoord2f(v[0]/tex_scale, v[2]/tex_scale)
            else: glTexCoord2f(v[0]/tex_scale, v[1]/tex_scale)
            glVertex3f(*v)
    glEnd()
    glEndList()

    # 2. TECHOS
    stl_roof_list = glGenLists(1)
    glNewList(stl_roof_list, GL_COMPILE)
    glBegin(GL_TRIANGLES)
    for normal, verts in roof_geometry:
        glNormal3f(*normal)
        for v in verts:
            glTexCoord2f(v[0]/5.0, v[1]/5.0)
            glVertex3f(*v)
    glEnd()
    glEndList()

    # 3. SUELO (PASTO)
    stl_ground_list = glGenLists(1)
    glNewList(stl_ground_list, GL_COMPILE)
    glBegin(GL_TRIANGLES)
    for normal, verts in ground_geometry:
        glNormal3f(*normal)
        for v in verts:
            glTexCoord2f(v[0]/5.0, v[1]/5.0)
            glVertex3f(*v)
    glEnd()
    glEndList()
    
    print(f"Clasificación: {len(walls_geometry)} paredes, {len(roof_geometry)} techos, {len(ground_geometry)} pasto.")

def _load_img_generic(path):
    try:
        img = Image.open(path).transpose(1)
        img_data = img.convert("RGBA").tobytes()
        w, h = img.size
        tid = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tid)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
        glGenerateMipmap(GL_TEXTURE_2D)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT) 
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glBindTexture(GL_TEXTURE_2D, 0)
        print(f"Textura cargada: {os.path.basename(path)}")
        return tid
    except Exception as e:
        print(f"Error textura {path}: {e}")
        return None

def load_textures_all(base_path):
    global wall_texture_id, roof_texture_id, grass_texture_id
    wall_texture_id = _load_img_generic(os.path.join(base_path, "image.jpg"))
    roof_texture_id = _load_img_generic(os.path.join(base_path, "tejado.jpg"))
    grass_texture_id = _load_img_generic(os.path.join(base_path, "pasto.jpg"))

# ---------- DIBUJO ----------

def draw_axes(length=10.0):
    glDisable(GL_TEXTURE_2D); glLineWidth(3.0); glBegin(GL_LINES)
    glColor3f(1,0,0); glVertex3f(-length,0,0); glVertex3f(length,0,0)
    glColor3f(0,1,0); glVertex3f(0,-length,0); glVertex3f(0,length,0)
    glColor3f(0,0,1); glVertex3f(0,0,-length); glVertex3f(0,0,length)
    glEnd(); glLineWidth(1.0); glColor3f(1,1,1)

def draw_model():
    glLoadIdentity()
    gluLookAt(0, 0, 10, 0, 0, 0, 0, 1, 0)
    glTranslatef(pan_x, pan_y, 0)
    glRotatef(rotation_x, 1, 0, 0); glRotatef(rotation_y, 0, 1, 0)
    glScalef(scale, scale, scale)

    if show_axes: glDisable(GL_DEPTH_TEST); draw_axes(15.0); glEnable(GL_DEPTH_TEST)

    glPushMatrix()
    glRotatef(-90, 1, 0, 0)
    glScalef(0.1, 0.1, 0.1) 
    glColor3f(1, 1, 1)

    # 1. Paredes
    if stl_walls_list:
        if wall_texture_id: glEnable(GL_TEXTURE_2D); glBindTexture(GL_TEXTURE_2D, wall_texture_id)
        else: glDisable(GL_TEXTURE_2D); glColor3f(0.7, 0.7, 0.7)
        glCallList(stl_walls_list)

    # 2. Techos
    if stl_roof_list:
        if roof_texture_id: glEnable(GL_TEXTURE_2D); glBindTexture(GL_TEXTURE_2D, roof_texture_id)
        else: glDisable(GL_TEXTURE_2D); glColor3f(0.8, 0.4, 0.4)
        glCallList(stl_roof_list)

    # 3. Pasto
    if stl_ground_list:
        if grass_texture_id: glEnable(GL_TEXTURE_2D); glBindTexture(GL_TEXTURE_2D, grass_texture_id)
        else: glDisable(GL_TEXTURE_2D); glColor3f(0.2, 0.8, 0.2) # Verde si falla la imagen
        glCallList(stl_ground_list)

    glBindTexture(GL_TEXTURE_2D, 0); glDisable(GL_TEXTURE_2D)
    glPopMatrix()

# ---------- INPUTS Y SHADERS ----------
def key_callback(window, key, scancode, action, mods):
    global rotation_x, rotation_y, scale, show_axes
    if action == glfw.PRESS or action == glfw.REPEAT:
        if key == glfw.KEY_UP: rotation_x += 5.0
        elif key == glfw.KEY_DOWN: rotation_x -= 5.0
        elif key == glfw.KEY_LEFT: rotation_y -= 5.0
        elif key == glfw.KEY_RIGHT: rotation_y += 5.0
        elif key == glfw.KEY_EQUAL: scale += 0.1
        elif key == glfw.KEY_MINUS: scale -= 0.1
        elif key == glfw.KEY_A and action == glfw.PRESS: show_axes = not show_axes

def mouse_button_callback(window, button, action, mods):
    global mouse_button_pressed, middle_mouse_pressed
    if button == glfw.MOUSE_BUTTON_LEFT: mouse_button_pressed = (action == glfw.PRESS)
    elif button == glfw.MOUSE_BUTTON_MIDDLE: middle_mouse_pressed = (action == glfw.PRESS)

def scroll_callback(window, xoffset, yoffset):
    global scale; scale += yoffset * 0.1; 
    if scale < 0.1: scale = 0.1

def mouse_move_callback(window, x, y):
    global last_mouse_x, last_mouse_y, rotation_x, rotation_y, pan_x, pan_y
    if mouse_button_pressed:
        rotation_y += (x - last_mouse_x) * 0.2; rotation_x += (y - last_mouse_y) * 0.2
    elif middle_mouse_pressed:
        pan_x += (x - last_mouse_x) * 0.01; pan_y -= (y - last_mouse_y) * 0.01
    last_mouse_x = x; last_mouse_y = y

def framebuffer_size_callback(window, width, height):
    global window_width, window_height; window_width = width; window_height = height
    glViewport(0, 0, width, height); glMatrixMode(GL_PROJECTION); glLoadIdentity()
    aspect = width / height if height != 0 else 1.0
    glOrtho(-5 * aspect, 5 * aspect, -5, 5, 1, 100); glMatrixMode(GL_MODELVIEW)

_gradient_prog = None; _gradient_vao = None; _uniform_time = None; _uniform_res = None
def create_gradient_shader():
    global _gradient_prog, _gradient_vao, _uniform_time, _uniform_res
    vert_src = "#version 330 core\nlayout(location=0) in vec2 a;layout(location=1) in vec2 b;out vec2 v;void main(){v=b;gl_Position=vec4(a,0,1);}"
    frag_src = """#version 330 core
    in vec2 v;out vec4 f;uniform float u_time;uniform vec2 u_resolution;
    void main(){vec2 uv=v;float w=sin((uv.y*10.+u_time)+(sin(uv.x*6.+u_time*0.7)*0.8))*0.5+0.5;
    vec3 c=mix(vec3(0.7,1,0.2),vec3(0.05,0.75,0.45),smoothstep(0.0,1.0,uv.y+w*0.2));
    f=vec4(c,1);}"""
    try:
        vert = shaders.compileShader(vert_src, GL_VERTEX_SHADER); frag = shaders.compileShader(frag_src, GL_FRAGMENT_SHADER)
        prog = shaders.compileProgram(vert, frag)
        quad = np.array([-1,-1,0,0, 1,-1,1,0, 1,1,1,1, -1,-1,0,0, 1,1,1,1, -1,1,0,1], dtype=np.float32)
        vao = glGenVertexArrays(1); vbo = glGenBuffers(1)
        glBindVertexArray(vao); glBindBuffer(GL_ARRAY_BUFFER, vbo)
        glBufferData(GL_ARRAY_BUFFER, quad.nbytes, quad, GL_STATIC_DRAW)
        glEnableVertexAttribArray(0); glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 16, ctypes.c_void_p(0))
        glEnableVertexAttribArray(1); glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 16, ctypes.c_void_p(8))
        _gradient_prog = prog; _gradient_vao = vao
        _uniform_time = glGetUniformLocation(prog, "u_time"); _uniform_res = glGetUniformLocation(prog, "u_resolution")
    except: pass

def draw_animated_gradient():
    if _gradient_prog:
        glDisable(GL_DEPTH_TEST); glDepthMask(GL_FALSE); glUseProgram(_gradient_prog)
        if _uniform_time!=-1: glUniform1f(_uniform_time, glfw.get_time())
        glBindVertexArray(_gradient_vao); glDrawArrays(GL_TRIANGLES, 0, 6); glBindVertexArray(0)
        glUseProgram(0); glDepthMask(GL_TRUE); glEnable(GL_DEPTH_TEST)

# ---------- MAIN ----------
def main():
    if not glfw.init(): return
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3); glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_COMPAT_PROFILE)
    window = glfw.create_window(800, 600, "Visor 3D - Final", None, None)
    if not window: glfw.terminate(); return
    glfw.make_context_current(window)

    create_gradient_shader()
    glEnable(GL_DEPTH_TEST); glEnable(GL_LIGHTING); glEnable(GL_LIGHT0); glEnable(GL_COLOR_MATERIAL)
    glLightfv(GL_LIGHT0, GL_POSITION, (10, 10, 10, 1)); glClearColor(0,0,0,1)

    # --- RUTA DE TU PROYECTO ---
    ruta_carpeta = r"D:\nicol\Documentos\GitHub\CV_03"
    print(f"Directorio: {ruta_carpeta}")
    
    # Cargar TODO
    load_textures_all(ruta_carpeta)
    load_stl(os.path.join(ruta_carpeta, "Final.stl"))

    # Configs
    glfw.set_framebuffer_size_callback(window, framebuffer_size_callback)
    glfw.set_key_callback(window, key_callback); glfw.set_scroll_callback(window, scroll_callback)
    glfw.set_mouse_button_callback(window, mouse_button_callback); glfw.set_cursor_pos_callback(window, mouse_move_callback)
    glMatrixMode(GL_PROJECTION); glLoadIdentity(); glOrtho(-5*1.33, 5*1.33, -5, 5, 1, 100); glMatrixMode(GL_MODELVIEW)

    while not glfw.window_should_close(window):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        draw_animated_gradient()
        glUseProgram(0)
        draw_model()
        glfw.swap_buffers(window); glfw.poll_events()
    glfw.terminate()

if __name__ == "__main__":
    main()