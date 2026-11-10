"""Тексты игры из файлов данных assets/data/**/*.json (задания, Гильдия, Кабинет посадки, мануал, сноски, титры…).

С 10.11.2026 содержание вынесено из game.py, поэтому скрипты перевода и чистки словаря читают и game.py (AST),
и эти файлы. Текст для перевода — любое строковое ЗНАЧЕНИЕ в JSON, кроме полей "source" (ссылки на страницы
мануалов) и "comment" (заметки разработчиков); ключи объектов (id деталей, имена полей) — не текст. Строки без
кириллицы (id, имена файлов, «TiLite Aero Z») отбрасывает уже вызывающий скрипт.

    from data_strings import data_strings
    for text, where in data_strings(): ...      # where — путь файла от корня проекта
"""
import json
import os

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DATA_DIR = os.path.join(ROOT, "assets", "data")
SKIP_KEYS = ("source", "comment")


def _walk(v, out, where):
    if isinstance(v, str):
        out.append((v, where))
    elif isinstance(v, list):
        for x in v:
            _walk(x, out, where)
    elif isinstance(v, dict):
        for k, x in v.items():
            if k not in SKIP_KEYS:
                _walk(x, out, where)


def data_files():
    """Все .json в assets/data в стабильном порядке (как их перечисляет загрузчик — по алфавиту путей)."""
    files = []
    for dirpath, _dirs, names in os.walk(DATA_DIR):
        for n in names:
            if n.endswith(".json"):
                files.append(os.path.join(dirpath, n))
    return sorted(files)


def data_strings():
    """[(строка, файл)] — все строковые значения файлов данных, без полей source/comment, с повторами."""
    out = []
    for path in data_files():
        with open(path, encoding="utf-8") as f:
            _walk(json.load(f), out, os.path.relpath(path, ROOT).replace(os.sep, "/"))
    return out


if __name__ == "__main__":
    import re
    cyr = re.compile("[А-Яа-яЁё]")
    s = data_strings()
    print(len(s), "строк в", len(data_files()), "файлах;", len({t for t, _ in s if cyr.search(t)}),
          "разных с кириллицей")
