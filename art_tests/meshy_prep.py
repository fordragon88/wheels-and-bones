"""Референсы для Meshy (Multi-image to 3D): по 4 снимка коляски со всех сторон -> art_tests/meshy_ref/<коляска>/.
Фон — белый (у фото с фоном — вырезка BiRefNet в ComfyUI), объект по центру с полями, 1024×1024; цвет, где
на фото другой, приводится к цвету коляски в игре (сдвиг оттенка насыщенных пикселей).
python art_tests/meshy_prep.py   (исходники — art_tests/meshy_ref/_raw/<ключ>/, скачаны meshy_fetch.py)"""
import os, sys, colorsys, shutil
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "meshy_ref", "_raw")
OUT = os.path.join(HERE, "meshy_ref")
SP = r"C:\Users\wario\AppData\Local\Temp\claude\D--wheels-and-bones\d845888a-7a45-42b9-a337-635687a142cf\scratchpad"
sys.path.insert(0, SP)

# ключ: (папка, [(файл, вид)], нужна вырезка фона, перекраска (оттенок_от, оттенок_до, допуск) в градусах или None)
SETS = {
    "1_Permobil_M3_Corpus": ("m3", [("m3-corpus-01.png", "1_front_3-4"), ("m3-corpus-05.png", "2_side"),
                                    ("m3-corpus-04.png", "3_top_from_back"), ("m3-corpus-07.png", "4_other_side")],
                             False, (0, 275, 28)),                     # красный -> фиолетовый, как в игре
    "2_Permobil_F5_Corpus": ("f5", [("00_f5-corpus-15.png", "1_front_3-4"), ("05_f5-corpus-20.png", "2_front"),
                                    ("02_f5-corpus-17.png", "3_back"), ("01_untitled-1_f5-corpus-iso-right-no-lights.png", "4_back_3-4")],
                             False, "gray"),                           # бирюзовый -> графит, как в игре
    "3_Quantum_Edge_4": ("edge4", [("00_Quantum-Edge-4.jpg", "1_front_3-4"), ("03_Quantum-Edge-left-view.jpg", "2_side"),
                                   ("04_Quantum-Edge-right-view.jpg", "3_other_side")],   # вида сзади у новой Edge 4 нет нигде
                         False, (228, 2, 30)),                         # синий -> красный, как в игре
    "4_Quantum_Q6_Edge": ("q6edge", [("00_dscn1449_orig.jpg", "1_front_3-4"), ("01_dscn1450_orig.jpg", "2_side"),
                                     ("03_dscn1452_orig.jpg", "3_back"), ("05_dscn1454_orig.jpg", "4_other_side")],
                          True, None),
    "5_Drive_Trident_HD": ("trident", [("00_trident_hd_power_wheelchair.jpg", "1_front_3-4"),
                                       ("01_side_trident_hd_power_wheelchair.jpg", "2_side"),
                                       ("03_back_trident_hd_power_wheelchair.jpg", "3_back"),
                                       ("02_front_trident_hd_power_wheelchair.jpg", "4_front")], False, None),
    "6_Quickie_Pulse_6": ("pulse6", [("00_s-l1600.jpg", "1_front"), ("03_s-l1600.jpg", "2_side"),
                                     ("01_s-l1600.jpg", "3_back"), ("02_s-l1600.jpg", "4_other_side")], True, None),
}


def cut_bg(path, name):
    """Вырезка фона BiRefNet-HR-matting (ComfyUI) -> RGBA."""
    from comfy_client import upload, queue, wait, download
    src = upload(path, f"wnb_meshy_{name}.png")
    g = {"1": {"class_type": "LoadImage", "inputs": {"image": src}},
         "2": {"class_type": "BiRefNetRMBG", "inputs": {"image": ["1", 0], "model": "BiRefNet-HR-matting", "sensitivity": 1.0,
                                                        "process_res": 1024, "mask_blur": 0, "mask_offset": 0,
                                                        "invert_output": False, "refine_foreground": True,
                                                        "background": "Alpha", "background_color": "#ffffff"}},
         "3": {"class_type": "SaveImage", "inputs": {"images": ["2", 0], "filename_prefix": f"wnb/meshy/{name}"}}}
    p = download(wait(queue(g)), os.path.join(SP, "meshy_cut"), name)
    return Image.open(p[0]).convert("RGBA")


def recolor(im, rule):
    a = np.asarray(im.convert("RGBA")).astype(np.float32) / 255
    rgb, al = a[..., :3], a[..., 3:]
    mx, mn = rgb.max(-1), rgb.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    hsv = np.vectorize(colorsys.rgb_to_hsv, otypes=[float, float, float])
    if rule == "gray":                                   # насыщенное -> графит той же яркости
        m = sat > 0.3
        g = (0.35 * mx)[..., None] + 0.08
        rgb = np.where(m[..., None], np.repeat(g, 3, -1), rgb)
    else:
        h0, h1, tol = rule
        h, s, v = hsv(rgb[..., 0], rgb[..., 1], rgb[..., 2])
        dh = np.abs(((h * 360 - h0) + 180) % 360 - 180)
        m = (s > 0.35) & (dh < tol) & (v > 0.12)
        h2 = np.where(m, h1 / 360.0, h)
        r, g_, b = np.vectorize(colorsys.hsv_to_rgb, otypes=[float, float, float])(h2, s, v)
        rgb = np.stack([r, g_, b], -1)
    return Image.fromarray(np.uint8(np.clip(np.concatenate([rgb, al], -1), 0, 1) * 255))


def frame(im, size=1024, pad=0.08):
    """На белый фон, объект по центру с полями."""
    im = im.convert("RGBA")
    a = np.asarray(im)[..., 3]
    if a.min() == 255:                                   # фото без прозрачности (студийное на белом): обрезка по «не белому»
        rgb = np.asarray(im.convert("RGB")).astype(int)
        nz = np.nonzero((rgb < 240).any(-1))
    else:
        nz = np.nonzero(a > 10)
    y0, y1, x0, x1 = nz[0].min(), nz[0].max() + 1, nz[1].min(), nz[1].max() + 1
    im = im.crop((x0, y0, x1, y1))
    k = size * (1 - 2 * pad) / max(im.size)
    im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)
    bg = Image.new("RGBA", (size, size), (255, 255, 255, 255))
    bg.alpha_composite(im, ((size - im.width) // 2, (size - im.height) // 2))
    return bg.convert("RGB")


only = sys.argv[1:] or list(SETS)
for key in only:
    folder, files, need_cut, rule = SETS[key]
    dst = os.path.join(OUT, key)
    shutil.rmtree(dst, ignore_errors=True)
    os.makedirs(dst)
    for fn, view in files:
        src = os.path.join(RAW, folder, fn)
        im = cut_bg(src, f"{folder}_{view}") if need_cut else Image.open(src).convert("RGBA")
        if rule:
            im = recolor(im, rule)
        frame(im).save(os.path.join(dst, f"{view}.png"))
    sheet = Image.new("RGB", (len(files) * 256, 256), "white")
    for i, (_, view) in enumerate(files):
        sheet.paste(Image.open(os.path.join(dst, f"{view}.png")).resize((256, 256)), (i * 256, 0))
    sheet.save(os.path.join(dst, "_all4.png"))
    print(key, "готово")
