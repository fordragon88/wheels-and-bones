"""Студийные снимки коляски на белом фоне из магазина на Shopify (все фото товара из <url>/products/<handle>.json)
-> art_tests/meshy_ref/_raw/<ключ>/ + лист превью (meshy_fetch.py).
python art_tests/meshy_shop.py <ключ> <https://магазин/products/handle>"""
import json, os, subprocess, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
key, url = sys.argv[1], sys.argv[2].rstrip("/")
req = urllib.request.Request(url + ".json", headers={"User-Agent": "Mozilla/5.0"})
prod = json.load(urllib.request.urlopen(req, timeout=60))["product"]
print(prod["title"])
srcs = [im["src"].split("?")[0] for im in prod["images"]]
subprocess.run([sys.executable, os.path.join(HERE, "meshy_fetch.py"), key] + srcs, check=True)
