"""Наклон в пространстве (tilt-in-space) для готовой модели игры (assets/models/*.json): сиденье со спинкой,
подлокотниками и подножками поворачивается назад; колёса, касторы, тормоза, антиопрокидыватели и низ рамы — на
месте. Решение принимается для каждой связной детали целиком (трубы не рвутся пополам на границе).
python art_tests/tilt_model.py <in.json> <out.json> <градусы> <pivot_x> <pivot_y> <base_y> <front_x>
                               [детали_на_базе,…] [детали_горизонтально,…]
  деталь поворачивается, если её центр выше base_y или впереди front_x (и она не из «на базе»);
  «горизонтально» — площадки этих деталей (ниже 160 мм до поворота) после поворота выравниваются обратно.
Оси модели: x — вперёд, y — вверх, мм."""
import json, math, sys
from collections import Counter

src, dst = sys.argv[1], sys.argv[2]
deg, px, py, base_y, front_x = (float(v) for v in sys.argv[3:8])
keep = set(sys.argv[8].split(",")) if len(sys.argv) > 8 and sys.argv[8] else set()
level_names = set(sys.argv[9].split(",")) if len(sys.argv) > 9 else set()
d = json.load(open(src, encoding="utf-8"))
V, F, names = d["verts"], d["faces"], d["parts"]
a = math.radians(deg)
ca, sa = math.cos(a), math.sin(a)

# связные куски: вершины, общие у граней (точное совпадение координат — тоже связь)
parent = list(range(len(V)))


def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


pos = {}
for i, v in enumerate(V):
    k = (round(v[0], 1), round(v[1], 1), round(v[2], 1))
    if k in pos:
        parent[find(i)] = find(pos[k])
    else:
        pos[k] = i
for f in F:
    r = find(f[0])
    for i in f[1:3]:
        parent[find(i)] = r
comp_faces = {}
for fi, f in enumerate(F):
    comp_faces.setdefault(find(f[0]), []).append(fi)
low = [sum(V[i][1] for i in f[:3]) / 3 < 160 for f in F]      # низ (площадки подножек) — до поворота
rot = [False] * len(F)
for faces in comp_faces.values():
    part = Counter(names[F[fi][3]] for fi in faces).most_common(1)[0][0]
    if part in keep:
        continue
    cx = sum(V[i][0] for fi in faces for i in F[fi][:3]) / (3 * len(faces))
    cy = sum(V[i][1] for fi in faces for i in F[fi][:3]) / (3 * len(faces))
    if cy > base_y or cx > front_x:
        for fi in faces:
            rot[fi] = True
copy = {}
for fi, f in enumerate(F):
    if not rot[fi]:
        continue
    for k in range(3):
        i = f[k]
        if i not in copy:
            x, y, z = V[i]
            dx, dy = x - px, y - py
            copy[i] = len(V)
            V.append([round(px + dx * ca - dy * sa, 1), round(py + dx * sa + dy * ca, 1), z])
        f[k] = copy[i]
for li in [i for i, n in enumerate(names) if n in level_names]:   # площадки — снова горизонтально
    vs = sorted({i for f, lo in zip(F, low) if f[3] == li and lo for i in f[:3]})
    if not vs:
        continue
    cx = sum(V[i][0] for i in vs) / len(vs)
    cy = sum(V[i][1] for i in vs) / len(vs)
    for i in vs:
        dx, dy = V[i][0] - cx, V[i][1] - cy
        V[i][0] = round(cx + dx * ca + dy * sa, 1)
        V[i][1] = round(cy - dx * sa + dy * ca, 1)
json.dump(d, open(dst, "w", encoding="utf-8"), separators=(",", ":"))
print(f"{dst}: кусков {len(comp_faces)}, повёрнуто {sum(rot)} граней из {len(F)}")
