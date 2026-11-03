"""Пристёгнутая к коляске отдельная модель GLB (подушка ROHO на сиденье Invacare 9000 XDT — art_tests/cushion_ref/):
общий код для кадров (blender_render.py, ключ spec "attach") и для модели игры (tripo_label.py, SPECS[...]["attach"]).
Исходник GLB не меняется; всё — при загрузке.

attach = dict(
    glb="art_tests/cushion_ref/cushion_model.glb",   # путь от корня проекта (или абсолютный)
    origin=(x, y, z),       # точка модели в её осях glTF (y вверх), которая встаёт в pos (подушка: центр низа основания)
    scale=262,              # мм игры на единицу glTF
    rot=(yaw, pitch, roll), # градусы, как rot у move в blender_frames: сначала roll (вокруг x), pitch (вокруг z), yaw (вокруг y)
    pos=(x, y, z),          # мм игры (x вперёд, y вверх, пол 0, z вбок, +z — правая сторона)
    edit=[...],             # правки в осях glTF ДО переноса, по порядку:
                            #   dict(box=((x0, x1), (y0, y1), (z0, z1)), clone=(dx, dy, dz)) — копия граней коробки со сдвигом
                            #   dict(box=..., flat=(ось 0|1|2, значение), col=(r, g, b)) — вершины коробки прижать к плоскости
                            #     (убрать торчащую деталь: лишний ниппель), грани коробки — матовые цвета col (0..1)
    mat=dict(col=(r, g, b), rough=0.8),   # необязательно: свой матовый материал вместо текстуры модели
    part="cushion", parts=[("valve", box), ...])   # для tripo_label: деталь игры (грань по центру в коробке glTF)
"""
import math, os
import numpy as np

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def glb_path(a):
    p = a["glb"]
    return p if os.path.isabs(p) else os.path.join(ROOT, p)


def attach_matrix(a):
    """4×4: координаты glTF (мир файла) -> мм игры."""
    yaw, pitch, roll = [math.radians(v) for v in (list(a.get("rot", (0, 0, 0))) + [0, 0, 0])[:3]]
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    Rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    Rz = np.array([[cp, -sp, 0], [sp, cp, 0], [0, 0, 1]])
    Ry = np.array([[cy, 0, -sy], [0, 1, 0], [sy, 0, cy]])     # как yaw в blender_render.move_parts
    M = np.eye(4)
    M[:3, :3] = Ry @ Rz @ Rx * float(a.get("scale", 1.0))
    M[:3, 3] = np.asarray(a.get("pos", (0, 0, 0)), float) - M[:3, :3] @ np.asarray(a.get("origin", (0, 0, 0)), float)
    return M


def in_box(P, box):
    m = np.ones(len(P), bool)
    for k in range(3):
        m &= (P[:, k] >= box[k][0]) & (P[:, k] <= box[k][1])
    return m


def edit_numpy(V, F, C, edits):
    """Правки edit для сетки V (glTF), F, C (цвет вершин 0..255) — для tripo_label. Возврат V, F, C."""
    V, F, C = V.copy(), F.copy(), C.copy()
    for e in edits or []:
        sel = in_box(V, e["box"])
        if e.get("clone") is not None:
            fm = sel[F].all(1)
            vi = np.unique(F[fm])
            remap = np.full(len(V), -1)
            remap[vi] = len(V) + np.arange(len(vi))
            V = np.vstack([V, V[vi] + np.asarray(e["clone"], float)])
            C = np.vstack([C, C[vi]])
            F = np.vstack([F, remap[F[fm]]])
        elif e.get("flat") is not None:
            ax, val = e["flat"]
            V[sel, int(ax)] = val
            if e.get("col") is not None:
                C[sel] = np.asarray(e["col"], float) * 255
    return V, F, C


# подушка ROHO (модель владельца, art_tests/cushion_ref/, параметры — attach_glb.py) на сиденье Invacare 9000 XDT (Бомм,
# задание «cushion»): 5×5 ячеек вверх, основание 1,68×1,60 ед. glTF -> 440×419 мм, низ — на стропе/трубах сиденья (y 512),
# зад — у спинки (x −268); у модели два ниппеля по серединам сторон: передний перенесён к правому углу, оба исходных прижаты
ROHO_XDT = dict(glb="art_tests/cushion_ref/cushion_model.glb", origin=(-0.11, -0.197, -0.11), scale=262, rot=(-90, 0, 0),
                pos=(-58, 512, 0), part="cushion",
                edit=[dict(box=((-0.16, -0.03), (-0.21, -0.10), (0.70, 0.93)), clone=(-0.62, 0, 0)),   # ниппель -> к углу
                      dict(box=((-0.16, -0.03), (-0.21, -0.10), (0.712, 0.93)), flat=(2, 0.712), col=(0.03, 0.03, 0.035)),
                      dict(box=((0.742, 0.96), (-0.21, -0.10), (-0.16, -0.03)), flat=(0, 0.742), col=(0.03, 0.03, 0.035))],
                parts=[("valve", ((-0.80, -0.62), (-0.21, -0.10), (0.70, 0.93)))])
