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
    "4_Quantum_Q6_Edge": ("q6edge2", [("01_PWR01076Front.jpg", "1_front"), ("02_PWR01076RightSide.jpg", "2_side"),
                                      ("05_PWR01076Back.jpg", "3_back"), ("06_PWR01076LeftSide.jpg", "4_other_side")],
                          False, None),                         # студийные фото магазина (Q6 Edge 2.0), белый фон
    "5_Drive_Trident_HD": ("trident", [("00_trident_hd_power_wheelchair.jpg", "1_front_3-4"),
                                       ("01_side_trident_hd_power_wheelchair.jpg", "2_side"),
                                       ("03_back_trident_hd_power_wheelchair.jpg", "3_back"),
                                       ("02_front_trident_hd_power_wheelchair.jpg", "4_front")], False, None),
    "6_Quickie_Pulse_6": ("pulse6b", [("00_PWR00807Overview_0b1331c4-4699-452f-a0bf-88329d5f13f8.jpg", "1_front_3-4"),
                                      ("02_PWR00807RightSide_7c6fb164-c9e0-4dba-8604-abdbb2e39bfc.jpg", "2_side"),
                                      ("03_PWR00807Back_0fa992fc-732c-4c26-83ed-54667b911628.jpg", "3_back"),
                                      ("04_PWR00807LeftSide_d59645f7-4fa6-4d5d-8bad-8162c900d1c7.jpg", "4_other_side"),
                                      ("01_PWR00807Front_958e5491-e7f8-463d-be89-5ddb709c1c69.jpg", "5_front")], False, None),
    "8_Ki_Mobility_Focus_CR": ("focuscr", [("00_PhotoAug012023_12249PM.jpg", "1_front_3-4"),
                                           ("02_PhotoAug012023_12247PM.jpg", "2_side"),
                                           ("01_PhotoAug012023_12246PM.jpg", "3_back"),
                                           ("04_PhotoAug012023_12250PM.jpg", "4_other_side"),
                                           ("06_PhotoAug012023_12252PM.jpg", "5_front")], False, None),   # прямо; наклон — в игре
    "9_Zippie_Iris": ("iris2", [("00_image_b21f2a94-7f9d-49b6-aa74-f", "1_front_3-4"),
                                ("04_image_8cea1d28-3d39-48a6-b01b-b", "2_side"),
                                ("05_image_15e6e694-d74c-4bc9-977f-3", "3_back"),
                                ("03_image_e727272c-6a41-49d3-b0ef-f", "4_front")], False, None),
    # ---- ручные (студийные фото производителя / магазина) ----
    "10_TiLite_Aero_Z": ("aeroz", [("00_", "1_front_3-4"), ("03_", "2_side"), ("02_", "3_back"),
                                   ("04_", "4_other_side"), ("01_", "5_front")], False, None),
    "11_WHILL_Model_C2": ("whillci", [("00_", "1_front_3-4"), ("04_", "2_side"), ("05_", "3_back"),
                                       ("06_", "4_other_side"), ("01_", "5_front")], False, None),
    "12_Etac_Cross_6": ("cross6", [("00_", "1_front_3-4"), ("01_", "2_side"), ("02_", "3_back"), ("03_", "4_front")],
                        False, None),
    "13_Panthera_X3": ("x3", [("00_", "1_view_a"), ("01_", "2_view_b"), ("02_", "3_view_c"), ("03_", "4_view_d")],
                       True, None),
    "14_Progeo_Noir_2": ("noir_arch", [("01_", "1_front"), ("02_", "2_front_3-4"), ("03_", "3_side"),
                                       ("04_", "4_back_3-4_other_side")], True, None),   # архив rehateamprogeo.com
    "15_Vermeiren_D100": ("d100", [("00_", "1_front_3-4"), ("01_", "2_side")], False, None),
    "16_Invacare_9000": ("inv9000", [("00_", "1_front_3-4"), ("01_", "2_other_3-4"), ("02_", "3_side"),
                                     ("04_", "4_front_folded")], False, None),
    "17_Magic_Mobility_X8": ("x8", [("00_", "1_side"), ("11_", "2_other_side"), ("05_", "3_front_3-4")], True, None),
    "18_Quickie_Nitrum": ("nitrum", [("03_", "1_front_3-4"), ("04_", "2_other_3-4"), ("01_", "3_side")], True, None),
    "19_Progeo_Ego": ("ego", [("13_", "1_front_3-4"), ("40_", "2_back_3-4_other_side")],
                      True, (28, 72, 22)),   # 40_ — архив rehateamprogeo.com EG0005: оранжевая рама -> салатовая, как 13_
    "20_Progeo_Tekna_Advance": ("tekna", [("01_", "1_view_a"), ("13_", "2_view_b"), ("30_", "3_view_c"),
                                          ("31_", "4_view_d")], True, None),   # 30_, 31_ — johnpreston.ie
    "21_Progeo_Exelle_Junior": ("exelle_arch", [("03_", "1_front_3-4"), ("10_", "2_side"), ("02_", "3_back_3-4"),
                                              ("01_", "4_other_side")], True, None),   # архив rehateamprogeo.com
    "7_Pride_Jazzy_614": ("jazzy614b", [("00_PhotoRoom_000_20230222_094737.jpg", "1_front_3-4"),
                                        ("03_PhotoRoom_003_20230222_094737.jpg", "2_side"),
                                        ("05_PhotoRoom_005_20230222_094737.jpg", "3_back"),
                                        ("04_PhotoRoom_004_20230222_094737.jpg", "4_other_side"),
                                        ("01_PhotoRoom_001_20230222_094737.jpg", "5_front")], False, None),
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
        if not os.path.exists(src):                     # имя дано началом
            src = os.path.join(RAW, folder, next(f for f in sorted(os.listdir(os.path.join(RAW, folder))) if f.startswith(fn)))
        im = cut_bg(src, f"{folder}_{view}") if need_cut else Image.open(src).convert("RGBA")
        if rule:
            im = recolor(im, rule)
        frame(im).save(os.path.join(dst, f"{view}.png"))
    sheet = Image.new("RGB", (5 * 256, 256), "white")
    for i, (_, view) in enumerate(files):
        sheet.paste(Image.open(os.path.join(dst, f"{view}.png")).resize((256, 256)), (i * 256, 0))
    sheet.save(os.path.join(dst, "_all4.png"))
    print(key, "готово")
