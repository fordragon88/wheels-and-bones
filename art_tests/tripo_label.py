"""Разметка деталей облегчённой модели Tripo и запись в формат игры (assets/models/chair_<key>_ai[_lod].json).

python tripo_label.py <key>        (читает art_tests/tripo/<key>_full.npz; правила — SPECS ниже)

Правила по порядку, грань берёт первую подходящую деталь (по центру грани), остальное — «frame».
  wheel  — колесо: центр (x, y) и радиус уточняются по точкам обода; по расстоянию до оси:
           шина / обод / спицы / подшипник / ось, обруч (pushrim) — снаружи плоскости колеса;
  box    — коробка x/y/|z| (мм), можно ограничить стороной (z>0 / z<0).
Оси игры: x — вперёд, y — вверх, пол 0, z — вбок (пульт/правая сторона = +z), мм."""
import sys, json, math
import numpy as np
from scipy.spatial import cKDTree
import fast_simplification

INF = 1e9
SPECS = {
    # Баба Яга — Vermeiren D100 (складная стальная)
    "yaga": dict(art="chair_yaga", wheels=[
        dict(c=(-210, 300), R=290, z=(270, 350), kind="spoked"),
        dict(c=(190, 90), R=88, z=(185, 265), kind="caster")],
        boxes=[("caster_stem", (155, 245), (120, 280), (175, 275)),
               ("footrest", (335, 540), (110, 300), (0, INF)),
               ("brake", (-15, 70), (320, 470), (240, 315)),
               ("armrest", (-140, 110), (660, 730), (0, INF)),
               ("backrest", (-290, -105), (440, 950), (0, 300)),
               ("seat", (-170, 130), (430, 580), (0, 270))]),
    # Русалка — Panthera X3 (карбон)
    "rusalka": dict(art="chair_rusalka", wheels=[
        dict(c=(-110, 300), R=300, z=(225, 305), kind="spoked"),
        dict(c=(265, 48), R=50, z=(205, 275), kind="caster")],
        boxes=[("caster_stem", (235, 305), (55, 270), (195, 280)),
               ("footrest", (320, 430), (40, 240), (0, INF)),
               ("brake", (110, 210), (330, 430), (170, 270)),
               ("backrest", (-380, -250), (440, 780), (0, INF)),
               ("seat", (-170, 240), (440, 570), (0, 240))]),
    # Ра (бог солнца) — Quickie Nitrum + колёса с мотором в ступице (e-motion): ступицу дорисовываем
    "firebird": dict(art="chair_ra", wheels=[
        dict(c=(-100, 300), R=300, z=(245, 325), kind="spoked", hub=dict(r=105, w=55, part="motor")),
        dict(c=(280, 45), R=46, z=(205, 270), kind="caster")],
        boxes=[("caster_stem", (255, 325), (55, 200), (195, 275)),
               ("brake", (150, 250), (320, 445), (195, 300)),
               ("footrest", (300, 430), (40, 120), (0, 210)),
               ("backrest", (-260, -110), (560, 830), (0, INF)),
               ("seat", (-200, 280), (400, 570), (0, 250))],
        recolor_frame=(205, 45, 30)),
    # Леший — Magic Mobility Extreme X8 (4×4)
    "leshy": dict(art="chair_leshy", wheels=[
        dict(c=(-430, 215), R=215, z=(215, 355), kind="power"),
        dict(c=(200, 215), R=215, z=(215, 355), kind="power")],
        boxes=[("freewheel", (-700, -545), (250, 440), (0, 220)),
               ("joystick", (95, 240), (690, 860), (0, INF)),
               ("footrest", (300, 720), (200, 340), (0, INF)),
               ("motor", (-560, 330), (110, 320), (120, 215)),
               ("battery", (-330, 160), (140, 420), (0, 150)),
               ("backrest", (-420, -140), (720, 1400), (0, INF)),
               ("seat", (-160, 320), (600, 730), (0, INF))]),
    # Змей Горыныч — Pride Jazzy 614 (среднеприводная)
    "raiju": dict(art="chair_gorynych", wheels=[
        dict(c=(20, 160), R=160, z=(215, 310), kind="power"),
        dict(c=(345, 62), R=64, z=(215, 310), kind="caster"),
        dict(c=(-400, 62), R=64, z=(215, 310), kind="caster")],
        boxes=[("joystick", (90, 220), (600, 700), (0, INF)),
               ("controller", (40, 240), (540, 640), (150, INF)),
               ("breaker", (-400, -300), (230, 340), (0, 110)),
               ("freewheel", (-110, 60), (240, 310), (120, 235)),
               ("motor", (-80, 120), (80, 250), (110, 215)),
               ("battery", (-380, 10), (40, 330), (0, 200)),
               ("footrest", (290, 500), (60, 150), (0, INF)),
               ("backrest", (-420, -190), (480, 1010), (0, INF)),
               ("armrest", (-260, 120), (540, 660), (0, INF)),
               ("seat", (-280, 300), (340, 520), (0, INF))]),
}


def fit_circle(P):
    A = np.c_[2 * P[:, 0], 2 * P[:, 1], np.ones(len(P))]
    b = (P ** 2).sum(1)
    cx, cy, c = np.linalg.lstsq(A, b, rcond=None)[0]
    return cx, cy, math.sqrt(max(c + cx * cx + cy * cy, 1))


def refine_wheel(V, w):
    cx, cy = w["c"]
    R = w["R"]
    az = np.abs(V[:, 2])
    band = (az >= w["z"][0]) & (az <= w["z"][1])
    R0 = R
    for _ in range(4):                                   # центр — по кольцу, радиус — по самой внешней точке шины
        r = np.hypot(V[:, 0] - cx, V[:, 1] - cy)
        m = band & (r > 0.8 * R0) & (r < 1.15 * R0)
        if m.sum() < 50:
            break
        cx, cy, _ = fit_circle(V[m][:, :2])
    lowest = V[band & (np.abs(V[:, 0] - cx) < 0.3 * R0), 1]
    R = cy - (lowest.min() if len(lowest) else 0.0)      # колесо стоит на полу: радиус = высота оси над низом шины
    return cx, cy, R


def label(V, F, C, spec):
    names = ["frame"]

    def pid(n):
        if n not in names:
            names.append(n)
        return names.index(n)
    P = V[F].mean(1)
    az = np.abs(P[:, 2])
    lab = np.full(len(F), -1)
    wheels = []
    for w in spec["wheels"]:
        cx, cy, R = refine_wheel(V, w)
        wheels.append((cx, cy, R, w))
        r = np.hypot(P[:, 0] - cx, P[:, 1] - cy)
        inband = (az >= w["z"][0] - 5) & (az <= w["z"][1] + 5) & (r <= R * 1.06) & (lab < 0)
        k = w["kind"]
        if k == "caster":
            lab[inband & (r > 0.55 * R)] = pid("caster")
            lab[inband & (r <= 0.55 * R)] = pid("bearing" if "caster_bearing" in w else "caster")
            continue
        tire_w = 32 if k == "spoked" else 0.3 * R
        tire_r = (r >= R - tire_w)
        plane = np.median(az[inband & tire_r]) if (inband & tire_r).any() else np.mean(w["z"])
        if k == "spoked":
            push = inband & (az > plane + 14) & (r > 0.72 * R)
            lab[push] = pid("rear_wheel")
            rest = inband & ~push
            lab[rest & tire_r] = pid("tire")
            lab[rest & (r >= R - 52) & ~tire_r] = pid("rim")
            lab[rest & (r < 34)] = pid("axle")
            lab[rest & (r >= 34) & (r < 62)] = pid("bearing")
            lab[rest & (r >= 62) & (r < R - 52)] = pid("spokes")
        else:                                            # электро: толстая шина, диск, ось
            lab[inband & tire_r] = pid("tire")
            lab[inband & ~tire_r & (r >= 0.18 * R)] = pid("rim")
            lab[inband & (r < 0.18 * R)] = pid("axle")
    for name, (x0, x1), (y0, y1), (z0, z1) in spec["boxes"]:
        m = (lab < 0) & (P[:, 0] >= x0) & (P[:, 0] <= x1) & (P[:, 1] >= y0) & (P[:, 1] <= y1) & (az >= z0) & (az <= z1)
        lab[m] = pid(name)
    lab[lab < 0] = 0
    return lab, names, wheels


def add_hubs(V, F, C, lab, names, wheels):
    """Ступица с мотором и батареей (как у e-motion): толстый диск на каждом заднем колесе."""
    for cx, cy, R, w in wheels:
        h = w.get("hub")
        if not h:
            continue
        if h["part"] not in names:
            names.append(h["part"])
        p = names.index(h["part"])
        for side in (-1, 1):
            zc = side * (np.mean(w["z"]) - h["w"] * 0.25)
            n = 28
            base = len(V)
            ring = []
            for z in (zc - h["w"] / 2, zc + h["w"] / 2):
                for i in range(n):
                    a = 2 * math.pi * i / n
                    ring.append((cx + h["r"] * math.cos(a), cy + h["r"] * math.sin(a), z))
            ring += [(cx, cy, zc - h["w"] / 2), (cx, cy, zc + h["w"] / 2)]
            V = np.vstack([V, ring])
            nf = []
            for i in range(n):
                j = (i + 1) % n
                nf += [(base + i, base + j, base + n + j), (base + i, base + n + j, base + n + i),
                       (base + 2 * n, base + j, base + i), (base + 2 * n + 1, base + n + i, base + n + j)]
            F = np.vstack([F, nf])
            col = np.tile([[62, 62, 70]], (len(ring), 1)).astype(np.float32)
            col[n:2 * n] = (90, 92, 104) if side > 0 else (62, 62, 70)
            C = np.vstack([C, col])
            lab = np.r_[lab, np.full(len(nf), p)]
    return V, F, C, lab, names


def to_json(V, F, C, lab, names, src):
    Cf = np.clip(C[F].mean(1), 0, 255).astype(int)
    faces = [[int(a), int(b), int(c), int(l), int(r), int(g), int(bl)]
             for (a, b, c), l, (r, g, bl) in zip(F, lab, Cf)]
    return dict(verts=[[round(float(x), 1) for x in v] for v in V], faces=faces, parts=names, cull=False, source=src)


if __name__ == "__main__":
    key = sys.argv[1]
    spec = SPECS[key]
    d = np.load(f"art_tests/tripo/{key}_full.npz")
    V, F, C = d["V"], d["F"], d["C"]
    if "--target" in sys.argv:                           # меньше граней для «полной» модели игры
        t = int(sys.argv[sys.argv.index("--target") + 1])
        Vs, Fs = fast_simplification.simplify(V.astype(np.float32), F.astype(np.int32), target_reduction=1 - t / len(F))
        _, idx = cKDTree(V).query(Vs, k=4)
        V, F, C = Vs.astype(float), Fs.astype(np.int64), C[idx].mean(1)
    lab, names, wheels = label(V, F, C, spec)
    if spec.get("recolor_frame"):                        # перекраска светлых труб рамы
        Cf = C[F].mean(1)
        lum = Cf.mean(1)
        tgt = np.array(spec["recolor_frame"], float)
        m = (lab == 0) & (lum > 70)
        for fi in np.nonzero(m)[0]:
            k = lum[fi] / 170.0
            C[F[fi]] = np.clip(tgt * k, 0, 255)
    V, F, C, lab, names = add_hubs(V, F, C, lab, names, wheels)
    np.savez_compressed(f"art_tests/tripo/{key}_labels.npz", lab=lab, names=np.array(names))
    np.savez_compressed(f"art_tests/tripo/{key}_labeled_mesh.npz", V=V, F=F, C=C, lab=lab, names=np.array(names))
    for cx, cy, R, w in wheels:
        print(f"  колесо {w['kind']}: центр ({cx:.0f}, {cy:.0f}) R {R:.0f}")
    cnt = np.bincount(lab, minlength=len(names))
    print("  детали:", {n: int(c) for n, c in zip(names, cnt)})
    out = f"art_tests/tripo/models/{spec['art']}_ai.json"   # в assets/ — только официальные файлы с подписки Tripo
    json.dump(to_json(V, F, C, lab, names, "Tripo"), open(out, "w"), separators=(",", ":"))
    # облегчённая копия для окна диагностики: детали — по ближайшей грани полной модели
    Vs, Fs = fast_simplification.simplify(V.astype(np.float32), F.astype(np.int32), target_reduction=1 - 11000 / len(F))
    Pc_full = V[F].mean(1)
    tree = cKDTree(Pc_full)
    _, fi = tree.query(Vs[Fs].mean(1))
    labs = lab[fi]
    _, vi = cKDTree(V).query(Vs, k=4)
    json.dump(to_json(Vs.astype(float), Fs.astype(np.int64), C[vi].mean(1), labs, names, "Tripo"),
              open(out.replace(".json", "_lod.json"), "w"), separators=(",", ":"))
    print("  записано:", out, len(F), "граней; lod", len(Fs))
