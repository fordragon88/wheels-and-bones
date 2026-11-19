class_name Prof
extends Node
## Профилировка кадра — включается только явно: браузер — ?prof=1 вместе с ?test=1 или ?fps=1, компьютер — «-- --prof».
## Без неё ничего не делает (UI проверяет одну статическую переменную Prof.on).
## Что меряет (окно 1 с, средние на кадр):
##   • process — все _process узлов (от сигнала process_frame до Prof — приоритет 1999, Web — 2000), tick — экрана;
##   • draw — перерисовка CanvasItem: по сигналу draw каждого узла (подписка ставится ПЕРВОЙ — раньше draw.connect
##     самого узла), время узла = до начала следующего; ключ — класс скрипта (или движка) и имя узла;
##   • текст — вызовы и время UI.draw_text / draw_wrapped / wrap_lines / text_width / fit_*; draw_round_rect (StyleBox);
##   • render — время отрисовки кадра процессором (RenderingServer, viewport_get_measured_render_time_cpu) и
##     видеокартой (gpu; в браузере обычно 0 — таймеры WebGL закрыты), вызовы рисования (draw calls), объекты, узлы.
## Сводка: Prof.summary (Dictionary) → window.wnbState.prof (?test=1) и строка «[wnb] prof …» в консоль раз в 3 с
## (на компьютере — в stdout).

static var on: bool = false
static var acc: Dictionary = {}           # ключ → PackedInt64Array[вызовов, мкс] (текст, тик экрана)
static var summary: Dictionary = {}

var _frames: int = 0
var _win_t: float = 0.0
var _log_t: float = 0.0
var _draw: Dictionary = {}                # ключ узла → [вызовов, мкс]
var _last_key: String = ""
var _last_us: int = 0
var _draw_t0: int = 0
var _draw_sum: int = 0
var _draw_n: int = 0
var _proc_t0: int = 0
var _proc_sum: int = 0
var _render_cpu: float = 0.0
var _render_gpu: float = 0.0
var _calls: float = 0.0
var _objs: float = 0.0
var _prims: float = 0.0
var _frame_us: int = 0
var _last_frame: int = 0
var _worst_frame: int = 0


static func t0() -> int:
	return Time.get_ticks_usec()


static func add(key: String, since: int) -> void:
	var a: PackedInt64Array = acc.get(key, PackedInt64Array([0, 0]))
	a[0] += 1
	a[1] += Time.get_ticks_usec() - since
	acc[key] = a


static func count(key: String) -> void:
	var a: PackedInt64Array = acc.get(key, PackedInt64Array([0, 0]))
	a[0] += 1
	acc[key] = a


func _ready() -> void:
	name = "Prof"
	on = true
	process_mode = Node.PROCESS_MODE_ALWAYS
	process_priority = 1999                   # перед Web (2000): конец _process всех остальных
	get_tree().process_frame.connect(_on_frame_start)      # сигнал — до _process узлов
	get_tree().node_added.connect(_hook)
	_hook_all(get_tree().root)
	RenderingServer.viewport_set_measure_render_time(get_viewport().get_viewport_rid(), true)


func _on_frame_start() -> void:
	_proc_t0 = Time.get_ticks_usec()
	var now := _proc_t0
	if _last_frame > 0:
		var d := now - _last_frame
		_frame_us += d
		_worst_frame = maxi(_worst_frame, d)
	_last_frame = now


func _hook_all(n: Node) -> void:
	_hook(n)
	for c in n.get_children():
		_hook_all(c)


## Подписка на draw — первой, чтобы метка времени стояла до рисования самого узла (свои draw.connect — после).
func _hook(n: Node) -> void:
	if not (n is CanvasItem) or n.has_meta("_prof"):
		return
	n.set_meta("_prof", true)
	var ci := n as CanvasItem
	var own := ci.get_signal_connection_list("draw")
	for c: Dictionary in own:
		ci.draw.disconnect(c["callable"])
	ci.draw.connect(_on_draw.bind(ci))
	for c: Dictionary in own:
		ci.draw.connect(c["callable"], c["flags"])


func _key(n: Node) -> String:
	var s: Script = n.get_script()
	var cls := s.get_global_name() if s != null else StringName()
	var c := String(cls) if cls != StringName() else n.get_class()
	var nm := String(n.name)
	if nm.begins_with("@") or nm.begins_with(c):
		return c
	var i := nm.find("_")                     # Card_flat, Part_tire, Spot_axle → Card_*, Part_*
	if i > 0:
		nm = nm.substr(0, i) + "_*"
	return c + ":" + nm


func _on_draw(n: CanvasItem) -> void:
	var now := Time.get_ticks_usec()
	if _last_key == "":
		_draw_t0 = now
		_end_draws.call_deferred()            # после всех перерисовок кадра (очередь отложенных вызовов)
	else:
		_add_draw(_last_key, now - _last_us)
	_last_key = _key(n)
	_last_us = now
	_draw_n += 1


func _end_draws() -> void:
	var now := Time.get_ticks_usec()
	if _last_key != "":
		_add_draw(_last_key, now - _last_us)
		_draw_sum += now - _draw_t0
	_last_key = ""


func _add_draw(k: String, us: int) -> void:
	var a: PackedInt64Array = _draw.get(k, PackedInt64Array([0, 0]))
	a[0] += 1
	a[1] += us
	_draw[k] = a


func _process(dt: float) -> void:
	_proc_sum += Time.get_ticks_usec() - _proc_t0
	_frames += 1
	var vp := get_viewport().get_viewport_rid()
	_render_cpu += RenderingServer.viewport_get_measured_render_time_cpu(vp) + RenderingServer.get_frame_setup_time_cpu()
	_render_gpu += RenderingServer.viewport_get_measured_render_time_gpu(vp)
	_calls += Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)
	_objs += Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME)
	_prims += Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME)
	_win_t += dt
	if _win_t >= 1.0:
		_summarize()
	_log_t += dt
	if _log_t >= 3.0 and not summary.is_empty():
		_log_t = 0.0
		var line := "[wnb] prof " + line_text()
		if OS.has_feature("web"):
			JavaScriptBridge.eval("console.log(%s)" % JSON.stringify(line), true)
		else:
			print(line)


func _ms(us: float) -> float:
	return snappedf(us / 1000.0 / maxf(1, _frames), 0.01)


func _summarize() -> void:
	var f := float(maxi(1, _frames))
	var top: Array = []
	for k: String in _draw:
		var a: PackedInt64Array = _draw[k]
		top.append([k, snappedf(a[1] / 1000.0 / f, 0.01), snappedf(a[0] / f, 0.1)])
	top.sort_custom(func(x: Array, y: Array) -> bool: return x[1] > y[1])
	var text := {}
	var ticks := {}
	for k: String in acc:
		var a: PackedInt64Array = acc[k]
		var row := [snappedf(a[1] / 1000.0 / f, 0.01), snappedf(a[0] / f, 0.1)]
		if k.begins_with("tick:"):
			ticks[k.substr(5)] = row
		else:
			text[k] = row
	var procs := {}
	_count_proc(get_tree().root, procs)
	summary = {"screen": Nav.current_name, "frames": _frames, "fps": snappedf(_frames / _win_t, 0.1),
		"frame_ms": _ms(_frame_us), "worst_ms": snappedf(_worst_frame / 1000.0, 0.1),
		"process_ms": _ms(_proc_sum), "draw_ms": _ms(_draw_sum), "redraws": snappedf(_draw_n / f, 0.1),
		"render_cpu_ms": snappedf(_render_cpu / f, 0.01), "render_gpu_ms": snappedf(_render_gpu / f, 0.01),
		"draw_calls": snappedf(_calls / f, 0.1), "objects": snappedf(_objs / f, 0.1), "primitives": snappedf(_prims / f, 0.1),
		"nodes": int(Performance.get_monitor(Performance.OBJECT_NODE_COUNT)), "draw_top": top.slice(0, 14),
		"text": text, "tick": ticks, "processing": procs}
	_frames = 0
	_win_t = 0.0
	_frame_us = 0
	_worst_frame = 0
	_proc_sum = 0
	_draw_sum = 0
	_draw_n = 0
	_render_cpu = 0.0
	_render_gpu = 0.0
	_calls = 0.0
	_objs = 0.0
	_prims = 0.0
	_draw.clear()
	acc.clear()


func _count_proc(n: Node, out: Dictionary) -> void:
	if n.is_processing() and n.can_process() and n != self:
		var s: Script = n.get_script()
		var c := String(s.get_global_name()) if s != null and s.get_global_name() != StringName() else n.get_class()
		out[c] = int(out.get(c, 0)) + 1
	for ch in n.get_children():
		_count_proc(ch, out)


## Одна строка для консоли: кадр, process/draw/render, вызовы рисования, топ-5 узлов, текст.
static func line_text() -> String:
	var s := summary
	var out := "%s fps %.0f frame %.1f ms: process %.2f draw %.2f render %.2f (gpu %.2f) · calls %.0f redraws %.0f nodes %d" % [
		s["screen"], s["fps"], s["frame_ms"], s["process_ms"], s["draw_ms"], s["render_cpu_ms"], s["render_gpu_ms"],
		s["draw_calls"], s["redraws"], s["nodes"]]
	var top: Array = s["draw_top"]
	out += " · top"
	for r: Array in top.slice(0, 5):
		out += " %s %.2f/%.0f" % r
	var tx: Dictionary = s["text"]
	out += " · text"
	for k: String in tx:
		out += " %s %.2f/%.0f" % [k, tx[k][0], tx[k][1]]
	return out
