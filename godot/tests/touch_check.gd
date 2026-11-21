extends Node
## Сенсорный экран: запас на промах пальцем, как в game.py (TOUCH_PAD, _touch_pick, _touch_snap, Game._tap,
## _hotspot_at). Числа — те же, что в selftest game.py (блок «запас на промах пальцем»), плюс события Godot:
## тап мимо цели доходит до кнопки (Nav._input → Nav.touch_snap), с мышью — нет. Зовёт самопроверка
## (tests/selftest_runner.gd, отдельно «-- --test --only touch»). run(R) → строка для итога; ошибки — R.err().

var R: Node
var _n := 0


func run(runner: Node) -> String:
	R = runner
	var t0: int = UI._touch
	_pick_numbers()
	await _hub()
	await _job()
	await _settings()
	UI._touch = t0
	Nav.go("hub")
	await R._frames(1)
	SaveGame.reset()
	return "запас пальца (как game.py): %d проверок — _touch_pick (pad 16, точное попадание первым, ключ 0), карточка " \
		% _n + "мастерской ±16/17 px, плитка инструмента −6 px, коляска — без переноса, кружок детали r+16, «+»/«−», ⚙ +9 px, " \
		+ "ползунок громкости — block; с мышью всё точно"


func _ok(cond: bool, msg: String) -> void:
	_n += 1
	if not cond:
		R.err("сенсор: " + msg)


func _tap(pos: Vector2) -> void:
	var m := InputEventMouseMotion.new()
	m.position = pos
	m.global_position = pos
	get_viewport().push_input(m, true)
	for pressed: bool in [true, false]:
		var e := InputEventMouseButton.new()
		e.button_index = MOUSE_BUTTON_LEFT
		e.pressed = pressed
		e.position = pos
		e.global_position = pos
		get_viewport().push_input(e, true)
	await R._frames(2)


# ---- _touch_pick / _touch_snap: те же прямоугольники и точки, что в selftest game.py ----
func _pick_numbers() -> void:
	var ra := Rect2(100, 100, 50, 50)
	var rb := Rect2(158, 100, 50, 50)                       # соседние плитки, зазор 8
	var pad := UI.TOUCH_PAD
	_ok(pad == 16 and UI.TOUCH_TAP_GROW == 9 and UI.TOUCH_SPOT_PAD == 16,
		"числа запаса %d/%d/%d, в game.py 16 / inflate(18) / 16" % [pad, UI.TOUCH_TAP_GROW, UI.TOUCH_SPOT_PAD])
	_ok(UI.touch_pick([ra, rb], Vector2(150, 120), pad, true) == 0 and UI.touch_pick([ra, rb], Vector2(158, 120), pad, true) == 1,
		"_touch_pick: точное попадание/ближайший сосед")
	_ok(UI.touch_pick([ra], Vector2(ra.end.x - 1 + pad - 1, 120), pad, true) == 0, "_touch_pick: промах на pad−1 px не попал")
	_ok(UI.touch_pick([ra], Vector2(ra.end.x - 1 + pad, 120), pad, true) == 0, "_touch_pick: промах ровно на pad px не попал")
	_ok(UI.touch_pick([ra], Vector2(ra.end.x - 1 + pad + 2, 120), pad, true) == -1, "_touch_pick: промах на pad+2 px попал")
	_ok(UI.touch_pick([ra], Vector2(ra.position.x - 3, ra.position.y), pad, true) == 0, "_touch_pick: ключ 0 потерян")
	_ok(UI.touch_pick([ra], Vector2(ra.end.x + 2, 120), pad, false) == -1, "_touch_pick: без сенсорного режима появился запас")
	_ok(UI.touch_snap(Vector2(5, 5), [ra], [], false) == Vector2(5, 5), "_touch_snap: без сенсорного режима тап сдвинут")
	_ok(UI.touch_snap(Vector2(155, 120), [ra], [], true) == ra.get_center(), "_touch_snap: тап рядом — не в центр цели")
	_ok(UI.touch_snap(Vector2(155, 120), [ra], [Rect2(152, 110, 10, 20)], true) == Vector2(155, 120),
		"_touch_snap: тап в зоне block перенесён")
	_ok(UI.touch_snap(Vector2(160, 120), [ra, rb], [], true) == Vector2(160, 120), "_touch_snap: точное попадание перенесено")


# ---- мастерская: карточка клиента (click_hub), ⚙ шире пальца (Game._tap) ----
func _hub() -> void:
	SaveGame.reset()
	Nav.go("hub")
	await R._frames(2)
	var card: Control = null
	for c: Node in Nav.current.get_children():
		if c is ClientCard and c.get_meta("job", "") == "flat":
			card = c
	if card == null:
		R.err("сенсор: нет карточки flat в мастерской")
		return
	var r := card.get_global_rect()
	var y := r.get_center().y
	UI._touch = 1
	_ok(Nav.touch_snap(Vector2(r.position.x - 16, y)) == r.get_center(), "мастерская: тап на 16 px левее карточки не в неё")
	_ok(Nav.touch_snap(Vector2(r.position.x - 17, y)) == Vector2(r.position.x - 17, y), "мастерская: тап на 17 px левее карточки — в неё")
	var seat: Control = Nav.current.get_node_or_null("Seating")
	if seat:
		var sp := Vector2(seat.get_global_rect().position.x - 8, seat.get_global_rect().get_center().y)
		_ok(Nav.touch_snap(sp) == sp, "мастерская: большие кнопки справа — не цели переноса (в game.py block)")
	var gear: Control = Nav.current.get_node_or_null("Gear")
	var gp := gear.get_global_rect().end + Vector2(6, -19) if gear else Vector2.ZERO
	_ok(gear != null and UI.hits(gear, gp), "⚙: на сенсоре касание на 6 px правее не попало (Game._tap inflate(18, 18))")
	_ok(gear != null and not UI.hits(gear, gear.get_global_rect().end + Vector2(10, -19)), "⚙: запас больше 9 px")
	UI._touch = 0
	_ok(Nav.touch_snap(Vector2(r.position.x - 10, y)) == Vector2(r.position.x - 10, y), "мышь: клик мимо карточки перенесён")
	_ok(gear != null and not UI.hits(gear, gp), "мышь: ⚙ шире, чем был")
	# событиями: мышь мимо — ничего; палец мимо на 10 px — задание
	await _tap(Vector2(r.position.x - 10, y))
	_ok(Nav.current_name == "hub", "мышь: клик на 10 px левее карточки открыл задание")
	UI._touch = 1
	await _tap(Vector2(r.position.x - 10, y))
	_ok(Nav.current_name == "job" and Nav.current.job.get("id", "") == "flat",
		"тап на 10 px левее карточки не открыл задание (экран %s)" % Nav.current_name)
	UI._touch = 0


# ---- задание: плитка инструмента −6 px (как selftest game.py), коляска — block, кружок детали r+16, «+»/«−» ----
func _job() -> void:
	Nav.go("job", {"job": "flat", "variant": 0})
	await R._frames(2)
	var j: Node = Nav.current
	# кружок детали: на сенсоре r + 16, из соседних — ближайший (_hotspot_at); мышь — r + 4
	j.chair.t0 = -1e9
	await R._frames(1)
	var sp: Array = j.chair.spot_of("brake")
	var b: HotspotButton = j.chair.spot_button("brake")
	if sp.is_empty() or b == null:
		R.err("сенсор: нет кружка brake у flat")
	else:
		var c: Vector2 = Vector2(sp[1], sp[2]) + j.chair.get_parent().global_position
		var off := Vector2(sp[3] + 12, 0)                  # 12 px за кольцом: палец — да, мышь (r + 4) — нет
		UI._touch = 1
		_ok(UI.hits(b, c + off) and j.chair.hotspot_at(c + off - j.chair.get_parent().global_position, UI.TOUCH_SPOT_PAD) == "brake",
			"кружок brake: на сенсоре тап на r+12 мимо")
		_ok(not UI.hits(b, c + Vector2(sp[3] + 17, 0)), "кружок brake: на сенсоре попадание дальше r+16")
		UI._touch = 0
		_ok(not UI.hits(b, c + off) and UI.hits(b, c + Vector2(sp[3] + 3, 0)), "мышь: зона кружка не r+4")
	# «+»/«−»: _touch_pick с запасом 16 (правее кнопки, за краем окна коляски)
	var zin: Control = j.get_node_or_null("ZoomIn")
	if zin:
		var zp := Vector2(zin.get_global_rect().end.x + 10, zin.get_global_rect().get_center().y)
		UI._touch = 1
		_ok(UI.hits(zin, zp), "«+»: на сенсоре тап на 10 px правее не попал")
		UI._touch = 0
		_ok(not UI.hits(zin, zp), "мышь: «+» шире, чем был")
	# ремонт: плитка инструмента
	j.phase = "repair"
	j.rebuild()
	await R._frames(2)
	j = Nav.current
	j.sel_tool = ""
	var tid0: String = j.tools.tiles.keys()[0]
	var tr0: Rect2 = (j.tools.tiles[tid0] as Control).get_global_rect()
	var miss := Vector2(tr0.position.x - 6, tr0.get_center().y)
	await _tap(miss)
	_ok(j.sel_tool == "", "мышь: клик мимо плитки инструмента выбрал её (%s)" % j.sel_tool)
	UI._touch = 1
	await _tap(miss)
	_ok(j.sel_tool == tid0, "тап рядом с плиткой инструмента её не выбрал (%s)" % j.sel_tool)
	j.sel_tool = ""
	# тап по коляске (не по кружку) — без переноса: инструмент не выбран, коляска вертится
	var cr: Rect2 = j.chair.get_global_rect()
	var mid := cr.get_center()
	var found := false
	for yy in range(int(cr.get_center().y), int(cr.end.y) - 8, 6):
		for xx in range(int(cr.get_center().x) - 60, int(cr.get_center().x) + 61, 6):
			var q := Vector2(xx, yy)
			if j.chair.hotspot_at(q - j.chair.get_parent().global_position, UI.TOUCH_SPOT_PAD) == "" \
					and Nav.touch_snap(q) == q and q.distance_to(miss) > 200:
				mid = q
				found = true
				break
		if found:
			break
	_ok(found, "коляска: не нашлось точки без кружка (окно коляски — block)")
	await _tap(mid)
	_ok(j.sel_tool == "", "тап по коляске %s выбрал инструмент %s" % [mid, j.sel_tool])
	# мини-окно: свой список целей (_mini_touch_targets), дорожка зазора — block
	UI._touch = 0


# ---- настройки: вкладка — цель, ползунок громкости — block (inflate(24, 30)) ----
func _settings() -> void:
	Nav.go("hub")
	await R._frames(1)
	Nav.open_settings()
	await R._frames(2)
	var s: Control = Nav.settings
	if s == null:
		R.err("сенсор: настройки не открылись")
		return
	UI._touch = 1
	var tab: Control = s.get_node_or_null("Tab_graphics")
	if tab:
		var tr := tab.get_global_rect()
		var p := Vector2(tr.get_center().x, tr.end.y - 1 + 10)
		_ok(Nav.touch_snap(p) == tr.get_center() or Nav.touch_snap(p) == p and _covered(s, p),
			"настройки: тап на 10 px ниже вкладки не в неё")
	var vol: Control = s.get_node_or_null("Vol_master")
	if vol:
		var vr := vol.get_global_rect()
		var q := Vector2(vr.get_center().x, vr.position.y + 2)   # в зоне inflate(24, 30) дорожки — не переносим
		_ok(Nav.touch_snap(q) == q, "настройки: тап по ползунку громкости перенесён")
	UI._touch = 0
	Nav.close_settings()
	await R._frames(1)


## Точка занята другой кнопкой окна (тогда переноса и не должно быть).
func _covered(root: Control, p: Vector2) -> bool:
	for n: Node in root.find_children("*", "BaseButton", true, false):
		if (n as Control).is_visible_in_tree() and (n as Control).get_global_rect().has_point(p):
			return true
	return false
