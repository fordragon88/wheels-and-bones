extends Screen
## Итог задания (draw_result в game.py): «ГОТОВО!», звёзды (3 − ошибки/2, не меньше 1) со вспышками и звуками,
## «спасибо» клиента (печатается после 1,2 с), карточка «ЧТО ТЫ УЗНАЛ (по-настоящему):» (fact), шутка — нога Мартина
## (со сценкой) или реплика Мартина, довольный герой слева подпрыгивает, потом — волшебство (после подпрыга, раз в 60 с
## и по клику), Барти справа, «В МАСТЕРСКУЮ». Параметры: {"job": разыгранное задание, "stars", "gag", "mistakes"}.

var job: Dictionary = {}
var stars: int = 3
var gag: String = ""
var portrait: MagicPortrait
var _deco: Control
var _add: Control
var _btn: GameButton
var _leg: LegGag
var _stars_played: Dictionary = {}
var _typing: Array = ["", 0.0]
var _gy: float = 470.0


func _ready() -> void:
	job = params.get("job", {})
	stars = int(params.get("stars", 3))
	gag = params.get("gag", "")
	super._ready()


func build() -> void:
	add_child(BgLayer.make("bg_workshop.png"))
	var c: Dictionary = Content.consts.get("magic", {})
	var rb: Array = c.get("result_box", [24, 300, 210, 250])
	portrait = MagicPortrait.make(job["client_art"], Rect2(rb[0], rb[1], rb[2], rb[3]), 0.0, true)
	portrait.enter_t = 0.0
	portrait.t = st
	add_child(portrait)
	if Settings.barty_on():
		var g := Figure.make("ghost.png", Vector2(UI.W - 200, 290), Vector2(150, 200), "float", "barty_wave")
		g.name = "Barty"
		add_child(g)
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
	var gags: Array = Content.talk.get("leg_gags", [])
	if gag in gags:
		var kinds: Array = Content.consts.get("leg_gag_kind", ["drop", "peek", "roll", "hop"])
		_leg = LegGag.make(kinds[gags.find(gag) % kinds.size()], Rect2(260, 500, 760, 100))
		add_child(_leg)
	_btn = GameButton.make(Rect2(UI.W / 2.0 - 150, UI.H - 110, 300, 56),
		"В ГИЛЬДИЮ" if job.get("track") == "tech" else ("НА ВЕЧЕРИНКУ" if party_next() else "В МАСТЕРСКУЮ"), UI.AMBER)
	_btn.name = "ToHub"
	_btn.pressed.connect(func() -> void:
		Audio.sfx("tick")
		go_back())
	add_child(_btn)
	Chrome.add(self, true, true, false)


func first_focus() -> Control:
	return _btn


func summary() -> String:
	return Loc.t("ГОТОВО!") + " " + "★".repeat(stars) + ". " + Loc.t(job.get("thanks", "")) + " " + \
		Loc.t("ЧТО ТЫ УЗНАЛ (по-настоящему):") + " " + Loc.t(job.get("fact", ""))


## Вечеринка — один раз, после последнего ремонта (_party_next); переигрывание ведёт в мастерскую.
func party_next() -> bool:
	return SaveGame.user_done_count() >= Content.jobs.size() and not SaveGame.ending_seen


func go_back() -> void:
	if job.get("track") == "tech":
		Nav.go("guild")
		return
	if party_next():
		SaveGame.ending_seen = true
		SaveGame.save()
		Nav.go("ending")
		return
	Nav.go("hub")


func tick(_dt: float) -> void:
	portrait.hop = int(18 * absf(UI.wsin(st * 6)) * maxf(0.0, 1 - st / 1.6))
	for i in 3:
		var d := 0.45 + 0.28 * i
		if i < stars and st >= d and not _stars_played.has(i):
			_stars_played[i] = true
			Audio.sfx("star%d" % i)
	if _leg:
		_leg.t = st - 1.4
	_deco.queue_redraw()
	_add.queue_redraw()


func _typed(text: String) -> int:
	if Settings.a11y.get("instant", false):
		return 1 << 30
	if _typing[0] != text:
		_typing = [text, t]
		return 0
	return int((t - float(_typing[1])) * 75)


func _plate(r: Rect2) -> void:
	UI.draw_round_rect(_deco, r.grow_individual(8, 4, 8, 4), Color8(14, 12, 20, 175), Color(), 0, 8)


func _draw_deco() -> void:
	var gk := UI.ease_back(st / 0.5)
	if gk > 0.01:
		_deco.draw_set_transform(Vector2(UI.W / 2.0, 70), 0.0, Vector2(gk, gk))
		UI.draw_text(_deco, Loc.t("ГОТОВО!"), Vector2.ZERO, 44, UI.GOOD, true, 1)
		_deco.draw_set_transform(Vector2.ZERO)
	for i in 3:
		var d := 0.45 + 0.28 * i
		var k := UI.ease_back((st - d) / 0.4)
		if k > 0.01:
			_deco.draw_set_transform(Vector2(UI.W / 2.0 + (i - 1) * 52, 130), 0.0, Vector2(k, k))
			UI.draw_text(_deco, "★" if i < stars else "☆", Vector2.ZERO, 40, UI.AMBER, false, 1)
			_deco.draw_set_transform(Vector2.ZERO)
	var thanks := Loc.t(job.get("thanks", ""))
	var lines := UI.wrap_lines(thanks, 760, 20)
	if st > 1.2 and not lines.is_empty():
		var bw := 0.0
		for ln in lines:
			bw = maxf(bw, UI.text_width(ln, 20))
		_plate(Rect2(UI.W / 2.0 - bw / 2, 185, bw, lines.size() * (UI.line_height(20) + 2) - 2))
	var ty := UI.draw_wrapped(_deco, thanks, Vector2(UI.W / 2.0, 185), 760, 20, UI.WHITE, true, 2,
		_typed(thanks) if st > 1.2 else 0)
	var top := maxf(250, ty + 12)
	var fact := Loc.t(job.get("fact", ""))
	var fsz := 14
	for s: int in [18, 17, 16, 15, 14]:
		fsz = s
		if 54 + UI.wrap_lines(fact, 712, s).size() * (UI.line_height(s) + 2) + 14 <= 200:
			break
	var fh := UI.wrap_lines(fact, 712, fsz).size() * (UI.line_height(fsz) + 2)
	var card := Rect2(UI.W / 2.0 - 380, top + int(50 * (1 - UI.appear(st, 0.9, 0.5))), 760, maxf(180, 54 + fh + 14))
	_deco.draw_rect(card, Color8(26, 32, 30, 235))
	UI.draw_round_rect(_deco, card, Color(0, 0, 0, 0), UI.GHOST, 2, 10)
	UI.draw_text(_deco, Loc.t("ЧТО ТЫ УЗНАЛ (по-настоящему):"), card.position + Vector2(24, 18), 18, UI.GHOST, true)
	UI.draw_wrapped(_deco, fact, card.position + Vector2(24, 54), card.size.x - 48, fsz, UI.WHITE)
	_gy = maxf(470, top + card.size.y + 14)
	if gag != "":
		var gt := Loc.t(gag)
		var w := UI.text_width(gt, 17)
		_plate(Rect2(UI.W / 2.0 - w / 2, _gy - UI.line_height(17) / 2, w, UI.line_height(17)))
		UI.draw_text(_deco, gt, Vector2(UI.W / 2.0, _gy), 17, UI.PURPLE, false, 1)
	if _leg:
		var t2 := _gy + int(UI.line_height(17) / 2) + 12     # сценка — ниже подписи
		_leg.area = Rect2(260, t2, 760, maxf(60, UI.H - 114 - t2))


## Вспышки звёзд (draw_burst): искры разлетаются от звезды.
func _draw_add() -> void:
	if Settings.calm() or not Settings.glow:
		return
	for i in range(stars):
		var d := 0.45 + 0.28 * i
		var ph := (st - d) / 0.7
		if ph <= 0.0 or ph >= 1.0:
			continue
		var c := Vector2(UI.W / 2.0 + (i - 1) * 52, 130)
		for k in 10:
			var a := k * TAU / 10 + 0.3
			var dd := 70 * UI.ease_out(ph)
			UI.draw_glow(_add, c + Vector2(cos(a), sin(a)) * dd, 8, Color8(255, 210, 90), 1 - ph)
