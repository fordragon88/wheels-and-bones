extends Node
## Браузерная сборка (godot/tools/build_web.py, страница web/shell.html): всё, что относится только к браузеру.
##   • параметры адреса страницы (?fps=1, ?test=1; ссылки-задания разбирает Share — только свои ключи);
##   • сеть: кадры и музыка лежат файлами рядом с игрой (frames/…, music/…), качает их fetch страницы (wnbNet) —
##     параллельно и мимо игрового кадра; игра раз в кадр забирает готовое (Frames);
##   • музыка — элемент <audio> страницы (wnbMusic): Audio зовёт music_*;
##   • плашка кадров/с по ?fps=1 (на компьютере — «-- --fps»), как FPS_HUD в game.py, и строка в консоль браузера;
##     на сенсорном экране — крупнее, в две строки, с размером окна в CSS-пикселях и devicePixelRatio (и потолком ?res);
##   • ?prof=1 (только вместе с ?test=1 или ?fps=1; на компьютере «-- --prof») — профилировка кадра (ui/prof.gd);
##   • заслонка «поверни телефон» (страница, shell.html): пока она закрывает игру — дерево на паузе и кадры не
##     рисуются (RenderingServer.render_loop_enabled); язык игры уходит странице (wnbLang) — тексты заслонки и кнопок;
##   • ?test=1 — раз в 0,25 с window.wnbState (JSON) для проверки godot/tools/web_smoke.py: экран, фаза, кадры/с,
##     кадры (скачано/в очереди/ошибки), видимые кнопки с прямоугольниками и подсказка «что нажать дальше».
## На компьютере (не браузер) работает только плашка кадров/с.

var on: bool = false
var params: Dictionary = {}              # параметры адреса страницы: имя → значение (последнее)
var test: bool = false                   # ?test=1 — состояние для автопроверки
var fps_on: bool = false                 # ?fps=1 / --fps — плашка кадров/с
var prof_on: bool = false                # ?prof=1 (+ ?test=1/?fps=1) / --prof — профилировка кадра
var covered: bool = false                # заслонка страницы закрывает игру (книжная ориентация телефона)
var cfg: Dictionary = {}                 # game_consts.json → web: {frames_v, music_v, music_ext} (пишет build_web.py)
var fps: float = 0.0
var fps_min10: float = 0.0
var title_marked: bool = false

var _n: int = 0
var _t: float = 0.0
var _hist: Array[float] = []
var _hud: Label
var _st_t: float = 0.0
var _log_t: float = 0.0
var _music_url: String = ""
var _music_vol: float = -1.0
var _worst_ms: float = 0.0               # самый долгий кадр за окно замера
var _worst_win: float = 0.0
var _touch: bool = false
var _cover_cb: JavaScriptObject           # обратный вызов для страницы (держим ссылку, иначе его соберут)
var _lang_sent: String = ""
var _stage_cb: JavaScriptObject           # ?test=1: window.wnbStage(имя) — состояние снимка tests/shots.gd (замер)
var _stager: Node


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	process_priority = 2000                  # после экранов: состояние кадра уже обновлено
	on = OS.has_feature("web")
	cfg = Content.consts.get("web", {})
	if on:
		params = parse_query(str(JavaScriptBridge.eval("window.location.search || ''", true)))
	test = on and flag("test")
	fps_on = flag("fps") or OS.get_cmdline_user_args().has("--fps")
	prof_on = (flag("prof") and (test or fps_on)) or OS.get_cmdline_user_args().has("--prof")
	if prof_on:
		add_child(Prof.new())
	_touch = DisplayServer.is_touchscreen_available()
	if on:
		_cover_cb = JavaScriptBridge.create_callback(_on_cover)
		if str(JavaScriptBridge.eval("typeof window.wnbOnCover", true)) == "function":
			JavaScriptBridge.get_interface("window").wnbOnCover(_cover_cb)
		Loc.changed.connect(_send_lang)
		_send_lang()
	if test:                                 # web_smoke screens: любое состояние экрана без прохождения
		_stage_cb = JavaScriptBridge.create_callback(_on_stage)
		JavaScriptBridge.get_interface("window").wnbStage = _stage_cb
	if fps_on and not on:
		# компьютер (-- --fps): одна строка мелко у нижнего края — там на всех экранах нет кнопок (см. PORT_PLAN,
		# «Плашка замера»). В браузере плашка — в странице (wnbHud в web/shell.html): в чёрных полях по бокам, если они
		# есть, иначе узкой полосой у нижнего края; касания сквозь неё проходят в игру.
		var layer := CanvasLayer.new()
		layer.name = "FpsHud"
		layer.layer = 128
		_hud = Label.new()
		_hud.mouse_filter = Control.MOUSE_FILTER_IGNORE
		_hud.add_theme_font_size_override("font_size", 10)
		_hud.add_theme_color_override("font_color", Color.WHITE)
		var sb := StyleBoxFlat.new()
		sb.bg_color = Color(0, 0, 0, 0.5)
		sb.content_margin_left = 3
		sb.content_margin_right = 3
		_hud.add_theme_stylebox_override("normal", sb)
		_hud.position = Vector2(2, 720 - 14)
		_hud.auto_translate_mode = Node.AUTO_TRANSLATE_MODE_DISABLED
		_hud.accessibility_name = ""
		layer.add_child(_hud)
		get_tree().root.add_child.call_deferred(layer)


## Страница: заслонка закрыла/открыла игру. Закрыла — пауза дерева и без отрисовки кадров (не греть телефон зря).
func _on_cover(args: Array) -> void:
	var c := bool(args[0]) if not args.is_empty() else false
	if c == covered:
		return
	covered = c
	get_tree().paused = c
	RenderingServer.render_loop_enabled = not c


## window.wnbStage("seat_fit_troll") — поставить экран в состояние снимка (tests/shots.gd stage, только ?test=1).
func _on_stage(args: Array) -> void:
	if args.is_empty():
		return
	if _stager == null:
		var gd := load("res://tests/shots.gd") as GDScript
		if gd == null or not gd.can_instantiate():
			push_error("tests/shots.gd не загрузился")
			return
		_stager = gd.new()
		_stager.set("stage_only", true)
		add_child(_stager)
	_stager.call("web_stage", str(args[0]))


## Язык игры — странице (тексты заслонки и кнопок полного экрана; запоминает до следующей загрузки).
func _send_lang() -> void:
	if Loc.code == _lang_sent:
		return
	_lang_sent = Loc.code
	JavaScriptBridge.eval("window.wnbLang && wnbLang(%s)" % JSON.stringify(Loc.code), true)


## «a=1&b=x+y» → {a: "1", b: "x y"} (как parse_qs: последнее значение).
static func parse_query(q: String) -> Dictionary:
	var s := q.strip_edges()
	if s.begins_with("?"):
		s = s.substr(1)
	var h := s.find("#")
	if h >= 0:
		s = s.substr(0, h)
	var out := {}
	for pair: String in s.split("&", false):
		var eq := pair.find("=")
		var k := (pair if eq < 0 else pair.substr(0, eq)).replace("+", " ").uri_decode()
		var v := ("" if eq < 0 else pair.substr(eq + 1)).replace("+", " ").uri_decode()
		out[k] = v
	return out


## Параметр-флажок: ?fps=1 / ?fps=yes — да; пусто, 0, no, off, false — нет (fps_hud_wanted в game.py).
func flag(k: String) -> bool:
	if not params.has(k):
		return false
	return not str(params[k]).strip_edges().to_lower() in ["0", "no", "off", "false"]


## Адрес файла рядом с игрой с меткой версии (против кеша браузера): asset("frames/…webp", "frames_v").
func asset(rel: String, ver_key: String) -> String:
	var v := str(cfg.get(ver_key, ""))
	return rel + ("?v=" + v if v != "" else "")


# ---------------- сеть (wnbNet страницы) ----------------

func net_get(url: String) -> void:
	JavaScriptBridge.eval("wnbNet.get(%s)" % JSON.stringify(url), true)


## Адреса, которые докачались (или не смогли) с прошлого вызова.
func net_ready() -> PackedStringArray:
	var s: Variant = JavaScriptBridge.eval("wnbNet.next()", true)
	return str(s).split("\n", false) if s != null else PackedStringArray()


## Кадр уже распакован фоновым потоком страницы: размер (Vector2i); (0, 0) — в take() сырые байты файла.
func net_dims(url: String) -> Vector2i:
	var s := str(JavaScriptBridge.eval("wnbNet.dims(%s)" % JSON.stringify(url), true))
	var p := s.split(",")
	return Vector2i(int(p[0]), int(p[1])) if p.size() == 2 else Vector2i.ZERO


## Байты скачанного файла (пусто — ошибка сети/404) или RGBA-пиксели (net_dims). Забирает: второй раз — пусто.
func net_take(url: String) -> PackedByteArray:
	var b: Variant = JavaScriptBridge.eval("wnbNet.take(%s)" % JSON.stringify(url), true)
	return b if b is PackedByteArray else PackedByteArray()


## Убрать из очереди страницы ещё не начатые загрузки с этим началом адреса (коляска сменилась).
func net_drop(prefix: String) -> void:
	JavaScriptBridge.eval("wnbNet.drop(%s)" % JSON.stringify(prefix), true)


func net_stats() -> Dictionary:
	var s: Variant = JavaScriptBridge.eval("wnbNet.stats()", true)
	var d: Variant = JSON.parse_string(str(s)) if s != null else null
	return d if d is Dictionary else {}


# ---------------- музыка (wnbMusic страницы) ----------------

func music_url(theme: String) -> String:
	return asset("music/%s.%s" % [theme, str(cfg.get("music_ext", "mp3"))], "music_v")


func music_play(theme: String) -> void:
	var u := music_url(theme)
	if u == _music_url:
		return
	_music_url = u
	JavaScriptBridge.eval("wnbMusic.play(%s)" % JSON.stringify(u), true)


func music_stop() -> void:
	if _music_url == "":
		return
	_music_url = ""
	JavaScriptBridge.eval("wnbMusic.stop()", true)


## Громкость 0..1 (вызывается каждый кадр — в страницу уходит только заметное изменение).
func music_volume(v: float) -> void:
	if absf(v - _music_vol) < 0.004 and not (v == 0.0 and _music_vol != 0.0):
		return
	_music_vol = v
	JavaScriptBridge.eval("wnbMusic.volume(%.4f)" % v, true)


# ---------------- кадр ----------------

func _process(dt: float) -> void:
	if on and not title_marked and Nav.current != null:
		title_marked = true                  # первый кадр игры с экраном — заставка страницы гаснет, время загрузки
		JavaScriptBridge.eval("window.wnbMark && wnbMark('title')", true)
	_n += 1
	_t += dt
	_worst_win = maxf(_worst_win, dt * 1000.0)
	if _t >= 1.0:
		fps = _n / _t
		_n = 0
		_t = 0.0
		_worst_ms = _worst_win
		_worst_win = 0.0
		_hist.append(fps)
		if _hist.size() > 10:
			_hist.pop_front()
		fps_min10 = _hist.min()
		if fps_on:
			var ws := DisplayServer.window_get_size()
			var parts: Array = ["fps %.0f" % fps, "min10s %.0f" % fps_min10, "max %.0f ms" % _worst_ms]
			if _touch:
				parts.append("touch")
			if on:                               # окно Godot — в строку размеров страницы, поля — в плашку страницы
				parts.append(Frames.status_line())
				JavaScriptBridge.eval("window.wnbGodotSize = '%d\u00d7%d'; window.wnbHud && wnbHud(%s)" % [ws.x, ws.y,
					JSON.stringify(parts)], true)
			elif _hud != null:
				parts.append("%s %d×%d" % [Loc.t("холст"), ws.x, ws.y])
				parts.append(Frames.status_line())
				_hud.text = " · ".join(parts)
				_hud.reset_size()
				_hud.position = Vector2(2, 720 - _hud.size.y)
	if on and fps_on:
		_log_t += dt
		if _log_t >= 3.0:                     # журнал замеров — только с ?fps=1 (как game.py)
			_log_t = 0.0
			var ws := DisplayServer.window_get_size()
			var line := "[wnb] fps %.1f min10s %.0f max %.0f ms px %dx%d scene %s frames %s" % [fps, fps_min10, _worst_ms,
				ws.x, ws.y, Nav.current_name, Frames.status_line()]
			JavaScriptBridge.eval("console.log(%s)" % JSON.stringify(line), true)
	if test:
		_st_t += dt
		if _st_t >= 0.25:
			_st_t = 0.0
			JavaScriptBridge.eval("window.wnbState = %s" % JSON.stringify(JSON.stringify(state())), true)


# ---------------- состояние для проверки (?test=1) ----------------

func state() -> Dictionary:
	var scr: Node = Nav.current
	var d := {"t": Time.get_ticks_msec(), "screen": Nav.current_name, "fps": snappedf(fps, 0.1), "fps_min10": snappedf(fps_min10, 0.1),
		"worst_ms": snappedf(_worst_ms, 0.1), "frames": Frames.stats(), "net": net_stats(),
		"lang": Loc.code, "calm": Settings.calm(), "sound": Settings.vol.get("on", true),
		"done": SaveGame.done.keys(), "assign": SaveGame.assign.get("id", "") if SaveGame.assign_on() else "",
		"toast": Nav.toast.text if Nav.toast.active() else "", "speech": Speech.last(),
		"share_dlg": Share.dlg.ui.get("mode", "") if Share.dlg != null else "",
		"settings": Nav.settings != null, "errors": Content.errors.size(), "migrated": SaveGame.migrated,
		"fullscreen": DisplayServer.window_get_mode() == DisplayServer.WINDOW_MODE_FULLSCREEN,
		"text_k": Settings.a11y.get("text", 0), "speech_on": Settings.a11y.get("on", false),
		"kb": str(A11y.kb_cur.name) if is_instance_valid(A11y.kb_cur) else "",
		"music": Audio._cur_theme, "buttons": _buttons(), "hint": [], "covered": covered, "paused": get_tree().paused}
	# окно Godot (= буфер холста) и где в нём игровая картинка 1280×720 после растяжения (x, y, ш, в) — для проверки,
	# что картинка целиком на экране (web_smoke stale)
	var ws := DisplayServer.window_get_size()
	var gr := get_tree().root.get_final_transform() * Rect2(0, 0, 1280, 720)
	d["win"] = [ws.x, ws.y]
	d["game"] = [snappedf(gr.position.x, 0.1), snappedf(gr.position.y, 0.1), snappedf(gr.size.x, 0.1), snappedf(gr.size.y, 0.1)]
	if prof_on:
		d["prof"] = Prof.summary
	if flag("compat"):                       # web_smoke migrate: прогресс и настройки — сверка с эталоном game.py
		d["compat"] = SaveGame.compat_dump(Settings)
	if scr != null:
		for k: String in ["phase", "step_idx", "sel_tool", "mistakes", "ride_done"]:
			if k in scr:
				d[k] = scr.get(k)
		if "job" in scr and scr.get("job") is Dictionary:
			d["job"] = (scr.get("job") as Dictionary).get("id", "")
		var rv: Variant = scr.get("ride") if "ride" in scr else null
		if rv is RideView:
			var r: RideView = rv
			d["ride"] = {"active": r.active, "riding": r.riding(), "loop": r.loop_name, "drawn": r.drawn, "stay": r.stay}
		var mp: Variant = scr.get("portrait") if "portrait" in scr else null
		if mp is MagicPortrait:
			d["magic"] = {"loop": mp.loop_name, "playing": mp.magic_t0 >= 0.0, "ready": mp.loop_name != "" and Frames.loop_ready(mp.loop_name)}
		var mg: Variant = scr.get("mini") if "mini" in scr else null
		if mg is MiniGame:
			d["mini"] = {"kind": mg.kind, "value": mg.value, "cfg": mg.cfg}
		d["hint"] = _hint(scr)
	return d


## Видимые нажимаемые кнопки: [имя, x, y, w, h] в координатах холста 1280×720 (страница переводит в пиксели).
func _buttons() -> Array:
	var out: Array = []
	var roots: Array[Node] = [Nav.host, Nav.overlay]
	for r: Node in roots:
		if r != null:
			_collect(r, out)
	return out


func _collect(n: Node, out: Array) -> void:
	if n is CanvasItem and not (n as CanvasItem).visible:
		return
	if (n is BaseButton and not (n as BaseButton).disabled or n is TextEdit or n is LineEdit \
			or n is Control and str(n.name).begins_with("Slider_")) \
			and (n as Control).mouse_filter != Control.MOUSE_FILTER_IGNORE:
		var c := n as Control
		var r := c.get_global_transform_with_canvas() * Rect2(Vector2.ZERO, c.size)
		out.append([str(c.name), roundf(r.position.x), roundf(r.position.y), roundf(r.size.x), roundf(r.size.y)])
	for ch: Node in n.get_children():
		_collect(ch, out)


## Что нажать дальше, чтобы пройти экран верно (только для проверки): имена кнопок по порядку.
func _hint(scr: Node) -> Array:
	match Nav.current_name:
		"title":
			return ["Start"]
		"intro":
			return ["Next"]
		"result":
			return ["ToHub"]
		"job":
			var job: Dictionary = scr.job
			var mg: Variant = scr.mini
			if mg is MiniGame:
				var m: MiniGame = mg
				match m.kind:
					"pump":
						var lo := int(m.cfg["lo"])
						var hi := int(m.cfg["hi"])
						if m.value < lo:
							return ["Pump"]
						if m.value > hi:
							return ["Release"]
						return ["Done"]
					"ping":
						return ["Spoke_%d" % int(m.dull.keys()[0])] if not m.dull.is_empty() else []
					"meter":
						var opts: Array = m.cfg["options"]
						for i in opts.size():
							if opts[i][1]:
								return ["Opt_%d" % i]
					"gap":
						return ["Check"]
				return []
			match str(scr.phase):
				"diagnose":
					var out: Array = []
					for pid: String in job["parts"]:
						if out.size() + scr.inspected.size() >= int(scr.inspect_req):
							break
						if not scr.inspected.has(pid):
							out.append("Part_" + pid)
					if not out.is_empty():
						return out
					for i in (job["diagnosis"] as Array).size():
						if job["diagnosis"][i].get("correct", false):
							return ["Diag_%d" % i]
				"repair":
					var st: Dictionary = scr.cur_step()
					if st.is_empty():
						return []
					if scr.sel_tool != st["tool"]:
						return ["Tool_" + str(st["tool"])]
					return ["Part_" + str(st["part"])]
				"test":
					return ["TestDrive"]
		"tech":
			if str(scr.phase) == "test" or bool(scr.ride_done):
				return ["TestDrive"]
			return ["StepSkip"]
	return []
