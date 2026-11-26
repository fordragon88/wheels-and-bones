extends Node
## Смена экранов: Nav.go("hub") / Nav.go("job", {"job": "flat"}); «назад» — Nav.back() (решает сам экран, как Esc
## в game.py); короткий переход — прошлый кадр растворяется 0,35 с (без анимации — сразу). Здесь же общее для всех
## экранов: сообщение сверху (Nav.flash), окно настроек, глобальные клавиши (Esc, M, F11), рамка фокуса
## только после клавиатуры/геймпада (UI.kb_active).

signal screen_changed(name: String)

const SCREENS := {
	"title": "res://screens/title.tscn",
	"hub": "res://screens/hub.tscn",
	"job": "res://screens/job.tscn",
	"result": "res://screens/result.tscn",
	"intro": "res://screens/intro.tscn",
	"garage": "res://screens/garage.tscn",
	"ending": "res://screens/ending.tscn",
	"credits": "res://screens/credits.tscn",
	"guild": "res://screens/guild.tscn",
	"tech": "res://screens/tech.tscn",
	"failed": "res://screens/failed.tscn",
	"exam_result": "res://screens/exam_result.tscn",
	"seating": "res://screens/seating.tscn",
}
const FALLBACK := {}

var current: Screen
var current_name: String = ""
var params: Dictionary = {}
var history: Array = []                   # [[имя, параметры]] — откуда пришли
var test_mode: bool = false
var hub_page: int = 0                     # страница очереди мастерской (game.py self.hub_page) — переживает экран
var garage_page: int = 0                  # страница гаража (game.py self.garage_page)
var host: Control                         # здесь живёт текущий экран
var overlay: CanvasLayer                  # поверх: сообщение, настройки, переход
var toast: Toast
var settings: SettingsDialog
var feedback: FeedbackDialog
var help: HelpOverlay
var _fade: TextureRect
var _fade_t: float = -1.0
var _snapping := false                    # Nav._input: идёт повтор нажатия в перенесённой точке (запас пальца)
var _esc_t: float = 0.0
var _touch_as_mouse: bool = bool(ProjectSettings.get_setting("input_devices/pointing/emulate_mouse_from_touch", true))
var _emu_press := false                   # Nav._input: было нажатие эмулированной мыши, его касание ещё не пришло
var support_opened: int = 0              # сколько раз нажали «Поддержать» (тесты)                   # «ещё раз Esc — выйти»


func _ready() -> void:
	test_mode = OS.get_cmdline_user_args().has("--test")
	process_mode = Node.PROCESS_MODE_ALWAYS
	Input.joy_connection_changed.connect(_on_pad_connection)
	host = Control.new()
	host.name = "ScreenHost"
	host.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	host.mouse_filter = Control.MOUSE_FILTER_IGNORE
	host.auto_translate_mode = Node.AUTO_TRANSLATE_MODE_DISABLED   # перевод — свой (Loc), не TranslationServer
	overlay = CanvasLayer.new()
	overlay.name = "Overlay"
	overlay.layer = 10
	var top := Control.new()
	top.name = "Top"
	top.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	top.mouse_filter = Control.MOUSE_FILTER_IGNORE
	top.auto_translate_mode = Node.AUTO_TRANSLATE_MODE_DISABLED
	overlay.add_child(top)
	toast = Toast.new()
	toast.name = "Toast"
	top.add_child(toast)
	_fade = TextureRect.new()
	_fade.name = "Fade"
	_fade.size = Vector2(UI.W, UI.H)
	_fade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_fade.visible = false
	top.add_child(_fade)
	get_tree().root.add_child.call_deferred(host)
	get_tree().root.add_child.call_deferred(overlay)
	DisplayServer.window_set_title(Loc.window_title())


func go(name: String, p: Dictionary = {}, remember: bool = true) -> void:
	if not SCREENS.has(name):
		name = FALLBACK.get(name, "hub")
	if current != null and remember:
		history.append([current_name, params])
		if history.size() > 20:
			history.pop_front()
	_snapshot()
	if current != null:
		host.remove_child(current)
		current.queue_free()
	close_settings()
	toast.on_input()                       # итог хода прошлого экрана не висит на новом
	params = p
	current_name = name
	if Frames.net:
		Frames.retry_failed()                  # браузер: кадры, не пришедшие из-за сети, — ещё раз (сеть могла вернуться)
	var scene := load(SCREENS[name]) as PackedScene
	current = scene.instantiate() as Screen
	current.params = p
	current.screen_name = name
	host.add_child(current)
	sync_focus(null, false)                    # окно поверх нового экрана (итог задания) — фокус у окна, не у экрана
	if Share.dlg != null:
		UI.focus_later(Share.dlg.first_focus())
	Audio.scene(name, current.music_theme())
	_esc_t = 0.0
	screen_changed.emit(name)                 # сводку экрана говорит A11y (как a11y_frame: «новый экран»)


func back() -> void:
	if help != null:
		toggle_help()
		return
	if feedback != null:
		feedback.close()
		return
	if Share.dlg != null:
		Share.dlg.escape()
		return
	if settings != null:
		close_settings()
		return
	if current != null:
		current.go_back()


## Предыдущий экран из истории (или титул).
func pop() -> void:
	if history.is_empty():
		go("title", {}, false)
		return
	var h: Array = history.pop_back()
	go(h[0], h[1], false)


## Растворение прошлого кадра (как _fade_from в game.py).
func _snapshot() -> void:
	if current == null or Settings.calm() or DisplayServer.get_name() == "headless":
		return
	var img := get_viewport().get_texture().get_image()
	if img == null or img.is_empty():
		return
	_fade.texture = ImageTexture.create_from_image(img)
	_fade.size = Vector2(UI.W, UI.H)
	_fade.visible = true
	_fade.modulate.a = 1.0
	_fade_t = 0.0
	Audio.sfx("whoosh")


func flash(text: String, color: Color = UI.WHITE, secs: float = 3.0, sticky: bool = false) -> void:
	toast.bounds = UI.phone_bounds(current.toast_bounds() if current != null else Vector2(8, 56))
	toast.show_msg(text, color, secs, sticky)
	Speech.say(Loc.t(text), true)


func open_settings() -> void:
	if settings != null:
		return
	settings = SettingsDialog.new()
	settings.closed.connect(_on_settings_closed)
	_remember_focus(settings)
	overlay.get_node("Top").add_child(settings)
	overlay.get_node("Top").move_child(toast, -1)
	sync_focus(settings.first_focus())


## Окно замечания: d — что за замечание (kind general — флажок ⚑, иначе — «Я не согласен» с ошибкой);
## on_done(sent, online) — после закрытия. Снимок экрана — до открытия окна.
func open_feedback(d: Dictionary, on_done: Callable = Callable()) -> void:
	if feedback != null:
		return
	var shot: Image = null
	if DisplayServer.get_name() != "headless":
		shot = get_viewport().get_texture().get_image()
	feedback = FeedbackDialog.make(d, shot)
	var fb := feedback
	feedback.closed.connect(func(sent: bool, online: bool) -> void:
		if feedback != fb:                     # второй send()/close() того же окна в одном кадре — уже закрыто
			return
		feedback = null
		_restore_focus(fb)
		if sent and d.get("kind", "general") == "general":
			flash("Спасибо! Замечание отправляется разработчикам." if online else
				"Спасибо! Замечание сохранено — его проверят и поправят игру.", UI.GOOD, 5.0)
		if on_done.is_valid():
			on_done.call(sent, online))
	_remember_focus(feedback)
	overlay.get_node("Top").add_child(feedback)
	overlay.get_node("Top").move_child(toast, -1)
	sync_focus(null, false)                    # фокус ставит само окно (первая причина)
	Audio.sfx("tick")


## Флажок ⚑: замечание о любой неточности на текущем экране.
func open_flag() -> void:
	var d: Dictionary = current.feedback_context() if current != null else {}
	open_feedback(d)


## F1 — справка по клавишам (модально; Esc или F1 — закрыть).
func toggle_help() -> void:
	if help != null:
		var h := help
		h.queue_free()
		help = null
		_restore_focus(h)                       # фокус — тому окну, что под справкой (настройки, замечание…), не экрану
		Speech.say(Loc.t("Справка закрыта."), true)
		return
	var keys: Array = []                       # справка вслух — все клавиши (toggle_help в game.py)
	for kv: Array in Content.consts.get("help_keys", []):
		keys.append("%s: %s." % [Loc.t(kv[0]), Loc.t(kv[1])])
	Speech.say(Loc.t("Клавиши.") + " " + " ".join(keys) + " " + Loc.t("Esc — закрыть справку."), true)
	help = HelpOverlay.new()
	_remember_focus(help)
	overlay.get_node("Top").add_child(help)
	sync_focus()


## Модальное окно поверх экрана (и поверх настроек): окно кодов и ссылок.
func show_modal(c: Control) -> void:
	_remember_focus(c)
	overlay.get_node("Top").add_child(c)
	overlay.get_node("Top").move_child(toast, -1)
	sync_focus(c.call("first_focus") if c.has_method("first_focus") else null)


func hide_modal(c: Control) -> void:
	if c.get_parent():
		c.get_parent().remove_child(c)
	c.queue_free()
	_restore_focus(c)


func close_settings() -> void:
	if settings != null:
		settings.close()


func _on_settings_closed() -> void:
	var s := settings
	settings = null
	_restore_focus(s)


# ================= слои окон и фокус (один диспетчер на все окна) =================
## Сверху вниз: справка F1 > замечание > окно кодов и ссылок > настройки > окно экрана (мини-игра, мануал, спека,
## сноски, карточка гаража — Screen.modal()) > сам экран. Фокус Godot (Tab, Enter, чтец экрана) — только у верхнего
## слоя, у нижних выключен (UI.set_focus_enabled). sync_focus зовут при открытии и закрытии любого окна и в конце
## пересборки экрана (Screen.rebuild): пересобранный под окном экран не забирает фокус (E7), закрытое окно отдаёт
## фокус следующему открытому, а не экрану (E9). Как в game.py: там модальное окно просто ловит ввод первым.
var _focus_before: Dictionary = {}           # id окна → элемент, у которого был фокус до его открытия


## Верхний слой: окно поверх экрана, окно экрана или сам экран (null — экрана ещё нет).
func top_layer() -> Node:
	for w: Variant in [help, feedback, Share.dlg, settings]:
		if w != null and is_instance_valid(w) and (w as Node).is_inside_tree():
			return w
	if current == null or not is_instance_valid(current):
		return null
	var m := current.modal()
	return m if m != null else current


## Фокус только у верхнего слоя. want — куда поставить фокус (если он в верхнем слое); иначе (fallback) — фокус
## остаётся, где был, если он в верхнем слое, а нет — первый пункт верхнего слоя. Справка своих пунктов не имеет.
func sync_focus(want: Control = null, fallback: bool = true) -> void:
	var top := top_layer()
	for w: Variant in [feedback, Share.dlg, settings]:
		if w != null and is_instance_valid(w):
			UI.set_focus_enabled(w, w == top)
	if current != null and is_instance_valid(current):
		if top == current or (top != null and current.is_ancestor_of(top)):
			current.apply_focus()
		else:
			UI.set_focus_enabled(host, false)
	if top == null or top == help:
		return
	if want != null and is_instance_valid(want) and (want == top or top.is_ancestor_of(want)):
		UI.focus_later(want)
		return
	if not fallback:
		return
	var fo := get_viewport().gui_get_focus_owner()
	if fo != null and top.is_ancestor_of(fo):
		return
	UI.focus_later(_first_focus_of(top))


static func _first_focus_of(n: Node) -> Control:
	return n.call("first_focus") as Control if n.has_method("first_focus") else null


## Окно открывается: запомнить, у кого был фокус (вернуть ему при закрытии).
func _remember_focus(w: Node) -> void:
	_focus_before[w.get_instance_id()] = get_viewport().gui_get_focus_owner()


## Окно закрылось: фокус — тому, у кого он был до окна (если он в новом верхнем слое), или пункту клавиатуры, или
## первому пункту верхнего слоя.
func _restore_focus(w: Node) -> void:
	var prev: Variant = _focus_before.get(w.get_instance_id() if w != null else 0)
	_focus_before.erase(w.get_instance_id() if w != null else 0)
	var want: Control = prev as Control if is_instance_valid(prev) else null
	if want == null and is_instance_valid(A11y.kb_cur):
		want = A11y.kb_cur
	var top := top_layer()
	if want != null and top != null and not (want == top or top.is_ancestor_of(want)):
		want = null
	sync_focus(want if want != null else (_first_focus_of(top) if top != null else null))


func _process(dt: float) -> void:
	_pad_t += dt
	if _pad_dir != 0 and _pad_t >= _pad_next:      # держат крестовину/стик — повтор стрелки
		_pad_next = _pad_t + PAD_REPEAT[1]
		_pad_key(_pad_dir)
	if _fade_t >= 0.0:
		_fade_t += dt
		var k := _fade_t / 0.35
		if k >= 1.0:
			_fade.visible = false
			_fade.texture = null
			_fade_t = -1.0
		else:
			_fade.modulate.a = 1.0 - UI.ease_out(k)
	if _esc_t > 0.0:
		_esc_t -= dt
	if current != null:
		toast.bounds = UI.phone_bounds(current.toast_bounds())
	# потолок крупного текста 125 % (text_cap в game.py): плотные экраны, окно настроек, окно мини-игры
	var cap: float = current.text_cap() if current != null else 0.0
	if settings != null or Share.dlg != null or (current != null and current.get("mini") != null):
		cap = 1.25
	if cap != Settings.text_cap:              # подписи кнопок рисуются один раз — перерисовать всё новым размером
		Settings.text_cap = cap
		get_tree().root.propagate_call("queue_redraw")


## Геймпад (pad_action в game.py): кнопки → клавиши управления с клавиатуры. Крестовина и левый стик — стрелки
## (держишь — повтор через 0,42 с, потом каждые 0,13 с), A — Enter, B — Esc, X — H (подсказка), Y — R (где я),
## LB/RB — Shift+Tab/Tab (группы), Back — F1 (справка), Start — настройки (открыты — закрыть).
const PAD_KEYS := {JOY_BUTTON_A: KEY_ENTER, JOY_BUTTON_B: KEY_ESCAPE, JOY_BUTTON_X: KEY_H, JOY_BUTTON_Y: KEY_R,
	JOY_BUTTON_BACK: KEY_F1, JOY_BUTTON_DPAD_UP: KEY_UP, JOY_BUTTON_DPAD_DOWN: KEY_DOWN,
	JOY_BUTTON_DPAD_LEFT: KEY_LEFT, JOY_BUTTON_DPAD_RIGHT: KEY_RIGHT}
const PAD_REPEAT := [0.42, 0.13]
var pad_presses: int = 0                     # нажатий кнопок геймпада (тесты)
var _pad_dir: int = 0                        # клавиша-стрелка, которую держат, или 0
var _pad_next: float = 0.0
var _pad_t: float = 0.0
var _stick: Vector2 = Vector2.ZERO


## Геймпад подключили / отключили посреди игры (JOYDEVICEADDED/REMOVED в game.py): подключили — подсказка, как
## game.py pad_action("added"); отключили, держа крестовину или стик, — повтор стрелки останавливается (PAD["dir"] =
## None): Godot при отключении молча забывает нажатые кнопки, отпускания не присылает — стрелка повторялась бы вечно.
func _on_pad_connection(_device: int, connected: bool) -> void:
	if connected:
		if current != null:
			flash("Геймпад подключён: крестовина — пункты, A — выбрать, B — назад, Start — настройки.", UI.GOOD, 4.0)
	else:
		_pad_dir = 0
		_stick = Vector2.ZERO


func _pad_key(code: Key, down: bool = true, shift: bool = false) -> void:
	var k := InputEventKey.new()
	k.keycode = code
	k.physical_keycode = code
	k.shift_pressed = shift
	k.pressed = down
	get_viewport().push_input.call_deferred(k)   # не изнутри разбора события геймпада (иначе клавиша «поглощается»)


func _pad(e: InputEvent) -> bool:
	if e is InputEventJoypadButton:
		var b := e as InputEventJoypadButton
		if b.pressed:
			pad_presses += 1
		match b.button_index:
			JOY_BUTTON_LEFT_SHOULDER, JOY_BUTTON_RIGHT_SHOULDER:
				if b.pressed:
					_pad_key(KEY_TAB, true, b.button_index == JOY_BUTTON_LEFT_SHOULDER)
					_pad_key(KEY_TAB, false, b.button_index == JOY_BUTTON_LEFT_SHOULDER)
			JOY_BUTTON_START:
				if b.pressed:                       # закрыть — только когда настройки сверху (не под справкой/окном)
					if settings != null:
						if top_layer() == settings:
							close_settings()
					elif feedback == null and Share.dlg == null and help == null:
						open_settings()
			_:
				if not PAD_KEYS.has(b.button_index):
					return true
				var code: Key = PAD_KEYS[b.button_index]
				if code in [KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT]:
					if b.pressed:
						_pad_dir = code
						_pad_next = _pad_t + PAD_REPEAT[0]
					elif _pad_dir == code:
						_pad_dir = 0
				_pad_key(code, b.pressed)
		return true
	if e is InputEventJoypadMotion:
		var m := e as InputEventJoypadMotion
		if m.axis == JOY_AXIS_LEFT_X:
			_stick.x = m.axis_value
		elif m.axis == JOY_AXIS_LEFT_Y:
			_stick.y = m.axis_value
		else:
			return true
		var code: Key = 0 as Key
		if absf(_stick.x) > 0.5 and absf(_stick.x) >= absf(_stick.y):
			code = KEY_RIGHT if _stick.x > 0 else KEY_LEFT
		elif absf(_stick.y) > 0.5:
			code = KEY_DOWN if _stick.y > 0 else KEY_UP
		if code != _pad_dir:
			_pad_dir = code
			if code != 0:
				pad_presses += 1
				_pad_next = _pad_t + PAD_REPEAT[0]
				_pad_key(code)
		return true
	return false


func _input(e: InputEvent) -> void:
	if e is InputEventMouseButton and e.pressed and e.device == InputEvent.DEVICE_ID_EMULATION:
		_emu_press = true                      # нажатие пальца пришло мышью — само касание придёт следом
	var as_mouse := false                      # это касание уже пришло нажатием мыши (и уже погасило итог хода)
	if e is InputEventScreenTouch and e.is_pressed():
		as_mouse = _emu_press
		_emu_press = false
	if A11y.scan_input(e):                     # одна кнопка: нажатие — выбрать, держать — назад
		if not UI.kb_active:
			UI.kb_active = true
		get_viewport().set_input_as_handled()
		return
	if (e is InputEventScreenTouch or e is InputEventScreenDrag) and _touch_as_mouse:
		# касание уже пришло событием мыши (emulate_mouse_from_touch) — само касание интерфейсу не отдаём: кнопки
		# Godot 4.7 нажимаются и им, одно касание давало ДВА нажатия (браузер на телефоне: «начать» → мастерская →
		# сразу карточка под пальцем)
		# Итог хода гасит нажатие мыши (ниже, ДО действия кнопки, как _toast_input в game.py). Godot шлёт
		# эмулированную мышь РАНЬШЕ самого касания (Input::_parse_input_event_impl): гасить ещё и здесь — значит
		# погасить итог, который кнопка только что показала (на телефоне он исчезал через 0,3 с). Гасим касанием
		# только второй и следующие пальцы — для них мышь не эмулируется.
		if e is InputEventScreenTouch and e.is_pressed() and not as_mouse:
			toast.on_input()
		get_viewport().set_input_as_handled()
		return
	if e is InputEventMouseButton and e.pressed and e.button_index == MOUSE_BUTTON_LEFT and not _snapping and UI.touch():
		# палец чуть мимо цели — нажатие переносится в её центр (_touch_snap в game.py). Godot выбирает кнопку по
		# «мыши над» (посчитано до _input по старой точке), поэтому не правим событие, а шлём заново: движение в
		# новую точку и нажатие там; исходное нажатие гасим. Отпускание придёт к той же кнопке (фокус мыши).
		# С мышью сюда не попадаем.
		var mb := e as InputEventMouseButton
		var q := touch_snap(mb.position)
		if q != mb.position:
			_snapping = true
			var mm := InputEventMouseMotion.new()
			mm.position = q
			mm.global_position = q
			get_viewport().push_input(mm, true)
			var nb := mb.duplicate() as InputEventMouseButton
			nb.position = q
			nb.global_position = q
			get_viewport().push_input(nb, true)
			_snapping = false
			get_viewport().set_input_as_handled()
			return
	if e is InputEventJoypadButton or e is InputEventJoypadMotion:
		var n0 := pad_presses
		if _pad(e):
			# режим клавиатуры — только когда геймпад что-то нажал (кнопка, стик за мёртвой зоной 0,5): дрожь стика
			# в покое и правый стик рамку фокуса не включают (pad_actions в game.py дают для них [])
			if pad_presses != n0 and not UI.kb_active:
				UI.kb_active = true
				_redraw_focus()
			get_viewport().set_input_as_handled()
			return
	if e is InputEventMouseMotion:
		if UI.kb_active:
			UI.kb_active = false
			_redraw_focus()
	elif (e is InputEventKey and e.pressed) or (e is InputEventJoypadButton and e.pressed):
		if not UI.kb_active:
			UI.kb_active = true
			_redraw_focus()
	if (e is InputEventKey or is_click(e) or e is InputEventScreenTouch or e is InputEventJoypadButton) \
			and e.is_pressed() and not e.is_echo():
		toast.on_input()                       # колёсико (зум коляски) итог хода не гасит — как _toast_input game.py
	if e is InputEventKey and e.is_pressed():   # стрелки и Tab — по списку пунктов game.py (A11y.kb_items)
		var k := e as InputEventKey
		if A11y.nav_key(k):
			get_viewport().set_input_as_handled()
		elif k.keycode in [KEY_ENTER, KEY_KP_ENTER, KEY_SPACE] and not k.echo:
			A11y.kb_pressed(get_viewport().gui_get_focus_owner())


## _touch_snap game.py для текущего окна/экрана: цели — видимые кнопки области Screen.touch_scope() (или окна
## настроек), кроме помеченных UI.touch_skip; зоны без переноса — UI.touch_block (с запасом touch_grow), кнопки
## не-цели (по их зоне попадания — кружки деталей, «+/−», значки шапки шире пальца) и значки шапки экрана поверх
## окна задания (Game._tap идёт раньше click_job). Справка F1, замечание, окно кодов — без переноса.
func touch_snap(p: Vector2, on: bool = UI.touch()) -> Vector2:
	if not on or help != null or feedback != null or Share.dlg != null:
		return p
	var scope: Control = settings if settings != null else (current.touch_scope() if current != null else null)
	if scope == null or not scope.is_visible_in_tree():
		return p
	var targets: Array = []
	var block: Array = []
	var corner: Variant = null
	for n: Node in [scope] + scope.find_children("*", "Control", true, false):
		var c := n as Control
		if c == null or not c.is_visible_in_tree() or c.mouse_filter == Control.MOUSE_FILTER_IGNORE:
			continue
		if c.is_in_group("touch_block"):
			var g: Vector2 = c.get_meta("touch_grow", Vector2.ZERO)
			block.append(c if g == Vector2.ZERO else c.get_global_rect().grow_individual(g.x, g.y, g.x, g.y))
		elif c is BaseButton:
			if c.get_meta("touch_skip", false):
				block.append(c)
			else:
				targets.append(c.get_global_rect())
				# круглая кнопка (спица, GameButton.hit_circle): угол её квадрата — не мимо, а «почти попал»: в центр
				# (обзор 26.11, E17 — 21 % квадрата 56×56 не нажимал ничего, а точка снаружи квадрата переносилась)
				if corner == null and c.get("hit_circle") == true and c.get_global_rect().has_point(p) and not UI.hits(c, p):
					corner = c.get_global_rect().get_center()
	if corner != null:
		return corner
	if settings == null and scope != current:
		for c: Node in current.get_children():
			if c is BaseButton and (c as Control).is_visible_in_tree() and c.get_meta("touch_skip", false):
				block.append(c)
	return UI.touch_snap(p, targets, block, true)


## Нажатие кнопки мыши 1–3 (левая, правая, средняя): колёсико — не «игрок что-то нажал» (MOUSEBUTTONDOWN с
## button 1–3 в _toast_input game.py; окна замечания и карточка гаража там закрываются только левой).
static func is_click(e: InputEvent) -> bool:
	return e is InputEventMouseButton and (e as InputEventMouseButton).button_index in \
		[MOUSE_BUTTON_LEFT, MOUSE_BUTTON_RIGHT, MOUSE_BUTTON_MIDDLE]


func _redraw_focus() -> void:
	var f := get_viewport().gui_get_focus_owner()
	if f:
		f.queue_redraw()


func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventKey and e.pressed:
		var k := e as InputEventKey
		if k.keycode == KEY_F1 and not k.echo:
			toggle_help()
			get_viewport().set_input_as_handled()
			return
		# окна поверх экрана — как a11y_key game.py: F2 работает везде; R/T/H/C — кроме справки и полей ввода
		# (A11y.key сам смотрит, печатают ли в поле); F11/Alt+Enter — весь экран (в справке Alt+Enter — это Enter)
		if help != null:
			if k.keycode in [KEY_ESCAPE, KEY_ENTER, KEY_KP_ENTER, KEY_SPACE] and not k.echo:
				toggle_help()                      # справку закрывают Esc, Enter, пробел (и A геймпада — это Enter)
			elif k.keycode == KEY_F2 and not k.echo:
				A11y.toggle_speech()
			elif k.keycode == KEY_F11:
				_toggle_fullscreen()
			get_viewport().set_input_as_handled()
			return
		if feedback != null:
			if k.keycode == KEY_ESCAPE:
				feedback.close()
			elif not A11y.key(k) and not _fullscreen_key(k):
				return
			get_viewport().set_input_as_handled()
			return
		if Share.dlg != null:
			if k.keycode == KEY_ESCAPE:
				if not k.echo:
					Share.dlg.escape()
			elif not A11y.key(k) and not _fullscreen_key(k):
				return
			get_viewport().set_input_as_handled()
			return
		if settings != null:
			if k.keycode == KEY_ESCAPE:
				if not k.echo:
					settings.escape()
			elif k.keycode == KEY_M:              # как game.py: M работает и при открытых настройках
				if not k.echo:
					_toggle_sound_key()
			elif not A11y.key(k) and not _fullscreen_key(k):
				return
			get_viewport().set_input_as_handled()
			return
		if A11y.key(k):
			get_viewport().set_input_as_handled()
			return
		if current != null and current.handle_key(k):
			get_viewport().set_input_as_handled()
			return
		match k.keycode:
			KEY_ESCAPE:
				if not k.echo:
					back()
				get_viewport().set_input_as_handled()
			KEY_M:
				if not k.echo:
					_toggle_sound_key()
				get_viewport().set_input_as_handled()
			KEY_F11, KEY_ENTER, KEY_KP_ENTER:
				if _fullscreen_key(k):
					get_viewport().set_input_as_handled()
	elif e is InputEventJoypadButton and e.pressed and (e as InputEventJoypadButton).button_index == JOY_BUTTON_B:
		back()                                     # (геймпад переводится в клавиши в _input — сюда не доходит)
		get_viewport().set_input_as_handled()


func _toggle_sound_key() -> void:
	var on := Audio.toggle_sound()
	flash("Звук включён" if on else "Звук выключен (M — включить)", UI.GHOST, 1.8)


## F11 или Alt+Enter — весь экран / в окне. true — это была она.
func _fullscreen_key(k: InputEventKey) -> bool:
	if k.keycode == KEY_F11 or (k.keycode in [KEY_ENTER, KEY_KP_ENTER] and k.alt_pressed):
		if not k.echo:
			_toggle_fullscreen()
		return true
	return false


var fullscreen_toggles: int = 0              # сколько раз переключали весь экран (тесты: там окно не трогаем)


func _toggle_fullscreen() -> void:
	fullscreen_toggles += 1
	if test_mode:
		return
	# браузер: полный экран можно включить только из обработчика нажатия — Godot сам вызывает это внутри события
	# страницы (кнопка настроек, F11 на холсте); иначе браузер молча откажет
	var fs := DisplayServer.window_get_mode() == DisplayServer.WINDOW_MODE_FULLSCREEN
	DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED if fs else DisplayServer.WINDOW_MODE_FULLSCREEN)


## Прибрать перед выходом (тесты, снимки, выход из игры): потоки кадров, звук, экран, кэши шрифтов.
func shutdown() -> void:
	Frames.wait_tasks()
	for key: String in Frames.loaded_keys():
		Frames.release(key)
	Audio.stop_all()
	close_settings()
	if current != null:
		current.queue_free()
		current = null
	UI.clear_font_cache()
	UI._glow_tex = null


## «Поддержать GOAT ♥»: страница пожертвований в браузере (в тестах не открывается).
func open_support() -> void:
	Audio.sfx("tick")
	support_opened += 1
	if not test_mode:
		OS.shell_open(str(Content.consts.get("support_url", "")))
	flash("Спасибо! Страница пожертвований GOAT (Zeffy) открывается в браузере.", UI.GOOD, 3.0)


## Выход из игры по второму Esc на титуле.
func quit_request() -> void:
	if _esc_t > 0.0 or OS.has_feature("web"):
		if not OS.has_feature("web"):
			shutdown()
			get_tree().quit.call_deferred()
		return
	_esc_t = Settings.esc_secs()
	flash("Ещё раз Esc — выйти из игры.", UI.AMBER, _esc_t)
