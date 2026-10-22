"""Реплики и сюжетные тексты игры -> таблица для редактора (английский текст правят в колонке «New English»).
python art_tests/dialogs_export.py  -> art_tests/dialogs/WheelsAndBones_dialogues.xlsx
Обратно: python art_tests/dialogs_import.py <файл.xlsx>  (правки -> i18n_work/en9_fixes15_editor.json)."""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import pygame
pygame.init()
pygame.display.set_mode((1280, 720))
import game
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation  # noqa: F401  (на будущее)

SRC = open(os.path.join(HERE, "..", "game.py"), encoding="utf-8").read()
OUT = os.path.join(HERE, "dialogs", "WheelsAndBones_dialogues.xlsx")
game.set_lang("en")
EN = game.tr

rows = {"Dialogues": [], "Story": [], "Job texts": []}
seen = set()
SPEAKERS = {"Бренна", "Барти", "Бартоломью", "Мартин"}


def add(sheet, where, who, ru):
    if not ru or ru in seen:
        return
    seen.add(ru)
    en = EN(ru)
    if who is None:                                   # говорящий — из перевода: «Zix: “…”» -> Zix
        who = en.split(":", 1)[0].strip() if ":" in en[:40] else ""
        SPEAKERS.add(ru.split(":", 1)[0].strip())
    else:
        who = EN(who) if who else ""
    rows[sheet].append((where, who, en, ru))


titles = {j["id"]: j["title"] for j in game.ALL_JOBS}
order = [j["id"] for j in game.ALL_JOBS]
# 1. Реплики клиентов и наставников по заданиям
KIND = {"intro": "arrives", "worry": "chats while you work", "learn": "shares a tip", "mistake": "after your mistake",
        "good": "after a good step", "test": "before the test ride"}
for jid in order:
    talk = game.CLIENT_TALK.get(jid, {})
    job = next(j for j in game.ALL_JOBS if j["id"] == jid)
    where = EN(titles[jid])
    if job.get("intro"):
        add("Dialogues", f"{where} — job start", None, job["intro"])
    for kind, lines in talk.items():
        for ln in lines:
            add("Dialogues", f"{where} — {KIND.get(kind, kind)}", None, ln)
    for var in [job] + list(job.get("variants", [])):        # у части заданий шаги — в вариантах поломки
        for st in var.get("steps", []):
            if st.get("ghost"):
                add("Dialogues", f"{where} — step hint", None, st["ghost"])
        if var.get("thanks"):
            add("Dialogues", f"{where} — thanks at the end", None, var["thanks"])
for kind, lines in game.BARTY_TALK.items():
    for ln in lines:
        add("Dialogues", f"Barty's jokes — {kind}", None, ln)
for kind, lines in game.MARTIN_TALK.items():
    for ln in lines:
        add("Dialogues", f"Martin after a repair — {kind}", None, ln)
for ln in game.LEG_GAGS:
    add("Dialogues", "Leg gags after a repair", None, ln)
# 2. Сюжет: вступление
g = game.Game(headless=True)
for i, (title, text) in enumerate(g.intro_slides):
    add("Story", f"Intro slide {i + 1} — title", "", title)
    add("Story", f"Intro slide {i + 1} — text", "", text)
# прочие реплики «Имя: «…»» из словаря (финал, Гильдия, итоги)
for ru in game._TR:
    head = ru.split(":", 1)[0].strip() if ":" in ru[:30] else ""
    if head in SPEAKERS and "«" in ru and ru[:40] in SRC:      # только то, что ещё есть в игре
        add("Dialogues", "Other scenes (ending, Guild, results)", None, ru)
# 3. Тексты заданий: название, история, проверка
for jid in order:
    job = next(j for j in game.ALL_JOBS if j["id"] == jid)
    where = EN(titles[jid])
    add("Job texts", where, "title", job["title"])
    add("Job texts", where, "client", job["client"])
    add("Job texts", where, "problem (story)", job["symptom"])
    for var in [job] + list(job.get("variants", [])):
        if isinstance(var.get("test"), str):
            add("Job texts", where, "test ride", var["test"])

wb = Workbook()
info = wb.active
info.title = "How to edit"
help_lines = [
    "Wheels & Bones — dialogue editing sheet",
    "",
    "1. Edit ONLY the column \"New English\". Leave it empty if the line is fine.",
    "2. Keep the speaker at the start in the same form: Name: “text”. The game splits the name off at the first colon.",
    "3. Keep lines short: speech bubbles are small (about 2–3 lines on screen). 150 characters is a good maximum.",
    "4. Facts about wheelchairs (numbers, part names, safety) come from the manufacturers' manuals — if you change "
    "a fact, please add a note in \"Comment\" so we can double-check it.",
    "5. Do not change the hidden column \"key\" — it links the row to the game.",
    "6. Send the file back (or share the Google Sheet) — the changes go into the game with one command.",
]
for i, t in enumerate(help_lines, 1):
    info.cell(i, 1, t).font = Font(bold=(i == 1), size=14 if i == 1 else 11)
info.column_dimensions["A"].width = 130

head_fill = PatternFill("solid", fgColor="FFE9B0")
edit_fill = PatternFill("solid", fgColor="FFFFF4CC")
for name, data in rows.items():
    ws = wb.create_sheet(name)
    ws.append(["Where in the game", "Who / what", "English now", "New English", "Comment", "key"])
    for c in ws[1]:
        c.font = Font(bold=True)
        c.fill = head_fill
    for where, who, en, ru in data:
        ws.append([where, who, en, "", "", ru])
    for col, w in zip("ABCDEF", (34, 16, 70, 70, 30, 40)):
        ws.column_dimensions[col].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
        row[3].fill = edit_fill
    ws.column_dimensions["F"].hidden = True
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = ws.dimensions
os.makedirs(os.path.dirname(OUT), exist_ok=True)
wb.save(OUT)
print(OUT, {k: len(v) for k, v in rows.items()})
