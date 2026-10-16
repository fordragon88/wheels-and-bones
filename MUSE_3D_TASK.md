# TASK FOR THE CODING AGENT: improve the 3D wheelchair models

**Project:** «Колёса и Кости» / *Wheels & Bones* — an educational wheelchair-repair game (Python 3.10 + pygame + numpy).
Full project knowledge is in `AGENTS.md` (Russian). This file is the **only thing you need for this task** — read it fully.

## 1. Goal
Make the 17 procedural 3D wheelchair models **look like the real chairs in the game art** and look **higher quality**
(cleaner shapes, correct proportions, correct details), without breaking the game.

Each model must clearly read as its real product (TiLite Aero Z, Permobil F5, WHILL C2, …) when compared with
its 2D art `assets/chair_<key>.png`. The art was redrawn from real manufacturer photos — **the art is the reference**.
Extra reference pictures from the manuals: `art_tests/ref_new/<key>_ref*.png`, `whillc2_photo.png`.

Current state (art on the left, current 3D on the right, same view):
`art_tests/_art_vs_3d_A.png` (9 chairs) and `art_tests/_art_vs_3d_B.png` (8 chairs).
Per-chair silhouette overlays: `art_tests/fit/<key>.png` (art | 3D | overlay: green = match, red = only in art, blue = only in 3D).

## 2. Files you may edit
| File | Models |
|---|---|
| `art_tests/build_9_chairs.py` | basic, troll, elf, dwarf, fairy, orc, edge4, m3, trident (`BUILDERS` dict at the end) |
| `art_tests/build_new_chairs.py` | aeroz, cross6, iris, focuscr, whillc2, f5, pulse6, q6edge (imports helpers from build_9_chairs.py) |

Output files (generated, do not hand-edit): `assets/models/chair_<key>_ai.json` and `chair_<key>_ai_lod.json`.

**Do NOT edit:** `game.py`, any `assets/*.png`, `assets/lang_en.json`, music. Do not rename keys or files.
`build_new_chairs.py` imports helpers from `build_9_chairs.py`: **never change the signature or default output of an
existing helper** — add optional keyword arguments (defaults = old behaviour) or write new helpers instead.

## 3. Model format and conventions (must keep)
- Builder class `TriMeshBuilder`; save format JSON: `{"verts": [[x,y,z],...], "faces": [[a,b,c, part_index, r,g,b],...],
  "parts": ["frame", ...], "cull": false, "source": "Custom3D"}` — use the existing save code (`to_dict()` + the `__main__` block).
- **Units: millimetres. Axes: x = forward (front of the chair, footrests), y = up (floor at y = 0), z = sideways,
  symmetric about z = 0; the right side (joystick side on power chairs) is +z.** Real sizes: manual chairs ~800–950 mm tall,
  power chairs ~1000–1200 mm.
- Colours: flat RGB per face; the game adds lighting. Sample colours from the art.
- **Face budget:** full model ≤ ~13 000 faces; the LOD copy (`lod=0.65`) ≤ ~9 500. The game renders in software with pygame,
  more faces = lower FPS.
- **Part labels are click targets in the game** (players click a part to inspect it). Every part listed below must exist
  on that model as labelled faces **located where that component really is**. Unlabelled structure goes to `"frame"`.

| key | real chair | required part labels | IoU now |
|---|---|---|---|
| basic | Invacare 9000 (folding) | bolts, brake, rear_wheel, rim, spokes, tire, tube, valve | 0.70 |
| troll | Invacare 9000 XDT (heavy-duty folding) | cushion, frame, seat, valve | 0.70 |
| elf | Progeo Ego (rigid active, lime) | bearing, bolts, brake, caster, caster_stem, rear_wheel, rim, spokes, tire | 0.71 |
| dwarf | Progeo Tekna Advance (copper) | bolts, brake, frame, rear_wheel, tire | 0.72 |
| fairy | Progeo Exelle Junior (pediatric, pink) | bearing, bolts, rim, spokes, tube | 0.70 |
| orc | Progeo Noir 2.0 (rigid, black) | axle, bearing, brake, rear_wheel, tire | 0.74 |
| edge4 | Quantum Edge 4 (mid-wheel drive, seat elevator) | actuator, armrest, battery, controller, frame, freewheel, seat, seat_lift, wiring | 0.74 |
| m3 | Permobil M3 Corpus (mid-wheel drive) | battery, boot, controller, joystick, wiring | 0.82 |
| trident | Drive Trident HD (bariatric power) | axle, battery, controller, frame, freewheel, motor, wiring | 0.82 |
| aeroz | TiLite Aero Z (ultralight rigid) | anti_tip, axle, bolts, brake, spokes, tire | 0.71 |
| cross6 | Etac Cross 6 (folding) | anti_tip, backrest, bolts, brake, cushion, tire | 0.71 |
| iris | Quickie/Zippie Iris (pediatric tilt-in-space) | anti_tip, brake, tilt_cable, tilt_lever, tilt_lock, tire | 0.69 |
| focuscr | Ki Mobility Focus CR (tilt-in-space) | anti_tip, brake, gas_spring, tilt_cable, tilt_lever, tilt_lock | 0.71 |
| whillc2 | WHILL Model C2 (omni wheels, white) | armrest, battery, controller, freewheel, joystick, seat, seat_cable, tire | 0.80 |
| f5 | Permobil F5 Corpus (FRONT-wheel drive) | battery, breaker, frame, freewheel, joystick, motor, tire | 0.79 |
| pulse6 | Quickie Pulse 6 (mid-wheel drive, VR2) | battery, brushes, controller, freewheel, joystick, motor, wiring | 0.82 |
| q6edge | Quantum Q6 Edge (mid-wheel drive, yellow shroud) | battery, controller, frame, freewheel, joystick, mag_brake, motor, wiring | 0.80 |

(Other labels already on a model may stay. Many manual-chair parts — tire, rim, spokes, axle, bearing, valve, tube,
caster, caster_stem — come from the shared helpers `add_manual_rear_wheel` / `add_front_caster`.)

## 4. How to build and check (run from the project root)
```bash
pip install pygame numpy                         # Python 3.10+ ; pygame-ce also works on 3.12+
python art_tests/build_9_chairs.py               # rebuilds the 9 models into assets/models
python art_tests/build_new_chairs.py "" aeroz,f5 # rebuilds only the listed new models ("" = default output dir)
python art_tests/fit_view.py basic elf f5        # silhouette match vs art: prints IoU, writes art_tests/fit/<key>.png
python art_tests/art_vs_3d.py out.png basic elf  # art | 3D side by side
set SDL_VIDEODRIVER=dummy  (bash: export SDL_VIDEODRIVER=dummy)
python game.py --selftest                        # MUST print "SELFTEST OK" (checks every required part is on every model)
python game.py                                   # play: open a job, the 3D model is shown in the diagnosis window; Tab = big 3D view
```
**Silhouette IoU** is only a helper: the art has strong close-camera perspective, so ~0.85 is about the ceiling and the
best-matching view can be a mirrored one. Always **look at the images yourself**. Target: IoU ≥ 0.75 where possible
and, more importantly, the chair is visually clearly the same model as the art.

If you cannot run code: still edit the builders carefully, keep all conventions above, and say so in your report so the
owner can run the checks.

## 5. What to improve (owner's priorities)
1. **Recognisability:** frame shape and tube bends, wheel type (wire spokes vs mag/5-spoke vs omni), tyre colour,
   push handles (present/absent), armrests and side guards, footrests (one platform vs two plates, angle), backrest
   height/headrest, power-chair bases and shrouds, drive-wheel position (front vs mid), casters and suspension.
2. **Quality:** smooth round wheels and tyres, clean tube joints, no gaps or floating parts, no z-fighting, sensible
   normals/winding (the game draws both sides only when `cull` is false), believable proportions.
3. Known issues: Edge 4 art shows the joystick on the chair's LEFT but the game convention keeps it on +z (right) — keep +z
   unless told otherwise. Manual chairs fit only ~0.70 because of the art's perspective. Iris rocker rails sit inboard and
   are hard to see.

## 6. Deliverables
- Modified `art_tests/build_9_chairs.py` and/or `art_tests/build_new_chairs.py`.
- Regenerated `assets/models/chair_<key>_ai.json` + `_lod.json` for every model you changed.
- A short report: per chair — what changed, IoU before → after, face counts, any compromises.
- Add one entry at the top of «Журнал изменений» in `AGENTS.md`: `YYYY-MM-DD — <your name/model> — what you did (files)`.
- `python game.py --selftest` must print `SELFTEST OK`.

---

## Кратко по-русски (для владельца)
Задача агенту: улучшить 17 процедурных 3D-моделей колясок, чтобы они были похожи на арт `assets/chair_<key>.png`
и выглядели качественнее. Править можно только `art_tests/build_9_chairs.py` и `art_tests/build_new_chairs.py`,
результат — файлы `assets/models/*.json`. Обязательные детали (кликабельные) и соглашения по осям — в таблице выше.
Проверка: `python game.py --selftest` → `SELFTEST OK`, плюс `art_tests/fit_view.py` и картинки сравнения.
