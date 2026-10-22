# Meshy 3D модели

Оригинальные модели колясок, сделанные владельцем в Meshy (Multi-image to 3D, через fal.ai) по референсам
из `art_tests/meshy_ref/`. Это исходники: их не правим и не облегчаем.

| Файл | Коляска | Задание в игре | Дата |
|---|---|---|---|
| `permobil_m3_corpus.glb` | Permobil M3 Corpus | «Джойстик» (чародейка Мора), `chair_m3.png` | 2026-10-22 |
| `quantum_edge_4.glb` | Quantum Edge 4 | «Лифт сиденья» (гоблин Зикс), `chair_edge4.png` | 2026-10-22 |
| `permobil_f5_corpus.glb` | Permobil F5 Corpus | «Зарядка в холоде» (барсучиха Матильда), `chair_f5.png` | 2026-10-22 |
| `drive_trident_hd.glb` | Drive Trident HD | «Свободный ход» (`freewheel`), `chair_trident.png` | 2026-10-22 |
| `quickie_pulse_6.glb` | Quickie Pulse 6 | Гильдия, «Pulse 6» (`t_pulse6`), `chair_pulse6.png` | 2026-10-22 |
| `pride_jazzy_614.glb` | Pride Jazzy (EVO) 614 | Змей Горыныч (`gorynych_jazzy`), `chair_gorynych.png` | 2026-10-22 |
| `whill_model_c2.glb` | WHILL Model C2/Ci | «Код ошибки» (`whill_code`), `chair_whillc2.png` | 2026-10-22 |
| `ki_mobility_focus_cr.glb` | Ki Mobility Focus CR | бабушка Агата (`focuscr_cable`), `chair_focuscr.png`; в игре наклон 20° | 2026-10-22 |
| `magic_mobility_x8.glb` | Magic Mobility Extreme X8 | Леший (`leshy_x8`), `chair_leshy.png` (корпус перекрашен в красный) | 2026-10-22 |

Как модель попадает в игру:
1. `art_tests/tripo_convert.py meshy_models/<файл>.glb art_tests/gen3d/<ключ> height=<мм> --keep-big=0.002`
   — облегчённая копия (только для деталей и кружков задания), затем `art_tests/tripo_label.py <ключ> --dir art_tests/gen3d`.
2. `art_tests/glb_xform.py meshy_models/<файл>.glb <ключ> height=<мм> --keep-big=0.002` — матрица «модель → оси игры».
3. `art_tests/blender_frames.py chair_<…>.png` — кадры поворота в Blender снимаются с ЭТОГО файла (полная сетка,
   родная текстура; цвет подгоняется под игру), затем `art_tests/art_from_turntable.py <job_id>`.

Файлы `.glb` не в git (крупные) — храните копию.
