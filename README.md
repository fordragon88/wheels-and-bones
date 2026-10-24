# Wheels & Bones / Колёса и Кости

An educational fantasy **wheelchair repair simulator** in Python + Pygame — real repair procedures, playable with the mouse or with the keyboard alone, with speech for blind players.

[English](#english) · [Русский](#русский)

---

## English

**Wheels & Bones** teaches real wheelchair maintenance and repair through a cozy fantasy story. It is a
single-file Python + Pygame game. The art lives in `assets/`, but the game also runs **without any images**:
characters, wheelchairs and backgrounds fall back to built-in vector art drawn by code.

**Content:** 21 repair jobs (27 breakdown variants), 6 Wheelwrights' Guild jobs plus a final exam, and a
Seating Clinic about posture and positioning.

### The story

**Martin** is a good-natured zombie who keeps losing his left leg (it falls off at the worst moments). He is
invited to a party, the leg is missing again, so he **rents a wheelchair** — and it **breaks down on the way**.

"How do you even fix these?!" Enter **Bartholomew (Barty)**, the ghost of the chair's previous owner. He never
really knew how to repair anything, but he *"watched the masters do it"*, so his hints are sometimes spot on and
sometimes hilariously wrong. Martin gets hooked, opens a workshop and builds a **collection of unusual
wheelchairs** belonging to fantasy clients — an elf, a werewolf, a fairy, an orc, a troll, a kitsune, a dryad, a
little dragon, an owl grandmother — and later takes on **power wheelchairs** too.

Once word spreads, the **Wheelwrights' Guild** notices him, and Martin becomes the apprentice of **Master
Brenna**, the ghost of a dwarf mechanic whose lessons Barty half-remembers. Real technician training begins.

**About the tone.** The humour comes from Martin (and his leg), from the clueless but kind ghost and from
fantasy absurdity. Never from disability: the wheelchairs and their users are treated with respect, the repairs
are shown accurately, and the educational part is real. Clients are confident, lively characters.

### Gameplay: a deep repair sim

Every client is a separate job with a real fault:

1. **Diagnosis.** Inspect the parts of the chair — the diagnosis stays locked until you have gathered evidence
   (at least 2 inspections). Some clients have **different faults behind the same symptom**, so on a repeat
   visit the cause may differ: trust the inspection, not your memory. The chair on screen is a 3D model in real
   proportions — tyres, rims, pushrims, spokes, hub bearings, cross-brace, casters, brakes; on power chairs also
   motors, freewheel levers, battery and joystick controller. Drag it to rotate (during diagnosis and repair),
   scroll to zoom, right-click to reset the view, click a part circle to inspect it.
2. **Repair.** Perform real steps **in the right order**: pick a tool at the bottom, then click the part — right
   on the chair picture or in the list on the right. A wrong tool or part gets an explanation ("you lever a tube
   off with a tyre lever, not a wrench"). Each correct step comes with a short learning note.
3. **Mini-games.** Key steps are more than a click: inflating a tyre to the gauge (stop in the green zone —
   over-inflate and it goes BANG), the spoke ping test (find the dull spokes by ear), setting the brake gap on a
   scale, reading a multimeter (volts → verdict).
4. **Test drive.** The chair goes into your **garage collection** with stars for quality and a "What you
   learned" card.

**Live dialogue.** Clients chat, worry about their plans, react to your moves and share tips from their own
experience as wheelchair users. Barty gives a hint at every step — some are deliberately wrong: learn to read
the manual, not just listen to the ghost.

### What the game teaches (all based on real procedures)

In the hub every job is tagged **ⓜ MANUAL** or **⚡ POWER**.

**Manual wheelchairs:**

| Client | Fault | What you learn |
|---|---|---|
| Martin (tutorial) — Invacare 9000 | Flat rear tyre | Removing the tyre, replacing the tube, inflating to the gauge |
| Aelin the elf — Progeo Ego | Caster flutter — **2 possible causes** | Cleaning the axle and tightening the stem OR the fork mounting — tell them apart by inspection |
| Wolf the werewolf — Quickie 2 | Wheel lock doesn't hold | Pressure, tightening and moving the lock clamp, 3–6 mm gap on a scale |
| Tilly the fairy — Progeo Exelle Junior | Loose spokes | Ping test by ear, spoke tension, bolt strength grades |
| Gra the orc — Progeo Noir 2.0 | Whine from the rear wheel — **2 possible causes** | Replacing a bearing OR moving a rubbing brake away — listen to the hub |
| Bomm the troll — Invacare 9000 XDT | Leaking air cushion | Finding the puncture, patching, pressure-sore prevention |
| Yuki the kitsune — TiLite Aero Z | Wheel lock slips on a slope | Pressure per the sidewall, lock clamp: ≥ 3/16″ (≈5 mm) into the tyre; locks are not brakes |
| Ivushka the dryad — Etac Cross 6 | Crooked backrest | Backrest post angle — 13 mm nut at the wheel mount, compare both sides, check the anti-tippers |
| Iskra the little dragon — Zippie Iris (child, tilt) | Tilt "clunks", chair rocks backwards | Anti-tippers 38–51 mm on both sides, tilt cable tension, no grease on the mechanism |
| Grandma Agatha — Ki Focus CR (tilt) | Tilt "creeps" and sticks | A kinked cable is replaced, never straightened; routing without bends; triggers must not be left locked open |

**Power wheelchairs:**

| Client | Fault | What you learn |
|---|---|---|
| Zix the goblin mechanic — Quantum Edge 4 | Seat lift won't lower — **2 possible causes** | The lift harness stretched at the top and pulled the actuator plug OR a box zip-tied under the seat leaves the scissors nowhere to fold |
| Mora the sorceress — Permobil M3 Corpus | Jerky joystick, torn boot | Dry it first, then restart, cleaning, cable connector (power off); calibration is a technician's job; replacing the boot against moisture |
| Grund the golem — Drive Trident HD | Stalled, whining motor | Freewheel mode (push by hand), motor connectors, diagnosis by sound |
| Saira the lizard — WHILL Model C2 | Red code on the joystick — **3 variants** (01/02/10) | Code table: armrest, joystick touched at power-on, seat connector |
| Count Draculescu — Quantum Q6 Edge 2.0 | After the library the chair crawls — **2 variants** (yellow / red icon) | TRU-Balance 3 inhibits: seat elevated — 1/4 speed, tilt or recline > 20° — drive lockout; Q-Logic 3 indicator green/yellow/red; an object under the lift is removed with the power off; inhibits are never bypassed |
| Matilda the badger — Permobil F5 Corpus | Won't charge after winter | Main breaker during storage, charging not below +5 °C, charger connection order, 250 kPa tyres |
| Baba Yaga — Vermeiren D100 | Raised the seat — the brakes won't hold | Three seat heights (470/500/530 mm) by moving the wheels, forks vertical to the floor; brakes re-adjusted after any height change |
| Olga the mermaid — Panthera X3 | Crunches and runs stiff after the sea | Sand and salt water: clean the caster forks, a drop of oil in the bearings, grease the quick-release axle; 8 bar in the tyres — a brake only holds on an inflated tyre |
| Leshy — Magic Mobility Extreme X8 | Stuck in the bog — pulls to one side | Don't hold the joystick when stuck (motors overheat); unequal tyre pressure pulls the chair sideways; off-road pressure is lower but equal; no driving into water |
| Seneb the mummy — Quickie Nitrum + Alber e-motion | Charging stops in the sun | e-motion wheels charge only at 0…40 °C (all lights flash white, 4 beeps); the wheels have no brakes of their own; a burning battery — sand or a class D extinguisher, never water |
| Zmey Gorynych — Pride Jazzy 614 | Uphill the breaker trips | The main breaker protects motors and electronics: wait a minute, push the button, switch on; repeated tripping — service; 136 kg weight limit includes everything hanging on the chair |

All real wheelchair models, numbers and step orders come from manufacturer manuals; the pages are cited in
`source:` comments on each job in `game.py`.

### The Wheelwrights' Guild — a pro track for future technicians

After **5 repaired chairs** the Guild opens: certified-technician-level jobs with **Master Brenna**. The pro track
plays differently — that is the difference between "following instructions" and "being a technician":

- **Step order is not given** — operations are listed and you build the sequence yourself (steps have real
  dependencies).
- **Numbers only from the manual.** Jobs come with an in-game MANUAL of specs (tolerances, terminal order,
  matching rules); a spec step cannot be done without checking it.
- **A safety violation fails the job**, with an explanation of why the mistake is dangerous. Touching terminals
  with the power on, or removing the positive before the negative, is a fail, not a lost star.

| Job | Level | What you learn |
|---|---|---|
| Truing a wobbly rim | ⓜ technician | Truing stand, runout gauge, tensiometer, 1/4-turn adjustments, 1–2 mm tolerance |
| Replacing a battery pair | ⚡ technician | Power OFF, terminal order (negative off first, positive on first), matching type/capacity/age, first charge |
| Toe-in: the chair pulls | ⓜ technician | Pressure first, then geometry; front/rear rim measurement, 1 mm tolerance, cross-pattern tightening |
| Quickie Pulse 6: 2 bars flashing (VR2) | ⚡ technician | VR2 indicator codes, motor reading 0–1.5 Ω → controller or brushes, brush run-in with the gearbox unlocked |
| Quantum Q6 Edge: code #203 | ⚡ technician | Q-Logic codes, freewheel only with power off, brake reading ≈80 Ω from the block diagram |
| Replacing a battery pair: Q6 Edge 2.0 | ⚡ technician | Same job, different chair: front shroud on release handles, quick-release harness connectors, breaker button on the rear frame, batteries flat with terminals rearward — three specs that only the right manual answers |

**Guild exam.** Pass all six Guild jobs and Brenna admits you to the exam: a **random ticket** from the topics
you have covered, **no hints** (the manual is allowed — just like real life), at most **3 mistakes**, and any
safety violation means an instant retake. Pass and you get the **Guild diploma**, a checklist and the title
"Certified Technician". And yes — Brenna finally remembers Barty.

> ⚠️ **Electrical safety.** The game only teaches **user-level**, safe actions (charging, connectors, joystick
> boot, freewheel mode, multimeter checks) and explicitly discourages poking at live electronics. Freewheel mode
> is engaged only with the power **off** and **on level ground** (the brakes are disengaged). Serious electronics
> (controller, motors, live wiring) belong with a certified technician; when working on electrics, disconnect the
> negative battery terminal first.

### The Seating Clinic — Mortimer the Necromancer teaches positioning

A button in the workshop (after your first repair). The host is **Mortimer the Necromancer**: he has studied
bones for a thousand years and knows better than anyone that "the pelvis is the king of the skeleton". He jokes
about himself and his gloomy trade — never about clients. Based on Permobil's *Wheelchair Seating & Positioning
Guide*.

- **Lessons:** pelvis first; sacral sitting (signs, risks, causes in the chair itself); footrests, knees and feet;
  pelvic obliquity and rotation, three-point lateral support; correct or accommodate a posture (there is no
  universal "90-90-90" recipe); measurements; pressure and tilt-in-space (≥ 45° for pressure relief; recline
  without tilt means shear).
- **Fitting:** the client sits in the chair, side view; sliders change seat depth, footrest length, backrest
  height and angle, tilt — the posture and pressure zones change live. An X-ray skeleton view, "show the
  target", a front view with three-point support. Six fitting clients.
- **Quiz:** 6 questions on postures; pass with 5 correct.

### Running the game

```bash
pip install pygame          # on new Python (3.12+), where pygame won't install: pip install pygame-ce
python game.py
```

Optional: `numpy` enables the big 3D inspection (V key) with a live mesh; the diagnosis window always uses pre-rendered turntable frames. On Windows `cytolk` and `pywin32` enable speech.

On Windows the easiest way is to double-click **`start_game.bat`**: it starts the game and, if something goes
wrong, keeps the window with the error message open instead of closing silently.

Flags:

```bash
python game.py --assets     # list the images the game looks for
python game.py --selftest   # headless logic check (no window)
python game.py --reset      # delete the save (save.json)
python game.py --unlock     # preview: unlock all jobs and the Guild
python game.py --mute       # no sound
python game.py --speak      # turn speech on right away
python game.py --lang en    # force English (or ru)
python game.py --window     # start in a window, not fullscreen
python game.py --feedback   # show player feedback ("I disagree" reports)
```

### Accessibility: playable by blind and low-vision players

The whole game can be played **with the keyboard alone**, and it **talks**:

- arrows — choose an item (← → move sliders), **Tab** / Shift+Tab — next/previous group, **Enter** / Space —
  press, **Esc** — back;
- **R** — repeat where you are and what to do; **T** — read the whole screen; **H** — ghost hint;
  **C** — what the client said; **F1** — help with all keys; **F2** — speech on/off.

If a screen reader is running (NVDA, JAWS), the game speaks **through it** via Tolk (including braille displays);
otherwise it uses the Windows voice in the game's language. With a screen reader running, speech turns on by
itself. In settings (gear → ACCESSIBILITY): characters' lines read aloud, voice speed, high-contrast background,
instant text (no letter-by-letter typing). The pump in the mini-game plays a tone that rises with pressure, and
spokes are checked by ear.

### Settings, sound and screen

The **gear** in the top-right corner of every screen opens the settings menu:

- **SOUND** — master, music, effects and ambience volume, mute (or the **M** key);
- **GRAPHICS** — windowed / fullscreen, resolution (AUTO, 1280×720 … 2560×1440, whatever fits your monitor),
  glow and GPU-accelerated 3D; **F11** / **Alt+Enter** toggles fullscreen;
- **ACCESSIBILITY** — see above.
- **GAME** — progress summary and **RESET PROGRESS** (asks yes/no; settings are kept).

Settings are stored in `settings.json` and are not cleared by `--reset`.

**Sound effects** are synthesized in code — no files needed: chimes for a correct step, a soft "bonk" for a
mistake, a distinct sound per tool, scene ambience (crickets on the road, the forge in the Guild). In the spoke
ping test the bright "ping" and the dull "thunk" really sound different. **Music** is in `assets/music/`
(workshop / road / guild / party), generated locally in ComfyUI with YuE2. Listen to every sound in a row:
`python art_tests/sound_demo.py wav`.

**Mouse controls:** in a repair, click a tool (bottom), then a part (on the chair picture or in the list on the
right). In Guild jobs, click a tool, then a step from the list; the MANUAL button is at the top right.

**Esc is "back" and "quit":** it closes overlays; from the garage/Guild — back to the workshop; from the workshop
— to the title screen; from the title — quits. During a repair you need a **double Esc** (protection against
accidental exits; the current job resets, overall progress is saved automatically after every repair).

**Player feedback.** The ⚑ flag at the top right reports any inaccuracy (a screenshot is saved to
`feedback_shots/`). After a counted mistake an **"I DISAGREE"** button appears: pick a reason and describe what
you think is right. The disputed mistake is not counted (except in the exam). View all reports:
`python game.py --feedback`.

### Where things live

- **Quest texts, diagnoses, steps and solutions** — all in `game.py`, in data blocks: `JOBS` (regular jobs),
  `TECH_JOBS` (Guild), `SEAT_CASES` / `SEAT_LESSONS` / `SEAT_QUIZ` (Seating Clinic), dialogue `CLIENT_TALK` /
  `BARTY_TALK` / `MARTIN_TALK`, and the Guild manual `MANUAL`.
- **English translation** — `assets/lang_en.json`, built from `i18n_work/en*.json` by
  `python i18n_work/build_lang.py`.
- **A readable export of all quests** is in `docs/QUESTS.md` (English) and `docs/QUESTS_ru.md`; regenerate it with `python docs/export_quests.py`.
- **Saves** (`save.json`, `settings.json`, `feedback.json`, `crash.log`):
  - running from source — next to `game.py`;
  - the Windows exe — `%APPDATA%\WheelsAndBones\`;
  - the browser version — the browser's localStorage (keys `wnb:save.json` etc.).
- **Reset progress:** gear → GAME → RESET PROGRESS, or `python game.py --reset`, or delete `save.json`.

### Browser version

```bash
python build_web.py             # build (pygbag → WebAssembly) into web_build/
python build_web.py --serve     # build and serve locally at http://127.0.0.1:8000
```

The browser version is **English only**, has no 3D models (the chair pictures are used instead) and keeps saves
in localStorage; speech goes through an aria-live region on the page (plus the browser voice on F2). It is
currently **not public** and will be published later with `python build_web.py --on`.

### Building a single Windows exe

`build_exe.bat` builds `dist/WheelsAndBones.exe` (PyInstaller, `--onefile`): Python, pygame, art, music,
translation and speech support are all inside — nothing to install. The exe keeps its saves in
`%APPDATA%\WheelsAndBones\`.

### Languages

**Russian / English.** The RU/EN switch is at the top right on the title screen, in the workshop, Guild and
garage; the choice is remembered in `settings.json`. On first launch the language follows the system. Force it
with `python game.py --lang en`. The game logic runs on Russian keys and text is translated on output
(`assets/lang_en.json`; `{0}` marks substitutions). `i18n_work/build_lang.py` rebuilds the dictionary and checks
that no Cyrillic is left on English screens.

### Art

The main art in `assets/` (backgrounds, Martin, the ghosts, Mortimer, clients in their chairs, the wheelchairs,
tool icons) was generated locally in ComfyUI with **Qwen Image** in one clean cartoon style — the pipeline and
prompts are described in **[PROMPTS.md](PROMPTS.md)**, sources and scripts are in `art_tests/`. The wheelchairs
are **drawn from blueprints** in real proportions and only restyled by the model, so the click hotspots land on
the right parts. The 3D models are either procedural (built in code, real millimetres) or made by our team in Meshy
(`meshy_models/`). To replace a picture, drop a
PNG with the same name into `assets/`; `python game.py --assets` prints the full list.

### Checks

```bash
python game.py --selftest            # data, jobs, mini-games, Guild, exam, Seating Clinic, 3D parts, hotspots
python art_tests/ui_playthrough.py   # a bot plays the whole game by clicking and screenshots every screen
python art_tests/keyboard_playthrough.py   # a "blind player" bot plays everything with keys only
python art_tests/monkey_test.py      # thousands of random actions, catches crashes
```

### Credibility: where the repair steps come from

Tools, parts and procedures are taken from real maintenance guides for manual **and power** wheelchairs and from
manufacturer manuals — nothing is made up. If you are unsure about repairing a real chair, leave it to a
technician (especially spoke tensioning and live electronics).

**Sources — manual wheelchairs:**

- [Wheelchair Maintenance and Minor Repairs — UW Spinal Cord Injury (PDF)](https://sci.washington.edu/summit2013/WHEELCHAIR%20MAINTENANCE%20AND%20MINOR%20REPAIRS.pdf) — tools, tube replacement (10 steps), wheel locks, spokes (ping test), casters, bolts, cushions; plus a power chair section (battery, joystick, boot, wiring, motors, water exposure).
- [Maintenance Guide for Users of Manual and Power Wheelchairs — MSKTC (PDF)](https://msktc.org/sites/default/files/2022-06/MSKTC-Wheelchair-Maint-508.pdf) — routine maintenance of manual and power chairs.
- [The Parts of a Wheelchair — Karman Healthcare](https://www.karmanhealthcare.com/the-parts-of-a-wheelchair-and-its-features/) — anatomy: rear wheels, casters, pushrims, brakes.
- [3 Common Causes of Caster Flutter — Caster Concepts](https://www.casterconcepts.com/blog/casters-for-any-application/3-common-causes-of-caster-flutter-and-5-ways-to-correct-it/) — causes and fixes for caster flutter.
- [How to Adjust Wheelchair Locks — DME Hub](https://www.dmehub.net/blog/how-to-adjust-wheelchair-locks-for-optimal-use/) and [How to Fix and Adjust Wheelchair Brakes — Engineer Fix](https://engineerfix.com/how-to-fix-and-adjust-wheelchair-brakes/) — wheel lock adjustment, 1/8–1/4 inch gap.

**Sources — power wheelchairs:**

- [Power Wheelchair Troubleshooting Guide — Southwest Mobility](https://www.southwestmobility.com/articles/power-wheelchair-troubleshooting-guide) — "won't turn on" (key, connectors, breaker/reset), beep codes, joystick, motors.
- [Common Electric Wheelchair Problems & How to Fix Them — Malisa Mobility](https://malisamobility.com/blogs/news/common-electric-wheelchair-problems-and-how-to-fix-them-1) — joystick restart/cleaning/calibration, connector checks.
- [Can You Push an Electric Wheelchair? (freewheel mode) — Quantum Rehab](https://www.quantumrehab.com/resources/consumer-article-can-you-push-an-electric-wheelchair.asp) and [What is a freewheel lever — MedMart](https://medmartonline.com/knowledge-base/what-is-a-freewheel-lever-and-how-do-i-use-it/) — freewheel mode: power off and level ground only, brakes disengaged.

**Sources — Guild pro track (technician level):**

- [Wheel and Rim Truing — Park Tool](https://www.parktool.com/en-us/blog/repair-help/wheel-and-rim-truing) — truing: gauge/caliper, small nipple steps, which way spokes pull.
- [Wheelbuilding — Sheldon Brown](https://www.sheldonbrown.com/wheelbuild.html) — spoke tension, tensiometer, why tuning "by ear" is only a rough estimate.
- Manufacturer service documentation for power wheelchairs (Pride Mobility, Invacare, Permobil, Quantum — public service/owner manuals) — replacing batteries in pairs, terminal order (negative off first, positive on first), first full charge with the original charger, controller codes.
- WHO **Wheelchair Service Training Package** (basic/intermediate) — the real framework for training wheelchair service personnel; the model for the Guild exam.
- Permobil **Wheelchair Seating & Positioning Guide** — the Seating Clinic.

> As in the base game: the game teaches safe procedures and says clearly where the line is — live electronics
> (controller, powered wiring) are fixed by a certified technician, not by a player after the tutorial.

### How to extend

The game is **data-driven** — the content sits in data blocks in `game.py`:

- **New job** → an entry in `JOBS` (symptom, `inspect` clues per part, `diagnosis` options, `steps` via the
  `S(...)` helper, fact) plus client lines in `CLIENT_TALK`.
- **Several causes for one symptom** → a `variants` field: client/symptom shared in the base, while
  `parts/inspect/diagnosis/steps/test/fact` go in each variant; the game picks one at random.
- **Mini-game on a step** → `S(..., mini=dict(kind="pump"|"gap"|"ping"|"meter", ...))`.
- **New Guild job** → an entry in `TECH_JOBS`: steps via `T(...)` (dependencies `after`, `safety=True` for safety
  steps, `spec=...` for values from the manual), a `tools` palette, `manual` pages.
- **New manual page** → an entry in `MANUAL` (specs refer to it).
- **New tool/part** → an entry in `TOOLS` / `PARTS`.
- **Any new text** → add it to the translation (`i18n_work/`, then `python i18n_work/build_lang.py`).
- The self-test (`--selftest`) checks the integrity of all of this automatically.

---

## Русский

Обучающий **симулятор ремонта инвалидных колясок** в фэнтези-мире, на Python +
Pygame. Один файл, играть можно мышью или **только с клавиатуры** (с озвучкой).
Арт лежит в `assets/`, но игра запускается и **без картинок вообще**: весь визуал
(персонажи, коляски, фоны) тогда рисуется кодом во встроенном векторном flat-стиле.

**Контент:** 21 задание (27 вариантов поломок), 6 заданий Гильдии и экзамен,
Кабинет посадки.

### Сценарий

**Мартин** — добродушный зомби, который вечно теряет левую ногу (она отваливается
в самый неподходящий момент). Его позвали на вечеринку друзей. Нога опять
потерялась, и чтобы доехать, Мартин **взял инвалидную коляску напрокат** — а она
**сломалась прямо по дороге**.

«Как их вообще чинят?!» Мир ремонта оказался тёмным и запутанным. Тут появляется
**Бартоломью** — призрак прошлого хозяина коляски. Сам он чинить толком не умел,
но *«видел, как делали мастера»*, и теперь подсказывает Мартину — иногда дельно,
иногда мимо. Вместе они учатся. Мартин втягивается, открывает мастерскую и
**собирает коллекцию диковинных колясок** фэнтези-клиентов: эльфийки, оборотня, феи,
орка, тролля, кицунэ, дриады, дракончика и бабушки-совы — а позже берётся и за
**электрические коляски**.

Когда о мастерской начинают говорить, Мартина замечает **Гильдия Колёсников** —
и он попадает в ученики к **Мастерице Бренне**, призраку гномки-механика. Той
самой, чьи уроки Барти при жизни «видел краем глаза» и теперь пересказывает
через пень-колоду. Начинается настоящее обучение на техника.

**О тоне.** Юмор идёт от Мартина (роняет ногу), от бестолкового, но доброго
призрака и от фэнтези-абсурда. К самим коляскам и их владельцам игра относится
уважительно: ремонт показан достоверно, а образовательная часть — настоящая.

### Геймплей: глубокий ремонт-сим

Каждый клиент — отдельное задание с реальной поломкой. Цикл:

1. **Диагностика.** Осматриваешь детали коляски (клик) — диагноз заблокирован,
   пока не соберёшь улики (минимум 2 осмотра). У части клиентов под одним
   симптомом живут **разные поломки**: при повторном визите причина может
   оказаться другой, так что решает осмотр, а не память. Коляска на экране — 3D-модель
   в реальных пропорциях (шины, обод, обруч, спицы, ступица с подшипниками, X-крестовина,
   касторы, тормоз; у электроколяски — моторы, расцепление, батарея, контроллер с
   джойстиком): тяни мышью — повернуть (и в осмотре, и в ремонте), колесо — зум, правая
   кнопка — исходный вид, клик по кружку детали — осмотр; неосмотренные детали пульсируют.
2. **Ремонт.** Выполняешь реальные шаги **по порядку**: выбираешь нужный
   инструмент внизу, затем кликаешь деталь — **прямо на схеме коляски** (детали
   подсвечиваются и подписываются) или в списке справа. Неверный инструмент или
   деталь — игра объясняет, почему так нельзя (например: «камеру поддевают
   монтажкой, а не ключом»). Каждый верный шаг даёт короткую обучающую заметку.
3. **Мини-интеракции.** Ключевые шаги — не просто клик: накачка шины по
   манометру (останови в зелёной зоне, перекачаешь — «БАБАХ»), пинг-тест спиц
   (найди глухие на колесе), установка зазора тормоза по шкале, чтение
   мультиметра (вольты → вердикт).
4. **Тест-драйв.** Проверяешь — и коляска отправляется в **гараж-коллекцию** со
   звёздами за качество и карточкой «Что ты узнал».

**Живые диалоги.** Клиенты болтают, волнуются о своих планах, реагируют на твои
ходы и делятся советами из собственного опыта пользователей колясок.
**Бартоломью** даёт подсказку на каждом шаге. Часть подсказок — намеренно
смешно-неверные: учись читать инструкцию, а не только слушать призрака.

### Что игра учит чинить (всё — по реальным процедурам)

В хабе у каждого задания свой тег: **ⓜ РУЧНАЯ** или **⚡ ЭЛЕКТРО**.

**Ручные коляски:**

| Клиент | Поломка | Чему учит |
|---|---|---|
| Мартин (туториал) — Invacare 9000 | Прокол заднего колеса | Бортировка покрышки, замена камеры, накачка по манометру |
| Эльфийка Аэлин — Progeo Ego | Тряска переда — **2 варианта причины** | Чистка оси и подтяжка штока ИЛИ крепёж вилки — различай осмотром |
| Оборотень Вольф — Quickie 2 | Тормоз-замок не держит | Давление, подтяжка и сдвиг крепления, зазор 3–6 мм по шкале |
| Фея Тилли — Progeo Exelle Junior | Ослабли спицы | Пинг-тест на слух («пинь»/«тук»), натяжение спиц, класс прочности болтов |
| Орк Гра — Progeo Noir 2.0 | Вой у заднего колеса — **2 варианта причины** | Замена подшипника ИЛИ отодвинуть трущий тормоз — слушай ступицу |
| Тролль Бомм — Invacare 9000 XDT | Дырявая воздушная подушка | Поиск прокола, заплатка, профилактика пролежней |
| Кицунэ Юки — TiLite Aero Z | Тормоз-замок не держит на уклоне | Давление по боковине, хомут замка: упор ≥ 3/16″ (≈5 мм) в шину; замки — не тормоза |
| Дриада Ивушка — Etac Cross 6 | Спинку перекосило | Угол стоек — гайка 13 мм у крепления колеса, сверка обеих сторон, проверка антиопрокидывателей |
| Дракончик Искра — Zippie Iris (детская, наклон) | Наклон «клацает», качает назад | Антиопрокидыватели 38–51 мм с обеих сторон, натяжка троса наклона, без смазки механизма |
| Бабушка Агата — Ki Focus CR (наклон) | Наклон «ползёт» и заедает | Трос с заломом — только замена, прокладка без изгибов, нельзя оставлять курки зафиксированными открытыми |

**Электрические коляски:**

| Клиент | Поломка | Чему учит |
|---|---|---|
| Гоблин-механик Зикс — Quantum Edge 4 | Не опускается лифт сиденья — **2 варианта причины** | Жгут лифта натянулся в верхней точке и вытянул разъём актуатора ИЛИ под сиденье привязан ящик — ножницам некуда складываться |
| Чародейка Мора — Permobil M3 Corpus | Дёргает джойстик, порван пыльник | Сначала просушка, потом перезагрузка, чистка, разъём кабеля (без питания); калибровка — работа техника; замена пыльника против влаги |
| Голем Грунд — Drive Trident HD | Заглохла, вой мотора | Режим свободного хода (откатить вручную), разъёмы мотора, диагностика по звуку |
| Ящерка Сайра — WHILL Model C2 | Красный код на пульте — **3 варианта** (01/02/10) | Таблица кодов: подлокотник, джойстик при включении, разъём сиденья |
| Граф Дракулеску — Quantum Q6 Edge 2.0 | После библиотеки коляска ползёт — **2 варианта** (жёлтый / красный значок) | Блокировки TRU-Balance 3: поднятое сиденье — 1/4 скорости, наклон или откидывание > 20° — ход запрещён; индикатор Q-Logic 3 зелёный/жёлтый/красный; посторонний предмет под лифтом убирают при выключенном питании; блокировки не обходят |
| Барсучиха Матильда — Permobil F5 Corpus | Не заряжается после зимы | Главный автомат на хранении, заряд не ниже +5 °C, порядок подключения зарядки, шины 250 кПа |
| Баба Яга — Vermeiren D100 | Подняла сиденье — тормоза не держат | Три высоты сиденья (470/500/530 мм) перестановкой колёс, вилки отвесно к полу; после смены высоты тормоза регулируют заново |
| Русалка Ольга — Panthera X3 | После моря хрустит и туго ходит | Песок и солёная вода: чистить вилки касторов, по капле масла в подшипники, смазать быстросъёмную ось; 8 бар в шинах — тормоз держит только на накачанной шине |
| Леший — Magic Mobility Extreme X8 | Застрял в болоте — тянет вбок | Застрял — джойстик не держать (мотор перегреется); разное давление в шинах тянет вбок; на бездорожье давление ниже, но одинаковое; в воду не въезжать |
| Мумия Сенеб — Quickie Nitrum + Alber e-motion | Зарядка обрывается на солнце | Колёса e-motion заряжают только при 0…40 °C (все огоньки мигают белым, 4 сигнала); своих тормозов у колёс нет; горящая батарея — песок или огнетушитель класса D, не вода |
| Змей Горыныч — Pride Jazzy 614 | В горку выбивает автомат | Главный автомат защищает моторы и электронику: минута, кнопка, включить; выбивает снова — сервис; предел 136 кг включает всё, что висит на коляске |

Все реальные модели колясок, цифры и порядок шагов — из инструкций производителей
(страницы указаны в комментариях `source:` у заданий в `game.py`).

### Гильдия Колёсников — про-трек для будущих техников

После **5 починенных колясок** открывается Гильдия: задания уровня
сертифицированного техника. Наставница — **Мастерица Бренна**, призрак
гномки-механика (та самая, у которой «видел, как делали мастера» Бартоломью).

Про-трек играется иначе — это и есть разница между «уметь по инструкции» и
«быть техником»:

- **Порядок шагов не подсказывается** — операции даны списком, последовательность
  выстраиваешь сам (у шагов есть реальные зависимости).
- **Числа — только из мануала.** У заданий есть внутриигровой МАНУАЛ со спеками
  (допуски, порядок клемм, правила подбора); шаг со спецификацией нельзя
  выполнить, не сверившись.
- **Нарушение техники безопасности проваливает задание** — с разбором, чем
  именно опасна ошибка. Работа с клеммами при включённом питании или снятие
  плюса раньше минуса — это не «минус звёздочка», это провал.

| Задание | Уровень | Чему учит |
|---|---|---|
| Правка «восьмёрки» обода | ⓜ техник | Правочный станок, индикатор биения, тензиометр, правка по 1/4 оборота, допуск 1–2 мм |
| Замена пары батарей | ⚡ техник | Питание ВЫКЛ, порядок клемм (минус первым снимаем, плюс первым ставим), подбор пары по типу/ёмкости/возрасту, первая зарядка |
| Схождение: коляску уводит | ⓜ техник | Сначала давление, потом геометрия; замер между ободами спереди/сзади, допуск 1 мм, затяжка крест-накрест, контрольный замер |
| Quickie Pulse 6: мигают 2 деления (VR2) | ⚡ техник | Коды индикатора VR2, замер мотора 0–1,5 Ом → контроллер или щётки, обкатка щёток с разблокированным редуктором |
| Quantum Q6 Edge: код #203 | ⚡ техник | Коды Q-Logic, свободный ход только без питания, замер тормоза ≈80 Ом по блок-схеме |
| Замена пары батарей: Q6 Edge 2.0 | ⚡ техник | Та же работа, другая коляска: передний кожух на ручках-защёлках, быстросъёмные разъёмы жгута, автомат-кнопка на задней раме, батареи плашмя клеммами назад — три спеки, на которые отвечает только нужный мануал |

**Экзамен Гильдии.** Сдал зачёты Гильдии — Бренна допускает к экзамену:
**случайный билет** из пройденных тем, **без подсказок** (мануал разрешён — как
в жизни), лимит **3 ошибки**, нарушение техники безопасности = мгновенная
пересдача. Сдал — **диплом Гильдии** на экране результата, чек-лист по пунктам
и звание «Сертифицированный техник». И да — Бренна наконец вспоминает Барти.

> ⚠️ **Безопасность электрики.** Игра учит только **пользовательским**, безопасным
> действиям (зарядка, контакты, пыльник, режим свободного хода, проверка
> мультиметром) и прямо отговаривает «лезть в живую электронику». Свободный ход
> включают только при **выключенном** питании и **на ровном месте** (тормоза при
> этом отключены). Серьёзную электронику (контроллер, моторы, проводку под
> напряжением) в реальности доверяют сертифицированному технику; при работе с
> электрикой сначала снимают клемму с минуса батареи.

### Кабинет посадки — некромант Мортимер учит позиционированию

Кнопка в мастерской (после первого ремонта). Хозяин — **некромант Мортимер**: тысячу лет
изучает кости и потому лучше всех знает, что «таз — король скелета». Шутит над собой
и своим мрачным ремеслом, никогда — над клиентами. Материал — по руководству Permobil
«Wheelchair Seating & Positioning Guide».

- **Уроки:** сначала таз; сидение на крестце (признаки, риски, причины в самой коляске);
  подножка и колени/стопы; перекос и поворот таза, боковые упоры «в три точки»;
  исправить или учесть позу (готового рецепта «90-90-90» нет); мерки; давление и
  наклон сиденья (≥ 45° для разгрузки, откидывание без наклона = сдвиг тканей).
- **Примерка:** клиент в коляске сбоку; ползунками меняешь глубину сиденья, длину
  подножки, высоту и угол спинки, наклон — поза фигуры и зоны давления меняются вживую.
  Скелет-«рентген», «показать норму», вид спереди с тремя точками опоры; шесть клиентов.
  Мерки клиента и карта терапевта даны: игрок — техник, который настраивает коляску.
- **Проверь себя:** 6 вопросов по позам, зачёт — 5 верных.

### Запуск

```bash
pip install pygame          # на новых Python (3.12+), где pygame не ставится: pip install pygame-ce
python game.py
```

Необязательно: `numpy` включает большой 3D-осмотр (клавиша V) с живой сеткой; в окне диагностики всегда заранее снятые кадры поворота. На Windows `cytolk` и `pywin32` — озвучку.

На Windows проще всего — двойной клик по **`start_game.bat`**: он запускает
игру и, если что-то пошло не так, оставляет окно с текстом ошибки открытым
(а не молча закрывается).

Флаги:

```bash
python game.py --assets     # список картинок, которые ищет игра
python game.py --selftest   # headless-проверка логики (без окна)
python game.py --reset      # удалить сохранение (save.json)
python game.py --unlock     # предпросмотр: открыть все задания и Гильдию
python game.py --mute       # без звука
python game.py --speak      # сразу включить озвучку
python game.py --lang en    # принудительно английский (или ru)
python game.py --window     # в окне, а не во весь экран
python game.py --feedback   # показать замечания игроков («Я не согласен»)
```

### Доступность: игра для незрячих и слабовидящих

Вся игра проходится **с клавиатуры** и умеет **говорить**:

- стрелки — выбрать пункт (← → двигают ползунки), **Tab** / Shift+Tab — следующая/предыдущая группа,
  **Enter** / Пробел — нажать, Esc — назад;
- **R** — повторить, где ты и что делать; **T** — прочитать весь экран; **H** — подсказка призрака;
  **C** — что сказал клиент; **F1** — все клавиши; **F2** — озвучка вкл/выкл.

Если запущен экранный чтец (NVDA, JAWS), игра говорит **его голосом** через Tolk (и на брайлевский дисплей);
без чтеца — голосом Windows на языке игры. Под чтецом озвучка включается сама. В настройках
(шестерёнка → ДОСТУПНОСТЬ): реплики героев вслух, скорость голоса, контрастный фон, текст без печати по буквам.
Насос в мини-игре звучит тоном, который растёт с давлением; спицы проверяются на слух.

### Настройки, звук и экран

**Шестерёнка** справа вверху любого экрана открывает меню настроек:

- **ЗВУК** — общая громкость, музыка, эффекты и атмосфера сцен отдельными ползунками, «без звука»
  (или клавиша **M**);
- **ГРАФИКА** — режим (в окне / весь экран), разрешение (АВТО, 1280×720, 1600×900, 1920×1080,
  2560×1440 — что помещается на монитор), свечение и 3D через видеокарту. Раскладка задана в 1280×720,
  а рисуется всё в выбранном разрешении; кадр вписывается в окно по центру без искажений, окно можно
  тянуть и разворачивать. **F11** / **Alt+Enter** — весь экран;
- **ДОСТУПНОСТЬ** — см. выше.
- **ИГРА** — сводка прогресса и **СБРОСИТЬ ПРОГРЕСС** (с вопросом «да / нет»; настройки сохраняются).

Настройки хранятся в `settings.json` и не сбрасываются `--reset`.

**Звук** синтезируется прямо кодом — файлы не нужны: колокольчики за верный
шаг, мягкий «бонк» за ошибку, у инструментов свой звук (металл звякает, тряпка
шуршит, мультиметр пищит), «блип» лупы при осмотре, звёзды звенят по нотам,
у каждой сцены тихая фоновая атмосфера (сверчки на дороге, треск горна в Гильдии,
музыкальная шкатулка на вечеринке). В пинг-тесте спиц звонкое «пинь» и глухое
«тук» реально различаются на слух — тренировка как у настоящего механика.
**Музыка** — `assets/music/` (workshop / road / guild / party, mp3): своя тема у
мастерской, ночной дороги, Гильдии и вечеринки, плавный переход при смене сцены.
Сгенерирована локально в ComfyUI моделью YuE2 (исходники и варианты — `art_tests/music/`).
YuE2 — песенная модель и почти всегда «напевает» мелодию; вокал проверяется разделителем
MelBandRoFormer, и где он есть, в игру идёт инструментальная дорожка без него.
Послушать все звуки подряд: `python art_tests/sound_demo.py wav`.

**Визуализация**: верный шаг — инструмент «работает» прямо на детали (ключ проворачивается,
насос качает, монтажка поддевает…), ошибка — красный крест; тест-драйв — клиент проезжает
через мастерскую; шутки про ногу Мартина разыграны сценками (`assets/gag_leg.png`).

**Управление мышью:** в ремонте — сначала клик по инструменту (внизу),
потом по детали (на схеме коляски или в списке справа). В заданиях Гильдии —
по инструменту, потом по шагу из списка; кнопка МАНУАЛ — вверху справа.

**Esc — «назад» и выход:** закрывает оверлеи; из гаража/Гильдии — в мастерскую;
из мастерской — на титул; с титула — выход из игры. В ремонте — **двойной
Esc** (защита от случайного выхода; прогресс задания сбросится, общий прогресс
сохраняется после каждого ремонта автоматически).

**Замечания игроков («Я не согласен» и флажок ⚑).** Флажок ⚑ справа вверху — сообщить о любой неточности
(снимок экрана сохраняется сам в `feedback_shots/`). После засчитанной ошибки в задании появляется кнопка
«Я НЕ СОГЛАСЕН»: игрок выбирает причину и пишет, как правильно по его мнению. Замечание сохраняется
в `feedback.json` (см. «Где что лежит»), спорная ошибка не засчитывается (кроме экзамена).
Посмотреть все замечания: `python game.py --feedback`.

### Где что лежит

- **Тексты квестов, диагнозы, шаги и решения** — всё в `game.py`, в блоках данных: `JOBS` (обычные
  задания), `TECH_JOBS` (Гильдия), `SEAT_CASES` / `SEAT_LESSONS` / `SEAT_QUIZ` (Кабинет посадки),
  реплики `CLIENT_TALK` / `BARTY_TALK` / `MARTIN_TALK`, мануал Гильдии `MANUAL`.
- **Английский перевод** — `assets/lang_en.json`, собирается из `i18n_work/en*.json` командой
  `python i18n_work/build_lang.py`.
- **Читаемая выгрузка всех квестов** — `docs/QUESTS.md` (English) и `docs/QUESTS_ru.md`; пересобрать: `python docs/export_quests.py`.
- **Сохранения** (`save.json`, `settings.json`, `feedback.json`, `crash.log`):
  - запуск из исходников — рядом с `game.py`;
  - exe для Windows — `%APPDATA%\WheelsAndBones\`;
  - браузерная версия — localStorage браузера (ключи `wnb:save.json` и т. д.).
- **Сбросить прогресс:** шестерёнка → ИГРА → СБРОСИТЬ ПРОГРЕСС, или `python game.py --reset`, или удалить `save.json`.

### Браузерная версия

```bash
python build_web.py             # сборка (pygbag → WebAssembly) в web_build/
python build_web.py --serve     # собрать и запустить локально: http://127.0.0.1:8000
```

Браузерная версия — **только на английском**, без 3D-моделей (вместо них рисунки колясок), сохранения —
в localStorage; озвучка — через aria-live на странице (плюс голос браузера по F2). Сейчас она **скрыта**
и будет опубликована позже командой `python build_web.py --on`.

### Арт: сгенерированный в ComfyUI + векторный запасной

Основной арт — в папке **`assets/`**: фоны, Мартин, два призрака, Мортимер, клиенты
в своих колясках, учебные коляски и иконки инструментов. Всё сделано локально в ComfyUI на
**Qwen Image** в едином чистом мультяшном стиле — конвейер, промпты и грабли описаны в
**[PROMPTS.md](PROMPTS.md)**, исходники и скрипты — в `art_tests/`.

**Коляски — по чертежу.** Учебные коляски не «придуманы» нейросетью: сначала
рисуется чертёж в реальных пропорциях (`art_tests/chair_skeleton.py`,
`art_tests/power_skeleton.py`), модель только перерисовывает его в стиле.
`art_tests/build_assets.py` вписывает каждую коляску в габарит чертежа, поэтому
хотспоты (`CHAIR_HOTSPOTS`) попадают в детали на любой коляске своего типа.

**Без `assets/` игра тоже работает**: всё рисуется векторным кодом (`VECTOR_ART`),
и векторные схемы колясок построены по тому же чертежу — механика и хотспоты
совпадают с PNG. **3D-модели** колясок — либо процедурные (строятся кодом в реальных мм, `assets/models/`,
сборка — `art_tests/build_9_chairs.py`, `art_tests/build_new_chairs.py`), либо сделаны нашей командой в Meshy
(`meshy_models/`).

Заменить картинку — положить PNG с тем же именем в `assets/` (кода не трогать).
Персонажи — с прозрачным фоном, вписываются без искажения пропорций.
`python game.py --assets` печатает полный список файлов.

Иконки инструментов — `assets/tool_<id>.png`: панель инструментов на экране
ремонта — минималистичные плитки-иконки с анимацией, описание инструмента — в карточке
справа, выбранный инструмент «в руке» следует за курсором.

### Языки и сборка в один файл

**Русский / English.** Переключатель RU/EN — справа вверху на титуле, в мастерской,
Гильдии и гараже; выбор запоминается в `settings.json`. При первом запуске язык берётся
из системы. Принудительно: `python game.py --lang en`. Перевод — `assets/lang_en.json`
(ключ — русская строка, `{0}` — подстановки); весь текст переводится на выводе, логика
игры остаётся на русских ключах. Инструменты перевода — `i18n_work/` (`build_lang.py`
собирает словарь и проверяет, что на английском экране не осталось кириллицы).

**Один файл для друзей.** `build_exe.bat` собирает `dist/WheelsAndBones.exe` (PyInstaller,
`--onefile`): внутри Python, pygame, картинки, музыка, перевод и озвучка — ничего ставить не нужно.
Сохранения exe-версии лежат в `%APPDATA%\WheelsAndBones\`.

**Проверки:**

```bash
python game.py --selftest            # данные, задания, мини-игры, Гильдия, экзамен, кабинет посадки, 3D, хотспоты
python art_tests/ui_playthrough.py   # бот проходит всю игру кликами и снимает каждый экран
python art_tests/keyboard_playthrough.py   # «незрячий игрок» проходит всё одними клавишами
python art_tests/monkey_test.py      # тысячи случайных действий, ловит падения
```

### Достоверность: на чём основаны шаги ремонта

Инструменты, детали и порядок действий взяты из реальных руководств по
обслуживанию ручных **и электрических** колясок и из инструкций производителей —
это не выдумка. Если хочешь углубиться или проверить: ремонт реальной коляски, в
котором ты не уверен, лучше доверить техническому специалисту (особенно натяжение
спиц и электронику под напряжением).

**Источники — ручные коляски:**

- [Wheelchair Maintenance and Minor Repairs — UW Spinal Cord Injury (PDF)](https://sci.washington.edu/summit2013/WHEELCHAIR%20MAINTENANCE%20AND%20MINOR%20REPAIRS.pdf) — инструменты, замена камеры (10 шагов), тормоза-замки, спицы (пинг-тест), касторы, болты, подушки; а также раздел по электроколяскам (батарея, джойстик, пыльник, проводка, моторы, контакт с водой).
- [Maintenance Guide for Users of Manual and Power Wheelchairs — MSKTC (PDF)](https://msktc.org/sites/default/files/2022-06/MSKTC-Wheelchair-Maint-508.pdf) — регулярное обслуживание ручных и электрических колясок.
- [The Parts of a Wheelchair — Karman Healthcare](https://www.karmanhealthcare.com/the-parts-of-a-wheelchair-and-its-features/) — анатомия: задние колёса, касторы, ободы-толкатели, тормоза.
- [3 Common Causes of Caster Flutter — Caster Concepts](https://www.casterconcepts.com/blog/casters-for-any-application/3-common-causes-of-caster-flutter-and-5-ways-to-correct-it/) — причины и устранение флаттера кастора.
- [How to Adjust Wheelchair Locks — DME Hub](https://www.dmehub.net/blog/how-to-adjust-wheelchair-locks-for-optimal-use/) и [How to Fix and Adjust Wheelchair Brakes — Engineer Fix](https://engineerfix.com/how-to-fix-and-adjust-wheelchair-brakes/) — регулировка тормоза-замка, зазор 1/8–1/4 дюйма.

**Источники — электрические коляски:**

- [Power Wheelchair Troubleshooting Guide — Southwest Mobility](https://www.southwestmobility.com/articles/power-wheelchair-troubleshooting-guide) — «не включается» (ключ, разъёмы, автомат/сброс), коды-сигналы, джойстик, моторы.
- [Common Electric Wheelchair Problems & How to Fix Them — Malisa Mobility](https://malisamobility.com/blogs/news/common-electric-wheelchair-problems-and-how-to-fix-them-1) — перезагрузка/чистка/калибровка джойстика, проверка разъёмов.
- [Can You Push an Electric Wheelchair? (freewheel mode) — Quantum Rehab](https://www.quantumrehab.com/resources/consumer-article-can-you-push-an-electric-wheelchair.asp) и [What is a freewheel lever — MedMart](https://medmartonline.com/knowledge-base/what-is-a-freewheel-lever-and-how-do-i-use-it/) — режим свободного хода: только при выключенном питании и на ровном месте, тормоза отключаются.

**Источники — про-трек Гильдии (уровень техника):**

- [Wheel and Rim Truing — Park Tool](https://www.parktool.com/en-us/blog/repair-help/wheel-and-rim-truing) — правка обода: индикатор/суппорт, малые шаги ниппеля, в какую сторону тянут спицы.
- [Wheelbuilding — Sheldon Brown](https://www.sheldonbrown.com/wheelbuild.html) — натяжение спиц, тензиометр, почему «на звон» — только грубая прикидка.
- Сервис-документация производителей электроколясок (Pride Mobility, Invacare, Permobil, Quantum — открытые service/owner manuals) — замена батарей парой, порядок клемм (минус снимают первым, плюс подключают первым), первая полная зарядка штатным ЗУ, коды контроллеров.
- WHO **Wheelchair Service Training Package** (basic/intermediate) — реальная рамка подготовки специалистов по колясочному сервису; ориентир для экзамена Гильдии.
- Permobil **Wheelchair Seating & Positioning Guide** — Кабинет посадки.

> Как и в базовой игре: игра учит безопасным процедурам и прямо говорит, где
> граница — живую электронику (контроллер, проводка под напряжением) чинит
> сертифицированный техник, а не игрок после туториала.

### Как расширять

Игра **data-driven** — контент лежит в блоках данных в `game.py`:

- **Новое задание** → запись в `JOBS` (симптом, `inspect`-подсказки по деталям,
  варианты `diagnosis`, список `steps` через хелпер `S(...)`, факт) и реплики клиента в `CLIENT_TALK`.
- **Несколько причин у одного симптома** → поле `variants` в задании: общие
  клиент/симптом в базе, а `parts/inspect/diagnosis/steps/test/fact` — в каждом
  варианте; игра выбирает случайный (см. эльфийку и орка).
- **Мини-интеракция на шаге** → `S(..., mini=dict(kind="pump"|"gap"|"ping"|"meter", ...))`.
- **Новое про-задание Гильдии** → запись в `TECH_JOBS`: шаги через `T(...)`
  (зависимости `after`, `safety=True` для шагов ТБ, `spec=...` для значений из
  мануала), палитра `tools`, страницы `manual`.
- **Новая страница мануала** → запись в `MANUAL` (на неё ссылаются спеки).
- **Новый инструмент/деталь** → запись в `TOOLS` / `PARTS`.
- **Любой новый текст** → в перевод (`i18n_work/`, затем `python i18n_work/build_lang.py`).
- Селфтест (`--selftest`) проверяет целостность всего этого автоматически.

Идеи на потом: варианты поломок для остальных клиентов (движок уже готов),
чтение кодов ошибок контроллера на слух (писки уже синтезируются), новые
про-задания (подшипники ступицы с выпрессовкой, щётки мотора, актуатор
наклона), таймер/счёт за скорость, «магазин запчастей».
