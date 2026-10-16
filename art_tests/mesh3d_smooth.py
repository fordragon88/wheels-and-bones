"""Шлифовка готовой модели игры: меньше «шероховатости» + облегчённая копия для окна диагностики.
python art_tests/mesh3d_smooth.py <in.json> <out.json> [lod.json] [итераций_формы] [размер_ячейки_lod_мм]
1) склейка совпадающих вершин;
2) сглаживание Таубина (λ/μ) — убирает бугры, почти не «сдувая» модель;
3) цвет: среднее с соседними гранями той же детали и близкого цвета (границы материалов остаются);
4) LOD: кластеризация вершин по сетке — в маленьком окне разница не видна, граней в разы меньше."""
import sys, json
import numpy as np

src, dst = sys.argv[1], sys.argv[2]
lod_out = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "-" else None
SHAPE_IT = int(sys.argv[4]) if len(sys.argv) > 4 else 6
CELL = float(sys.argv[5]) if len(sys.argv) > 5 else 11.0
KEEP = {"joystick", "boot", "valve"}                 # мелкие акценты — форму не трогаем

d = json.load(open(src))
V = np.asarray(d["verts"], float)
Fa = np.asarray(d["faces"], np.int64)
F, PI, COL = Fa[:, :3], Fa[:, 3], Fa[:, 4:7].astype(float)
names = d["parts"]

# 1) склейка вершин
key, inv = np.unique(V.round(2), axis=0, return_inverse=True)
inv = inv.ravel()
V, F = key, inv[F]
ok = (F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])
F, PI, COL = F[ok], PI[ok], COL[ok]
nV = len(V)

# рёбра (неориентированные) -> соседи вершин
E = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
E = np.unique(np.sort(E, 1), axis=0)
deg = np.bincount(E.ravel(), minlength=nV).astype(float)
fixed = np.zeros(nV, bool)
for i, p in enumerate(names):
    if p in KEEP:
        fixed[F[PI == i].ravel()] = True


def lap(P):
    acc = np.zeros_like(P)
    np.add.at(acc, E[:, 0], P[E[:, 1]])
    np.add.at(acc, E[:, 1], P[E[:, 0]])
    L = acc / np.maximum(deg, 1)[:, None] - P
    L[deg == 0] = 0
    L[fixed] = 0
    return L


# 2) Таубин
for _ in range(SHAPE_IT):
    V = V + 0.5 * lap(V)
    V = V - 0.53 * lap(V)
V[:, 1] -= V[:, 1].min()                              # пол остаётся на y=0

# 3) цвет по соседним граням (общее ребро), только та же деталь и близкий цвет
fe = np.concatenate([np.sort(F[:, [0, 1]], 1), np.sort(F[:, [1, 2]], 1), np.sort(F[:, [2, 0]], 1)])
fid = np.tile(np.arange(len(F)), 3)
ek = fe[:, 0] * nV + fe[:, 1]
order = np.argsort(ek)
ek, fid = ek[order], fid[order]
same = ek[1:] == ek[:-1]
A, B = fid[:-1][same], fid[1:][same]                  # пары граней с общим ребром
A, B = np.concatenate([A, B]), np.concatenate([B, A])
lock = np.isin(PI, [i for i, p in enumerate(names) if p in KEEP])
for _ in range(4):
    dcol = np.abs(COL[A] - COL[B]).max(1)
    m = (PI[A] == PI[B]) & (dcol < 46)
    acc = COL.copy(); cnt = np.ones(len(F))
    np.add.at(acc, A[m], COL[B[m]]); np.add.at(cnt, A[m], 1)
    new = acc / cnt[:, None]
    COL = np.where(lock[:, None], COL, new)


def dump(path, V_, F_, PI_, COL_):
    faces = np.concatenate([F_, PI_[:, None], np.clip(COL_.round(), 0, 255).astype(np.int64)], 1)
    out = dict(d)
    out["verts"] = V_.round(1).tolist()
    out["faces"] = faces.tolist()
    json.dump(out, open(path, "w"), separators=(",", ":"))


dump(dst, V, F, PI, COL)
print(f"{src}: граней {len(Fa)} -> {len(F)}, вершин {len(d['verts'])} -> {nV}")

# 4) LOD: кластеризация вершин по сетке; ячейка растёт от CELL, пока граней больше LOD_MAX
LOD_MAX = 12000


def cluster(cs):
    cell = np.floor(V / cs).astype(np.int64)
    ck, cinv = np.unique(cell, axis=0, return_inverse=True)
    cinv = cinv.ravel()
    cnt = np.bincount(cinv).astype(float)
    LV = np.zeros((len(ck), 3))
    np.add.at(LV, cinv, V)
    LV /= cnt[:, None]
    LF = cinv[F]
    ok = (LF[:, 0] != LF[:, 1]) & (LF[:, 1] != LF[:, 2]) & (LF[:, 0] != LF[:, 2])
    LF, LP, LC = LF[ok], PI[ok], COL[ok]
    sk = np.sort(LF, 1)                               # дубли граней (с любым обходом) -> одна
    _, first, finv = np.unique(sk, axis=0, return_index=True, return_inverse=True)
    finv = finv.ravel()
    csum = np.zeros((len(first), 3)); np.add.at(csum, finv, LC)
    return LV, LF[first], LP[first], csum / np.bincount(finv).astype(float)[:, None]


if lod_out:
    cs = CELL
    while True:
        lod = cluster(cs)
        if len(lod[1]) <= LOD_MAX or cs > 40:
            break
        cs *= 1.15
    # все детали задания должны пережить упрощение
    lost = set(PI.tolist()) - set(lod[2].tolist())
    dump(lod_out, *lod)
    print(f"  LOD {cs:.0f} мм: граней {len(lod[1])}" + (f", потеряны: {[names[i] for i in lost]}" if lost else ""))
