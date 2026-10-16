"""Пульт электроколяски в реальных координатах готовой модели (если разметка его не нашла).
python art_tests/mesh3d_joystick.py <in.json> <out.json>
Ищет выступ над передним концом подлокотника: верх — джойстик, под ним пыльник, ниже корпус пульта."""
import sys, json
import numpy as np

src, dst = sys.argv[1], sys.argv[2]
d = json.load(open(src)); P = d["parts"]; F = d["faces"]
V = np.asarray(d["verts"], float)
C = V[np.asarray([f[:3] for f in F])].mean(1)
H, X1 = V[:, 1].max(), V[:, 0].max()
for nm in ("controller", "joystick", "boot"):
    if nm not in P:
        P.append(nm)
best = None
for side in (-1, 1):
    zone = np.where((C[:, 2] * side > 90) & (C[:, 1] > H * 0.5) & (C[:, 1] < H * 0.8) & (C[:, 0] > X1 * 0.45))[0]
    if len(zone) < 30:
        continue
    pk = zone[C[zone, 1].argmax()]
    rise = C[pk, 1] - np.median(C[zone, 1])
    print(f"side {side:+d}: зона {len(zone)}, пик {C[pk].round()}, выступ {rise:.0f}")
    if best is None or rise > best[0]:
        best = (rise, pk, zone)
rise, pk, zone = best
px, py, pz = C[pk]
n = {}
for i in zone:
    c = C[i]; r = np.hypot(c[0] - px, c[2] - pz)
    nm = None
    if r < 45 and c[1] > py - 20:
        nm, col = "joystick", [210, 70, 64]
    elif r < 45 and c[1] > py - 50:
        nm, col = "joystick", [170, 174, 186]
    elif r < 55 and c[1] > py - 80:
        nm, col = "boot", [30, 30, 36]
    elif abs(c[0] - px) < 90 and abs(c[2] - pz) < 70 and c[1] > py - 140:
        nm, col = "controller", [40, 42, 50]
    if nm:
        F[i][3] = P.index(nm); F[i][4:7] = col; n[nm] = n.get(nm, 0) + 1
d["parts"] = P
json.dump(d, open(dst, "w"), separators=(",", ":"))
print("пульт:", n)
