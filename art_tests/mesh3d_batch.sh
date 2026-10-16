#!/bin/bash
# Обработка сгенерированных Hunyuan3D моделей колясок: post -> label -> wheels (ручные)
# использование: bash art_tests/mesh3d_batch.sh <ключ> <высота_мм> <manual|power> [сиды...]
PY=/d/ComfyUI_CU130_TORCH2100/ComfyUI_CU130_TORCH2100/ComfyUI_windows_portable/python_embeded/python.exe
O=D:/ComfyUI_CU130_TORCH2100/ComfyUI_CU130_TORCH2100/ComfyUI_windows_portable/ComfyUI/output/wnb/real3d
IN="${WNB_REAL_DIR:-./real}"   # папка с исходными рендерами (переменная WNB_REAL_DIR)
k=$1; h=$2; kind=$3; shift 3
for s in "$@"; do
  g=$O/${k}_s${s}_00001_.glb; [ -f "$g" ] || continue
  out=art_tests/mesh3d/r_${k}_s$s
  iou=$(PYTHONIOENCODING=utf-8 $PY art_tests/mesh3d_post.py "$g" "$IN/in3d_$k.png" $out.json $h 2>&1 | grep -o "IoU [0-9.]*")
  PYTHONIOENCODING=utf-8 python art_tests/mesh3d_label.py $out.json ${out}_l.json $kind >/dev/null 2>&1
  if [ "$kind" = manual ]; then python art_tests/mesh3d_wheels.py ${out}_l.json ${out}_l.json >/dev/null 2>&1; fi
  echo "$k s$s $iou"
done
