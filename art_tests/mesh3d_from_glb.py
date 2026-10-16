"""GLB с цветом вершин (Pixal3D/TRELLIS.2 + PaintMesh) -> JSON-модель игры.
Запуск python'ом ComfyUI (trimesh):
  python_embeded\\python.exe art_tests\\mesh3d_from_glb.py <mesh.glb> <out.json> <высота_мм>
Оси игры: x — вперёд (прочь от ручек/спинки), y — вверх, пол y=0, z — вбок; мм.
Цвет грани = среднее цветов её вершин (сгенерирован моделью, без проекции)."""
import sys, json
import numpy as np
import trimesh

src, out, height = sys.argv[1], sys.argv[2], float(sys.argv[3])
import struct


def read_glb(path):
    """Прямое чтение GLB: POSITION, COLOR_0, индексы (trimesh теряет COLOR_0 при наличии материала)."""
    raw = open(path, "rb").read()
    jl = struct.unpack("<I", raw[12:16])[0]
    js = json.loads(raw[20:20 + jl])
    bin_ = raw[20 + jl + 8:]
    CT = {5126: np.float32, 5121: np.uint8, 5123: np.uint16, 5125: np.uint32}
    NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}

    def acc(i):
        a = js["accessors"][i]; bv = js["bufferViews"][a["bufferView"]]
        off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        dt = np.dtype(CT[a["componentType"]]); n = NC[a["type"]]
        arr = np.frombuffer(bin_, dtype=dt, count=a["count"] * n, offset=off).reshape(a["count"], n)
        if a.get("normalized") or dt != np.float32:
            arr = arr.astype(float) / (255.0 if dt == np.uint8 else 65535.0 if dt == np.uint16 else 1.0) if a.get("normalized") else arr
        return np.asarray(arr)
    Vs, Fs, Cs, base = [], [], [], 0
    for m in js["meshes"]:
        for pr in m["primitives"]:
            v = acc(pr["attributes"]["POSITION"]).astype(float)
            f = acc(pr["indices"]).reshape(-1, 3).astype(int) + base
            c = acc(pr["attributes"]["COLOR_0"])[:, :3].astype(float) if "COLOR_0" in pr["attributes"] else np.full((len(v), 3), 0.6)
            Vs.append(v); Fs.append(f); Cs.append(c); base += len(v)
    return np.vstack(Vs), np.vstack(Fs), np.vstack(Cs)


V, F, C = read_glb(src)
C = C * 255.0 if C.max() <= 1.0001 else C
# gamma: цвета в GLB линейные -> sRGB для нашего плоского рендера
C = 255.0 * np.clip(C / 255.0, 0, 1) ** (1 / 2.2)     # линейный цвет glTF -> sRGB
V = V - (V.min(0) + V.max(0)) / 2                    # glTF: Y вверх
# Pixal3D сохраняет ракурс картинки (коляска по диагонали) — выравниваем по минимальному
# прямоугольнику в плане: перебор поворота вокруг вертикали
best = None
for deg in np.arange(0, 90, 0.5):
    a_ = np.radians(deg)
    x = V[:, 0] * np.cos(a_) + V[:, 2] * np.sin(a_); z = -V[:, 0] * np.sin(a_) + V[:, 2] * np.cos(a_)
    area = np.ptp(x) * np.ptp(z)
    if best is None or area < best[0]:
        best = (area, a_)
a_ = best[1]
V = np.stack([V[:, 0] * np.cos(a_) + V[:, 2] * np.sin(a_), V[:, 1], -V[:, 0] * np.sin(a_) + V[:, 2] * np.cos(a_)], 1)
V = V - (V.min(0) + V.max(0)) / 2
print(f"поворот в плане {np.degrees(a_):.1f}°")
ext = np.ptp(V, 0)
side_axis = 0 if ext[0] < ext[2] else 2
long_axis = 2 if side_axis == 0 else 0
k = height / ext[1]
top = V[:, 1] > V[:, 1].max() - ext[1] * 0.08         # ручки/подголовник — это зад
fwd = -1.0 if V[top, long_axis].mean() > 0 else 1.0
P = np.stack([V[:, long_axis] * fwd, V[:, 1] - V[:, 1].min(), V[:, side_axis]], 1) * k
M = np.zeros((3, 3)); M[0, long_axis] = fwd; M[1, 1] = 1; M[2, side_axis] = 1
if np.linalg.det(M) < 0:
    F = F[:, [0, 2, 1]]
F = F[:, [0, 2, 1]]                                   # обход граней как ждёт движок
P[:, 0] += 180 - (P[:, 0].min() + P[:, 0].max()) / 2
FC = C[F].mean(1)
# тёмные материалы чуть светлее (наш плоский свет делает чёрное «дырой»), оттенок сохраняем
mx = FC.max(1, keepdims=True)
FC = np.where(mx < 64, np.where(mx > 6, FC * (64.0 / np.maximum(mx, 1)), [[56, 56, 62]]), FC)
faces = [[int(a), int(b), int(c), 0, int(r), int(g), int(bl)] for (a, b, c), (r, g, bl) in zip(F, FC.round())]
json.dump({"verts": P.round(1).tolist(), "faces": faces, "parts": ["frame"], "source": "Pixal3D"}, open(out, "w"))
print(f"faces {len(F)}, verts {len(V)}, color range {C.min():.0f}..{C.max():.0f}")
