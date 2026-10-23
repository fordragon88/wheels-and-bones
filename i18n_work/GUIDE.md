# Translation guide: «Колёса и Кости» → "Wheels & Bones"

Educational wheelchair-repair simulator in a friendly fantasy world. Player is Martin, a kind
zombie who keeps losing his left leg; mentor is Bartholomew ("Barty"), a Victorian gentleman
ghost; Guild master is Brenna, ghost of an elderly dwarven woman mechanic. Humour is about
Martin, the ghost and fantasy absurdity — **never about disability or wheelchair users**.
Tone toward clients: warm, respectful, matter-of-fact. Repair steps are REAL procedures from
real wheelchair manuals — accuracy matters more than style.

## Output format
Write a JSON object `{ "<russian string exactly as given>": "<english>" , ... }` covering
EVERY item of your chunk, UTF-8, to the output path you were given. Keys must be
byte-identical copies of the `ru` field (including spaces, punctuation, «», \n).

## Hard rules
- `fmt: true` items contain placeholders `{0}`, `{1}`… — keep every placeholder exactly
  (same numbers); you may reorder them in the English sentence. Literal braces appear as `{{` `}}` — keep them.
- Keep length close to the original (UI space is tight). Short labels stay short.
  ALL-CAPS labels/buttons stay ALL-CAPS.
- Russian quotes «…» → English “…”. Keep ✔ ★ • … — and other symbols.
- Keep units/specs exactly (psi, В→V, мм→mm, Н·м→N·m, А→A, кг→kg, ″ stays).
- Speech lines "Имя: «…»" → "Name: “…”".
- Do not translate code identifiers; if an item is clearly an internal key, keep it as is.

## Names (fixed)
Мартин → Martin · Бартоломью → Bartholomew · Барти → Barty · Бренна / Мастерица Бренна → Brenna / Master Brenna ·
Аэлин → Aelin (elf) · Вольф → Wolf (werewolf; до 23.10.2026 на его месте был гном Дургин → Durgin) · Тилли → Tilly (fairy) ·
Гра → Gra (orc, male; talks about himself in 3rd person, short blunt words: "Gra likes quiet.") ·
Бомм → Bomm (troll; very simple speech: "Bomm sit. Bomm not fall. Bomm friend.") ·
Зикс → Zix (goblin mechanic, cheeky) · Мора → Mora (sorceress, dry wit) ·
Грунд → Grund (stone golem, speaks in CAPS: "GRUND. ROLLS. GRUND PLEASED.") ·
Тавр → Tavr (centaur courier) · Некромант Мортимер → Mortimer the Necromancer (Seating Clinic mentor, gothic-pompous but kind) · Гильдия Колёсников → the Wheelwrights' Guild ·
«Колёса и Кости» → "Wheels & Bones".
Клиенты второй волны и народных заданий (так в assets/lang_en.json): Кицунэ Юки → Yuki the Kitsune · Дриада Ивушка →
Ivushka the Dryad · Дракончик Искра → Iskra the Dragonling · Бабушка Агата → Granny Agatha · Ящерка-картограф Сайра →
Saira the Lizardfolk Cartographer · Барсучиха-пасечница Матильда → Matilda the Badger Beekeeper · Баба Яга → Baba Yaga ·
Русалка Ольга → Olga the Mermaid · Леший → Leshy · Мумия Сенеб → Seneb the Mummy (до 22.10 — Ра) · Змей Горыныч →
Zmey Gorynych · Оборотень Вольф → Wolf the Werewolf.
Эльфийка → Elf · Оборотень → Werewolf · Гном/гномка → Dwarf (Бренна) · Фея → Fairy · Орк → Orc · Тролль → Troll ·
Гоблин-механик → Goblin mechanic · Чародейка → Sorceress · Голем → Golem · Кентавр → Centaur.

## Glossary (real terminology)
инвалидная коляска / коляска → wheelchair · ручная коляска → manual wheelchair ·
электроколяска → power wheelchair · заднее колесо → rear wheel · обод → rim ·
обруч / обод-толкатель → pushrim (handrim) · спицы → spokes · ниппель (спицы) → spoke nipple ·
ниппель (камеры) → valve · покрышка → tire · камера → inner tube · кастор → caster ·
шток кастора → caster stem · вилка → fork · тормоз-замок → wheel lock · подшипник → bearing ·
ось / быстросъёмная ось (QR) → axle / quick-release (QR) axle · ступица → hub ·
подножка → footrest · сиденье → seat · подушка → cushion · спинка → backrest · рама → frame ·
болты/гайки → bolts/nuts · осевая пластина → axle plate · схождение → toe / wheel alignment ·
«восьмёрка» обода → wheel wobble (out-of-true rim) · правка обода → truing ·
правочный станок → truing stand · биение → runout · индикатор (часового типа) → dial indicator ·
тензиометр → spoke tension meter · спицевой ключ → spoke wrench · шестигранник → hex key (Allen key) ·
торцевой ключ → socket wrench · разводной ключ → adjustable wrench · отвёртка → screwdriver ·
монтажка → tire lever · насос → pump · заплатка / ремкомплект → patch / patch kit ·
смазка → lubricant · щётка/пинцет → brush/tweezers · тряпка/салфетка → cloth ·
таз с водой → bowl of water · пинг-тест → ping test · манометр → pressure gauge ·
мультиметр → multimeter · зарядка → charger · рулетка → tape measure ·
контроллер → controller · джойстик → joystick · пыльник → (joystick) boot ·
батарея → battery · предохранитель / автомат → fuse / circuit breaker ·
разъём → connector · проводка → wiring · мотор → motor ·
рычаг расцепления / свободный ход → freewheel lever / freewheel mode ·
флаттер / кастор бьёт → caster flutter · люфт → play (looseness) ·
техника безопасности (ТБ) → safety rules · мануал → manual · спека → spec ·
диагностика → diagnosis · осмотр → inspection · тест-драйв → test drive ·
мастерская → workshop · гараж-коллекция → garage collection · вечеринка → party ·
подмастерье → journeyman · ученик → apprentice · техник → technician.
