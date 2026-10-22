"""Цвет одной сгенерированной модели -> на форму другой (обе по одной картинке, оси tripo_convert):
габариты подгоняются по осям, цвет вершины — среднее k ближайших точек донора.
python art_tests/gen3d_colorize.py <форма> <донор цвета> <выход>   (имена из art_tests/gen3d/<имя>_full.npz)"""
import os, sys
import numpy as np
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
G = os.path.join(HERE, "gen3d")
shape, donor, out = sys.argv[1:4]
a = dict(np.load(os.path.join(G, shape + "_full.npz")))
b = np.load(os.path.join(G, donor + "_full.npz"))
Va, Vb, Cb = a["V"], b["V"], b["C"][:, :3]
la, ha, lb, hb = Va.min(0), Va.max(0), Vb.min(0), Vb.max(0)
Vb2 = (Vb - lb) / np.maximum(hb - lb, 1e-6) * (ha - la) + la          # донор — в габариты формы
d, idx = cKDTree(Vb2).query(Va, k=6)
w = 1.0 / np.maximum(d, 1.0)
C = (Cb[idx] * w[..., None]).sum(1) / w.sum(1)[:, None]
a["C"] = np.c_[C, a["C"][:, 3:]] if a["C"].shape[1] > 3 else C
np.savez_compressed(os.path.join(G, out + "_full.npz"), **a)
print(out, "вершин", len(Va), "средн. расстояние до донора, мм:", round(float(d[:, 0].mean()), 1))
