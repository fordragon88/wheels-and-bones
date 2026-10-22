"""Доработка модели игры (assets/models/*.json) кусками другой модели: убрать лишнее, добавить недостающее.
python art_tests/model_patch.py <ключ>   (правила — PATCHES ниже; пишет out и out_lod)

drop — убрать грани: коробка x/y/z (z со знаком) и, по желанию, только детали из parts;
add  — взять грани донора (коробка + детали), масштаб s=(sx, sy, sz) вокруг 0 и сдвиг d, деталь — как у донора
       (или part=…, если такой детали у цели нет — добавится). Оси: x — вперёд, y — вверх, z — вбок, мм."""
import json, sys, os

INF = 1e9
PATCHES = {
    # Матильда — Permobil F5 Corpus: скан Tripo (art_tests/tripo/v3) + задние колёсики и подножка прежней модели;
    # у скана задних колёсиков нет (корпус висит), подножка — тонкая палка, слева — второй пульт
    "f5": dict(
        base="art_tests/tripo/v3/models/chair_f5_ai.json",
        donor="art_tests/tripo/bak_before_v3/chair_f5_ai.json",
        out="assets/models/chair_f5_ai.json", brighten=1.1,
        drop=[dict(box=((330, INF), (-INF, 200), (-INF, INF))),                  # подножка скана
              dict(box=((-30, 240), (742, 850), (-INF, -150)))],                 # ручка левого «пульта» (у F5 пульт один, справа)
        add=[dict(box=((-INF, -280), (-INF, 180), (-INF, INF)), s=(1, 1, 0.82), d=(0, 0, 0)),   # задние колёсики
             dict(box=((271, INF), (-INF, 200), (-INF, INF)), parts=("footrest", "frame"),
                  s=(1, 1, 1.2), d=(-5, 0, 0))]),                                # подножка с кронштейном
    # Бабушка Агата — Ki Mobility Focus CR: скан Tripo без наклона + антиопрокидыватели прежней модели
    # (масштаб по заднему колесу: старое R 249, центр x 15 → скан R 226, центр x −334); затем tilt_model.py 20°
    "focuscr": dict(
        base="art_tests/tripo/v3/models/chair_focuscr_ai.json",
        donor="art_tests/tripo/bak_before_v3/chair_focuscr_ai.json",
        out="art_tests/tripo/v3/models/chair_focuscr_patched.json",
        drop=[dict(box=((-INF, INF), (-INF, INF), (-INF, INF)), parts=("anti_tip",))],   # у скана это не они
        add=[dict(box=((-INF, INF), (-INF, INF), (-INF, INF)), parts=("anti_tip",),
                  s=(0.908, 0.908, 1.0), d=(-347.6, 0, 0))]),
}


def inside(c, box):
    return all(lo <= v <= hi for v, (lo, hi) in zip(c, box))


def patch(spec, base_path, donor_path, out_path):
    d = json.load(open(base_path, encoding="utf-8"))
    don = json.load(open(donor_path, encoding="utf-8"))
    V, F, names = d["verts"], d["faces"], d["parts"]
    cen = lambda VV, f: [sum(VV[i][k] for i in f[:3]) / 3 for k in range(3)]
    keep = []
    for f in F:
        c = cen(V, f)
        if any(inside(c, r["box"]) and (not r.get("parts") or names[f[3]] in r["parts"]) for r in spec.get("drop", [])):
            continue
        keep.append(f)
    nd = 0
    for r in spec.get("add", []):
        vmap = {}
        for f in don["faces"]:
            c = cen(don["verts"], f)
            pn = don["parts"][f[3]]
            if not inside(c, r["box"]) or (r.get("parts") and pn not in r["parts"]):
                continue
            pn = r.get("part", pn)
            if pn not in names:
                names.append(pn)
            nf = []
            for i in f[:3]:
                if i not in vmap:
                    x, y, z = don["verts"][i]
                    vmap[i] = len(V)
                    V.append([round(x * r["s"][0] + r["d"][0], 1), round(y * r["s"][1] + r["d"][1], 1),
                              round(z * r["s"][2] + r["d"][2], 1)])
                nf.append(vmap[i])
            keep.append(nf + [names.index(pn)] + list(f[4:7]))
            nd += 1
    k = spec.get("brighten")                         # тёмный скан: цвета светлее (детали не сливаются в окне игры)
    if k:
        for f in keep:
            f[4:7] = [min(255, int(c * k + 12)) for c in f[4:7]]
    used = sorted({i for f in keep for i in f[:3]})
    remap = {o: n for n, o in enumerate(used)}
    d["verts"] = [V[i] for i in used]
    d["faces"] = [[remap[f[0]], remap[f[1]], remap[f[2]]] + f[3:] for f in keep]
    json.dump(d, open(out_path, "w", encoding="utf-8"), separators=(",", ":"))
    print(f"{out_path}: убрано {len(F) - (len(keep) - nd)}, добавлено {nd}, граней {len(keep)}")


if __name__ == "__main__":
    spec = PATCHES[sys.argv[1]]
    patch(spec, spec["base"], spec["donor"], spec["out"])
    lod = lambda p: p.replace(".json", "_lod.json")
    patch(spec, lod(spec["base"]), lod(spec["donor"]), lod(spec["out"]))
