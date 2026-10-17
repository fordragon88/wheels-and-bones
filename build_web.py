"""Браузерная версия (pygbag → WebAssembly): python build_web.py [--serve]

Собирает папку web_build/wheels_and_bones (main.py + game.py + assets, музыка в .ogg),
затем pygbag кладёт готовый сайт в web_build/wheels_and_bones/build/web/:
  index.html + wheels_and_bones.apk + favicon.png — эти файлы и выкладываются на сервер.
--serve — после сборки запустить локальный сервер http://localhost:8000 для проверки."""
import os, sys, shutil, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(ROOT, "web_build", "wheels_and_bones")

MAIN = '''# Колёса и Кости — браузерная версия (собрано build_web.py, не править вручную)
import asyncio
import pygame          # pygbag подгружает пакеты по импортам main.py — pygame нужен до game
# numpy в браузерной сборке ломает дисплей SDL («did not add any displays») — без него 3D-осмотр
# заменяется рисунками колясок


async def start():
    pygame.mixer.pre_init(44100, -16, 2, 4096)   # формат браузера и большой буфер — без хрипа
    pygame.init()
    pygame.display.set_mode((1280, 720))   # холст — сразу, внутри async (так SDL в браузере видит дисплей)
    import game
    await game.main()

asyncio.run(start())
'''


def stage():
    if os.path.isdir(APP):
        shutil.rmtree(APP)
    os.makedirs(APP)
    shutil.copy2(os.path.join(ROOT, "game.py"), APP)
    with open(os.path.join(APP, "main.py"), "w", encoding="utf-8") as f:
        f.write(MAIN)
    src, dst = os.path.join(ROOT, "assets"), os.path.join(APP, "assets")
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("*.ico", "README.txt", "*.mp3", "*.wav",
                                                       "*_ai.json", "*_ai_lod.json"))
    # 3D-модели (*_ai.json, 12 МБ) не берём: без numpy в браузере их не отрисовать, 3D-осмотр — схемой
    # музыка: браузер надёжно играет .ogg
    os.makedirs(os.path.join(dst, "music"), exist_ok=True)
    for name in os.listdir(os.path.join(src, "music")):
        base, ext = os.path.splitext(name)
        if ext.lower() in (".mp3", ".wav"):
            out = os.path.join(dst, "music", base + ".ogg")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(src, "music", name),
                            "-ac", "1", "-c:a", "libvorbis", "-q:a", "3", out], check=True)
    # картинки легче в 3–6 раз: фоны → JPEG, крупные рисунки → 256 цветов с прозрачностью
    from PIL import Image
    for name in os.listdir(dst):
        fp = os.path.join(dst, name)
        if not name.endswith(".png") or os.path.getsize(fp) < 150_000:
            continue
        im = Image.open(fp)
        if name.startswith("bg_"):
            im.convert("RGB").save(fp[:-4] + ".jpg", "JPEG", quality=86, optimize=True)
            os.remove(fp)
        else:
            im.convert("RGBA").quantize(colors=256, method=Image.Quantize.FASTOCTREE,
                                        dither=Image.Dither.FLOYDSTEINBERG).save(fp, "PNG", optimize=True)
    # значок вкладки
    import pygame
    icon = pygame.image.load(os.path.join(src, "ghost.png"))
    pygame.image.save(pygame.transform.smoothscale(icon, (64, 64)), os.path.join(APP, "favicon.png"))


def build(serve=False):
    cmd = [sys.executable, "-m", "pygbag", "--title", "Wheels & Bones", "--app_name", "wheels_and_bones",
           "--width", "1280", "--height", "720", "--ume_block", "0"]
    if not serve:
        cmd.append("--build")
    cmd.append(APP)
    subprocess.run(cmd, check=True, cwd=ROOT)


if __name__ == "__main__":
    stage()
    print("подготовлено:", APP)
    build(serve="--serve" in sys.argv)
    web = os.path.join(APP, "build", "web")
    if os.path.isdir(web):
        for n in os.listdir(web):
            print(f"  {n:32s} {os.path.getsize(os.path.join(web, n)) / 1e6:6.1f} МБ")
