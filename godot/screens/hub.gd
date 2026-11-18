extends Screen
## Мастерская (draw_hub): «Кто сегодня в очереди на ремонт:», карточки клиентов 4×2 из данных (коляска крупно,
## портрет в кружке, имя, поломка, РУЧНАЯ/ЭЛЕКТРО, отметка «✔ готово»), листание ◀ ▶ с точками страниц, Барти,
## кнопки «Кабинет посадки», «Гильдия колёсников», «Гараж-коллекция» (пока — заглушки с тем же видом),
## счётчик «Починено: N/21». При наведении/фокусе на карточке — записка клиента (с чем пришёл / спасибо).

const COLS := 4
const ROWS := 2

var page: int = 0
var _cards: Array[ClientCard] = []
var _note: Control
var _deco: Control
var _note_jid: String = ""
var _note_t0: float = 0.0


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
	var seat_ok := SaveGame.tutorial_ok()
	var seat := GameButton.make(Rect2(UI.W - 360, UI.H - 290, 300, 54), "КАБИНЕТ ПОСАДКИ", UI.GOOD,
		Loc.fmt("примерки {0}/{1}", [SaveGame.seat_done.size(), 9]) + (" · зачёт ✔" if SaveGame.seat_quiz_ok else "")
		if seat_ok else "откроется после первого ремонта")
	seat.name = "Seating"
	seat.enabled = seat_ok
	seat.update_a11y()
	seat.pressed.connect(func() -> void:
		if seat_ok:
			Nav.flash("Кабинет посадки появится в следующих шагах переноса.", UI.CYAN, 3.0)
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
	_note = Control.new()
	_note.name = "Note"
	_note.size = size
	_note.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_note.draw.connect(_draw_note)
	add_child(_note)
	Chrome.add(self, true, true, true)


@warning_ignore("integer_division")
func _pages() -> int:
	var per := COLS * ROWS
	return maxi(1, (SaveGame.available_jobs().size() + per - 1) / per)


func first_focus() -> Control:
	return _cards[0] if not _cards.is_empty() else null


func toast_bounds() -> Vector2:
	return Vector2(54, 164)


func summary() -> String:
	return Loc.t("Мастерская") + ". " + Loc.t("Кто сегодня в очереди на ремонт:")


func go_back() -> void:
	Nav.go("title")


func tick(_dt: float) -> void:
	for b in _cards:
		var i: int = b.get_meta("i")
		b.slide = Vector2(0, int(60 * (1 - UI.appear(st, 0.05 * i, 0.4))))
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
	UI.draw_text(_deco, Loc.t("Кто сегодня в очереди на ремонт:"), Vector2(60, 86), 20, UI.WHITE, true)
	var pages := _pages()
	if pages > 1:
		var cx := (60 + 54 + 60 + 4 * 214 - 14 - 54) / 2.0
		for k in pages:
			_deco.draw_circle(Vector2(cx + (k - (pages - 1) / 2.0) * 22, 657), 6, UI.AMBER if k == page else UI.DIM,
				true, -1, true)
	var counter := Loc.fmt("Починено: {0}/{1}", [SaveGame.user_done_count(), Content.jobs.size()])
	if SaveGame.guild_unlocked():
		counter += Loc.fmt("   ·   Гильдия: {0}/{1}", [SaveGame.tech_done_count(), Content.tech_jobs.size()])
	counter += "   ·   Esc — на титул/выход"
	UI.draw_text(_deco, Loc.t(counter), Vector2(60, UI.H - 40), 16, UI.GHOST)


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
