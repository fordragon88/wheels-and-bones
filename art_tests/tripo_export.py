"""Очищенные модели Tripo для владельца: архив с GLB и референсами.

Для каждой коляски:
  <имя>_clean.glb  — исходник Tripo в полном качестве (≈1,9 млн треугольников, родная текстура), но без мусора:
                     оторванные куски убраны (как в tripo_convert.py), плюс правки геометрии из SPECS tripo_label.py
                     (drop/move: «рога» за спинкой Ольги, пульт Лешего — на правый подлокотник);
  <имя>_game.glb   — лёгкая версия из игры (22 тыс. граней, цвет в вершинах), каждая деталь — отдельный объект
                     (tire, rim, joystick…); у Ра здесь рама перекрашена в красный и дорисованы ступицы e-motion;
  preview.png      — как коляска выглядит в игре (кадры поворота);
  reference/       — по чему делалась модель: картинка для 3D-генератора, фото и схема из мануала, рисунок в игре.
В корне — README.md и TASK_cleanup.md (задание другой модели, напр. Gemini: дочистить мусор).
Оси GLB — как принято в glTF: Y вверх, +Z вперёд (к подножкам), метры, пол на Y = 0.

python art_tests/tripo_export.py [out_dir]     (venv с numpy, scipy, pillow — как для tripo_convert.py)"""
import os, sys, json, struct, shutil, zipfile
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from tripo_convert import read_glb, orient, keep_attached
from tripo_label import SPECS, edit

DL = os.path.join(os.path.expanduser("~"), "Downloads")
REFS = os.path.join(HERE, "new_chars_refs")
# key (SPECS) -> папка, исходник из вьюпорта Tripo, ориентация (подобрана сравнением с моделями игры), референсы
CHAIRS = [
    ("yaga", "1_baba_yaga_vermeiren_d100", "Scene.glb", 0,
     ["for_3d/baba_yaga_vermeiren_d100_34front.png", "baba_yaga__vermeiren_d100/page01_img414.jpeg",
      "baba_yaga__vermeiren_d100/page07.png"]),
    ("rusalka", "2_olga_panthera_x3", "Scene (4).glb", 180,
     ["for_3d/rusalka_panthera_x3_34front.png", "for_3d/rusalka_panthera_x3_side.png",
      "rusalka__panthera_x3/page04_img53.jpeg", "rusalka__panthera_x3/page05.png"]),
    ("leshy", "3_leshy_magic_mobility_x8", "Scene (1).glb", 270,
     ["leshy__magic_mobility_extreme_x8/page02_img9.jpeg", "leshy__magic_mobility_extreme_x8/page09.png"]),
    ("firebird", "4_ra_quickie_nitrum_alber_emotion", "Scene (3).glb", 0,
     ["for_3d/firebird_wolturnus_w5_34front.png", "for_3d/firebird_wolturnus_w5_34back_bw.png",
      "firebird__quickie_nitrum_alber_emotion/nitrum_page01.png",
      "firebird__quickie_nitrum_alber_emotion/emotion_page46.png"]),
    ("raiju", "5_zmey_gorynych_pride_jazzy_614", "Scene (2).glb", 0,
     ["for_3d/raiju_jazzy614_34front.png", "raiju__pride_jazzy_evo_614/page01_img2573.jpeg",
      "raiju__pride_jazzy_evo_614/page07.png"]),
]


def to_gltf(V):
    """Оси игры (x вперёд, y вверх, z вбок, мм) -> glTF (Y вверх, +Z вперёд, м): поворот вокруг Y."""
    return np.c_[-V[:, 2], V[:, 1], V[:, 0]] / 1000.0


def smooth_normals(V, F):
    """Нормали вершин (по площади); вершины на швах текстуры (одна точка — разные UV) получают общую нормаль."""
    q = np.round(V * 1e5).astype(np.int64)
    _, inv = np.unique(q, axis=0, return_inverse=True)
    inv = inv.ravel()
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    acc = np.zeros((inv.max() + 1, 3))
    for k in range(3):
        np.add.at(acc, inv[F[:, k]], fn)
    N = acc[inv]
    return N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)


class GLB:
    """Минимальный писатель GLB: меши (примитивы) + материалы, всё в одном бинарном буфере."""

    def __init__(self):
        self.js = dict(asset=dict(version="2.0", generator="Wheels & Bones tripo_export.py"), scene=0,
                       scenes=[dict(nodes=[])], nodes=[], meshes=[], materials=[], accessors=[], bufferViews=[])
        self.bin = bytearray()

    def view(self, data, target=None):
        while len(self.bin) % 4:
            self.bin += b"\0"
        bv = dict(buffer=0, byteOffset=len(self.bin), byteLength=len(data))
        if target:
            bv["target"] = target
        self.bin += data
        self.js["bufferViews"].append(bv)
        return len(self.js["bufferViews"]) - 1

    def acc(self, arr, ctype, typ, target, normalized=False, minmax=False):
        a = dict(bufferView=self.view(arr.tobytes(), target), componentType=ctype, count=len(arr), type=typ)
        if normalized:
            a["normalized"] = True
        if minmax:
            a["min"], a["max"] = arr.min(0).tolist(), arr.max(0).tolist()
        self.js["accessors"].append(a)
        return len(self.js["accessors"]) - 1

    def texture(self, data, mime):
        bv = self.view(data)
        self.js.setdefault("images", []).append(dict(bufferView=bv, mimeType=mime))
        self.js.setdefault("samplers", []).append(dict(magFilter=9729, minFilter=9987))
        self.js.setdefault("textures", []).append(dict(source=len(self.js["images"]) - 1, sampler=0))
        return len(self.js["textures"]) - 1

    def material(self, name, tex=None):
        pbr = dict(metallicFactor=0.0, roughnessFactor=0.8)
        if tex is not None:
            pbr["baseColorTexture"] = dict(index=tex)
        self.js["materials"].append(dict(name=name, pbrMetallicRoughness=pbr, doubleSided=True))
        return len(self.js["materials"]) - 1

    def mesh(self, name, P, F, mat, N=None, UV=None, COL=None):
        attrs = dict(POSITION=self.acc(P.astype(np.float32), 5126, "VEC3", 34962, minmax=True))
        if N is not None:
            attrs["NORMAL"] = self.acc(N.astype(np.float32), 5126, "VEC3", 34962)
        if UV is not None:
            attrs["TEXCOORD_0"] = self.acc(UV.astype(np.float32), 5126, "VEC2", 34962)
        if COL is not None:
            attrs["COLOR_0"] = self.acc(COL.astype(np.uint8), 5121, "VEC4", 34962, normalized=True)
        ind = self.acc(F.astype(np.uint32).ravel(), 5125, "SCALAR", 34963)
        self.js["meshes"].append(dict(name=name, primitives=[dict(attributes=attrs, indices=ind, material=mat)]))
        self.js["nodes"].append(dict(name=name, mesh=len(self.js["meshes"]) - 1))
        self.js["scenes"][0]["nodes"].append(len(self.js["nodes"]) - 1)

    def save(self, path):
        while len(self.bin) % 4:
            self.bin += b"\0"
        self.js["buffers"] = [dict(byteLength=len(self.bin))]
        j = json.dumps(self.js, separators=(",", ":")).encode()
        j += b" " * (-len(j) % 4)
        with open(path, "wb") as f:
            f.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(j) + 8 + len(self.bin)))
            f.write(struct.pack("<II", len(j), 0x4E4F534A) + j)
            f.write(struct.pack("<II", len(self.bin), 0x004E4942) + bytes(self.bin))


def clean_model(key, src, yaw, out):
    """Полная модель: та же цепочка, что в tripo_convert.py (без склейки и облегчения) + правки SPECS."""
    ref = np.load(os.path.join(HERE, "tripo", f"{key}_full.npz"))["V"]
    ax = ("length", float(ref[:, 0].max() - ref[:, 0].min()))     # габарит — как у модели в игре
    V, F, C, UV, _, (img, mime) = read_glb(os.path.join(DL, src), full=True)
    n0 = len(F)
    V = orient(V, ax, False, yaw)
    V, F, keep, dropped, _, _ = keep_attached(V, F, cell=12.0)
    C, UV = C[keep], UV[keep]
    V = orient(V, ax, False, 0)
    V[:, 1] -= V[:, 1].min()
    n1 = len(F)
    V, F, A = edit(V, F, np.c_[C, UV], SPECS[key])               # UV едут вместе с вершинами
    UV = A[:, 3:5]
    F = F[(F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])]
    P = to_gltf(V)
    g = GLB()
    g.mesh(SPECS[key]["art"].replace("chair_", ""), P, F, g.material("tripo", g.texture(img, mime)),
           N=smooth_normals(P, F), UV=UV)
    g.save(out)
    print(f"  {os.path.basename(out)}: {n0} -> {n1} (оторванный мусор) -> {len(F)} треугольников (правки); "
          f"габарит мм {np.round((V.max(0) - V.min(0))).astype(int).tolist()}", flush=True)


def game_model(key, out):
    """Лёгкая модель игры: детали — отдельные объекты, цвет граней — в вершинах."""
    d = json.load(open(os.path.join(HERE, "tripo", "models", SPECS[key]["art"] + "_ai.json")))
    V = np.asarray(d["verts"], float)
    fa = np.asarray(d["faces"])
    g = GLB()
    mat = g.material("vertex_color")
    for pi, name in enumerate(d["parts"]):
        sel = fa[fa[:, 3] == pi]
        if not len(sel):
            continue
        P = to_gltf(V[sel[:, :3].ravel()])                        # своя тройка вершин на грань — цвет грани ровный
        F = np.arange(len(P)).reshape(-1, 3)
        fn = np.cross(P[F[:, 1]] - P[F[:, 0]], P[F[:, 2]] - P[F[:, 0]])
        fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
        col = np.repeat(np.c_[sel[:, 4:7], np.full(len(sel), 255)], 3, axis=0)
        g.mesh(name, P, F, mat, N=np.repeat(fn, 3, axis=0), COL=col)
    g.save(out)


def preview(art, out):
    tt = os.path.join(HERE, "new_v2", "assets", "turntable")
    ims = [Image.open(os.path.join(tt, f"{art}_{i:02d}.png")).convert("RGBA") for i in (0, 6, 12, 18, 24, 30)]
    H = 360
    row = [im.resize((round(im.width * H / im.height), H)) for im in ims]
    sheet = Image.new("RGB", (sum(r.width for r in row) + 12 * (len(row) + 1), H + 24), (236, 232, 224))
    x = 12
    for r in row:
        sheet.paste(r, (x, 12), r)
        x += r.width + 12
    sheet.save(out)


if __name__ == "__main__":
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "export")
    root = os.path.join(out_dir, "wheels_and_bones_folk_chairs")
    shutil.rmtree(root, ignore_errors=True)
    for key, folder, src, yaw, refs in CHAIRS:
        d = os.path.join(root, folder)
        os.makedirs(os.path.join(d, "reference"), exist_ok=True)
        name = folder.split("_", 1)[1]
        print(folder, flush=True)
        clean_model(key, src, yaw, os.path.join(d, f"{name}_clean.glb"))
        game_model(key, os.path.join(d, f"{name}_game.glb"))
        art = SPECS[key]["art"]
        preview(art, os.path.join(d, "preview.png"))
        k = art[len("chair_"):]
        for f in refs:
            shutil.copy(os.path.join(REFS, f), os.path.join(d, "reference", f.replace("/", "__")))
        for a in (f"chair_{k}.png", f"client_{k}.png"):
            shutil.copy(os.path.join(HERE, "new_v2", "assets", a), os.path.join(d, "reference", "game_" + a))
    shutil.copy(os.path.join(HERE, "tripo_export_README.md"), os.path.join(root, "README.md"))
    shutil.copy(os.path.join(HERE, "tripo_export_TASK.md"), os.path.join(root, "TASK_cleanup.md"))   # для Gemini
    z = os.path.join(out_dir, "wheels_and_bones_folk_chairs.zip")
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for base, _, files in os.walk(root):
            for f in files:
                p = os.path.join(base, f)
                zf.write(p, os.path.relpath(p, out_dir))
    print("архив:", z, round(os.path.getsize(z) / 1e6, 1), "МБ")
