"""Чистая окраска ручной коляски по зонам (поверх mesh3d_label + mesh3d_wheels).
python art_tests/mesh3d_scheme.py <in.json> <out.json> <схема>
Колёса — по геометрии (центр и радиус по граням шины), обивка — между колёсами выше
сиденья, остальное — рама. Цвета схем взяты с артов колясок."""
import sys, json, math

SCHEMES = {   # обивка, рама, обод/обруч (None — оставить как есть)
    "inv9000": ((40, 54, 112), (128, 132, 142), None),
    "xdt": ((40, 54, 112), (128, 132, 142), None),
    "ego": ((44, 44, 50), (172, 206, 44), (172, 206, 44)),
    "tekna": ((44, 44, 50), (62, 62, 70), (196, 120, 64)),
    "exelle_jr": ((44, 44, 50), (236, 170, 200), (236, 170, 200)),
    "noir": ((44, 44, 50), (58, 58, 66), None),
}
WHEEL = {"tire", "rim", "spokes", "axle", "caster", "tube", "valve", "bearing"}
SPOKE = (178, 182, 194)

src, dst, key = sys.argv[1], sys.argv[2], sys.argv[3]
up, frame, rim = SCHEMES[key]
d = json.load(open(src))
V, F, P = d["verts"], d["faces"], d["parts"]
cen = [[sum(V[i][k] for i in f[:3]) / 3 for k in range(3)] for f in F]
H = max(v[1] for v in V)
wheels = []
for side in (-1, 1):
    tires = [c for f, c in zip(F, cen) if P[f[3]] == "tire" and c[2] * side > 0]
    if len(tires) < 20:
        continue
    cx = sum(c[0] for c in tires) / len(tires); cy = sum(c[1] for c in tires) / len(tires)
    R = max(math.hypot(c[0] - cx, c[1] - cy) for c in tires)
    zw = sorted(abs(c[2]) for c in tires)[len(tires) // 2]
    wheels.append((cx, cy, R, zw, side))
inner = min(w[3] for w in wheels) - 55 if wheels else 200
seat_y = H * 0.42
n_up = n_fr = n_wh = 0
for f, c in zip(F, cen):
    name = P[f[3]]
    in_wheel = any(c[2] * s > 0 and abs(abs(c[2]) - zw) < 26 and math.hypot(c[0] - cx, c[1] - cy) < R * 1.02
                   for cx, cy, R, zw, s in wheels)
    if name in WHEEL:
        if name == "rim" and rim:
            f[4:7] = list(rim)
        continue
    if in_wheel:                                  # «ничьи» грани внутри колеса — спицы/ступица
        f[4:7] = list(SPOKE); n_wh += 1
    elif abs(c[2]) < inner and c[1] > seat_y and name not in ("footrest", "brake", "bolts"):
        f[4:7] = list(up); n_up += 1
    elif name not in ("footrest", "brake", "bolts"):
        f[4:7] = list(frame); n_fr += 1
# обруч (rear_wheel) — внешняя часть обода, снаружи плоскости колеса; ниппель — нижняя точка обода
for nm in ("rear_wheel", "valve"):
    if nm not in P:
        P.append(nm)
for cx, cy, R, zw, side in wheels:
    rims = [i for i, (f, c) in enumerate(zip(F, cen)) if P[f[3]] == "rim" and c[2] * side > 0]
    outer = [i for i in rims if abs(cen[i][2]) > zw + 12]
    for i in outer:
        F[i][3] = P.index("rear_wheel")
    low = sorted((i for i in rims if i not in set(outer)), key=lambda i: cen[i][1])[:12]
    for i in low:
        F[i][3] = P.index("valve"); F[i][4:7] = [214, 178, 92]
d["parts"] = P
json.dump(d, open(dst, "w"), separators=(",", ":"))
print(f"{key}: обивка {n_up}, рама {n_fr}, внутри колёс {n_wh}, колёса {len(wheels)}")
