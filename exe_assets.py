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
print(f"exe assets: {kept} файлов в {DST}; отброшено {dropped} файлов, {dropped_bytes / 1e6:.1f} МБ")
