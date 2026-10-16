#!/bin/bash
# Pixal3D GLB -> модель игры: геометрия и ЦВЕТ от Pixal3D, детали — разметкой (label + колёса).
# bash art_tests/pixal_batch.sh <ключ> <высота_мм> <manual|power|m3> <схема|-> [сиды...]
PY=/d/ComfyUI_CU130_TORCH2100/ComfyUI_CU130_TORCH2100/ComfyUI_windows_portable/python_embeded/python.exe
O=D:/ComfyUI_CU130_TORCH2100/ComfyUI_CU130_TORCH2100/ComfyUI_windows_portable/ComfyUI/output/wnb/pixal4
k=$1; h=$2; kind=$3; sch=$4; shift 4
for s in "$@"; do
  g=$O/${k}_s${s}_00001_.glb; [ -f "$g" ] || { echo "$k s$s: нет файла"; continue; }
  b=art_tests/mesh3d/px_${k}_s$s
  PYTHONIOENCODING=utf-8 $PY art_tests/mesh3d_from_glb.py "$g" $b.json $h >/dev/null 2>&1 || { echo "$k s$s: ошибка конвертации"; continue; }
  PYTHONIOENCODING=utf-8 python art_tests/mesh3d_label.py $b.json ${b}_l.json $kind >/dev/null 2>&1
  if [ "$kind" = manual ]; then
    python art_tests/mesh3d_wheels.py ${b}_l.json ${b}_l.json >/dev/null 2>&1
    PYTHONIOENCODING=utf-8 python art_tests/mesh3d_scheme.py ${b}_l.json ${b}_l.json $sch >/dev/null 2>&1
  fi
  python - $b <<'PYEOF'
import json, sys
b = sys.argv[1]
a = json.load(open(b + ".json")); d = json.load(open(b + "_l.json"))
keep = {"joystick", "boot", "controller", "valve"}          # эти акценты оставляем размеченным цветом
for fa, fd in zip(a["faces"], d["faces"]):
    if d["parts"][fd[3]] not in keep:
        fd[4:7] = fa[4:7]
d["verts"] = [[round(c) for c in v] for v in d["verts"]]
d["cull"] = True                      # сетка Pixal3D замкнутая: задние грани можно не рисовать
json.dump(d, open(b + "_l.json", "w"), separators=(",", ":"))
print(b.split("/")[-1], "граней", len(d["faces"]))
PYEOF
done
