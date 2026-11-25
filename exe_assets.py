"""Копия assets/ для exe без лишнего: build/exe_assets (её кладёт build_exe.bat через --add-data "build\exe_assets;assets").
Не берём: полные 3D-модели models/chair_*_ai.json (игра на компьютере использует только *_lod.json — окно диагностики
и центры кружков; полные нужны лишь art_tests/blender_export.py), тела Бомма seat_body_*.png и seat_bodies.json
(SEAT_BODY_ON = False, отложено владельцем 23.10). Кадры поворота turntable/ нужны — на компьютере они и показываются.
python exe_assets.py   — пишет сколько файлов и мегабайт отброшено."""
import os, shutil, fnmatch

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC, DST = os.path.join(ROOT, "assets"), os.path.join(ROOT, "build", "exe_assets")
SKIP = ("models/chair_*_ai.json", "seat_body_*.png", "seat_bodies.json")


def skip(rel):
    rel = rel.replace("\\", "/")
    return any(fnmatch.fnmatch(rel, p) for p in SKIP)


if os.path.isdir(DST):
    shutil.rmtree(DST)
kept = dropped = 0
dropped_bytes = 0
for dp, _, files in os.walk(SRC):
    for fn in files:
        full = os.path.join(dp, fn)
        rel = os.path.relpath(full, SRC)
        if skip(rel):
            dropped += 1
            dropped_bytes += os.path.getsize(full)
            continue
        out = os.path.join(DST, rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        shutil.copy2(full, out)
        kept += 1
# Петли героев (anim/: проезд, волшебство — с 16.11 у всех 21 героя, 79 МБ исходников) ужимаем так же, как для браузера
# (build_web.shrink_anim: кадр не выше 400 px, JPEG 80, маска вдвое меньше — игра растягивает её сама): exe ~170 МБ
# вместо ~200, а картинка та же, что на сайте.
import build_web
EXE_FULL_LOOPS = {"magic_martin"}
before = after = n_anim = 0
for dp, _, files in os.walk(os.path.join(DST, "anim")):
    for fn in files:
        # magic_martin не ужимаем: рядом с ним на портрете живая петля martin_idle в полном разрешении, и ужатое
        # «волшебство» выглядело мягче неё (замечание владельца 20.11 про стык; кадры перенарезаны 21.11 — 562 px)
        if (fn.endswith((".jpg", ".png")) and os.path.basename(dp).startswith(("ride_", "magic_"))
                and os.path.basename(dp) not in EXE_FULL_LOOPS):                                  # машущие — как были
            fp = os.path.join(dp, fn)
            before += os.path.getsize(fp)
            # «волшебство» 20 героев с 25.11 нарезано 480 px (портрет в кадре ~380 px — без растяжения на 1080p):
            # в exe оставляем эту высоту (JPEG 80 и половинная маска — как у всех), проезд — 400, как на сайте
            build_web.shrink_anim(fp, max_h=480 if os.path.basename(dp).startswith("magic_") else 400)
            after += os.path.getsize(fp)
            n_anim += 1
print(f"exe assets: петли anim — {n_anim} кадров ужато, {before / 1e6:.1f} → {after / 1e6:.1f} МБ")
print(f"exe assets: {kept} файлов в {DST}; отброшено {dropped} файлов, {dropped_bytes / 1e6:.1f} МБ")
