class_name MagicPortrait
extends Control
## Портрет героя с «волшебством» (magic_* — _magic_tick/_draw_magic/start_magic в game.py). Статичный портрет дышит;
## петля волшебства ложится так, что портрет в кадре совпадает со статичным (масштаб — высота портрета в кадре =
## высоте на экране, раскладка из anim_magic_index.json), поля с волшебством выходят за бокс, выше top — обрезано
## (под шапкой). Переход портрет ↔ кадр — 0,25 с. Задание: раз через 0,8 с после входа (если кадры в памяти не позже
## 15 с) и по клику/тапу на портрет. Итог: после подпрыга (1,8 с), потом раз в 60 с и по клику. «Без анимации»,
## проезд, нет петли — статичный портрет.
## «Живой» портрет (IDLE_LOOPS — Мартин martin_idle, 20.11 как game.py): кадр 0 петли = поза картинки = кадр 0
## волшебства, поэтому петля портрета идёт по своим часам (idle_t0, portrait_t — _portrait_t в game.py): после входа
## стоит на кадре 0, пока не сыграет первое волшебство (не дольше magic.hold с), волшебство само стартует на стыке
## петли (queue — queue_magic), к концу волшебства под ним кадр 0, после — петля с кадра 0. Клик: стык ближе
## magic.seam_wait — ждём его, иначе сразу (переход fade от текущего кадра петли).

var art: String = ""
var box: Rect2 = Rect2(24, 70, 150, 190)
var top: float = 55.0
var result_mode: bool = false
var loop_name: String = ""
var t: float = 0.0
var enter_t: float = 0.0
var magic_t0: float = -1.0
var auto: bool = true
var next_t: float = -1.0
var plays: int = 0
var drawn: int = 0
var hop: float = 0.0                       # подпрыг (итог) — сдвиг вверх
var paused: bool = false                   # проезд тест-драйва: волшебство не играет
var idle_t0: float = -1.0                  # часы петли «живого» портрета (_idle_t0); < 0 — стоит на кадре 0
var magic_at: float = -1.0                 # волшебство ждёт стыка петли портрета (_magic_at); < 0 — не ждёт
var _fig: Figure
var _layer: Control
var _c: Dictionary = {}


static func make(client_art: String, bx: Rect2, clip_top: float, on_result: bool) -> MagicPortrait:
	var m := MagicPortrait.new()
	m.art = client_art
	m.box = bx
	m.top = clip_top
	m.result_mode = on_result
	return m


func _init() -> void:
	clip_contents = true
	mouse_filter = Control.MOUSE_FILTER_STOP
	name = "Portrait"


func _ready() -> void:
	position = Vector2(0, top)
	size = Vector2(UI.W, UI.H - top)
	_c = Content.consts.get("magic", {})
	for n: String in Frames.magic:
		if Frames.magic[n].get("art") == art and Frames.loop_count(n) >= int(Frames.magic[n].get("n", 0)):
			loop_name = n
	_fig = Figure.make(art, box.position - position, box.size, "breathe")
	add_child(_fig)
	_layer = Control.new()                       # кадр волшебства — поверх статичного портрета
	_layer.size = size
	_layer.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_layer.draw.connect(_draw_frame)
	add_child(_layer)


func _has_point(p: Vector2) -> bool:
	return Rect2(box.position - position, box.size).has_point(p)


func _gui_input(e: InputEvent) -> void:
	if e is InputEventMouseButton and e.pressed and e.button_index == MOUSE_BUTTON_LEFT:
		if magic_t0 < 0.0 and queue(true):
			accept_event()


func playing() -> bool:
	return magic_t0 >= 0.0


func _dur() -> float:
	var e: Dictionary = Frames.magic.get(loop_name, {})
	return float(e.get("n", 1)) / float(e.get("fps", 12))


func hopping() -> bool:
	return result_mode and t - enter_t < float(_c.get("result_hop", 1.6))


## Сыграть волшебство с начала (true — началось); at ≥ 0 — с какого момента (стык петли портрета).
func start(at: float = -1.0) -> bool:
	magic_at = -1.0
	if loop_name == "" or Settings.calm() or paused or not Frames.loop_ready(loop_name):
		return false
	var t0 := t if at < 0.0 else minf(t, at)
	if result_mode:
		if hopping():
			return false
		next_t = t0 + float(_c.get("repeat", 60.0))
	magic_t0 = t0
	auto = false
	plays += 1
	return true


## Волшебство на стыке «живого» портрета (queue_magic): портрет не живой или петля на кадре 0 — сразу; клик и стык
## дальше seam_wait — тоже сразу. true — началось или ждёт стыка.
func queue(click: bool = false) -> bool:
	if magic_t0 >= 0.0 or magic_at >= 0.0:
		return false
	var at := seam()
	if at < 0.0 or at <= t or (click and at - t > float(_c.get("seam_wait", 0.4))):
		return start()
	if loop_name == "" or Settings.calm() or paused or (result_mode and hopping()):
		return false
	magic_at = at
	return true


## Петля «живого» портрета (IDLE_LOOPS), если её кадры в памяти и анимация включена, иначе "" (_portrait_live).
func live_loop() -> String:
	var n := Figure.idle_loop(art)
	if n == "" or Settings.calm() or Frames.loop_count(n) == 0 or not Frames.loop_ready(n):
		return ""
	return n


## Часы петли портрета (_portrait_t): от idle_t0 с кадра 0, до него — кадр 0. Пока играет волшебство: первая
## половина — кадр, на котором оно началось, вторая — кадр 0; после — снова с кадра 0. Герой без волшебства — свои t.
func portrait_t() -> float:
	if loop_name == "":
		return t
	var t0 := idle_t0
	var now := t
	if magic_t0 >= 0.0:
		if t - magic_t0 >= _dur() / 2:
			t0 = magic_t0 + _dur()
		else:
			now = magic_t0
	return 0.0 if t0 < 0.0 else maxf(0.0, now - t0) + 1e-4     # на стыке k·период — кадр 0, не последний


## Ближайший стык петли портрета (снова кадр 0) или -1 — портрет не живой (_portrait_seam).
func seam() -> float:
	var n := live_loop()
	if n == "":
		return -1.0
	if idle_t0 < 0.0:
		return t
	var per := Frames.loop_count(n) / Frames.anim_fps
	return idle_t0 + per * maxf(0.0, ceilf((t - idle_t0) / per - 1e-6))


## Номер кадра петли портрета сейчас (самопроверка) или -1 — портрет картинкой.
func portrait_frame() -> int:
	var n := live_loop()
	if n == "" or not _fig.live():
		return -1
	return int(portrait_t() * Frames.anim_fps) % Frames.loop_count(n)


func _process(dt: float) -> void:
	t += dt
	_fig.position = box.position - position - Vector2(0, hop)
	if loop_name == "":
		magic_t0 = -1.0
	elif Settings.calm() or paused:              # «Без анимации», проезд — портрет как раньше
		if magic_t0 >= 0.0 or idle_t0 < 0.0:
			idle_t0 = t                          # петля портрета — с кадра 0
		magic_t0 = -1.0
		magic_at = -1.0
	elif magic_t0 >= 0.0:
		var end := magic_t0 + _dur()
		if t >= end:
			magic_t0 = -1.0                      # доиграло — снова портрет: петля с кадра 0
			idle_t0 = end
	else:
		if idle_t0 < 0.0 and t - enter_t > float(_c.get("hold", 3.0)):
			idle_t0 = t                          # первое волшебство не готово — петля портрета пошла
		Frames.want_loop(loop_name)              # кадры — в память заранее
		var ready := Frames.loop_ready(loop_name)
		var since := t - enter_t
		if magic_at >= 0.0:                      # ждём стыка петли портрета
			if t >= magic_at:
				start(magic_at)
		elif result_mode:
			var due := (auto and since >= float(_c.get("result_delay", 1.8))) or (next_t >= 0.0 and t >= next_t)
			if due and ready:
				queue()                          # на стыке «живого» портрета
		else:
			if auto and since > float(_c.get("auto_secs", 15.0)):
				auto = false
			if auto and ready and since >= float(_c.get("delay", 0.8)):
				queue()                          # петля портрета ещё на кадре 0 — сразу, иначе на стыке
	_fig.clock_t = portrait_t() if loop_name != "" else -1.0
	_fig.visible = _alpha() < 1.0
	_layer.queue_redraw()


func _alpha() -> float:
	if magic_t0 < 0.0 or hop > 0.0 or loop_name == "":
		return 0.0
	var u := t - magic_t0
	return clampf(minf(u, _dur() - u) / float(_c.get("fade", 0.25)), 0.0, 1.0)


## Где рисовать кадр волшебства (экран): портрет в кадре (portrait из anim_magic_index.json) — точно на картинке
## UI.fit_rect(картинка, бокс) по обеим осям (20.11; раньше ширина — по масштабу высоты).
func frame_rect() -> Rect2:
	var e: Dictionary = Frames.magic.get(loop_name, {})
	var st_tex := Content.texture(art)
	if e.is_empty() or st_tex == null:
		return Rect2()
	var real := UI.fit_rect(st_tex.get_size(), box)
	var sz: Array = e["size"]
	var pr: Array = e["portrait"]
	var k := real.size / Vector2(float(pr[2]), float(pr[3]))
	return Rect2(real.position - Vector2(float(pr[0]), float(pr[1])) * k, Vector2(float(sz[0]), float(sz[1])) * k)


func _draw_frame() -> void:
	if magic_t0 < 0.0 or hop > 0.0:
		return
	var e: Dictionary = Frames.magic[loop_name]
	var fps := float(e["fps"])
	var dur := _dur()
	var u := t - magic_t0
	var tex := Frames.loop_frame(loop_name, minf(u, dur - 0.5 / fps), fps)
	var st_tex := Content.texture(art)
	if tex == null or st_tex == null:
		return
	var a := _alpha()                            # переход: статичный портрет под кадром
	var fr := frame_rect()
	_layer.draw_texture_rect(tex, Rect2(fr.position - position, fr.size), false, Color(1, 1, 1, a))
	drawn += 1
