"""Кадры поворота коляски в Blender (запускать внутри Blender):
tools/blender-4.2.23-windows-x64/blender.exe -b --factory-startup -P art_tests/blender_render.py -- <render_in/x.json> <out_dir> [кадры 0,9,18]
Модель — из art_tests/blender_export.py (оси игры: x вперёд, y вверх, z вбок, мм; в Blender: X=x, Y=−z, Z=y).
Камера повторяет project_point игры: перспектива с 2600 мм, центр кадра — pivot на 0,54 высоты, масштаб s пикс/мм.
Цвет: у граней одной детали и близкого цвета — плавный переход по вершинам (без «мозаики»), между деталями —
чёткая граница; сглаживание по углу 35° (острые рёбра остаются); свет — мягкий студийный, фон прозрачный."""
import bpy, sys, json, math, os
import numpy as np
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
src, out = os.path.abspath(argv[0]), os.path.abspath(argv[1])
only = [int(v) for v in argv[2].split(",")] if len(argv) > 2 and argv[2] else None
os.makedirs(out, exist_ok=True)
d = json.load(open(src, encoding="utf-8"))
name = os.path.splitext(os.path.basename(src))[0]

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

def import_glb(path, M, recolor=None):
    """Оригинальная модель (Meshy/Tripo GLB, полная сетка и текстура) в осях игры: M — мм игры из мировых glTF."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    B2G = Matrix(((1, 0, 0, 0), (0, 0, 1, 0), (0, -1, 0, 0), (0, 0, 0, 1)))           # Blender -> glTF
    G2B = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1))) @ Matrix.Scale(0.001, 4)
    T = G2B @ Matrix(M) @ B2G
    for o in set(bpy.data.objects) - before:
        if o.parent is None:
            o.matrix_world = T @ o.matrix_world
    if recolor:                                          # оттенок текстуры как у коляски в игре (красный -> фиолетовый)
        h0, h1, tol, *rest = recolor                   # 4-й (необязательный) — множитель насыщенности (пастель < 1)
        smul = rest[0] if rest else 1.0
        for img in bpy.data.images:
            if img.size[0] == 0 or "normal" in img.name.lower():
                continue
            px = np.empty(img.size[0] * img.size[1] * 4, np.float32)
            img.pixels.foreach_get(px)
            p = px.reshape(-1, 4)
            rgb = p[:, :3]
            mx, mn = rgb.max(1), rgb.min(1)
            dlt = mx - mn
            sat = dlt / np.maximum(mx, 1e-6)
            h = np.zeros_like(mx)
            m = dlt > 1e-6
            r, g, b = rgb[:, 0], rgb[:, 1], rgb[:, 2]
            hr = m & (mx == r); hg = m & (mx == g) & ~hr; hb = m & ~hr & ~hg
            h[hr] = ((g - b)[hr] / dlt[hr]) % 6
            h[hg] = (b - r)[hg] / dlt[hg] + 2
            h[hb] = (r - g)[hb] / dlt[hb] + 4
            h *= 60
            sel = (sat > 0.35) & (np.abs(((h - h0) + 180) % 360 - 180) < tol) & (mx > 0.08)
            if h1 < 0:                                   # в графит: без цвета, темнее
                g = mx * 0.42 + 0.05
                rgb[sel, 0], rgb[sel, 1], rgb[sel, 2] = g[sel], g[sel], g[sel] * 1.04
                img.pixels.foreach_set(p.ravel())
                img.update()
                print("в графит пикселей:", int(sel.sum()), img.name)
                continue
            hh = h1 / 60.0                               # тот же цвет с новым оттенком (яркость и насыщенность — прежние)
            c = mx * sat * smul
            x = c * (1 - abs(hh % 2 - 1))
            base = mx - c
            rr, gg, bb = {0: (c, x, 0 * c), 1: (x, c, 0 * c), 2: (0 * c, c, x), 3: (0 * c, x, c), 4: (x, 0 * c, c),
                          5: (c, 0 * c, x)}[int(hh) % 6]
            rgb[sel, 0], rgb[sel, 1], rgb[sel, 2] = (rr + base)[sel], (gg + base)[sel], (bb + base)[sel]
            img.pixels.foreach_set(p.ravel())
            img.update()
            print("перекрашено пикселей:", int(sel.sum()), img.name)


def move_parts(moves):
    """Сдвиг части оригинальной модели (напр. подножка выше под короткие ноги): вершины с x, y (мм игры) в зоне
    (и |z| в az, если задано), кроме тех, что в круге колеса (not_wheel = cx, cy, R, |z| от), едут на d (мм игры);
    delete=True — вершины зоны удаляются (напр. антиопрокидыватель); rot=(yaw°, pitch°[, roll°]) с pivot (+ сдвиг d) — поворот части
    (кривой джойстик Meshy). Порядок — как в списке."""
    import bmesh
    for o in [o for o in sc.objects if o.type == "MESH"]:
        mw = o.matrix_world
        for mv in moves:
            n = len(o.data.vertices)
            co = np.empty(n * 3)
            o.data.vertices.foreach_get("co", co)
            w = np.c_[co.reshape(-1, 3), np.ones(n)] @ np.asarray(mw).T
            x, y, z = w[:, 0] * 1000, w[:, 2] * 1000, -w[:, 1] * 1000
            sel = (x >= mv["x"][0]) & (x <= mv["x"][1]) & (y >= mv["y"][0]) & (y <= mv["y"][1])
            if mv.get("az"):
                sel &= (np.abs(z) >= mv["az"][0]) & (np.abs(z) <= mv["az"][1])
            if mv.get("z"):                                     # знаковый диапазон z (одна сторона коляски)
                sel &= (z >= mv["z"][0]) & (z <= mv["z"][1])
            if mv.get("not_wheel"):
                cx, cy, R, zw = mv["not_wheel"]
                sel &= ~((np.hypot(x - cx, y - cy) < R) & (np.abs(z) > zw))
            if mv.get("rot"):                                # поворот части: rot=(yaw°, pitch°), pivot=(x, y, z) мм игры
                yaw, pitch, roll = [math.radians(v) for v in (list(mv["rot"]) + [0])[:3]]
                px, py, pz = mv["pivot"]
                gx, gy, gz = x[sel] - px, y[sel] - py, z[sel] - pz
                cr, sr = math.cos(roll), math.sin(roll)                  # roll — вокруг оси x (крен)
                gy, gz = gy * cr - gz * sr, gy * sr + gz * cr
                # pitch — вокруг оси z игры (нос x вниз при pitch<0), потом yaw — вокруг оси y (вертикали)
                cp, sp_ = math.cos(pitch), math.sin(pitch)
                gx, gy = gx * cp - gy * sp_, gx * sp_ + gy * cp
                cy_, sy_ = math.cos(yaw), math.sin(yaw)
                gx, gz = gx * cy_ - gz * sy_, gx * sy_ + gz * cy_
                dx_, dy_, dz_ = mv.get("d", (0, 0, 0))
                nx, ny, nz = gx + px + dx_, gy + py + dy_, gz + pz + dz_
                w[sel, 0] = nx / 1000
                w[sel, 1] = -nz / 1000
                w[sel, 2] = ny / 1000
                print("повёрнуто вершин:", int(sel.sum()), o.name)
                new = w @ np.asarray(mw.inverted()).T
                o.data.vertices.foreach_set("co", new[:, :3].ravel())
                continue
            if mv.get("delete"):
                bm = bmesh.new()
                bm.from_mesh(o.data)
                bm.verts.ensure_lookup_table()
                bmesh.ops.delete(bm, geom=[bm.verts[i] for i in np.nonzero(sel)[0]], context="VERTS")
                bm.to_mesh(o.data)
                bm.free()
                print("удалено вершин:", int(sel.sum()), o.name)
                continue
            dx, dy, dz = mv["d"]
            w[sel, 0] += dx / 1000
            w[sel, 1] -= dz / 1000
            w[sel, 2] += dy / 1000
            print("сдвинуто вершин:", int(sel.sum()), o.name)
            new = w @ np.asarray(mw.inverted()).T
            o.data.vertices.foreach_set("co", new[:, :3].ravel())
        o.data.update()


def add_hub(h):
    """Мотор-ступица (Alber e-motion), которой нет в модели Meshy: тёмный корпус и светлая крышка.
    h: c — центр (x, y, z, мм игры), r — радиус, w — толщина, мм."""
    x, y, z = h["c"]
    for r, w, col, met in ((h["r"], h["w"], (0.03, 0.03, 0.035, 1), 0.35),
                           (h["r"] * 0.45, h["w"] + 6, (0.6, 0.61, 0.65, 1), 0.85)):
        bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=r / 1000, depth=w / 1000,
                                            location=(x / 1000, -z / 1000, y / 1000), rotation=(math.pi / 2, 0, 0))
        ob = bpy.context.active_object
        m = bpy.data.materials.new("hub")
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = col
        b.inputs["Metallic"].default_value = met
        b.inputs["Roughness"].default_value = 0.35
        ob.data.materials.append(m)
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))


def fix_spokes(ws):
    """Спицы Meshy рвутся на куски: вырезаем их внутри колеса и ставим ровные (перекрёстная спицовка, оба колеса).
    w: c — центр колеса (x, y, мм игры), zp — |z| плоскости спиц у обода, cut_r/cut_z — зона вырезки (радиус от центра,
    |z|), rh/rr — радиус фланца ступицы и обода, fl — полуширина ступицы, n — спиц на колесо, cross — сдвиг по ободу
    (рад), col — цвет; side (+1/−1) — только это колесо, hc — центр втулки (у Meshy она сдвинута от центра обода)."""
    import bmesh
    for w in ws:
        cx, cy = w["c"]
        for o in [o for o in sc.objects if o.type == "MESH"]:
            n = len(o.data.vertices)
            co = np.empty(n * 3)
            o.data.vertices.foreach_get("co", co)
            g = np.c_[co.reshape(-1, 3), np.ones(n)] @ np.asarray(o.matrix_world).T
            x, y, z = g[:, 0] * 1000, g[:, 2] * 1000, -g[:, 1] * 1000
            r = np.hypot(x - cx, y - cy)
            sel = (r > w["cut_r"][0]) & (r < w["cut_r"][1]) & (np.abs(z) >= w["cut_z"][0]) & (np.abs(z) <= w["cut_z"][1])
            if "side" in w:
                sel &= z * w["side"] > 0
            if sel.any():
                bm = bmesh.new()
                bm.from_mesh(o.data)
                bm.verts.ensure_lookup_table()
                bmesh.ops.delete(bm, geom=[bm.verts[i] for i in np.nonzero(sel)[0]], context="VERTS")
                bm.to_mesh(o.data)
                bm.free()
                o.data.update()
                print("спицы Meshy: удалено вершин", int(sel.sum()), o.name)
        verts, faces, k, t = [], [], 6, w.get("t", 1.4)
        cross = w.get("cross", 0.2)                          # сдвиг спицы по ободу, рад (почти касательная к ступице)
        hx, hy = w.get("hc", w["c"])
        for side in ((w["side"],) if "side" in w else (-1, 1)):
            for i in range(w["n"]):
                a = 2 * math.pi * i / w["n"]
                zf = side * (w["zp"] + (w["fl"] if i % 2 else -w["fl"]))
                ar = a + (cross if (i // 2) % 2 else -cross)
                p0 = np.array([hx + w["rh"] * math.cos(a), hy + w["rh"] * math.sin(a), zf])
                p1 = np.array([cx + w["rr"] * math.cos(ar), cy + w["rr"] * math.sin(ar), side * w["zp"]])
                ax = (p1 - p0) / np.linalg.norm(p1 - p0)
                u = np.cross(ax, [0, 0, 1.0])
                u = u / np.linalg.norm(u) if np.linalg.norm(u) > 1e-6 else np.array([1.0, 0, 0])
                v = np.cross(ax, u)
                base = len(verts)
                for p in (p0, p1):
                    for j in range(k):
                        q = p + t * (math.cos(2 * math.pi * j / k) * u + math.sin(2 * math.pi * j / k) * v)
                        verts.append((q[0] / 1000, -q[2] / 1000, q[1] / 1000))
                for j in range(k):
                    jj = (j + 1) % k
                    faces.append((base + j, base + jj, base + k + jj, base + k + j))
        me_ = bpy.data.meshes.new("spokes")
        me_.from_pydata(verts, [], faces)
        me_.update()
        ob_ = bpy.data.objects.new("spokes", me_)
        sc.collection.objects.link(ob_)
        m = bpy.data.materials.new("spoke")
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*w.get("col", (0.7, 0.7, 0.72)), 1)
        b.inputs["Metallic"].default_value = 0.9
        b.inputs["Roughness"].default_value = 0.3
        me_.materials.append(m)


def clone_parts(cl):
    """Копии куска оригинальной модели (напр. единственный антиопрокидыватель Meshy — на обе стороны): грани, все
    вершины которых в зоне x/y/|z| (мм игры), копируются; copies — [dict(mirror=bool (отразить по z), d=(dx, dy, dz))];
    исходник удаляется (keep=False). Текстура/UV у копий — свои, как у исходника."""
    import bmesh
    for o in [o for o in sc.objects if o.type == "MESH"]:
        M = o.matrix_world
        Mi = M.inverted()
        bm = bmesh.new()
        bm.from_mesh(o.data)

        def g(v):
            w = M @ v.co
            return w.x * 1000, w.z * 1000, -w.y * 1000                    # мм игры: x, y (вверх), z

        def inzone(v):
            x, y, z = g(v)
            return (cl["x"][0] <= x <= cl["x"][1] and cl["y"][0] <= y <= cl["y"][1]
                    and cl["az"][0] <= abs(z) <= cl["az"][1])
        src = [f for f in bm.faces if all(inzone(v) for v in f.verts)]
        if not src:
            bm.free()
            continue
        for cp in cl["copies"]:
            ret = bmesh.ops.duplicate(bm, geom=src)
            nv = [e for e in ret["geom"] if isinstance(e, bmesh.types.BMVert)]
            nf = [e for e in ret["geom"] if isinstance(e, bmesh.types.BMFace)]
            dx, dy, dz = cp["d"]
            for v in nv:
                x, y, z = g(v)
                if cp.get("mirror"):
                    z = -z
                x, y, z = x + dx, y + dy, z + dz
                v.co = Mi @ Vector((x / 1000, -z / 1000, y / 1000))
            if cp.get("mirror"):
                bmesh.ops.reverse_faces(bm, faces=nf)
        if not cl.get("keep"):
            bmesh.ops.delete(bm, geom=src, context="FACES")
        bm.to_mesh(o.data)
        bm.free()
        o.data.update()
        print("скопировано граней:", len(src), "x", len(cl["copies"]), o.name)


def add_tube(t):
    """Трубка, которой нет в модели (крепление пульта и т.п.): p0→p1 (мм игры), r — радиус, col — цвет."""
    p0, p1 = np.array(t["p0"], float), np.array(t["p1"], float)
    ax = (p1 - p0) / np.linalg.norm(p1 - p0)
    ref = np.array([0, 0, 1.0]) if abs(ax[2]) < 0.9 else np.array([1.0, 0, 0])
    u = np.cross(ax, ref); u /= np.linalg.norm(u)
    v = np.cross(ax, u)
    k, r = 16, t.get("r", 8)
    verts = []
    for p in (p0, p1):
        for j in range(k):
            q = p + r * (math.cos(2 * math.pi * j / k) * u + math.sin(2 * math.pi * j / k) * v)
            verts.append((q[0] / 1000, -q[2] / 1000, q[1] / 1000))
    faces = [(j, (j + 1) % k, k + (j + 1) % k, k + j) for j in range(k)] + [tuple(range(k))[::-1], tuple(range(k, 2 * k))]
    me_ = bpy.data.meshes.new("tube")
    me_.from_pydata(verts, [], faces)
    ob_ = bpy.data.objects.new("tube", me_)
    sc.collection.objects.link(ob_)
    m = bpy.data.materials.new("tube")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*t.get("col", (0.06, 0.06, 0.065)), 1)
    b.inputs["Metallic"].default_value = 0.7
    b.inputs["Roughness"].default_value = 0.35
    me_.materials.append(m)
    bpy.context.view_layer.objects.active = ob_
    ob_.select_set(True)
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
    ob_.select_set(False)


def add_antitip(a):
    """Антиопрокидыватель, которого нет (или он кривой) в модели Meshy: трубка от рамы назад-вниз и колёсико.
    a: p0, p1 — концы трубки (x, y, z, мм игры), r — радиус трубки, wheel — (r, ширина) колёсика у p1."""
    import bmesh
    p0, p1 = np.array(a["p0"], float), np.array(a["p1"], float)
    ax = (p1 - p0) / np.linalg.norm(p1 - p0)
    u = np.cross(ax, [0, 0, 1.0]); u /= np.linalg.norm(u)
    v = np.cross(ax, u)
    k, r = 12, a.get("r", 9)
    verts, faces = [], []
    for p in (p0, p1):
        for j in range(k):
            q = p + r * (math.cos(2 * math.pi * j / k) * u + math.sin(2 * math.pi * j / k) * v)
            verts.append((q[0] / 1000, -q[2] / 1000, q[1] / 1000))
    faces = [(j, (j + 1) % k, k + (j + 1) % k, k + j) for j in range(k)]
    me_ = bpy.data.meshes.new("antitip")
    me_.from_pydata(verts, [], faces)
    ob_ = bpy.data.objects.new("antitip", me_)
    sc.collection.objects.link(ob_)
    for nm, col, met in (("tube", a.get("col", (0.05, 0.05, 0.055)), 0.6),):
        m = bpy.data.materials.new(nm)
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*col, 1)
        b.inputs["Metallic"].default_value = met
        b.inputs["Roughness"].default_value = 0.35
        me_.materials.append(m)
    wr, ww = a.get("wheel", (24, 18))
    for rr, w, col in ((wr, ww, (0.04, 0.04, 0.045)), (wr * 0.5, ww + 4, (0.55, 0.56, 0.6))):
        bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=rr / 1000, depth=w / 1000,
                                            location=(p1[0] / 1000, -p1[2] / 1000, p1[1] / 1000), rotation=(math.pi / 2, 0, 0))
        ob = bpy.context.active_object
        m = bpy.data.materials.new("atw")
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (*col, 1)
        b.inputs["Roughness"].default_value = 0.5
        ob.data.materials.append(m)
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))


# ---------- модель ----------
if d.get("glb"):
    import_glb(d["glb"], d["glb_matrix"], d.get("recolor"))
    if d.get("move"):
        move_parts(d["move"])
    if os.environ.get("WB_CULL"):                      # проверка: с отсечением задних граней видны дыры/вывернутые нормали
        for m_ in bpy.data.materials:
            m_.use_backface_culling = True
    if d.get("spokes"):
        fix_spokes(d["spokes"])
    for cl in d.get("clones") or []:
        clone_parts(cl)
    for at in d.get("antitips") or []:
        add_antitip(at)
    for t in d.get("tubes") or []:
        add_tube(t)
    for h in d.get("hubs") or []:
        add_hub(h)
    if os.environ.get("WB_EXPORT"):                    # исправленная копия модели (glb_fixed.py): без рендера
        bpy.ops.object.select_all(action="DESELECT")
        for o in sc.objects:
            o.select_set(o.type == "MESH")
        bpy.ops.export_scene.gltf(filepath=os.environ["WB_EXPORT"], export_format="GLB", use_selection=True)
        print("exported", os.environ["WB_EXPORT"], flush=True)
        sys.exit(0)
V = np.asarray(d["verts"], dtype=np.float64)
VB = np.c_[V[:, 0], -V[:, 2], V[:, 1]] / 1000.0          # мм -> м, оси Blender
tris, fcol, fmet, fpart = [], [], [], []
parts = {}
for idx, part, col, met in d["faces"]:
    pid = parts.setdefault(part, len(parts))
    for j in range(1, len(idx) - 1):
        tris.append((idx[0], idx[j], idx[j + 1]))
        fcol.append(col); fmet.append(met); fpart.append(pid)
T = np.asarray(tris, dtype=np.int64)
C = np.asarray(fcol, dtype=np.float64) / 255.0
# плавный цвет: для каждого угла — среднее цветов граней вокруг вершины той же детали и близкого цвета
nv = len(VB)
corner_col = np.zeros((len(T), 3, 3))
by_vert = [[] for _ in range(nv)]
for fi, t in enumerate(T):
    for v in t:
        by_vert[v].append(fi)
fpart = np.asarray(fpart)
for fi, t in enumerate(T):
    for k, v in enumerate(t):
        nb = [g for g in by_vert[v] if fpart[g] == fpart[fi] and np.abs(C[g] - C[fi]).max() < 0.22]
        corner_col[fi, k] = C[nb].mean(0) if nb else C[fi]
me = bpy.data.meshes.new(name)
me.from_pydata(VB.tolist(), [], T.tolist())
me.update()
attr = me.color_attributes.new("col", "BYTE_COLOR", "CORNER")
rgba = np.c_[corner_col.reshape(-1, 3), np.ones(len(T) * 3)]
attr.data.foreach_set("color_srgb", rgba.ravel().astype(np.float32))
ob = bpy.data.objects.new(name, me)
if not d.get("glb"):
    sc.collection.objects.link(ob)
if not d.get("glb"):
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
BEVEL = 0 if d.get("glb") else float(os.environ.get("WB_BEVEL", "0"))            # мм: скруглить рёбра «коробок» (наши электроколяски)
if BEVEL > 0:
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.0008)           # грани-«ящики» сшить, иначе фаске нечего скруглять
    bpy.ops.object.mode_set(mode="OBJECT")
    bv = ob.modifiers.new("bevel", "BEVEL")
    bv.width = BEVEL / 1000.0
    bv.segments = 3
    bv.limit_method = "ANGLE"
    bv.angle_limit = math.radians(50)
    bv.harden_normals = False
    bv.profile = 0.6
if not d.get("glb"):
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))


def material(nm, metal):
    m = bpy.data.materials.new(nm)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    ca = nt.nodes.new("ShaderNodeVertexColor")
    ca.layer_name = "col"
    nt.links.new(ca.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Metallic"].default_value = 0.75 if metal else 0.0
    bsdf.inputs["Roughness"].default_value = 0.32 if metal else 0.55
    return m


me.materials.append(material("paint", False))
me.materials.append(material("metal", True))
me.polygons.foreach_set("material_index", np.asarray(fmet, dtype=np.int32))
me.update()

# ---------- свет ----------
sc.render.engine = "BLENDER_EEVEE_NEXT"
sc.eevee.taa_render_samples = 48
sc.render.film_transparent = True
sc.view_settings.view_transform = "Standard"
sc.view_settings.look = "None"
sc.eevee.use_raytracing = True                            # мягкие затенения в щелях (как AO)
world = bpy.data.worlds.new("w")
sc.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.62, 0.62, 0.66, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = float(os.environ.get("WB_AMB", "0.32"))


def light(kind, energy, loc, size, color=(1, 1, 1)):
    ld = bpy.data.lights.new(kind + str(energy), kind)
    ld.energy = energy
    ld.color = color
    if kind == "AREA":
        ld.size = size
    else:
        ld.angle = math.radians(size)
    lo = bpy.data.objects.new(ld.name, ld)
    sc.collection.objects.link(lo)
    lo.location = loc
    lo.rotation_euler = (Vector((0, 0, 0.55)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return lo


light("SUN", float(os.environ.get("WB_SUN", "2.2")), (2.0, -1.5, 3.0), 8, (1.0, 0.97, 0.92))      # ключевой, тёплый, мягкая тень
light("AREA", 110, (-2.2, 2.0, 1.6), 2.5, (0.85, 0.9, 1.0))     # заполняющий, холодный
light("AREA", 90, (-0.6, -2.6, 2.4), 2.0)                       # контровой

# ---------- камера как в игре ----------
W, H, s = d["W"], d["H"], d["s"]
px, py, pz = d["pivot"]
cam_d = bpy.data.cameras.new("cam")
cam_d.sensor_fit = "VERTICAL"
cam_d.sensor_height = 36.0
cam_d.lens = 36.0 * 2600.0 * s / H
cam_d.shift_y = 0.04                                    # при VERTICAL — в долях высоты: центр на 0,54 H
cam_d.clip_start, cam_d.clip_end = 0.05, 20
cam = bpy.data.objects.new("cam", cam_d)
sc.collection.objects.link(cam)
sc.camera = cam
sc.render.resolution_x, sc.render.resolution_y = W, H
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"


def g2b(x, y, z):                                          # оси игры -> Blender
    return Vector((x, -z, y))


p = d["pitch"]
cp, sp = math.cos(p), math.sin(p)
for i, yaw in enumerate(d["yaws"]):
    if only is not None and i not in only:
        continue
    cy, sy = math.cos(yaw), math.sin(yaw)
    right = g2b(cy, 0, sy)
    up = g2b(sp * sy, cp, -sp * cy)
    back = g2b(-cp * sy, sp, cp * cy)
    pos = g2b(px - 2600 * cp * sy, py + 2600 * sp, pz + 2600 * cp * cy) / 1000.0
    M = Matrix(((right.x, up.x, back.x, pos.x), (right.y, up.y, back.y, pos.y),
                (right.z, up.z, back.z, pos.z), (0, 0, 0, 1)))
    cam.matrix_world = M
    sc.render.filepath = os.path.join(out, f"{name}_{i:02d}.png")
    bpy.ops.render.render(write_still=True)
    print("frame", i, flush=True)
