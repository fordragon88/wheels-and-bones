"""Пост-обработка сгенерированной Hunyuan3D модели для 3D-осмотра игры.

Запуск python'ом ComfyUI (там есть trimesh+numpy+scipy):
  python_embeded\\python.exe art_tests\\mesh3d_post.py <mesh.glb> <input_rgba.png> <out.json>

1. Находит ракурс камеры входной картинки: перебор поворота/наклона, максимум
   совпадения силуэтов (Hunyuan сохраняет поворот объекта из картинки).
2. Раскрашивает вершины проекцией картинки с этой камеры (z-буфер = видимость);
   невидимая сторона берёт цвет зеркальной точки (коляска симметрична).
3. Детали — по цвету (голубая рама, чёрная шина, серебро, синяя обивка, красный тормоз).
4. Переводит в мм и оси игры (x — вперёд, y — вверх, пол y=0, высота 950 мм)."""
import sys, json
import numpy as np
import trimesh
from PIL import Image
from scipy.ndimage import binary_dilation
from scipy.spatial import cKDTree

src, img_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
mesh = trimesh.util.concatenate([g for g in trimesh.load(src, force="scene").dump()
                                 if isinstance(g, trimesh.Trimesh)])
comps = mesh.split(only_watertight=False)
if len(comps) > 1:
    big = max(len(c.faces) for c in comps)
    mesh = trimesh.util.concatenate([c for c in comps if len(c.faces) > big * 0.004])
mesh.merge_vertices()
trimesh.repair.fix_winding(mesh)                     # согласованная ориентация граней
trimesh.repair.fix_normals(mesh, multibody=True)     # нормали наружу — можно отсекать задние грани
V = np.asarray(mesh.vertices, float)
F = np.asarray(mesh.faces, int)
V = V - (V.min(0) + V.max(0)) / 2

img = np.asarray(Image.open(img_path).convert("RGBA")).astype(float)
alpha = img[..., 3] > 128
ys, xs = np.nonzero(alpha)
ix0, ix1, iy0, iy1 = xs.min(), xs.max(), ys.min(), ys.max()
crop = alpha[iy0:iy1 + 1, ix0:ix1 + 1]
A = np.asarray(Image.fromarray(crop.astype(np.uint8) * 255).resize((96, 96))) > 128
samp = V[np.random.default_rng(0).choice(len(V), min(len(V), 120000), replace=False)]


def view(P, yaw, pitch):
    cy, sy, cp, sp = np.cos(yaw), np.sin(yaw), np.cos(pitch), np.sin(pitch)
    x = P[:, 0] * cy + P[:, 2] * sy
    z = -P[:, 0] * sy + P[:, 2] * cy
    y = P[:, 1] * cp - z * sp
    d = P[:, 1] * sp + z * cp                    # глубина: больше — ближе к камере
    return x, y, d


def iou(yaw, pitch):
    x, y, _ = view(samp, yaw, pitch)
    u = (x - x.min()) / np.ptp(x); w = (y.max() - y) / np.ptp(y)
    B = np.zeros((96, 96), bool); B[(w * 95).astype(int), (u * 95).astype(int)] = True
    B = binary_dilation(B, iterations=1)
    return (A & B).sum() / (A | B).sum()


best = max(((iou(np.radians(a), np.radians(p)), a, p) for a in range(0, 360, 4) for p in range(-30, 41, 5)))
score, yaw_d, pitch_d = best
# уточнение
best = max(((iou(np.radians(a), np.radians(p)), a, p)
            for a in np.arange(yaw_d - 4, yaw_d + 4.1, 1) for p in np.arange(pitch_d - 5, pitch_d + 5.1, 1)))
score, yaw_d, pitch_d = best
print(f"camera yaw {yaw_d:.0f} pitch {pitch_d:.0f}, silhouette IoU {score:.2f}")

x, y, d = view(V, np.radians(yaw_d), np.radians(pitch_d))
u = (x - x.min()) / np.ptp(x); w = (y.max() - y) / np.ptp(y)
H, W = alpha.shape
px = np.clip((ix0 + u * (ix1 - ix0)).round().astype(int), 0, W - 1)
py = np.clip((iy0 + w * (iy1 - iy0)).round().astype(int), 0, H - 1)
S = 2                                                # z-буфер вдвое грубее картинки
zb = np.full((H // S + 1, W // S + 1), -1e9)
# растеризуем грани грубо: центры и вершины граней в z-буфер
np.maximum.at(zb, (py // S, px // S), d)
VN = np.asarray(mesh.vertex_normals, float)
_, _, dn = view(VN, np.radians(yaw_d), np.radians(pitch_d))
visible = (d >= zb[py // S, px // S] - np.ptp(d) * 0.015) & alpha[py, px] & (dn > 0.15)
col = np.zeros((len(V), 3))
col[visible] = img[py[visible], px[visible], :3]
vis = np.nonzero(visible)[0]
hid = np.nonzero(~visible)[0]
tree = cKDTree(V[vis])
mir = V[hid].copy()
# зеркало по поперечной оси коляски — ось наименьшего размера среди горизонтальных
ext = np.ptp(V, 0)
side_axis = 0 if ext[0] < ext[2] else 2
mir[:, side_axis] *= -1
_, j = tree.query(mir)
col[hid] = col[vis[j]]
print(f"visible vertices {visible.mean():.0%}")

FC = col[F].mean(1)
# палитра исходной картинки: k-means по непрозрачным пикселям
from scipy.cluster.vq import kmeans2
pix = img[alpha][:, :3]
pix = pix[np.random.default_rng(1).choice(len(pix), min(len(pix), 60000), replace=False)]
cent, _ = kmeans2(pix, 7, minit="++", seed=3)
lab = np.argmin(((FC[:, None, :] - cent[None, :, :]) ** 2).sum(2), 1)
adj = mesh.face_adjacency                               # сглаживание: большинство соседей
for _ in range(4):
    votes = np.zeros((len(F), len(cent)))
    np.add.at(votes, (np.arange(len(F)), lab), 2.0)
    np.add.at(votes, (adj[:, 0], lab[adj[:, 1]]), 1.0)
    np.add.at(votes, (adj[:, 1], lab[adj[:, 0]]), 1.0)
    lab = votes.argmax(1)
FC = cent[lab]


def kind(c):
    r, g, b = c
    mx, mn = max(c), min(c)
    sat = (mx - mn) / max(mx, 1)
    if r > 140 and r > g + 50 and r > b + 50:
        return 4                                        # красный тормоз
    if mx < 80:
        return 2                                        # чёрное: шины (подножки ниже)
    if b > r + 30 and mx < 150:
        return 1                                        # тёмно-синяя обивка
    if sat < 0.22 and mx >= 110:
        return 3                                        # серебро
    return 0                                            # голубая рама


ckind = np.array([kind(c) for c in cent])
part = ckind[lab]
PARTS = ["frame", "seat", "tire", "rim", "brake", "footrest"]
print("palette:", [(tuple(int(v) for v in c), PARTS[ckind[i]]) for i, c in enumerate(cent)])

# --- оси игры: y вверх, x — вперёд (прочь от спинки), z — вбок; мм ---
long_axis = 2 if side_axis == 0 else 0
HEIGHT = float(sys.argv[4]) if len(sys.argv) > 4 else 950.0
k = HEIGHT / np.ptp(V[:, 1])
top = V[:, 1] > V[:, 1].max() - np.ptp(V[:, 1]) * 0.08   # ручки/верх спинки — это зад
fwd = -1.0 if V[top, long_axis].mean() > 0 else 1.0
P = np.stack([V[:, long_axis] * fwd, V[:, 1] - V[:, 1].min(), V[:, side_axis]], 1) * k
cen = P[F].mean(1)
part[(part == 2) & (cen[:, 0] > np.percentile(P[:, 0], 75)) & (cen[:, 1] < 200)] = 5   # подножки
P[:, 0] += 180 - (P[:, 0].min() + P[:, 0].max()) / 2
# смена осей могла быть зеркальной — тогда разворачиваем порядок вершин граней
M = np.zeros((3, 3)); M[0, long_axis] = fwd; M[1, 1] = 1; M[2, side_axis] = 1
if np.linalg.det(M) < 0:
    F = F[:, [0, 2, 1]]
# движок игры считает «лицевой» грань с обратным обходом — проверено рендером
F = F[:, [0, 2, 1]]

faces = [[int(a), int(b_), int(c), int(pi), int(cr), int(cg), int(cb)]
         for (a, b_, c), pi, (cr, cg, cb) in zip(F, part, np.clip(FC, 0, 255).round())]
json.dump({"verts": P.round(1).tolist(), "faces": faces, "parts": PARTS,
           "source": "Hunyuan3D 2.1", "camera": [float(yaw_d), float(pitch_d), float(score)]}, open(out, "w"))
print("faces", len(F), "parts", {p: int((part == i).sum()) for i, p in enumerate(PARTS)})
