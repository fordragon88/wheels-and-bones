"""Разметка деталей сгенерированной модели по процедурной модели игры (ближайшая грань).
python art_tests/mesh3d_label.py <in.json> <out.json> <kind>   (kind: m3, power, manual)"""
import os, sys, json
os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
import game

src, dst, kind = sys.argv[1], sys.argv[2], sys.argv[3]
d = json.load(open(src))
V = np.asarray(d["verts"], float)
ref = game.get_chair3d(kind)
RV = np.asarray(ref.verts, float)
# совместить габариты: высота, длина, ширина (генерация масштабирована только по высоте)
V0 = V.copy()                                         # настоящие пропорции (для не-M3 сохраняем их)
lo, hi, rlo, rhi = V.min(0), V.max(0), RV.min(0), RV.max(0)
V = (V - lo) / (hi - lo) * (rhi - rlo) + rlo
CLICK = {"joystick", "boot", "controller", "wiring", "battery", "fuse", "motor", "freewheel", "axle",
         "tire", "rim", "spokes", "caster", "caster_stem", "brake", "footrest", "seat", "cushion", "bolts", "valve", "tube", "bearing"}
cent, parts = [], []
for idx, part, col, fl in ref.faces:
    if part in CLICK:
        cent.append(RV[list(idx)].mean(0)); parts.append(part)
F = d["faces"]
FC = V[np.asarray([f[:3] for f in F])].mean(1)


def nearest(C):
    dist = np.empty(len(FC)); j = np.empty(len(FC), int)
    for a in range(0, len(FC), 2000):                # ближайший центр детали (без scipy)
        dd = ((FC[a:a + 2000, None, :] - C[None, :, :]) ** 2).sum(2)
        j[a:a + 2000] = dd.argmin(1); dist[a:a + 2000] = np.sqrt(dd.min(1))
    return dist, j


# пульт может стоять на другом подлокотнике — пробуем модель как есть и зеркально (по z)
C = np.asarray(cent)
best = None
for sgn in (1, -1):
    Cm = C * [1, 1, sgn]
    dist, j = nearest(Cm)
    ctrl = [k for k, p in enumerate(parts) if p in ("controller", "joystick")]
    score = np.sqrt(((Cm[ctrl][:, None, :] - FC[None, :, :]) ** 2).sum(2)).min(1).mean() if ctrl else 0.0
    print(f"mirror {sgn:+d}: controller/joystick distance {score:.0f} мм")
    if best is None or score < best[0]:
        best = (score, dist, j)
_, dist, j = best
names = list(d["parts"])
stats = {}
for i, f in enumerate(F):
    p = parts[j[i]] if dist[i] < 70 else "frame"
    if p not in names:
        names.append(p)
    f[3] = names.index(p)
    stats[p] = stats.get(p, 0) + 1
# --- окраска по зонам (только для электроколясок M-серии) ---
if kind == "m3":
    lab = np.asarray([names[f[3]] if f[3] < len(names) else "frame" for f in F])
    y = FC[:, 1]
    TIRE, RIM, METAL, UPH, PURPLE = (34, 34, 40), (92, 94, 104), (104, 108, 118), (74, 62, 92), (112, 66, 158)
    # колёса: ведущие (axle) и касторы — у пола, по радиусу от центра колеса
    dx, dy, dr = game.M3["drive"]
    for i, f in enumerate(F):
        c = FC[i]
        if lab[i] == "axle":
            r = np.hypot(c[0] - dx, c[1] - dy)
            f[4:7] = list(TIRE) if r > dr * 0.72 else list(RIM)
        elif y[i] < 200 and lab[i] == "frame":
            near_c = any(np.hypot(c[0] - wx, c[1] - wy) < wr * 1.15 for wx, wy, wr in (game.M3["front"], game.M3["rear"]))
            if near_c:
                r = min(np.hypot(c[0] - wx, c[1] - wy) for wx, wy, wr in (game.M3["front"], game.M3["rear"]))
                f[4:7] = list(TIRE) if r > 60 else list(RIM)
        elif y[i] > 470 and lab[i] not in ("controller", "joystick", "boot", "wiring"):
            f[4:7] = list(UPH)                          # спинка, подголовник, сиденье, подлокотники
        elif 300 < y[i] <= 470 and lab[i] == "frame":
            f[4:7] = list(METAL)                        # рама сиденья, подъёмник
        elif lab[i] == "frame" and f[4] > f[5] + 20 and f[6] > f[5] + 20:
            f[4:7] = list(PURPLE)                       # фиолетовые кожухи — ярче
if kind in ("m3", "power"):
    # пульт на подлокотнике: самая высокая точка на переднем конце подлокотника — джойстик
    for nm in ("controller", "joystick", "boot"):
        if nm not in names:
            names.append(nm)
    for side in (-1, 1):
        zone = [i for i in range(len(F)) if FC[i, 2] * side > (150 if kind == "m3" else 100) and 560 < FC[i, 1] < (860 if kind == "m3" else 960) and FC[i, 0] > 230]
        if len(zone) < 40:
            continue
        pk = max(zone, key=lambda i: FC[i, 1])
        px, py, pz = FC[pk]
        base = np.median(FC[zone, 1])
        if py - base < 30:                               # нет выступа — пульта на этой стороне нет
            continue
        for i in zone:
            c = FC[i]
            near = np.hypot(c[0] - px, c[2] - pz) < 50
            if near and c[1] > py - 18:
                F[i][3] = names.index("joystick"); F[i][4:7] = [210, 70, 64]       # красная кнопка
            elif near and c[1] > py - 45:
                F[i][3] = names.index("joystick"); F[i][4:7] = [170, 174, 186]    # шток
            elif near and c[1] > base + 5:
                F[i][3] = names.index("boot"); F[i][4:7] = [30, 30, 36]          # пыльник
            elif abs(c[0] - px) < 110 and c[1] <= base + 25:
                F[i][3] = names.index("controller"); F[i][4:7] = [40, 42, 50]    # корпус пульта
        print(f"joystick peak at x={px:.0f} y={py:.0f} z={pz:.0f} (side {side:+d})")
# запасной вариант: джойстик не выделился выступом — берём верхушку пульта
if kind in ("m3", "power") and "joystick" in names and not any(f[3] == names.index("joystick") for f in F):
    ci = [i for i, f in enumerate(F) if names[f[3]] == "controller"]
    if ci:
        ys = sorted(FC[i, 1] for i in ci); cut = ys[int(len(ys) * 0.7)]
        top = [i for i in ci if FC[i, 1] >= cut]
        for i in top:
            F[i][3] = names.index("joystick"); F[i][4:7] = [210, 70, 64]
        print("joystick: верхушка пульта,", len(top), "граней")
# тёмные материалы светлее (иначе чёрная коляска сливается в силуэт): графит/обивка, оттенок сохраняем
for f in F:
    c = f[4:7]
    if max(c) < 70 and kind != "m3":               # поднимаем яркость, сохраняя оттенок (синева обивки не уходит в серый)
        k_ = 70.0 / max(max(c), 1)
        f[4:7] = [min(255, int(v * k_)) for v in c] if max(c) > 8 else [62, 62, 68]
# узнаваемые акценты пульта: экран и кнопка джойстика
d["parts"] = names
d["verts"] = [[round(c) for c in v] for v in (V if kind == "m3" else V0).tolist()]
json.dump(d, open(dst, "w"), separators=(",", ":"))
print("labels:", stats)
