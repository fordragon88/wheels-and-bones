extends Screen
## Титры (draw_credits в game.py): данные credits.json (заголовок раздела + строки), сами медленно ползут вверх (после
## 1,2 с; «Без анимации» — стоят), колесо мыши / протянуть / ↑ ↓ PgUp PgDn Home End — листать; края плавно гаснут.
## «НАЗАД» — туда, откуда пришли (титул или вечеринка), «ПОДДЕРЖАТЬ GOAT ♥». Параметры: {"from": "title"|"ending"}.

const AREA := Rect2(0, 120, UI.W, UI.H - 210)

var from: String = "title"
var scroll_y: float = 0.0
var _text: Control
var _deco: Control
var _back: GameButton
var _shade: Control


func _ready() -> void:
	from = params.get("from", "title")
	super._ready()


func music_theme() -> String:
	return "party" if from == "ending" else "workshop"


func text_cap() -> float:
	return 1.25                          # плотная раскладка (TEXT_CAP_SCENES в game.py)


func summary() -> String:
	var secs: Array = []
	for sec: Dictionary in Content.credits:
		secs.append(Loc.t(sec.get("title", "")) + ". " + " ".join((sec.get("lines", []) as Array).map(
			func(x: String) -> String: return Loc.t(x))))
	return Loc.t("Титры.") + " " + " ".join(secs) + " " + Loc.t("Esc — назад.")


func toast_bounds() -> Vector2:
	return Vector2(8, 56)


## Строки: [текст, размер, цвет, жирный, y от начала] и высота всего.
func layout() -> Array:
	var out: Array = []
	var y := 0.0
	var i := 0
	for sec: Dictionary in Content.credits:
		out.append([sec.get("title", ""), 30 if i == 0 else 22, UI.AMBER, true, y])
		y += 46 if i == 0 else 36
		for ln: String in sec.get("lines", []):
			out.append([ln, 18, UI.WHITE if i else UI.GHOST, false, y])
			y += 27
		y += 34
		i += 1
	return [out, y]


func max_scroll() -> float:
	return maxf(0.0, float(layout()[1]) - (UI.H - 290))


func build() -> void:
	add_child(BgLayer.make("bg_party.png" if from == "ending" else "bg_workshop.png"))
	_text = Control.new()
	_text.name = "Rows"
	_text.position = AREA.position
	_text.size = AREA.size
	_text.clip_contents = true
	_text.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_text.draw.connect(_draw_rows)
	add_child(_text)
	_deco = Control.new()
	_deco.name = "Deco"
	_deco.size = size
	_deco.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_deco.draw.connect(_draw_deco)
	add_child(_deco)
	move_child(_deco, 1)                          # затемнение — под строками
	_back = GameButton.make(Rect2(UI.W - 200, UI.H - 70, 170, 46), "НАЗАД", UI.GOOD)
	_back.name = "BackBtn"
	_back.pressed.connect(go_back)
	add_child(_back)
	var sp := GameButton.make(Rect2(30, UI.H - 70, 230, 46), "ПОДДЕРЖАТЬ GOAT ♥", UI.AMBER)
	sp.name = "Support"
	sp.pressed.connect(Nav.open_support)
	add_child(sp)
	var shade := Control.new()
	shade.name = "Shade"
	shade.size = size
	shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	shade.draw.connect(_draw_shade.bind(shade))
	add_child(shade)
	move_child(shade, 3)
	_shade = shade
	Chrome.add(self, false, true, false)
	accessibility_description = summary()


func first_focus() -> Control:
	return _back


func go_back() -> void:
	Audio.sfx("tick")
	Nav.go(from if from in ["title", "ending"] else "title")


func scroll(d: float) -> void:
	scroll_y = clampf(scroll_y + d, 0.0, max_scroll())


func tick(dt: float) -> void:
	if not Settings.calm() and st > 1.2:
		scroll_y = minf(scroll_y + 26 * dt, max_scroll())       # медленно вверх
	_text.queue_redraw()
	_deco.queue_redraw()
	_shade.queue_redraw()


func handle_key(e: InputEventKey) -> bool:
	var d: float = {KEY_UP: -60.0, KEY_DOWN: 60.0, KEY_PAGEUP: -300.0, KEY_PAGEDOWN: 300.0, KEY_HOME: -1e6,
		KEY_END: 1e6}.get(e.keycode, 0.0)
	if d != 0.0:
		scroll(d)
		return true
	return false


func _gui_input(e: InputEvent) -> void:
	if e is InputEventMouseButton and e.pressed and e.button_index in [MOUSE_BUTTON_WHEEL_UP, MOUSE_BUTTON_WHEEL_DOWN]:
		scroll(-60 if e.button_index == MOUSE_BUTTON_WHEEL_UP else 60)
		accept_event()
	elif e is InputEventMouseMotion and (e.button_mask & MOUSE_BUTTON_MASK_LEFT):
		scroll(-e.relative.y)
		accept_event()


func _draw_deco() -> void:
	_deco.draw_rect(Rect2(0, 0, UI.W, UI.H), Color8(12, 10, 18, 205))


func _draw_rows() -> void:
	var top := 44 - int(scroll_y)
	for row: Array in layout()[0]:
		var yy: float = top + float(row[4])
		if -40 < yy and yy < AREA.size.y + 10:
			UI.draw_text(_text, Loc.t(row[0]), Vector2(UI.W / 2.0, yy), row[1], row[2], row[3], 1)


func _draw_shade(c: Control) -> void:
	var col := Color8(12, 10, 18)
	c.draw_rect(Rect2(0, 0, UI.W, AREA.position.y), Color(col, 200 / 255.0))
	c.draw_rect(Rect2(0, AREA.end.y, UI.W, UI.H - AREA.end.y), Color(col, 200 / 255.0))
	for k in 36:
		var a := (200.0 * (36 - k) / 36.0) / 255.0
		c.draw_rect(Rect2(0, AREA.position.y + k, UI.W, 1), Color(col, a))
		c.draw_rect(Rect2(0, AREA.end.y - 1 - k, UI.W, 1), Color(col, a))
	UI.wave_title(c, "ТИТРЫ", Vector2(UI.W / 2.0, 70), 44, UI.AMBER, st, t)
	UI.draw_text(c, Loc.t("колесо мыши / ↑ ↓ — листать · Esc — назад"), Vector2(UI.W / 2.0, UI.H - 47), 15, UI.GREY, false, 1)
