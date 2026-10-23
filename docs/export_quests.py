"""Выгрузка всех квестов в читаемый вид (для проверки людьми): python docs/export_quests.py
Пишет docs/QUESTS.md (English) и docs/QUESTS_ru.md (русский). Источник — данные в game.py; файлы не править вручную."""
import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import pygame
pygame.init()
pygame.display.set_mode((8, 8))
import game

L = {
    "en": dict(title="Wheels & Bones — all quests", intro=(
        "Generated from `game.py` by `python docs/export_quests.py` — do not edit by hand.\n\n"
        "Found a mistake? Note the quest number and step, what is wrong and how it should be "
        "(or use the ⚑ flag in the game — it attaches a screenshot)."),
        client="Client", chair="Wheelchair", symptom="Symptom", clues="Inspection clues (what the player sees)",
        diag="Diagnosis options", steps="Repair steps", tool="Tool", part="Part", also="also accepted",
        hint="Hint", note="After the step", wrong="If wrong", test="Test", fact="What you learn",
        thanks="Client says", variant="Variant", guild="Wheelwrights' Guild (technician level)",
        order="Order: free; must come after", safety="SAFETY step", spec="Value from the manual",
        mini="Mini-game", base="Workshop jobs", correct="correct"),
    "ru": dict(title="Колёса и Кости — все квесты", intro=(
        "Собрано из `game.py` командой `python docs/export_quests.py` — вручную не править.\n\n"
        "Нашли ошибку? Укажите номер квеста и шага, что не так и как правильно "
        "(или флажок ⚑ в игре — он приложит снимок экрана)."),
        client="Клиент", chair="Коляска", symptom="Симптом", clues="Улики при осмотре (что видит игрок)",
        diag="Варианты диагноза", steps="Шаги ремонта", tool="Инструмент", part="Деталь", also="также принимается",
        hint="Подсказка", note="После шага", wrong="При ошибке", test="Проверка", fact="Что ты узнал",
        thanks="Клиент говорит", variant="Вариант", guild="Гильдия Колёсников (уровень техника)",
        order="Порядок свободный; только после", safety="шаг ТЕХНИКИ БЕЗОПАСНОСТИ", spec="Значение из мануала",
        mini="Мини-игра", base="Задания мастерской", correct="верно"),
}


def tool(t):
    return game.tr(game.TOOLS.get(t, (t,))[0])


def part(p):
    return game.tr(game.PARTS.get(p, p))


def job_block(job, n, T, out, label=""):
    tr = game.tr
    out.append(f"### {n}. {tr(job['title'])}{label}")
    out.append(f"- **{T['client']}:** {tr(job['client'])}  ")
    if job.get("chair_name"):
        out.append(f"- **{T['chair']}:** {tr(job['chair_name'])}  ")
    out.append(f"- **{T['symptom']}:** {tr(job['symptom'])}\n")
    if job.get("inspect"):
        out.append(f"**{T['clues']}**\n")
        for p, clue in job["inspect"].items():
            out.append(f"- *{part(p)}* — {tr(clue)}")
        out.append("")
    if job.get("diagnosis"):
        out.append(f"**{T['diag']}**\n")
        for d in job["diagnosis"]:
            mark = f"✅ ({T['correct']})" if d["correct"] else "❌"
            fb = f" — {tr(d['feedback'])}" if d.get("feedback") else ""
            out.append(f"- {mark} {tr(d['text'])}{fb}")
        out.append("")
    out.append(f"**{T['steps']}**\n")
    tech = job.get("track") == "tech"
    for i, st in enumerate(job["steps"], 1):
        line = f"{i}. {tr(st['instr'])}  \n   *{T['tool']}:* {tool(st['tool'])}"
        if not tech:
            line += f" → *{T['part']}:* {part(st['part'])}"
            if st.get("alt"):
                line += f" ({T['also']}: {', '.join(part(a) for a in sorted(st['alt']))})"   # alt — set: порядок фиксируем
        else:
            if st.get("after"):
                names = [str(next(k for k, s2 in enumerate(job["steps"], 1) if s2["id"] == a)) for a in st["after"]]
                line += f"  \n   *{T['order']}:* {', '.join(names)}"
            if st.get("safety"):
                line += f"  \n   **{T['safety']}**"
            if st.get("spec"):
                sp = st["spec"]
                opts = "; ".join(("✅ " if o[1] else "❌ ") + tr(o[0]) for o in sp["options"])
                line += f"  \n   *{T['spec']}:* {tr(sp['prompt'])} — {opts}"
        if st.get("mini"):
            line += f"  \n   *{T['mini']}:* {st['mini']['kind']}"
        if st.get("ghost"):
            line += f"  \n   *{T['hint']}:* {tr(st['ghost'])}"
        if st.get("note"):
            line += f"  \n   *{T['note']}:* {tr(st['note'])}"
        if st.get("wrongmsg"):
            line += f"  \n   *{T['wrong']}:* {tr(st['wrongmsg'])}"
        out.append(line)
    out.append("")
    for k, name in (("test", T["test"]), ("fact", T["fact"]), ("thanks", T["thanks"])):
        if job.get(k):
            out.append(f"**{name}:** {tr(job[k])}  ")
    out.append("\n---\n")


def export(lang):
    game.set_lang(lang)
    T = L[lang]
    out = [f"# {T['title']}\n", T["intro"] + "\n", f"## {T['base']}\n"]
    for n, base in enumerate(game.JOBS, 1):
        variants = base.get("variants") or [None]
        for vi in range(len(variants)):
            job = game.resolve_job(base, vi if base.get("variants") else None)
            label = f" — {T['variant']} {vi + 1}/{len(variants)}" if len(variants) > 1 else ""
            job_block(job, n, T, out, label)
    out.append(f"## {T['guild']}\n")
    for n, job in enumerate(game.TECH_JOBS, 1):
        job_block(job, f"G{n}", T, out)
    name = "QUESTS.md" if lang == "en" else "QUESTS_ru.md"
    with open(os.path.join(HERE, name), "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print("docs/" + name)


if __name__ == "__main__":
    export("en")
    export("ru")
