extends Screen
## Титул (draw_title): фон мастерской, крутящиеся колёса, название буквами с перелётом, подзаголовки, машущие
## Мартин (въезжает слева) и Барти (парит справа), «[ клик — начать ]», «ТИТРЫ», «ПОДДЕРЖАТЬ GOAT ♥», подсказки
## клавиш, справа вверху язык и шестерёнка. Клик/тап по пустому месту, Enter или пробел — начать.

var _start: GameButton
var _martin: Figure
var _barty: Figure
var _deco: Control
var _credits: GameButton
var _support: GameButton
var _focused := false


func build() -> void:
	_focused = false
	add_child(BgLayer.make("bg_workshop.png"))
	_deco = Control.new()
	_deco.name = "Deco"
	_deco.size = size
	_deco.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_deco.draw.connect(_draw_deco)
	add_child(_deco)
	_martin = Figure.make("martin.png", Vector2(-260, UI.H - 300), Vector2(230, 260), "breathe", "martin_wave")
	_martin.loop_box = Rect2(0, -30, 230, 290)       # кадры петли с полями: (230, 290) на 30 px выше — тот же рост
	_martin.name = "Martin"
	add_child(_martin)
	_barty = Figure.make("ghost.png", Vector2(UI.W - 250, UI.H - 330), Vector2(190, 240), "float", "barty_wave")
	_barty.name = "Barty"
	add_child(_barty)
	_start = GameButton.make(Rect2(UI.W / 2.0 - 230, 448, 460, 44), "", UI.AMBER)
	_start.name = "Start"
	_start.plain = true
	_start.hover_sound = false
	_start.on_draw = _draw_start
	_start.pressed.connect(start)
	add_child(_start)
	_credits = GameButton.make(Rect2(UI.W / 2.0 - 215, 520, 200, 40), "ТИТРЫ", UI.GHOST)
	_credits.name = "Credits"
	_credits.pressed.connect(func() -> void:
		Audio.sfx("tick")
		Nav.go("credits", {"from": "title"}))
	add_child(_credits)
	_support = GameButton.make(Rect2(UI.W / 2.0 + 15, 520, 200, 40), "ПОДДЕРЖАТЬ GOAT ♥", UI.AMBER)
	_support.name = "Support"
	_support.pressed.connect(_open_support)
	add_child(_support)
	Chrome.add(self, false, false, true)
	_update_start_label()
	tick(0.0)


func _update_start_label() -> void:
	var cont := SaveGame.done.size() > 0
	var touch := DisplayServer.is_touchscreen_available() and OS.has_feature("mobile")
	if touch:
		_start.label = "[ тап — продолжить ]" if cont else "[ тап — начать ]"
	else:
		_start.label = "[ клик — продолжить ]" if cont else "[ клик — начать ]"
	_start.accessibility_name = Loc.t(_start.label).trim_prefix("[ ").trim_suffix(" ]")


func first_focus() -> Control:
	return _start


func music_theme() -> String:
	return "workshop"


func toast_bounds() -> Vector2:
	return Vector2(8, 112)


func summary() -> String:
	return Loc.t("Колёса и Кости") + ". " + Loc.t("Обучающий симулятор ремонта инвалидных колясок в фэнтези-мире")


func tick(_dt: float) -> void:
	var mx := -260 + int(320 * UI.ease_out((st - 0.4) / 1.4))
	_martin.position.x = mx
	_barty.appear_k = UI.ease_back((st - 1.4) / 0.6)
	var shown := st > 1.6 or Settings.calm()
	_credits.visible = shown
	_support.visible = shown
	_start.visible = shown
	if shown and not _focused and Nav.settings == null:      # «начать» появилась — фокус на ней (Enter/пробел)
		_focused = true
		if get_viewport().gui_get_focus_owner() == null:
			_start.grab_focus()
	_deco.queue_redraw()


func _draw_start(b: GameButton, r: Rect2) -> void:
	var pulse := 0.5 + 0.5 * UI.wsin(t * 3.2)
	var c := UI.AMBER
	c.a = (150 + 105 * pulse) / 255.0
	UI.draw_text(b, Loc.t(b.label), r.get_center() + Vector2(0, roundf(3 * b.hover_k)), 24, c, true, 1)


func _draw_deco() -> void:
	for p: Array in [[UI.W / 2.0 - 510, 1.0], [UI.W / 2.0 + 510, -1.0]]:
		_spin_wheel(Vector2(p[0], 205), 50, t * 1.3 * p[1], UI.ease_back((st - 0.7) / 0.6))
	UI.wave_title(_deco, "КОЛЁСА И КОСТИ", Vector2(UI.W / 2.0, 210), 76, UI.AMBER, st, t, 2 * 510 - 140)
	var c1 := UI.GHOST
	c1.a = UI.appear(st, 0.9, 0.6)
	UI.draw_text(_deco, Loc.t("ремонтная мастерская Мартина"), Vector2(UI.W / 2.0, 285), 26, c1, false, 1)
	var c2 := UI.WHITE
	c2.a = UI.appear(st, 1.2, 0.6)
	UI.draw_text(_deco, Loc.t("Обучающий симулятор ремонта инвалидных колясок в фэнтези-мире"),
		Vector2(UI.W / 2.0, 360), 19, c2, false, 1)
	var touch := OS.has_feature("mobile")
	if touch:
		UI.draw_text(_deco, Loc.t("прогресс сохраняется автоматически"), Vector2(UI.W / 2.0, UI.H - 36), 15, UI.GREY, false, 1)
	else:
		var h1 := "M — sound · progress saves automatically" if OS.has_feature("web") \
			else Loc.t("Esc — выход · M — звук · прогресс сохраняется автоматически")
		UI.draw_text(_deco, h1, Vector2(UI.W / 2.0, UI.H - 36), 15, UI.GREY, false, 1)
		UI.draw_text(_deco, Loc.t("F1 — управление с клавиатуры · F2 — озвучка для незрячих"),
			Vector2(UI.W / 2.0, UI.H - 62), 15, UI.CYAN, false, 1)


## Вращающееся колесо коляски: шина, обод, 12 спиц, ступица (draw_spin_wheel).
@warning_ignore("integer_division")
func _spin_wheel(c: Vector2, r: float, ang: float, k: float) -> void:
	if k <= 0.01:
		return
	if Settings.calm():
		ang = 0.3
	var rr := maxf(4, int(r * k))
	var col := Color8(205, 210, 225)
	# в pygame колесо рисуется вдвое крупнее и уменьшается: радиусы ×0,5 от «большой» картинки
	var tire_w := maxf(2, int(rr) / 4) / 2.0
	_deco.draw_arc(c, rr - tire_w / 2.0, 0, TAU, 64, Color8(40, 40, 48), tire_w, true)
	var rim_w := maxf(2, int(rr) / 12) / 2.0
	_deco.draw_arc(c, rr * 0.81 - rim_w / 2.0, 0, TAU, 64, col, rim_w, true)
	for i in 12:
		var a := ang + i * PI / 6
		_deco.draw_line(c, c + Vector2(cos(a), sin(a)) * rr * 0.8, col, maxf(1, int(rr) / 18) / 2.0 + 0.5, true)
	_deco.draw_circle(c, maxf(3, int(rr) / 4) / 2.0, col, true, -1, true)
	_deco.draw_circle(c, maxf(2, int(rr) / 10) / 2.0, Color8(90, 90, 100), true, -1, true)


func start() -> void:
	Audio.sfx("tick")
	if SaveGame.done.size() > 0 or SaveGame.tutorial_skipped or SaveGame.assign_on():   # задание — сразу в мастерскую
		Nav.go("hub")
	else:
		Nav.go("intro")                     # вступления ещё нет — Nav ведёт в мастерскую (там пока только Мартин)


func _open_support() -> void:
	Nav.open_support()


func _gui_input(e: InputEvent) -> void:
	if e is InputEventMouseButton and e.pressed and e.button_index == MOUSE_BUTTON_LEFT:
		accept_event()
		start()


func handle_key(e: InputEventKey) -> bool:
	if e.keycode == KEY_ESCAPE and not e.echo:
		Nav.quit_request()
		return true
	return false


func go_back() -> void:
	Nav.quit_request()
