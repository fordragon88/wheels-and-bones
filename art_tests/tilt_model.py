"""Наклон в пространстве (tilt-in-space) для готовой модели игры (assets/models/*.json): сиденье со спинкой,
подлокотниками и подножками поворачивается назад; колёса, касторы, тормоза, антиопрокидыватели и низ рамы — на
месте. Общие вершины копируются (база не тянется за сиденьем).
python art_tests/tilt_model.py <in.json> <out.json> <градусы> <pivot_x> <pivot_y> <base_y> <front_x> [детали_на_базе,…]
Оси модели: x — вперёд, y — вверх, мм."""
import json, math, sys

src, dst = sys.argv[1], sys.argv[2]
deg, px, py, base_y, front_x = (float(v) for v in sys.argv[3:8])
keep = set(sys.argv[8].split(",")) if len(sys.argv) > 8 else set()
d = json.load(open(src, encoding="utf-8"))
V, F, names = d["verts"], d["faces"], d["parts"]
keep_i = {i for i, n in enumerate(names) if n in keep}
a = math.radians(deg)
ca, sa = math.cos(a), math.sin(a)
copy = {}
n_rot = 0
for f in F:
    if f[3] in keep_i:
        continue
    cx = sum(V[i][0] for i in f[:3]) / 3
    cy = sum(V[i][1] for i in f[:3]) / 3
    if cy <= base_y and cx <= front_x:
        continue
    n_rot += 1
    for k in range(3):
        i = f[k]
        if i not in copy:
            x, y, z = V[i]
            dx, dy = x - px, y - py
            copy[i] = len(V)
            V.append([round(px + dx * ca - dy * sa, 1), round(py + dx * sa + dy * ca, 1), z])
        f[k] = copy[i]
json.dump(d, open(dst, "w", encoding="utf-8"), separators=(",", ":"))
print(f"{dst}: повёрнуто {n_rot} граней из {len(F)}, вершин +{len(copy)}")
