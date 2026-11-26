extends Node
## Озвучка «где я и что делать» (a11y_frame, a11y_summary, a11y_key, _a11y_focus в game.py):
##   • сменился экран или его состояние (Screen.a11y_sig) — сказать сводку экрана (новый экран — полную);
##   • «Реплики героев вслух» — новые реплики клиента, Барти, Мортимера (Screen.a11y_lines);
##   • фокус с клавиатуры/геймпада перешёл на элемент — «Группа. Подпись (k из n)» (группа — при смене группы);
##   • F2 — озвучка вкл/выкл, R — повторить сводку, T — прочитать экран, H — подсказка призрака, C — что сказал клиент.
## Сводки окон поверх экрана (справка, замечание, коды и ссылки, настройки) — здесь же, как в game.py.

var _sig: Array = []
var _group: String = ""
var _lines_seen: Dictionary = {}
var _focus_seen: Control


func _ready() -> void:
	process_priority = 900                 # после экранов, до Speech (очередь кадра — одной фразой)
	get_viewport().gui_focus_changed.connect(_on_focus)


## Окно поверх экрана: [вид, подробность] — справка, замечание, коды, настройки; [] — нет окна.
func overlay() -> Array:
	if Nav.help != null:
		return ["help", ""]
	if Nav.feedback != null:
		return ["feedback", ""]
	if Share.dlg != null:
		return ["share", Share.dlg.mode()]
	if Nav.settings != null:
		return ["settings", SettingsDialog.tab]
	return []


func state_sig() -> Array:
	var scr: Screen = Nav.current
	return [Nav.current_name, overlay(), scr.a11y_sig() if scr != null else []]


func _process(dt: float) -> void:
	_scan_tick(dt)
	if Nav.current == null:
		return
	var s := state_sig()
	if s != _sig:
		var a: Array = s[2]
		var b: Array = _sig[2] if not _sig.is_empty() else []
		var big: bool = _sig.is_empty() or s[0] != _sig[0] or s[1] != _sig[1] or a.slice(0, 1) != b.slice(0, 1)
		_sig = s
		if big:
			_group = ""
			if is_instance_valid(kb_cur) and not kb_cur in kb_items():
				kb_cur = null                   # новый экран/окно: пункта нет — «фокуса ещё не ставили» (kb.key = None)
		Speech.say(summary(big))
	if Settings.a11y.get("voices", true):           # реплики героев — вслух, в очередь
		for ln: String in Nav.current.a11y_lines():
			if ln != "" and not _lines_seen.has(ln):
				Speech.say(Loc.t(ln))
		_lines_seen.clear()
		for ln: String in Nav.current.a11y_lines():
			_lines_seen[ln] = true


## Главное о текущем экране или окне: где ты и что делать (a11y_summary).
func summary(full: bool = true) -> String:
	var ov := overlay()
	if not ov.is_empty():
		match ov[0]:
			"help":
				return Loc.t("Справка по клавишам.")
			"feedback":
				var d: Dictionary = Nav.feedback.d
				var head := Loc.t("Сообщить о неточности." if d.get("kind", "general") == "general" else "Я не согласен с игрой.")
				var extra := ""
				if d.get("expected", "") != "":
					extra = " %s: %s. %s: %s." % [Loc.t("Игра ожидала"), Loc.t(d["expected"]), Loc.t("Ты выбрал"), Loc.t(d["got"])]
				return head + extra + " " + Loc.t("Стрелки — выбрать причину, печатай комментарий, Enter — отправить, Esc — отмена.")
			"share":
				var ui: Dictionary = Share.dlg.ui
				var t: String = {"show": ui.get("title", ""), "paste": "Вставить код.", "confirm": ui.get("q", ""),
					"resume": ui.get("q", ""), "summary": "Итог задания.", "result": "Результат ученика.",
					"builder": "Ссылка-задание."}.get(ui["mode"], "")
				var extra := ""
				if ui["mode"] in ["summary", "result"]:
					var res: Dictionary = ui.get("res", {}) if ui["mode"] == "result" else Share.assign_result()
					extra = Share.result_summary(res["rows"]) + "."
				elif ui["mode"] in ["confirm", "resume"]:
					extra = Loc.t(ui.get("sub", ""))
				elif ui["mode"] == "show" and ui.get("kind") != "text":
					extra = Loc.t("Скопировано в буфер обмена.") if ui.get("ok") == true else ""
				return (Loc.t(t) + " " + extra + " " + Loc.t("Стрелки — пункты, Enter — выбрать, Esc — закрыть.")).replace("  ", " ")
			"settings":
				var tab: String = ov[1]
				if tab == "game":
					var parts: Array = []
					for x: String in Nav.settings.progress_summary():
						parts.append(Loc.t(x) + ".")
					return Loc.t("Настройки.") + " " + Loc.t("Игра.") + " " + " ".join(parts) + " " + \
						Loc.t("Tab — к вкладкам и пунктам, Esc — закрыть.")
				return Loc.t("Настройки.") + " " + Loc.t({"sound": "Звук.", "graphics": "Графика.", "access": "Доступность."}.get(tab, "")) + \
					" " + Loc.t("Tab — к вкладкам и пунктам, Esc — закрыть.")
	return Nav.current.summary_full(full) if Nav.current != null else ""


## Фокус перешёл (клавиатура, геймпад, одна кнопка): «Группа. Подпись (k из n)» (_a11y_focus).
func _on_focus(c: Control) -> void:
	if c == null or c == _focus_seen or not UI.kb_active or Speech.kind == "reader":
		_focus_seen = c                        # чтец экрана читает фокус сам (по имени элемента) — не дублируем
		return
	_focus_seen = c
	announce(c)


func announce(c: Control) -> void:
	var g := group_of(c)
	var head := ""
	if g != _group:
		head = Loc.t(g) + ". "
		_group = g
	var lst: Array = kb_items()                # «k из n» — по списку клавиатуры (как в game.py)
	if not c in lst:
		lst = focusables(root_of(c))
	var same: Array = lst.filter(func(x: Control) -> bool: return group_of(x) == g)
	var pos := (" (%s)" % _of(same.find(c) + 1, same.size())) if same.size() > 1 else ""
	Audio.sfx("tick")
	Speech.say(head + label_of(c) + pos, true)


static func _of(a: int, b: int) -> String:
	return ("%d из %d" if Loc.code == "ru" else "%d of %d") % [a, b]


static func group_of(c: Control) -> String:
	if c.has_meta("a11y_group"):
		return c.get_meta("a11y_group")
	return "Кнопки"


static func label_of(c: Control) -> String:
	var s := str(c.accessibility_name)
	if s == "" and c is GameButton:
		s = Loc.t((c as GameButton).label)
	return s


## Окно, в котором элемент: модальное окно поверх экрана или сам экран.
static func root_of(c: Control) -> Node:
	var n: Node = c
	while n != null:
		if n is ShareDialog or n is SettingsDialog or n is FeedbackDialog or n is Screen:
			return n
		n = n.get_parent()
	return c.get_parent()


## Элементы, на которые встаёт фокус, в порядке обхода (видимые, с фокусом).
static func focusables(root: Node) -> Array:
	var out: Array = []
	_collect(root, out)
	return out


static func _collect(n: Node, out: Array) -> void:
	for c in n.get_children():
		if c is Control:
			var ctl := c as Control
			if not ctl.is_visible_in_tree():
				continue
			if ctl.focus_mode == Control.FOCUS_ALL:
				out.append(ctl)
		_collect(c, out)


# ================= порядок обхода с клавиатуры (a11y_items + a11y_key в game.py) =================
## Пункты окна — ОДИН список в порядке game.py (группы по очереди: особые пункты экрана, потом «Кнопки», потом
## «Меню»; внутри группы — порядок экрана). Стрелки ↑ ← / ↓ → — предыдущий/следующий пункт с заворотом; Tab /
## Shift+Tab — первый пункт следующей/предыдущей группы (заворот); у ползунка ← → меняют значение (их ловит сам
## ползунок). kb_cur — пункт, на который клавиатура ставила фокус (kb["key"]): мышь и фокус экрана при входе его не
## трогают, как в game.py; null — «ещё не ставили»: ↓ → — первый пункт, ↑ ← — последний, Tab — первая группа.
## Порядок задаёт экран/окно: kb_order(items) (свой список) или kb_groups() (порядок особых групп); пункт с метой
## kb_skip в список не идёт (кружки деталей на коляске — в game.py их нет в a11y_items).

var kb_cur: Control


func kb_root() -> Node:
	return active_root()


func kb_items() -> Array:
	if Nav.help != null:
		return []
	var r := active_root()
	if r == null:
		return []
	var items: Array = focusables(r).filter(func(c: Control) -> bool: return not c.has_meta("kb_skip"))
	if r.has_method("kb_order"):
		return r.call("kb_order", items)
	return order_groups(items, r.call("kb_groups") if r.has_method("kb_groups") else [])


## Пункты по группам: сначала first (в этом порядке), потом прочие особые группы — в порядке первого появления,
## потом «Кнопки» (кнопки, нарисованные в кадре — _a11y_generic), потом «Меню» (настройки, флажок, язык).
static func order_groups(items: Array, first: Array = []) -> Array:
	var groups: Array = first.duplicate()
	for c: Control in items:
		var g := group_of(c)
		if not g in groups and g != "Кнопки" and g != "Меню":
			groups.append(g)
	for g: String in ["Кнопки", "Меню"]:
		if not g in groups:
			groups.append(g)
	var out: Array = []
	for g: String in groups:
		var part: Array = items.filter(func(c: Control) -> bool: return group_of(c) == g)
		if g == "Меню":                        # значки в углу — как в a11y_items: настройки, флажок, язык
			var rest := part.filter(func(c: Control) -> bool: return _menu_rank(c) < 0)
			var icons := part.filter(func(c: Control) -> bool: return _menu_rank(c) >= 0)
			icons.sort_custom(func(a: Control, b: Control) -> bool: return _menu_rank(a) < _menu_rank(b))
			part = rest + icons
		out.append_array(part)
	return out


static func _menu_rank(c: Control) -> int:
	if c is IconButton:
		return {IconButton.Kind.GEAR: 0, IconButton.Kind.FLAG: 1, IconButton.Kind.LANG: 2}.get((c as IconButton).kind, -1)
	return -1


## Окно поверх экрана (мини-игра, мануал, спека): его пункты и «◂ назад» экрана — в game.py значок рисуется после
## окна и тоже в списке, последним.
static func with_screen_back(items: Array) -> Array:
	var out := order_groups(items)
	var back: Node = Nav.current.get_node_or_null("Back") if Nav.current != null else null
	if back is Control and (back as Control).is_visible_in_tree():
		var bc := back as Control
		if bc.has_meta("_focus_mode"):          # экран под окном выключил фокус (UI.set_focus_enabled) — «назад» в списке
			bc.focus_mode = bc.get_meta("_focus_mode")
			bc.remove_meta("_focus_mode")
		if bc.focus_mode != Control.FOCUS_NONE:
			out.append(bc)
	return out


## Пересборка окна или экрана root: пункт клавиатуры (kb_cur) запоминается путём от root и после сборки ставится на
## новый узел с тем же путём (в game.py ключ пункта — строка, он переживает пересборку). Пустой путь — kb_cur не в root.
func kb_save(root: Node) -> NodePath:
	if is_instance_valid(kb_cur) and root.is_ancestor_of(kb_cur):
		return root.get_path_to(kb_cur)
	return NodePath()


func kb_restore(root: Node, path: NodePath) -> void:
	if path.is_empty() or not root.has_node(path):
		return
	var n := root.get_node(path)
	if n is Control:
		kb_cur = n as Control


func kb_index(items: Array) -> int:
	return items.find(kb_cur) if is_instance_valid(kb_cur) else -1


## Стрелки и Tab (a11y_key в game.py). true — обработано (дальше событие не идёт: свой обход Godot не нужен).
func nav_key(k: InputEventKey) -> bool:
	if not k.pressed or k.ctrl_pressed or k.alt_pressed or k.meta_pressed or Nav.help != null:
		return false
	var code := k.keycode
	if not code in [KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_TAB]:
		return false
	if code in [KEY_UP, KEY_DOWN] and Nav.current_name == "credits" and overlay().is_empty():
		return false                           # титры листаются ↑ ↓ (handle_credits_event)
	var fo := get_viewport().gui_get_focus_owner()
	if code in [KEY_LEFT, KEY_RIGHT] and fo != null and is_slider(fo):
		return false                           # ползунок: ← → — значение (cur["adj"])
	if code in [KEY_LEFT, KEY_RIGHT] and fo is ChairView:
		return false                           # фокус на коляске (щёлкнули по ней): ← → — повернуть, как в её подписи
	var items := kb_items()
	if items.is_empty():
		return false
	UI.kb_active = true
	var idx := kb_index(items)
	var n := items.size()
	if code == KEY_TAB:
		var groups: Array = []
		for c: Control in items:
			if not group_of(c) in groups:
				groups.append(group_of(c))
		var g: int = groups.find(group_of(items[idx])) if idx >= 0 else -1
		g = posmod(g + (-1 if k.shift_pressed else 1), groups.size())
		for c: Control in items:
			if group_of(c) == groups[g]:
				kb_focus(c)
				break
		return true
	var d := -1 if code in [KEY_UP, KEY_LEFT] else 1
	var i := posmod((idx if idx >= 0 else (-1 if d > 0 else 0)) + d, n)
	kb_focus(items[i])
	return true


## Поставить фокус клавиатуры на пункт (_a11y_focus): фокус Godot настоящий (чтец экрана читает его сам), фраза
## «Группа. Подпись (k из n)» — из _on_focus; если фокус уже там (экран поставил его при входе) — сказать сразу.
func kb_focus(c: Control) -> void:
	kb_cur = c
	if c.has_focus():
		if Speech.kind != "reader":
			announce(c)
		c.queue_redraw()
	else:
		c.grab_focus()


## Enter/Пробел нажали на пункте с фокусом — он и есть пункт клавиатуры (в game.py Enter жмёт kb["key"]).
func kb_pressed(c: Control) -> void:
	if c != null and c in kb_items():
		kb_cur = c


## Клавиши озвучки (a11y_key): F2, R, T, H, C. true — обработано.
func key(k: InputEventKey) -> bool:
	if k.echo:
		return false
	if k.keycode == KEY_F2:
		toggle_speech()
		return true
	if k.keycode == KEY_F3 and SCAN_ENABLED:
		toggle_scan()
		return true
	var typing := Nav.feedback != null or (Share.dlg != null and Share.dlg.field_key() != "")
	if typing or k.ctrl_pressed or k.alt_pressed:
		return false
	match k.keycode:
		KEY_R:
			Speech.say(summary(true), true)
			return true
		KEY_T:
			Speech.say(screen_text(), true)
			return true
		KEY_H:
			var line: String = Nav.current.hint_line() if Nav.current != null and Nav.current_name in ["job", "tech"] else ""
			Speech.say(Loc.t(line) if line != "" else Loc.t("Подсказки сейчас нет."), true)
			return true
		KEY_C:
			var cl: String = Nav.current.client_now() if Nav.current != null else ""
			Speech.say(Loc.t(cl) if cl != "" else Loc.t("Клиент пока молчит."), true)
			return true
	return false


## F2: озвучка вкл/выкл (toggle_speech).
func toggle_speech() -> void:
	Settings.a11y["speech_set"] = true
	if Settings.a11y.get("on", false):
		Speech.say_now(Loc.t("Озвучка выключена. F2 — включить."), true)
		Settings.set_a11y("on", false)
	else:
		Settings.set_a11y("on", true)
		Speech.init()
		if Speech.kind == "":
			Nav.flash("Озвучка недоступна на этом компьютере.", UI.AMBER, 3.0)
		else:
			_sig = []                           # сразу рассказать, где мы
			Speech.say(Loc.t("Озвучка включена.") + " " + Loc.t("F1 — справка по клавишам."), true)


## T — весь экран: сводка и подписи элементов окна (a11y_screen_text — по тому, что нарисовано).
func screen_text() -> String:
	var root: Node = Nav.current
	var ov := overlay()
	if not ov.is_empty():
		root = {"help": Nav.help, "feedback": Nav.feedback, "share": Share.dlg, "settings": Nav.settings}[ov[0]]
	var out: Array = [summary(true)]
	for c: Control in focusables(root):
		var l := label_of(c)
		if l != "":
			out.append(l)
	return ". ".join(out) if out.size() > 0 else Loc.t("На экране нет текста.")



# ================= одна кнопка (switch access, _scan_* в game.py) =================
## Пункты окна выделяются сами по очереди (через 1 / 1,6 / 2,5 с); короткое нажатие — выбрать, держать 1,2 с —
## назад (Esc), держать 4 с — выключить режим. Кнопка — Пробел/Enter, клик или касание в любом месте, A на геймпаде.
## Ползунок: нажать — «Меньше / Больше / Готово» по очереди, нажатие — сделать выделенное.
## Как в game.py, опция в настройках скрыта (SCAN_ENABLED = False: владелец выключил «Одну кнопку» 25.10 — коллега
## в ней застревала); механизм перенесён целиком, включается Settings.a11y.scan (тесты) и F3, если опцию вернут.

const SCAN_ENABLED := false
const SCAN_SPEEDS := [1.0, 1.6, 2.5]
const SCAN_HOLD := 1.2
const SCAN_OFF_HOLD := 4.0
const SCAN_SUB := ["Меньше", "Больше", "Готово"]

var scan_t: float = 0.0
var scan_sub: Dictionary = {}              # {ctl, i} — ползунок: меньше/больше/готово
var scan_stat := {"press": 0, "hold": 0, "steps": 0}
var _scan_next: float = -1.0
var _scan_down: float = -1.0
var _frame: Control


func scan_on() -> bool:
	return int(Settings.a11y.get("scan", 0)) > 0


func scan_iv() -> float:
	return SCAN_SPEEDS[clampi(int(Settings.a11y.get("scan", 1)), 1, SCAN_SPEEDS.size()) - 1]


## Где сейчас пункты: окно поверх экрана, модальное окно экрана (мини-игра, спека, мануал, сноски) или экран.
func active_root() -> Node:
	var ov := overlay()
	if not ov.is_empty():
		return {"help": Nav.help, "feedback": Nav.feedback, "share": Share.dlg, "settings": Nav.settings}[ov[0]]
	var scr: Node = Nav.current
	if scr == null:
		return null
	for k: String in ["mini", "manual_dlg", "spec_dlg", "notes"]:   # мануал, открытый из спеки, — поверх неё
		var w: Variant = scr.get(k)
		if w is Control and is_instance_valid(w) and (w as Control).is_visible_in_tree():
			return w
	return scr


func scan_items() -> Array:
	return kb_items()                       # тот же список, что у стрелок (kb["items"] в game.py)


static func is_slider(c: Control) -> bool:
	return c is VolSlider or c is GapTrack or (c.has_meta("a11y_group") and c.get_meta("a11y_group") == "Ползунки")


## Следующий пункт (или следующий вариант «меньше / больше / готово» у ползунка) — scan_tick.
func scan_step() -> void:
	scan_stat["steps"] += 1
	UI.kb_active = true
	if not scan_sub.is_empty():
		if is_instance_valid(scan_sub["ctl"]) and (scan_sub["ctl"] as Control).has_focus():
			scan_sub["i"] = (int(scan_sub["i"]) + 1) % SCAN_SUB.size()
			Audio.sfx("tick")
			Speech.say(Loc.t(SCAN_SUB[scan_sub["i"]]), true)
			return
		scan_sub = {}
	var items := scan_items()
	if items.is_empty():
		return
	var i := kb_index(items)
	kb_focus(items[0 if i < 0 else (i + 1) % items.size()])


## Нажатие одной кнопки: выбрать выделенный пункт (scan_select).
func scan_select() -> void:
	var items := scan_items()
	if items.is_empty():
		return
	UI.kb_active = true
	var cur: Control = kb_cur if is_instance_valid(kb_cur) else null
	if not scan_sub.is_empty() and cur == scan_sub["ctl"]:
		if int(scan_sub["i"]) == 2:
			scan_sub = {}
			Audio.sfx("tick")
			Speech.say(Loc.t("Готово"), true)
		else:
			_adj(cur, -1 if int(scan_sub["i"]) == 0 else 1)
		return
	scan_sub = {}
	if cur == null or not cur in items:
		kb_focus(items[0])
		return
	if is_slider(cur):
		scan_sub = {"ctl": cur, "i": 1}
		Audio.sfx("tick")
		Speech.say(Loc.t("Больше") + ". " + Loc.t("Нажимай, чтобы менять. Меньше, больше, готово — по очереди."), true)
		return
	activate(cur)


## Нажать пункт (_a11y_activate): кнопка — как Enter; поле окна кодов — «применить».
func activate(c: Control) -> void:
	if c is BaseButton:
		(c as BaseButton).pressed.emit()
	elif c is ShareDialog.ShareField:
		var f := c as ShareDialog.ShareField
		f.dlg.action("apply" if f.key == "text" else "make")
	else:
		_key_to(c, KEY_ENTER)


func _adj(c: Control, d: int) -> void:
	_key_to(c, KEY_RIGHT if d > 0 else KEY_LEFT)
	Speech.say(label_of(c), true)


func _key_to(c: Control, code: Key) -> void:
	var k := InputEventKey.new()
	k.keycode = code
	k.physical_keycode = code
	k.pressed = true
	c.grab_focus()
	c._gui_input(k)


## События в режиме одной кнопки (_scan_event): true — съедено (кнопка, клик, касание).
func scan_input(e: InputEvent) -> bool:
	if not scan_on() or Nav.help != null:
		return false
	var down := false
	var up := false
	if e is InputEventKey and (e as InputEventKey).keycode in [KEY_SPACE, KEY_ENTER, KEY_KP_ENTER] and not e.is_echo():
		down = e.pressed
		up = not e.pressed
	elif e is InputEventMouseButton and (e as InputEventMouseButton).button_index == MOUSE_BUTTON_LEFT:
		down = e.pressed
		up = not e.pressed
	elif e is InputEventScreenTouch:
		down = e.pressed
		up = not e.pressed
	elif e is InputEventMouseMotion:
		return true                         # мышь фокус не сбивает
	else:
		return false
	if down:
		if _scan_down < 0:
			_scan_down = scan_t
		return true
	if up and _scan_down >= 0:
		var held := scan_t - _scan_down
		_scan_down = -1.0
		if held >= SCAN_OFF_HOLD:
			toggle_scan(false)
		elif held >= SCAN_HOLD:
			scan_stat["hold"] += 1
			scan_sub = {}
			Nav.back()
		else:
			scan_stat["press"] += 1
			scan_select()
		_scan_next = scan_t + scan_iv() * 1.5
		return true
	return true


## Режим одной кнопки вкл/выкл (toggle_scan): F3 (если опция включена) или удержание 4 с.
func toggle_scan(on: Variant = null) -> void:
	var cur := int(Settings.a11y.get("scan", 0))
	var want: bool = (cur == 0) if on == null else bool(on)
	if want and cur == 0:
		Settings.a11y["scan"] = clampi(int(Settings.a11y.get("scan_last", 1)), 1, SCAN_SPEEDS.size())
		Nav.flash("Режим одной кнопки включён. Выключить: F3 или держи кнопку 4 с.", UI.AMBER, 6.0)
	elif not want and cur > 0:
		Settings.a11y["scan_last"] = cur
		Settings.a11y["scan"] = 0
		Nav.flash("Режим одной кнопки выключен.", UI.GOOD, 4.0)
	else:
		return
	_scan_down = -1.0
	scan_sub = {}
	_scan_next = scan_t + 1.5
	Speech.say(Loc.t("Одна кнопка") + ": " + Loc.t("ВКЛ" if want else "ВЫКЛ"), true)
	Settings.save()


func _scan_tick(dt: float) -> void:
	scan_t += dt
	if _frame == null:
		var layer := CanvasLayer.new()
		layer.layer = 50
		_frame = Control.new()
		_frame.name = "ScanFrame"
		_frame.mouse_filter = Control.MOUSE_FILTER_IGNORE
		_frame.size = Vector2(UI.W, UI.H)
		_frame.draw.connect(_draw_frame)
		layer.add_child(_frame)
		get_tree().root.add_child.call_deferred(layer)
	_frame.queue_redraw()
	if not scan_on() or Nav.help != null or _scan_down >= 0:
		return
	if _scan_next < 0:
		_scan_next = scan_t + scan_iv()
	if scan_t < _scan_next:
		return
	_scan_next = scan_t + scan_iv()
	scan_step()


@warning_ignore("integer_division")
## Рамка выделенного пункта (белая с янтарной пульсацией, как в game.py) и подсказка внизу (_draw_scan).
func _draw_frame() -> void:
	if not scan_on() or Nav.help != null:
		return
	var cur := get_viewport().gui_get_focus_owner()
	if cur != null and cur.is_visible_in_tree():
		var rr := cur.get_global_rect()
		var r := rr.grow(6) if rr.size.y > 12 else rr.grow_individual(12, 15, 12, 15)
		var pulse := 0.5 + 0.5 * UI.wsin(scan_t * 5)
		UI.draw_round_rect(_frame, r.grow(5), Color(0, 0, 0, 0), Color(0, 0, 0), 3, 13)
		UI.draw_round_rect(_frame, r, Color(0, 0, 0, 0), Color(1, 1, 1), 3, 10)
		UI.draw_round_rect(_frame, r.grow(3), Color(0, 0, 0, 0), UI.AMBER, 3 + int(pulse), 12)
		if not scan_sub.is_empty() and cur == scan_sub["ctl"]:
			var w := 130
			var h := 34
			var x0 := clampi(int(rr.get_center().x) - (3 * (w + 6)) / 2, 8, UI.W - 3 * (w + 6) - 8)
			var y0 := rr.end.y + 16 if rr.end.y + 16 + h < UI.H - 30 else rr.position.y - 16 - h
			for i in 3:
				var b := Rect2(x0 + i * (w + 6), y0, w, h)
				var on := i == int(scan_sub["i"])
				UI.draw_round_rect(_frame, b, Color8(52, 44, 20) if on else Color8(20, 18, 26), UI.AMBER if on else UI.GREY,
					3 if on else 1, 8)
				UI.draw_text(_frame, ["− ", "+ ", "✓ "][i] + Loc.t(SCAN_SUB[i]), b.get_center(), 16, UI.AMBER if on else UI.WHITE, on, 1)
	var hint := Loc.t("Одна кнопка: нажми — выбрать, держи — назад · выключить: F3 или держи 4 с")
	var fw := UI.text_width(hint, 14) + 24
	var hb := Rect2(UI.W / 2.0 - int(fw / 2), UI.H - 26, int(fw), 22)
	UI.draw_round_rect(_frame, hb, Color8(12, 10, 18), Color(0, 0, 0, 0), 0, 6)
	UI.draw_text(_frame, hint, hb.get_center(), 14, UI.AMBER, false, 1)
