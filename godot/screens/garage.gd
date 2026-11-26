extends Screen
## Гараж-коллекция (draw_garage/click_garage в game.py): починенные коляски по 9 на страницу (3 × 3) — картинка,
## клиент, поломка, звёзды, «что ты узнал» кратко, «▸ подробнее»; клик по карточке — окно с полным уроком
## («ЧЕМУ НАУЧИЛСЯ», любой клик или Esc закрывает). Листание ◀ ▶, «НАЗАД» — в мастерскую. Пусто — подсказка.

const PER := 9

## Страница гаража — вне экрана (Nav.garage_page), как self.garage_page в game.py (не сбрасывается за сеанс).
var page: int:
	get:                                    # как game.py: min(garage_page, страниц − 1), само число не трогаем
		return clampi(Nav.garage_page, 0, pages() - 1)
	set(v):
		Nav.garage_page = v
var open_idx: int = -1
var _cards: Array[GameButton] = []
var _popup: Control
var _close: GameButton
var _deco: Control


func music_theme() -> String:
	return "workshop"


func summary() -> String:
	return Loc.t("Гараж-коллекция")


func pages() -> int:
	return maxi(1, ceili(SaveGame.garage.size() / float(PER)))


@warning_ignore("integer_division")
func card_rect(k: int) -> Rect2:
	var cols := 3
	var gx := 20
	var gy := 14
	var cw := (UI.W - 80 - (cols - 1) * gx) / cols
	var ch := (UI.H - 76 - 10 - 72 - 2 * gy) / 3
	var x0 := (UI.W - cols * cw - (cols - 1) * gx) / 2
	return Rect2(x0 + (k % cols) * (cw + gx), 72 + (k / cols) * (ch + gy), cw, ch)


func build() -> void:
	_cards.clear()
	add_child(BgLayer.make("bg_garage.png"))
	add_child(TopBar.make("Гараж-коллекция"))
	_deco = Control.new()
	_deco.name = "Deco"
	_deco.size = size
	_deco.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_deco.draw.connect(_draw_deco)
	add_child(_deco)
	var items: Array = range(SaveGame.garage.size()).slice(page * PER, (page + 1) * PER)
	for k in items.size():
		var i: int = items[k]
		var g: Array = SaveGame.garage[i]
		var job := Content.job_by_id(g[0])
		var b := GameButton.make(card_rect(k), "", UI.PURPLE)
		b.name = "Car_" + str(g[0])
		b.set_meta("i", i)
		b.set_meta("k", k)
		b.on_draw = _draw_card
		b.redraw_sig = func() -> int: return 0         # содержимое карточки не меняется (въезд и наведение видит кнопка)
		b.accessibility_name = "%s. %s. %s" % [Loc.t(job.get("client", "")), Loc.t(job.get("title", "")),
			"★".repeat(int(g[1])) + "☆".repeat(3 - int(g[1]))]
		b.pressed.connect(open_card.bind(i))
		add_child(b)
		_cards.append(b)
	if pages() > 1:
		for d: int in [-1, 1]:
			var r := Rect2(UI.W / 2.0 - 120, UI.H - 66, 54, 40) if d < 0 else Rect2(UI.W / 2.0 + 66, UI.H - 66, 54, 40)
			if UI.phone():                       # телефон: стрелки 64×56 у нижнего края
				r = Rect2(UI.W / 2.0 - 120, UI.H - 64, 64, 56) if d < 0 else Rect2(UI.W / 2.0 + 56, UI.H - 64, 64, 56)
			var a := GameButton.make(r, "◀" if d < 0 else "▶", UI.AMBER)
			a.name = "Prev" if d < 0 else "Next"
			a.accessibility_name = Loc.t("Назад") if d < 0 else Loc.t("Дальше")
			a.pressed.connect(func() -> void:
				page = posmod(page + d, pages())
				Audio.sfx("tick")
				rebuild())
			add_child(a)
	var back := GameButton.make(Rect2(40, UI.H - 64, 160, 56) if UI.phone() else Rect2(40, UI.H - 70, 160, 48), "НАЗАД", UI.AMBER)
	back.name = "BackBtn"
	back.pressed.connect(go_back)
	add_child(back)
	Chrome.add(self, true, true, true)
	get_node("Back").set_meta("kb_skip", true)   # в a11y_items game.py гаража — только большая «НАЗАД»
	_popup = Control.new()
	_popup.name = "Popup"
	_popup.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_popup.mouse_filter = Control.MOUSE_FILTER_STOP
	_popup.draw.connect(_draw_popup)
	_popup.gui_input.connect(func(e: InputEvent) -> void:
		if e is InputEventMouseButton and e.pressed:
			if e.button_index == MOUSE_BUTTON_LEFT:
				close_card()                 # окно урока: любой щелчок закрывает (левой, как в game.py; колёсико — нет)
			_popup.accept_event())
	add_child(_popup)
	_close = GameButton.make(Rect2(UI.W / 2.0 - 90, 110 + 470 - 72, 180, 56) if UI.phone()
		else Rect2(UI.W / 2.0 - 90, 110 + 470 - 64, 180, 46), "ЗАКРЫТЬ", UI.AMBER)
	_close.name = "Close"
	_close.pressed.connect(close_card)
	_popup.add_child(_close)
	_popup.visible = open_idx >= 0
	_popup_a11y()                            # пересборка (RU/EN) при открытой карточке — подписи окна на новом языке


func first_focus() -> Control:
	if open_idx >= 0:
		return _close
	return _cards[0] if not _cards.is_empty() else get_node_or_null("BackBtn")


## Окно урока сверху (Nav.sync_focus).
func modal() -> Control:
	return _popup if open_idx >= 0 and _is_modal(_popup) else null


## При окне урока фокус — у окна и, как в game.py, у значков настроек, флажка и языка (они в списке клавиатуры).
func apply_focus() -> void:
	super.apply_focus()
	if modal() != null:
		for n: String in ["Gear", "Flag", "Lang"]:
			var ic := get_node_or_null(n) as Control
			if ic != null and ic.has_meta("_focus_mode"):
				ic.focus_mode = ic.get_meta("_focus_mode")
				ic.remove_meta("_focus_mode")


func _popup_a11y() -> void:
	if open_idx < 0 or open_idx >= SaveGame.garage.size():
		return
	var job := Content.job_by_id(SaveGame.garage[open_idx][0])
	_popup.accessibility_name = Loc.t(job.get("client", ""))
	_popup.accessibility_description = Loc.t("ЧЕМУ НАУЧИЛСЯ") + ": " + Loc.t(job.get("fact", _fact(job)))


func open_card(i: int) -> void:
	open_idx = i
	Audio.sfx("tick")
	_popup.visible = true
	_popup_a11y()
	Nav.sync_focus(_close)


func close_card() -> void:
	if open_idx < 0:
		return
	open_idx = -1
	Audio.sfx("tick")
	_popup.visible = false
	Nav.sync_focus(first_focus())


func go_back() -> void:
	if open_idx >= 0:
		close_card()
		return
	Nav.go("hub")


func tick(_dt: float) -> void:
	for b in _cards:
		b.slide = Vector2(0, int(40 * (1 - UI.appear(st, 0.06 * int(b.get_meta("k")), 0.4))))
	redraw_on(_deco, [page, SaveGame.garage.size()])
	redraw_on(_popup, [open_idx, page])


## Урок задания: fact (у заданий с вариантами — первого варианта, как в данных).
static func _fact(job: Dictionary) -> String:
	if job.has("fact"):
		return job["fact"]
	var vs: Array = job.get("variants", [{}])
	return vs[0].get("fact", "") if not vs.is_empty() else ""


func _draw_deco() -> void:
	if SaveGame.garage.is_empty():
		UI.draw_text(_deco, Loc.t("Пока пусто. Почини хотя бы одну коляску!"), Vector2(UI.W / 2.0, 300), 22, UI.GREY, false, 1)
	if pages() > 1:
		UI.draw_text(_deco, "%d / %d" % [page + 1, pages()], Vector2(UI.W / 2.0, UI.H - 54), 16, UI.WHITE, false, 1)


func _draw_card(b: GameButton, r: Rect2) -> void:
	var g: Array = SaveGame.garage[int(b.get_meta("i"))]
	var job := Content.job_by_id(g[0])
	var stars := int(g[1])
	var art := minf(110, r.size.y - 16)
	var tex := Content.texture(job.get("chair_art", ""))
	if tex:
		b.draw_texture_rect(tex, UI.fit_rect(tex.get_size(), Rect2(r.position.x + 8, r.position.y + floorf((r.size.y - art) / 2), art, art)), false)
	var tx := r.position.x + art + 18
	var tw := r.size.x - art - 28
	var y := UI.draw_wrapped(b, Loc.t(job.get("client", "")), Vector2(tx, r.position.y + 10), tw, 15, UI.WHITE, false, 2, -1, 2)
	y = UI.draw_wrapped(b, Loc.t(job.get("title", "")), Vector2(tx, y), tw, 12, UI.GREY, false, 2, -1, 2)
	UI.draw_text(b, "★".repeat(stars) + "☆".repeat(3 - stars), Vector2(tx, y + 2), 16, UI.AMBER)
	var lh := UI.line_height(11) + 2
	var left := maxi(1, int((r.end.y - 22 - (y + 24)) / lh))
	UI.draw_wrapped(b, Loc.t(_fact(job)), Vector2(tx, y + 24), tw, 11, UI.GHOST, false, 2, -1, left)
	UI.draw_text(b, "▸ " + Loc.t("подробнее"), Vector2(r.end.x - 10, r.end.y - 18), 11, UI.CYAN, false, 2)


func _draw_popup() -> void:
	if open_idx < 0 or open_idx >= SaveGame.garage.size():
		return
	_popup.draw_rect(Rect2(0, 0, UI.W, UI.H), Color8(8, 8, 12, 170))
	var g: Array = SaveGame.garage[open_idx]
	var job := Content.job_by_id(g[0])
	var stars := int(g[1])
	var p := Rect2(UI.W / 2.0 - 380, 110, 760, 470)
	UI.draw_round_rect(_popup, p, Color8(20, 18, 30, 248), UI.PURPLE, 2, 14)
	var chair := Content.texture(job.get("chair_art", ""))
	if chair:
		_popup.draw_texture_rect(chair, UI.fit_rect(chair.get_size(), Rect2(p.position + Vector2(24, 24), Vector2(170, 170))), false)
	var face := Content.texture(job.get("client_art", ""))
	if face:
		_popup.draw_texture_rect(face, UI.fit_rect(face.get_size(), Rect2(p.position + Vector2(54, 210), Vector2(110, 130))), false)
	var x := p.position.x + 220
	var w := p.size.x - 250
	var y := UI.draw_wrapped(_popup, Loc.t(job.get("client", "")), Vector2(x, p.position.y + 26), w, 22, UI.WHITE)
	y = UI.draw_wrapped(_popup, Loc.t(job.get("title", "")), Vector2(x, y + 2), w, 16, UI.GREY)
	UI.draw_text(_popup, "★".repeat(stars) + "☆".repeat(3 - stars), Vector2(x, y + 6), 22, UI.AMBER)
	UI.draw_text(_popup, Loc.t("ЧЕМУ НАУЧИЛСЯ"), Vector2(x, y + 46), 15, UI.CYAN, true)
	var fy := y + 70
	var fact := Loc.t(_fact(job))
	var fsz := 17
	while fsz > 12 and UI.wrap_lines(fact, w, fsz).size() * (UI.line_height(fsz) + 3) > p.end.y - 80 - fy:
		fsz -= 1
	UI.draw_wrapped(_popup, fact, Vector2(x, fy), w, fsz, UI.WHITE, false, 3)
