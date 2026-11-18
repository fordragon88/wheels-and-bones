extends Screen
## Кабинет посадки некроманта Мортимера (open_seating/draw_seating/click_seating в game.py): вкладки «УРОКИ»,
## «ПРИМЕРКА», «ПРОВЕРЬ СЕБЯ»; Мортимер с репликой над схемой (печать по буквам). Уроки — 7 карточек, поза с
## ошибкой и «ПОКАЗАТЬ НОРМУ»; примерка — 9 клиентов, ползунки (мышь, палец, ←/→ на ползунке в фокусе), список
## проверок и «ГОТОВО — ПРОВЕРИТЬ ПОСАДКУ» (seat_done); зачёт — 7 вопросов, после ответа рисунок плавно переходит к
## правильной посадке (0,7 с; при неверном — сначала 1,2 с ошибка), 6 верных — зачёт (seat_quiz_ok).
## Рисунок — SeatFigure: вид сбоку; спереди — примерка (_seat_front_fit) у клиентов с перекосом таза и схема урока 4 и
## вопросов 6–7 (_seat_front: дуга сколиоза, подкладка, три упора); сверху — поворот таза (_seat_top).

const CV := Rect2(24, 176, 730, 488)
const BTN := Rect2(780, 612, 476, 48)
const BACK := Rect2(UI.W - 230, 64, 206, 38)
const TOGGLE := Rect2(24 + 730 - 238, 176 + 8, 228, 32)
const BUBBLE := Rect2(96, 110, 658, 60)
const TAB_NAMES := {"lessons": "УРОКИ", "fit": "ПРИМЕРКА", "quiz": "ПРОВЕРЬ СЕБЯ"}

var tab: String = "lessons"
var lesson: int = 0
var case_i: int = 0
var cfg: Dictionary = {}
var drag: String = ""
var focus_key: String = ""
var quiz_i: int = 0
var picked: int = -1
var score: int = 0
var quiz_done: bool = false
var solved: bool = false
var demo_good: bool = false
var view: String = "side"
var fails: int = 0
var say: String = ""
var fix_t0: float = -99.0
var quiz: Array = []                      # вопросы зачёта с перемешанными вариантами (верный — не всегда первым)

var fig: SeatFigure
var _back: Control                        # подложка рамки и реплика Мортимера
var _fg: Control                          # тексты поверх рисунка
var _dyn: Control                         # кнопки, которые меняются вместе с вкладкой/клиентом/вопросом
var _typing: Array = ["", 0.0]
var _said: String = ""
var sliders: Dictionary = {}              # ключ → SeatSlider


func music_theme() -> String:
	return "workshop"


func _init() -> void:
	super._init()
	quiz = Content.seating.get("quiz", []).duplicate(true)
	_shuffle_quiz()
	load_case(0)
	say = mentor("intro")


func mentor(key: String) -> String:
	return str(Content.seating.get("mentor", {}).get(key, ""))


func _shuffle_quiz() -> void:
	for q: Dictionary in quiz:
		(q["options"] as Array).shuffle()


func cases() -> Array:
	return SeatLogic.cases()


func lessons() -> Array:
	return Content.seating.get("lessons", [])


func load_case(i: int) -> void:
	var c: Dictionary = cases()[i]
	cfg = (c["start"] as Dictionary).duplicate()
	if not cfg.has("tilt"):
		cfg["tilt"] = 0
	case_i = i
	solved = false
	view = str(c.get("view", "side"))
	focus_key = ""
	fails = 0
	say = mentor("view_" + str(c["view"])) if c.get("view") else mentor("fit")


func slider_keys() -> Array:
	var c: Dictionary = cases()[case_i]
	if c.get("sliders"):
		return c["sliders"]
	return ["depth", "leg", "back_h", "back_a"] + (["tilt"] if c.get("tilt") else [])


@warning_ignore("integer_division")
func slider_rect(i: int) -> Rect2:
	var row_h := ((cases().size() + 1) / 2) * 40
	return Rect2(800, 112 + row_h + 26 + i * 44, 290, 8)


@warning_ignore("integer_division")
func list_rect(i: int) -> Rect2:
	if tab == "lessons":
		return Rect2(780 + (i % 2) * 238, 112 + (i / 2) * 44, 230, 38)
	return Rect2(780 + (i % 2) * 238, 112 + (i / 2) * 40, 230, 35)


func quiz_rect(i: int) -> Rect2:
	return Rect2(780, 260 + i * 92, 476, 82)


# ---------------- сборка ----------------

func build() -> void:
	add_child(BgLayer.make("bg_workshop.png"))
	add_child(TopBar.make("Кабинет посадки некроманта Мортимера"))
	_back = Control.new()
	_back.name = "Back"
	_back.size = size
	_back.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_back.draw.connect(_draw_back)
	add_child(_back)
	fig = SeatFigure.new()
	add_child(fig)
	_fg = Control.new()
	_fg.name = "Fg"
	_fg.size = size
	_fg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_fg.draw.connect(_draw_fg)
	add_child(_fg)
	for i in 3:
		var tb: String = ["lessons", "fit", "quiz"][i]
		var b := GameButton.make(Rect2(24 + i * 214, 64, 204, 38), TAB_NAMES[tb], UI.CYAN)
		b.name = "Tab_" + tb
		b.pressed.connect(set_tab.bind(tb))
		add_child(b)
	var back := GameButton.make(BACK, "В МАСТЕРСКУЮ", UI.AMBER)
	back.name = "BackBtn"
	back.pressed.connect(go_back)
	add_child(back)
	_dyn = Control.new()
	_dyn.name = "Dyn"
	_dyn.size = size
	_dyn.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_dyn)
	Chrome.add(self, true, true, false)
	_build_dyn()
	tick(0.0)


## Кнопки вкладки (пересобираются при смене вкладки, клиента, вопроса); фокус остаётся на кнопке с тем же именем.
func refresh() -> void:
	var fo := get_viewport().gui_get_focus_owner() if is_inside_tree() else null
	var keep := String(fo.name) if fo != null and _dyn.is_ancestor_of(fo) else ""
	for c in _dyn.get_children():
		_dyn.remove_child(c)
		c.queue_free()
	_build_dyn()
	if keep != "" and _dyn.has_node(keep):
		var n := _dyn.get_node(keep) as Control
		if n.focus_mode != Control.FOCUS_NONE:
			UI.focus_later(n)
	elif fo != null and not is_instance_valid(fo):
		UI.focus_later(first_focus())


func _build_dyn() -> void:
	sliders.clear()
	for i in 3:
		var tb: String = ["lessons", "fit", "quiz"][i]
		var t_btn := get_node_or_null("Tab_" + tb) as GameButton
		if t_btn:
			t_btn.active = tab == tb
			t_btn.queue_redraw()
	if tab == "lessons":
		for i in lessons().size():
			var b := GameButton.make(list_rect(i), "", UI.CYAN)
			b.name = "Lesson_%d" % i
			b.active = i == lesson
			b.set_meta("i", i)
			b.on_draw = _draw_lesson_btn
			b.accessibility_name = "%d. %s" % [i + 1, Loc.t(lessons()[i]["title"])]
			b.pressed.connect(pick_lesson.bind(i))
			_dyn.add_child(b)
		var lpose: Dictionary = _lpose()
		for k: String in ["p", "slide", "deep", "knee_up", "dangle", "front"]:
			if lpose.has(k):
				var tg := GameButton.make(TOGGLE, "ПОЗА: НОРМА ✔" if demo_good else "ПОКАЗАТЬ НОРМУ ▶",
					UI.GOOD if demo_good else UI.PURPLE)
				tg.name = "Toggle"
				tg.active = demo_good
				tg.pressed.connect(toggle_demo)
				_dyn.add_child(tg)
				break
	elif tab == "fit":
		for i in cases().size():
			var done := SaveGame.seat_done.has(cases()[i]["id"])
			var b := GameButton.make(list_rect(i), "", UI.GOOD if done else UI.CYAN)
			b.name = "Case_%d" % i
			b.active = i == case_i
			b.set_meta("i", i)
			b.on_draw = _draw_case_btn
			b.accessibility_name = ("✔ " if done else "") + Loc.t(cases()[i]["client"])
			b.pressed.connect(pick_case.bind(i))
			_dyn.add_child(b)
		var c: Dictionary = cases()[case_i]
		if c.get("view"):
			var vname: String = {"front": "ВИД: СПЕРЕДИ  ⇄", "top": "ВИД: СВЕРХУ  ⇄", "side": "ВИД: СБОКУ  ⇄"}[view]
			var tg := GameButton.make(TOGGLE, vname, UI.CYAN)
			tg.name = "Toggle"
			tg.active = view != "side"
			tg.pressed.connect(toggle_view)
			_dyn.add_child(tg)
		var keys := slider_keys()
		for i in keys.size():
			var s := SeatSlider.new()
			s.scr = self
			s.key = keys[i]
			s.name = "Slider_" + keys[i]
			var tr := slider_rect(i)
			s.position = tr.position - Vector2(15, 15)
			s.size = tr.size + Vector2(30, 30)
			_dyn.add_child(s)
			sliders[keys[i]] = s
		var go := GameButton.make(BTN, "СЛЕДУЮЩИЙ КЛИЕНТ ▶" if solved else "ГОТОВО — ПРОВЕРИТЬ ПОСАДКУ",
			UI.GOOD if solved else UI.AMBER)
		go.name = "Check"
		go.pressed.connect(check_fit)
		_dyn.add_child(go)
		_update_slider_a11y()
	else:
		if quiz_done:
			var again := GameButton.make(BTN, "ПРОЙТИ ЕЩЁ РАЗ", UI.CYAN)
			again.name = "Again"
			again.pressed.connect(quiz_again)
			_dyn.add_child(again)
			return
		var q: Dictionary = quiz[quiz_i]
		for i in (q["options"] as Array).size():
			var ok: bool = q["options"][i][1]
			var col := UI.CYAN
			if picked >= 0:
				col = UI.GOOD if ok else (UI.BAD if i == picked else UI.DIM)
			var b := GameButton.make(quiz_rect(i), "", col)
			b.name = "Opt_%d" % i
			b.enabled = picked < 0 or i == picked or ok
			b.set_meta("i", i)
			b.on_draw = _draw_option
			b.accessibility_name = Loc.t(q["options"][i][0])
			b.pressed.connect(quiz_pick.bind(i))
			_dyn.add_child(b)
		if picked >= 0:
			var nx := GameButton.make(BTN, "ДАЛЬШЕ ▶", UI.AMBER)
			nx.name = "Next"
			nx.pressed.connect(quiz_next)
			_dyn.add_child(nx)


func first_focus() -> Control:
	return get_node_or_null("Tab_" + tab) as Control


func go_back() -> void:
	Nav.go("hub")


func text_cap() -> float:
	return 1.25 if tab == "fit" else 0.0


func summary() -> String:
	if tab == "lessons":
		var les: Dictionary = lessons()[lesson]
		var pts: Array = []
		for x: String in les["points"]:
			pts.append(Loc.t(x))
		return "%s: %s. " % [Loc.t("Кабинет посадки. Урок"), Loc.t(les["title"])] + " ".join(pts)
	if tab == "fit":
		var c: Dictionary = cases()[case_i]
		return "%s: %s. %s %s: %s %s. %s" % [Loc.t("Примерка"), Loc.t(c["client"]), Loc.t(c["story"]),
			Loc.t("Карта терапевта"), Loc.t(c["therapist"]), SeatLogic.measure_text(c),
			Loc.t("Двигай ползунки стрелками влево-вправо, потом «Проверить посадку».")]
	if quiz_done:
		return "%s: %s." % [Loc.t("Зачёт"), _of(score, quiz.size())]
	var q: Dictionary = quiz[quiz_i]
	var pic := (" " + Loc.t(q["desc"])) if q.get("desc") else ""
	return "%s %s: %s%s" % [Loc.t("Вопрос"), _of(quiz_i + 1, quiz.size()), Loc.t(q["q"]), pic]


# ---------------- действия ----------------

func set_tab(tb: String) -> void:
	tab = tb
	say = mentor(tb)
	Audio.sfx("tick")
	refresh()


func pick_lesson(i: int) -> void:
	lesson = i
	demo_good = false
	var lines: Array = Content.seating.get("mentor", {}).get("lesson", [])
	say = str(lines[i % lines.size()]) if not lines.is_empty() else say
	Audio.sfx("tick")
	refresh()


func pick_case(i: int) -> void:
	load_case(i)
	Audio.sfx("tick")
	refresh()


func toggle_demo() -> void:
	demo_good = not demo_good
	Audio.sfx("ghost")
	refresh()


func toggle_view() -> void:
	var cv_: String = cases()[case_i]["view"]
	view = "side" if view == cv_ else cv_
	say = mentor("side_ok" if view == "side" else "view_" + cv_)
	Audio.sfx("tick")
	refresh()


func set_value(key: String, v: int) -> void:
	var sl: Array = SeatLogic.sliders()[key]
	v = clampi(v, int(sl[2]), int(sl[3]))
	if v != int(cfg[key]):
		cfg[key] = v
		Audio.sfx("ratchet")
		_update_slider_a11y()


func set_from_x(key: String, x: float) -> void:
	var tr := slider_rect(slider_keys().find(key))
	var sl: Array = SeatLogic.sliders()[key]
	var lo := float(sl[2])
	var hi := float(sl[3])
	set_value(key, int(roundf(lo + (hi - lo) * clampf((x - tr.position.x) / tr.size.x, 0.0, 1.0))))


## ←/→ на ползунке в фокусе: шаг 1 (звук — каждый раз, как в pygame).
func step_value(key: String, d: int) -> void:
	focus_key = key
	var sl: Array = SeatLogic.sliders()[key]
	cfg[key] = clampi(int(cfg[key]) + d, int(sl[2]), int(sl[3]))
	Audio.sfx("ratchet")
	_update_slider_a11y()


func _update_slider_a11y() -> void:
	if sliders.is_empty():
		return
	var checks: Array = SeatLogic.seat_eval(cases()[case_i], cfg)[0]
	for k: String in sliders:
		var state := ""
		for ch: Array in checks:
			if ch[0] == k:
				state = ch[2]
				break
		(sliders[k] as Control).accessibility_name = "%s: %s. %s" % [Loc.t(SeatLogic.sliders()[k][0]),
			SeatLogic.val_text(k, cfg[k]), Loc.t(state)]


func check_fit() -> void:
	var c: Dictionary = cases()[case_i]
	if solved:
		load_case((case_i + 1) % cases().size())
		refresh()
		return
	var checks: Array = SeatLogic.seat_eval(c, cfg)[0]
	var bad: Array = []
	for ch: Array in checks:
		if not ch[1]:
			bad.append(ch[2])
	if not bad.is_empty():
		Audio.sfx("bad")
		fails += 1
		say = mentor("fail")
		Nav.flash("Ещё не так: " + str(bad[0]), UI.BAD, 3)
	else:
		solved = true
		say = mentor("solved")
		SaveGame.seat_done[c["id"]] = true
		SaveGame.save()
		Audio.sfx("fanfare")
		Nav.flash(c["fact"], UI.GOOD, 6)
		drag = ""
		refresh()


func quiz_pick(i: int) -> void:
	if quiz_done or picked >= 0:
		return
	var q: Dictionary = quiz[quiz_i]
	picked = i
	var ok: bool = q["options"][i][1]
	score += 1 if ok else 0
	say = mentor("right" if ok else "wrong")
	var fx: Array = Content.consts.get("seat_fix", [0.7, 1.2])
	fix_t0 = t - 99.0 if Settings.calm() else t + (0.0 if ok else float(fx[1]))
	Audio.sfx("ok" if ok else "bad")
	if q.get("fix"):
		Speech.say("%s: %s" % [Loc.t("Так правильно" if ok else "Правильно так"), Loc.t(q["fix"])])
	refresh()
	UI.focus_later(_dyn.get_node_or_null("Next") as Control)


func quiz_next() -> void:
	if picked < 0:
		return
	if quiz_i + 1 < quiz.size():
		quiz_i += 1
		picked = -1
	else:
		quiz_done = true
		var ok := score >= SeatLogic.QUIZ_PASS
		say = mentor("pass" if ok else "nopass")
		if ok:
			SaveGame.seat_quiz_ok = true
			SaveGame.save()
			Audio.sfx("fanfare")
	refresh()
	UI.focus_later((_dyn.get_node_or_null("Again") if quiz_done else _dyn.get_node_or_null("Opt_0")) as Control)


func quiz_again() -> void:
	quiz_i = 0
	picked = -1
	score = 0
	quiz_done = false
	_shuffle_quiz()
	refresh()


## Доля перехода к исправленной позе 0..1 (плавно), -1 — ответа ещё нет (_seat_fix_t).
func fix_t() -> float:
	if picked < 0:
		return -1.0
	var dur: float = Content.consts.get("seat_fix", [0.7, 1.2])[0]
	var u := clampf((t - fix_t0) / dur, 0.0, 1.0)
	return u * u * (3.0 - 2.0 * u)


## «3 из 5» / «3 of 5» — для озвучки счётчиков (_of).
static func _of(a: int, b: int) -> String:
	return ("%d из %d" if Loc.code == "ru" else "%d of %d") % [a, b]


func _lpose() -> Dictionary:
	var p: Variant = lessons()[lesson].get("pose")
	return p if p is Dictionary else {}


# ---------------- кадр ----------------

func tick(_dt: float) -> void:
	if say != _said:
		_said = say
		if Settings.a11y.get("voices", true):
			Speech.say(Loc.t(say))
	_place_figure()
	_back.queue_redraw()
	_fg.queue_redraw()


func _place_figure() -> void:
	fig.mode = "none"
	fig.highlight = true
	fig.show_necro = true
	var inner := Rect2(CV.position + Vector2(8, 12), CV.size - Vector2(16, 24))
	if tab == "lessons":
		var lp := _lpose()
		if lp.get("front"):
			fig.mode = "front"
			fig.front_corrected = demo_good
			fig.front_pads = true
			fig.front_obl = -1.0
			fig.front_wedge = 0.0
			fig.place(Rect2(0, 0, UI.W, UI.H), CV)
			return
		var d := SeatLogic.demo_pose(lp, demo_good)
		fig.case = d[0]
		fig.cfg = d[1]
		fig.pose = d[2]
		fig.mode = "scene"
		fig.place(CV.grow(-2), inner)
	elif tab == "fit":
		var c: Dictionary = cases()[case_i]
		var lay := _fit_layout()
		fig.case = c
		if view != "side":
			fig.cfg = cfg
			fig.pose = SeatLogic.seat_eval(c, cfg)[1]
			fig.mode = "front_fit" if view == "front" else "top"
			fig.place(lay[5], lay[4])
			return
		if c.get("view"):
			fig.cfg = SeatLogic.side_cfg(c)
			fig.pose = SeatLogic.eval_side(c, fig.cfg)[1]
		else:
			fig.cfg = cfg
			fig.pose = SeatLogic.seat_eval(c, cfg)[1]
		fig.mode = "scene"
		fig.place(lay[5], lay[4])
	else:
		if quiz_done:
			var ok := score >= SeatLogic.QUIZ_PASS
			fig.mode = "puppet"
			fig.targets = [[CV.get_center().x + 40, CV.get_center().y - 52, UI.GOOD if ok else UI.AMBER, true]]
			fig.puppet_bad = not ok
			fig.place(Rect2(0, 0, UI.W, UI.H), CV)
			return
		var q: Dictionary = quiz[quiz_i]
		var qp: Variant = q.get("pose")
		if qp is Dictionary and (qp as Dictionary).get("front"):    # до ответа — без упоров и подписей: не подсказка
			var ft0 := fix_t()
			var kind0 := SeatLogic.fix_kind(q)
			var tt0 := ft0 if (ft0 >= 0.0 and kind0 != "") else 0.0
			fig.mode = "front"
			if kind0 == "wedge":
				fig.front_corrected = false
				fig.front_pads = false
				fig.front_obl = -1.0
				fig.front_wedge = tt0
			else:
				fig.front_corrected = tt0 >= 0.5
				fig.front_pads = tt0 >= 0.5
				fig.front_obl = 1.0 - 0.88 * tt0
				fig.front_wedge = 0.0
			fig.place(Rect2(0, 0, UI.W, UI.H), CV)
			return
		if qp is Dictionary:
			var ft := fix_t()
			var kind := SeatLogic.fix_kind(q)
			var tt := ft if (ft >= 0.0 and kind != "") else 0.0
			var d := SeatLogic.fix_pose(qp, tt)
			fig.case = d[0]
			fig.cfg = d[1]
			fig.pose = d[2]
			fig.highlight = picked >= 0
			fig.mode = "scene"
			fig.place(Rect2(0, 0, UI.W, UI.H), inner)
		else:
			fig.mode = "myth"
			fig.place(Rect2(0, 0, UI.W, UI.H), CV)


## Шапка примерки: [строки истории, карта, строки карты, y карты, рамка сцены, рамка обрезки].
func _fit_layout() -> Array:
	var c: Dictionary = cases()[case_i]
	var st_lines := UI.wrap_lines(Loc.t(c["story"]), CV.size.x - 362, 14)
	var chart := "%s: %s" % [Loc.t("Карта терапевта"), Loc.t(c["therapist"])]
	var ch_lines := UI.wrap_lines(chart, CV.size.x - 126, 13)
	var lh14 := UI.line_height(14) + 2
	var lh13 := UI.line_height(13) + 2
	var ch_y := CV.position.y + 10 + maxf(st_lines.size() * lh14, 36)
	var head_bottom := maxf(CV.position.y + 98, ch_y + ch_lines.size() * lh13 + 6)
	var scene_r := Rect2(CV.position.x + 8, head_bottom, CV.size.x - 16, CV.end.y - 24 - head_bottom)
	var clip_r := Rect2(CV.position.x + 4, scene_r.position.y - 4, CV.size.x - 8, CV.end.y - scene_r.position.y)
	return [st_lines, chart, ch_lines, ch_y, scene_r, clip_r]


func typed(text: String, cps: float) -> int:
	if Settings.a11y.get("instant", false):
		return 1 << 30
	if _typing[0] != text:
		_typing = [text, t]
		return 0
	return int((t - float(_typing[1])) * cps)


func _draw_back() -> void:
	var ci := _back
	UI.draw_round_rect(ci, BUBBLE, Color8(30, 22, 40, 232), UI.PURPLE, 2, 8)
	var head := Content.texture("mentor_necro_head.png")
	if head:
		SeatFigure.breathe(ci, head, Rect2(24, 104, 68, 68), t, 0.0)
	var line := Loc.t(say if say != "" else mentor("intro"))
	var sz := 14
	while sz > 10 and UI.wrap_lines(line, BUBBLE.size.x - 24, sz).size() * (UI.line_height(sz) + 2) > BUBBLE.size.y - 10:
		sz -= 1
	UI.draw_wrapped(ci, line, BUBBLE.position + Vector2(12, 5), BUBBLE.size.x - 24, sz, Color8(226, 214, 246), false, 2,
		typed(line, 95), 3)
	UI.draw_round_rect(ci, CV, Color8(18, 20, 28, 238), Color8(96, 78, 136), 2, 12)


func _plate(ci: CanvasItem, r: Rect2) -> void:
	UI.draw_round_rect(ci, r.grow_individual(8, 4, 8, 4), Color8(14, 12, 20, 175), Color(), 0, 8)


## draw_text(..., plate=True).
func _text_plate(ci: CanvasItem, s: String, pos: Vector2, size_: float, col: Color, bold: bool = false, align: int = 0) -> void:
	var w := UI.text_width(s, size_, bold)
	var h := UI.line_height(size_, bold)
	var tl := pos
	if align == 1:
		tl = pos - Vector2(w, h) / 2.0
	elif align == 2:
		tl = pos - Vector2(w, 0)
	_plate(ci, Rect2(tl, Vector2(w, h)))
	UI.draw_text(ci, s, pos, size_, col, bold, align)


## draw_wrapped(..., plate=True); возврат — y под блоком.
func _wrapped_plate(ci: CanvasItem, s: String, pos: Vector2, width: float, size_: float, col: Color) -> float:
	var lines := UI.wrap_lines(s, width, size_)
	if not lines.is_empty():
		var bw := 0.0
		for ln in lines:
			bw = maxf(bw, UI.text_width(ln, size_))
		_plate(ci, Rect2(pos, Vector2(bw, lines.size() * (UI.line_height(size_) + 2) - 2)))
	return UI.draw_wrapped(ci, s, pos, width, size_, col)


func _fit(ci: CanvasItem, s: String, pos: Vector2, width: float, size_: int, col: Color, bold: bool = false) -> void:
	var f: Array = UI.fit_text(s, width, size_, bold)
	@warning_ignore("integer_division")
	UI.draw_text(ci, f[0], Vector2(pos.x, pos.y + (size_ - int(f[1])) / 2), f[1], col, bold)


func _draw_fg() -> void:
	var ci := _fg
	if tab == "lessons":
		var les: Dictionary = lessons()[lesson]
		var lp := _lpose()
		if lp.get("measure"):
			var cap := Loc.t("Жёсткая рулетка: глубина = бедро − 5 см (2″)")
			var cw := UI.text_width(cap, 14, true) + 14
			UI.draw_round_rect(ci, Rect2(CV.end.x - 14 - cw, CV.position.y + 46, cw, 22), Color8(16, 12, 24, 215), Color(), 0, 5)
			UI.draw_text(ci, cap, Vector2(CV.end.x - 21, CV.position.y + 48), 14, UI.AMBER, true, 2)
		@warning_ignore("integer_division")
		var y := 112.0 + ((lessons().size() + 1) / 2) * 44 + 10
		UI.draw_text(ci, Loc.t(les["title"]), Vector2(780, y), 20, UI.AMBER, true)
		y += 32
		var psz := 15
		while psz > 10:
			var need := 0.0
			for p: String in les["points"]:
				need += UI.wrap_lines("• " + Loc.t(p), 476, psz).size() * (UI.line_height(psz) + 2) + 8
			if need <= UI.H - 16 - y:
				break
			psz -= 1
		for p: String in les["points"]:
			y = _wrapped_plate(ci, "• " + Loc.t(p), Vector2(780, y), 476, psz, UI.WHITE) + 8
		UI.draw_text(ci, Loc.t("По руководству Permobil «Seating & Positioning Guide»"), Vector2(CV.end.x - 14, CV.end.y - 18),
			11, UI.GREY, false, 2)
	elif tab == "fit":
		_draw_fit(ci)
	else:
		_draw_quiz(ci)


func _draw_fit(ci: CanvasItem) -> void:
	var c: Dictionary = cases()[case_i]
	var res: Array = SeatLogic.seat_eval(c, cfg)
	var checks: Array = res[0]
	var lay := _fit_layout()
	if view == "side" and c.get("view"):
		var note := Loc.t("Сбоку посадка ровная — перекос виден только спереди" if c["view"] == "front"
			else "Сбоку посадка ровная — поворот таза виден только сверху")
		var nw := UI.text_width(note, 13, true) + 16
		UI.draw_round_rect(ci, Rect2(CV.end.x - 14 - nw, CV.end.y - 56, nw, 24), Color8(16, 12, 24, 225), Color(), 0, 5)
		UI.draw_text(ci, note, Vector2(CV.end.x - 22, CV.end.y - 53), 13, UI.AMBER, true, 2)
	var face := Content.texture(c["client_art"])
	if face:
		SeatFigure.breathe(ci, face, Rect2(CV.position.x + 12, CV.position.y + 6, 92, 108), t, 0.0)
	UI.draw_wrapped(ci, Loc.t(c["story"]), CV.position + Vector2(112, 10), CV.size.x - 362, 14, UI.WHITE)
	UI.draw_wrapped(ci, lay[1], Vector2(CV.position.x + 112, lay[3]), CV.size.x - 126, 13, UI.CYAN)
	UI.draw_text(ci, SeatLogic.measure_text(c), Vector2(CV.position.x + 14, CV.end.y - 18), 11, UI.AMBER)
	var keys := slider_keys()
	for i in keys.size():
		var key: String = keys[i]
		var sl: Array = SeatLogic.sliders()[key]
		var tr := slider_rect(i)
		var v := float(cfg[key])
		var ok := true
		for ch: Array in checks:
			if (ch[0] == key or (key == "leg" and ch[0] == "floor")) and not ch[1]:
				ok = false
		var col := UI.GOOD if ok else UI.AMBER
		UI.draw_text(ci, Loc.t(sl[0]), Vector2(tr.position.x, tr.position.y - 20), 13, UI.WHITE)
		_fit(ci, SeatLogic.val_text(key, cfg[key]), Vector2(tr.end.x + 8, tr.position.y - 9), 150, 14, col)
		UI.draw_round_rect(ci, tr, Color8(44, 46, 60), Color(), 0, 4)
		var fw := int(tr.size.x * (v - float(sl[2])) / (float(sl[3]) - float(sl[2])))
		if fw > 0:
			UI.draw_round_rect(ci, Rect2(tr.position, Vector2(fw, tr.size.y)), col, Color(), 0, 4)
		var kc := Vector2(tr.position.x + fw, tr.get_center().y)
		var s: SeatSlider = sliders.get(key)
		var hov := s != null and (s.hover or drag == key)
		var r := 10.0 if hov else 8.0
		ci.draw_circle(kc, r, UI.WHITE, true, -1, true)
		UI.draw_ring(ci, kc, r, col, 3)
		if s != null and s.has_focus() and UI.kb_active:
			UI.draw_round_rect(ci, Rect2(s.position, s.size), Color(0, 0, 0, 0), UI.WHITE, 2, 8)
	var y := slider_rect(keys.size() - 1).position.y + 24
	var room := BTN.position.y - 6 - y
	var order: Array = []
	for ch: Array in checks:
		if not ch[1]:
			order.append(ch)
	for ch: Array in checks:
		if ch[1]:
			order.append(ch)
	var csz := 13
	while csz > 10:
		var need := 0.0
		for ch: Array in order:
			need += UI.wrap_lines(("✔ " if ch[1] else "⚠ ") + Loc.t(ch[2]), 476, csz).size() * (UI.line_height(csz) + 2) + 2
		if need <= room:
			break
		csz -= 1
	var bottom := BTN.position.y - 6
	for ch: Array in order:
		var left := int((bottom - y) / (UI.line_height(csz) + 2))
		if left < 1:
			break
		y = UI.draw_wrapped(ci, ("✔ " if ch[1] else "⚠ ") + Loc.t(ch[2]), Vector2(780, y), 476, csz,
			UI.GOOD if ch[1] else UI.AMBER, false, 2, -1, left) + 2


func _draw_quiz(ci: CanvasItem) -> void:
	if quiz_done:
		var ok := score >= SeatLogic.QUIZ_PASS
		var cc := CV.get_center()
		_text_plate(ci, Loc.t("Верно %d из %d" % [score, quiz.size()]), Vector2(cc.x + 40, cc.y - 20), 30,
			UI.GOOD if ok else UI.AMBER, true, 1)
		_text_plate(ci, Loc.t("Зачёт по посадке сдан!" if ok else "Для зачёта нужно %d. Перечитай уроки." % SeatLogic.QUIZ_PASS),
			Vector2(cc.x + 40, cc.y + 24), 18, UI.WHITE, false, 1)
		return
	var q: Dictionary = quiz[quiz_i]
	var qp: Variant = q.get("pose")
	var front := qp is Dictionary and bool((qp as Dictionary).get("front", false))
	var ft := fix_t()
	var kind := SeatLogic.fix_kind(q)
	if ft >= 0.0 and q.get("fix") and (kind == "" or ft >= 1.0):
		var right: bool = q["options"][picked][1]
		_fix_caption(ci, "%s: %s" % [Loc.t("Так правильно" if right else "Правильно так"), Loc.t(q["fix"])], front)
	_text_plate(ci, Loc.t("Вопрос %d из %d" % [quiz_i + 1, quiz.size()]), Vector2(780, 120), 15, UI.GREY)
	_wrapped_plate(ci, Loc.t(q["q"]), Vector2(780, 146), 476, 20, UI.WHITE)


## Зелёная плашка «Так правильно: …» (_draw_seat_fix_caption): внизу рамки, top — справа вверху (вид спереди).
func _fix_caption(ci: CanvasItem, text: String, top: bool) -> void:
	var w := 244.0 if top else CV.size.x - 170
	var sz := 15
	while sz > 12 and UI.wrap_lines(text, w, sz).size() > (2 if top else 1):
		sz -= 1
	var nmax := 4 if top else 2
	var lines := UI.wrap_lines(text, w, sz)
	if lines.size() > nmax:
		lines = lines.slice(0, nmax)
	var lh := UI.line_height(sz) + 2
	var bw := 0.0
	for ln in lines:
		bw = maxf(bw, UI.text_width(ln, sz))
	bw = int(bw) + 24
	var bh := lines.size() * lh + 10
	var box: Rect2
	if top:
		box = Rect2(CV.end.x - 8 - bw, CV.position.y + 8, bw, bh)
	else:
		@warning_ignore("integer_division")
		var bx := int(CV.get_center().x + 40) - int(bw) / 2
		bx = maxi(int(CV.position.x) + 150, mini(bx, int(CV.end.x - 8 - bw)))
		box = Rect2(bx, CV.end.y - 8 - bh, bw, bh)
	UI.draw_round_rect(ci, box, Color8(18, 46, 30, 236), UI.GOOD, 2, 8)
	UI.draw_wrapped(ci, text, Vector2(box.get_center().x, box.position.y + 5), w, sz, UI.GOOD, true, 2, -1, nmax)


func _draw_lesson_btn(b: GameButton, r: Rect2) -> void:
	var i := int(b.get_meta("i"))
	_fit(b, "%d. %s" % [i + 1, Loc.t(lessons()[i]["title"])], r.position + Vector2(10, 9), r.size.x - 20, 15, UI.WHITE,
		i == lesson)


func _draw_case_btn(b: GameButton, r: Rect2) -> void:
	var i := int(b.get_meta("i"))
	var done := SaveGame.seat_done.has(cases()[i]["id"])
	_fit(b, ("✔ " if done else "") + Loc.t(cases()[i]["client"]), r.position + Vector2(10, 8), r.size.x - 20, 14, UI.WHITE)


func _draw_option(b: GameButton, _lifted: Rect2) -> void:
	var r := Rect2(b.slide, b.size)            # текст стоит на месте, кнопка при наведении поднимается (как в pygame)
	var i := int(b.get_meta("i"))
	var o: Array = quiz[quiz_i]["options"][i]
	var ty := UI.draw_wrapped(b, Loc.t(o[0]), r.position + Vector2(14, 8), r.size.x - 28, 15, UI.WHITE)
	if picked == i and str(o[2]) != "":
		var fb := Loc.t(o[2])
		var fsz := 11
		var flh := UI.line_height(11) + 2
		for s: int in [13, 12, 11]:
			fsz = s
			flh = UI.line_height(s) + 2
			if ty + UI.wrap_lines(fb, r.size.x - 28, s).size() * flh <= r.end.y - 4:
				break
		UI.draw_wrapped(b, fb, Vector2(r.position.x + 14, ty), r.size.x - 28, fsz, UI.BAD, false, 2, -1,
			maxi(1, int((r.end.y - 4 - ty) / flh)))


## Ползунок примерки: рамка = дорожка, расширенная на 15 px (как inflate(30, 30)); рисует экран.
class SeatSlider extends Control:
	var scr: Node
	var key: String = ""
	var hover: bool = false
	var _drag: bool = false

	func _init() -> void:
		focus_mode = Control.FOCUS_ALL
		mouse_filter = Control.MOUSE_FILTER_STOP
		mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
		mouse_entered.connect(func() -> void: hover = true)
		mouse_exited.connect(func() -> void: hover = false)
		focus_entered.connect(func() -> void: scr.focus_key = key)

	func _gui_input(e: InputEvent) -> void:
		if scr.solved:
			return
		if e is InputEventMouseButton and (e as InputEventMouseButton).button_index == MOUSE_BUTTON_LEFT:
			_drag = e.pressed
			scr.drag = key if e.pressed else ""
			if e.pressed:
				scr.set_from_x(key, position.x + e.position.x)
			accept_event()
		elif e is InputEventMouseMotion and _drag:
			scr.set_from_x(key, position.x + e.position.x)
			accept_event()
		elif e is InputEventScreenTouch:
			_drag = e.pressed
			scr.drag = key if e.pressed else ""
			if e.pressed:
				scr.set_from_x(key, position.x + e.position.x)
			accept_event()
		elif e is InputEventScreenDrag:
			scr.set_from_x(key, position.x + e.position.x)
			accept_event()
		elif e is InputEventKey and e.pressed and ((e as InputEventKey).keycode == KEY_LEFT or (e as InputEventKey).keycode == KEY_RIGHT):
			scr.step_value(key, 1 if (e as InputEventKey).keycode == KEY_RIGHT else -1)
			accept_event()
