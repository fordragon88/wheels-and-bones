"""Модели игры из лучшего от двух источников (2026-10-20): геометрия — из дочистки Gemini
(art_tests/export/gemini/<имя>_fixed/<имя>_fixed.glb: ровнее обивка, убраны обрубки и шипы), цвет — из НАШЕЙ
текстуры (art_tests/export/wheels_and_bones_folk_chairs/*/<имя>_clean.glb; у Gemini текстура темнее: обручи
Ольги и Ра стали чёрными). У Ра — наша геометрия (Gemini заменил колёса целиком).
Пишет art_tests/tripo/hybrid/<key>_full.npz (40 тыс. граней), дальше — как обычно:
  python art_tests/tripo_label.py <key> --target 22000 --dir art_tests/tripo/hybrid
python art_tests/tripo_merge.py      (venv meshenv: numpy, scipy, pillow, fast-simplification)"""
import os, sys, glob, json, struct, io, shutil
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from tripo_convert import decimate
CT = {5126: np.float32, 5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32}
NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}
def load(path):
    """GLB (меши, текстура) -> V (оси игры, мм), F, C (цвет вершин из текстуры), размер текстуры."""
    raw = open(path, "rb").read()
    jl = struct.unpack("<I", raw[12:16])[0]
    js = json.loads(raw[20:20 + jl]); b = raw[20 + jl + 8:]
    def acc(i):
        a = js["accessors"][i]; bv = js["bufferViews"][a["bufferView"]]
        return np.frombuffer(b, dtype=CT[a["componentType"]], count=a["count"] * NC[a["type"]],
                             offset=bv.get("byteOffset", 0) + a.get("byteOffset", 0)).reshape(a["count"], NC[a["type"]])
    Vs, Fs, Cs, off = [], [], [], 0
    for m in js["meshes"]:
        for p in m["primitives"]:
            A = p["attributes"]
            V = acc(A["POSITION"]).astype(np.float64)
            F = acc(p["indices"]).reshape(-1, 3).astype(np.int64)
            C = np.full((len(V), 3), 160.0)
            mat = js["materials"][p.get("material", 0)]
            t = mat.get("pbrMetallicRoughness", {}).get("baseColorTexture")
            ts = None
            if t is not None and "TEXCOORD_0" in A:
                img = js["images"][js["textures"][t["index"]]["source"]]; bv = js["bufferViews"][img["bufferView"]]
                T = np.asarray(Image.open(io.BytesIO(b[bv.get("byteOffset", 0):bv.get("byteOffset", 0) + bv["byteLength"]])).convert("RGB"))
                ts = T.shape[:2]
                UV = acc(A["TEXCOORD_0"]).astype(np.float64)
                h, w = T.shape[:2]
                C = T[np.clip(((UV[:, 1] % 1) * (h - 1)).astype(int), 0, h - 1), np.clip(((UV[:, 0] % 1) * (w - 1)).astype(int), 0, w - 1)].astype(np.float64)
            Vs.append(V); Fs.append(F + off); Cs.append(C); off += len(V)
    V = np.vstack(Vs); V = np.c_[V[:, 2], V[:, 1], -V[:, 0]] * 1000.0
    return V, np.vstack(Fs), np.vstack(Cs), ts


EXP = os.path.join(HERE, "export")
OUT = os.path.join(HERE, "tripo", "hybrid")
GEMINI = {"yaga": "baba_yaga_vermeiren_d100", "rusalka": "olga_panthera_x3", "leshy": "leshy_magic_mobility_x8",
          "raiju": "zmey_gorynych_pride_jazzy_614"}


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for key, name in GEMINI.items():
        V, F, C, _ = load(os.path.join(EXP, "gemini", name + "_fixed", name + "_fixed.glb"))
        q = np.round(V * 100).astype(np.int64)            # склейка по месту (швы UV) — иначе облегчение рвёт дыры
        _, first, inv = np.unique(q, axis=0, return_index=True, return_inverse=True)
        inv = inv.ravel()
        V, F = V[first], inv[F]
        F = F[(F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])]
        V, F, _ = decimate(V, F, np.zeros((len(V), 3)), 40000)
        V[:, 1] -= V[:, 1].min()
        V1, _, C1, _ = load(glob.glob(os.path.join(EXP, "wheels_and_bones_folk_chairs", "*", name + "_clean.glb"))[0])
        _, idx = cKDTree(V1).query(V, k=12)               # цвет — среднее 12 ближайших точек нашей модели
        np.savez_compressed(os.path.join(OUT, key + "_full.npz"), V=V, F=F, C=C1[idx].mean(1))
        print(key, len(F), "граней")
    shutil.copy(os.path.join(HERE, "tripo", "firebird_full.npz"), os.path.join(OUT, "firebird_full.npz"))
    print("firebird (Ра) — наша геометрия")
