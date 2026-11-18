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
}
const FALLBACK := {"guild": "hub", "seating": "hub"}

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
var support_opened: int = 0               # сколько раз нажали «Поддержать» (тесты)                   # «ещё раз Esc — выйти»


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
	Audio.scene(name, current.music_theme())
	_esc_t = 0.0
	Speech.say(current.summary(), true)
	screen_changed.emit(name)


func back() -> void:
	if help != null:
		toggle_help()
		return
	if feedback != null:
		feedback.close()
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
		return
	help = HelpOverlay.new()
	UI.set_focus_enabled(host, false)
	overlay.get_node("Top").add_child(help)


func close_settings() -> void:
	if settings != null:
		settings.close()


func _on_settings_closed() -> void:
	settings = null
	UI.set_focus_enabled(host, true)
	if current != null:
		current._focus_default()


func _process(dt: float) -> void:
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


func _input(e: InputEvent) -> void:
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
		if settings != null:
			if k.keycode == KEY_ESCAPE:
				close_settings()
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
		back()
		get_viewport().set_input_as_handled()


func _toggle_fullscreen() -> void:
	if OS.has_feature("web") or test_mode:
		return
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
