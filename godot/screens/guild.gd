extends Screen
## Гильдия Колёсников (draw_guild/click_guild в game.py): звание Мартина по числу сданных зачётов (после экзамена —
## «Сертифицированный техник Гильдии» и «✔ ДИПЛОМ ГИЛЬДИИ ПОЛУЧЕН»), 6 про-заданий карточками (портрет, коляска,
## «УРОВЕНЬ: ТЕХНИК», «✔ сдано»), Мастерица Бренна справа, её (или Барти) реплика, «ЭКЗАМЕН ГИЛЬДИИ» после всех
## зачётов, «НАЗАД» — в мастерскую. Вход — из мастерской после 5 ремонтов.

var _cards: Array[GameButton] = []
var _deco: Control                       # звание, пояснение, подпись Бренны (неподвижное)
var _barty: Control                      # машущий Барти у реплики (каждый кадр)
var _bubble: Control                     # реплика (неподвижная)
var _exam: GameButton


func music_theme() -> String:
	return "guild"


func text_cap() -> float:
	return 1.25                          # плотная раскладка (TEXT_CAP_SCENES в game.py)


func summary() -> String:
	return Loc.t("Гильдия Колёсников") + ". " + Loc.t("Мартин — " + rank())


func rank() -> String:
	var n := SaveGame.tech_done_count()
	if SaveGame.exam_passed:
		return "Сертифицированный техник Гильдии"
	if n >= Content.tech_jobs.size():
		return "Подмастерье — допуск к экзамену"
	var names: Array = Content.consts.get("rank_names", ["Ученик Гильдии", "Младший подмастерье", "Подмастерье", "Старший подмастерье"])
	return names[mini(n, 3)]


@warning_ignore("integer_division")
func card_rect(i: int) -> Rect2:
	var step := mini(116, (UI.H - 100 - 160) / maxi(1, Content.tech_jobs.size()))
	return Rect2(60, 160 + i * step, 560, step - 10)


func build() -> void:
	_cards.clear()
	add_child(BgLayer.make("bg_guild.png"))
	add_child(TopBar.make("Гильдия Колёсников"))
	var m := Figure.make("master.png", Vector2(UI.W - 300, 130), Vector2(200, 280), "float")
	m.phase = 0.7
	m.name = "Brenna"
	add_child(m)
	_deco = Control.new()
	_deco.name = "Deco"
	_deco.size = size
	_deco.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_deco.draw.connect(_draw_deco)
	add_child(_deco)
	_barty = _layer("BartyWave", _draw_barty)       # слои подряд — тот же порядок рисования, что был в одном _deco
	_bubble = _layer("Bubble", _draw_bubble)
	for i in Content.tech_jobs.size():
		var job: Dictionary = Content.tech_jobs[i]
		var done := SaveGame.is_done(job["id"])
		var b := GameButton.make(card_rect(i), "", UI.GOOD if done else UI.CYAN)
		b.name = "Tech_" + str(job["id"])
		b.active = done
		b.set_meta("i", i)
		b.on_draw = _draw_card
		b.redraw_sig = func() -> int: return 0         # содержимое карточки не меняется (сдвиг и наведение видит кнопка)
		b.accessibility_name = "%s. %s. %s%s" % [Loc.t(job["title"]), Loc.t(job["client"]), Loc.t("УРОВЕНЬ: ТЕХНИК"),
			(". " + Loc.t("✔ сдано")) if done else ""]
		b.pressed.connect(func() -> void:
			Audio.sfx("tick")
			Nav.go("tech", {"job": job["id"]}))
		add_child(b)
		_cards.append(b)
	if SaveGame.tech_done_count() >= Content.tech_jobs.size():
		_exam = GameButton.make(Rect2(UI.W - 360, UI.H - 160, 300, 54), "ЭКЗАМЕН ГИЛЬДИИ", UI.GOOD,
			"диплом есть — но можно блеснуть" if SaveGame.exam_passed else "случайный билет · без подсказок")
		_exam.name = "Exam"
		_exam.pressed.connect(start_exam)
		add_child(_exam)
	var back := GameButton.make(Rect2(40, UI.H - 70, 160, 48), "НАЗАД", UI.AMBER)
	back.name = "BackBtn"
	back.pressed.connect(go_back)
	add_child(back)
	Chrome.add(self, true, true, true)
	get_node("Back").set_meta("kb_skip", true)   # в a11y_items game.py Гильдии — только большая «НАЗАД»


## Экзамен: случайный билет из заданий Гильдии.
static func start_exam() -> void:
	Audio.sfx("tick")
	var ticket: Dictionary = Content.tech_jobs.pick_random()
	Nav.go("tech", {"job": ticket["id"], "exam": true})


func first_focus() -> Control:
	return _cards[0] if not _cards.is_empty() else null


func go_back() -> void:
	Nav.go("hub")


func tick(_dt: float) -> void:
	for b in _cards:
		b.slide = Vector2(-int(140 * (1 - UI.appear(st, 0.1 * int(b.get_meta("i")), 0.45))), 0)
	(get_node("Brenna") as Figure).appear_k = UI.ease_back((st - 0.3) / 0.6)
	if _barty_on():
		_barty.queue_redraw()


func _layer(nm: String, fn: Callable) -> Control:
	var c := Control.new()
	c.name = nm
	c.size = size
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	c.draw.connect(fn)
	add_child(c)
	return c


## Реплику говорит Барти (машет у пузыря).
func _barty_on() -> bool:
	return _line().begins_with("Барти") and Settings.barty_on()


func _line() -> String:
	if SaveGame.tech_done_count() >= Content.tech_jobs.size():
		return "Барти: «Она ПОМНИТ меня, Мартин! Лучший день моей смерти!»" if SaveGame.exam_passed \
			else "Бренна: «Все зачёты сданы. Осталось главное — экзамен. Билет вытянешь сам.»"
	return "Барти: «Это ОНА, Мартин! Та самая мастерица, про которую я рассказывал! ...Она меня не помнит. Обидно.»"


func _draw_deco() -> void:
	UI.draw_text(_deco, Loc.t("Мартин — " + rank()), Vector2(60, 68), 20, UI.GOOD if SaveGame.exam_passed else UI.CYAN, true)
	var dy := 68 + UI.line_height(20, true) + 8
	if SaveGame.exam_passed:
		UI.draw_text(_deco, Loc.t("✔ ДИПЛОМ ГИЛЬДИИ ПОЛУЧЕН"), Vector2(60, dy), 15, UI.AMBER, true)
	else:
		var note := Loc.t("Здесь ремонт по-взрослому: порядок шагов выбираешь сам, значения — только из мануала, а нарушение техники безопасности проваливает задание.")
		var nsz := 14
		while nsz > 11 and dy + UI.wrap_lines(note, 680, nsz).size() * (UI.line_height(nsz) + 2) > 152:
			nsz -= 1
		var lines := UI.wrap_lines(note, 680, nsz)
		var bw := 0.0
		for ln in lines:
			bw = maxf(bw, UI.text_width(ln, nsz))
		UI.draw_round_rect(_deco, Rect2(60 - 8, dy - 4, bw + 16, lines.size() * (UI.line_height(nsz) + 2) - 2 + 8),
			Color8(14, 12, 20, 175), Color(), 0, 8)
		UI.draw_wrapped(_deco, note, Vector2(60, dy), 680, nsz, UI.GREY)
	UI.draw_text(_deco, Loc.t("Мастерица Бренна"), Vector2(UI.W - 200, 420), 16, UI.WHITE, true, 1)


func _draw_barty() -> void:
	if not _barty_on():
		return
	var tex := Frames.loop_frame("barty_wave", t)
	if tex == null:
		tex = Content.texture("ghost.png")
	if tex:
		var bx := Rect2(UI.W - 540, 446, 64, 78)
		var r := UI.fit_rect(tex.get_size(), bx)
		_barty.draw_set_transform(bx.get_center() + Vector2(0, 7 * UI.wsin(t * 1.6 + 1.3)), deg_to_rad(-2.5 * UI.wsin(t * 1.1 + 1.3)))
		_barty.draw_texture_rect(tex, Rect2(r.position - bx.get_center(), r.size), false)
		_barty.draw_set_transform(Vector2.ZERO)


func _draw_bubble() -> void:
	var line := _line()
	if Settings.barty_on() or not line.begins_with("Барти"):
		var tl := Loc.t(line)
		var ls := UI.wrap_lines(tl, 420, 15)
		if ls.size() > 5:
			ls = ls.slice(0, 5)
		var bw2 := 0.0
		for ln in ls:
			bw2 = maxf(bw2, UI.text_width(ln, 15))
		UI.draw_round_rect(_bubble, Rect2(UI.W - 470 - 8, 452 - 4, bw2 + 16, ls.size() * (UI.line_height(15) + 2) - 2 + 8),
			Color8(14, 12, 20, 175), Color(), 0, 8)
		UI.draw_wrapped(_bubble, tl, Vector2(UI.W - 470, 452), 420, 15, UI.GHOST, false, 2, -1, 5)


func _draw_card(b: GameButton, r: Rect2) -> void:
	var job: Dictionary = Content.tech_jobs[int(b.get_meta("i"))]
	var done := SaveGame.is_done(job["id"])
	var art := minf(70, r.size.y - 10)
	var face := Content.texture(job["client_art"])
	if face:
		b.draw_texture_rect(face, UI.fit_rect(face.get_size(), Rect2(r.position.x + 10, r.position.y + floorf((r.size.y - art) / 2), art, art)), false)
	var cw := minf(110, r.size.y + 20)
	var chair := Content.texture(job["chair_art"])
	if chair:
		var cr := UI.fit_rect(chair.get_size(), Rect2(0, 0, cw, art))
		b.draw_texture_rect(chair, Rect2(Vector2(r.end.x - 14 - cw + cr.position.x, r.get_center().y + (10 if done else 0) - art / 2 + cr.position.y), cr.size), false)
	var ty := r.position.y + floorf((r.size.y - 66) / 2)
	var f: Array = UI.fit_text(Loc.t(job["title"]), r.size.x - 96 - cw - 28, 18, true)
	UI.draw_text(b, f[0], Vector2(r.position.x + 96, ty + floorf((18 - int(f[1])) / 2.0)), f[1], UI.WHITE, true)
	UI.draw_text(b, Loc.t(job["client"]), Vector2(r.position.x + 96, ty + 25), 14, UI.GREY)
	UI.draw_text(b, Loc.t("УРОВЕНЬ: ТЕХНИК"), Vector2(r.position.x + 96, ty + 47), 12, UI.PURPLE, true)
	if done:
		UI.draw_text(b, Loc.t("✔ сдано"), Vector2(r.end.x - 14, r.position.y + 12), 15, UI.GOOD, false, 2)
