extends Screen
## Про-задание Гильдии (draw_job_tech/click_job_tech/do_tech_action в game.py), то же — экзамен (exam: true).
## Фаза repair: порядок операций выбираешь сам — карточки операций (перемешаны), предпосылки after; операция раньше
## своего шага техники безопасности (safety) — немедленный провал (экран failed с разбором failnote); значения — из
## мануала (spec: окно с вариантами, открывается после чтения страницы); мини-игры шагов; палитра инструментов задания;
## слева — коляска кадрами поворота; Бренна в пузыре внизу. Фаза test: «ПРОВЕРКА ПОД НАГРУЗКОЙ» (коляска едет, Бренна
## парит рядом) → итог (или на экзамене — exam_result). Экзамен: случайный билет, без подсказок, без пропуска шагов,
## больше 3 ошибок — провал. Параметры: {"job": id, "exam": bool}.

const TEST_BTN := Rect2(UI.W / 2.0 - 170, 560, 340, 64)
const MANUAL_BTN := Rect2(UI.W - 204, 62, 180, 40)
const SKIP_BTN := Rect2(UI.W - 384, 60, 170, 26)
const CLIENT_IDLE := [22.0, 32.0]
const TALK_GAP := 5.0

var job: Dictionary = {}
var exam: bool = false
var phase: String = "repair"
var done_steps: Dictionary = {}
var step_order: Array = []
var mistakes: int = 0
var sel_tool: String = ""
var manual_viewed: Dictionary = {}
var ride_done: bool = false
var ghost_line: String = ""
var ghost_quip: String = ""
var ghost_quip_until: float = 0.0
var client_queue: Array = []
var client_next: float = 2.0
var talk_later: Array = []
var last_talk_t: float = -99.0
var talk_n: int = 0
var talk_used: Dictionary = {}
var esc_t: float = 0.0
var dispute: Dictionary = {}
var max_mistakes: int = 3

var tools: ToolPanel
var action: ToolAction
var ride: RideView
var mini: MiniGame
var spec_dlg: SpecDialog
var manual_dlg: ManualDialog
var chair: TurntableShow
var _ops: Array[GameButton] = []
var _deco: Control
var _mentor: SpeechBubble
var _bar_sig: Array = []
var _bar: TopBar
var _dispute_btn: GameButton
var _test_btn: GameButton
var _manual_page: String = ""


func _ready() -> void:
	exam = bool(params.get("exam", false))
	var base := Content.job_by_id(str(params.get("job", "truing")))
	if base.is_empty():
		base = Content.tech_jobs[0]
	job = Content.resolve_job(base)
	for st: Dictionary in job["steps"]:
		st["after"] = st.get("after", [])
		st["safety"] = st.get("safety", false)
		step_order.append(st["id"])
	step_order.shuffle()                         # порядок карточек не подсказывает решение
	max_mistakes = int(Content.consts.get("exam_max_mistakes", 3))
	if exam:
		ghost_line = "Бренна: «Экзамен. Билет — „%s“. Мануал разрешён, подсказок не будет. Больше %d ошибок — пересдача.»" \
			% [job["title"], max_mistakes]
	else:
		ghost_line = job.get("intro", "")
		client_queue = Content.client_talk(job["id"]).get("intro", []).duplicate()
	super._ready()


func _exit_tree() -> void:
	if not job.is_empty():
		Frames.release("tt:" + str(job["chair_art"]))


func music_theme() -> String:
	return "guild"


func text_cap() -> float:
	return 1.25                          # плотная раскладка (TEXT_CAP_SCENES в game.py)


func summary() -> String:
	return summary_full(true)


## Сводка про-задания (_a11y_job_summary, ветка tech): мини-игра, мануал, спека, операции, проверка под нагрузкой.
func summary_full(full: bool) -> String:
	if mini != null:
		return load("res://screens/job.gd").mini_summary(mini)
	if manual_dlg != null and manual_dlg.page != "":
		var e: Dictionary = Content.manual.get(manual_dlg.page, {})
		return "%s. %s. " % [Loc.t("Мануал"), Loc.t(e.get("title", ""))] + " ".join((e.get("lines", []) as Array).map(
			func(x: String) -> String: return Loc.t(x)))
	if spec_dlg != null:
		var sp: Dictionary = spec_dlg.spec()
		return Loc.t(sp["prompt"]) + ("" if manual_viewed.has(sp["manual"]) else " " + Loc.t("Сначала открой мануал — варианты откроются."))
	if phase == "repair":
		var out := "%s: %s." % [Loc.t("Выполнено"), A11y._of(done_steps.size(), job["steps"].size())]
		if full:
			out = "%s. %s " % [Loc.t(job["title"]), Loc.t(job["symptom"])] + out + " " + \
				Loc.t("Порядок шагов выбираешь сам: выбери инструмент, потом операцию. Значения — из мануала.")
		var voices: bool = Settings.a11y.get("voices", true)
		return out + (" " + Loc.t(ghost_line) if voices and ghost_line != "" and (Settings.barty_on() or
			not ghost_line.begins_with("Бартоломью")) else "")
	return Loc.t("Проверка под нагрузкой.") + " " + Loc.t(job.get("test", "")) + " " + Loc.t(
		"Проверка пройдена. Enter на кнопке ГОТОВО — к итогу." if ride_done else "Enter на кнопке — прокатить и проверить.")


func a11y_sig() -> Array:
	return [[phase, mini != null, manual_dlg != null, spec_dlg != null], [done_steps.size(), manual_dlg.page if manual_dlg != null else ""]]


func a11y_lines() -> Array:
	return [ghost_quip if t < ghost_quip_until else ""]


func hint_line() -> String:
	return ghost_line


func toast_bounds() -> Vector2:
	if dispute_visible():
		return Vector2(54, 346)
	return Vector2(54, 164)


func step_by_id(sid: String) -> Dictionary:
	for st: Dictionary in job["steps"]:
		if st["id"] == sid:
			return st
	return {}


func tech_chair_rect() -> Rect2:
	if phase == "test":
		return Rect2(UI.W / 2.0 - 215, 202, 430, 234)
	return Rect2(8, 308, 284, 226)


@warning_ignore("integer_division")
func op_rect(i: int) -> Rect2:
	var x0 := 300
	var y0 := 150
	var w := 470
	var gx := 16
	var gy := 10
	var per_col := maxi(5, (step_order.size() + 1) / 2)
	var h: int
	if per_col > 5:
		gy = 6
		h = mini(52, (362 - (per_col - 1) * gy) / per_col)
	else:
		h = mini(52, (306 - (per_col - 1) * gy) / per_col)
	return Rect2(x0 + (i / per_col) * (w + gx), y0 + (i % per_col) * (h + gy), w, h)


# ---------------- сборка ----------------

func build() -> void:
	_bar_sig = []
	_ops.clear()
	_test_btn = null
	tools = null
	add_child(BgLayer.make("bg_guild.png"))
	_bar = TopBar.make(("ЭКЗАМЕН: " if exam else "Гильдия: ") + job["title"], job.get("chair_name", ""))
	add_child(_bar)
	var face := Figure.make(job["client_art"], Vector2(24, 70), Vector2(150, 190), "breathe")
	face.name = "Client"
	add_child(face)
	chair = TurntableShow.make(job["chair_art"], tech_chair_rect(), 1.12 if phase == "test" else 1.0)
	add_child(chair)
	_deco = Control.new()
	_deco.name = "Deco"
	_deco.size = size
	_deco.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_deco.draw.connect(_draw_deco)
	add_child(_deco)
	_mentor = SpeechBubble.make(SpeechBubble.Kind.MENTOR)
	_mentor.job = job
	_mentor.top_y = 540.0 if phase == "repair" else 440.0
	_mentor.say(ghost_text())
	add_child(_mentor)
	if phase == "repair":
		var mb := GameButton.make(MANUAL_BTN, "МАНУАЛ", UI.PURPLE)
		mb.name = "Manual"
		mb.pressed.connect(open_manual.bind(""))
		add_child(mb)
		if not exam:
			var sk := GameButton.make(SKIP_BTN, "ПРОПУСТИТЬ ▸", UI.AMBER)
			sk.name = "StepSkip"
			sk.label_size = 15
			sk.pressed.connect(step_skip)
			add_child(sk)
		for i in step_order.size():
			var sid: String = step_order[i]
			var b := GameButton.make(op_rect(i), "", UI.AMBER)
			b.name = "Op_" + sid
			b.plain = true
			b.set_meta("sid", sid)
			b.on_draw = _draw_op
			b.redraw_sig = func() -> int: return done_steps.size()   # «✔» у сделанного; наведение видит кнопка
			b.pressed.connect(op_clicked.bind(sid))
			add_child(b)
			_ops.append(b)
		tools = ToolPanel.new()
		tools.ids = job.get("tools", [])
		tools.job_screen = self
		tools.tool_pressed.connect(select_tool)
		add_child(tools)
	else:
		_test_btn = GameButton.make(TEST_BTN, "ГОТОВО ▸" if ride_done else "ПРОВЕРИТЬ РАБОТУ", UI.GOOD)
		_test_btn.name = "TestDrive"
		_test_btn.pressed.connect(_test_pressed)
		add_child(_test_btn)
	action = ToolAction.new()
	add_child(action)
	ride = RideView.new()
	ride.tech = true
	ride.art = job["client_art"]
	ride.chair_art = job["chair_art"]
	ride.job_id = job["id"]
	add_child(ride)
	_dispute_btn = GameButton.make(Rect2(UI.W - 340, 10, 176, 34), "Я НЕ СОГЛАСЕН", UI.PURPLE)
	_dispute_btn.name = "Dispute"
	_dispute_btn.visible = false
	_dispute_btn.pressed.connect(open_dispute)
	add_child(_dispute_btn)
	Chrome.add(self, true, true, false)
	_update_a11y()


func first_focus() -> Control:
	if phase == "repair" and tools:
		return tools.tiles.get(sel_tool if sel_tool != "" else tools.ids[0]) if not tools.ids.is_empty() else null
	return _test_btn


func _update_a11y() -> void:
	for b in _ops:
		var sid: String = b.get_meta("sid")
		b.accessibility_name = Loc.t(step_by_id(sid)["instr"]) + (", " + Loc.t("выполнено") if done_steps.has(sid) else "")
		b.set_meta("a11y_group", "Операции")
	var sk := get_node_or_null("StepSkip") as Control
	if sk:
		sk.accessibility_name = Loc.t("Пропустить шаг (минус звезда)")
		sk.set_meta("a11y_group", "Шаги")
	if tools:
		tools.update_a11y(sel_tool)


func rebuild() -> void:
	var keep: Array[Control] = []
	for w: Control in [mini, spec_dlg, manual_dlg]:
		if w and w.get_parent() == self:
			remove_child(w)
			keep.append(w)
	# смена языка/размера текста пересобирает экран: проезд (идёт или герой уже стоит справа) — переживает пересборку,
	# иначе новый RideView пуст и на месте героя снова пустая коляска
	var rs := {}
	if ride:
		rs = {"active": ride.active, "stay": ride.stay, "loop": ride.loop_name, "t": ride.t, "t0": ride.t0,
			"drawn": ride.drawn}
	super.rebuild()
	if rs.get("active", false) or rs.get("stay", false):
		ride.loop_name = rs["loop"]
		ride.t = rs["t"]
		ride.t0 = rs["t0"]
		ride.drawn = rs["drawn"]
		ride.active = rs["active"]
		ride.stay = rs["stay"]
		chair.visible = not (ride.active or ride.stay)
		if _test_btn:
			_test_btn.visible = not ride.riding()
	for w in keep:
		add_child(w)
	if not keep.is_empty():
		UI.set_focus_enabled(self, false)
		UI.set_focus_enabled(keep[-1], true)
		UI.focus_later((keep[-1] as Variant).first_focus())


# ---------------- для панели инструментов ----------------

func tutor_want() -> Array:
	return []


func tutor_step() -> Dictionary:
	return {}


func note_part_at() -> String:
	return ""


# ---------------- действия ----------------

func select_tool(tid: String) -> void:
	sel_tool = tid
	Audio.sfx(Content.consts.get("tool_sound", {}).get(tid, "tool_metal"))
	Speech.say(Loc.tf("В руке: {0}", [Loc.t(Content.tools[tid]["name"])]), true)
	if tools:
		tools.update_a11y(sel_tool)


func op_clicked(sid: String) -> void:
	if sel_tool == "":
		Nav.flash("Сначала выбери инструмент внизу.", UI.AMBER, 2.5)
	else:
		do_tech_action(sel_tool, sid)


func _op_pos(sid: String) -> Vector2:
	var i := step_order.find(sid)
	if i < 0:
		return Vector2(UI.W / 2.0, 300)
	var r := op_rect(i)
	return Vector2(r.end.x - 40, r.get_center().y)


## Попытка операции: "ok" | "spec" | "mini" | "wrong" | "fail" | "done" (do_tech_action).
func do_tech_action(tid: String, sid: String) -> String:
	var st := step_by_id(sid)
	if done_steps.has(sid):
		Nav.flash("Этот шаг уже выполнен.", UI.GREY, 2.0)
		return "done"
	var missing: Array = st["after"].filter(func(a: String) -> bool: return not done_steps.has(a))
	for ms: String in missing:
		var pre := step_by_id(ms)
		if pre["safety"]:
			fail_tech(st, pre)
			return "fail"
	if not missing.is_empty():
		var pre := step_by_id(missing[0])
		miss("Рано! Порядок операций нарушен." if exam else "Рано! Сначала: " + pre["instr"] + ".")
		return "wrong"
	if tid != st["tool"]:
		action.start(tid, false, _op_pos(sid), st.get("part", ""))
		miss("Инструмент не тот." if exam else Loc.fmt("Инструмент не тот. Нужен: {0}.", [Content.tools[st["tool"]]["name"]]), 3.5)
		return "wrong"
	if st.get("spec") is Dictionary:
		if not exam:
			ghost_line = "Бренна: «Стоп. Сначала цифры из мануала, потом руки.»"
		open_spec(st)
		return "spec"
	if st.get("mini") is Dictionary:
		start_mini(st)
		return "mini"
	complete_tech_step(st)
	return "ok"


func complete_tech_step(st: Dictionary) -> void:
	action.start(st["tool"], true, _op_pos(st["id"]))
	done_steps[st["id"]] = true
	sel_tool = ""
	close_spec()
	Audio.sfx("ok")
	Nav.flash("Шаг выполнен. " + str(st.get("note", "")), UI.GOOD, 4.0, true)
	if st.get("ghost", "") != "" and not exam:
		ghost_line = st["ghost"]
	_update_a11y()
	if done_steps.size() >= job["steps"].size():
		phase = "test"
		if RideView.tech_loop(job["id"]) != "":       # пока читают — подгрузить кадры петли проезда (anim_prefetch)
			Frames.want_loop(RideView.tech_loop(job["id"]))
		ghost_line = "Экзамен: сборка окончена. Финальная проверка." if exam \
			else "Бренна: «Закончил? Слова дешёвые. Проверим под нагрузкой.»"
		if not exam:
			talk_later = [t + 1.5, "client", "test"]
		rebuild()
	else:
		react_good()


func choose_spec(idx: int) -> bool:
	if spec_dlg == null:
		return false
	var st: Dictionary = spec_dlg.step
	var spec: Dictionary = st["spec"]
	if not manual_viewed.has(spec["manual"]):
		Nav.flash("Сначала открой мануал и сверься со спецификацией.", UI.AMBER, 3.0)
		return false
	var o: Array = spec["options"][idx]
	if o[1]:
		complete_tech_step(st)
		return true
	miss(o[2] if o.size() > 2 and str(o[2]) != "" else "Неверно. Перечитай мануал.")
	return false


func fail_tech(st: Dictionary, pre: Dictionary) -> void:
	var msg := "Ты попытался: «%s» — не выполнив шаг техники безопасности: «%s». " % [st["instr"], pre["instr"]] \
		+ str(pre.get("failnote", ""))
	var elec: Array = Content.consts.get("electric_parts", [])
	var zap: bool = st.get("part", "") in elec or pre.get("part", "") in elec
	Audio.sfx("fail")
	if zap:
		Audio.sfx("zap")
	Nav.go("failed", {"msg": msg, "exam": exam, "job": job["id"], "zap": zap})


## Ошибка: сообщение, счётчик, на экзамене — лимит (miss + _exam_check).
func miss(msg: String, secs: float = 4.0) -> void:
	mistakes += 1
	Audio.sfx("bad")
	Nav.flash(msg, UI.BAD, secs, true)
	if dispute.is_empty() or dispute["t"] != t:
		note_dispute("mistake", "", "", msg)
	react_mistake()
	if exam and mistakes > max_mistakes:
		close_mini()
		close_spec()
		Audio.sfx("fail")
		Nav.go("failed", {"msg": "Лимит ошибок экзамена исчерпан: %d при допустимых %d. Бренна молча закрывает ведомость."
			% [mistakes, max_mistakes], "exam": true, "job": job["id"], "zap": false})


## «ПРОПУСТИТЬ ▸»: игра делает одну доступную операцию сама (две ошибки); на экзамене нельзя (_tech_skip).
func step_skip() -> void:
	if exam:
		Nav.flash("На экзамене шаги не пропускаются.", UI.AMBER, 3.0)
		return
	var st: Dictionary = {}
	for s: Dictionary in job["steps"]:
		if not done_steps.has(s["id"]) and s["after"].all(func(a: String) -> bool: return done_steps.has(a)):
			st = s
			break
	if st.is_empty():
		return
	close_mini()
	mistakes += 2
	var ans := ""
	if st.get("spec") is Dictionary:
		for o: Array in st["spec"]["options"]:
			if o[1]:
				ans = o[0]
	complete_tech_step(st)
	var msg := "%s: %s (%s)." % [Loc.t("Шаг пропущен — правильно"), Loc.t(st["instr"]), Loc.t(Content.tools[st["tool"]]["name"])]
	if ans != "":
		msg += " " + Loc.t(ans) + "."
	if str(st.get("note", "")) != "":
		msg += " " + Loc.t(st["note"])
	Nav.flash(msg, UI.AMBER, 7.0, true)


# ---------------- окна: мануал, спека, мини-игра ----------------

func _modal(w: Control) -> void:
	UI.set_focus_enabled(self, false)
	add_child(w)


func _unmodal() -> void:
	UI.set_focus_enabled(self, true)
	if spec_dlg:                                  # мануал поверх спеки — фокус обратно в спеку
		UI.set_focus_enabled(self, false)
		UI.set_focus_enabled(spec_dlg, true)
		spec_dlg.refresh()
		UI.focus_later(spec_dlg.first_focus())
	else:
		_focus_default()


func open_manual(key: String = "") -> void:
	if manual_dlg:
		return
	var pages: Array = job.get("manual", [])
	if pages.is_empty():
		pages = Content.manual.keys()
	manual_dlg = ManualDialog.make(pages, key if key != "" else _manual_page, manual_viewed)
	manual_dlg.closed.connect(func() -> void:
		_manual_page = manual_dlg.page
		manual_dlg = null
		_unmodal())
	Audio.sfx("tick")
	_modal(manual_dlg)


func open_spec(st: Dictionary) -> void:
	close_spec()
	spec_dlg = SpecDialog.make(st, manual_viewed)
	spec_dlg.chosen.connect(func(i: int) -> void: choose_spec(i))
	spec_dlg.open_manual.connect(func(key: String) -> void: open_manual(key))
	spec_dlg.closed.connect(close_spec)
	_modal(spec_dlg)


func close_spec() -> void:
	if spec_dlg:
		spec_dlg.queue_free()
		spec_dlg = null
		if manual_dlg == null:
			_unmodal()


func start_mini(st: Dictionary) -> void:
	close_mini()
	mini = MiniGame.make(st)
	mini.solved.connect(func() -> void:
		var s: Dictionary = mini.step
		close_mini()
		complete_tech_step(s))
	mini.missed.connect(func(msg: String, secs: float) -> void: miss(msg, secs))
	mini.closed.connect(close_mini)
	_modal(mini)


func close_mini() -> void:
	if mini:
		mini.queue_free()
		mini = null
		_unmodal()


# ---------------- проверка под нагрузкой ----------------

func _test_pressed() -> void:
	if ride.riding():
		return
	if ride_done:
		finish_test()
		return
	ride.start(ride.t)
	if Settings.calm():
		ride.t0 = ride.t - ride.secs()
	Audio.sfx("whoosh")
	chair.visible = false
	_test_btn.visible = false


@warning_ignore("integer_division")
func finish_test() -> void:
	Audio.sfx("fanfare")
	if exam:
		SaveGame.exam_passed = true
		SaveGame.save()
		Nav.go("exam_result", {"mistakes": mistakes})
		return
	var stars := maxi(1, 3 - mistakes / 2)
	var jid: String = job["id"]
	SaveGame.done[jid] = true
	var found := false
	for g: Array in SaveGame.garage:
		if g[0] == jid:
			found = true
			if stars > int(g[1]):
				g[1] = stars
	if not found:
		SaveGame.garage.append([jid, stars])
	var gag := ""
	if randf() < 0.5:
		var legs: Array = Content.talk.get("leg_gags", []).filter(func(g: String) -> bool:
			return Settings.barty_on() or not g.begins_with("Бартоломью"))
		gag = legs.pick_random() if not legs.is_empty() else ""
	else:
		var pool: Array = Content.talk.get("martin", {}).get("good" if mistakes == 0 else "mistake", [])
		gag = pool.pick_random() if not pool.is_empty() else ""
	SaveGame.save()
	Nav.go("result", {"job": job, "stars": stars, "gag": gag, "mistakes": mistakes})


func go_back() -> void:
	if manual_dlg:
		manual_dlg.close()
		return
	if spec_dlg:
		close_spec()
		return
	if mini:
		close_mini()
		return
	if esc_t > 0.0:
		esc_t = 0.0
		Nav.go("guild")
		return
	esc_t = 2.5
	Nav.flash("Ещё раз Esc — покинуть ремонт (прогресс задания сбросится).", UI.AMBER, esc_t)


# ---------------- замечания ----------------

func _done_text() -> String:
	return ("сделано: " + ", ".join(done_steps.keys())) if not done_steps.is_empty() else "начало"


func note_dispute(kind: String, expected: String, got: String, msg: String) -> void:
	dispute = {"kind": kind, "job": job["id"], "title": job.get("title", ""), "phase": phase, "step": _done_text(),
		"expected": expected, "got": got, "msg": msg, "t": t, "sent": false, "scene": "job"}


func dispute_visible() -> bool:
	return not dispute.is_empty() and not dispute["sent"] and t - float(dispute["t"]) < 25.0 and Nav.feedback == null \
		and not ride.riding()


func open_dispute() -> void:
	var d := dispute
	Nav.open_feedback(d, func(sent: bool, online: bool) -> void:
		if not sent:
			return
		d["sent"] = true
		var refunded := false
		if not exam and mistakes > 0:          # на экзамене ошибки не списываются
			mistakes -= 1
			refunded = true
		Nav.flash(("Спасибо! Замечание отправляется разработчикам." if online else
			"Спасибо! Замечание сохранено — его проверят и поправят игру.")
			+ (" Эта ошибка не засчитана." if refunded else ""), UI.GOOD, 5.0))


func feedback_context() -> Dictionary:
	return {"kind": "general", "job": job["id"], "title": job.get("title", ""), "phase": phase, "step": "",
		"expected": "", "got": "", "msg": "", "scene": "job"}


# ---------------- реплики ----------------

func ghost_text() -> String:
	return ghost_quip if ghost_quip != "" and t < ghost_quip_until else ghost_line


func _show_client(line: String) -> void:
	if line == "":
		return
	client_next = t + randf_range(CLIENT_IDLE[0], CLIENT_IDLE[1])
	last_talk_t = t
	if not Settings.barty_on() and (line.begins_with("Барти") or line.begins_with("Бартоломью")):
		return
	ghost_quip = line                          # в Гильдии все реплики — в пузыре наставника
	ghost_quip_until = t + maxf(7.0, 3.0 + line.length() / 12.0)


func _pick(kind: String) -> String:
	var lines: Array = Content.client_talk(job["id"]).get(kind, [])
	if lines.is_empty():
		return ""
	var used: Array = talk_used.get(kind, [])
	var left: Array = lines.filter(func(l: String) -> bool: return not l in used)
	if left.is_empty():
		used.clear()
		left = lines.duplicate()
	var line: String = left.pick_random()
	used.append(line)
	talk_used[kind] = used
	return line


func react_mistake() -> void:
	if exam or Settings.quiet_talk():
		return
	client_queue.clear()
	if randf() < 0.75:
		talk_later = [t + 1.2, "client", "mistake"]


func react_good() -> void:
	if exam or Settings.quiet_talk():
		return
	if randf() < 0.3:
		talk_later = [t + 1.8, "client", "good"]


func _talk_tick() -> void:
	if ride.riding() or mini or spec_dlg or manual_dlg:
		return
	var toast := Nav.toast
	var quiet := t - last_talk_t < TALK_GAP or (toast.active() and (not toast.sticky or toast.t - toast.t0 < 3.0))
	if Settings.quiet_talk():
		talk_later = []
		if not client_queue.is_empty() and t >= client_next and not quiet and not exam:
			_show_client(client_queue[0])
			client_queue.clear()
		return
	if not talk_later.is_empty() and t >= talk_later[0]:
		if quiet:
			if t - talk_later[0] > 8.0:
				talk_later = []
			return
		var later := talk_later
		talk_later = []
		_show_client(_pick(later[2]))
		return
	if phase == "test" or exam:
		return
	if t >= client_next and not quiet:
		if not client_queue.is_empty():
			_show_client(client_queue.pop_front())
			client_next = t + 10.0
		else:
			talk_n += 1
			client_next = t + randf_range(CLIENT_IDLE[0], CLIENT_IDLE[1])
			_show_client(_pick("learn" if talk_n % 2 == 0 else "worry"))


# ---------------- кадр ----------------

func tick(dt: float) -> void:
	if esc_t > 0.0:
		esc_t -= dt
	_talk_tick()
	var riding := ride.riding()
	if Frames.net and phase == "test" and not ride_done and not riding and RideView.tech_loop(job["id"]) != "":
		Frames.want_loop(RideView.tech_loop(job["id"]))   # браузер: петля качается по сети — держать, пока читают
	if ride.active and not riding:
		ride.active = false
		ride_done = true
		ghost_line = "Бренна: «Проверка пройдена. Дочитаешь — жми ГОТОВО.»"
		ride.stay = ride.loop_name != "" and not Settings.calm()   # проехал(а) и стоит справа, а не пустая коляска
		chair.visible = not ride.stay
		_test_btn.visible = true
		_test_btn.set_label("ГОТОВО ▸")
		UI.focus_later(_test_btn)
	_mentor.visible = not riding
	if _mentor.say(ghost_text()) and _mentor.shown():
		Audio.sfx("ghost")
	var dv := dispute_visible()
	_dispute_btn.visible = dv
	_bar.brand = not dv
	_bar.right_edge = (UI.W - 352.0) if dv else UI.W - 170.0
	if _bar_sig != [_bar.brand, _bar.right_edge]:   # шапка — только когда сменилась
		_bar_sig = [_bar.brand, _bar.right_edge]
		_bar.queue_redraw()
	redraw_on(_deco, [phase, step_order.size(), done_steps.size(), mistakes, ride_done, ride.riding()])


func _draw_deco() -> void:
	UI.draw_wrapped(_deco, Loc.t(job["client"]), Vector2(24, 266), 168, 15, UI.WHITE, false, 2, -1, 2)
	if phase == "repair":
		UI.draw_text(_deco, Loc.t("ЭКЗАМЕН ГИЛЬДИИ — подсказок нет, мануал разрешён" if exam
			else "ЗАДАНИЕ ТЕХНИКА — порядок шагов выбираешь сам"), Vector2(300, 62), 17, UI.CYAN, true)
		UI.draw_wrapped(_deco, Loc.t(job["symptom"]), Vector2(300, 88), 770, 14, UI.WHITE)
		var y_stat := 466.0
		for i in step_order.size():
			y_stat = maxf(y_stat, op_rect(i).end.y + 6)
		var lim := (" (лимит %d)" % max_mistakes) if exam else ""
		UI.draw_text(_deco, Loc.t("Выполнено: %d/%d   Ошибки: %d%s" % [done_steps.size(), job["steps"].size(), mistakes, lim]),
			Vector2(300, y_stat), 14, UI.GHOST)
	else:
		UI.draw_text(_deco, Loc.t("ПРОВЕРКА ПОД НАГРУЗКОЙ"), Vector2(360, 70), 20, UI.GOOD, true)
		UI.draw_wrapped(_deco, Loc.t(job.get("test", "")), Vector2(360, 100), 560, 19, UI.WHITE)
		if ride_done and not ride.riding():
			var lbl := Loc.t("✔ Проверка пройдена")
			var w := UI.text_width(lbl, 17, true)
			var c := Vector2(TEST_BTN.get_center().x, TEST_BTN.position.y - 22)
			UI.draw_round_rect(_deco, Rect2(c - Vector2(w / 2 + 8, UI.line_height(17, true) / 2 + 4),
				Vector2(w + 16, UI.line_height(17, true) + 8)), Color8(14, 12, 20, 175), Color(), 0, 8)
			UI.draw_text(_deco, lbl, c, 17, UI.GOOD, true, 1)


func _draw_op(b: GameButton, _r: Rect2) -> void:
	var sid: String = b.get_meta("sid")
	var st := step_by_id(sid)
	var done := done_steps.has(sid)
	var r := Rect2(Vector2.ZERO, b.size)
	UI.draw_round_rect(b, r, Color8(24, 34, 28) if done else UI.PANEL, UI.GOOD if done else (UI.AMBER if b.is_hovered() else UI.DIM), 2, 6)
	var txt := ("✔ " if done else "• ") + Loc.t(st["instr"])
	var pad := 4 if r.size.y >= 44 else 2
	var fs := 10
	for s: int in [13, 12, 11, 10]:
		fs = s
		if UI.wrap_lines(txt, r.size.x - 20, s).size() * (UI.line_height(s) + 2) <= r.size.y - 2 * pad:
			break
	UI.draw_wrapped(b, txt, Vector2(10, pad), r.size.x - 20, fs, UI.GREY if done else UI.WHITE)
