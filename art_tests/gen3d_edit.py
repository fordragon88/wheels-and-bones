"""Правка сгенерированной модели по референсу (до разметки tripo_label): убрать лишнее, перекрасить зоны.
python art_tests/gen3d_edit.py <ключ>   (правила — EDITS; art_tests/gen3d/<src>_full.npz -> <dst>_full.npz)"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
G = os.path.join(HERE, "gen3d")
INF = 1e9
EDITS = {
    # Permobil M3 Corpus: форма Hunyuan3D 2.1 + цвет Pixal3D (gen3d_colorize). На рисунке-референсе джойстик один
    # (справа, +z, красная ручка), у модели — второй слева; крылья корпуса над ведущими колёсами — фиолетовые.
    "m3": dict(src="m3_hybrid", dst="m3gen",
               drop=[dict(x=(40, 240), y=(772, 900), z=(-INF, -230))],               # ручка левого пульта (над подлокотником)
               paint=[dict(x=(-370, 245), y=(70, 330), az=(215, 345), dark=140, avoid_wheel=((-70, 200), 214),
                           color=(104, 52, 150))]),
}
spec = EDITS[sys.argv[1]]
d = dict(np.load(os.path.join(G, spec["src"] + "_full.npz")))
V, F, C = d["V"], d["F"], d["C"].astype(np.float32)
P = V[F].mean(1)
keep = np.ones(len(F), bool)
for b in spec.get("drop", []):
    keep &= ~((P[:, 0] >= b["x"][0]) & (P[:, 0] <= b["x"][1]) & (P[:, 1] >= b["y"][0]) & (P[:, 1] <= b["y"][1])
              & (P[:, 2] >= b["z"][0]) & (P[:, 2] <= b["z"][1]))
print("убрано граней:", int((~keep).sum()))
for b in spec.get("paint", []):
    az = np.abs(V[:, 2])
    m = (V[:, 0] >= b["x"][0]) & (V[:, 0] <= b["x"][1]) & (V[:, 1] >= b["y"][0]) & (V[:, 1] <= b["y"][1]) \
        & (az >= b["az"][0]) & (az <= b["az"][1]) & (C[:, :3].mean(1) < b["dark"])
    if b.get("avoid_wheel"):
        (cx, cy), R = b["avoid_wheel"]
        m &= np.hypot(V[:, 0] - cx, V[:, 1] - cy) > R                 # шину и диск не красим
    lum = C[m, :3].mean(1, keepdims=True) / 60.0                     # светотень исходника сохраняется
    C[m, :3] = np.clip(np.asarray(b["color"], np.float32) * np.clip(lum, 0.55, 1.35), 0, 255)
    print("перекрашено вершин:", int(m.sum()))
F = F[keep]
used = np.unique(F)
remap = np.full(len(V), -1)
remap[used] = np.arange(len(used))
d.update(V=V[used], F=remap[F], C=C[used])
np.savez_compressed(os.path.join(G, spec["dst"] + "_full.npz"), **d)
print("->", spec["dst"], len(d["F"]), "граней")
