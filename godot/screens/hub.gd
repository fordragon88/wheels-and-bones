extends Screen
## Мастерская (draw_hub): «Кто сегодня в очереди на ремонт:», карточки клиентов 4×2 из данных (коляска крупно,
## портрет в кружке, имя, поломка, РУЧНАЯ/ЭЛЕКТРО, отметка «✔ готово»), листание ◀ ▶ с точками страниц, Барти,
## кнопки «Кабинет посадки», «Гильдия колёсников», «Гараж-коллекция» (пока — заглушки с тем же видом),
## счётчик «Починено: N/21». При наведении/фокусе на карточке — записка клиента (с чем пришёл / спасибо).
## Задание по ссылке (_draw_hub_assign): плашка «Задание от X: k/N», только назначенные поломки, справа — «Кабинет
## посадки» (если в задании есть примерки), «Итог задания», «Выйти из задания». Запуск без ссылки при незаконченном
## задании — вопрос «продолжить задание / обычная игра» (Share.maybe_ask_resume, просьба владельца).

const COLS := 4
const ROWS := 2

var page: int = 0
var _cards: Array[ClientCard] = []
var _note: Control
var _deco: Control
var _note_jid: String = ""
var _note_t0: float = 0.0
var _note_sig: Array = []


@warning_ignore("integer_division")
func build() -> void:
	_cards.clear()
	add_child(BgLayer.make("bg_workshop.png"))
	add_child(TopBar.make("Мастерская"))
	_deco = Control.new()
	_deco.name = "Deco"
	_deco.size = size
	_deco.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_deco.draw.connect(_draw_deco)
	add_child(_deco)
	var ids := SaveGame.available_jobs()
	var pages := _pages()
	page = clampi(page, 0, pages - 1)
	var per := COLS * ROWS
	var i := 0
	for jid: String in ids.slice(page * per, (page + 1) * per):
		var b := ClientCard.make_card(jid, Rect2(60 + (i % COLS) * 214, 124 + (i / COLS) * 262, 200, 250))
		b.set_meta("job", jid)
		b.set_meta("i", i)
		b.pressed.connect(_open_job.bind(jid))
		b.focus_entered.connect(func() -> void: _set_note(jid if UI.kb_active else ""))
		b.hovered_changed.connect(func(on: bool) -> void: _set_note(jid if on else ""))
		add_child(b)
		_cards.append(b)
		i += 1
	if pages > 1:
		for d: int in [-1, 1]:
			var ar := Rect2(60, 642, 54, 30) if d < 0 else Rect2(60 + 4 * 214 - 14 - 54, 642, 54, 30)
			var a := GameButton.make(ar, "◀" if d < 0 else "▶", UI.AMBER)
			a.name = "Prev" if d < 0 else "Next"
			a.accessibility_name = Loc.t("Назад") if d < 0 else Loc.t("Дальше")
			a.pressed.connect(_flip.bind(d))
			add_child(a)
	if Settings.barty_on():
		var g := Figure.make("ghost.png", Vector2(UI.W - 220, 120), Vector2(150, 200), "float", "barty_wave")
		g.name = "Barty"
		add_child(g)
	if SaveGame.assign_on():
		_build_assign()
	else:
		_build_normal()
	_note = Control.new()
	_note.name = "Note"
	_note.size = size
	_note.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_note.draw.connect(_draw_note)
	add_child(_note)
	Chrome.add(self, true, true, true)
	if params.get("summary", false):
		params.erase("summary")
		Share.maybe_summary.call_deferred(true)
	else:
		Share.maybe_ask_resume.call_deferred()


## Задание по ссылке: «Кабинет посадки» (если есть примерки), «Итог задания», «Выйти из задания».
func _build_assign() -> void:
	var a := SaveGame.assign
	if not (a["seat"] as Array).is_empty():
		var k := 0
		for c: String in a["seat"]:
			if (a["done"] as Dictionary).has(c):
				k += 1
		var seat := GameButton.make(Rect2(UI.W - 360, UI.H - 290, 300, 54), "КАБИНЕТ ПОСАДКИ", UI.GOOD,
			Loc.fmt("примерки {0}/{1}", [k, (a["seat"] as Array).size()]))
		seat.name = "Seating"
		seat.pressed.connect(func() -> void: Nav.go("seating"))
		add_child(seat)
	var res := GameButton.make(Rect2(UI.W - 360, UI.H - 220, 300, 54), "ИТОГ ЗАДАНИЯ", UI.CYAN,
		"всё выполнено ✔" if SaveGame.assign_complete() else "что уже сделано")
	res.name = "Summary"
	res.pressed.connect(func() -> void: Share.open({"mode": "summary"}))
	add_child(res)
	var ex := GameButton.make(Rect2(UI.W - 360, UI.H - 150, 300, 54), "ВЫЙТИ ИЗ ЗАДАНИЯ", UI.PURPLE, "в обычную игру")
	ex.name = "ExitAssign"
	ex.pressed.connect(Share.exit_assignment)
	add_child(ex)


## Плашка задания: «Задание от Имя: 1/3» (_hub_assign_label).
static func assign_label() -> String:
	var a := SaveGame.assign
	var n := Share.assign_items(a).size()
	var k := (a["done"] as Dictionary).size()
	return Loc.fmt("Задание от {0}: {1}/{2}", [a["from"], k, n]) if a.get("from", "") != "" else Loc.fmt("Задание: {0}/{1}", [k, n])


func _build_normal() -> void:
	var seat_ok := SaveGame.tutorial_ok()
	var seat := GameButton.make(Rect2(UI.W - 360, UI.H - 290, 300, 54), "КАБИНЕТ ПОСАДКИ", UI.GOOD,
		Loc.fmt("примерки {0}/{1}", [SaveGame.seat_done.size(), 9]) + (" · зачёт ✔" if SaveGame.seat_quiz_ok else "")
		if seat_ok else "откроется после первого ремонта")
	seat.name = "Seating"
	seat.enabled = seat_ok
	seat.update_a11y()
	seat.pressed.connect(func() -> void:
		if seat_ok:
			Nav.go("seating")
		else:
			Nav.flash("Кабинет посадки откроется после первого ремонта.", UI.CYAN, 3.0))
	add_child(seat)
	var guild_ok := SaveGame.guild_unlocked()
	var req := int(Content.consts.get("guild_req", 5))
	var guild := GameButton.make(Rect2(UI.W - 360, UI.H - 220, 300, 54), "ГИЛЬДИЯ КОЛЁСНИКОВ", UI.CYAN,
		"про-ремонт: уровень техника" if guild_ok else Loc.fmt("откроется после {0} ремонтов", [req]))
	guild.name = "Guild"
	guild.enabled = guild_ok
	guild.update_a11y()
	guild.pressed.connect(func() -> void:
		if guild_ok:
			Audio.sfx("tick")
			Nav.go("guild")
		else:
			Nav.flash(Loc.fmt("Гильдия Колёсников примет тебя после {0} починенных колясок.", [req]), UI.CYAN, 3.5))
	add_child(guild)
	var garage := GameButton.make(Rect2(UI.W - 360, UI.H - 150, 300, 54), "ГАРАЖ-КОЛЛЕКЦИЯ", UI.PURPLE)
	garage.name = "Garage"
	garage.pressed.connect(func() -> void:
		Audio.sfx("tick")
		Nav.go("garage"))
	add_child(garage)
	if SaveGame.user_done_count() >= Content.jobs.size():
		var party := GameButton.make(Rect2(UI.W - 360, UI.H - 80, 300, 54), "НА ВЕЧЕРИНКУ! ", UI.GOOD)
		party.name = "Party"
		party.pressed.connect(func() -> void:
			Audio.sfx("tick")
			Nav.go("ending"))
		add_child(party)


@warning_ignore("integer_division")
func _pages() -> int:
	var per := COLS * ROWS
	return maxi(1, (SaveGame.available_jobs().size() + per - 1) / per)


func first_focus() -> Control:
	return _cards[0] if not _cards.is_empty() else null


func toast_bounds() -> Vector2:
	return Vector2(54, 164)


func summary() -> String:
	if SaveGame.assign_on():
		return Loc.t("Мастерская.") + " " + Loc.t(assign_label()) + ". " + 			Loc.t("Стрелки — выбрать клиента, Enter — взять заказ, Tab — другие разделы.")
	return "%s %s: %s. " % [Loc.t("Мастерская."), Loc.t("Починено"), A11y._of(SaveGame.user_done_count(), Content.jobs.size())] + \
		Loc.t("Стрелки — выбрать клиента, Enter — взять заказ, Tab — другие разделы.")


func go_back() -> void:
	Nav.go("title")


func tick(_dt: float) -> void:
	for b in _cards:
		var i: int = b.get_meta("i")
		b.slide = Vector2(0, int(60 * (1 - UI.appear(st, 0.05 * i, 0.4))))
	# записка: перерисовка, пока выпрыгивает, и когда сменилась (иначе картинка та же)
	var sig := [_note_jid, minf(1.0, (t - _note_t0) / 0.25) if _note_jid != "" else 0.0]
	if sig != _note_sig:
		_note_sig = sig
		_note.queue_redraw()


func _flip(d: int) -> void:
	page = posmod(page + d, _pages())
	st = 0.0                                 # карточки въезжают заново
	Audio.sfx("tick")
	rebuild()
	var nb := get_node_or_null("Next" if d > 0 else "Prev")
	if nb is Control:
		(nb as Control).grab_focus()


func _open_job(jid: String) -> void:
	Audio.sfx("tick")
	Nav.go("job", {"job": jid})


func _set_note(jid: String) -> void:
	if jid == "":
		var f := get_viewport().gui_get_focus_owner()
		if f is GameButton and f.has_meta("job") and UI.kb_active:
			jid = f.get_meta("job")
	if jid != _note_jid:
		_note_jid = jid
		_note_t0 = t


func _draw_deco() -> void:
	var asg := SaveGame.assign_on()
	if not asg:
		UI.draw_text(_deco, Loc.t("Кто сегодня в очереди на ремонт:"), Vector2(60, 86), 20, UI.WHITE, true)
	var pages := _pages()
	if pages > 1:
		var cx := (60 + 54 + 60 + 4 * 214 - 14 - 54) / 2.0
		for k in pages:
			_deco.draw_circle(Vector2(cx + (k - (pages - 1) / 2.0) * 22, 657), 6, UI.AMBER if k == page else UI.DIM,
				true, -1, true)
	if asg:
		_draw_assign_plate()
		UI.draw_text(_deco, Loc.t(assign_label() + "   ·   Esc — на титул/выход"), Vector2(60, UI.H - 40), 16, UI.GHOST)
		return
	var counter := Loc.fmt("Починено: {0}/{1}", [SaveGame.user_done_count(), Content.jobs.size()])
	if SaveGame.guild_unlocked():
		counter += Loc.fmt("   ·   Гильдия: {0}/{1}", [SaveGame.tech_done_count(), Content.tech_jobs.size()])
	counter += "   ·   Esc — на титул/выход"
	UI.draw_text(_deco, Loc.t(counter), Vector2(60, UI.H - 40), 16, UI.GHOST)


func _fit(s: String, pos: Vector2, width: float, size_: int, col: Color, bold: bool = false) -> void:
	var f: Array = UI.fit_text(s, width, size_, bold)
	@warning_ignore("integer_division")
	UI.draw_text(_deco, f[0], Vector2(pos.x, pos.y + (size_ - int(f[1])) / 2), f[1], col, bold)


## Плашка задания по ссылке сверху (_draw_hub_assign).
func _draw_assign_plate() -> void:
	var a := SaveGame.assign
	var plate := Rect2(56, 62, 4 * 214 - 10, 54)
	UI.draw_round_rect(_deco, plate, Color8(24, 20, 30, 235), UI.GOOD, 2, 10)
	_fit(Loc.t(assign_label()), plate.position + Vector2(16, 6), plate.size.x - 32, 20, UI.GOOD, true)
	var sub := "Только эти задания, по порядку. Обычный прогресс не меняется."
	if a.get("title", "") != "":
		sub = "«%s» · Только эти задания, по порядку. Обычный прогресс не меняется." % a["title"]
	_fit(Loc.t(sub), plate.position + Vector2(16, 32), plate.size.x - 32, 13, UI.GREY)
	if (a["jobs"] as Array).is_empty():
		UI.draw_wrapped(_deco, Loc.t("Поломок в задании нет — задание в Кабинете посадки (кнопка справа)."), Vector2(60, 160),
			4 * 214 - 40, 18, UI.WHITE)


## Записка клиента у карточки (_draw_hub_note): с чем пришёл, после ремонта — спасибо.
func _draw_note() -> void:
	if _note_jid == "":
		return
	var card: ClientCard = null
	for b in _cards:
		if b.get_meta("job") == _note_jid:
			card = b
	if card == null:
		return
	var job := Content.job_by_id(_note_jid)
	var done := SaveGame.is_done(_note_jid)
	var thanks: String = job.get("thanks", "")
	if thanks == "" and job.has("variants"):
		thanks = job["variants"][0].get("thanks", "")
	var intro: Array = Content.client_talk(_note_jid).get("intro", [""])
	var line := Loc.t(thanks if done else (intro[0] if not intro.is_empty() else ""))
	if line == "":
		return
	var colon := line.find(":")
	var nm := line.substr(0, colon).strip_edges() if colon >= 0 else ""
	var text := line.substr(colon + 1).strip_edges() if colon >= 0 else line
	var w := 320.0
	var lines := UI.wrap_lines(text, w - 28, 14)
	if lines.size() > 5:
		lines = lines.slice(0, 5)
	var h := 38 + lines.size() * (UI.line_height(14) + 2) + 10
	var r := Rect2(card.position, card.size)
	var right := 60 + COLS * 214 - 14
	var x := minf(maxf(12, r.get_center().x - w / 2), right - w)
	var y := r.end.y + 6 if r.end.y + 6 + h < UI.H - 50 else r.position.y - h - 6
	var k := UI.ease_back((t - _note_t0) / 0.25)
	var c := Vector2(x + w / 2, y + h / 2)
	_note.draw_set_transform(c, 0.0, Vector2(maxf(0.05, k), maxf(0.05, k)))
	var box := Rect2(-w / 2, -h / 2, w, h)
	UI.draw_round_rect(_note, box, Color8(238, 226, 196, 245), Color8(120, 92, 52), 2, 8)
	UI.draw_text(_note, ("✔ " if done else "✉ ") + (nm if nm != "" else Loc.t(job["client"])),
		box.position + Vector2(14, 9), 14, Color8(110, 70, 30), true)
	UI.draw_wrapped(_note, " ".join(lines), box.position + Vector2(14, 34), w - 28, 14, Color8(52, 40, 30), false, 2, -1, 5)
	_note.draw_set_transform(Vector2.ZERO)
