extends Screen
## Провал про-задания или экзамена (draw_failed в game.py): «ПРОВАЛ. РАЗБОР ОШИБКИ» / «ЭКЗАМЕН НЕ СДАН» с тряской,
## разбор (что попытался и какой шаг безопасности пропустил + failnote, или лимит ошибок экзамена), слова Бренны и
## Барти; если провал электрический — вспышка и молнии. «ЗАНОВО» / «ПЕРЕСДАТЬ» (новый билет), «В ГИЛЬДИЮ».
## Параметры: {"msg", "exam", "job", "zap"}.

var msg: String = ""
var exam: bool = false
var jid: String = ""
var zap: bool = false
var _deco: Control
var _add: Control
var _retry: GameButton


func _ready() -> void:
	msg = params.get("msg", "")
	exam = bool(params.get("exam", false))
	jid = params.get("job", "")
	zap = bool(params.get("zap", false))
	super._ready()


func music_theme() -> String:
	return "guild"


func text_cap() -> float:
	return 1.25                          # плотная раскладка (TEXT_CAP_SCENES в game.py)


func summary() -> String:
	return Loc.t("ЭКЗАМЕН НЕ СДАН" if exam else "ПРОВАЛ. РАЗБОР ОШИБКИ") + ". " + Loc.t(msg)


func build() -> void:
	add_child(BgLayer.make("bg_guild.png"))
	_deco = Control.new()
	_deco.name = "Deco"
	_deco.size = size
	_deco.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_deco.draw.connect(_draw_deco)
	add_child(_deco)
	_add = Control.new()
	_add.size = size
	_add.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var mat := CanvasItemMaterial.new()
	mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	_add.material = mat
	_add.draw.connect(_draw_add)
	add_child(_add)
	_retry = GameButton.make(Rect2(UI.W / 2.0 - 330, 560, 300, 56), "ПЕРЕСДАТЬ" if exam else "ЗАНОВО", UI.AMBER)
	_retry.name = "Retry"
	_retry.pressed.connect(retry)
	add_child(_retry)
	var back := GameButton.make(Rect2(UI.W / 2.0 + 30, 560, 300, 56), "В ГИЛЬДИЮ", UI.CYAN)
	back.name = "ToGuild"
	back.pressed.connect(go_back)
	add_child(back)
	Chrome.add(self, true, true, false)
	accessibility_description = summary()


func first_focus() -> Control:
	return _retry


func retry() -> void:
	Audio.sfx("tick")
	if exam:
		_exam_again()
	else:
		Nav.go("tech", {"job": jid})


static func _exam_again() -> void:
	var ticket: Dictionary = Content.tech_jobs.pick_random()      # пересдача: новый случайный билет
	Nav.go("tech", {"job": ticket["id"], "exam": true})


func go_back() -> void:
	Nav.go("guild")


func tick(_dt: float) -> void:
	_deco.queue_redraw()
	_add.queue_redraw()


func _draw_deco() -> void:
	if zap and st < 0.9 and not Settings.calm():
		var k := st / 0.9
		if k < 0.15:
			_deco.draw_rect(Rect2(0, 0, UI.W, UI.H), Color8(200, 225, 255, int((90 if Settings.glow else 40) * (1 - k / 0.15))))
		_bolts(Vector2(UI.W / 2.0 - 160, 300), k, 2.2)
		_bolts(Vector2(UI.W / 2.0 + 200, 330), minf(1.0, k * 1.2), 1.8)
	var shake := int(14 * sin(st * 42) * maxf(0.0, 1 - st / 0.6)) if not Settings.calm() else 0
	UI.draw_text(_deco, Loc.t("ЭКЗАМЕН НЕ СДАН" if exam else "ПРОВАЛ. РАЗБОР ОШИБКИ"), Vector2(UI.W / 2.0 + shake, 120), 46, UI.BAD, true, 1)
	var card := Rect2(UI.W / 2.0 - 420, 190 + int(40 * (1 - UI.appear(st, 0.2))), 840, 220)
	_deco.draw_rect(card, Color8(40, 22, 26, 240))
	UI.draw_round_rect(_deco, card, Color(0, 0, 0, 0), UI.BAD, 2, 10)
	UI.draw_wrapped(_deco, Loc.t(msg), card.position + Vector2(26, 24), card.size.x - 52, 19, UI.WHITE)
	var brenna := "Бренна: «Пересдача — не позор. Позор — выдать человеку непроверенную коляску.»" if exam \
		else "Бренна: «В мастерской ошибка стоит железа. На дороге — жизни. Заново, ученик.»"
	UI.draw_wrapped(_deco, Loc.t(brenna), Vector2(card.position.x + 26, 432), card.size.x - 52, 18, UI.GHOST)
	var bl := Loc.t("Барти: «Не красней, Мартин. Меня она гоняла так же. Посмертно.»")
	var w := UI.text_width(bl, 16)
	UI.draw_round_rect(_deco, Rect2(UI.W / 2.0 - w / 2 - 8, 508 - UI.line_height(16) / 2 - 4, w + 16, UI.line_height(16) + 8),
		Color8(14, 12, 20, 175), Color(), 0, 8)
	UI.draw_text(_deco, bl, Vector2(UI.W / 2.0, 508), 16, UI.PURPLE, false, 1)


## Молнии (draw_zap): две-три дрожащие ветки сверху, искры.
func _bolts(pos: Vector2, u: float, size_: float) -> void:
	if u >= 1.0:
		return
	var fade := 1 - u
	var seed_ := int(u * 14)
	var srcs := [Vector2(-55, -95), Vector2(40, -100), Vector2(-10, -120)]
	for j in (3 if size_ > 1.2 else 2):
		var pts := ToolAction._bolt(pos + srcs[j] * size_, pos, seed_ * 7 + j, 0.25)
		var wd := maxf(2, int(5 * size_ * fade))
		_deco.draw_polyline(pts, Color8(120, 190, 255), wd + 4, true)
		_deco.draw_polyline(pts, Color8(240, 250, 255), maxf(1, int(wd / 2.0) + 1), true)


func _draw_add() -> void:
	if zap and st < 0.9 and not Settings.calm() and Settings.glow:
		UI.draw_glow(_add, Vector2(UI.W / 2.0 - 160, 300), int(46 * 2.2), Color8(90, 150, 255), 0.9 * (1 - st / 0.9))
