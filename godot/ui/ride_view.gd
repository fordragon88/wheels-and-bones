class_name RideView
extends Control
## Тест-драйв: клиент проезжает через мастерскую (_draw_ride/_draw_ride_anim в game.py). С петлёй ride_* (у всех 21
## героя): въезд из-за левого края, полный ход 60 % времени, плавное торможение по косинусу до центра зоны коляски;
## кадр петли — по пройденному пути (колёса не проскальзывают), предел ускорения из ride.json. Без петли — скользящий
## портрет (4 с, RIDE_FLIP — отражённый). Линии скорости и пыль из-под колёс.

var art: String = ""
var loop_name: String = ""                 # выбрано при старте проезда — до конца проезда
var stop_x: float = 575.0
var t: float = 0.0
var t0: float = -1.0
var active: bool = false                  # проезд идёт (или только что закончился — экран заберёт итог)
var drawn: int = 0
var _add: Control
var _r: Dictionary = {}


func _init() -> void:
	size = Vector2(UI.W, UI.H)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	name = "Ride"


func _ready() -> void:
	_r = Frames.ride
	_add = Control.new()
	_add.size = size
	_add.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var mat := CanvasItemMaterial.new()
	mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	_add.material = mat
	_add.draw.connect(_draw_add)
	add_child(_add)


## Петля проезда героя (по портрету) или "" — без проверки кадров.
static func hero_loop(client_art: String) -> String:
	var n: String = Frames.ride.get("anim", {}).get(client_art, "")
	return n if Frames.loop_count(n) > 0 else ""


## Сколько длится проезд: с петлёй 4,6 с, без — 4,0 с.
func secs() -> float:
	return float(_r.get("secs", 4.6)) if loop_name != "" else float(_r.get("secs_plain", 4.0))


func start(at: float) -> void:
	var n := hero_loop(art)
	loop_name = n if n != "" and not Settings.calm() and Frames.loop_ready(n) else ""
	t0 = at
	active = true
	drawn = 0


func riding() -> bool:
	return active and t - t0 < secs()


func _process(dt: float) -> void:
	t += dt
	if active:
		queue_redraw()
		_add.queue_redraw()


func anim_size(n: String) -> Vector2:
	var h := roundf(float(_r.get("height", 330)) * float(_r.get("scale", {}).get(n, 1.0)))
	return Vector2(roundf(h * float(_r.get("aspect", {}).get(n, 1.05))), h)


## [x, y, скорость 0..1, время петли] в момент проезда.
func _anim_state() -> Array:
	var T := secs()
	var p := float(_r.get("cruise", 0.6))
	var k := clampf((t - t0) / T, 0.0, 1.0)
	var dist := p + (1 - p) * 2 / PI
	var e: float
	var v: float
	if k < p:
		e = k / dist
		v = 1.0
	else:
		var u := (k - p) / (1 - p)
		e = (p + (1 - p) * 2 / PI * sin(PI / 2 * u)) / dist
		v = cos(PI / 2 * u)
	var sz := anim_size(loop_name)
	var x0 := -sz.x / 2
	var P := stop_x - x0
	var lp: Array = _r.get("loop", {}).get(loop_name, [12, 0.25, 2.4])
	var roll := float(lp[1]) * sz.y
	var peak := P / (dist * T)
	var tau := e * P / maxf(roll, peak / float(lp[2]))
	return [x0 + P * e - sz.x / 2, float(_r.get("floor", 534)) - sz.y, v, tau, float(lp[0])]


func _draw() -> void:
	if not active:
		return
	if loop_name != "":
		var s := _anim_state()
		var sz := anim_size(loop_name)
		var x: float = s[0]
		var y: float = s[1]
		var v: float = s[2]
		if v > 0.35:                                  # линии скорости — пока едет быстро
			for i in 6:
				var ly := y + sz.y * 0.3 + i * 26
				var ln := (60 + 40 * BgLayer._h01(i, 3)) * v
				var xe := x + sz.x * 0.08 - (20 * i) % 50
				draw_line(Vector2(xe - ln, ly), Vector2(xe, ly), Color8(200, 200, 210), 2.0)
		var tex := Frames.loop_frame(loop_name, s[3], s[4])
		if tex:
			draw_texture_rect(tex, UI.fit_rect(tex.get_size(), Rect2(roundf(x), y, sz.x, sz.y)), false)
			drawn += 1
		return
	var k := clampf((t - t0) / secs(), 0.0, 1.0)
	var e := k * k * (3 - 2 * k)
	var x := -260 + (UI.W + 520) * e
	var y := 290 - int(4 * absf(UI.wsin(t * 18)))
	for i in 6:
		var ly := y + 60 + i * 26
		var ln := 60 + 40 * BgLayer._h01(i, 3)
		var off := (20 * i) % 50
		draw_line(Vector2(x - 30 - ln - off, ly), Vector2(x - 30 - off, ly), Color8(200, 200, 210), 2.0)
	var tex := Content.texture(art)
	if tex:
		var r := UI.fit_rect(tex.get_size(), Rect2(x, y, 230, 250))
		var flip: bool = art in _r.get("flip", [])
		var mb := Vector2(x + 115, y + 250)           # покачивание -3° вокруг низа (blit_idle rock)
		draw_set_transform(mb, deg_to_rad(3), Vector2(-1 if flip else 1, 1))
		var lr := Rect2(r.position - mb, r.size)
		if flip:
			lr.position.x = -(r.end.x - mb.x)
		draw_texture_rect(tex, lr, false)
		draw_set_transform(Vector2.ZERO)
		drawn += 1


func _draw_add() -> void:
	if not active or not Settings.glow:
		return
	if loop_name != "":
		var s := _anim_state()
		var sz := anim_size(loop_name)
		var fl := float(_r.get("floor", 534))
		for i in 4:
			UI.draw_glow(_add, Vector2(float(s[0]) + sz.x * 0.3 - i * 30, fl - 6), 18, Color8(80, 70, 55), (0.7 - 0.15 * i) * float(s[2]))
		return
	var k := clampf((t - t0) / secs(), 0.0, 1.0)
	var e := k * k * (3 - 2 * k)
	var x := -260 + (UI.W + 520) * e
	var y := 290 - int(4 * absf(UI.wsin(t * 18)))
	for i in 4:
		UI.draw_glow(_add, Vector2(x + 40 - i * 30, y + 240), 18, Color8(80, 70, 55), 0.7 - 0.15 * i)
