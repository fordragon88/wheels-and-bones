extends Screen
## Экран задания (draw_job/click_job из game.py) для ЛЮБОГО задания из данных. Фазы: diagnose (сделано),
## repair/test/result — следующие шаги переноса (сейчас вместо ремонта — заглушка с кнопкой «в мастерскую»).
## Диагностика: шапка (название, модель коляски), портрет клиента с именем и пузырём реплики, симптом, коляска на
## кадрах поворота с кружками деталей, «ОСМОТРЕТЬ» справа, «ДИАГНОЗ» (открывается после INSPECT_REQ осмотров),
## пузырь Барти внизу, улики и ошибки — сообщением сверху (как flash в game.py).
## Параметры: {"job": id, "variant": индекс варианта поломки или −1 — случайный}.

const CHAIR_CX := 575.0                  # центр зоны коляски: между портретом и правой колонкой
const QUIP_IDLE := [35.0, 50.0]          # пауза между шутками Барти на диагностике
const CLIENT_IDLE := [22.0, 32.0]        # пауза между репликами клиента
const TALK_GAP := 5.0                    # между репликами персонажей — не меньше

var job: Dictionary = {}
var phase: String = "diagnose"
var inspected: Dictionary = {}
var mistakes: int = 0
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

var chair: ChairView
var _deco: Control
var _top: Control
var _part_btns: Array[GameButton] = []
var _diag_btns: Array[GameButton] = []
var _client_bubble: SpeechBubble
var _mentor: SpeechBubble
var _skip: GameButton
var _zin: GameButton
var _zout: GameButton
var _dsize: int = 14
var _m3d_state: Dictionary = {}          # ракурс коляски переживает пересборку экрана


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
	return Loc.t(job.get("title", "")) + ". " + Loc.t(job.get("symptom", ""))


func toast_bounds() -> Vector2:
	if _skip != null:
		return Vector2(54, UI.W - _skip.position.x + 6)
	return Vector2(54, 164)


func first_focus() -> Control:
	if phase == "diagnose" and not _part_btns.is_empty():
		return _part_btns[0]
	var b := get_node_or_null("ToHub")
	return b as Control


## Первое задание (Мартин), пока обучение не пройдено: в шапке — «Пропустить обучение».
func tutorial_skip_shown() -> bool:
	return job.get("id") == "flat" and not SaveGame.tutorial_ok()


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
	add_child(BgLayer.make("bg_workshop.png"))
	var bar := TopBar.make(job["title"], job.get("chair_name", ""))
	if tutorial_skip_shown():
		_skip = GameButton.make(Rect2(UI.W - 390, 9, 210, 36), "ПРОПУСТИТЬ ОБУЧЕНИЕ ▸", UI.CYAN)
		_skip.name = "SkipTutorial"
		_skip.pressed.connect(skip_tutorial)
		bar.brand = false
		bar.right_edge = _skip.position.x - 12
	add_child(bar)
	var face := Figure.make(job["client_art"], Vector2(24, 70), Vector2(150, 190), "breathe")
	face.name = "Client"
	add_child(face)
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
	_mentor.say(ghost_text())
	add_child(_mentor)
	chair = ChairView.new()
	chair.show_spots = phase == "diagnose"
	chair.setup(job["chair_art"], job["parts"], chair_rect(), inspected)
	if not _m3d_state.is_empty():
		chair.yaw = _m3d_state["yaw"]
		chair.zoom_k = _m3d_state["zoom_k"]
		chair.t0 = -1e9
	chair.part_pressed.connect(part_clicked)
	add_child(chair)
	var cr := chair_rect()
	if chair.has_frames():
		_zin = GameButton.make(Rect2(cr.end.x - 44, cr.position.y + 4, 40, 36), "+", UI.CYAN)
		_zin.name = "ZoomIn"
		_zin.accessibility_name = Loc.t("Крупнее")
		_zin.pressed.connect(zoom.bind(1))
		add_child(_zin)
		_zout = GameButton.make(Rect2(cr.end.x - 44, cr.position.y + 44, 40, 36), "−", UI.CYAN)
		_zout.name = "ZoomOut"
		_zout.accessibility_name = Loc.t("Мельче")
		_zout.pressed.connect(zoom.bind(-1))
		add_child(_zout)
	if phase == "diagnose":
		_build_diagnose()
	else:
		_build_repair_stub()
	if not Content.job_notes(job).is_empty() and phase in ["diagnose", "repair"]:
		var nb := GameButton.make(Rect2(UI.W - 24 - 180, UI.H - 44, 180, 34), "СНОСКИ МАНУАЛА", UI.PURPLE)
		nb.name = "Notes"
		nb.pressed.connect(func() -> void:
			Audio.sfx("tick")
			Nav.flash("Сноски мануала появятся в следующих шагах переноса.", UI.PURPLE, 3.0))
		add_child(nb)
	if _skip:
		add_child(_skip)
	Chrome.add(self, true, true, false)


func _build_diagnose() -> void:
	var parts: Array = job["parts"]
	for i in parts.size():
		var pid: String = parts[i]
		var b := GameButton.make(part_rect(i), "", UI.AMBER)
		b.name = "Part_" + pid
		b.plain = true
		b.set_meta("pid", pid)
		b.set_meta("i", i)
		b.on_draw = _draw_part_row
		b.pressed.connect(part_clicked.bind(pid))
		add_child(b)
		_part_btns.append(b)
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


func _build_repair_stub() -> void:
	var p := PanelBox.make(Rect2(330, 220, 620, 190), "Ремонт — следующий шаг переноса",
		"Диагноз поставлен верно. Шаги ремонта, мини-игры и тест-драйв появятся в следующих шагах переноса.")
	p.name = "RepairStub"
	add_child(p)
	var b := GameButton.make(Rect2(330 + 310 - 120, 220 + 190 - 62, 240, 44), "В МАСТЕРСКУЮ", UI.AMBER)
	b.name = "ToHub"
	b.pressed.connect(func() -> void:
		Audio.sfx("tick")
		Nav.go("hub"))
	add_child(b)


func _update_a11y() -> void:
	var unlocked := inspected.size() >= inspect_req
	for b in _part_btns:
		var pid: String = b.get_meta("pid")
		b.accessibility_name = "%d. %s%s" % [int(b.get_meta("i")) + 1, Loc.t(Content.part_name(pid)),
			" ✔" if inspected.has(pid) else ""]
	for b in _diag_btns:
		b.enabled = unlocked
		b.color = UI.CYAN if unlocked else UI.DIM
		b.accessibility_name = Loc.t(job["diagnosis"][int(b.get_meta("i"))]["text"]) + \
			("" if unlocked else " (" + Loc.t("недоступно") + ")")
	if chair:
		for pid: String in job["parts"]:
			var hb := chair.spot_button(pid)
			if hb:
				hb.update_a11y()


func rebuild() -> void:
	if chair:
		_m3d_state = {"yaw": chair.view_yaw(), "zoom_k": chair.zoom_k}
	super.rebuild()


# ---------------- действия ----------------

## Клик по детали (кружок, строка списка): осмотр в диагнозе.
func part_clicked(pid: String) -> void:
	if phase == "diagnose":
		inspect_part(pid)


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
		Audio.sfx("ok")
		Nav.flash("Диагноз верный! Приступаем к ремонту.", UI.GOOD, 3.0)
		var steps: Array = job.get("steps", [])
		if not steps.is_empty():
			ghost_line = steps[0].get("ghost", "")
		client_queue.clear()
		talk_later = [t + 1.8, "client", "good"]
		rebuild()
		return true
	mistakes += 1
	Audio.sfx("bad")
	var fb: String = opt.get("feedback", "")
	Nav.flash(fb if fb != "" else "Не похоже. Осмотри ещё раз.", UI.BAD, 4.0)
	react_mistake()
	return false


func zoom(steps: int) -> void:
	Audio.sfx("tick")
	if not chair.zoom(steps):
		Nav.flash("Крупнее нельзя." if steps > 0 else "Мельче нельзя.", UI.GHOST, 1.5)


func skip_tutorial() -> void:
	SaveGame.tutorial_skipped = true
	SaveGame.save()
	Audio.sfx("whoosh")
	Nav.go("hub")
	Nav.flash("Обучение пропущено: все клиенты уже ждут. Коляску Мартина можно починить в любой момент.", UI.GOOD, 5.0)


func go_back() -> void:
	if esc_t > 0.0:
		esc_t = 0.0
		Nav.go("hub")
		return
	esc_t = 2.5
	Nav.flash("Ещё раз Esc — покинуть ремонт (прогресс задания сбросится).", UI.AMBER, esc_t)


func handle_key(e: InputEventKey) -> bool:
	if e.keycode in [KEY_PLUS, KEY_EQUAL, KEY_KP_ADD] and chair and chair.has_frames():
		zoom(1)
		return true
	if e.keycode in [KEY_MINUS, KEY_KP_SUBTRACT] and chair and chair.has_frames():
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
	if _mentor.say(ghost_text()) and _mentor.shown():
		Audio.sfx("ghost")
	if _client_bubble.line != client_line:
		_client_bubble.say(client_line)
	var i := 0
	for b in _part_btns:
		b.slide = Vector2(int(160 * (1 - UI.appear(st, 0.05 * i, 0.35))), 0)
		i += 1
	_deco.queue_redraw()


func _draw_deco() -> void:
	UI.draw_text(_deco, Loc.t(job["client"]), Vector2(24, 266), 16, UI.WHITE, true)
	if phase == "diagnose":
		var cr := chair_rect()
		UI.draw_text(_deco, Loc.t("ДИАГНОСТИКА"), Vector2(360, 70), 20, UI.CYAN, true)
		UI.draw_wrapped(_deco, Loc.t(job["symptom"]), Vector2(360, 100), 560, 17, UI.WHITE)
		var unlocked := inspected.size() >= inspect_req
		var touch := OS.has_feature("mobile")
		var tip := Loc.t("Улики собраны — выбери диагноз:") if unlocked else Loc.tf(
			"Осмотри детали (тап по коляске или списку): {0}/{1}" if touch else "Осмотри детали (клик по коляске или списку): {0}/{1}",
			[inspected.size(), inspect_req])
		UI.draw_text(_deco, tip, Vector2(360, cr.end.y + 4), 15, UI.GREY if unlocked else UI.AMBER, not unlocked)
		UI.draw_text(_deco, Loc.t("ДИАГНОЗ"), Vector2(980, right_col_top() + 6), 16, UI.CYAN if unlocked else UI.DIM, true)
		UI.draw_text(_deco, Loc.t("ОСМОТРЕТЬ"), Vector2(980, 70), 16, UI.AMBER, true)
	else:
		UI.draw_text(_deco, Loc.t("РЕМОНТ"), Vector2(360, 70), 20, UI.AMBER, true)


func _draw_part_row(b: GameButton, _r: Rect2) -> void:
	var pid: String = b.get_meta("pid")
	var i: int = b.get_meta("i")
	var hov := b.is_hovered()
	var r := Rect2(b.slide, b.size)
	UI.draw_round_rect(b, r, UI.PANEL2 if hov else UI.PANEL, UI.AMBER if hov else UI.DIM, 2, 6)
	var nc := r.position + Vector2(17, r.size.y / 2.0)
	b.draw_circle(nc, 11, UI.INK, true, -1, true)
	UI.draw_ring(b, nc, 11, UI.GOOD if (phase == "diagnose" and inspected.has(pid)) else UI.AMBER, 2)
	UI.draw_text(b, str(i + 1), nc, 13, UI.WHITE, true, 1)
	var f: Array = UI.fit_text(Loc.t(Content.part_name(pid)), r.size.x - 56, 16)
	var fh := floorf(UI.line_height(16) / 2.0)
	UI.draw_text(b, f[0], Vector2(r.position.x + 34, nc.y - fh + floorf((16 - int(f[1])) / 2.0)), f[1], UI.WHITE)
	if phase == "diagnose" and inspected.has(pid):
		UI.draw_text(b, "✔", Vector2(r.end.x - 10, nc.y - 9), 15, UI.GOOD, false, 2)


func _draw_diag(b: GameButton, r: Rect2) -> void:
	var i: int = b.get_meta("i")
	var unlocked := inspected.size() >= inspect_req
	UI.draw_wrapped(b, Loc.t(job["diagnosis"][i]["text"]), r.position + Vector2(12, 6), r.size.x - 24, _dsize,
		UI.WHITE if unlocked else UI.GREY)
