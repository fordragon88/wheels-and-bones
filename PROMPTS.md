# КОЛЁСА И КОСТИ — как генерируется арт
> **Актуальность (24.10.2026).** Этот файл описывает первый конвейер арта (ComfyUI, Qwen Image, коляски «по чертежу»).
> Сейчас коляски — 3D-модели Meshy, снятые кадрами в Blender (AGENTS.md §8б), а новые портреты и иконки инструментов рисует
> Codex по ТЗ `art_tests/codex_*/BRIEF.md`. Фоны, Мартин, призраки, Мортимер и ранние клиенты — по-прежнему из ComfyUI.


Весь арт игры сделан локально в ComfyUI на **Qwen Image 2.1** (стиль выбран после
сравнения с Flux 2 Klein + LoRA, Hunyuan Image 3 и Krea 2). Исходники и рабочие
файлы — в `art_tests/`, готовые ассеты — в `assets/` (игра подхватывает их сама,
без PNG рисует векторные заглушки).

- `art_tests/final_v1/` — финальные картинки (исходное разрешение, с прозрачностью)
- `art_tests/build_assets.py` — собирает `assets/` из `final_v1/` и считает хотспоты колясок
- `art_tests/chair_skeleton.py`, `art_tests/power_skeleton.py` — чертежи колясок в реальных мм
- `art_tests/hotspots_check/` — коляски с нанесёнными хотспотами для проверки глазами

---

## Главное правило: коляски — по чертежу, не «из головы»

Коляски — учебный материал, их механика должна быть верной. Поэтому коляску никогда
не генерируем с нуля: сначала рисуем **чертёж в реальных пропорциях** (колесо 24″,
кастор, сиденье ~50 см, тормоз упирается в шину; у электроколяски — средний привод),
а Qwen его только **перерисовывает в стиле**, сохраняя геометрию.

После генерации каждую коляску проверяем глазами: тормоз-рычаг, вилка кастора,
подножка, обруч, спицы. Варианты, где деталь пропала, — в брак.

Хотспоты: `build_assets.py` вписывает контур каждой коляски в габарит чертежа в рамке
380×300, поэтому у всех колясок одного типа детали на одних координатах, а
`CHAIR_HOTSPOTS` в `game.py` считаются из мм чертежа (константы `CHAIR_GEOM`).

## Конвейер (ComfyUI, Qwen Image 2.1)

Модели: `qwen2.1\qwen_image_2.1_int8_convrot` → `QwenImage21Cache`,
CLIP `Qwen text_encoder\qwen3vl_8b_int8_convrot` (type qwen_image),
VAE `qwen_image_2.1_vae_bf16`, `TextEncodeQwenImage21`, KSampler 25 шагов, cfg 1,
euler/simple. Для правки по картинке — `resolution: 0`, латент из выхода энкодера.

1. **Фон** — text-to-image 1280×720, без персонажей, со свободным местом под клиента.
2. **Коляска** — правка по двум картинкам: `<image1>` чертёж, `<image2>` фон мастерской
   как образец стиля. Цвет рамы — под клиента.
3. **Клиент** — правка: `<image1>` готовая коляска, `<image2>` фон; «посади персонажа
   в эту коляску, коляску не меняй».
4. **Вырезка фона** — два способа, по типу объекта:
   - **непрозрачное** (коляски, клиенты) — `BiRefNetRMBG`, модель `BiRefNet-HR-matting`,
     `refine_foreground`: режет по маске пиксель в пиксель, геометрия коляски не меняется,
     между спицами прозрачно;
   - **полупрозрачное** (призраки Барти и Бренна) — правка Qwen 2.1 с промптом
     `Remove the background, and output a PNG image` (шаблон
     `image_qwen_image_2_1_background_removal`): VAE Qwen 2.1 сразу отдаёт RGBA, свечение и
     прозрачность сохраняются. BiRefNet на призраках оставляет тёмные дыры. Минус Qwen —
     он перерисовывает картинку (объект мельче, детали могут сдвинуться), поэтому для
     учебных колясок не годится.
5. `python art_tests/build_assets.py <папка с чертежами>` → `assets/`, затем
   `python game.py --selftest`.

### Стиль (суффикс/префикс)

```
clean, bright, colorful cartoon style with soft shading, clean readable shapes, no text
```

### Шаблоны промптов

**Фон:**
```
Video game background art in a clean, bright, colorful cartoon style with soft shading,
clean readable shapes, no characters, no text. <описание сцены>, open floor in the center.
```

**Коляска по чертежу:**
```
Redraw the wheelchair from <image1> in the exact art style of <image2>: the same clean,
bright, colorful cartoon rendering, soft shading, line quality and warm lighting. Keep the
wheelchair from <image1> exactly: the same side view facing right, the same proportions
and the same position of every part (large rear wheel with spokes and pushrim, front
caster with fork, seat, backrest, armrest, footrest, brake lever, push handles).
<цвета рамы и обивки>. Show only the wheelchair on a plain white background, no room,
no people, no text.
```

**Клиент в коляске:**
```
Seat <персонаж> in the wheelchair from <image1>, drawn in the exact clean, bright,
colorful cartoon style of <image2>. The character sits naturally and comfortably upright
on the seat cushion with their back against the backrest, facing right, feet on the
footplate, looking confident and friendly. Keep the wheelchair exactly as in <image1>:
the same side view, size, position, proportions, colors and every part. Plain white
background, no room, no text.
```
(для электроколяски — `one hand resting on the joystick knob`)

## Персонажи

| Ассет | Кто | Коляска |
|---|---|---|
| `martin.png` | Мартин — добрый зомби, бледно-зелёная кожа, жилет с заплатками; левой ноги нет ниже колена | базовая, голубая |
| `ghost.png` | Барти — прозрачный бирюзовый джентльмен-призрак, монокль, бабочка, парит | — |
| `master.png` | Мастерица Бренна — призрак пожилой гномки, очки, косы, фартук с ключами | — |
| `client_elf.png` | Аэлин — золотая коса, острые уши, зелёная туника | шалфейно-зелёная |
| `client_dwarf.png` | (с 23.10.2026 — оборотень Вольф на Quickie 2, портрет — Codex; имя файла прежнее) до того: Дургин — гном-кузнец, рыжая заплетённая борода, фартук, молот | была бронзовая с заклёпками (Tekna) |
| `client_fairy.png` | Тилли — маленькая фея, розовые волосы, крылья | розовая с цветочками |
| `client_orc.png` | Гра (мужчина!) — орк, клыки, пучок, кожаный жилет | хаки, шипованные шины |
| `client_troll.png` | Бомм — большой застенчивый тролль, мох, шарф, свитер | усиленная серая |
| `client_goblin.png` | Зикс — гоблин-механик, очки-гогглы, пояс с отвёртками | электро |
| `client_sorceress.png` | Мора — серебряные волосы, звёздная мантия, руны | электро |
| `client_golem.png` | Грунд — каменный голем, мох, светящиеся руны-глаза | электро |
| `client_centaur.png` | Тавр — кентавр-курьер, кепка, зелёная рубашка, сумка; задние ноги на колёсной тележке | своя тележка |
| `client_q6edge2.png` | Граф Дракулеску — вампир-библиотекарь: бледная серо-лиловая кожа, монокль, чёрный плащ с красной подкладкой, бордовый жилет, жабо с рубином, стопка старых книг на коленях, летучая мышь на подголовнике; **портрет — Codex** (`art_tests/codex_dracula/BRIEF.md`, 24.10) | Quantum Q6 Edge 2.0, синяя (рендер нашей модели — главный референс) |
| `client_aeroz.png` | Юки — кицунэ-лисица, рыжая, несколько хвостов | TiLite Aero Z (3D Meshy) |
| `client_cross6.png` | Ивушка — дриада, кора и листья, зелёные волосы | Etac Cross 6 (3D Meshy) |
| `client_f5.png` | Матильда — барсучиха-пасечница, фартук, дымарь | Permobil F5 Corpus (3D Meshy) |
| `client_focuscr.png`, `client_focuscr_grandson.png` | Агата — пожилая сова-астроном, очки, мантия в звёздах; с внуком-филином; **портреты — Codex** (`art_tests/codex_agata*/`) | Ki Mobility Focus CR, наклон 20° (3D Meshy) |
| `client_iris.png`, `client_iris_mom.png` | Искра — дракончик; с мамой-драконихой за спинкой | Zippie Iris, наклон ≥ 45° (процедурная 3D) |
| `client_whillc2.png` | Сайра — ящерка-картограф, тубус с картами | WHILL Model C2 (3D Meshy) |
| `client_yaga.png` | Баба Яга — ступа заменена коляской, платок, клюка | Vermeiren D100 (3D Meshy) |
| `client_rusalka.png` | Ольга — русалка, хвост, мокрые волосы | Panthera X3 (3D Meshy) |
| `client_leshy.png` | Леший — мох, ветки, болотная тина | Magic Mobility Extreme X8 (3D Meshy) |
| `client_mummy.png` | Сенеб — мумия в бинтах (до 22.10 — Ра) | Quickie Nitrum + Alber e-motion (3D Meshy) |
| `client_gorynych.png` | Змей Горыныч — три головы | Pride Jazzy 614 (3D Meshy) |
| `chair_*.png` (25 файлов) | рисунки колясок — кадр 0 кадров поворота 3D-моделей (`art_from_turntable.py`); список моделей и заданий — `meshy_models/README.md` | — |

## Грабли, на которые уже наступили

- **«wheelchair game» в промпте** сажает в коляску всех подряд (даже призрака). Для
  персонажей без коляски это слово убирать, писать «floats freely, no chair».
- **Кентавра** все модели рисуют лошадью. Работает обход: сгенерировать лошадь с
  тележкой, потом правкой «замени голову и шею лошади на торс человека».
- **Ступени** модель рисует по привычке. Вечеринка и все места в игре — доступные:
  пандусы с перилами (исправлено правкой фона).
- **Фон не должен спорить с UI**: на дороге не рисуем коляску (Мартин в своей), в гараже
  пустые полки — коллекция заполняется по мере ремонтов.
- Стилевые LoRA для Flux 2 Klein на дистиллированном Klein почти не действуют при силе
  1.0 — нужна 1.5–2.

## Иконки инструментов

20 иконок `assets/tool_<id>.png` (128×128): Qwen 2.1 text-to-image, один шаблон на все,
фон — BiRefNet, `build_assets.py` обрезает по контуру и вписывает в квадрат (исходники —
`art_tests/final_v1/tools/`).

```
A single game UI icon of <предмет>, centered with generous margins, simple chunky flat
cartoon style with soft shading and a thin dark outline, matching a clean bright colorful
cartoon game, plain white background, no text, no shadow, no frame.
```

Грабли: «tire pressure gauge» модель рисует спидометром на шине — уточнять «handheld … with a
short hose and a brass valve chuck»; «spoke tension meter» — добавлять «no wheel».
