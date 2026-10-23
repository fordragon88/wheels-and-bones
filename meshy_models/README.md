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
| `vermeiren_d100.glb` | Vermeiren D100 | Баба Яга (`yaga_d100`), `chair_yaga.png` | 2026-10-23 |
| `panthera_x3.glb` | Panthera X3 | русалка Ольга (`olga_x3`), `chair_rusalka.png` | 2026-10-23 |
| `quickie_nitrum.glb` | Quickie Nitrum (без e-motion — ступицы дорисовываем) | мумия Сенеб (`ra_emotion`), `chair_ra.png` | 2026-10-23 |
| `invacare_9000.glb` | Invacare 9000 | Мартин (`flat`, `toe`) и Бомм (`cushion`, ×1.07), `chair_basic.png`, `chair_troll.png` | 2026-10-23 |
| `progeo_exelle_junior.glb` | Progeo Exelle Junior (рама в кадрах — розовая; антиопрокидыватель клонирован на обе стороны) | фея Тилли (`spokes`), `chair_fairy.png` | 2026-10-23 |
| `tilite_aero_z.glb` | TiLite Aero Z (антиопрокидыватели добавлены) | кицунэ Юки (`aeroz_lock`), `chair_aeroz.png` | 2026-10-23 |
| `etac_cross_6.glb` | Etac Cross 6 | дриада Ивушка (`cross6_back`), `chair_cross6.png` | 2026-10-23 |
| `progeo_noir_2.glb` | Progeo Noir 2.0 | орк Гра (`bearing`), `chair_orc.png` | 2026-10-23 |
| `progeo_ego.glb` | Progeo Ego | эльфийка Аэлин (`caster`), `chair_elf.png` | 2026-10-23 |
| `quickie_2.glb` | Quickie 2 | оборотень Вольф (`brake`, бывший гном Дургин), `chair_dwarf.png` | 2026-10-23 |
| `quantum_q6_edge_classic.glb` | Quantum Q6 Edge (классическая, жёлтая); крепление пульта дорисовано (tubes), висящие провода, ремешок и зажим убраны (move delete, петля жгута — `seed`) | Гильдия (`t_q6brake`), `chair_q6edge.png` | 2026-10-23 |
| `quantum_q6_edge.glb` | Quantum Q6 Edge 2.0 — пробная (кривые пульт и подножки, правка — move rot в blender_frames); владелец перегенерирует по набору 4b_Quantum_Q6_Edge_classic; в игру не ставилась | Гильдия (`t_q6brake`) | 2026-10-23 |

Как модель попадает в игру:
1. `art_tests/tripo_convert.py meshy_models/<файл>.glb art_tests/gen3d/<ключ> height=<мм> --keep-big=0.002`
   — облегчённая копия (только для деталей и кружков задания), затем `art_tests/tripo_label.py <ключ> --dir art_tests/gen3d`.
2. `art_tests/glb_xform.py meshy_models/<файл>.glb <ключ> height=<мм> --keep-big=0.002` — матрица «модель → оси игры».
3. `art_tests/blender_frames.py chair_<…>.png` — кадры поворота в Blender снимаются с ЭТОГО файла (полная сетка,
   родная текстура; цвет подгоняется под игру), затем `art_tests/art_from_turntable.py <job_id>`.

**Исправленные копии `*_fixed.glb`** (`python art_tests/glb_fixed.py`): у моделей Meshy тонкие спицы рвутся на куски —
в копии они вырезаны и поставлены ровные (`blender_render.fix_spokes`), у Nitrum добавлены ступицы Alber e-motion
(`add_hub`), у Q6 Edge убраны висящие провода и ремешок. Копия уже в осях игры: метры, пол на 0, вперёд +X, правая сторона +Z (исходник не меняется). Есть для
`vermeiren_d100`, `panthera_x3`, `quickie_nitrum`, `progeo_exelle_junior`, `tilite_aero_z`, `quantum_q6_edge_classic` — для других появятся, когда им зададут `spokes`/`hubs` в
`art_tests/blender_frames.py` (словарь `GLB`).

Файлы `.glb` не в git (крупные) — храните копию.
