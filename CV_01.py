from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GL import shaders
from PIL import Image
import glfw
import numpy as np
import ctypes
import os
import math

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
show_axes = True 

# --- AJUSTES DE POSICIÓN Y ESCALA ---
# Escala para que el tamaño coincida con la casa
ESCALA_VENTANAS = 4.0 

# SI LAS VENTANAS FLOTAN O ESTÁN HUNDIDAS, AJUSTA ESTE VALOR.
# La pared está en el eje Y (Fondo).
# Si flotan hacia afuera, hazlo negativo (ej. -0.5).
# Si están hundidas, hazlo positivo (ej. 0.5).
OFFSET_VENTANAS_X = 0.0 
OFFSET_VENTANAS_Y = 0.0
OFFSET_VENTANAS_Z = 0.0

# Listas de visualización
stl_walls_list = None
stl_roof_list = None
stl_ground_list = None 

# Identificadores de Textura
wall_texture_id = None
roof_texture_id = None
grass_texture_id = None 

# ---------- CARGA DE STL ----------
def load_stl(file_path):
    global stl_walls_list, stl_roof_list, stl_ground_list
    all_triangles = []
    min_z = float('inf'); max_z = float('-inf')
    
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
                    if v[2] < min_z: min_z = v[2]
                    if v[2] > max_z: max_z = v[2]
                elif parts[0] == 'endfacet':
                    if len(triangle_buffer) == 3:
                        all_triangles.append((current_normal, triangle_buffer))
    except FileNotFoundError:
        print(f"Error: No se encontró {file_path}")
        return

    # --- CLASIFICACIÓN ---
    walls_geometry = []
    roof_geometry = []
    ground_geometry = []
    
    total_height = max_z - min_z
    ground_threshold = min_z + (total_height * 0.15)
    
    # SOLUCIÓN CRÍTICA: Umbral de Altura del Tejado. 
    # Usamos 85%. Solo el 15% superior del modelo (la pirámide) es candidato a tejado inclinado.
    roof_height_threshold = min_z + (total_height * 0.85) 
    
    for normal, verts in all_triangles:
        avg_z = sum([v[2] for v in verts]) / 3.0
        
        # 1. ¿Superficie Horizontal (Techo/Pasto)?
        if abs(normal[2]) > 0.5: 
            if avg_z < ground_threshold: 
                ground_geometry.append((normal, verts))
            else: 
                roof_geometry.append((normal, verts))
        
        # 2. ¿Superficie Inclinada/Vertical (Pared)?
        else:
            # Si el triángulo inclinado está MUY ARRIBA (en el 15% superior),
            # lo forzamos a ser techo.
            if avg_z > roof_height_threshold:
                roof_geometry.append((normal, verts))
            else:
                # Si está abajo o en el centro (prisma), es una pared normal.
                walls_geometry.append((normal, verts))

    stl_walls_list = glGenLists(1); glNewList(stl_walls_list, GL_COMPILE); glBegin(GL_TRIANGLES)
    tex_scale = 5.0 
    for normal, verts in walls_geometry:
        glNormal3f(*normal)
        xs=[v[0] for v in verts]; ys=[v[1] for v in verts]; zs=[v[2] for v in verts]
        sx=max(xs)-min(xs); sy=max(ys)-min(ys); sz=max(zs)-min(zs)
        if sx<=sy and sx<=sz: m='YZ'
        elif sy<=sx and sy<=sz: m='XZ'
        else: m='XY'
        for v in verts:
            if m=='YZ': glTexCoord2f(v[1]/tex_scale, v[2]/tex_scale)
            elif m=='XZ': glTexCoord2f(v[0]/tex_scale, v[2]/tex_scale)
            else: glTexCoord2f(v[0]/tex_scale, v[1]/tex_scale)
            glVertex3f(*v)
    glEnd(); glEndList()

    stl_roof_list = glGenLists(1); glNewList(stl_roof_list, GL_COMPILE); glBegin(GL_TRIANGLES)
    for normal, verts in roof_geometry:
        glNormal3f(*normal)
        for v in verts: glTexCoord2f(v[0]/5.0, v[1]/5.0); glVertex3f(*v)
    glEnd(); glEndList()

    stl_ground_list = glGenLists(1); glNewList(stl_ground_list, GL_COMPILE); glBegin(GL_TRIANGLES)
    for normal, verts in ground_geometry:
        glNormal3f(*normal)
        for v in verts: glTexCoord2f(v[0]/5.0, v[1]/5.0); glVertex3f(*v)
    glEnd(); glEndList()

# ---------- TEXTURAS ----------
def _load_img_generic(path):
    try:
        img = Image.open(path).transpose(1)
        img_data = img.convert("RGBA").tobytes()
        w, h = img.size
        tid = glGenTextures(1); glBindTexture(GL_TEXTURE_2D, tid)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
        glGenerateMipmap(GL_TEXTURE_2D)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT) 
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glBindTexture(GL_TEXTURE_2D, 0)
        return tid
    except: return None

def load_textures_all(base_path):
    global wall_texture_id, roof_texture_id, grass_texture_id
    wall_texture_id = _load_img_generic(os.path.join(base_path, "image.jpg"))
    roof_texture_id = _load_img_generic(os.path.join(base_path, "tejado.jpg"))
    grass_texture_id = _load_img_generic(os.path.join(base_path, "pasto.jpg"))

# ---------- DIBUJO DE DETALLES (VERSIÓN SIMPLE Y LIMPIA) ----------

def draw_simple_window(points):
    # 1. Aplicar ESCALA y OFFSET a los puntos
    scaled_points = []
    for p in points:
        nx = p[0] * ESCALA_VENTANAS + OFFSET_VENTANAS_X
        ny = p[1] * ESCALA_VENTANAS + OFFSET_VENTANAS_Y
        nz = p[2] * ESCALA_VENTANAS + OFFSET_VENTANAS_Z
        scaled_points.append((nx, ny, nz))
    
    # 2. Dibujar VIDRIO (Un solo quad)
    glColor3f(0.2, 0.3, 0.5) 
    glBegin(GL_QUADS)
    for p in scaled_points: glVertex3fv(p)
    glEnd()
    
    # 3. Dibujar MARCO (Líneas blancas gruesas alrededor)
    glColor3f(0.9, 0.9, 0.9)
    glLineWidth(3.0)
    glBegin(GL_LINE_LOOP)
    for p in scaled_points: glVertex3fv(p)
    glEnd()
    
    # 4. CRUZ (Divisiones)
    p0, p1, p2, p3 = np.array(scaled_points[0]), np.array(scaled_points[1]), np.array(scaled_points[2]), np.array(scaled_points[3])
    mid_bottom = (p0 + p1) / 2
    mid_top = (p2 + p3) / 2
    mid_right = (p1 + p2) / 2
    mid_left = (p3 + p0) / 2
    
    glBegin(GL_LINES)
    glVertex3fv(mid_bottom); glVertex3fv(mid_top)
    glVertex3fv(mid_left); glVertex3fv(mid_right)
    glEnd()
    glLineWidth(1.0)

def draw_simple_garage(points):
    scaled_points = []
    for p in points:
        nx = p[0] * ESCALA_VENTANAS + OFFSET_VENTANAS_X
        ny = p[1] * ESCALA_VENTANAS + OFFSET_VENTANAS_Y
        nz = p[2] * ESCALA_VENTANAS + OFFSET_VENTANAS_Z
        scaled_points.append((nx, ny, nz))
        
    glColor3f(0.3, 0.3, 0.35)
    glBegin(GL_QUADS)
    for p in scaled_points: glVertex3fv(p)
    glEnd()
    
    # Rayas
    glColor3f(0.2, 0.2, 0.25)
    glLineWidth(2.0)
    steps = 5
    
    p0, p1, p2, p3 = np.array(scaled_points[0]), np.array(scaled_points[1]), np.array(scaled_points[2]), np.array(scaled_points[3])
    v_left = p3 - p0
    v_right = p2 - p1
    
    glBegin(GL_LINES)
    for i in range(1, steps):
        f = i / steps
        start = p0 + v_left * f
        end = p1 + v_right * f
        glVertex3fv(start); glVertex3fv(end)
    glEnd()
    glLineWidth(1.0)

def draw_all_custom_elements():
    glDisable(GL_TEXTURE_2D)
    # ELIMINADO glDisable(GL_DEPTH_TEST) - Permitimos que el muro oculte los objetos
    glDisable(GL_LIGHTING)
    
    draw_simple_window([(3,2,4.5), (1,2,4.5), (1,2,3), (3,2,3)])
    draw_simple_window([(2.5,1,7), (1.5,1,7), (1.5,1,7.5), (2.5,1,7.5)])
    draw_simple_window([(3,2,4.5), (1,2,4.5), (1,2,3), (3,2,3)])
    draw_simple_window([(-4, -0.5 , 2.7), (-4,-0.5 ,3.3 ), (-4,0.5 , 3.3) , (-4,0.5 ,2.7 )])
    draw_simple_window([(1,0.5,7.5), (1,-0.5,7.5), (1,-0.5,7), (1,0.5,7)])
    # Corregido el error de sintaxis en el 2do punto de la V6
    draw_simple_window([(-1, 1.83814, 3.24693), (-1, 1.83814, 2.62139), (-3, 1.83814, 2.62139), (-3, 1.83814, 3.24693)])
    draw_simple_garage([(-1,2,0.5), (-3,2,0.5), (-3,2,2), (-1,2,2)])

    glEnable(GL_LIGHTING)
    # ELIMINADO glEnable(GL_DEPTH_TEST) - Ya está activo globalmente
    glEnable(GL_TEXTURE_2D)
    glColor3f(1,1,1)

# ---------- DIBUJO ESCENA ----------
def draw_model():
    glLoadIdentity()
    gluLookAt(0, 0, 10, 0, 0, 0, 0, 1, 0)
    glTranslatef(pan_x, pan_y, 0)
    glRotatef(rotation_x, 1, 0, 0); glRotatef(rotation_y, 0, 1, 0)
    glScalef(scale, scale, scale)

    if show_axes:
        glDisable(GL_DEPTH_TEST); glBegin(GL_LINES)
        glColor3f(1,0,0); glVertex3f(-15,0,0); glVertex3f(15,0,0)
        glColor3f(0,1,0); glVertex3f(0,-15,0); glVertex3f(0,15,0)
        glColor3f(0,0,1); glVertex3f(0,0,-15); glVertex3f(0,0,15)
        glEnd(); glEnable(GL_DEPTH_TEST)

    glPushMatrix()
    glRotatef(-90, 1, 0, 0)
    glScalef(0.1, 0.1, 0.1) 
    
    # 1. Dibujar la casa (SÓLIDO)
    glDisable(GL_LIGHTING) 
    glColor3f(1, 1, 1)
    
    if stl_walls_list:
        if wall_texture_id: glEnable(GL_TEXTURE_2D); glBindTexture(GL_TEXTURE_2D, wall_texture_id)
        else: glDisable(GL_TEXTURE_2D); glColor3f(0.7,0.7,0.7)
        glCallList(stl_walls_list)

    if stl_roof_list:
        if roof_texture_id: glEnable(GL_TEXTURE_2D); glBindTexture(GL_TEXTURE_2D, roof_texture_id)
        else: glDisable(GL_TEXTURE_2D); glColor3f(0.8,0.4,0.4)
        glCallList(stl_roof_list)

    if stl_ground_list:
        if grass_texture_id: glEnable(GL_TEXTURE_2D); glBindTexture(GL_TEXTURE_2D, grass_texture_id)
        else: glDisable(GL_TEXTURE_2D); glColor3f(0.2,0.8,0.2)
        glCallList(stl_ground_list)
        
    glEnable(GL_LIGHTING) 
    
    glBindTexture(GL_TEXTURE_2D, 0); glDisable(GL_TEXTURE_2D)
    
    # 2. Dibujar ventanas AL FINAL
    draw_all_custom_elements()
    
    glPopMatrix()

# ---------- INPUTS / UTILS ----------
def key_callback(w, k, s, a, m):
    global rotation_x, rotation_y, scale, show_axes
    if a==glfw.PRESS or a==glfw.REPEAT:
        if k==glfw.KEY_UP: rotation_x+=5
        elif k==glfw.KEY_DOWN: rotation_x-=5
        elif k==glfw.KEY_LEFT: rotation_y-=5
        elif k==glfw.KEY_RIGHT: rotation_y+=5
        elif k==glfw.KEY_EQUAL: scale += 0.1
        elif k == glfw.KEY_MINUS: scale -= 0.1
        elif k == glfw.KEY_A and a==glfw.PRESS: show_axes=not show_axes

def mouse_move_callback(w, x, y):
    global last_mouse_x, last_mouse_y, rotation_x, rotation_y, pan_x, pan_y
    if mouse_button_pressed: rotation_y+=(x-last_mouse_x)*0.2; rotation_x+=(y-last_mouse_y)*0.2
    elif middle_mouse_pressed: pan_x+=(x-last_mouse_x)*0.01; pan_y-=(y-last_mouse_y)*0.01
    last_mouse_x=x; last_mouse_y=y

# SHADER
_gp=None; _gv=None; _ut=None; _ur=None
def create_shader():
    global _gp, _gv, _ut, _ur
    v="#version 330 core\nlayout(location=0) in vec2 a;out vec2 v;void main(){v=(a+1.0)/2.0;gl_Position=vec4(a,0,1);}"
    f="""#version 330 core
    in vec2 v;out vec4 c;uniform float t;
    void main(){vec2 u=v;float w=sin((u.y*10.+t)+(sin(u.x*6.+t*0.7)*0.8))*0.5+0.5;
    c=vec4(mix(vec3(0.7,1,0.2),vec3(0.05,0.75,0.45),smoothstep(0.,1.,u.y+w*0.2)),1);}"""
    try:
        vs=shaders.compileShader(v,GL_VERTEX_SHADER); fs=shaders.compileShader(f,GL_FRAGMENT_SHADER)
        _gp=shaders.compileProgram(vs,fs)
        q=np.array([-1,-1, 1,-1, 1,1, -1,-1, 1,1, -1,1],dtype=np.float32)
        _gv=glGenVertexArrays(1); glBindVertexArray(_gv)
        b=glGenBuffers(1); glBindBuffer(GL_ARRAY_BUFFER,b); glBufferData(GL_ARRAY_BUFFER,q.nbytes,q,GL_STATIC_DRAW)
        glEnableVertexAttribArray(0); glVertexAttribPointer(0,2,GL_FLOAT,GL_FALSE,8,ctypes.c_void_p(0))
        _ut=glGetUniformLocation(_gp,"t")
    except: pass

def draw_bg():
    if _gp:
        glDisable(GL_DEPTH_TEST); glDepthMask(GL_FALSE); glUseProgram(_gp)
        if _ut!=-1: glUniform1f(_ut, glfw.get_time())
        glBindVertexArray(_gv); glDrawArrays(GL_TRIANGLES,0,6); glUseProgram(0)
        glDepthMask(GL_TRUE); glEnable(GL_DEPTH_TEST)

# ---------- MAIN ----------
def main():
    if not glfw.init(): return
    window = glfw.create_window(800, 600, "Final - Sin Sombras", None, None)
    if not window: glfw.terminate(); return
    glfw.make_context_current(window)
    
    glfw.set_key_callback(window, key_callback)
    glfw.set_cursor_pos_callback(window, mouse_move_callback)
    glfw.set_mouse_button_callback(window, lambda w,b,a,m: globals().update(mouse_button_pressed=(b==0 and a==1), middle_mouse_pressed=(b==2 and a==1)))
    glfw.set_scroll_callback(window, lambda w,x,y: globals().update(scale=max(0.1, scale+y*0.1)))

    create_shader()
    glEnable(GL_DEPTH_TEST); glEnable(GL_LIGHTING); glEnable(GL_LIGHT0); glEnable(GL_COLOR_MATERIAL)
    glLightfv(GL_LIGHT0, GL_POSITION, (10, 10, 10, 1)); glClearColor(0,0,0,1)

    ruta = r"D:\nicol\Documentos\GitHub\CV_03"
    load_textures_all(ruta)
    load_stl(os.path.join(ruta, "Final.stl"))

    while not glfw.window_should_close(window):
        width, height = glfw.get_framebuffer_size(window)
        if height == 0: height = 1 
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION); glLoadIdentity()
        aspect = width / height
        glOrtho(-5 * aspect, 5 * aspect, -5, 5, 1, 100)
        glMatrixMode(GL_MODELVIEW)

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        draw_bg()
        draw_model()
        
        glfw.swap_buffers(window); glfw.poll_events()
    glfw.terminate()

if __name__ == "__main__": main()