extends Screen
## Финал — вечеринка (draw_ending/click_ending в game.py): после последнего из 21 ремонта (один раз — ending_seen;
## потом — кнопкой «НА ВЕЧЕРИНКУ!» в мастерской). Мартин танцует в коляске, Барти кружит, конфетти, «ВЕЧЕРИНКА!»,
## история, слова Барти, «Коллекция: N колясок…», «[ клик — посмотреть гараж ]», «ТИТРЫ», «ПОДДЕРЖАТЬ GOAT ♥».

var _deco: Control                       # подложка истории
var _wave: Control                       # «ВЕЧЕРИНКА!» (каждый кадр)
var _text: Control                       # история, реплика Барти, коллекция
var _top: Control
var _martin: Figure
var _barty: Figure
var _garage: GameButton

const STORY := "Мартин докатил до друзей на отремонтированной коляске. Левая нога снова отвалилась у самого входа — но коляска едет идеально, а это главное."
const BARTY := "Бартоломью: «Ты научился чинить лучше, чем я когда-либо видел. Горжусь, парень. Теперь — танцуй.»"


func music_theme() -> String:
	return "party"


func text_cap() -> float:
	return 1.25                          # плотная раскладка (TEXT_CAP_SCENES в game.py)


func summary() -> String:
	return Loc.t("ВЕЧЕРИНКА!") + " " + Loc.t(STORY)


func toast_bounds() -> Vector2:
	return Vector2(54, 56)


func build() -> void:
	add_child(BgLayer.make("bg_party.png"))
	_martin = Figure.make("martin.png", Vector2(-260, UI.H - 290), Vector2(240, 270), "none")
	_martin.name = "Martin"
	add_child(_martin)
	if Settings.barty_on():
		_barty = Figure.make("ghost.png", Vector2(UI.W - 230, UI.H - 300), Vector2(170, 220), "float", "barty_wave")
		_barty.name = "Barty"
		add_child(_barty)
	_deco = Control.new()
	_deco.name = "Deco"
	_deco.size = size
	_deco.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_deco.draw.connect(_draw_deco)
	add_child(_deco)
	_wave = _layer("Title", _draw_wave)        # слои подряд — порядок рисования тот же, что был в одном _deco
	_text = _layer("Story", _draw_story)
	_garage = GameButton.make(Rect2(UI.W / 2.0 - 260, 490, 520, 40), "", UI.AMBER)
	_garage.name = "ToGarage"
	_garage.plain = true
	_garage.hover_sound = false
	_garage.on_draw = _draw_garage_label
	_garage.accessibility_name = Loc.t("[ клик — посмотреть гараж ]").trim_prefix("[ ").trim_suffix(" ]")
	_garage.pressed.connect(to_garage)
	add_child(_garage)
	var cr := GameButton.make(Rect2(UI.W / 2.0 - 215, 560, 200, 40), "ТИТРЫ", UI.GHOST)
	cr.name = "Credits"
	cr.pressed.connect(func() -> void:
		Audio.sfx("tick")
		Nav.go("credits", {"from": "ending"}))
	add_child(cr)
	var sp := GameButton.make(Rect2(UI.W / 2.0 + 15, 560, 200, 40), "ПОДДЕРЖАТЬ GOAT ♥", UI.AMBER)
	sp.name = "Support"
	sp.pressed.connect(Nav.open_support)
	add_child(sp)
	_top = Control.new()                       # конфетти — поверх героев
	_top.name = "Confetti"
	_top.size = size
	_top.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_top.draw.connect(_draw_confetti)
	add_child(_top)
	move_child(_top, 3 if _barty else 2)
	Chrome.add(self, true, false, false)


func first_focus() -> Control:
	return _garage


func to_garage() -> void:
	Audio.sfx("tick")
	Nav.go("garage")


func go_back() -> void:
	Nav.go("hub")


func _gui_input(e: InputEvent) -> void:
	if e is InputEventMouseButton and e.pressed and e.button_index == MOUSE_BUTTON_LEFT:
		accept_event()
		to_garage()                              # клик по пустому месту — в гараж


func tick(_dt: float) -> void:
	var rock := 6 * UI.wsin(t * 4.2)
	var bounce := int(8 * absf(UI.wsin(t * 4.2)))
	_martin.position = Vector2(-260 + int(320 * UI.ease_out(st / 1.2)), UI.H - 290 - bounce)
	_martin.rotation_degrees = -rock
	_martin.pivot_offset = Vector2(120, 270)
	if _barty:
		_barty.appear_k = UI.ease_back((st - 0.6) / 0.6)
		_barty.rotation_degrees = -8 * UI.wsin(t * 2.1)
		_barty.pivot_offset = Vector2(85, 110)
	redraw_on(_deco, [minf(st, 1.1)])          # подложка проявляется до 1 с, потом стоит
	_wave.queue_redraw()                       # «ВЕЧЕРИНКА!» — буквы качаются волной
	_top.queue_redraw()                        # конфетти


func _layer(nm: String, fn: Callable) -> Control:
	var c := Control.new()
	c.name = nm
	c.size = size
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	c.draw.connect(fn)
	add_child(c)
	return c


## Сколько колясок в гараже (билеты Гильдии — не коляски).
func chairs() -> int:
	var n := 0
	for g: Array in SaveGame.garage:
		for j: Dictionary in Content.jobs:
			if j["id"] == g[0]:
				n += 1
	return n


func _layout() -> Array:
	var story := Loc.t(STORY)
	var barty := Loc.t(BARTY) if Settings.barty_on() else ""
	var y1 := 230.0
	var y2 := maxf(330, y1 + UI.wrap_lines(story, 800, 20).size() * (UI.line_height(20) + 2) + 14)
	var y3 := maxf(430, y2 + UI.wrap_lines(barty, 800, 19).size() * (UI.line_height(19) + 2) + 16) if barty != "" else y2 + 10
	var panel := Rect2(UI.W / 2.0 - 440, 205, 880, maxf(270, y3 + UI.line_height(18) + 22 - 205))
	return [story, barty, y1, y2, y3, panel]


func _draw_deco() -> void:
	var L := _layout()
	var panel: Rect2 = L[5]
	var pk := UI.appear(st, 0.5, 0.5)
	UI.draw_round_rect(_deco, panel, Color8(18, 16, 30, int(200 * pk)), Color(), 0, 14)


func _draw_wave() -> void:
	UI.wave_title(_wave, "ВЕЧЕРИНКА!", Vector2(UI.W / 2.0, 140), 60, UI.AMBER, st, t)


func _draw_story() -> void:
	var L := _layout()
	var panel: Rect2 = L[5]
	UI.draw_wrapped(_text, L[0], Vector2(UI.W / 2.0, L[2]), 800, 20, UI.WHITE, true)
	if L[1] != "":
		UI.draw_wrapped(_text, L[1], Vector2(UI.W / 2.0, L[3]), 800, 19, UI.GHOST, true)
	UI.draw_text(_text, Loc.tf("Коллекция: {0} колясок починено и спасено.", [chairs()]), Vector2(UI.W / 2.0, L[4]), 18,
		UI.PURPLE, false, 1)
	_garage.position.y = maxf(510, panel.end.y + 20) - 20


func _draw_garage_label(b: GameButton, r: Rect2) -> void:
	var c := UI.AMBER
	c.a = (150 + 105 * (0.5 + 0.5 * UI.wsin(t * 3.2))) / 255.0
	UI.draw_text(b, Loc.t("[ клик — посмотреть гараж ]"), r.get_center(), 20, c, false, 1)


## Конфетти (draw_confetti): 80 полосок падают и кружатся; «Без анимации» и «Свечение» — нет.
func _draw_confetti() -> void:
	if not Settings.glow_on():
		return
	var pal := [Color8(240, 190, 90), Color8(120, 210, 160), Color8(230, 120, 170), Color8(120, 180, 240), Color8(250, 240, 170)]
	for i in 80:
		var sp := 60 + 70 * BgLayer._h01(i, 1)
		var x := UI.W * BgLayer._h01(i, 2) + 40 * sin(t * (0.8 + BgLayer._h01(i, 3)) + i)
		var y := -20 + fmod(t * sp + 780 * BgLayer._h01(i, 4), 780.0)
		var a := t * (2 + 3 * BgLayer._h01(i, 5)) + i
		var w := 7.0
		var h := 3 + 4 * absf(sin(a))
		var ca := cos(a * 0.7)
		var sa := sin(a * 0.7)
		var pts := PackedVector2Array()
		for dd: Vector2 in [Vector2(-w, -h), Vector2(w, -h), Vector2(w, h), Vector2(-w, h)]:
			pts.append(Vector2(x + dd.x * ca - dd.y * sa, y + dd.x * sa + dd.y * ca))
		_top.draw_colored_polygon(pts, pal[i % pal.size()])
