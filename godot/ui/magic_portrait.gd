class_name MagicPortrait
extends Control
## Портрет героя с «волшебством» (magic_* — _magic_tick/_draw_magic/start_magic в game.py). Статичный портрет дышит;
## петля волшебства ложится так, что портрет в кадре совпадает со статичным (масштаб — высота портрета в кадре =
## высоте на экране, раскладка из anim_magic_index.json), поля с волшебством выходят за бокс, выше top — обрезано
## (под шапкой). Переход портрет ↔ кадр — 0,25 с. Задание: раз через 0,8 с после входа (если кадры в памяти не позже
## 15 с) и по клику/тапу на портрет. Итог: после подпрыга (1,8 с), потом раз в 60 с и по клику. «Без анимации»,
## проезд, нет петли — статичный портрет.

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
		if magic_t0 < 0.0 and start():
			accept_event()


func playing() -> bool:
	return magic_t0 >= 0.0


func _dur() -> float:
	var e: Dictionary = Frames.magic.get(loop_name, {})
	return float(e.get("n", 1)) / float(e.get("fps", 12))


func hopping() -> bool:
	return result_mode and t - enter_t < float(_c.get("result_hop", 1.6))


## Сыграть волшебство с начала (true — началось).
func start() -> bool:
	if loop_name == "" or Settings.calm() or paused or not Frames.loop_ready(loop_name):
		return false
	if result_mode:
		if hopping():
			return false
		next_t = t + float(_c.get("repeat", 60.0))
	magic_t0 = t
	auto = false
	plays += 1
	return true


func _process(dt: float) -> void:
	t += dt
	_fig.position = box.position - position - Vector2(0, hop)
	if loop_name == "" or Settings.calm() or paused:
		magic_t0 = -1.0
	elif magic_t0 >= 0.0:
		if t - magic_t0 >= _dur():
			magic_t0 = -1.0                      # доиграло — снова статичный портрет
	else:
		Frames.want_loop(loop_name)              # кадры — в память заранее
		var ready := Frames.loop_ready(loop_name)
		var since := t - enter_t
		if result_mode:
			var due := (auto and since >= float(_c.get("result_delay", 1.8))) or (next_t >= 0.0 and t >= next_t)
			if due and ready:
				start()
		else:
			if auto and since > float(_c.get("auto_secs", 15.0)):
				auto = false
			if auto and ready and since >= float(_c.get("delay", 0.8)):
				start()
	_fig.visible = _alpha() < 1.0
	_layer.queue_redraw()


func _alpha() -> float:
	if magic_t0 < 0.0 or hop > 0.0 or loop_name == "":
		return 0.0
	var u := t - magic_t0
	return clampf(minf(u, _dur() - u) / float(_c.get("fade", 0.25)), 0.0, 1.0)


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
	var real := UI.fit_rect(st_tex.get_size(), box)
	var sz: Array = e["size"]
	var pr: Array = e["portrait"]
	var sf := real.size.y / float(pr[3])
	var pos := Vector2(real.position.x + real.size.x / 2 - (float(pr[0]) + float(pr[2]) / 2) * sf,
		real.position.y + real.size.y / 2 - (float(pr[1]) + float(pr[3]) / 2) * sf)
	_layer.draw_texture_rect(tex, Rect2(pos - position, Vector2(float(sz[0]), float(sz[1])) * sf), false, Color(1, 1, 1, a))
	drawn += 1
