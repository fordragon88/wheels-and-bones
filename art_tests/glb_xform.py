"""Матрица «исходный GLB -> оси и размер игры» — та же, что делает tripo_convert (поворот, масштаб, центр), но
без облегчения: в Blender кадры снимаются с оригинальной модели (полная сетка, родная текстура), а облегчённая
копия игры нужна только для деталей и кружков.
python art_tests/glb_xform.py <in.glb> <имя> <axis>=<mm> [--keep-big=доля] [--flip-z] [--yaw N]
-> art_tests/gen3d/<имя>_xform.json (4×4, мм игры = A · (x, y, z, 1) мировых координат glTF)"""
import os, sys, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tripo_convert as tc

src, name, ax = sys.argv[1], sys.argv[2], sys.argv[3]
axis, mm = ax.split("=")
yaw = int(sys.argv[sys.argv.index("--yaw") + 1]) if "--yaw" in sys.argv else 0
V, F, C = tc.read_glb(src)
q = np.round(V / (np.abs(V).max() * 1e-5)).astype(np.int64)           # склейка — как в tripo_convert
_, first, inv = np.unique(q, axis=0, return_index=True, return_inverse=True)
raw = V[first]
F = inv.ravel()[F]
F = F[(F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])]
G = tc.orient(raw, (axis, float(mm)), "--flip-z" in sys.argv, yaw)
G, F2, keep, *_ = tc.keep_attached(G, F, cell=12.0)
raw = raw[keep]
G = tc.orient(G, (axis, float(mm)), "--flip-z" in sys.argv, 0)
X = np.c_[raw, np.ones(len(raw))]
A, *_ = np.linalg.lstsq(X, G, rcond=None)                               # (4, 3): G = X · A
err = np.abs(X @ A - G).max()
M = np.eye(4)
M[:3, :] = A.T
json.dump(dict(src=os.path.abspath(src), matrix=M.tolist(), err_mm=float(err)),
          open(os.path.join(HERE, "gen3d", name + "_xform.json"), "w"), indent=1)
print(name, "ошибка подгонки, мм:", round(float(err), 4))
