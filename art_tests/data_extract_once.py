"""ОДНОРАЗОВЫЙ перенос содержания из game.py в assets/data/*.json (выполнен 10.11.2026, ветка feature/data-files).

Читает game.py ИСХОДНОЙ версии (где JOBS, TECH_JOBS, SEAT_* … ещё литералы в коде) через AST: вызовы S/D/T
превращаются в объекты с явно записанными полями, dict(...) — в объекты, кортежи — в списки; комментарии
«# source: …» (с их строками-продолжениями) становятся полем "source" того объекта, над которым стояли, прочие
комментарии — полем "comment". Сейчас game.py уже грузит данные из JSON — запускать повторно незачем:
  python art_tests/data_extract_once.py <старый game.py> <папка assets/data>
Оставлен для истории и проверки (git show 822767a:game.py > old.py).
"""
import ast
import io
import json
import os
import sys
import tokenize
from collections import defaultdict

PARAMS = {
    "S": ["instr", "tool", "part", "note", "ghost", "ghost_wrong", "wrongmsg", "mini", "alt", "alt_tools"],
    "D": ["text", "correct", "feedback"],
    "T": ["id", "instr", "tool", "part", "note", "ghost", "after", "safety", "spec", "failnote", "mini"],
}
TARGETS = ("JOBS", "FOLK_JOBS", "TECH_JOBS", "SEAT_CASES", "SEAT_LESSONS", "SEAT_QUIZ", "SEAT_MENTOR",
           "MANUAL", "MANUAL_NOTES", "TOOLS", "PARTS", "CREDITS")


class Conv:
    def __init__(self, src):
        self.src = src
        self.lines = src.splitlines()
        self.tree = ast.parse(src)
        self.comments = []          # (line, own_line, text)
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.COMMENT:
                ln = tok.start[0]
                own = self.lines[ln - 1].lstrip().startswith("#")
                self.comments.append((ln, own, tok.string[1:].strip()))
        self.objs = []              # (start, end, obj dict) — объекты, к которым цепляются комментарии
        self.tuples = defaultdict(int)
        self.used_comments = set()

    # --- значение узла AST -> JSON ------------------------------------------------------------- #
    def conv(self, n, path):
        if isinstance(n, ast.Constant):
            return n.value
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub) and isinstance(n.operand, ast.Constant):
            return -n.operand.value
        if isinstance(n, ast.List):
            return [self.conv(x, path + "[*]") for x in n.elts]
        if isinstance(n, ast.Tuple):
            self.tuples[path] += 1
            return [self.conv(x, path + "[*]") for x in n.elts]
        if isinstance(n, ast.Dict):
            out = {}
            for k, v in zip(n.keys, n.values):
                assert isinstance(k, ast.Constant) and isinstance(k.value, str), ast.dump(k)
                out[k.value] = self.conv(v, path + "." + k.value)
            return self.obj(n, out, path)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            fn = n.func.id
            if fn == "dict":
                assert not n.args
                out = {kw.arg: self.conv(kw.value, path + "." + kw.arg) for kw in n.keywords}
                return self.obj(n, out, path)
            if fn in PARAMS:
                names = PARAMS[fn]
                out = {}
                for i, a in enumerate(n.args):
                    out[names[i]] = self.conv(a, f"{path}<{fn}>.{names[i]}")
                for kw in n.keywords:
                    k = "id" if (fn == "T" and kw.arg == "sid") else kw.arg
                    assert k in names, (fn, k)
                    out[k] = self.conv(kw.value, f"{path}<{fn}>.{k}")
                # порядок полей — как в сигнатуре (для чтения); загрузчик всё равно зовёт S/D/T(**поля)
                out = {k: out[k] for k in names if k in out}
                return self.obj(n, out)
        raise ValueError(f"line {n.lineno}: не литерал: {ast.unparse(n)[:80]}")

    # словари-отображения (деталь -> улика, мерки тела, позы): комментарий внутри них относится к объекту выше
    MAPPINGS = ("inspect", "body", "start", "solution", "fixed", "pose")

    def obj(self, n, d, path=""):
        assert "source" not in d and "comment" not in d, n.lineno
        if path.rsplit(".", 1)[-1] not in self.MAPPINGS:
            self.objs.append((n.lineno, n.end_lineno, d))
        return d

    # --- комментарии -> поля source/comment ------------------------------------------------- #
    def attach(self, lo, hi):
        """Комментарии в строках lo..hi: блок своих строк подряд -> следующий объект; хвостовой -> объект строки."""
        coms = [c for c in self.comments if lo <= c[0] <= hi]
        i = 0
        while i < len(coms):
            ln, own, text = coms[i]
            if not own:
                self.add(self.innermost(ln), [text])
                self.used_comments.add(ln)
                i += 1
                continue
            block = [coms[i]]
            while i + 1 < len(coms) and coms[i + 1][1] and coms[i + 1][0] == block[-1][0] + 1:
                i += 1
                block.append(coms[i])
            i += 1
            nxt = block[-1][0] + 1
            while nxt <= len(self.lines) and (not self.lines[nxt - 1].strip()
                                              or self.lines[nxt - 1].lstrip().startswith("#")):
                nxt += 1
            starting = [o for o in self.objs if o[0] == nxt]
            target = max(starting, key=lambda o: o[1] - o[0])[2] if starting else self.innermost(nxt)
            self.add(target, [b[2] for b in block])
            for b in block:
                self.used_comments.add(b[0])

    def innermost(self, ln):
        inside = [o for o in self.objs if o[0] <= ln <= o[1]]
        if not inside:
            return None
        return min(inside, key=lambda o: o[1] - o[0])[2]

    @staticmethod
    def add(target, texts):
        assert target is not None, texts
        src, com = [], []
        for t in texts:
            if t.startswith("source:"):
                src.append(t[len("source:"):].strip())
            elif src:
                src[-1] += "\n" + t
            else:
                com.append(t)
        if com:
            target.setdefault("comment", []).extend(com)
        if src:
            target.setdefault("source", []).extend(src)


def first_keys(d):
    """comment и source — первыми (над объектом, как было в коде)."""
    if isinstance(d, dict):
        out = {}
        for k in ("comment", "source"):
            if k in d:
                out[k] = d[k]
        for k, v in d.items():
            if k not in out:
                out[k] = first_keys(v)
        return out
    if isinstance(d, list):
        return [first_keys(x) for x in d]
    return d


def main():
    src_path, out_dir = sys.argv[1], sys.argv[2]
    src = open(src_path, encoding="utf-8").read()
    c = Conv(src)
    raw = defaultdict(list)          # имя -> [(узел значения, строки)]
    for node in c.tree.body:
        name = None
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            name, val = node.targets[0].id, node.value
        elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
            name, val = node.target.id, node.value
        elif (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
              and isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "update"):
            name, val = node.value.func.value.id, node.value.args[0]
        if name in TARGETS and not isinstance(val, ast.Name):
            raw[name].append((val, node.lineno, node.end_lineno))
    vals = {}
    for name, parts in raw.items():
        for val, lo, hi in parts:
            v = c.conv(val, name)
            if isinstance(val, ast.Dict):          # словари-справочники: запись «ключ: значение»
                for k, vv in zip(val.keys, val.values):
                    if isinstance(v[k.value], (list, str)):
                        o = {"__entry__": v[k.value]}
                        c.objs.append((k.lineno, vv.end_lineno, o))
                        v[k.value] = o
            if isinstance(val, ast.List) and name == "CREDITS":
                for i, e in enumerate(val.elts):
                    o = {"__entry__": v[i]}
                    c.objs.append((e.lineno, e.end_lineno, o))
                    v[i] = o
            c.attach(lo, hi)
            if isinstance(v, list):
                vals.setdefault(name, []).extend(v)
            else:
                vals.setdefault(name, {}).update(v)
    for t, n in sorted(c.tuples.items()):
        print("tuple", t, n)
    n_src = sum(1 for ln, own, t in c.comments if "# source:" in c.lines[ln - 1] and ln in c.used_comments)
    print("source-комментариев перенесено:", n_src)
    if "--raw" in sys.argv:
        json.dump(vals, open(os.path.join(out_dir, "_raw.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return

    def write(rel, obj):
        p = os.path.join(out_dir, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(first_keys(obj), ensure_ascii=False, indent=2) + "\n")

    def entry(o, fields):
        """{"__entry__": [a, b, …]} -> {comment?, source?, поле_a: a, …}."""
        out = {k: o[k] for k in ("comment", "source") if k in o}
        out.update(zip(fields, o["__entry__"]))
        return out

    folk = [j["id"] for j in vals["FOLK_JOBS"]]
    write("jobs/index.json", {"jobs": [j["id"] for j in vals["JOBS"]], "folk": folk})
    for j in vals["JOBS"] + vals["FOLK_JOBS"]:
        write(f"jobs/{j['id']}.json", j)
    write("tech/index.json", {"jobs": [j["id"] for j in vals["TECH_JOBS"]]})
    for j in vals["TECH_JOBS"]:
        write(f"tech/{j['id']}.json", j)
    write("seating/lessons.json", vals["SEAT_LESSONS"])
    write("seating/cases.json", vals["SEAT_CASES"])
    write("seating/quiz.json", vals["SEAT_QUIZ"])
    write("seating/mentor.json", {k: v["__entry__"] for k, v in vals["SEAT_MENTOR"].items()})
    write("manual.json", {k: entry(v, ("title", "lines")) for k, v in vals["MANUAL"].items()})
    write("manual_notes.json", {job: {k: dict(zip(("manual", "page", "text"), v)) for k, v in notes.items()}
                                for job, notes in vals["MANUAL_NOTES"].items()})
    write("tools.json", {k: entry(v, ("name", "hint")) for k, v in vals["TOOLS"].items()})
    write("parts.json", {k: v["__entry__"] for k, v in vals["PARTS"].items()})
    write("credits.json", [entry(v, ("title", "lines")) for v in vals["CREDITS"]])


if __name__ == "__main__":
    main()
