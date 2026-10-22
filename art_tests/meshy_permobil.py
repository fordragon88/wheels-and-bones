"""Студийные рендеры коляски с сайта Permobil (галерея товара: …/media/<id>/<имя>.png) -> art_tests/meshy_ref/_raw/<ключ>/.
Permobil выпускает и Progeo, и Panthera. python art_tests/meshy_permobil.py <ключ> <url страницы товара>"""
import os, re, subprocess, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
key, url = sys.argv[1], sys.argv[2]
html = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read().decode(
    "utf-8", "replace")
imgs = []
for m in re.findall(r'https://permobilwebcdn\.azureedge\.net/media/[a-z0-9]+/[^"\'?\s)]+\.(?:png|jpg|jpeg)', html, re.I):
    if m not in imgs and not re.search(r"logo|icon|header|banner|woman|man_|lifestyle|_web", m, re.I):
        imgs.append(m)
print(len(imgs), "картинок")
subprocess.run([sys.executable, os.path.join(HERE, "meshy_fetch.py"), key] + [i + "?width=1600" for i in imgs[:24]], check=True)
