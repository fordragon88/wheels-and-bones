extends Screen
## Экзамен сдан (draw_exam_result в game.py): «ЭКЗАМЕН СДАН» (без ошибок — «С ОТЛИЧИЕМ»), конфетти, чек-лист Гильдии
## (пункты появляются по очереди), диплом «— ДИПЛОМ ГИЛЬДИИ КОЛЁСНИКОВ —», Бренна вспоминает Барти, «В ГИЛЬДИЮ».
## Параметры: {"mistakes"}.

var mistakes: int = 0
var _deco: Control
var _top: Control
var _btn: GameButton


func _ready() -> void:
	mistakes = int(params.get("mistakes", 0))
	super._ready()


func music_theme() -> String:
	return "guild"


func text_cap() -> float:
	return 1.25                          # плотная раскладка (TEXT_CAP_SCENES в game.py)


func items() -> Array:
	return ["Техника безопасности — без нарушений", "Порядок операций — соблюдён", "Спецификации — по мануалу",
		"Ошибки — %d из %d допустимых" % [mistakes, int(Content.consts.get("exam_max_mistakes", 3))]]


func title() -> String:
	return "ЭКЗАМЕН СДАН — С ОТЛИЧИЕМ" if mistakes == 0 else "ЭКЗАМЕН СДАН"


func summary() -> String:
	return Loc.t(title()) + ". " + ". ".join(items().map(func(s: String) -> String: return Loc.t(s)))


func build() -> void:
	add_child(BgLayer.make("bg_guild.png"))
	_top = Control.new()
	_top.size = size
	_top.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_top.draw.connect(_draw_confetti)
	add_child(_top)
	_deco = Control.new()
	_deco.name = "Deco"
	_deco.size = size
	_deco.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_deco.draw.connect(_draw_deco)
	add_child(_deco)
	_btn = GameButton.make(Rect2(UI.W / 2.0 - 150, UI.H - 110, 300, 56), "В ГИЛЬДИЮ", UI.AMBER)
	_btn.name = "ToGuild"
	_btn.pressed.connect(go_back)
	add_child(_btn)
	Chrome.add(self, true, true, false)


func first_focus() -> Control:
	return _btn


func go_back() -> void:
	Audio.sfx("tick")
	Nav.go("guild")


func tick(_dt: float) -> void:
	redraw_on(_deco, [minf(st, 0.4 + 0.35 * items().size() + 0.35)])   # пункты чек-листа въезжают, потом стоят
	_top.queue_redraw()                         # конфетти — каждый кадр


func _plate(r: Rect2) -> void:
	UI.draw_round_rect(_deco, r.grow_individual(8, 4, 8, 4), Color8(14, 12, 20, 175), Color(), 0, 8)


func _draw_deco() -> void:
	UI.draw_text(_deco, Loc.t(title()), Vector2(UI.W / 2.0, 84), 46, UI.GOOD, true, 1)
	var card := Rect2(UI.W / 2.0 - 380, 150, 760, 196)
	_deco.draw_rect(card, Color8(24, 34, 28, 240))
	UI.draw_round_rect(_deco, card, Color(0, 0, 0, 0), UI.GOOD, 2, 10)
	UI.draw_text(_deco, Loc.t("ЧЕК-ЛИСТ ГИЛЬДИИ"), card.position + Vector2(24, 14), 16, UI.GHOST, true)
	var y := card.position.y + 46
	var its := items()
	for i in its.size():
		var a := UI.appear(st, 0.4 + 0.35 * i, 0.3)
		UI.draw_text(_deco, "✔ " + Loc.t(its[i]), Vector2(card.position.x + 34 + int(30 * (1 - a)), y), 17, Color(UI.WHITE, a))
		y += 34
	var dip := Rect2(UI.W / 2.0 - 380, 366, 760, 122)
	_deco.draw_rect(dip, Color8(40, 34, 20, 240))
	UI.draw_round_rect(_deco, dip, Color(0, 0, 0, 0), UI.AMBER, 3, 10)
	UI.draw_text(_deco, Loc.t("— ДИПЛОМ ГИЛЬДИИ КОЛЁСНИКОВ —"), Vector2(dip.get_center().x, dip.position.y + 16), 20, UI.AMBER, true, 1)
	UI.draw_text(_deco, Loc.t("Мартин, зомби — сертифицированный техник по ремонту кресел-колясок"),
		Vector2(dip.get_center().x, dip.position.y + 52), 17, UI.WHITE, false, 1)
	UI.draw_text(_deco, Loc.t("принято под надзором Мастерицы Бренны (посмертно)"), Vector2(dip.get_center().x, dip.position.y + 84),
		13, UI.GREY, false, 1)
	var bt := Loc.t("Бренна: «Сдано. И вот ещё что, Бартоломью... я помню тебя. Ты задавал хорошие вопросы.»")
	var ls := UI.wrap_lines(bt, 760, 17)
	var bw := 0.0
	for ln in ls:
		bw = maxf(bw, UI.text_width(ln, 17))
	_plate(Rect2(UI.W / 2.0 - bw / 2, 500, bw, ls.size() * (UI.line_height(17) + 2) - 2))
	var yb := UI.draw_wrapped(_deco, bt, Vector2(UI.W / 2.0, 500), 760, 17, UI.GHOST, true)
	var bl := Loc.t("Барти: «...Мартин. МАРТИН. Она меня ПОМНИТ!»")
	var w := UI.text_width(bl, 16)
	var cy := maxf(556, yb + 14)
	_plate(Rect2(UI.W / 2.0 - w / 2, cy - UI.line_height(16) / 2, w, UI.line_height(16)))
	UI.draw_text(_deco, bl, Vector2(UI.W / 2.0, cy), 16, UI.PURPLE, false, 1)


func _draw_confetti() -> void:
	if not Settings.glow_on():
		return
	var pal := [Color8(240, 190, 90), Color8(120, 210, 160), Color8(230, 120, 170), Color8(120, 180, 240), Color8(250, 240, 170)]
	for i in 50:
		var sp := 60 + 70 * BgLayer._h01(i, 1)
		var x := UI.W * BgLayer._h01(i, 2) + 40 * sin(t * (0.8 + BgLayer._h01(i, 3)) + i)
		var yy := -20 + fmod(t * sp + 780 * BgLayer._h01(i, 4), 780.0)
		var a := t * (2 + 3 * BgLayer._h01(i, 5)) + i
		var h := 3 + 4 * absf(sin(a))
		var ca := cos(a * 0.7)
		var sa := sin(a * 0.7)
		var pts := PackedVector2Array()
		for dd: Vector2 in [Vector2(-7, -h), Vector2(7, -h), Vector2(7, h), Vector2(-7, h)]:
			pts.append(Vector2(x + dd.x * ca - dd.y * sa, yy + dd.x * sa + dd.y * ca))
		_top.draw_colored_polygon(pts, pal[i % pal.size()])
