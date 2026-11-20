# -*- coding: utf-8 -*-
"""Эталон порядка обхода с клавиатуры: какие пункты и в каком порядке game.py даёт стрелкам и Tab (a11y_items) в
каждом состоянии экрана — тех же состояниях и под теми же именами, что снимки tools/ref_shots.py (ref_shots ставит
состояния, здесь вместо снимка записывается список). На RU и EN (каждый язык — свой процесс: game.py держит язык в
модуле). Пишет godot/content/kb_order_ref.json:
  {"ru": {"<состояние>": [[группа, подпись, что делает нажатие], …]}, "en": {…}, "rules": {…}}
«что делает нажатие»: adj — ползунок (← → меняют значение, Enter — повторить подпись), act:<что> — своё действие
пункта, click — клик в центр нарисованной кнопки. Проверка в Godot — tests/selftest_runner.gd `--only kborder`.
  python godot/tools/kb_order_ref.py
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DST = os.path.join(ROOT, "godot", "content", "kb_order_ref.json")
REF_SHOTS = os.path.join(ROOT, "godot", "tools", "ref_shots.py")


def _does(it):
    if it.get("adj") and not it.get("act"):
        return "adj"
    a = it.get("act")
    if a is not None:
        n = getattr(a, "__name__", "")
        if n and n != "<lambda>":
            return "act:" + n
        k = it["key"]
        return "act:" + (str(k[0]) if isinstance(k, tuple) else str(k))
    return "click"


def one(lang):
    """Пройти состояния ref_shots.py на языке lang и вернуть {состояние: пункты}."""
    out = {}
    src = open(REF_SHOTS, encoding="utf-8").read()
    ns = {"__name__": "__kb_order__", "__file__": REF_SHOTS}

    def hook(game):
        import pygame
        if lang == "en":
            orig = game.set_lang
            game.set_lang = lambda code: orig("en")
        game.A11Y["voices"] = False

        def save(surf, path):
            name = os.path.splitext(os.path.basename(path))[0]
            g = ns["g"]
            out[name] = [[it["group"], game.speech_clean(it["label"]), _does(it)] for it in g.a11y_items()]
            print(lang, name, len(out[name]), flush=True)
        pygame.image.save = save

    ns["__kb_hook"] = hook
    src = src.replace("\nimport game\n", "\nimport game\n__kb_hook(game)\n", 1)
    src = src.replace('OUT = os.path.join(ROOT, "godot", "tests", "ref")', 'OUT = ""', 1)
    sys.argv = [REF_SHOTS]
    exec(compile(src, REF_SHOTS, "exec"), ns)
    return out


RULES = {
    "arrows": "↑ ← — предыдущий пункт, ↓ → — следующий, по одному списку всех групп; с краёв — заворот (последний ↔ "
              "первый); без фокуса ↓/→ — первый пункт, ↑/← — последний. У ползунка (adj) ← → меняют значение, ↑ ↓ — "
              "соседние пункты.",
    "tab": "Tab — первый пункт следующей группы (группы — в порядке первого появления в списке), Shift+Tab — первый "
           "пункт предыдущей; заворот; без фокуса Tab — первая группа, Shift+Tab — последняя.",
    "enter": "Enter/Пробел — нажать пункт (act или клик в центр; у ползунка — повторить подпись). Без фокуса: на титуле, "
             "во вступлении и на празднике — первый пункт («начать»/«далее»/«гараж»); если пункт один — он; иначе "
             "фокус встаёт на первый пункт. В поле ввода (замечание, код) Пробел — буква, Enter без фокуса — отправить.",
    "esc": "Esc — назад (окно → закрыть; экран — его «назад»).",
    "credits": "Титры: ↑ ↓ листают текст (в список не идут), ← → и Tab — по пунктам.",
    "v3d": "3D-осмотр: всё, кроме Enter, — самому осмотру.",
    "modal": "Окно поверх (справка, замечание, коды, настройки, мини-игра, мануал, спека) — только его пункты.",
    "scan": "Одна кнопка — тот же список: выделение идёт по нему по очереди (scan_tick: следующий с заворотом), у "
            "ползунка — «меньше / больше / готово».",
}


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--one":
        lang, dst = sys.argv[2], sys.argv[3]
        res = one(lang)
        json.dump(res, open(dst, "w", encoding="utf-8"), ensure_ascii=False)
        return
    out = {}
    tmp = DST + ".tmp_{}.json"
    for lang in ("ru", "en"):
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        subprocess.run([sys.executable, os.path.abspath(__file__), "--one", lang, tmp.format(lang)], check=True,
                       cwd=ROOT, env=env, stdout=subprocess.DEVNULL)
        out[lang] = json.load(open(tmp.format(lang), encoding="utf-8"))
        os.remove(tmp.format(lang))
    out["rules"] = RULES
    with open(DST, "w", encoding="utf-8") as f:
        f.write("{\n")
        keys = ["ru", "en"]
        for i, lang in enumerate(keys):
            f.write(f' "{lang}": {{\n')
            names = list(out[lang])
            for j, n in enumerate(names):
                f.write(f'  {json.dumps(n)}: [\n')
                rows = out[lang][n]
                for k, r in enumerate(rows):
                    f.write("   " + json.dumps(r, ensure_ascii=False) + ("," if k < len(rows) - 1 else "") + "\n")
                f.write("  ]" + ("," if j < len(names) - 1 else "") + "\n")
            f.write(" },\n")
        f.write(' "rules": ' + json.dumps(RULES, ensure_ascii=False, indent=1).replace("\n", "\n ") + "\n}\n")
    n = sum(len(out[l]) for l in keys)
    m = sum(len(v) for l in keys for v in out[l].values())
    print(f"kb_order_ref.json: {n} состояний, {m} пунктов")


if __name__ == "__main__":
    main()
