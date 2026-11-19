extends Screen
## Экран задания (draw_job/click_job и логика задания из game.py) для ЛЮБОГО задания из данных, без кода под задание.
## Фазы: diagnose → repair → test, потом экран итога (result).
##   diagnose — симптом, коляска на кадрах поворота с кружками, «ОСМОТРЕТЬ», «ДИАГНОЗ» (после INSPECT_REQ осмотров).
##   repair   — шаг k/n с точками, «◂» (шаг назад) и «ШАГ ▸» (пропуск = 2 ошибки), инструкция, «ДЕТАЛЬ» со сносками
##              (книжка), панель инструментов: выбрать инструмент → деталь (кружок или список); верно — анимация
##              инструмента и следующий шаг, мини-игра шага (mini) — окном; неверно — ошибка (wrongmsg или «не тот
##              инструмент/деталь»), реакции клиента и Барти. Обучение в первом задании (flat): нужное — в зелёной рамке.
##   test     — «ТЕСТ-ДРАЙВ», текст test, «ПРОКАТИТЬ И ПРОВЕРИТЬ» → проезд героя → «ГОТОВО ▸» → итог.
## Улики, итоги ходов и ошибки — сообщением сверху (flash). Параметры: {"job": id, "variant": индекс или −1}.

const CHAIR_CX := 575.0                  # центр зоны коляски: между портретом и правой колонкой
const QUIP_IDLE := [35.0, 50.0]          # пауза между шутками Барти на диагностике
const CLIENT_IDLE := [22.0, 32.0]        # пауза между репликами клиента
const TALK_GAP := 5.0                    # между репликами персонажей — не меньше
const PREV_RECT := Rect2(836, 58, 40, 30)
const SKIP_RECT := Rect2(882, 58, 88, 30)
const TEST_BTN := Rect2(UI.W / 2.0 - 170, 560, 340, 64)

var job: Dictionary = {}
var phase: String = "diagnose"
var inspected: Dictionary = {}
var mistakes: int = 0
var step_idx: int = 0
var sel_tool: String = ""
var last_note: String = ""
var note_pin: String = ""
var ride_done: bool = false
var ghost_line: String = ""
var ghost_quip: String = ""
var ghost_quip_until: float = 0.0
var client_line: String = ""
var client_t: float = 0.0
var client_queue: Array = []
var client_next: float = 2.0
var talk_later: Array = []               # [время, "client"|"barty", вид]
var last_talk_t: float = -99.0
var quip_next: float = 0.0
var talk_n: int = 0
var talk_used: Dictionary = {}
var esc_t: float = 0.0
var inspect_req: int = 2
var log_actions: Array = []              # [инструмент, деталь, итог] — для проверок
var dispute: Dictionary = {}             # последняя засчитанная ошибка — её можно оспорить («Я НЕ СОГЛАСЕН»)

var chair: ChairView
var tools: ToolPanel
var mini: MiniGame
var notes: NotesDialog
var action: ToolAction
var ride: RideView
var portrait: MagicPortrait
var _deco: Control
var _fx: Control
var _part_btns: Array[GameButton] = []
var _diag_btns: Array[GameButton] = []
var _client_bubble: SpeechBubble
var _mentor: SpeechBubble
var _skip: GameButton
var _test_btn: GameButton
var _prev_btn: GameButton
var _dsize: int = 14
var _m3d_state: Dictionary = {}          # ракурс коляски переживает пересборку экрана
var _ok_t: float = -9.0
var _ok_pos: Vector2
var _portrait_state: Array = []
var _bar: TopBar
var _dispute_btn: GameButton


func _ready() -> void:
	var base := Content.job_by_id(str(params.get("job", "flat")))
	if base.is_empty():
		base = Content.jobs[0]
	job = Content.resolve_job(base, int(params.get("variant", -1)))
	inspect_req = int(Content.consts.get("inspect_req", 2))
	ghost_line = job.get("intro", "Бартоломью: «Так-так... осмотри детали и реши, что сломалось.»")
	client_queue = Content.client_talk(job["id"]).get("intro", []).duplicate()
	client_next = 2.0                    # клиент заговорит, когда сцена появится и осмотришься
	quip_next = randf_range(QUIP_IDLE[0], QUIP_IDLE[1])
	super._ready()


## Ушли с экрана задания — кадры коляски из памяти (держим только текущую коляску).
func _exit_tree() -> void:
	if not job.is_empty():
		Frames.release("tt:" + str(job["chair_art"]))


func music_theme() -> String:
	return "guild" if job.get("track") == "tech" else "workshop"


func summary() -> String:
	return summary_full(true)


## Сводка задания (_a11y_job_summary): мини-игра, сноски, диагноз, шаг ремонта, тест-драйв.
func summary_full(full: bool) -> String:
	if mini != null:
		return mini_summary(mini)
	if phase == "diagnose":
		return "%s. %s: %s. %s: %s. %s " % [Loc.t(job["title"]), Loc.t("Клиент"), Loc.t(job["client"]), Loc.t("Коляска"),
			Loc.t(job.get("chair_name", "")), Loc.t(job["symptom"])] + \
			Loc.t("Осмотри детали, минимум две, потом выбери диагноз. Tab — переход между группами.")
	if phase == "repair":
		var n: int = job["steps"].size()
		var st: Dictionary = job["steps"][mini(step_idx, n - 1)]
		var out := "%s %s: %s" % [Loc.t("Шаг"), A11y._of(step_idx + 1, n), Loc.t(st["instr"])]
		if full:
			out += " " + Loc.t("Выбери инструмент, потом деталь.")
		if Settings.a11y.get("voices", true) and ghost_audible():
			out += " " + Loc.t(ghost_line)
		return out
	return Loc.t("Тест-драйв.") + " " + Loc.t(job.get("test", "")) + " " + Loc.t(
		"Проверка пройдена. Enter на кнопке ГОТОВО — к итогу." if ride_done else "Enter на кнопке — прокатить и проверить.")


## Мини-игра (_a11y_job_summary, ветка mini_pending): инструкция шага, подсказка, что делать.
static func mini_summary(m: MiniGame) -> String:
	var cfg: Dictionary = m.cfg
	var hint: String = cfg.get("hint", "") if str(cfg.get("hint", "")) != "" else str(cfg.get("prompt", ""))
	var out := Loc.t(m.step["instr"]) + ". " + Loc.t(hint)
	match m.kind:
		"pump":
			out += " %s: %d %s. " % [Loc.t("Сейчас"), m.value, Loc.t(cfg["unit"])] + Loc.t("Нужно попасть в зелёную зону") + \
				": %s–%s %s. " % [Share.pystr(cfg["lo"]), Share.pystr(cfg["hi"]), Loc.t(cfg["unit"])] + \
				Loc.t("Enter на «Качать» — подкачать, «Стравить» — выпустить лишнее, потом «Готово».")
		"gap":
			out += " %s: %s–%s %s. " % [Loc.t("Допуск"), Share.pystr(cfg["lo"]), Share.pystr(cfg["hi"]), Loc.t(cfg["unit"])] + \
				Loc.t("Стрелки влево-вправо — значение, потом «Проверить».")
		"ping":
			out += " " + Loc.t("Простукивай спицы по очереди и слушай: звонкая — в норме, глухая — ослабла.")
		"meter":
			out += " %s: %s. %s" % [Loc.t("Прибор показывает"), Loc.t(cfg["reading"]), Loc.t(cfg.get("sub", ""))]
	return out


## Подсказку призрака озвучиваем по тому же правилу, что рисуем пузырь (_ghost_audible): Барти — если он включён.
func ghost_audible() -> bool:
	return ghost_line != "" and (Settings.barty_on() or not ghost_line.begins_with("Бартоломью") and not ghost_line.begins_with("Барти"))


func a11y_sig() -> Array:
	return [[phase, mini != null, notes != null and notes.visible], [step_idx]]


func a11y_lines() -> Array:
	var q := ghost_quip if t < ghost_quip_until else ""
	return [client_line, q]


func hint_line() -> String:
	return ghost_line if ghost_audible() else ""


func client_now() -> String:
	return client_line


func toast_bounds() -> Vector2:
	if dispute_visible():
		return Vector2(54, UI.W - (UI.W - 340) + 6)
	if _skip != null and _skip.visible:
		return Vector2(54, UI.W - _skip.position.x + 6)
	return Vector2(54, 164)


func first_focus() -> Control:
	if mini:
		return mini.first_focus()
	if phase == "diagnose" and not _part_btns.is_empty():
		return _part_btns[0]
	if phase == "repair" and tools:
		return tools.tiles.get(sel_tool if sel_tool != "" else "hands")
	return _test_btn


## Первое задание (Мартин), пока обучение не пройдено: в шапке — «Пропустить обучение».
func tutorial_skip_shown() -> bool:
	return job.get("id") == "flat" and not SaveGame.tutorial_ok()


func steps() -> Array:
	return job.get("steps", [])


func cur_step() -> Dictionary:
	return steps()[step_idx] if step_idx < steps().size() else {}


# ---------------- раскладка (как в game.py) ----------------

func chair_rect() -> Rect2:
	var top: float
	var h: float
	if phase == "diagnose":
		var lines := UI.wrap_lines(Loc.t(job["symptom"]), 560, 17).size()
		top = 100 + lines * (UI.line_height(17) + 2) + 8
		h = 556 - top
	else:
		top = 226
		h = 322
	var w := int(h * 380 / 300)
	return Rect2(CHAIR_CX - int(w / 2.0), top, w, h)


func part_rect(i: int) -> Rect2:
	return Rect2(980, 96 + i * 42, 280, 36)


func right_col_top() -> float:
	return 96 + job["parts"].size() * 42


func diag_rects() -> Array[Rect2]:
	var n: int = job["diagnosis"].size()
	var top := right_col_top() + 30
	var bottom := 668.0 if not Content.job_notes(job).is_empty() else 712.0
	var h := minf(68, floorf((bottom - top) / n) - 8)
	var out: Array[Rect2] = []
	for i in n:
		out.append(Rect2(980, top + i * (h + 8), 280, h))
	return out


# ---------------- сборка ----------------

func build() -> void:
	_part_btns.clear()
	_diag_btns.clear()
	_skip = null
	_test_btn = null
	_prev_btn = null
	tools = null
	add_child(BgLayer.make("bg_workshop.png"))
	var bar := TopBar.make(job["title"], job.get("chair_name", ""))
	if tutorial_skip_shown():
		_skip = GameButton.make(Rect2(UI.W - 390, 9, 210, 36), "ПРОПУСТИТЬ ОБУЧЕНИЕ ▸", UI.CYAN)
		_skip.name = "SkipTutorial"
		_skip.pressed.connect(skip_tutorial)
		bar.brand = false
		bar.right_edge = _skip.position.x - 12
	add_child(bar)
	_bar = bar
	var c: Dictionary = Content.consts.get("magic", {})
	var pb: Array = c.get("box", [24, 70, 150, 190])
	portrait = MagicPortrait.make(job["client_art"], Rect2(pb[0], pb[1], pb[2], pb[3]), float(c.get("top", 55)), false)
	if not _portrait_state.is_empty():                       # пересборка: волшебство не начинается заново
		portrait.t = _portrait_state[0]
		portrait.auto = _portrait_state[1]
		portrait.enter_t = 0.0
	add_child(portrait)
	_deco = Control.new()
	_deco.name = "Deco"
	_deco.size = size
	_deco.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_deco.draw.connect(_draw_deco)
	add_child(_deco)
	_client_bubble = SpeechBubble.make(SpeechBubble.Kind.CLIENT)
	_client_bubble.bottom = 572.0 if phase == "diagnose" else 548.0
	_client_bubble.say(client_line)
	_client_bubble.t0 = client_t - t + _client_bubble.t      # пересборка экрана — пузырь не выпрыгивает заново
	add_child(_client_bubble)
	_mentor = SpeechBubble.make(SpeechBubble.Kind.MENTOR)
	_mentor.job = job
	if phase != "diagnose":                                  # в ремонте — узкий пузырь в правой колонке
		var top := right_col_top() + 10
		_mentor.col = Rect2(980, top, 280, 552 - top)
	_mentor.say(ghost_text())
	add_child(_mentor)
	chair = ChairView.new()
	chair.show_spots = phase in ["diagnose", "repair"]
	chair.pulse = phase == "diagnose"
	chair.setup(job["chair_art"], job["parts"], chair_rect(), inspected if phase == "diagnose" else {})
	if not _m3d_state.is_empty():
		chair.yaw = _m3d_state["yaw"]
		chair.zoom_k = _m3d_state["zoom_k"]
		chair.t0 = -1e9
	chair.part_pressed.connect(part_clicked)
	chair.visible = not ride_done
	add_child(chair)
	var cr := chair_rect()
	if chair.has_frames() and phase in ["diagnose", "repair"]:
		var zin := GameButton.make(Rect2(cr.end.x - 44, cr.position.y + 4, 40, 36), "+", UI.CYAN)
		zin.name = "ZoomIn"
		zin.accessibility_name = Loc.t("Крупнее")
		zin.pressed.connect(zoom.bind(1))
		add_child(zin)
		var zout := GameButton.make(Rect2(cr.end.x - 44, cr.position.y + 44, 40, 36), "−", UI.CYAN)
		zout.name = "ZoomOut"
		zout.accessibility_name = Loc.t("Мельче")
		zout.pressed.connect(zoom.bind(-1))
		add_child(zout)
	match phase:
		"diagnose":
			_build_diagnose()
		"repair":
			_build_repair()
		_:
			_build_test()
	if not Content.job_notes(job).is_empty() and phase in ["diagnose", "repair"]:
		var nb := GameButton.make(Rect2(UI.W - 24 - 180, UI.H - 44, 180, 34), "СНОСКИ МАНУАЛА", UI.PURPLE)
		nb.name = "Notes"
		nb.pressed.connect(open_notes)
		add_child(nb)
	action = ToolAction.new()
	add_child(action)
	ride = RideView.new()
	ride.art = job["client_art"]
	ride.stop_x = chair_rect().get_center().x
	add_child(ride)
	_fx = Control.new()
	_fx.name = "Fx"
	_fx.size = size
	_fx.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_fx.draw.connect(_draw_fx)
	add_child(_fx)
	if _skip:
		add_child(_skip)
	_dispute_btn = GameButton.make(Rect2(UI.W - 340, 10, 176, 34), "Я НЕ СОГЛАСЕН", UI.PURPLE)
	_dispute_btn.name = "Dispute"
	_dispute_btn.visible = false
	_dispute_btn.pressed.connect(open_dispute)
	add_child(_dispute_btn)
	Chrome.add(self, true, true, false)


func _part_row(i: int, pid: String) -> GameButton:
	var b := GameButton.make(part_rect(i), "", UI.AMBER)
	b.name = "Part_" + pid
	b.plain = true
	b.set_meta("pid", pid)
	b.set_meta("i", i)
	b.on_draw = _draw_part_row
	b.pressed.connect(_part_row_pressed.bind(b))
	add_child(b)
	_part_btns.append(b)
	return b


func _build_diagnose() -> void:
	var parts: Array = job["parts"]
	for i in parts.size():
		_part_row(i, parts[i])
	var rects := diag_rects()
	_dsize = 11
	for s: int in [14, 13, 12, 11]:
		_dsize = s
		var ok := true
		for i in rects.size():
			var n := UI.wrap_lines(Loc.t(job["diagnosis"][i]["text"]), rects[i].size.x - 24, s).size()
			if n * (UI.line_height(s) + 2) > rects[i].size.y - 12:
				ok = false
				break
		if ok:
			break
	for i in rects.size():
		var b := GameButton.make(rects[i], "", UI.CYAN)
		b.name = "Diag_%d" % i
		b.set_meta("i", i)
		b.on_draw = _draw_diag
		b.pressed.connect(choose_diagnosis.bind(i))
		add_child(b)
		_diag_btns.append(b)
	_update_a11y()


func _build_repair() -> void:
	tools = ToolPanel.new()
	tools.job_screen = self
	tools.tool_pressed.connect(select_tool)
	add_child(tools)
	var parts: Array = job["parts"]
	for i in parts.size():
		_part_row(i, parts[i])
	_prev_btn = GameButton.make(PREV_RECT, "◂", UI.CYAN)
	_prev_btn.name = "StepBack"
	_prev_btn.label_size = 17
	_prev_btn.pressed.connect(step_back)
	add_child(_prev_btn)
	var sk := GameButton.make(SKIP_RECT, "ШАГ ▸", UI.AMBER)
	sk.name = "StepSkip"
	sk.pressed.connect(step_skip)
	add_child(sk)
	_update_a11y()


func _build_test() -> void:
	_test_btn = GameButton.make(TEST_BTN, "ГОТОВО ▸" if ride_done else "ПРОКАТИТЬ И ПРОВЕРИТЬ", UI.GOOD)
	_test_btn.name = "TestDrive"
	_test_btn.pressed.connect(_test_pressed)
	add_child(_test_btn)


## Подписи пунктов для озвучки фокуса — как a11y_items в game.py: группа (Детали, Диагноз, Инструменты, Шаги) и текст.
func _update_a11y() -> void:
	var unlocked := inspected.size() >= inspect_req
	for b in _part_btns:
		var pid: String = b.get_meta("pid")
		var nm := Loc.t(Content.part_name(pid))
		if phase == "diagnose" and inspected.has(pid):
			nm += ", " + Loc.t("осмотрено")
		b.accessibility_name = nm
		b.set_meta("a11y_group", "Детали")
	for b in _diag_btns:
		var i := int(b.get_meta("i"))
		b.enabled = unlocked
		b.color = UI.CYAN if unlocked else UI.DIM
		b.accessibility_name = "%s %d: %s" % [Loc.t("Диагноз"), i + 1, Loc.t(job["diagnosis"][i]["text"])] + \
			("" if unlocked else ", " + Loc.t("сначала осмотри детали"))
		b.set_meta("a11y_group", "Диагноз")
	if _prev_btn:
		_prev_btn.enabled = step_idx > 0
		_prev_btn.accessibility_name = Loc.t("Вернуться на шаг назад")
		_prev_btn.set_meta("a11y_group", "Шаги")
	var sk := get_node_or_null("StepSkip") as Control
	if sk:
		sk.accessibility_name = Loc.t("Пропустить шаг (минус звезда)")
		sk.set_meta("a11y_group", "Шаги")
	if tools:
		tools.update_a11y(sel_tool)
	if chair:
		for pid: String in job["parts"]:
			var hb := chair.spot_button(pid)
			if hb:
				hb.update_a11y()


func rebuild() -> void:
	if chair:
		_m3d_state = {"yaw": chair.view_yaw(), "zoom_k": chair.zoom_k}
	if portrait:
		_portrait_state = [portrait.t, portrait.auto]
	var keep: Array[Control] = []                            # окна мини-игры и сносок переживают пересборку
	for w: Control in [mini, notes]:
		if w and w.get_parent() == self:
			remove_child(w)
			keep.append(w)
	super.rebuild()
	for w in keep:
		add_child(w)
	if not keep.is_empty():
		UI.set_focus_enabled(self, false)
		for w in keep:
			UI.set_focus_enabled(w, true)
			UI.focus_later((w as Variant).first_focus())


# ---------------- диагностика ----------------

func _part_row_pressed(b: GameButton) -> void:
	var pid: String = b.get_meta("pid")
	if phase == "repair" and not UI.kb_active and b.get_local_mouse_position().x >= b.size.x - 30 \
			and _part_note(pid).size() > 0:          # книжка: закрепить сноску (отзыв 93)
		note_pin = "" if note_pin == pid else pid
		Audio.sfx("tick")
		return
	part_clicked(pid)


## Клик по детали (кружок, строка списка): осмотр в диагнозе, инструмент — в ремонте.
func part_clicked(pid: String) -> void:
	if phase == "diagnose":
		inspect_part(pid)
	elif phase == "repair":
		if sel_tool == "":
			Nav.flash("Сначала выбери инструмент внизу.", UI.AMBER, 2.5)
		else:
			do_action(sel_tool, pid)


func inspect_part(pid: String) -> void:
	if phase != "diagnose":
		return
	if pid in job["parts"]:
		inspected[pid] = true
	Audio.sfx("inspect")
	Nav.flash(job["inspect"].get(pid, "Тут вроде всё в порядке."), UI.CYAN, 4.0, true)
	_update_a11y()


func choose_diagnosis(idx: int) -> bool:
	if inspected.size() < inspect_req:
		Nav.flash(Loc.fmt("Диагноз ставят по уликам: осмотри детали справа ({0}/{1}).", [inspected.size(), inspect_req]),
			UI.AMBER, 3.0)
		return false
	var opt: Dictionary = job["diagnosis"][idx]
	if opt.get("correct", false):
		phase = "repair"
		step_idx = 0
		sel_tool = ""
		last_note = ""
		Audio.sfx("ok")
		Nav.flash("Диагноз верный! Приступаем к ремонту.", UI.GOOD, 3.0)
		_set_step_ghost()
		client_queue.clear()
		talk_later = [t + 1.8, "client", "good"]
		rebuild()
		return true
	mistakes += 1
	Audio.sfx("bad")
	var fb: String = opt.get("feedback", "")
	var right_text := ""
	for o: Dictionary in job["diagnosis"]:
		if o.get("correct", false):
			right_text = o["text"]
	note_dispute("diagnosis", right_text, opt["text"], fb)
	Nav.flash(fb if fb != "" else "Не похоже. Осмотри ещё раз.", UI.BAD, 4.0)
	react_mistake()
	return false


# ---------------- ремонт ----------------

func _set_step_ghost() -> void:
	if step_idx < steps().size():
		ghost_line = cur_step().get("ghost", "")


func select_tool(tid: String) -> void:
	sel_tool = tid
	Audio.sfx(Content.consts.get("tool_sound", {}).get(tid, "tool_metal"))
	Speech.say(Loc.tf("В руке: {0}", [Loc.t(Content.tools[tid]["name"])]), true)
	if tools:
		tools.update_a11y(sel_tool)


## Применить (инструмент, деталь) к текущему шагу: "ok" | "mini" | "wrong".
func do_action(tid: String, pid: String) -> String:
	if phase != "repair":
		return "wrong"
	var st_: Dictionary = cur_step()
	var tool_ok: bool = tid == st_["tool"] or tid in st_.get("alt_tools", [])
	var part_ok: bool = pid == st_["part"] or pid in st_.get("alt", [])
	if tool_ok and part_ok:
		log_actions.append([tid, pid, "mini" if st_.get("mini") else "ok"])
		if st_.get("mini") is Dictionary:
			start_mini(st_)
			return "mini"
		complete_base_step(st_)
		return "ok"
	log_actions.append([tid, pid, "wrong"])
	mistakes += 1
	Audio.sfx("bad")
	note_dispute("repair", "%s → %s" % [Content.tools[st_["tool"]]["name"], Content.part_name(st_["part"])],
		"%s → %s" % [Content.tools.get(tid, {"name": tid})["name"], Content.part_name(pid)], st_.get("wrongmsg", ""))
	action.start(tid, false, act_pos(pid), pid)
	var msg: String = st_.get("wrongmsg", "")
	if msg == "":
		if tid != st_["tool"] and pid == st_["part"]:
			msg = Loc.fmt("Деталь верная, но инструмент не тот. Нужен: {0}.", [Content.tools[st_["tool"]]["name"]])
		elif tid == st_["tool"] and pid != st_["part"]:
			msg = Loc.fmt("Инструмент верный, но не та деталь. Цель: {0}.", [Content.part_name(st_["part"])])
		else:
			msg = "Не то. Перечитай шаг и подсказку."
	dispute["msg"] = msg
	Nav.flash(msg, UI.BAD, 4.0, true)
	react_mistake()
	return "wrong"


## Экранная точка детали: кружок на коляске, иначе строка списка.
func act_pos(pid: String) -> Vector2:
	if chair and chair.visible:
		var s := chair.spot_of(pid)
		if not s.is_empty():
			return Vector2(s[1], s[2])
	var i: int = job["parts"].find(pid)
	if i >= 0:
		var r := part_rect(i)
		return Vector2(r.position.x - 30, r.get_center().y)
	return Vector2(UI.W / 2.0, 300)


func complete_base_step(st_: Dictionary) -> void:
	action.start(st_["tool"], true, act_pos(st_["part"]))
	last_note = st_.get("note", "")
	Audio.sfx("ok")
	Nav.flash("Шаг выполнен. " + last_note, UI.GOOD, 4.0, true)
	_ok_t = t
	_ok_pos = get_local_mouse_position()
	step_idx += 1
	sel_tool = ""
	if step_idx >= steps().size():
		phase = "test"
		ghost_line = "Бартоломью: «Кажется, всё. Прокатим — проверим!»"
		talk_later = [t + 1.5, "client", "test"]
		rebuild()
	else:
		_set_step_ghost()
		react_good()
		_update_a11y()


## Ошибка игрока (мини-игры): сообщение, счётчик, реакция.
func miss(msg: String, secs: float = 4.0) -> void:
	mistakes += 1
	Audio.sfx("bad")
	Nav.flash(msg, UI.BAD, secs, true)
	if dispute.is_empty() or dispute["t"] != t:
		note_dispute("mistake", "", "", msg)
	react_mistake()


## «◂»: прошлый шаг снова текущий (ошибки не списываются).
func step_back() -> void:
	Audio.sfx("tick")
	if phase != "repair":
		return
	if step_idx <= 0:
		Nav.flash("Это первый шаг.", UI.GHOST, 2.5)
		return
	step_idx -= 1
	close_mini()
	sel_tool = ""
	last_note = steps()[step_idx - 1].get("note", "") if step_idx > 0 else ""
	_set_step_ghost()
	var prev := cur_step()
	var msg := "%s: %s (%s → %s)" % [Loc.t("Шаг назад"), Loc.t(prev["instr"]), Loc.t(Content.tools[prev["tool"]]["name"]),
		Loc.t(Content.part_name(prev["part"]))]
	if prev.get("note", "") != "":
		msg += " ✔ " + Loc.t(prev["note"])
	Nav.flash(msg, UI.CYAN, 7.0, true)
	_update_a11y()


## «ШАГ ▸»: игра сама делает шаг и показывает правильный ход; пропуск = две ошибки.
func step_skip() -> void:
	if phase != "repair":
		return
	var st_ := cur_step()
	close_mini()
	mistakes += 2
	log_actions.append([st_["tool"], st_["part"], "skip"])
	complete_base_step(st_)
	var msg := "%s: %s → %s." % [Loc.t("Шаг пропущен — правильно"), Loc.t(Content.tools[st_["tool"]]["name"]),
		Loc.t(Content.part_name(st_["part"]))]
	if st_.get("note", "") != "":
		msg += " " + Loc.t(st_["note"])
	Nav.flash(msg, UI.AMBER, 6.0, true)


func react_good() -> void:
	if Settings.quiet_talk():
		return
	var r := randf()
	if r < 0.3:
		talk_later = [t + 1.8, "client", "good"]
	elif r < 0.42:
		talk_later = [t + 1.8, "barty", "good"]


# ---------------- замечания: «Я НЕ СОГЛАСЕН» ----------------

## Запомнить засчитанную ошибку — игрок может оспорить её 25 с (note_dispute).
func note_dispute(kind: String, expected: String, got: String, msg: String) -> void:
	var step := ""
	if phase == "repair" and step_idx < steps().size():
		step = cur_step()["instr"]
	dispute = {"kind": kind, "job": job["id"], "title": job.get("title", ""), "phase": phase,
		"variant": job.get("_variant"), "step": step, "expected": expected, "got": got, "msg": msg, "t": t,
		"sent": false, "scene": "job"}


func dispute_visible() -> bool:
	return not dispute.is_empty() and not dispute["sent"] and t - float(dispute["t"]) < 25.0 and Nav.feedback == null 		and not (ride != null and ride.riding())


func open_dispute() -> void:
	var d := dispute
	Nav.open_feedback(d, func(sent: bool, online: bool) -> void:
		if not sent:
			return
		d["sent"] = true
		var refunded := false
		if mistakes > 0:                       # спорная ошибка не засчитывается
			mistakes -= 1
			refunded = true
		Nav.flash(("Спасибо! Замечание отправляется разработчикам." if online else
			"Спасибо! Замечание сохранено — его проверят и поправят игру.")
			+ (" Эта ошибка не засчитана." if refunded else ""), UI.GOOD, 5.0))


func feedback_context() -> Dictionary:
	var step := ""
	if phase == "repair" and step_idx < steps().size():
		step = cur_step()["instr"]
	return {"kind": "general", "job": job["id"], "title": job.get("title", ""), "phase": phase, "step": step,
		"expected": "", "got": "", "msg": "", "scene": "job"}


# ---------------- обучение (первое задание) ----------------

## Шаг, чей инструмент и деталь подсвечиваются (flat, пока не пройдено), или {}.
func tutor_step() -> Dictionary:
	if job.get("id") != "flat" or SaveGame.is_done("flat") or phase != "repair" or mini != null:
		return {}
	return cur_step()


## ["tool", [инструменты]] пока нужный не в руке, потом ["part", [детали]]; [] — подсветки нет.
func tutor_want() -> Array:
	var st_ := tutor_step()
	if st_.is_empty():
		return []
	var ts: Array = [st_["tool"]] + st_.get("alt_tools", [])
	if not sel_tool in ts:
		return ["tool", ts]
	return ["part", [st_["part"]] + st_.get("alt", [])]


# ---------------- сноски мануала ----------------

func _part_note(pid: String) -> Dictionary:
	return Content.manual_notes.get(job["id"], {}).get(pid, {})


## Деталь со сноской: закреплённая книжкой, в фокусе клавиатуры, под мышью (строка или кружок); "" — нет.
func note_part_at() -> String:
	if phase != "repair" or mini != null:
		return ""
	if note_pin != "" and _part_note(note_pin).size() > 0:
		return note_pin
	var f := get_viewport().gui_get_focus_owner()
	if UI.kb_active and f != null and f.has_meta("pid"):
		return f.get_meta("pid") if _part_note(f.get_meta("pid")).size() > 0 else ""
	if UI.kb_active and f is HotspotButton:
		return (f as HotspotButton).pid if _part_note((f as HotspotButton).pid).size() > 0 else ""
	for b in _part_btns:
		if b.is_hovered():
			return b.get_meta("pid") if _part_note(b.get_meta("pid")).size() > 0 else ""
	if chair:
		for pid: String in job["parts"]:
			var hb := chair.spot_button(pid)
			if hb and hb.is_hovered():
				return pid if _part_note(pid).size() > 0 else ""
	return ""


func open_notes() -> void:
	Audio.sfx("tick")
	if notes:
		return
	notes = NotesDialog.make(job)
	notes.closed.connect(close_notes)
	UI.set_focus_enabled(self, false)
	add_child(notes)


func close_notes() -> void:
	if notes:
		notes.queue_free()
		notes = null
		UI.set_focus_enabled(self, true)
		_focus_default()


# ---------------- мини-игры ----------------

func start_mini(st_: Dictionary) -> void:
	close_mini()
	mini = MiniGame.make(st_)
	mini.solved.connect(_mini_solved)
	mini.missed.connect(func(msg: String, secs: float) -> void: miss(msg, secs))
	mini.closed.connect(close_mini)
	UI.set_focus_enabled(self, false)
	add_child(mini)


func close_mini() -> void:
	if mini:
		mini.queue_free()
		mini = null
		UI.set_focus_enabled(self, true)
		_focus_default()


func _mini_solved() -> void:
	var st_: Dictionary = mini.step
	close_mini()
	complete_base_step(st_)


# ---------------- тест-драйв ----------------

func _test_pressed() -> void:
	if ride.riding():
		return
	if ride_done:
		finish_test()
	else:
		start_ride()


func start_ride() -> void:
	ride.start(ride.t)
	if Settings.calm():                          # без анимации — проверка сразу, без проезда
		ride.t0 = ride.t - ride.secs()
	Audio.sfx("whoosh")
	chair.visible = false
	portrait.paused = true
	_test_btn.visible = false


func _ride_finished() -> void:
	ride.active = false
	ride_done = true
	portrait.paused = false
	ghost_line = "Бартоломью: «Едет как надо! Дочитаешь — жми ГОТОВО.»"
	_test_btn.visible = true
	_test_btn.set_label("ГОТОВО ▸")
	UI.focus_later(_test_btn)


@warning_ignore("integer_division")
func finish_test() -> void:
	Audio.sfx("fanfare")
	var stars := maxi(1, 3 - mistakes / 2)
	var jid: String = job["id"]
	if SaveGame.assign_on():                   # задание по ссылке: свой прогресс, обычный (done, гараж) не трогаем
		SaveGame.assign_record(jid, mistakes, int(t))
	else:
		SaveGame.done[jid] = true
		var found := false
		for g: Array in SaveGame.garage:
			if g[0] == jid:
				found = true
				if stars > int(g[1]):          # переигрывание: в гараже — лучшая оценка
					g[1] = stars
		if not found:
			SaveGame.garage.append([jid, stars])
	var gag := ""
	if randf() < 0.5:                          # то нога отвалится, то Мартин сам себя похвалит/подколет
		var legs: Array = Content.talk.get("leg_gags", []).filter(func(g: String) -> bool:
			return Settings.barty_on() or not g.begins_with("Бартоломью"))
		gag = legs.pick_random() if not legs.is_empty() else ""
	else:
		var pool: Array = Content.talk.get("martin", {}).get("good" if mistakes == 0 else "mistake", [])
		gag = pool.pick_random() if not pool.is_empty() else ""
	SaveGame.save()
	Nav.go("result", {"job": job, "stars": stars, "gag": gag, "mistakes": mistakes})


func zoom(steps_: int) -> void:
	Audio.sfx("tick")
	if not chair.zoom(steps_):
		Nav.flash("Крупнее нельзя." if steps_ > 0 else "Мельче нельзя.", UI.GHOST, 1.5)


func skip_tutorial() -> void:
	SaveGame.tutorial_skipped = true
	SaveGame.save()
	Audio.sfx("whoosh")
	Nav.go("hub")
	Nav.flash("Обучение пропущено: все клиенты уже ждут. Коляску Мартина можно починить в любой момент.", UI.GOOD, 5.0)


func go_back() -> void:
	if notes:
		close_notes()
		return
	if mini:
		close_mini()
		return
	if esc_t > 0.0:
		esc_t = 0.0
		Nav.go("hub")
		return
	esc_t = 2.5
	Nav.flash("Ещё раз Esc — покинуть ремонт (прогресс задания сбросится).", UI.AMBER, esc_t)


func handle_key(e: InputEventKey) -> bool:
	if mini or notes:
		return false
	if e.keycode in [KEY_PLUS, KEY_EQUAL, KEY_KP_ADD] and chair and chair.has_frames() and phase != "test":
		zoom(1)
		return true
	if e.keycode in [KEY_MINUS, KEY_KP_SUBTRACT] and chair and chair.has_frames() and phase != "test":
		zoom(-1)
		return true
	if (e.keycode == KEY_LEFT or e.keycode == KEY_RIGHT) and chair and get_viewport().gui_get_focus_owner() == null:
		chair.rotate_step(-1 if e.keycode == KEY_LEFT else 1)
		return true
	return false


# ---------------- живые реплики (talk_tick) ----------------

func _pick_line(key: String, lines: Array) -> String:
	if lines.is_empty():
		return ""
	var used: Array = talk_used.get(key, [])
	var left: Array = lines.filter(func(l: String) -> bool: return not l in used)
	if left.is_empty():
		used.clear()
		left = lines.duplicate()
	var line: String = left.pick_random()
	used.append(line)
	talk_used[key] = used
	return line


func _show_client(line: String) -> void:
	if line == "":
		return
	client_next = t + randf_range(CLIENT_IDLE[0], CLIENT_IDLE[1])
	last_talk_t = t
	if not Settings.barty_on() and (line.begins_with("Барти") or line.begins_with("Бартоломью")):
		return
	if line.begins_with("Барти") or line.begins_with("Бартоломью") or line.begins_with("Бренна"):
		ghost_quip = line                      # наставник — в пузыре наставника
		ghost_quip_until = t + maxf(7.0, 3.0 + line.length() / 12.0)
		return
	client_line = line
	client_t = t
	Audio.sfx("pop")


func client_say(kind: String) -> void:
	_show_client(_pick_line("c:" + kind, Content.client_talk(job["id"]).get(kind, [])))


func barty_quip(kind: String, secs: float = 6.5) -> void:
	if not Settings.barty_on() or Settings.quiet_talk():
		return
	var line := _pick_line("b:" + kind, Content.talk.get("barty", {}).get(kind, []))
	if line != "":
		ghost_quip = line
		ghost_quip_until = t + maxf(secs, 3.0 + line.length() / 12.0)
		last_talk_t = t


func react_mistake() -> void:
	if Settings.quiet_talk():
		return
	client_queue.clear()
	if phase == "diagnose" and randf() < 0.4:
		talk_later = [t + 1.2, "barty", "mistake"]
	elif randf() < 0.75:
		talk_later = [t + 1.2, "client", "mistake"]


func ghost_text() -> String:
	return ghost_quip if ghost_quip != "" and t < ghost_quip_until else ghost_line


func _talk_tick() -> void:
	if (ride and ride.riding()) or mini != null or notes != null:
		return
	var toast := Nav.toast
	var toast_fresh := toast.active() and (not toast.sticky or toast.t - toast.t0 < 3.0)
	var quiet := t - last_talk_t < TALK_GAP or toast_fresh
	if Settings.quiet_talk():                  # одна фраза при входе — и всё
		talk_later = []
		if not client_queue.is_empty() and t >= client_next and not quiet:
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
		if later[1] == "barty":
			barty_quip(later[2], 5.0)
		else:
			client_say(later[2])
		return
	if phase == "test":                        # перед проверкой — только отложенная реплика
		return
	if t >= client_next and not quiet:
		if not client_queue.is_empty():
			_show_client(client_queue.pop_front())
			client_next = t + 10.0
		else:
			talk_n += 1
			client_next = t + randf_range(CLIENT_IDLE[0], CLIENT_IDLE[1])
			client_say("learn" if talk_n % 2 == 0 else "worry")
	if phase == "diagnose" and t >= quip_next and client_queue.is_empty() and not quiet:
		if quip_next > 0:
			barty_quip("leg" if randf() < 0.3 else "idle", 8.0)
		quip_next = t + randf_range(QUIP_IDLE[0], QUIP_IDLE[1])


# ---------------- кадр ----------------

func tick(dt: float) -> void:
	if esc_t > 0.0:
		esc_t -= dt
	_talk_tick()
	var riding := ride.riding()
	if ride.active and not riding:
		_ride_finished()
	if (phase == "test" or Frames.net) and not ride_done and not riding:
		var hero := RideView.hero_loop(job["client_art"])
		if hero != "" and not Settings.calm():
			Frames.want_loop(hero)             # пока читают «Тест-драйв» — подгрузить кадры проезда (браузер — с
			                                   # начала задания, после кадров поворота: качаются по сети, как AnimWeb)
	var dv := dispute_visible()               # «Я НЕ СОГЛАСЕН» — в шапке на месте «КОЛЁСА И КОСТИ»
	_dispute_btn.visible = dv
	if _skip:
		_skip.visible = not dv
	_bar.brand = not dv and _skip == null
	_bar.right_edge = (UI.W - 340 - 12.0) if dv else (_skip.position.x - 12 if _skip else UI.W - 170.0)
	_bar.queue_redraw()
	_client_bubble.visible = not riding
	_mentor.visible = not riding
	action.visible = not riding
	if _mentor.say(ghost_text()) and _mentor.shown():
		Audio.sfx("ghost")
	if _client_bubble.line != client_line:
		_client_bubble.say(client_line)
	var i := 0
	for b in _part_btns:
		b.slide = Vector2(int(160 * (1 - UI.appear(st, 0.05 * i, 0.35))), 0)
		i += 1
	_deco.queue_redraw()
	_fx.queue_redraw()


func _draw_deco() -> void:
	UI.draw_text(_deco, Loc.t(job["client"]), Vector2(24, 266), 16, UI.WHITE, true)
	match phase:
		"diagnose":
			var cr := chair_rect()
			UI.draw_text(_deco, Loc.t("ДИАГНОСТИКА"), Vector2(360, 70), 20, UI.CYAN, true)
			UI.draw_wrapped(_deco, Loc.t(job["symptom"]), Vector2(360, 100), 560, 17, UI.WHITE)
			var unlocked := inspected.size() >= inspect_req
			var tip := Loc.t("Улики собраны — выбери диагноз:") if unlocked else Loc.tf(
				"Осмотри детали (клик по коляске или списку): {0}/{1}", [inspected.size(), inspect_req])
			UI.draw_text(_deco, tip, Vector2(360, cr.end.y + 4), 15, UI.GREY if unlocked else UI.AMBER, not unlocked)
			UI.draw_text(_deco, Loc.t("ДИАГНОЗ"), Vector2(980, right_col_top() + 6), 16, UI.CYAN if unlocked else UI.DIM, true)
			UI.draw_text(_deco, Loc.t("ОСМОТРЕТЬ"), Vector2(980, 70), 16, UI.AMBER, true)
		"repair":
			var n := steps().size()
			var hdr := UI.draw_text(_deco, Loc.tf("РЕМОНТ — шаг {0}/{1}", [mini_safe_idx() + 1, n]), Vector2(360, 70), 20,
				UI.AMBER, true)
			_draw_step_dots(n, Vector2(hdr.end.x + 22, hdr.get_center().y), PREV_RECT.position.x - 18)
			UI.draw_wrapped(_deco, Loc.t(cur_step().get("instr", "")), Vector2(360, 100), 560, 19, UI.WHITE)
			UI.draw_text(_deco, Loc.t("ДЕТАЛЬ"), Vector2(980, 70), 16, UI.AMBER, true)
		"test":
			UI.draw_text(_deco, Loc.t("ТЕСТ-ДРАЙВ"), Vector2(360, 70), 20, UI.GOOD, true)
			UI.draw_wrapped(_deco, Loc.t(job.get("test", "")), Vector2(360, 100), 560, 19, UI.WHITE)
			if ride_done:                       # клиент в починенной коляске
				var tex := Content.texture(job["client_art"])
				if tex:
					var cr := chair_rect()
					_deco.draw_texture_rect(tex, UI.fit_rect(tex.get_size(), Rect2(cr.get_center() - Vector2(115, 125),
						Vector2(230, 250))), false)
				var lbl := Loc.t("✔ Проверка пройдена")
				var w := UI.text_width(lbl, 17, true)
				var c := Vector2(TEST_BTN.get_center().x, TEST_BTN.position.y - 22)
				UI.draw_round_rect(_deco, Rect2(c - Vector2(w / 2 + 8, UI.line_height(17, true) / 2 + 4),
					Vector2(w + 16, UI.line_height(17, true) + 8)), Color8(14, 12, 20, 175), Color(), 0, 8)
				UI.draw_text(_deco, lbl, c, 17, UI.GOOD, true, 1)


func mini_safe_idx() -> int:
	return mini_idx_clamp(step_idx)


func mini_idx_clamp(i: int) -> int:
	return clampi(i, 0, maxi(0, steps().size() - 1))


func _draw_step_dots(n: int, at: Vector2, right: float) -> void:
	var step := 22.0
	if at.x + (n - 1) * 22 > right:
		step = maxf(6.0, (right - at.x - 8) / maxf(1, n - 1))
	var r := 7.0 if step >= 22 else maxf(3, int(step / 3))
	UI.draw_round_rect(_deco, Rect2(at.x - r - 7, at.y - r - 6, roundf((n - 1) * step) + 2 * r + 14, 2 * r + 12),
		Color8(14, 12, 20, 190), Color(), 0, int(r + 6))
	for i in n:
		var c := Vector2(roundf(at.x + i * step), at.y)
		var col := UI.GOOD if i < step_idx else (UI.AMBER if i == step_idx else UI.DIM)
		_deco.draw_circle(c, r, col, true, -1, true)
		if i > step_idx:
			UI.draw_ring(_deco, c, r, Color8(150, 150, 170), 1)
		if i == step_idx:
			UI.draw_ring(_deco, c, r + 3, UI.AMBER, 2)


## Поверх всего: зелёный кружок обучения у нужной детали, инструмент в руке у курсора, вспышка верного шага.
func _draw_fx() -> void:
	if phase == "repair" and chair and chair.visible:
		var want := tutor_want()
		if not want.is_empty() and want[0] == "part":
			var s := chair.spot_of(tutor_step()["part"])
			if not s.is_empty():
				TutorRing.draw_circle_ring(_fx, Vector2(s[1], s[2]), s[3], t)
	var m := get_local_mouse_position()
	if t - _ok_t < 0.7 and not Settings.calm():     # верный шаг — вспышка искр у курсора
		var ph := (t - _ok_t) / 0.7
		for i in 12:
			var a := i * TAU / 12 + 0.3
			_fx.draw_circle(_ok_pos + Vector2(cos(a), sin(a)) * 60 * UI.ease_out(ph), 4 * (1 - ph), Color(UI.GOOD, 1 - ph))
	if sel_tool == "" or phase != "repair" or mini != null or notes != null or UI.kb_active:
		return
	for b: GameButton in tools.tiles.values():
		if b.is_hovered():
			return
	var tex := Content.texture("tool_%s.png" % sel_tool)
	if tex:
		_fx.draw_set_transform(m + Vector2(22, 20), deg_to_rad(12 - 4 * UI.wsin(t * 4)))
		_fx.draw_texture_rect(tex, UI.fit_rect(tex.get_size(), Rect2(-17, -17, 34, 34)), false)
		_fx.draw_set_transform(Vector2.ZERO)


func _draw_part_row(b: GameButton, _r: Rect2) -> void:
	var pid: String = b.get_meta("pid")
	var i: int = b.get_meta("i")
	var hov := b.is_hovered()
	var r := Rect2(b.slide, b.size)
	var want := tutor_want()
	var tut: bool = not want.is_empty() and want[0] == "part" and pid == tutor_step()["part"]
	UI.draw_round_rect(b, r, UI.PANEL2 if hov else UI.PANEL, UI.GOOD if tut else (UI.AMBER if hov else UI.DIM),
		3 if tut else 2, 6)
	var nc := r.position + Vector2(17, r.size.y / 2.0)
	b.draw_circle(nc, 11, UI.INK, true, -1, true)
	UI.draw_ring(b, nc, 11, UI.GOOD if (phase == "diagnose" and inspected.has(pid)) else UI.AMBER, 2)
	UI.draw_text(b, str(i + 1), nc, 13, UI.WHITE, true, 1)
	var f: Array = UI.fit_text(Loc.t(Content.part_name(pid)), r.size.x - 56, 16)
	var fh := floorf(UI.line_height(16) / 2.0)
	UI.draw_text(b, f[0], Vector2(r.position.x + 34, nc.y - fh + floorf((16 - int(f[1])) / 2.0)), f[1], UI.WHITE)
	if phase == "diagnose" and inspected.has(pid):
		UI.draw_text(b, "✔", Vector2(r.end.x - 10, nc.y - 9), 15, UI.GOOD, false, 2)
	elif phase == "repair" and _part_note(pid).size() > 0:
		BookIcon.draw_icon(b, Vector2(r.end.x - 16, nc.y), 9, UI.CYAN if hov or note_pin == pid else UI.GHOST)


func _draw_diag(b: GameButton, r: Rect2) -> void:
	var i: int = b.get_meta("i")
	var unlocked := inspected.size() >= inspect_req
	UI.draw_wrapped(b, Loc.t(job["diagnosis"][i]["text"]), r.position + Vector2(12, 6), r.size.x - 24, _dsize,
		UI.WHITE if unlocked else UI.GREY)
