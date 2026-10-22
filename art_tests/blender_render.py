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
        h0, h1, tol = recolor
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
            c = mx * sat
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
    delete=True — вершины зоны удаляются (напр. антиопрокидыватель). Порядок — как в списке."""
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
            if mv.get("not_wheel"):
                cx, cy, R, zw = mv["not_wheel"]
                sel &= ~((np.hypot(x - cx, y - cy) < R) & (np.abs(z) > zw))
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


# ---------- модель ----------
if d.get("glb"):
    import_glb(d["glb"], d["glb_matrix"], d.get("recolor"))
    if d.get("move"):
        move_parts(d["move"])
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
