"""Разметка деталей облегчённой модели Tripo и запись в формат игры (assets/models/chair_<key>_ai[_lod].json).

python tripo_label.py <key> [--target N] [--dir D]   (читает D/<key>_full.npz, пишет в D и D/models; D по умолчанию
                                                      art_tests/tripo; правила — SPECS ниже)

Правила по порядку, грань берёт первую подходящую деталь (по центру грани), остальное — «frame».
  wheel  — колесо: центр (x, y) и радиус уточняются по точкам обода; по расстоянию до оси:
           шина / обод / спицы / подшипник / ось, обруч (pushrim) — снаружи плоскости колеса;
  box    — коробка x/y/|z| (мм), можно ограничить стороной (z>0 / z<0).
До разметки — правка геометрии: drop (убрать грани в коробке x/y/|z|, можно светлее lum) и move (перенести
грани в коробке x/y/z на d; общие с остальной моделью вершины копируются).
Оси игры: x — вперёд, y — вверх, пол 0, z — вбок (пульт/правая сторона = +z), мм."""
import os, sys, json, math
import numpy as np
from scipy.spatial import cKDTree
import fast_simplification
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

INF = 1e9
SPECS = {
    # Баба Яга — Vermeiren D100 (складная стальная)
    "yaga": dict(art="chair_yaga", spokes=36, wheels=[
        dict(c=(-210, 300), R=290, z=(270, 350), kind="spoked"),
        dict(c=(190, 90), R=88, z=(185, 265), kind="caster")],
        boxes=[("caster_stem", (155, 245), (120, 280), (175, 275)),
               ("footrest", (335, 540), (110, 300), (0, INF)),
               ("brake", (-15, 70), (320, 470), (240, 315)),
               ("armrest", (-140, 110), (660, 730), (0, INF)),
               ("backrest", (-290, -105), (440, 950), (0, 300)),
               ("seat", (-170, 130), (430, 580), (0, 270))]),
    # Русалка — Panthera X3 (карбон)
    "rusalka": dict(art="chair_rusalka", spokes=24, wheels=[
        dict(c=(-110, 300), R=300, z=(225, 305), kind="spoked"),
        dict(c=(265, 48), R=50, z=(205, 275), kind="caster")],
        drop=[dict(x=(-420, -322), y=(480, 680), az=(100, 230)),          # «рога» за спинкой — мусор Tripo
              dict(x=(-322, -306), y=(570, 680), az=(100, 230), lum=45)],
        boxes=[("caster_stem", (235, 305), (55, 270), (195, 280)),
               ("footrest", (320, 430), (40, 240), (0, INF)),
               ("brake", (110, 210), (330, 430), (170, 270)),
               ("backrest", (-380, -250), (440, 780), (0, INF)),
               ("seat", (-170, 240), (440, 570), (0, 240))]),
    # Ра (бог солнца) — Quickie Nitrum + колёса с мотором в ступице (e-motion): ступицу дорисовываем
    "firebird": dict(art="chair_ra", spokes=24, wheels=[
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
        # Tripo поставил пульт по центру перед сиденьем — переносим на правый подлокотник (как у X8 и под правой
        # рукой Лешего на рисунке); наклонную панель пульта убираем — на рисунке её нет
        move=[dict(x=(0, 340), y=(628, 900), z=(-110, 120), d=(-40, 0, 255))],
        drop=[dict(x=(-130, 100), y=(630, 700), az=(0, 70)),                 # остаток крепления пульта на сиденье
              dict(x=(205, 345), y=(740, 905), az=(0, 125))],                # наклонная панель пульта
        boxes=[("freewheel", (-700, -545), (250, 440), (0, 220)),
               ("joystick", (78, 300), (690, 860), (180, INF)),
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


def edit(V, F, C, spec):
    P = V[F].mean(1)
    L = C[F][:, :, :3].mean((1, 2))                      # яркость (у C могут быть ещё столбцы — UV и т.п.)
    keep = np.ones(len(F), bool)
    for b in spec.get("drop", []):
        az = np.abs(P[:, 2])
        keep &= ~((P[:, 0] >= b["x"][0]) & (P[:, 0] < b["x"][1]) & (P[:, 1] >= b["y"][0]) & (P[:, 1] <= b["y"][1])
                  & (az >= b["az"][0]) & (az <= b["az"][1]) & (L > b.get("lum", -1)))
    for b in spec.get("move", []):
        m = keep & (P[:, 0] >= b["x"][0]) & (P[:, 0] <= b["x"][1]) & (P[:, 1] >= b["y"][0]) & (P[:, 1] <= b["y"][1])             & (P[:, 2] >= b["z"][0]) & (P[:, 2] <= b["z"][1])
        vi = np.unique(F[m])
        remap = np.full(len(V), -1)
        remap[vi] = len(V) + np.arange(len(vi))
        V = np.vstack([V, V[vi] + np.asarray(b["d"], float)])
        C = np.vstack([C, C[vi]])
        F = F.copy()
        F[m] = remap[F[m]]
    F = F[keep]
    used = np.unique(F)                                  # убрать осиротевшие вершины
    remap = np.full(len(V), -1)
    remap[used] = np.arange(len(used))
    return V[used], remap[F], C[used]


def in_wheels(P, spec):
    """Грани в объёме колёс (спицы — тонкие и часто отдельные куски: их чистка не трогает)."""
    m = np.zeros(len(P), bool)
    az = np.abs(P[:, 2])
    for w in spec["wheels"]:
        r = np.hypot(P[:, 0] - w["c"][0], P[:, 1] - w["c"][1])
        m |= (r <= w["R"] * 1.08) & (az >= w["z"][0] - 25) & (az <= w["z"][1] + 25)
    return m


def despike(V, F, C, spec, small=40, ratio=12.0, min_len=18.0):
    """Мусор генерации вне колёс: маленькие отдельные куски (< small граней) и «иглы» — вытянутые грани
    с открытым краем (шипы и лохмотья; трубы рамы замкнуты, их длинные грани не трогаются)."""
    q = np.round(V * 10).astype(np.int64)
    _, inv = np.unique(q, axis=0, return_inverse=True)
    W = inv.ravel()[F]                                   # вершины, склеенные по месту
    P = V[F].mean(1)
    wh = in_wheels(P, spec)
    drop = np.zeros(len(F), bool)
    n = W.max() + 1
    r_ = np.r_[W[:, 0], W[:, 1]]
    c_ = np.r_[W[:, 1], W[:, 2]]
    k, lab = connected_components(coo_matrix((np.ones(len(r_)), (r_, c_)), shape=(n, n)), directed=False)
    fl = lab[W[:, 0]]
    size = np.bincount(fl, minlength=k)
    drop |= (size[fl] < small) & ~wh
    E = np.sort(np.r_[W[:, [0, 1]], W[:, [1, 2]], W[:, [2, 0]]], axis=1)
    key = E[:, 0] * n + E[:, 1]
    _, ei, cnt = np.unique(key, return_inverse=True, return_counts=True)
    open_edge = (cnt[ei] == 1).reshape(3, -1).T.any(1)
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    L = np.c_[np.linalg.norm(b - a, axis=1), np.linalg.norm(c - b, axis=1), np.linalg.norm(a - c, axis=1)]
    area = np.linalg.norm(np.cross(b - a, c - a), axis=1) / 2
    lmax = L.max(1)
    thin = lmax / np.maximum(2 * area / np.maximum(lmax, 1e-9), 1e-9)   # длина / высота
    drop |= open_edge & (thin > ratio) & (lmax > min_len) & ~wh
    print(f"  чистка: кусков {int(((size[fl] < small) & ~wh).sum())} граней, игл {int((drop).sum())} граней всего")
    F = F[~drop]
    used = np.unique(F)
    remap = np.full(len(V), -1)
    remap[used] = np.arange(len(used))
    return V[used], remap[F], C[used]


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
        wheels[-1] = (cx, cy, R, dict(w, plane=float(plane)))
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


def make_spokes(wheels, n_spokes):
    """Ровные спицы вместо спиц Tripo (тонкие спицы при облегчении рвутся на «чёрточки»): на каждом заднем
    колесе с обеих сторон коляски — n спиц от фланцев ступицы к ободу, перекрёстная (тангенциальная) спицовка.
    Спица — трёхгранная палочка ~5 мм (тоньше в окне игры не видно). Возврат: V, F, C."""
    Vs, Fs, Cs = [], [], []
    for cx, cy, R, w in wheels:
        if w["kind"] != "spoked":
            continue
        plane = w.get("plane", float(np.mean(w["z"])))
        r0 = (w["hub"]["r"] - 8) if w.get("hub") else 32
        r1 = R - 46                                          # внутренний край обода
        for side in (-1, 1):
            for i in range(n_spokes):
                a = 2 * math.pi * i / n_spokes
                fl = -18 if i % 2 else 8                         # два фланца ступицы
                da = 0.30 if (i // 2) % 2 else -0.30           # перекрёст: спица уходит к ободу со сдвигом
                p0 = np.array([cx + r0 * math.cos(a), cy + r0 * math.sin(a), side * (plane + fl)])
                p1 = np.array([cx + r1 * math.cos(a + da), cy + r1 * math.sin(a + da), side * plane])
                d = p1 - p0
                d /= np.linalg.norm(d)
                u = np.cross(d, [0, 0, 1.0])
                u /= np.linalg.norm(u)
                v = np.cross(d, u)
                base = sum(len(x) for x in Vs)
                ring = [2.6 * (math.cos(t) * u + math.sin(t) * v) for t in (0, 2.094, 4.189)]
                Vs.append(np.array([p0 + q for q in ring] + [p1 + q for q in ring]))
                Fs.append(np.array([(base + j, base + (j + 1) % 3, base + 3 + (j + 1) % 3) for j in range(3)] +
                                   [(base + j, base + 3 + (j + 1) % 3, base + 3 + j) for j in range(3)]))
                Cs.append(np.tile([[176, 179, 186]], (6, 1)))
    if not Vs:
        return np.zeros((0, 3)), np.zeros((0, 3), np.int64), np.zeros((0, 3))
    return np.vstack(Vs), np.vstack(Fs), np.vstack(Cs).astype(float)


def to_json(V, F, C, lab, names, src):
    Cf = np.clip(C[F].mean(1), 0, 255).astype(int)
    faces = [[int(a), int(b), int(c), int(l), int(r), int(g), int(bl)]
             for (a, b, c), l, (r, g, bl) in zip(F, lab, Cf)]
    return dict(verts=[[round(float(x), 1) for x in v] for v in V], faces=faces, parts=names, cull=False, source=src)


if __name__ == "__main__":
    key = sys.argv[1]
    spec = SPECS[key]
    D = sys.argv[sys.argv.index("--dir") + 1] if "--dir" in sys.argv else "art_tests/tripo"
    d = np.load(f"{D}/{key}_full.npz")
    V, F, C = edit(d["V"], d["F"], d["C"], spec)
    if "--target" in sys.argv:                           # меньше граней для «полной» модели игры
        t = int(sys.argv[sys.argv.index("--target") + 1])
        Vs, Fs = fast_simplification.simplify(V.astype(np.float32), F.astype(np.int32), target_reduction=1 - t / len(F))
        _, idx = cKDTree(V).query(Vs, k=4)
        V, F, C = Vs.astype(float), Fs.astype(np.int64), C[idx].mean(1)
    if "--no-despike" not in sys.argv:
        V, F, C = despike(V, F, C, spec)
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
    SV = np.zeros((0, 3))
    if spec.get("spokes") and "spokes" in names:          # спицы Tripo -> ровные спицы (добавляются после облегчения)
        keep = lab != names.index("spokes")
        F, lab = F[keep], lab[keep]
        SV, SF, SC = make_spokes(wheels, spec["spokes"])
    np.savez_compressed(f"{D}/{key}_labels.npz", lab=lab, names=np.array(names))
    np.savez_compressed(f"{D}/{key}_labeled_mesh.npz", V=V, F=F, C=C, lab=lab, names=np.array(names))
    for cx, cy, R, w in wheels:
        print(f"  колесо {w['kind']}: центр ({cx:.0f}, {cy:.0f}) R {R:.0f}")
    cnt = np.bincount(lab, minlength=len(names))
    print("  детали:", {n: int(c) for n, c in zip(names, cnt)})
    os.makedirs(f"{D}/models", exist_ok=True)
    out = f"{D}/models/{spec['art']}_ai.json"   # в assets/ — только официальные файлы с подписки Tripo
    def with_spokes(V, F, C, lab):
        if not len(SV):
            return V, F, C, lab
        return (np.vstack([V, SV]), np.vstack([F, SF + len(V)]), np.vstack([C, SC]),
                np.r_[lab, np.full(len(SF), names.index("spokes"))])
    json.dump(to_json(*with_spokes(V, F, C, lab), names, "Tripo"), open(out, "w"), separators=(",", ":"))
    # облегчённая копия для окна диагностики: детали — по ближайшей грани полной модели
    Vs, Fs = fast_simplification.simplify(V.astype(np.float32), F.astype(np.int32), target_reduction=1 - 11000 / len(F))
    Pc_full = V[F].mean(1)
    tree = cKDTree(Pc_full)
    _, fi = tree.query(Vs[Fs].mean(1))
    labs = lab[fi]
    _, vi = cKDTree(V).query(Vs, k=4)
    json.dump(to_json(*with_spokes(Vs.astype(float), Fs.astype(np.int64), C[vi].mean(1), labs), names, "Tripo"),
              open(out.replace(".json", "_lod.json"), "w"), separators=(",", ":"))
    print("  записано:", out, len(F), "граней; lod", len(Fs))
