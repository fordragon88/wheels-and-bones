extends Screen
## Вступление (draw_intro/click_intro в game.py): ночная дорога, Мартин и Барти, 5 слайдов истории (тексты —
## intro_slides game.py) печатаются по буквам; клик/тап, Enter или пробел — допечатать, потом следующий слайд; после
## последнего — первое задание (flat, обучение). «ПРОПУСТИТЬ ОБУЧЕНИЕ ▸» — сразу в мастерскую со всеми клиентами.
## На втором слайде нога Мартина упрыгивает (сценка hop).

var idx: int = 0
var _typing: Array = ["", 0.0]
var _deco: Control
var _next: GameButton
var _leg: LegGag
var _skip: GameButton


func slides() -> Array:
	return Content.consts.get("intro_slides", [])


func music_theme() -> String:
	return "road"


func summary() -> String:
	var s: Array = slides()[mini(idx, slides().size() - 1)]
	return "%s. %s " % [Loc.t(s[0]), Loc.t(s[1])] + Loc.t("Enter — далее.")


func a11y_sig() -> Array:
	return [[], [idx]]


func toast_bounds() -> Vector2:
	return Vector2(54, 56)


func build() -> void:
	add_child(BgLayer.make("bg_road.png"))
	var m := Figure.make("martin.png", Vector2(120, 230), Vector2(200, 280), "breathe")
	m.name = "Martin"
	add_child(m)
	var g := Figure.make("ghost.png", Vector2(UI.W - 320, 230), Vector2(200, 280), "float", "barty_wave")
	g.name = "Barty"
	add_child(g)
	_leg = LegGag.make("hop", Rect2(0, 560, UI.W, 150))
	add_child(_leg)
	_deco = Control.new()
	_deco.name = "Deco"
	_deco.size = size
	_deco.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_deco.draw.connect(_draw_deco)
	add_child(_deco)
	_next = GameButton.make(_panel(), "", UI.AMBER)    # невидимая кнопка на всё окно истории: Enter/пробел — далее
	_next.name = "Next"
	_next.plain = true
	_next.hover_sound = false
	_next.pressed.connect(advance)
	add_child(_next)
	_skip = GameButton.make(Rect2(UI.W - 280, UI.H - 76, 250, 46), "ПРОПУСТИТЬ ОБУЧЕНИЕ ▸", UI.CYAN)
	_skip.name = "SkipTutorial"
	_skip.pressed.connect(skip_tutorial)
	add_child(_skip)
	Chrome.add(self, true, false, false)
	_update_a11y()


func first_focus() -> Control:
	return _next


func _update_a11y() -> void:
	var s: Array = slides()[idx]
	_next.accessibility_name = "%s. %s. %d/%d" % [Loc.t(s[0]), Loc.t(s[1]), idx + 1, slides().size()]


func _lh() -> float:
	return UI.line_height(19) + 4


## Окно истории: высота — по самому длинному слайду (крупный текст — выше).
func _panel() -> Rect2:
	var most := 0
	for s: Array in slides():
		most = maxi(most, UI.wrap_lines(Loc.t(s[1]), 510, 19).size())
	var ph := maxf(250, 70 + most * _lh() + 54)
	return Rect2(360, 250, 560, ph)


func typed(text: String) -> int:
	if Settings.a11y.get("instant", false):
		return 1 << 30
	if _typing[0] != text:
		_typing = [text, t]
		return 0
	return int((t - float(_typing[1])) * 75)


func typing_done() -> bool:
	return Settings.a11y.get("instant", false) or _typing[0] == "" or (t - float(_typing[1])) * 75 >= _typing[0].length()


func advance() -> void:
	if not typing_done():                          # первый клик — допечатать текст
		_typing[1] = t - 1000.0
		return
	idx += 1
	Audio.sfx("tick")
	if idx >= slides().size():
		Nav.go("job", {"job": "flat"})
		return
	_update_a11y()
	Speech.say(summary(), true)


func skip_tutorial() -> void:
	SaveGame.tutorial_skipped = true
	SaveGame.save()
	Audio.sfx("whoosh")
	Nav.go("hub")
	Nav.flash("Обучение пропущено: все клиенты уже ждут. Коляску Мартина можно починить в любой момент.", UI.GOOD, 5.0)


func go_back() -> void:
	Nav.go("title")


func _gui_input(e: InputEvent) -> void:
	if e is InputEventMouseButton and e.pressed and e.button_index == MOUSE_BUTTON_LEFT:
		accept_event()
		advance()


func tick(_dt: float) -> void:
	var m: Figure = get_node("Martin")
	m.position.x = 120 - int(300 * (1 - UI.ease_out(st / 0.9)))
	(get_node("Barty") as Figure).appear_k = UI.ease_back((st - 0.3) / 0.6)
	_leg.t = (t - float(_typing[1])) if idx == 1 else -1.0
	# панель слайда въезжает 0,35 с, текст печатается по буквам — потом стоит
	var s: Array = slides()[mini(idx, slides().size() - 1)]
	var text := Loc.t(s[1])
	var n := mini(typed(text), text.length())
	redraw_on(_deco, [idx, n, minf(t - float(_typing[1]), 0.4)])


func _draw_deco() -> void:
	var s: Array = slides()[mini(idx, slides().size() - 1)]
	var text := Loc.t(s[1])
	var n := typed(text)
	var sk := UI.ease_out((t - float(_typing[1])) / 0.35)
	var p := _panel()
	p.position.y = 250 + int(24 * (1 - sk))
	_deco.draw_rect(p, Color8(22, 20, 30, int(230 * sk)))
	UI.draw_round_rect(_deco, p, Color(0, 0, 0, 0), UI.AMBER, 2, 8)
	var tsz := 26
	while tsz > 16:
		var widest := 0.0
		for sl: Array in slides():
			widest = maxf(widest, UI.text_width(Loc.t(sl[0]), tsz, true))
		if widest <= p.size.x - 40:
			break
		tsz -= 1
	var title := Loc.t(s[0])
	UI.draw_text(_deco, title, Vector2(p.get_center().x, p.position.y + 20 + floorf((26 - tsz) / 2.0)),
		tsz, Color(UI.AMBER, sk), true, 1)
	UI.draw_wrapped(_deco, text, Vector2(p.get_center().x, p.position.y + 70), p.size.x - 50, 19, UI.WHITE, true, 4, n)
	UI.draw_text(_deco, Loc.t("%d/%d   [ клик — далее ]" % [idx + 1, slides().size()]),
		Vector2(p.get_center().x, p.end.y - 34), 15, UI.GREY, false, 1)
