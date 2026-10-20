"""Модель из Tripo (GLB с текстурой, ~2 млн треугольников) -> модель игры (assets/models/*.json).

Шаг 1 (этот скрипт): только меш нулевого узла (остальное в файле вьюпорта — оси/сетка), мировая матрица,
цвет из baseColor-текстуры в вершины, отсев оторванных кусков (артефакты фона), оси игры
(x — вперёд к подножкам, y — вверх, пол y=0, z — вбок, мм; масштаб по известному размеру),
облегчение (fast_simplification) до full/lod. Разметка деталей — tripo_label.py.

Запуск (нужен venv с fast-simplification, scipy, pillow):
  python tripo_convert.py <in.glb> <out_prefix> <axis>=<mm> [--flip-z] [--yaw 0|90|180|270]
  axis: length (вдоль x) | width (вдоль z) | height (y)
Пишет <out_prefix>_full.npz (вершины, грани, цвета вершин) и превью <out_prefix>_views.png."""
import sys, json, struct, io, math
import numpy as np
from PIL import Image, ImageDraw
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
import fast_simplification

CT = {5126: np.float32, 5121: np.uint8, 5123: np.uint16, 5125: np.uint32}
NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def read_glb(path):
    raw = open(path, "rb").read()
    jl = struct.unpack("<I", raw[12:16])[0]
    js = json.loads(raw[20:20 + jl])
    bin_ = raw[20 + jl + 8:]

    def acc(i):
        a = js["accessors"][i]
        bv = js["bufferViews"][a["bufferView"]]
        dt, n = np.dtype(CT[a["componentType"]]), NC[a["type"]]
        return np.frombuffer(bin_, dtype=dt, count=a["count"] * n,
                             offset=bv.get("byteOffset", 0) + a.get("byteOffset", 0)).reshape(a["count"], n)

    def node_mat(n):
        if "matrix" in n:
            return np.array(n["matrix"], float).reshape(4, 4).T
        M = np.eye(4)
        x, y, z, w = n.get("rotation", [0, 0, 0, 1])
        R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                      [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                      [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
        M[:3, :3] = R * np.array(n.get("scale", [1, 1, 1]))
        M[:3, 3] = n.get("translation", [0, 0, 0])
        return M
    world = {}

    def walk(i, P):
        W = P @ node_mat(js["nodes"][i])
        world[i] = W
        for c in js["nodes"][i].get("children", []):
            walk(c, W)
    for r in js["scenes"][js.get("scene", 0)]["nodes"]:
        walk(r, np.eye(4))
    ni = next(i for i, n in enumerate(js["nodes"]) if n.get("mesh") == 0)
    pr = js["meshes"][0]["primitives"][0]
    A = pr["attributes"]
    V = acc(A["POSITION"]).astype(np.float64)
    V = (np.c_[V, np.ones(len(V))] @ world[ni].T)[:, :3]
    F = acc(pr["indices"]).reshape(-1, 3).astype(np.int64)
    UV = acc(A["TEXCOORD_0"]).astype(np.float64)
    mat = js["materials"][pr["material"]]
    tex_i = js["textures"][mat["pbrMetallicRoughness"]["baseColorTexture"]["index"]]["source"]
    bv = js["bufferViews"][js["images"][tex_i]["bufferView"]]
    tex = Image.open(io.BytesIO(bin_[bv.get("byteOffset", 0):bv.get("byteOffset", 0) + bv["byteLength"]])).convert("RGB")
    T = np.asarray(tex)
    h, w = T.shape[:2]
    u = np.clip((UV[:, 0] % 1.0) * (w - 1), 0, w - 1)
    v = np.clip((UV[:, 1] % 1.0) * (h - 1), 0, h - 1)    # glTF: v сверху вниз — как у картинки
    C = T[v.astype(int), u.astype(int)].astype(np.float32)
    return V, F, C


def keep_attached(V, F, cell):
    """Оставить «коляску» — самый большой кусок, связный через заполненные воксели (cell мм, соседство 26).
    Меш Tripo — сотни отдельных кусков; оторванные артефакты фона лежат в стороне и отпадают."""
    vox = np.floor(V / cell).astype(np.int64)
    uv, inv = np.unique(vox, axis=0, return_inverse=True)
    inv = inv.ravel()
    idx = {tuple(v): i for i, v in enumerate(uv.tolist())}
    rows, cols = [], []
    offs = [(dx, dy, dz) for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1) if (dx, dy, dz) != (0, 0, 0)]
    for i, (x, y, z) in enumerate(uv.tolist()):
        for dx, dy, dz in offs:
            j = idx.get((x + dx, y + dy, z + dz))
            if j is not None:
                rows.append(i); cols.append(j)
    nv = len(uv)
    k, lab = connected_components(coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(nv, nv)), directed=False)
    weight = np.bincount(lab[inv], minlength=k)           # вершин в кластере
    main = int(np.argmax(weight))
    keepv = lab[inv] == main
    dropped = int((~keepv).sum())
    fk = keepv[F].all(1)
    remap = -np.ones(len(V), np.int64)
    remap[keepv] = np.arange(keepv.sum())
    return V[keepv], remap[F[fk]], keepv, dropped, k, 1


def orient(V, axis_mm, flip_z=False, yaw=0):
    """Оси игры: y — вверх (у Tripo тоже y), x — вперёд: туда, где НЕТ спинки (верх модели — сзади)."""
    V = V - V.mean(0)
    if yaw:
        a = math.radians(yaw)
        x, z = V[:, 0] * math.cos(a) + V[:, 2] * math.sin(a), -V[:, 0] * math.sin(a) + V[:, 2] * math.cos(a)
        V = np.c_[x, V[:, 1], z]
    ext = V.max(0) - V.min(0)
    if ext[2] > ext[0]:                                  # длинная горизонтальная ось — x
        V = np.c_[V[:, 2], V[:, 1], -V[:, 0]]
    top = V[:, 1] > V[:, 1].min() + 0.8 * (V[:, 1].max() - V[:, 1].min())
    if V[top, 0].mean() > V[:, 0].mean():                # спинка/подголовник — сзади (x меньше)
        V = np.c_[-V[:, 0], V[:, 1], -V[:, 2]]
    if flip_z:
        V[:, 2] = -V[:, 2]
    name, mm = axis_mm
    i = {"length": 0, "height": 1, "width": 2}[name]
    V = V * (mm / (V[:, i].max() - V[:, i].min()))
    V[:, 1] -= V[:, 1].min()
    V[:, 0] -= (V[:, 0].max() + V[:, 0].min()) / 2
    V[:, 2] -= (V[:, 2].max() + V[:, 2].min()) / 2
    return V


def decimate(V, F, C, target):
    ratio = 1.0 - target / len(F)
    Vs, Fs = fast_simplification.simplify(V.astype(np.float32), F.astype(np.int32), target_reduction=ratio, agg=6)
    _, idx = cKDTree(V).query(Vs, k=12)                  # цвет — среднее 12 ближайших исходных точек (без «пятен»)
    return Vs.astype(np.float64), Fs.astype(np.int64), C[idx].mean(1)


def render(V, F, C, path, size=520):
    """Превью: 4 вида с миллиметровой сеткой (по 100 мм) — по нему пишутся области деталей."""
    views = [("side (x->)", lambda P: (P[:, 0], P[:, 1]), lambda P: P[:, 2]),
             ("front", lambda P: (-P[:, 2], P[:, 1]), lambda P: P[:, 0]),
             ("top", lambda P: (P[:, 0], -P[:, 2]), lambda P: P[:, 1]),
             ("3/4", lambda P: (P[:, 0] * 0.73 + P[:, 2] * 0.68, P[:, 1] * 0.95 + (-P[:, 0] * 0.68 + P[:, 2] * 0.73) * 0.3),
              lambda P: -P[:, 0] * 0.68 + P[:, 2] * 0.73)]
    sheet = Image.new("RGB", (size * 4, size + 24), "white")
    lim = np.abs(V).max() * 1.05 + 1
    cen = F.mean if False else None
    Pc = V[F].mean(1)
    Cf = C[F].mean(1)
    for k, (title, proj, depth) in enumerate(views):
        im = Image.new("RGB", (size, size), (250, 250, 250))
        d = ImageDraw.Draw(im)
        s = size / (2 * lim)

        def to(x, y):
            return size / 2 + x * s, size - 20 - y * s if k != 2 else size / 2 - y * s
        for g in range(-1500, 1501, 100):
            x0, y0 = to(g, -1500)
            x1, y1 = to(g, 1500)
            d.line([(x0, y0), (x1, y1)], fill=(225, 225, 235) if g % 500 else (190, 190, 210))
            x0, y0 = to(-1500, g)
            x1, y1 = to(1500, g)
            d.line([(x0, y0), (x1, y1)], fill=(225, 225, 235) if g % 500 else (190, 190, 210))
        order = np.argsort(depth(Pc))
        X, Y = proj(V)
        for fi in order:
            a, b, c = F[fi]
            pts = [to(X[a], Y[a]), to(X[b], Y[b]), to(X[c], Y[c])]
            d.polygon(pts, fill=tuple(int(t) for t in Cf[fi]))
        d.text((6, 4), title + "  grid 100 mm", fill=(200, 0, 0))
        sheet.paste(im, (k * size, 0))
    sheet.save(path)


if __name__ == "__main__":
    src, prefix, ax = sys.argv[1], sys.argv[2], sys.argv[3]
    name, mm = ax.split("=")
    yaw = int(sys.argv[sys.argv.index("--yaw") + 1]) if "--yaw" in sys.argv else 0
    V, F, C = read_glb(src)
    print("исходник:", len(V), "вершин,", len(F), "треугольников")
    # склейка: Tripo режет вершины по швам текстуры — без склейки облегчение раскрывает швы дырами
    q = np.round(V / (np.abs(V).max() * 1e-5)).astype(np.int64)
    _, first, inv = np.unique(q, axis=0, return_index=True, return_inverse=True)
    inv = inv.ravel()
    Cw = np.zeros((len(first), 3)); cnt = np.bincount(inv, minlength=len(first))[:, None]
    np.add.at(Cw, inv, C)
    V, C, F = V[first], (Cw / np.maximum(cnt, 1)).astype(np.float32), inv[F]
    F = F[(F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])]
    print("после склейки:", len(V), "вершин")
    V = orient(V, (name, float(mm)), "--flip-z" in sys.argv, yaw)
    V, F, keep, dropped, ncomp, nkept = keep_attached(V, F, cell=12.0)
    C = C[keep]
    V = orient(V, (name, float(mm)), "--flip-z" in sys.argv, 0)     # габарит — уже без мусора
    print(f"кластеров {ncomp}, выброшено вершин {dropped}")
    V, F, C = decimate(V, F, C, 40000)
    V[:, 1] -= V[:, 1].min()
    print("после облегчения:", len(V), "вершин,", len(F), "треугольников; габарит мм:", (V.max(0) - V.min(0)).round())
    np.savez_compressed(prefix + "_full.npz", V=V, F=F, C=C)
    render(V, F, C, prefix + "_views.png")
