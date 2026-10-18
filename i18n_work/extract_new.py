"""Выгрузка непереведённых русских строк из game.py в chunkN.json (формат как chunk1-4):
python i18n_work/extract_new.py chunk5.json  — строки-литералы и шаблоны f-строк ({0}, {1}…)."""
import ast, json, os, re, sys, glob
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "game.py")
CYR = re.compile("[А-Яа-яЁё]")
src = open(SRC, encoding="utf-8").read()
lines = src.splitlines()
have = {}
for f in glob.glob(os.path.join(HERE, "en*.json")):
    have.update(json.load(open(f, encoding="utf-8")))
known = {c["ru"] for f in glob.glob(os.path.join(HERE, "chunk*.json")) for c in json.load(open(f, encoding="utf-8"))}
out, seen = [], set()


def add(ru, node, fmt):
    if ru.lstrip().startswith(("#version", "(function(")) or ru.startswith(("[А-", "(?")):   # шейдеры, JS, регулярки — не текст игры
        return
    if ru in ("{0} из {1}", "на"):              # язык выбирается в коде (_of, speech_clean) — не в словаре
        return
    if not CYR.search(ru) or ru in have or ru in seen:
        return
    seen.add(ru)
    out.append(dict(ru=ru, line=node.lineno, fmt=fmt, context=lines[node.lineno - 1].strip()[:200]))


SKIP_FN = {"run_selftest", "print_assets", "main", "_selftest_play"}


class V(ast.NodeVisitor):
    def visit_FunctionDef(self, node):
        if node.name in SKIP_FN:
            return                               # консольные проверки — не экран игры
        self.generic_visit(node)

    def visit_Expr(self, node):
        if isinstance(node.value, ast.Constant):
            return                               # докстринги
        self.generic_visit(node)

    def visit_JoinedStr(self, node):
        parts, i = [], 0
        for v in node.values:
            if isinstance(v, ast.Constant):
                parts.append(str(v.value).replace("{", "{{").replace("}", "}}"))
            else:
                parts.append("{%d}" % i); i += 1
        add("".join(parts), node, True)          # вложенные константы не обходим — это части шаблона

    def visit_Constant(self, node):
        if isinstance(node.value, str):
            add(node.value, node, False)


V().visit(ast.parse(src))
dst = os.path.join(HERE, sys.argv[1] if len(sys.argv) > 1 else "chunk5.json")
json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(out), "строк ->", dst, "| уже в старых chunk:", sum(1 for o in out if o["ru"] in known))
