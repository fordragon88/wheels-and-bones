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
var host: Control                         # здесь живёт текущий экран
var overlay: CanvasLayer                  # поверх: сообщение, настройки, переход
var toast: Toast
var settings: SettingsDialog
var feedback: FeedbackDialog
var help: HelpOverlay
var _fade: TextureRect
var _fade_t: float = -1.0
var _esc_t: float = 0.0
var _touch_as_mouse: bool = bool(ProjectSettings.get_setting("input_devices/pointing/emulate_mouse_from_touch", true))
var support_opened: int = 0              # сколько раз нажали «Поддержать» (тесты)                   # «ещё раз Esc — выйти»


func _ready() -> void:
	test_mode = OS.get_cmdline_user_args().has("--test")
	process_mode = Node.PROCESS_MODE_ALWAYS
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
	var scene := load(SCREENS[name]) as PackedScene
	current = scene.instantiate() as Screen
	current.params = p
	current.screen_name = name
	host.add_child(current)
	if Share.dlg != null:                      # окно кодов поверх нового экрана (итог задания) — фокус у окна
		UI.set_focus_enabled(host, false)
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
	toast.bounds = current.toast_bounds() if current != null else Vector2(8, 56)
	toast.show_msg(text, color, secs, sticky)
	Speech.say(Loc.t(text), true)


func open_settings() -> void:
	if settings != null:
		return
	settings = SettingsDialog.new()
	settings.closed.connect(_on_settings_closed)
	UI.set_focus_enabled(host, false)
	overlay.get_node("Top").add_child(settings)
	overlay.get_node("Top").move_child(toast, -1)
	var f := settings.first_focus()
	UI.focus_later(f)


## Окно замечания: d — что за замечание (kind general — флажок ⚑, иначе — «Я не согласен» с ошибкой);
## on_done(sent, online) — после закрытия. Снимок экрана — до открытия окна.
func open_feedback(d: Dictionary, on_done: Callable = Callable()) -> void:
	if feedback != null:
		return
	var shot: Image = null
	if DisplayServer.get_name() != "headless":
		shot = get_viewport().get_texture().get_image()
	feedback = FeedbackDialog.make(d, shot)
	feedback.closed.connect(func(sent: bool, online: bool) -> void:
		feedback = null
		UI.set_focus_enabled(host, true)
		if settings == null and current != null:
			current._focus_default()
		if sent and d.get("kind", "general") == "general":
			flash("Спасибо! Замечание отправляется разработчикам." if online else
				"Спасибо! Замечание сохранено — его проверят и поправят игру.", UI.GOOD, 5.0)
		if on_done.is_valid():
			on_done.call(sent, online))
	UI.set_focus_enabled(host, false)
	overlay.get_node("Top").add_child(feedback)
	overlay.get_node("Top").move_child(toast, -1)
	Audio.sfx("tick")


## Флажок ⚑: замечание о любой неточности на текущем экране.
func open_flag() -> void:
	var d: Dictionary = current.feedback_context() if current != null else {}
	open_feedback(d)


## F1 — справка по клавишам (модально; Esc или F1 — закрыть).
func toggle_help() -> void:
	if help != null:
		help.queue_free()
		help = null
		UI.set_focus_enabled(host, true)
		if current != null:
			current._focus_default()
		Speech.say(Loc.t("Справка закрыта."), true)
		return
	var keys: Array = []                       # справка вслух — все клавиши (toggle_help в game.py)
	for kv: Array in Content.consts.get("help_keys", []):
		keys.append("%s: %s." % [Loc.t(kv[0]), Loc.t(kv[1])])
	Speech.say(Loc.t("Клавиши.") + " " + " ".join(keys) + " " + Loc.t("Esc — закрыть справку."), true)
	help = HelpOverlay.new()
	UI.set_focus_enabled(host, false)
	overlay.get_node("Top").add_child(help)


## Модальное окно поверх экрана (и поверх настроек): окно кодов и ссылок.
func show_modal(c: Control) -> void:
	UI.set_focus_enabled(host, false)
	if settings != null:
		UI.set_focus_enabled(settings, false)
	overlay.get_node("Top").add_child(c)
	overlay.get_node("Top").move_child(toast, -1)
	if c.has_method("first_focus"):
		UI.focus_later(c.call("first_focus"))


func hide_modal(c: Control) -> void:
	if c.get_parent():
		c.get_parent().remove_child(c)
	c.queue_free()
	if settings != null:
		UI.set_focus_enabled(settings, true)
		UI.focus_later(settings.first_focus())
	else:
		UI.set_focus_enabled(host, true)
		if current != null:
			current._focus_default()


func close_settings() -> void:
	if settings != null:
		settings.close()


func _on_settings_closed() -> void:
	settings = null
	UI.set_focus_enabled(host, true)
	if current != null:
		current._focus_default()


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
		toast.bounds = current.toast_bounds()
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
				if b.pressed:
					if settings != null:
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
	if A11y.scan_input(e):                     # одна кнопка: нажатие — выбрать, держать — назад
		if not UI.kb_active:
			UI.kb_active = true
		get_viewport().set_input_as_handled()
		return
	if (e is InputEventScreenTouch or e is InputEventScreenDrag) and _touch_as_mouse:
		# касание уже пришло событием мыши (emulate_mouse_from_touch) — само касание интерфейсу не отдаём: кнопки
		# Godot 4.7 нажимаются и им, одно касание давало ДВА нажатия (браузер на телефоне: «начать» → мастерская →
		# сразу карточка под пальцем)
		if e is InputEventScreenTouch and e.is_pressed():
			toast.on_input()
		get_viewport().set_input_as_handled()
		return
	if (e is InputEventJoypadButton or e is InputEventJoypadMotion) and _pad(e):
		if not UI.kb_active:
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
	if (e is InputEventKey or e is InputEventMouseButton or e is InputEventScreenTouch or e is InputEventJoypadButton) \
			and e.is_pressed() and not e.is_echo():
		toast.on_input()
	if e is InputEventKey and e.is_pressed():   # стрелки и Tab — по списку пунктов game.py (A11y.kb_items)
		var k := e as InputEventKey
		if A11y.nav_key(k):
			get_viewport().set_input_as_handled()
		elif k.keycode in [KEY_ENTER, KEY_KP_ENTER, KEY_SPACE] and not k.echo:
			A11y.kb_pressed(get_viewport().gui_get_focus_owner())


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
		if help != null:
			if k.keycode == KEY_ESCAPE:
				toggle_help()
			get_viewport().set_input_as_handled()
			return
		if feedback != null:
			if k.keycode == KEY_ESCAPE:
				feedback.close()
				get_viewport().set_input_as_handled()
			return
		if Share.dlg != null:
			if k.keycode == KEY_ESCAPE and not k.echo:
				Share.dlg.escape()
				get_viewport().set_input_as_handled()
			return
		if settings != null:
			if k.keycode == KEY_ESCAPE:
				close_settings()
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
					var on := Audio.toggle_sound()
					flash("Звук включён" if on else "Звук выключен (M — включить)", UI.GHOST, 1.8)
				get_viewport().set_input_as_handled()
			KEY_F11:
				_toggle_fullscreen()
				get_viewport().set_input_as_handled()
			KEY_ENTER:
				if k.alt_pressed:
					_toggle_fullscreen()
					get_viewport().set_input_as_handled()
	elif e is InputEventJoypadButton and e.pressed and (e as InputEventJoypadButton).button_index == JOY_BUTTON_B:
		back()                                     # (геймпад переводится в клавиши в _input — сюда не доходит)
		get_viewport().set_input_as_handled()


func _toggle_fullscreen() -> void:
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
	_esc_t = 2.5
	flash("Ещё раз Esc — выйти из игры.", UI.AMBER, _esc_t)
