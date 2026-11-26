"""Автоматические проверки содержания (assets/data) — без игры, без сети, секунды (внешняя проверка 26.11, S3).

    python art_tests/data_lint.py        # «DATA LINT OK — …» или список нарушений и код выхода 1
    python art_tests/data_lint.py <папка>   # проверить другую копию проекта (например, выгрузку старого коммита)

Что проверяется:
1. Про-задания Гильдии (assets/data/tech/*.json), граф шагов `after`:
   - ссылки только на существующие шаги, без петель;
   - нет «висячих» шагов: у задания ровно один последний шаг (на него сходятся все цепочки — итоговая проверка/
     зарядка); шаг, после которого ничего не обязано идти, можно сделать последним — так было с проверкой заряда
     в t_q6brake (E41.1);
   - отключение питания (шаг техники безопасности с деталью «пульт» — `safety` + `part: controller`) — предок
     каждой работы с силовой частью (POWER_PARTS: батарея, жгут, автомат, мотор, тормоз мотора, щётки,
     предохранитель, актуатор, кабель сиденья), кроме замеров мультиметром (MEASURE_TOOLS). Правило — из мануалов
     Edge 4 p25 («1. Turn off the power to the controller»), Q6 Edge 2.0 OM p27, F5 §4.8 и уже принятых заданий
     lift / f5_charge (сначала пульт, потом автомат). На исходных данных ловит t_battery: p_breaker без p_off (E41.2).
2. Обычные задания: все `alt`-детали шагов есть в `parts` того же варианта (иначе по ним нельзя кликнуть — E43).
3. Мини-игры: зелёная зона насоса не уже PUMP_MIN_ZONE (насос прибавляет 6–12 за нажатие — AGENTS.md, §4),
   зазора — не уже GAP_MIN_ZONE (ползунок ходит шагом 1); зона внутри шкалы.
4. Числа с единицами (psi, кПа, бар, Н·м, °, мм, см, дюймы ″/") в русской строке данных и в её переводе
   (assets/lang_en.json) совпадают (0,5 = 0.5; «7–8 psi» — оба числа). Исключения — UNIT_EXCEPTIONS (начало
   русской строки → почему).
"""
import json
import os
import re
import sys
from collections import Counter

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "i18n_work"))
import data_strings as _ds  # noqa: E402
if len(sys.argv) > 1:                                # другая копия проекта (выгрузка коммита до правок)
    ROOT = os.path.abspath(sys.argv[1])
    _ds.ROOT, _ds.DATA_DIR = ROOT, os.path.join(ROOT, "assets", "data")
DATA = os.path.join(ROOT, "assets", "data")
data_strings = _ds.data_strings

POWER_PARTS = {"battery", "wiring", "breaker", "motor", "mag_brake", "brushes", "fuse", "actuator", "seat_cable"}
MEASURE_TOOLS = {"multimeter"}
PUMP_MIN_ZONE = 12
GAP_MIN_ZONE = 1
UNIT_EXCEPTIONS = {
    # "начало русской строки": "почему в переводе другие числа",
    "Низкое напряжение — 1 деление": "bar — деление индикатора заряда VR2, не единица давления",
}


def load(rel):
    with open(os.path.join(DATA, rel), encoding="utf-8") as f:
        return json.load(f)


def lint_tech(path, errs):
    d = load(path)
    tid = d["id"]
    steps = d.get("steps", [])
    ids = [s["id"] for s in steps]
    by = {s["id"]: s for s in steps}
    for s in steps:
        for a in s.get("after") or []:
            if a not in by:
                errs.append(f"{tid}: шаг {s['id']}: after ссылается на несуществующий «{a}»")
    succ = {i: set() for i in ids}
    for s in steps:
        for a in s.get("after") or []:
            if a in succ:
                succ[a].add(s["id"])

    anc_cache = {}

    def ancestors(i, stack=()):
        if i in anc_cache:
            return anc_cache[i]
        if i in stack:
            errs.append(f"{tid}: петля в after: {' → '.join(stack + (i,))}")
            return set()
        out = set()
        for a in by[i].get("after") or []:
            if a in by:
                out |= {a} | ancestors(a, stack + (i,))
        anc_cache[i] = out
        return out

    for i in ids:
        ancestors(i)
    sinks = [i for i in ids if not succ[i]]
    if len(sinks) != 1:
        errs.append(f"{tid}: последних шагов {len(sinks)} ({', '.join(sinks)}) — шаг, после которого ничего не обязано "
                    f"идти, можно сделать последним; нужен один итоговый шаг")
    offs = [s["id"] for s in steps if s.get("safety") and s.get("part") == "controller"]
    for off in offs:
        for s in steps:
            if (s["part"] in POWER_PARTS and s["tool"] not in MEASURE_TOOLS and s["id"] != off
                    and off not in ancestors(s["id"])):
                errs.append(f"{tid}: шаг {s['id']} ({s['part']}, «{s['instr']}») можно сделать до отключения питания "
                            f"{off} — добавь {off} в его after (или в after его предка)")
    return len(steps)


def lint_jobs(errs):
    n = 0
    idx = load("jobs/index.json")
    for jid in list(idx.get("jobs", [])) + list(idx.get("folk", [])):
        d = load(f"jobs/{jid}.json")
        for vi, v in enumerate(d.get("variants") or [d]):
            parts = set(v.get("parts") or d.get("parts") or [])
            where = jid + (f" (вариант {vi + 1})" if d.get("variants") else "")
            for si, s in enumerate(v.get("steps") or []):
                n += 1
                for a in s.get("alt") or []:
                    if a not in parts:
                        errs.append(f"{where}: шаг {si + 1}: alt-деталь «{a}» не в parts — по ней не кликнуть")
                lint_mini(s.get("mini"), f"{where}: шаг {si + 1}", errs)
    for f in sorted(os.listdir(os.path.join(DATA, "tech"))):
        if f.endswith(".json") and f != "index.json":
            for s in load(f"tech/{f}").get("steps", []):
                lint_mini(s.get("mini"), f"tech/{f}: {s['id']}", errs)
    return n


def lint_mini(m, where, errs):
    if not m or m.get("kind") not in ("pump", "gap"):
        return
    lo, hi = m["lo"], m["hi"]
    mn, mx = m.get("mn", 0), m["mx"]
    if not (mn <= lo < hi <= mx):
        errs.append(f"{where}: зелёная зона {lo}–{hi} вне шкалы {mn}–{mx}")
    need = PUMP_MIN_ZONE if m["kind"] == "pump" else GAP_MIN_ZONE
    if hi - lo < need:
        errs.append(f"{where}: зелёная зона {m['kind']} {lo}–{hi} {m.get('unit', '')} уже {need}")


NUM = r"(\d+(?:[.,]\d+)?(?:/\d+)?)"
RU_UNITS = [("psi", r"psi"), ("kPa", r"кПа"), ("bar", r"бар"), ("Nm", r"Н[·⋅.]?м"), ("deg", r"°"),
            ("mm", r"мм"), ("cm", r"см"), ("in", r"[″\"]|дюйм\w*")]
EN_UNITS = [("psi", r"psi"), ("kPa", r"kPa"), ("bar", r"bar"), ("Nm", r"N[·⋅.]?m|newton[- ]met\w+"),
            ("deg", r"°|degrees?"), ("mm", r"mm|millimet\w+"), ("cm", r"cm|centimet\w+"),
            ("in", r"[″\"]|inch\w*|in\.")]


def units(text, table):
    out = Counter()
    for key, pat in table:
        rx = re.compile(NUM + r"(?:\s*[–—-]\s*" + NUM + r")?\s?(?:" + pat + r")(?![A-Za-zА-Яа-яЁё])")
        for m in rx.finditer(text):
            for g in m.groups():
                if g:
                    out[(g.replace(",", "."), key)] += 1
    return out


def lint_units(errs):
    with open(os.path.join(ROOT, "assets", "lang_en.json"), encoding="utf-8") as f:
        lang = json.load(f)
    seen, n = set(), 0
    for text, where in data_strings():
        if text in seen or text not in lang:
            continue
        seen.add(text)
        ru, en = units(text, RU_UNITS), units(lang[text], EN_UNITS)
        if not ru and not en:
            continue
        n += 1
        if ru != en and not any(text.startswith(k) for k in UNIT_EXCEPTIONS):
            miss = ", ".join(f"{v} {u}" for (v, u), c in (ru - en).items())
            extra = ", ".join(f"{v} {u}" for (v, u), c in (en - ru).items())
            errs.append(f"{where}: числа с единицами не совпадают с переводом (в RU нет в EN: {miss or '—'}; "
                        f"в EN лишнее: {extra or '—'})\n      RU: {text[:150]}\n      EN: {lang[text][:150]}")
    return n


def main():
    errs = []
    nt = 0
    for f in sorted(os.listdir(os.path.join(DATA, "tech"))):
        if f.endswith(".json") and f != "index.json":
            nt += lint_tech(f"tech/{f}", errs)
    nj = lint_jobs(errs)
    nu = lint_units(errs)
    if errs:
        print(f"DATA LINT FAIL — нарушений: {len(errs)}")
        for e in errs:
            print("  -", e)
        sys.exit(1)
    print(f"DATA LINT OK — шагов Гильдии {nt} (граф after, питание), шагов мастерской {nj} (alt, мини-игры), "
          f"строк с числами и единицами {nu} (RU = EN)")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
