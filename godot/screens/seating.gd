extends Screen
## Кабинет посадки некроманта Мортимера (open_seating/draw_seating/click_seating в game.py): вкладки «УРОКИ»,
## «ПРИМЕРКА», «ПРОВЕРЬ СЕБЯ»; Мортимер с репликой над схемой (печать по буквам). Уроки — 7 карточек, поза с
## ошибкой и «ПОКАЗАТЬ НОРМУ»; примерка — 9 клиентов, ползунки (мышь, палец, ←/→ на ползунке в фокусе), список
## проверок и «ГОТОВО — ПРОВЕРИТЬ ПОСАДКУ» (seat_done); зачёт — 7 вопросов, после ответа рисунок плавно переходит к
## правильной посадке (0,7 с; при неверном — сначала 1,2 с ошибка), 6 верных — зачёт (seat_quiz_ok).
## Рисунок — SeatFigure: вид сбоку; спереди — примерка (_seat_front_fit) у клиентов с перекосом таза и схема урока 4 и
## вопросов 6–7 (_seat_front: дуга сколиоза, подкладка, три упора); сверху — поворот таза (_seat_top).

## Раскладка (_layout() в build()): вне телефонного режима — как было; в телефонном (UI.phone(), 21.11) — цели ≥ 56:
## вкладки и «В МАСТЕРСКУЮ» 56 в высоту, реплика и рамка ниже на 18; уроки — список в 2 столбца, клиенты — в 3, строки
## 56 через 64, на кнопке мини-иконка (урок — пиктограмма ui/lesson_icons.gd, клиент — верх портрета) и название
## целиком (до 2 строк); ползунки — строки-зоны 476×56 через 64 (5 ползунков — 52 через 60): подпись и значение сверху,
## дорожка снизу; «ПОЗА…/ВИД…» 228×56, нижняя кнопка 56 у низа экрана.
var CV := Rect2(24, 176, 730, 488)
var BTN := Rect2(780, 612, 476, 48)
var BACK := Rect2(UI.W - 230, 64, 206, 38)
var TOGGLE := Rect2(24 + 730 - 238, 176 + 8, 228, 32)
var BUBBLE := Rect2(96, 110, 658, 60)
var TAB_H := 38.0
var Q_TOP := 0.0                          # сдвиг «Вопрос N из M», вопроса и ответов зачёта (телефон: ниже вкладок)
const TAB_NAMES := {"lessons": "УРОКИ", "fit": "ПРИМЕРКА", "quiz": "ПРОВЕРЬ СЕБЯ"}
const ROW_H := 56.0                       # телефон: строка списка уроков/клиентов и шаг 64
const ROW_STEP := 64.0
const LessonIcons := preload("res://ui/lesson_icons.gd")   # телефон: пиктограммы уроков 1…7 на кнопках списка

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
var case_t0: float = 0.0                  # начало примерки (время пункта задания по ссылке)
var say: String = ""
var fix_t0: float = -99.0
var quiz: Array = []                      # вопросы зачёта с перемешанными вариантами (верный — не всегда первым)

var fig: SeatFigure
var _back: Control                        # подложка рамки и реплика Мортимера
var _head: Control                        # голова Мортимера у реплики — «дышит» (каждый кадр)
var _face: Control                        # портрет клиента примерки — «дышит» (каждый кадр)
var _fg: Control                          # тексты поверх рисунка
var _fg0: Control                         # …из них неподвижные при перетаскивании ползунка (примерка)
var _fg0_sig: Array = []
var _lay: Array = []                      # _fit_layout() по подписи _lay_sig (перенос строк — не каждый кадр)
var _lay_sig: Array = []
var _back_sig: Array = []                 # перерисовка неподвижного — только при изменении (скорость, 19.11)
var _fg_sig: Array = []
var _dyn: Control                         # кнопки, которые меняются вместе с вкладкой/клиентом/вопросом
var _typing: Array = ["", 0.0]
var _said: String = ""
var sliders: Dictionary = {}              # ключ → SeatSlider
var text_sizes: Dictionary = {}           # кегли последнего кадра (реплика, урок, предупреждения, вопрос) — для проверок


func music_theme() -> String:
	return "workshop"


func _init() -> void:
	super._init()
	quiz = Content.seating.get("quiz", []).duplicate(true)
	_shuffle_quiz()
	load_case(SaveGame.seat_idx()[0])
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
	case_t0 = t
	say = mentor("view_" + str(c["view"])) if c.get("view") else mentor("fit")


func slider_keys() -> Array:
	var c: Dictionary = cases()[case_i]
	if c.get("sliders"):
		return c["sliders"]
	return ["depth", "leg", "back_h", "back_a"] + (["tilt"] if c.get("tilt") else [])


func _layout() -> void:
	var ph := UI.phone()
	TAB_H = 56.0 if ph else 38.0
	BACK = Rect2(UI.W - 230, 64, 206, TAB_H)
	BUBBLE = Rect2(96, 128, 658, 60) if ph else Rect2(96, 110, 658, 60)
	CV = Rect2(24, 194, 730, 470) if ph else Rect2(24, 176, 730, 488)
	TOGGLE = Rect2(CV.end.x - 238, CV.position.y + 8, 228, 56.0 if ph else 32.0)
	BTN = Rect2(780, UI.H - 60, 476, 56) if ph else Rect2(780, 612, 476, 48)
	Q_TOP = 8.0 if ph else 0.0


## Дорожка ползунка i (рисунок; set_from_x — по ней).
@warning_ignore("integer_division")
func slider_rect(i: int) -> Rect2:
	if UI.phone():
		var z := slider_zone(i)
		return Rect2(z.position.x + 20, z.end.y - 22, z.size.x - 40, 8)
	var row_h := ((cases().size() + 1) / 2) * 40
	return Rect2(800, 112 + row_h + 26 + i * 44, 290, 8)


## Зона попадания ползунка i (узел SeatSlider): как было — дорожка ± 15; телефон — строка 476×56 через 64 (при 5
## ползунках — 52 через 60, иначе предупреждениям не остаётся места), подпись и значение — внутри строки.
func slider_zone(i: int) -> Rect2:
	if UI.phone():
		var tight := _fit_tight()
		return Rect2(780, _list_bottom() + 8 + i * (60.0 if tight else 64.0), 476, 52.0 if tight else 56.0)
	return slider_rect(i).grow(15)


## Телефон, примерка с 4–5 ползунками: строки ползунков и «ГОТОВО» — 52 через 60 (с 56 через 64 предупреждениям
## при 100 % остаётся 80 px вместо прежних 112 — кегль 13 → 10).
func _fit_tight() -> bool:
	return UI.phone() and slider_keys().size() >= 4


## Нижняя кнопка примерки («ГОТОВО — ПРОВЕРИТЬ ПОСАДКУ» / «СЛЕДУЮЩИЙ КЛИЕНТ»).
func fit_btn() -> Rect2:
	return Rect2(780, UI.H - 54, 476, 52) if _fit_tight() else BTN


## Сколько пунктов в списке вкладки (уроки — все; примерка — назначенные).
func _list_n() -> int:
	return lessons().size() if tab == "lessons" else SaveGame.seat_idx().size()


## Телефон: низ списка уроков/клиентов.
func _list_bottom() -> float:
	return list_rect(maxi(_list_n() - 1, 0)).end.y


@warning_ignore("integer_division")
func list_rect(i: int) -> Rect2:
	if UI.phone():                               # уроки — 2 столбца по 234, клиенты — 3 по 153 (зазор 8)
		var cols := 2 if tab == "lessons" else 3
		var w := 234.0 if cols == 2 else 153.0
		return Rect2(780 + (i % cols) * (w + 8), 128 + (i / cols) * ROW_STEP, w, ROW_H)
	if tab == "lessons":
		return Rect2(780 + (i % 2) * 238, 112 + (i / 2) * 44, 230, 38)
	return Rect2(780 + (i % 2) * 238, 112 + (i / 2) * 40, 230, 35)


func quiz_rect(i: int) -> Rect2:
	return Rect2(780, 260 + Q_TOP + i * 92, 476, 82)


# ---------------- сборка ----------------

func build() -> void:
	_layout()
	add_child(BgLayer.make("bg_workshop.png"))
	add_child(TopBar.make("Кабинет посадки некроманта Мортимера"))
	_back = Control.new()
	_back.name = "Back"
	_back.size = size
	_back.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_back.draw.connect(_draw_back)
	add_child(_back)
	_head = Control.new()                  # сразу над подложкой (с ней не пересекается)
	_head.name = "Head"
	_head.size = size
	_head.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_head.draw.connect(_draw_head)
	add_child(_head)
	fig = SeatFigure.new()
	add_child(fig)
	_face = Control.new()                  # под текстами (с ними не пересекается)
	_face.name = "Face"
	_face.size = size
	_face.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_face.draw.connect(_draw_face)
	add_child(_face)
	_fg0 = Control.new()                   # тексты примерки, не зависящие от ползунков (история, карта, мерки)
	_fg0.name = "Fg0"
	_fg0.size = size
	_fg0.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_fg0.draw.connect(_draw_fg0)
	add_child(_fg0)
	_fg = Control.new()
	_fg.name = "Fg"
	_fg.size = size
	_fg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_fg.draw.connect(_draw_fg)
	add_child(_fg)
	for i in 3:
		var tb: String = ["lessons", "fit", "quiz"][i]
		var b := GameButton.make(Rect2(24 + i * 214, 64, 204, TAB_H), TAB_NAMES[tb], UI.CYAN)
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
			b.redraw_sig = _btn_sig
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
		var c: Dictionary = cases()[case_i]
		if c.get("view"):                            # «вид ⇄» — до списка клиентов: так его рисует и обходит game.py
			var vname: String = {"front": "ВИД: СПЕРЕДИ  ⇄", "top": "ВИД: СВЕРХУ  ⇄", "side": "ВИД: СБОКУ  ⇄"}[view]
			var tg := GameButton.make(TOGGLE, vname, UI.CYAN)
			tg.name = "Toggle"
			tg.active = view != "side"
			tg.pressed.connect(toggle_view)
			_dyn.add_child(tg)
		var idx := SaveGame.seat_idx()               # в задании по ссылке — только назначенные примерки
		for n in idx.size():
			var i: int = idx[n]
			var done := SaveGame.is_done(cases()[i]["id"])
			var b := GameButton.make(list_rect(n), "", UI.GOOD if done else UI.CYAN)
			b.name = "Case_%d" % i
			b.active = i == case_i
			b.set_meta("i", i)
			b.on_draw = _draw_case_btn
			b.redraw_sig = _btn_sig
			b.accessibility_name = ("✔ " if done else "") + Loc.t(cases()[i]["client"])
			b.pressed.connect(pick_case.bind(i))
			_dyn.add_child(b)
		var keys := slider_keys()
		for i in keys.size():
			var s := SeatSlider.new()
			s.scr = self
			s.key = keys[i]
			s.name = "Slider_" + keys[i]
			var tr := slider_zone(i)
			s.position = tr.position
			s.size = tr.size
			s.set_meta("a11y_group", "Ползунки")
			UI.touch_block(s)                      # click_seating: block — дорожка ползунка inflate(30, 30) = сам узел
			_dyn.add_child(s)
			sliders[keys[i]] = s
		var go := GameButton.make(fit_btn(), "СЛЕДУЮЩИЙ КЛИЕНТ ▶" if solved else "ГОТОВО — ПРОВЕРИТЬ ПОСАДКУ",
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
			b.redraw_sig = _btn_sig
			b.accessibility_name = Loc.t(q["options"][i][0])
			b.pressed.connect(quiz_pick.bind(i))
			UI.touch_skip(b, picked >= 0)            # ответ уже выбран — варианты не цели (как в game.py)
			_dyn.add_child(b)
		if picked >= 0:
			var nx := GameButton.make(BTN, "ДАЛЬШЕ ▶", UI.AMBER)
			nx.name = "Next"
			nx.pressed.connect(quiz_next)
			_dyn.add_child(nx)


## click_seating: цели — «назад», вкладки, список, переключатель, ответы, кнопка; ползунки — block.
func touch_scope() -> Control:
	return self


func first_focus() -> Control:
	return get_node_or_null("Tab_" + tab) as Control


func go_back() -> void:
	Nav.go("hub")


func text_cap() -> float:
	return 1.25 if tab == "fit" else 0.0


func a11y_sig() -> Array:
	return [[tab], [case_i, lesson, quiz_i, quiz_done]]


func a11y_lines() -> Array:
	return [say]


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
		var idx := SaveGame.seat_idx()
		load_case(idx[(idx.find(case_i) + 1) % idx.size()] if case_i in idx else idx[0])
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
		if SaveGame.assign_on():               # задание по ссылке: обычный прогресс не трогаем
			SaveGame.assign_record(c["id"], fails, int(t - case_t0))
		else:
			SaveGame.mark_seat(c["id"])
			SaveGame.save()
		Audio.sfx("fanfare")
		Nav.flash(c["fact"], UI.GOOD, 6)
		drag = ""
		refresh()
		Share.maybe_summary()


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
		var ok := score >= SeatLogic.quiz_pass()
		say = mentor("pass" if ok else "nopass")
		if ok:
			if not SaveGame.assign_on():
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
		pass                                   # реплику Мортимера говорит A11y (a11y_lines)
	_place_figure()
	var look := [Loc.code, Settings.a11y.get("text", 0), Settings.easy_font(), Settings.calm()]
	var line := _say_line()
	var bs := [line, mini(typed(line, 95), line.length()), look]
	if bs != _back_sig:                        # реплика печатается — каждый кадр, потом стоит
		_back_sig = bs
		_back.queue_redraw()
	var fs := [tab, lesson, case_i, cfg.duplicate(), view, drag, solved, demo_good, quiz_i, picked, quiz_done, score,
		fix_t(), UI.kb_active, look]
	for k: String in sliders:
		var sl: SeatSlider = sliders[k]
		fs.append([sl.hover, sl.has_focus()])
	if fs != _fg_sig:
		_fg_sig = fs
		_fg.queue_redraw()
		_face.queue_redraw()
	var f0 := [tab, case_i, view, look]
	if f0 != _fg0_sig:
		_fg0_sig = f0
		_fg0.queue_redraw()
	if not Settings.calm():                    # «дышат» голова Мортимера и портрет клиента
		_head.queue_redraw()
		if tab == "fit":
			_face.queue_redraw()
	elif _head.get_meta("look", []) != look:
		_head.set_meta("look", look)
		_head.queue_redraw()


## Подпись кнопок списка и вариантов (GameButton.redraw_sig): от чего зависит их содержимое.
func _btn_sig() -> Array:
	return [lesson, quiz_i, picked, Loc.code]


func _say_line() -> String:
	return Loc.t(say if say != "" else mentor("intro"))


func _place_figure() -> void:
	fig.mode = "none"
	fig.highlight = true
	fig.show_necro = true
	fig.status_avoid = Rect2() if tab == "quiz" else TOGGLE
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
			var ok := score >= SeatLogic.quiz_pass()
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
	var sig := [case_i, Loc.code, Settings.a11y.get("text", 0), Settings.easy_font(), UI.phone()]
	if sig != _lay_sig:
		_lay_sig = sig
		_lay = _fit_layout_calc()
	return _lay


func _fit_layout_calc() -> Array:
	var c: Dictionary = cases()[case_i]
	var st_lines := UI.wrap_lines(Loc.t(c["story"]), CV.size.x - 362, 14)
	var chart := "%s: %s" % [Loc.t("Карта терапевта"), Loc.t(c["therapist"])]
	var ch_lines := UI.wrap_lines(chart, CV.size.x - 126, 13)
	var lh14 := UI.line_height(14) + 2
	var lh13 := UI.line_height(13) + 2
	var ch_y := CV.position.y + 10 + maxf(st_lines.size() * lh14, 36)
	if UI.phone() and c.get("view"):             # телефон: «ВИД ⇄» 56 в высоту — карта терапевта под ним
		ch_y = maxf(ch_y, TOGGLE.end.y + 4)
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


func _draw_head() -> void:
	var head := Content.texture("mentor_necro_head.png")
	if head:
		SeatFigure.breathe(_head, head, Rect2(24, BUBBLE.position.y - 6, 68, 68), t, 0.0)


func _draw_face() -> void:
	if tab != "fit":
		return
	var face := Content.texture(cases()[case_i]["client_art"])
	if face:
		SeatFigure.breathe(_face, face, Rect2(CV.position.x + 12, CV.position.y + 6, 92, 108), t, 0.0)


func _draw_back() -> void:
	var ci := _back
	UI.draw_round_rect(ci, BUBBLE, Color8(30, 22, 40, 232), UI.PURPLE, 2, 8)
	var line := _say_line()
	var sz := 14
	while sz > 10 and UI.wrap_lines(line, BUBBLE.size.x - 24, sz).size() * (UI.line_height(sz) + 2) > BUBBLE.size.y - 10:
		sz -= 1
	text_sizes["say"] = sz
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


## Зазор между пунктами урока (телефон — 6: под списком в 4 ряда место дороже).
func _pt_gap() -> float:
	return 6.0 if UI.phone() else 8.0


## Телефон: название урока. Уроков нечётно (7) — в пустую клетку последнего ряда списка (до 2 строк, кегль 20 → 12),
## текст урока — сразу под списком; иначе — строкой под списком. Возврат — y начала текста урока.
func _lesson_title_phone(ci: CanvasItem, title: String) -> float:
	var n := lessons().size()
	if n % 2 == 1:
		var box := list_rect(n)                  # клетка рядом с последним уроком
		var sz := 20
		var lines := UI.wrap_lines(title, box.size.x, sz, true)
		while sz > 12:
			lines = UI.wrap_lines(title, box.size.x, sz, true)
			var wide := false
			for ln in lines:
				wide = wide or UI.text_width(ln, sz, true) > box.size.x
			if not wide and lines.size() <= 2 and lines.size() * (UI.line_height(sz, true) + 2) - 2 <= box.size.y:
				break
			sz -= 1
		var lh := UI.line_height(sz, true) + 2
		var ty := box.position.y + floorf((box.size.y - (mini(lines.size(), 2) * lh - 2)) / 2.0)
		for k in mini(lines.size(), 2):
			UI.draw_text(ci, lines[k], Vector2(box.position.x, ty + k * lh), sz, UI.AMBER, true)
		return _list_bottom() + 6
	var y := _list_bottom() + 8
	UI.draw_text_w(ci, title, Vector2(780, y), 476, 20, UI.AMBER, true)
	return y + UI.line_height(20, true) + 4


## Размер пунктов урока: урок целиком до низа окна (цикл psz 15 → 10, как game.py). С «лёгким» шрифтом SDL_ttf меряет
## строку Atkinson иначе, чем Godot (хинтованные целые advance + кернинг: на одних размерах шире, на других уже, общего
## коэффициента нет), и при 150 % Godot выбирал на размер крупнее. Поэтому — число, которое выбрала сама game.py
## (sync_content.py → content/data/seat_lesson_fit.json), если тексты урока те же (md5 строк «• пункт») и урок при нём
## помещается и у Godot; иначе — свой цикл.
func _lesson_psz(les: Dictionary, y: float) -> int:
	var need_at := func(sz: int) -> float:
		var need := 0.0
		for p: String in les["points"]:
			need += UI.wrap_lines("• " + Loc.t(p), 476, sz).size() * (UI.line_height(sz) + 2) + _pt_gap()
		return need
	var room := UI.H - (8 if UI.phone() else 16) - y     # телефон: до низа экрана − 8 (список уроков выше)
	var fit: Dictionary = Content.seating.get("lesson_fit", {})
	var i := lessons().find(les)
	var key := "%s|%d|%d" % [Loc.code, clampi(int(Settings.a11y.get("text", 0)), 0, 3), int(Settings.easy_font())]
	var sizes: Array = fit.get("sizes", {}).get(key, [])
	var md5s: Array = fit.get("md5", {}).get(Loc.code, [])
	# телефон: у game.py такой раскладки нет, а места под уроком больше (плитки вместо строк) — свой цикл, не мельче
	if i >= 0 and i < sizes.size() and i < md5s.size() and Settings.text_cap <= 0.0 and not UI.phone():
		var lines: PackedStringArray = []
		for p: String in les["points"]:
			lines.append("• " + Loc.t(p))
		var sz := int(sizes[i])
		if "\n".join(lines).md5_text() == str(md5s[i]) and need_at.call(sz) <= room:
			return sz
	var psz := 15
	while psz > 10 and need_at.call(psz) > room:
		psz -= 1
	return psz


func _draw_fg() -> void:
	var ci := _fg
	if tab == "lessons":
		var les: Dictionary = lessons()[lesson]
		var lp := _lpose()
		if lp.get("measure"):
			var cap := Loc.t("Жёсткая рулетка: глубина = бедро − 5 см (2″)")
			var cw := UI.text_width(cap, 14, true) + 14
			var cy := CV.position.y + 46
			if UI.phone() and _dyn.has_node("Toggle"):   # телефон: под «ПОКАЗАТЬ НОРМУ» 56
				cy = TOGGLE.end.y + 6
			UI.draw_round_rect(ci, Rect2(CV.end.x - 14 - cw, cy, cw, 22), Color8(16, 12, 24, 215), Color(), 0, 5)
			UI.draw_text(ci, cap, Vector2(CV.end.x - 21, cy + 2), 14, UI.AMBER, true, 2)
		var y := 0.0
		if UI.phone():                               # заголовок — в пустой клетке списка (7 уроков) или под ним
			y = _lesson_title_phone(ci, Loc.t(les["title"]))
		else:
			@warning_ignore("integer_division")
			y = 112.0 + ((lessons().size() + 1) / 2) * 44 + 10
			UI.draw_text(ci, Loc.t(les["title"]), Vector2(780, y), 20, UI.AMBER, true)
			y += maxf(32, UI.line_height(20, true) + 4)   # 150 %: первая плашка (подложка −4 px) — под заголовком
		var psz := _lesson_psz(les, y)
		text_sizes["lesson"] = psz
		for p: String in les["points"]:
			y = _wrapped_plate(ci, "• " + Loc.t(p), Vector2(780, y), 476, psz, UI.WHITE) + _pt_gap()
		text_sizes["lesson_over"] = maxi(0, ceili(y - _pt_gap() - (UI.H - (8 if UI.phone() else 16))))   # проверки
		UI.draw_text(ci, Loc.t("По руководству Permobil «Seating & Positioning Guide»"), Vector2(CV.end.x - 14, CV.end.y - 18),
			11, UI.GREY, false, 2)
	elif tab == "fit":
		_draw_fit(ci)
	else:
		_draw_quiz(ci)


## Неподвижное при ползунках (слой _fg0, под остальными текстами — как раньше, они рисовались первыми).
func _draw_fg0() -> void:
	if tab != "fit":
		return
	var ci := _fg0
	var c: Dictionary = cases()[case_i]
	var lay := _fit_layout()
	if view == "side" and c.get("view"):
		var note := Loc.t("Сбоку посадка ровная — перекос виден только спереди" if c["view"] == "front"
			else "Сбоку посадка ровная — поворот таза виден только сверху")
		var nw := UI.text_width(note, 13, true) + 16
		UI.draw_round_rect(ci, Rect2(CV.end.x - 14 - nw, CV.end.y - 56, nw, 24), Color8(16, 12, 24, 225), Color(), 0, 5)
		UI.draw_text(ci, note, Vector2(CV.end.x - 22, CV.end.y - 53), 13, UI.AMBER, true, 2)
	UI.draw_wrapped(ci, Loc.t(c["story"]), CV.position + Vector2(112, 10), CV.size.x - 362, 14, UI.WHITE)
	UI.draw_wrapped(ci, lay[1], Vector2(CV.position.x + 112, lay[3]), CV.size.x - 126, 13, UI.CYAN)
	UI.draw_text(ci, SeatLogic.measure_text(c), Vector2(CV.position.x + 14, CV.end.y - 18), 11, UI.AMBER)


func _draw_fit(ci: CanvasItem) -> void:
	var c: Dictionary = cases()[case_i]
	var res: Array = SeatLogic.seat_eval(c, cfg)
	var checks: Array = res[0]
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
		if UI.phone():                                # строка-зона: подпись слева и значение справа над дорожкой
			var z := slider_zone(i)
			UI.draw_round_rect(ci, z, Color8(24, 26, 38, 205), Color8(70, 80, 100), 2, 8)
			var vt := SeatLogic.val_text(key, cfg[key])
			var vw := minf(UI.text_width(vt, 14), 180.0)
			_fit(ci, vt, Vector2(tr.end.x - vw, z.position.y + 5), vw, 14, col)
			UI.draw_text_w(ci, Loc.t(sl[0]), Vector2(tr.position.x, z.position.y + 6), tr.size.x - vw - 12, 13, UI.WHITE)
		else:
			UI.draw_text_w(ci, Loc.t(sl[0]), Vector2(tr.position.x, tr.position.y - 20), tr.size.x + 2, 13, UI.WHITE)   # не на значение
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
	if UI.phone():                                    # заголовок — имя клиента (как название урока); список — под ползунками
		y = slider_zone(keys.size() - 1).end.y + 2
	var room := fit_btn().position.y - (4 if UI.phone() else 6) - y
	var order: Array = []
	for ch: Array in checks:
		if not ch[1]:
			order.append(ch)
	for ch: Array in checks:
		if ch[1]:
			order.append(ch)
	var csz := 13
	var need := 0.0
	while true:
		need = 0.0
		for ch: Array in order:
			need += UI.wrap_lines(("✔ " if ch[1] else "⚠ ") + Loc.t(ch[2]), 476, csz).size() * (UI.line_height(csz) + 2) + 2
		if need <= room or csz <= 10:
			break
		csz -= 1
	# телефон: весь список не помещается и при 10 (или 5 ползунков — Голем, Искра) — только «⚠» кеглем от 13 до 10
	# (пока не поместятся), «✔» — за ними тем же кеглем, целыми строками, пока помещаются (не мельчим ради «✔»)
	if UI.phone() and (need > room or keys.size() >= 5):
		var warns: Array = order.filter(func(ch: Array) -> bool: return not ch[1])
		csz = 13
		while true:
			need = 0.0
			for ch: Array in warns:
				need += _check_h(ch, csz)
			if need <= room or csz <= 10:
				break
			csz -= 1
		for ch: Array in order:
			if ch[1]:
				if need + _check_h(ch, csz) > room:
					break
				need += _check_h(ch, csz)
				warns.append(ch)
		order = warns
	text_sizes["warn"] = csz
	text_sizes["warn_over"] = maxi(0, ceili(need - room))   # проверки: сколько px списка не поместилось
	text_sizes["warn_n"] = "%d⚠ %d✔ из %d" % [order.filter(func(ch: Array) -> bool: return not ch[1]).size(),
		order.filter(func(ch: Array) -> bool: return ch[1]).size(), checks.size()]
	var bottom := fit_btn().position.y - (4 if UI.phone() else 6)
	var first := true
	text_sizes["warn_shown"] = 0
	for ch: Array in order:
		var left := int((bottom - y) / (UI.line_height(csz) + 2))
		if left < 1:
			break
		# телефон: строка списка — целиком или никак (кроме первой: её начало лучше, чем пусто)
		if UI.phone() and not first and UI.wrap_lines(("✔ " if ch[1] else "⚠ ") + Loc.t(ch[2]), 476, csz).size() > left:
			break
		first = false
		text_sizes["warn_shown"] = int(text_sizes.get("warn_shown", 0)) + 1   # проверки: сколько строк видно
		y = UI.draw_wrapped(ci, ("✔ " if ch[1] else "⚠ ") + Loc.t(ch[2]), Vector2(780, y), 476, csz,
			UI.GOOD if ch[1] else UI.AMBER, false, 2, -1, left) + 2


## Высота строки списка примерки (с переносом) кеглем sz.
func _check_h(ch: Array, sz: int) -> float:
	return UI.wrap_lines(("✔ " if ch[1] else "⚠ ") + Loc.t(ch[2]), 476, sz).size() * (UI.line_height(sz) + 2) + 2


func _draw_quiz(ci: CanvasItem) -> void:
	if quiz_done:
		var ok := score >= SeatLogic.quiz_pass()
		var cc := CV.get_center()
		_text_plate(ci, Loc.t("Верно %d из %d" % [score, quiz.size()]), Vector2(cc.x + 40, cc.y - 20), 30,
			UI.GOOD if ok else UI.AMBER, true, 1)
		_text_plate(ci, Loc.t("Зачёт по посадке сдан!" if ok else "Для зачёта нужно %d. Перечитай уроки." % SeatLogic.quiz_pass()),
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
	_text_plate(ci, Loc.t("Вопрос %d из %d" % [quiz_i + 1, quiz.size()]), Vector2(780, 120 + Q_TOP), 15, UI.GREY)
	var qt := Loc.t(q["q"])                     # 150 %: вопрос (с подложкой) — над первым ответом
	var qy := 146 + Q_TOP
	var qsz := UI.fit_wrapped_size(qt, 476, 20, quiz_rect(0).position.y - 6 - qy, 14)
	text_sizes["q"] = qsz
	_wrapped_plate(ci, qt, Vector2(780, qy), 476, qsz, UI.WHITE)


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


## Телефон: кнопка списка — мини-иконка слева (если icon задан) и название целиком (до 2 строк, по середине кнопки).
func _draw_row(b: GameButton, r: Rect2, text: String, base: int, bold: bool, icon: Callable) -> void:
	var lay := _row_fit(text, r.size.x, base, bold, icon.is_valid())
	var isz: float = lay[0]
	var x := r.position.x + 8
	if isz > 0.0:
		icon.call(b, Rect2(x, r.position.y + floorf((r.size.y - isz) / 2.0), isz, isz))
		x += isz + 6
	var lines: PackedStringArray = lay[2]
	var sz: int = lay[1]
	var lh := UI.line_height(sz, bold) + 2
	var y := r.position.y + floorf((r.size.y - (lines.size() * lh - 2)) / 2.0)
	for ln in lines:
		UI.draw_text(b, ln, Vector2(x, y), sz, UI.WHITE, bold)
		y += lh


static var _row_cache := {}


## Раскладка подписи кнопки: [иконка px, кегль, строки]. Уступки по порядку: иконка 44 при кегле base, base − 1
## (в 1–2 строки), потом иконка 32, потом без иконки; не влезло и так — кегль ещё меньше (до 9), строк не больше 2.
func _row_fit(text: String, w: float, base: int, bold: bool, with_icon := true) -> Array:
	# множитель текста, а не выбор игрока: на вкладке примерки потолок 125 % (text_cap) — при 150 % раскладка как при 125 %
	var key := "%s|%d|%d|%s|%s|%s|%s" % [text, w, base, bold, Settings.text_k(), Settings.easy_font(), with_icon]
	if _row_cache.has(key):
		return _row_cache[key]
	var out: Array = []
	for isz: float in ([44.0, 32.0, 0.0] if with_icon else [0.0]):
		var tw := w - 16 - (isz + 6 if isz > 0.0 else 0.0)
		for sz: int in ([base, base - 1] if isz > 0.0 else range(base, 8, -1)):
			var lines := _row_lines(text, tw, sz, bold)
			if not lines.is_empty():
				out = [isz, sz, lines]
				break
		if not out.is_empty():
			break
	if out.is_empty():
		out = [0.0, 9, UI.wrap_lines(text, w - 16, 9, bold).slice(0, 2)]
	if _row_cache.size() > 400:
		_row_cache.clear()
	_row_cache[key] = out
	return out


## Строки подписи, если она помещается в ширину tw и в 2 строки высотой кнопки (52 px), иначе пусто.
static func _row_lines(text: String, tw: float, sz: int, bold: bool) -> PackedStringArray:
	var lines := UI.wrap_lines(text, tw, sz, bold)
	if lines.size() > 2 or lines.size() * (UI.line_height(sz, bold) + 2) - 2 > 52:
		return PackedStringArray()
	for ln in lines:
		if UI.text_width(ln, sz, bold) > tw:
			return PackedStringArray()
	return lines


## Мини-иконка урока i (с 0): плитка и пиктограмма урока i + 1 (LessonIcons — пачка треугольников, посчитана раз на
## размер и рисуется одним вызовом; перерисовка кнопки — только по её подписи _btn_sig).
func _draw_lesson_icon(ci: CanvasItem, i: int, box: Rect2) -> void:
	UI.draw_round_rect(ci, box.grow(2), Color8(14, 12, 20, 200), Color(), 0, 6)
	LessonIcons.draw(ci, i + 1, box)


## Мини-иконка клиента: верх портрета (квадратная вырезка по ширине картинки).
func _draw_case_icon(ci: CanvasItem, i: int, box: Rect2) -> void:
	var tex := Content.texture(cases()[i]["client_art"])
	if tex == null:
		return
	var ts := tex.get_size()
	var s := minf(ts.x, ts.y) * 0.72
	ci.draw_texture_rect_region(tex, box, Rect2((ts.x - s) / 2.0, 0, s, s))


func _draw_lesson_btn(b: GameButton, r: Rect2) -> void:
	var i := int(b.get_meta("i"))
	if UI.phone():
		_draw_row(b, r, "%d. %s" % [i + 1, Loc.t(lessons()[i]["title"])], 15, i == lesson,
			(func(ci: CanvasItem, box: Rect2) -> void: _draw_lesson_icon(ci, i, box)) if LessonIcons.has(i + 1)
			else Callable())
		return
	var isz := desk_icon("lessons") if LessonIcons.has(i + 1) else 0.0
	var tx := _desk_text_x(isz)
	var title := "%d. %s" % [i + 1, Loc.t(lessons()[i]["title"])]
	var bold := i == lesson
	if isz > 0.0:
		_draw_lesson_icon(b, i, Rect2(r.position.x + DESK_ICON_X, r.position.y + floorf((r.size.y - isz) / 2.0), isz, isz))
		if bold and not _fits_line(title, r.size.x - tx - 10, 15, true):
			bold = false                          # со значком: жирным не помещается — обычным (выбран — видно по кнопке)
	_fit(b, title, r.position + Vector2(tx, 9), r.size.x - tx - 10, 15, UI.WHITE, bold)


func _case_label(i: int) -> String:
	return ("✔ " if SaveGame.is_done(cases()[i]["id"]) else "") + Loc.t(cases()[i]["client"])


## Телефон: портреты на кнопках клиентов — у всех или ни у кого. С портретом имя — портрет 44 или 32 и кегль 14 или
## 13 (_row_fit: не больше одной ступени мельче соседей); если хоть одно имя так не помещается — портретов нет у всех
## (единообразно), имена — без иконки, как раньше. Раскладка подписей — в text_sizes["cases"] (проверки).
func case_icons() -> bool:
	var w := list_rect(0).size.x
	var all := true
	var lay := PackedStringArray()
	for i: int in SaveGame.seat_idx():
		var f := _row_fit(_case_label(i), w, 14, false, true)
		lay.append("%d/%d" % [int(f[0]), int(f[1])])
		if float(f[0]) <= 0.0:
			all = false
	if not all:
		lay.clear()
		for i: int in SaveGame.seat_idx():
			lay.append("0/%d" % int(_row_fit(_case_label(i), w, 14, false, false)[1]))
	text_sizes["cases"] = " ".join(lay)
	return all


func _draw_case_btn(b: GameButton, r: Rect2) -> void:
	var i := int(b.get_meta("i"))
	var done := SaveGame.is_done(cases()[i]["id"])
	if UI.phone():
		_draw_row(b, r, _case_label(i), 14, false,
			(func(ci: CanvasItem, box: Rect2) -> void: _draw_case_icon(ci, i, box)) if case_icons() else Callable())
		return
	var isz := desk_icon("fit")
	var tx := _desk_text_x(isz)
	if isz > 0.0:
		_draw_case_icon(b, i, Rect2(r.position.x + DESK_ICON_X, r.position.y + floorf((r.size.y - isz) / 2.0), isz, isz))
	_fit(b, ("✔ " if done else "") + Loc.t(cases()[i]["client"]), r.position + Vector2(tx, 8), r.size.x - tx - 10, 14,
		UI.WHITE)


## Компьютер (не телефонный режим; решение владельца 21.11 — намеренное отличие от game.py): значок слева на кнопке
## списка — у уроков пиктограмма LessonIcons, у клиентов верх портрета; кнопки те же (230×38 / 230×35), название в одну
## строку по прежнему правилу (кегль до 75 % → «…»), место под него уже на значок. Размер — наибольший из
## DESK_ICONS[kind], при котором ни одно название, помещавшееся без значка (без «…», обычным и жирным — выбранный урок),
## не начинает обрезаться; не годится и 22 — значков нет у всего списка. 0.0 — без значков. Считается по подписи
## (язык, множитель текста, шрифт, подписи с «✔»), не каждый кадр; итог — в text_sizes["desk_icons_<kind>"] (проверки).
const DESK_ICONS := {"lessons": [30.0, 26.0, 22.0], "fit": [28.0, 25.0, 22.0]}
const DESK_ICON_X := 6.0                  # отступ значка от края кнопки; текст — через 6 после значка
static var _desk_cache := {}


func _desk_text_x(isz: float) -> float:
	return DESK_ICON_X + isz + 6.0 if isz > 0.0 else 10.0


func _desk_labels(kind: String) -> Array:
	var out: Array = []
	if kind == "lessons":
		for i in lessons().size():
			if LessonIcons.has(i + 1):
				out.append("%d. %s" % [i + 1, Loc.t(lessons()[i]["title"])])
	else:
		for i: int in SaveGame.seat_idx():
			out.append(_case_label(i))
	return out


func desk_icon(kind: String) -> float:
	var labels := _desk_labels(kind)
	var key := "%s|%s|%s|%s|%s" % [kind, Loc.code, Settings.text_k(), Settings.easy_font(), "\n".join(labels)]
	if not _desk_cache.has(key):
		var w := list_rect(0).size.x
		var base := 15 if kind == "lessons" else 14
		var res := [0.0, ""]                     # [размер, что мешает при 22 — для проверок]
		for isz: float in DESK_ICONS[kind]:
			var ok := true
			for s: String in labels:
				for bold: bool in [false]:     # выбранный урок — жирным, только если так помещается (_draw_lesson_btn)
					if _fits_line(s, w - 20, base, bold) and not _fits_line(s, w - _desk_text_x(isz) - 10, base, bold):
						ok = false
						res[1] = s
			if ok:
				res = [isz, ""]
				break
		if _desk_cache.size() > 64:
			_desk_cache.clear()
		_desk_cache[key] = res
	var v: Array = _desk_cache[key]
	text_sizes["desk_icons_" + kind] = int(v[0])
	text_sizes["desk_icons_%s_why" % kind] = v[1]
	return v[0]


## Название помещается в ширину без «…» (fit_text: кегль до 75 %, потом многоточие).
static func _fits_line(s: String, w: float, size_: int, bold: bool) -> bool:
	return str(UI.fit_text(s, w, size_, bold)[0]) == s


func _draw_option(b: GameButton, _lifted: Rect2) -> void:
	var r := Rect2(b.slide, b.size)            # текст стоит на месте, кнопка при наведении поднимается (как в pygame)
	var i := int(b.get_meta("i"))
	var o: Array = quiz[quiz_i]["options"][i]
	var ot := Loc.t(o[0])                      # 150 %: ответ в 3 строки — мельче, не за рамку
	var ty := UI.draw_wrapped(b, ot, r.position + Vector2(14, 8), r.size.x - 28,
		UI.fit_wrapped_size(ot, r.size.x - 28, 15, r.size.y - 12, 11), UI.WHITE)
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
