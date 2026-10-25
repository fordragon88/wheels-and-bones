"""Браузерная версия (pygbag → WebAssembly): python build_web.py [--serve]

Собирает папку web_build/wheels_and_bones (main.py + game.py + assets, музыка в .ogg),
затем pygbag кладёт готовый сайт в web_build/wheels_and_bones/build/web/:
  index.html + wheels_and_bones.apk + favicon.png — эти файлы и выкладываются на сервер.
--serve — после сборки запустить локальный сервер (проверять через http://127.0.0.1:8000).
--deploy — выложить сборку на GitHub Pages: https://fordragon88.github.io/wheels-and-bones-web/
           (публичный репозиторий только со сборкой; клон — в web_deploy/).
--off — скрыть всё: выключить GitHub Pages и сделать репозиторий приватным.
--on  — открыть: репозиторий публичный + GitHub Pages включены (сайт оживает через ~1 мин)."""
import re, os, sys, shutil, subprocess

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
    pygame.display.set_mode((1920, 1080))   # холст 1920×1080 (= WEB_RES в game.py) — сразу, внутри async (так SDL в браузере видит дисплей)
    import game
    await game.main()

asyncio.run(start())
'''


def _bleed(im):
    """Цвет под прозрачными пикселями — от соседних видимых: без этого JPEG даёт тёмную кайму по контуру."""
    import numpy as np
    from PIL import Image, ImageFilter
    a = np.asarray(im.split()[3], np.float32) / 255
    rgb = np.asarray(im.convert("RGB"), np.float32)
    out = rgb.copy()
    pm = Image.fromarray(np.uint8(np.clip(rgb * a[..., None], 0, 255)))
    wa = Image.fromarray(np.uint8(a * 255))
    for r in (2, 6, 16, 40):
        bp = np.asarray(pm.filter(ImageFilter.GaussianBlur(r)), np.float32)
        bw = np.asarray(wa.filter(ImageFilter.GaussianBlur(r)), np.float32) / 255
        m = (a < 0.5) & (bw > 0.02)
        out[m] = (bp / np.maximum(bw[..., None], 1e-3))[m]
    return Image.fromarray(np.uint8(np.clip(out, 0, 255)))


def stage():
    if os.path.isdir(APP):
        shutil.rmtree(APP)
    os.makedirs(APP)
    shutil.copy2(os.path.join(ROOT, "game.py"), APP)
    with open(os.path.join(APP, "main.py"), "w", encoding="utf-8") as f:
        f.write(MAIN)
    src, dst = os.path.join(ROOT, "assets"), os.path.join(APP, "assets")
    skip = shutil.ignore_patterns("*.ico", "README.txt", "*.mp3", "*.wav", "*_ai.json", "*_ai_lod.json",
                                  "seat_body_*.png", "seat_bodies.json")   # кукла Бомма отложена (SEAT_BODY_ON=False)

    def ignore(d, names):
        out = set(skip(d, names))
        if os.path.basename(d) == "turntable":                # кадры поворота — не в пакет, а рядом на сайт:
            out |= {n for n in names if n.endswith((".png", ".jpg"))}   # и png, и jpg+маски (в пакете — только index*.json;
        return out                                            # браузер качает кадры с сайта, 23.10 jpg весили 27 МБ в архиве)
    shutil.copytree(src, dst, ignore=ignore)
    # 3D-модели (*_ai.json, 12 МБ) не берём: без numpy в браузере их не отрисовать. В окне диагностики
    # коляску показывают кадры поворота (assets/turntable): игра скачивает их с сайта, когда коляска на экране
    # музыка: браузер надёжно играет .ogg
    os.makedirs(os.path.join(dst, "music"), exist_ok=True)
    for name in os.listdir(os.path.join(src, "music")):
        base, ext = os.path.splitext(name)
        if ext.lower() in (".mp3", ".wav"):
            out = os.path.join(dst, "music", base + ".ogg")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(src, "music", name),
                            "-ac", "1", "-c:a", "libvorbis", "-q:a", "3", out], check=True)
    # крупные картинки легче в 3–5 раз без «ряби» палитры в 256 цветов: цвет — JPEG, у рисунков прозрачность —
    # отдельной серой PNG <имя>.a.png (WebP браузерный pygame не читает). Игра собирает их сама (asset_path)
    from PIL import Image
    for name in os.listdir(dst):
        fp = os.path.join(dst, name)
        if (not name.endswith(".png") or name.endswith(".a.png") or os.path.getsize(fp) < 150_000
                or name.startswith("seat_body_")):            # части куклы тела грузятся напрямую — им нужна PNG
            continue
        im = Image.open(fp)
        if name.startswith("bg_"):
            im.convert("RGB").save(fp[:-4] + ".jpg", "JPEG", quality=90, optimize=True)
        else:
            im = im.convert("RGBA")
            _bleed(im).save(fp[:-4] + ".jpg", "JPEG", quality=88, optimize=True)
            mask = Image.new("RGBA", im.size, (255, 255, 255, 0))     # белая маска: игра умножает на неё
            mask.putalpha(im.split()[3])                              # (BLEND_RGBA_MULT — быстро и на телефоне)
            mask.save(fp[:-4] + ".a.png", "PNG", optimize=True)
        os.remove(fp)
    # значок вкладки
    import pygame
    icon = pygame.image.load(os.path.join(src, "ghost.png"))
    pygame.image.save(pygame.transform.smoothscale(icon, (64, 64)), os.path.join(APP, "favicon.png"))


def build(serve=False):
    cmd = [sys.executable, "-m", "pygbag", "--title", "Wheels & Bones", "--app_name", "wheels_and_bones",
           "--width", "1920", "--height", "1080", "--ume_block", "0"]
    if not serve:
        cmd.append("--build")
    cmd.append(APP)
    tt = os.path.join(APP, "build", "web", "turntable")       # кадры поворота колясок — файлами рядом с игрой
    os.makedirs(os.path.dirname(tt), exist_ok=True)
    shutil.rmtree(tt, ignore_errors=True)
    shutil.copytree(os.path.join(ROOT, "assets", "turntable"), tt,
                    ignore=lambda d, names: [n for n in names if not n.endswith((".png", ".jpg"))])
    subprocess.run(cmd, check=True, cwd=ROOT)
    polish_index(os.path.join(APP, "build", "web"))


SPLASH_CSS = """
<style id="wnb-splash-css">
  #wnb-splash { position: fixed; inset: 0; z-index: 999995; pointer-events: none; display: flex; flex-direction: column;
    align-items: center; justify-content: flex-end; padding-bottom: 7vh; box-sizing: border-box;
    background: linear-gradient(to bottom, rgba(0,0,0,0) 50%, rgba(10,8,14,.72) 100%), #1d1b24 url(splash.jpg) center / cover no-repeat;
    color: #f0b85a; transition: opacity .7s; }
  #wnb-splash .t { font: bold clamp(34px, 6vw, 64px) Georgia, "Times New Roman", serif; letter-spacing: 2px;
    text-shadow: 0 2px 16px #000, 0 0 3px #000; margin-bottom: 8px; }
  #wnb-splash .s { font: clamp(13px, 1.6vw, 17px) sans-serif; color: #ece6d4; text-shadow: 0 1px 8px #000, 0 0 2px #000;
    margin: 0 24px 18px; text-align: center; max-width: 680px; }
  #wnb-splash progress { width: min(460px, 80vw); height: 14px; accent-color: #e8a33d; }
  #wnb-splash .m { font: bold 15px sans-serif; color: #f0b85a; text-shadow: 0 1px 6px #000; margin-top: 10px; min-height: 20px; }
  #infobox { background: rgba(29, 27, 36, .94) !important; color: #f0b85a !important; border: 2px solid #e8a33d; border-radius: 12px;
    font: bold 18px sans-serif; text-align: center; box-shadow: 0 4px 24px #000; }
</style>
"""
SPLASH_HTML = ('<div id="wnb-splash"><div class="t">Wheels &amp; Bones</div>'
               '<div class="s">Loading the workshop… about 12 MB, usually 20–40 seconds. '
               'Nothing to install — the game runs right here in your browser.</div>'
               '<progress id="wnb-sp-bar" max="100" value="0"></progress><div class="m" id="wnb-sp-msg">Downloading…</div></div>'
               '<script>(function(){var sp=document.getElementById("wnb-splash");'
               'function tick(){if(window.wnbState){sp.style.opacity="0";setTimeout(function(){sp.remove();},800);return;}'
               'var p=document.getElementById("progress"),st=document.getElementById("status"),ib=document.getElementById("infobox"),'
               'bar=document.getElementById("wnb-sp-bar"),msg=document.getElementById("wnb-sp-msg");'
               'if(p&&p.max&&p.value>0){bar.max=p.max;bar.value=p.value;}else{bar.removeAttribute("value");}'
               'var txt=(ib&&ib.offsetParent!==null&&ib.innerText)||(st&&st.innerText)||"";'
               'if(/Ready/i.test(txt)){txt="Ready — click or tap anywhere to start";bar.max=100;bar.value=100;}'
               'if(txt)msg.textContent=txt;setTimeout(tick,250);}tick();})();</script>')


def polish_index(web):
    """Заставка загрузки (владелец 25.10): pygbag прячет свой #transfer почти сразу и 20–40 с показывает серую страницу с
    «Loading, please wait». Свой оверлей #wnb-splash: фон splash.jpg (art_tests/web_splash.jpg), заголовок, подпись,
    полоса (копирует #progress pygbag) и сообщение (#status / #infobox, «Ready…» → «click or tap anywhere to start»).
    pointer-events:none — клик «Ready to start» проходит на страницу; исчезает, когда игра пошла (window.wnbState)."""
    shutil.copy2(os.path.join(ROOT, "art_tests", "web_splash.jpg"), os.path.join(web, "splash.jpg"))
    index = os.path.join(web, "index.html")
    html = open(index, encoding="utf-8").read()
    if "wnb-splash-css" in html:
        return
    html = html.replace("</head>", SPLASH_CSS + "</head>", 1)
    html = html.replace("<body>", "<body>" + SPLASH_HTML, 1)
    open(index, "w", encoding="utf-8").write(html)



DEPLOY = os.path.join(ROOT, "web_deploy")
GH_REPO = "fordragon88/wheels-and-bones-web"
REPO = "https://github.com/fordragon88/wheels-and-bones-web.git"


def stamp_archives(index):
    """Метка версии в ссылке на архив игры (?v=хэш содержимого): после выкладки браузер (Firefox) не берёт старую копию."""
    import hashlib
    web = os.path.dirname(index)
    html = open(index, encoding="utf-8").read()
    for name in ("wheels_and_bones.tar.gz", "wheels_and_bones.apk"):
        path = os.path.join(web, name)
        if not os.path.exists(path):
            continue
        h = hashlib.sha1(open(path, "rb").read()).hexdigest()[:10]
        html = re.sub(r'platform\.fopen\("' + re.escape(name) + r'(\?v=[0-9a-f]+)?"', f'platform.fopen("{name}?v={h}"', html)
    open(index, "w", encoding="utf-8").write(html)


def wait_pages(timeout=900):
    """Ждать, пока GitHub Pages соберёт ИМЕННО выложенный коммит (latest build может быть ещё прежним)."""
    import time
    head = subprocess.run(["git", "-C", DEPLOY, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = subprocess.run(["gh", "api", f"repos/{GH_REPO}/pages/builds/latest", "--jq", '.status+" "+.commit'],
                           capture_output=True, text=True).stdout.strip()
        if r == f"built {head}":
            print("pages: built", head[:8])
            return True
        if r.startswith("errored") and r.endswith(head):
            print("pages: ОШИБКА сборки", r)
            return False
        time.sleep(15)
    print("pages: не дождался сборки", head[:8])
    return False


def deploy():
    web = os.path.join(APP, "build", "web")
    if not os.path.isdir(os.path.join(DEPLOY, ".git")):
        subprocess.run(["git", "clone", "-q", REPO, DEPLOY], check=True)
    for n in os.listdir(web):
        if os.path.isdir(os.path.join(web, n)):
            shutil.rmtree(os.path.join(DEPLOY, n), ignore_errors=True)
            shutil.copytree(os.path.join(web, n), os.path.join(DEPLOY, n))
        else:
            shutil.copy2(os.path.join(web, n), DEPLOY)
    stamp_archives(os.path.join(DEPLOY, "index.html"))
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
        if public:
            wait_pages()
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
            if os.path.isfile(os.path.join(web, n)):
                print(f"  {n:32s} {os.path.getsize(os.path.join(web, n)) / 1e6:6.1f} МБ")
    if "--deploy" in sys.argv:
        deploy()
