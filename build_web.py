"""Браузерная версия (pygbag → WebAssembly): python build_web.py [--serve]

Собирает папку web_build/wheels_and_bones (main.py + game.py + assets, музыка в .ogg),
затем pygbag кладёт готовый сайт в web_build/wheels_and_bones/build/web/:
  index.html + wheels_and_bones.apk + favicon.png — эти файлы и выкладываются на сервер.
--serve — после сборки запустить локальный сервер (проверять через http://127.0.0.1:8000).
--deploy — выложить сборку на GitHub Pages: https://fordragon88.github.io/wheels-and-bones-web/
           (публичный репозиторий только со сборкой; клон — в web_deploy/).
--off — скрыть всё: выключить GitHub Pages и сделать репозиторий приватным.
--on  — открыть: репозиторий публичный + GitHub Pages включены (сайт оживает через ~1 мин)."""
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


DEPLOY = os.path.join(ROOT, "web_deploy")
GH_REPO = "fordragon88/wheels-and-bones-web"
REPO = "https://github.com/fordragon88/wheels-and-bones-web.git"


def deploy():
    web = os.path.join(APP, "build", "web")
    if not os.path.isdir(os.path.join(DEPLOY, ".git")):
        subprocess.run(["git", "clone", "-q", REPO, DEPLOY], check=True)
    for n in os.listdir(web):
        shutil.copy2(os.path.join(web, n), DEPLOY)
    git = ["git", "-C", DEPLOY, "-c", "user.name=fordragon88",
           "-c", "user.email=98241749+fordragon88@users.noreply.github.com"]
    subprocess.run(git + ["add", "-A"], check=True)
    if subprocess.run(git + ["diff", "--cached", "--quiet"]).returncode:
        subprocess.run(git + ["commit", "-q", "-m", "Update web build"], check=True)
        subprocess.run(git + ["push", "-q"], check=True)
        public = subprocess.run(["gh", "api", f"repos/{GH_REPO}", "--jq", ".visibility"],
                                capture_output=True, text=True).stdout.strip() == "public"
        print("выложено: https://fordragon88.github.io/wheels-and-bones-web/ (обновится через ~1 мин)" if public
              else "сборка обновлена в скрытом репозитории (сайт выключен; открыть: python build_web.py --on)")
    else:
        print("сборка не изменилась — выкладывать нечего")


def site(on):
    """Включить/выключить публичный доступ к браузерной версии."""
    gh = ["gh", "api", "-X"]
    if on:
        subprocess.run(["gh", "repo", "edit", GH_REPO, "--visibility", "public",
                        "--accept-visibility-change-consequences"], check=True)
        subprocess.run(gh + ["POST", f"repos/{GH_REPO}/pages", "-f", "source[branch]=main", "-f", "source[path]=/"],
                       check=False, stdout=subprocess.DEVNULL)
        print("открыто: https://fordragon88.github.io/wheels-and-bones-web/ (заработает через ~1 мин)")
    else:
        subprocess.run(gh + ["DELETE", f"repos/{GH_REPO}/pages"], check=False)
        subprocess.run(["gh", "repo", "edit", GH_REPO, "--visibility", "private",
                        "--accept-visibility-change-consequences"], check=True)
        print("скрыто: сайт выключен, репозиторий приватный")


if __name__ == "__main__":
    if "--off" in sys.argv or "--on" in sys.argv:
        site("--on" in sys.argv)
        sys.exit(0)
    stage()
    print("подготовлено:", APP)
    build(serve="--serve" in sys.argv)
    web = os.path.join(APP, "build", "web")
    if os.path.isdir(web):
        for n in os.listdir(web):
            print(f"  {n:32s} {os.path.getsize(os.path.join(web, n)) / 1e6:6.1f} МБ")
    if "--deploy" in sys.argv:
        deploy()
