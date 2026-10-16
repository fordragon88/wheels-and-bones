"""Разметка колёс сгенерированной модели по геометрии (поверх mesh3d_post.py).
python art_tests/mesh3d_wheels.py <in.json> <out.json>
Оси игры: x — вперёд, y — вверх (пол 0), z — вбок; мм."""
import sys, json, math

d = json.load(open(sys.argv[1]))
V, F, PARTS = d["verts"], d["faces"], d["parts"]
for p in ("tire", "rim", "spokes", "axle", "caster", "footrest", "tube"):
    if p not in PARTS:
        PARTS.append(p)
pi = {p: i for i, p in enumerate(PARTS)}
COL = {"tire": (44, 44, 52), "rim": (200, 205, 218), "spokes": (178, 182, 194), "axle": (150, 155, 168),
       "caster": (44, 44, 52), "caster_hub": (190, 194, 206), "footrest": (58, 58, 66), "tube": (128, 58, 50)}
cen = [[sum(V[i][k] for i in f[:3]) / 3 for k in range(3)] for f in F]
xs = [v[0] for v in V]; ys = [v[1] for v in V]; zs = [v[2] for v in V]
zmin, zmax = min(zs), max(zs)
width = zmax - zmin
H = max(ys)


def fit_wheel(sel):
    """Центр и радиус колеса по точкам в его плоскости (x, y)."""
    pts = [cen[i] for i in sel]
    if not pts:
        return None
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
    y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
    R = max(x1 - x0, y1 - y0) / 2
    return ((x0 + x1) / 2, (y0 + y1) / 2, R)


def circle_fit(pts):
    """Окружность по точкам (алгебраическая подгонка Коса)."""
    n = len(pts)
    mx = sum(p[0] for p in pts) / n; my = sum(p[1] for p in pts) / n
    u = [p[0] - mx for p in pts]; v = [p[1] - my for p in pts]
    suu = sum(a * a for a in u); svv = sum(b * b for b in v); suv = sum(a * b for a, b in zip(u, v))
    suuu = sum(a ** 3 for a in u); svvv = sum(b ** 3 for b in v)
    suvv = sum(a * b * b for a, b in zip(u, v)); svuu = sum(b * a * a for a, b in zip(u, v))
    det = suu * svv - suv * suv
    uc = (svv * (suuu + suvv) - suv * (svvv + svuu)) / (2 * det)
    vc = (suu * (svvv + svuu) - suv * (suuu + suvv)) / (2 * det)
    R = math.sqrt(uc * uc + vc * vc + (suu + svv) / n)
    return mx + uc, my + vc, R


stats = {}
GEO = set()                                # грани, размеченные по геометрии
WHEELS = []
for side in (-1, 1):
    outer = zmax if side > 0 else zmin
    ring = [V[i] for i in range(len(V)) if abs(V[i][2] - outer) < width * 0.035 and V[i][1] < H * 0.8]
    cx, cy, _ = circle_fit(ring)
    R = cy                                    # колесо стоит на полу: радиус = высота центра
    # плоскость колеса — медиана z точек на окружности шины
    tire_pts = sorted(V[i][2] for i in range(len(V))
                      if abs(math.hypot(V[i][0] - cx, V[i][1] - cy) - R * 0.95) < R * 0.06 and V[i][2] * side > 0)
    zw = tire_pts[len(tire_pts) // 2]
    for i, c in enumerate(cen):
        if c[2] * side <= 0:
            continue
        r = math.hypot(c[0] - cx, c[1] - cy)
        rel = r / R
        dz = abs(c[2] - zw)
        name = None
        if 0.84 < rel <= 1.06 and dz < 45 and rel > 0.90:
            name = "tire"
        elif 0.78 < rel <= 1.0 and dz < 120 and (c[2] - zw) * side > -30:   # обод и обруч снаружи
            name = "rim"
        elif rel <= 0.84 and dz < 32:
            name = "axle" if rel < 0.13 else "spokes"
        elif rel < 0.13 and dz < 75:
            name = "axle"
        if name:
            old = F[i][4:7]
            colorful = (max(old) - min(old)) > 0.3 * max(max(old), 1) and max(old) > 90
            F[i][3] = pi[name]; GEO.add(i)
            if not (name == "rim" and colorful):            # цветной обод сохраняем, спицы — всегда металл     # цветные обода (розовые, лайм, медь) не трогаем
                F[i][4:7] = COL[name]
            stats[name] = stats.get(name, 0) + 1
    # касторы: впереди, у пола
    czone = [i for i, c in enumerate(cen) if c[1] < 230 and c[0] > cx + R * 0.7 and c[2] * side > 0]
    low = [cen[i] for i in czone if cen[i][1] < 110]      # нижняя дуга шины кастора, без вилки
    cw = None
    if len(low) > 20:
        ccx, ccy, cr = circle_fit(low)
        cr = ccy                                          # кастор тоже стоит на полу
        cw = (ccx, ccy, cr)
        czs = sorted(c[2] for c in low)
        czw = czs[len(czs) // 2]
        for i in czone:
            c = cen[i]
            r = math.hypot(c[0] - ccx, c[1] - ccy)
            if r <= cr * 1.1 and abs(c[2] - czw) < 40:
                name = "caster" if r > cr * 0.55 else "caster_hub"
                F[i][3] = pi["caster"]; F[i][4:7] = COL[name]; GEO.add(i)
                stats["caster"] = stats.get("caster", 0) + 1
    WHEELS.append((cx, cy, R, zw, side))
    print(f"side {side:+d}: wheel ({cx:.0f},{cy:.0f}) R {R:.0f} plane z {zw:.0f}; caster {cw and tuple(round(v) for v in cw)}")
# подножки: плоские пластины впереди у пола, не касторы
fx = max(xs)
for i, c in enumerate(cen):
    if c[0] > fx - (fx - min(xs)) * 0.18 and 60 < c[1] < 260 and PARTS[F[i][3]] in ("tire", "frame", "rim", "seat"):
        F[i][3] = pi["footrest"]; F[i][4:7] = COL["footrest"]; GEO.add(i)
d["parts"] = PARTS
json.dump(d, open(sys.argv[2], "w"))
print("relabelled:", stats)

CLEAN = len(sys.argv) > 3 and sys.argv[3] == "clean"   # перекраска под голубую коляску — только по запросу
# --- финальная чистка рамы/обивки: сглаживание по соседям вне колёс ---
from collections import defaultdict, Counter
edge_faces = defaultdict(list)
for i, f in enumerate(F):
    a, b, c = f[:3]
    for e in ((a, b), (b, c), (c, a)):
        edge_faces[tuple(sorted(e))].append(i)
nbrs = defaultdict(set)
for fl in edge_faces.values():
    for i in fl:
        nbrs[i].update(j for j in fl if j != i)
FIXED = {pi[p] for p in ("tire", "rim", "spokes", "axle", "caster", "footrest")}
NAVY = (50, 71, 125); BLUE = (82, 190, 239); GRIP = (44, 44, 52)
ymax = max(ys)
for i, c in enumerate(cen if CLEAN else []):   # серые кляксы выше сиденья — это обивка (кроме ручек)
    if i in GEO:
        continue
    r, g, b = F[i][4:7]
    if c[1] > ymax - 70:
        continue
    if c[1] > 430 and max(r, g, b) - min(r, g, b) < 40:
        F[i][3] = pi["seat"]; F[i][4:7] = list(NAVY)
    elif max(r, g, b) - min(r, g, b) < 40 and c[1] > 150 and not any(
            math.hypot(c[0] - wx, c[1] - wy) < wr * 1.08 and (c[2] - wz) * ws > -60 for wx, wy, wr, wz, ws in WHEELS):
        F[i][3] = pi["frame"]; F[i][4:7] = list(BLUE)
for _ in range(6):                          # большинство соседей (только рама/обивка)
    new = {}
    for i in range(len(F)):
        if i in GEO:
            continue
        cnt = Counter((F[j][3], tuple(F[j][4:7])) for j in nbrs[i] if j not in GEO)
        if cnt:
            (lab, col), n = cnt.most_common(1)[0]
            if n >= 2 and (lab, tuple(F[i][4:7])) != (lab, col):
                new[i] = (lab, col)
    for i, (lab, col) in new.items():
        F[i][3] = lab; F[i][4:7] = list(col)
json.dump(d, open(sys.argv[2], "w"))
print("cleaned")
