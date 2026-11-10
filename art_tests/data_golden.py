"""«Золотое» сравнение содержания игры (задания, Гильдия, Кабинет посадки, справочники).

Импортирует game и пишет каноническое представление всех структур данных, которые грузятся из assets/data/:
JOBS (и результат resolve_job для каждого варианта), FOLK_JOBS, TECH_JOBS, SEAT_LESSONS, SEAT_CASES, SEAT_QUIZ,
SEAT_MENTOR, MANUAL, MANUAL_NOTES, TOOLS, PARTS, CREDITS и число ссылок на мануалы (source_links: комментарии
«# source:» в game.py + поля "source" в assets/data — ни одна не должна пропасть). Типы сохраняются явно: кортеж, список и множество
различаются ({"__tuple__": [...]}, {"__set__": [...]}), порядок ключей словарей — как в игре.

  python art_tests/data_golden.py            # записать текущее состояние в art_tests/data_golden_now.json
  python art_tests/data_golden.py --check    # сравнить с эталоном art_tests/data_golden_before.json (код 1 при отличии)
  python art_tests/data_golden.py --update   # перезаписать эталон (ТОЛЬКО при намеренной правке содержания)

Эталон снят на test-build ДО выноса данных из game.py в assets/data (10.11.2026). Любое отличие после
рефакторинга — ошибка загрузчика или данных. Если содержание правили намеренно — обновить эталон (--update).
Хэш строк фиксирован (PYTHONHASHSEED=0): порядок в tuple(set(...)) (насос → ниппель) от него зависит.
"""
import json
import os
import subprocess
import sys

if os.environ.get("PYTHONHASHSEED") != "0":
    env = dict(os.environ, PYTHONHASHSEED="0")
    sys.exit(subprocess.call([sys.executable, os.path.abspath(__file__)] + sys.argv[1:], env=env))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((8, 8))
import game  # noqa: E402

GOLDEN = os.path.join(HERE, "data_golden_before.json")
NOW = os.path.join(HERE, "data_golden_now.json")


def canon(v):
    """Значение → JSON-совместимое с явными типами контейнеров."""
    if isinstance(v, tuple):
        return {"__tuple__": [canon(x) for x in v]}
    if isinstance(v, (set, frozenset)):
        return {"__set__": sorted((canon(x) for x in v), key=repr)}
    if isinstance(v, list):
        return [canon(x) for x in v]
    if isinstance(v, dict):
        if all(isinstance(k, str) for k in v) and "__tuple__" not in v and "__set__" not in v:
            return {k: canon(x) for k, x in v.items()}
        return {"__dict__": [[canon(k), canon(x)] for k, x in v.items()]}
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    return {"__repr__": repr(v)}


def source_links():
    """Ссылки на мануалы: строки «# source:» в game.py + элементы полей "source" в assets/data/**/*.json.
    При выносе данных комментарии стали полями — сумма обязана сохраниться (до выноса: 211 комментариев)."""
    with open(os.path.join(ROOT, "game.py"), encoding="utf-8") as f:
        n = sum(1 for line in f if "# source:" in line)

    def walk(v):
        if isinstance(v, dict):
            return (len(v["source"]) if isinstance(v.get("source"), list) else 0) + sum(walk(x) for x in v.values())
        if isinstance(v, list):
            return sum(walk(x) for x in v)
        return 0
    data_dir = os.path.join(ROOT, "assets", "data")
    for dirpath, _dirs, files in os.walk(data_dir):
        for name in files:
            if name.endswith(".json"):
                with open(os.path.join(dirpath, name), encoding="utf-8") as f:
                    n += walk(json.load(f))
    return n


def snapshot():
    jobs = list(game.JOBS)
    resolved = {}
    for j in jobs + list(game.TECH_JOBS):
        if "variants" in j:
            resolved[j["id"]] = [canon(game.resolve_job(j, i)) for i in range(len(j["variants"]))]
        else:
            resolved[j["id"]] = [canon(game.resolve_job(j))]
    data = {
        "JOBS": canon(jobs),
        "JOBS_ids": [j["id"] for j in jobs],
        "FOLK_JOBS": canon(list(game.FOLK_JOBS)),
        "FOLK_in_JOBS": [any(j is f for j in jobs) for f in game.FOLK_JOBS],
        "TECH_JOBS": canon(list(game.TECH_JOBS)),
        "ALL_JOBS_ids": [j["id"] for j in game.ALL_JOBS],
        "resolved": resolved,
        "SEAT_LESSONS": canon(game.SEAT_LESSONS),
        "SEAT_CASES": canon(game.SEAT_CASES),
        "SEAT_QUIZ": canon(game.SEAT_QUIZ),
        "SEAT_MENTOR": canon(game.SEAT_MENTOR),
        "MANUAL": canon(game.MANUAL),
        "MANUAL_NOTES": canon(game.MANUAL_NOTES),
        "TOOLS": canon(game.TOOLS),
        "PARTS": canon(game.PARTS),
        "CREDITS": canon(game.CREDITS),
        "source_links": source_links(),
    }
    return json.dumps(data, ensure_ascii=False, indent=1, sort_keys=False) + "\n"


def main():
    text = snapshot()
    if "--update" in sys.argv:
        with open(GOLDEN, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print(f"ЭТАЛОН ОБНОВЛЁН: {GOLDEN}")
        return 0
    if "--check" in sys.argv:
        with open(GOLDEN, encoding="utf-8") as f:
            want = f.read()
        if want == text:
            print("DATA GOLDEN OK — содержание совпадает с эталоном байт в байт")
            return 0
        with open(NOW, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        a, b = want.splitlines(), text.splitlines()
        for i, (x, y) in enumerate(zip(a, b)):
            if x != y:
                print(f"первое отличие в строке {i + 1}:\n  было:  {x[:200]}\n  стало: {y[:200]}")
                break
        else:
            print(f"длина разная: было {len(a)} строк, стало {len(b)}")
        print(f"DATA GOLDEN FAIL — текущее состояние в {NOW}; сравни с {GOLDEN}")
        return 1
    with open(NOW, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"записано: {NOW}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
