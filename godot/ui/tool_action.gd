class_name ToolAction
extends Control
## Инструмент работает на детали (draw_tool_action/_draw_action в game.py). Верный ход: замах → удар → миг паузы на
## детали (TOOL_WINDUP/STRIKE/HOLD), потом работа своим движением (ключ — дугой со стрелкой, насос качает, тряпка
## трёт, прибор — «✔ норма»…) и звуки работы. Ошибка: красный крест и отдёрнутый инструмент; с электрикой — разряд.
## «Без анимации» — не рисуется. Свечение — аддитивным слоем.

var tool: String = ""
var ok: bool = true
var zap: bool = false
var pos: Vector2
var t0: float = -99.0
var t: float = 0.0
var ticks: int = 0
var active: bool = false
var _add: Control
var _tm: Dictionary = {}


func _init() -> void:
	size = Vector2(UI.W, UI.H)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	name = "ToolAction"


func _ready() -> void:
	_tm = Content.consts.get("tool_timing", {"windup": 0.13, "strike": 0.05, "hold": 0.07, "ok_secs": 1.25})
	_add = Control.new()
	_add.size = size
	_add.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var mat := CanvasItemMaterial.new()
	mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	_add.material = mat
	_add.draw.connect(_draw_add)
	add_child(_add)


func start(tid: String, is_ok: bool, at: Vector2, part: String = "") -> void:
	tool = tid
	ok = is_ok
	pos = at
	t0 = t
	ticks = 0
	zap = not is_ok and part in Content.consts.get("electric_parts", [])
	active = true
	if zap:
		Audio.sfx("zap")


func pre() -> float:
	return float(_tm["windup"]) + float(_tm["strike"]) + float(_tm["hold"])


func dur() -> float:
	return float(_tm["ok_secs"]) if ok else (0.75 if zap else 0.6)


func _u() -> float:
	return (t - t0) / dur()


func _process(dt: float) -> void:
	t += dt
	if not active:
		return
	if Settings.calm() or _u() >= 1.0:
		active = false
		queue_redraw()
		_add.queue_redraw()
		return
	var u := _u()
	if ok and u >= pre():                          # звук работы — после замаха, по ходу работы
		var n := int((u - pre()) / (1 - pre()) * 6)
		if n > ticks:
			ticks = n
			if tool in Content.consts.get("rot_tools", []):
				Audio.sfx("ratchet")
			elif tool == "pump" and n % 2 == 0:
				Audio.sfx("hiss")
			elif tool == "pencil" and (n == 2 or n == 5):
				Audio.sfx("ping")
	queue_redraw()
	_add.queue_redraw()


func _icon(c: Vector2, sz: float, ang_deg: float, scale: float, alpha: float = 1.0) -> void:
	var tex := Content.texture("tool_%s.png" % tool)
	if tex == null:
		return
	draw_set_transform(c, deg_to_rad(-ang_deg), Vector2(scale, scale))
	draw_texture_rect(tex, UI.fit_rect(tex.get_size(), Rect2(-sz / 2, -sz / 2, sz, sz)), false, Color(1, 1, 1, alpha))
	draw_set_transform(Vector2.ZERO)


static func _bolt(a: Vector2, b: Vector2, seed_: int, rough: float = 0.22, n: int = 9) -> PackedVector2Array:
	var rnd := RandomNumberGenerator.new()
	rnd.seed = seed_
	var d := b - a
	var ln := maxf(1.0, d.length())
	var nrm := Vector2(-d.y, d.x) / ln
	var pts := PackedVector2Array([a])
	for i in range(1, n):
		var k := float(i) / n
		var off := (rnd.randf() - 0.5) * 2 * rough * ln * (1 - absf(0.5 - k))
		pts.append(a + d * k + nrm * off)
	pts.append(b)
	return pts


func _draw() -> void:
	if not active or Settings.calm():
		return
	var u := clampf(_u(), 0.0, 1.0)
	var x := pos.x
	var y := pos.y
	if not ok and zap:                             # разряд: молнии, инструмент отбрасывает
		var fade := 1 - u
		var seed_ := int(u * 14)
		var srcs := [Vector2(-55, -95), Vector2(40, -100)]
		for j in srcs.size():
			var pts := _bolt(pos + srcs[j], pos, seed_ * 7 + j, 0.25)
			var w := maxf(2, int(5 * fade))
			draw_polyline(pts, Color8(120, 190, 255), w + 4, true)
			draw_polyline(pts, Color8(240, 250, 255), maxf(1, int(w / 2.0) + 1), true)
		var rnd := RandomNumberGenerator.new()
		rnd.seed = seed_ + 99
		for i in 8:
			var ang := rnd.randf() * TAU
			var dd := (10 + 40 * u) * (0.6 + rnd.randf() * 0.8)
			draw_circle(pos + Vector2(dd * cos(ang), dd * sin(ang) + 30 * u * u),
				maxf(1, int(2.5 * fade)), Color8(255, 240, 170) if i % 2 else Color8(190, 225, 255), true, -1, true)
		_icon(Vector2(x + 30 + 50 * u, y - 30 - 40 * u), 40, 60 * u + 25, 1.0, 1 - u)
		return
	if not ok:                                     # ошибка: красный крест, инструмент отдёрнут
		var sh := 10 * sin(u * 40) * (1 - u)
		draw_line(Vector2(x - 14 + sh, y - 14), Vector2(x + 14 + sh, y + 14), UI.BAD, 5, true)
		draw_line(Vector2(x + 14 + sh, y - 14), Vector2(x - 14 + sh, y + 14), UI.BAD, 5, true)
		_icon(Vector2(x + 30, y - 30 - 20 * u), 40, 25 * (1 - u), 1.0, 1 - u)
		return
	var p := pre()
	if u < p:                                      # замах → удар → пауза на детали
		var soft: bool = tool in Content.consts.get("read_tools", []) or tool in ["hands", "pencil"]
		var amp := 0.45 if soft else 1.0
		var w_ := float(_tm["windup"]) / p
		var s_ := (float(_tm["windup"]) + float(_tm["strike"])) / p
		var k := u / p
		var off: float
		var rot: float
		var sc: float
		if k < w_:
			var b := UI.ease_out(k / w_)
			off = b
			rot = 22 * b
			sc = 0.6 + 0.5 * UI.ease_back(k / w_)
		elif k < s_:
			var b := (k - w_) / (s_ - w_)
			off = 1 - b * b
			rot = 22 * (1 - b * b) - 10 * b
			sc = 1.1
		else:
			var b := (k - s_) / (1 - s_)
			off = 0.0
			rot = -10 * (1 - b)
			sc = 1.0 - 0.1 * (1 - b)
			if not soft:
				UI.draw_ring(self, pos, 8 + 14 * b, Color8(255, 240, 200), 2)
		_icon(Vector2(int(x + 30 * off * amp), int(y - 4 - 34 * off * amp)), 46, rot * amp, maxf(0.01, sc))
		return
	u = (u - p) / (1 - p)                          # работа инструмента на месте
	var ak := UI.ease_out(u / 0.12)
	var ang := 0.0
	var dx := 0.0
	var dy := 0.0
	var scl := 1.0
	if tool in Content.consts.get("rot_tools", []):
		ang = 80 * sin(u * PI * 3)
		var a1 := -PI / 2
		var a2 := a1 + TAU * minf(1.0, u * 1.2)
		if a2 > a1 + 0.1:
			draw_arc(pos, 26, a1, a2, 32, UI.AMBER, 3, true)
	elif tool == "pump":
		dy = -18 * absf(sin(u * PI * 3))
	elif tool == "lever":
		ang = -38 * absf(sin(u * PI * 2))
		dx = 10
	elif tool == "cloth":
		dx = 22 * sin(u * PI * 6)
	elif tool == "brush":
		dx = 8 * sin(u * 60)
		for i in 5:
			var a := i * 1.3 + u * 6
			draw_circle(pos + Vector2(30 * u * cos(a), 30 * u * sin(a)), 3, Color8(140, 110, 80), true, -1, true)
	elif tool == "lube":
		ang = 40
		for i in 3:
			draw_circle(Vector2(x - 6, y + 4 + fmod(u * 3 + i / 3.0, 1.0) * 30), 3, Color8(226, 180, 70), true, -1, true)
	elif tool == "patch":
		scl = 1.6 - 0.6 * UI.ease_out(u / 0.4)
	elif tool == "bucket":
		for i in 6:
			var bu := fmod(u * 1.5 + i / 6.0, 1.0)
			UI.draw_ring(self, Vector2(x - 15 + 30 * BgLayer._h01(i, 7), y - 10 - 40 * bu), 3 + i % 3, Color8(170, 220, 250), 1)
	elif tool == "pencil":
		dy = -10 * absf(sin(u * PI * 2))
		UI.draw_ring(self, pos, 10 + 40 * fmod(u * 2, 1.0), UI.CYAN, 2)
	elif tool in Content.consts.get("read_tools", []):
		var lbl := Loc.t("✔ норма")
		var bw := maxf(86, UI.text_width(lbl, 14, true) + 20)
		var bx := x + 24 if x + 24 + bw <= UI.W - 8 else x - 24 - bw
		var bub := Rect2(bx, maxf(58, y - 54), bw, 26)
		UI.draw_round_rect(self, bub, Color8(20, 40, 30), UI.GOOD, 2, 8)
		UI.draw_text(self, lbl, bub.get_center(), 14, Color(UI.GOOD, clampf((u - 0.3) / 0.2, 0, 1)), true, 1)
		ang = 15 * sin(u * 20) * (1 - u)
	elif tool != "charger":
		dx = 6 * sin(u * 30) * (1 - u)
	_icon(Vector2(int(x + dx * ak), int(y + dy * ak - 4)), 46, ang * ak, maxf(0.01, 1.0 + (scl - 1.0) * ak),
		1.0 - (u - 0.8) / 0.2 if u > 0.8 else 1.0)


func _draw_add() -> void:
	if not active or Settings.calm() or not Settings.glow:
		return
	var u := clampf(_u(), 0.0, 1.0)
	if not ok:
		if zap:
			UI.draw_glow(_add, pos, 46, Color8(90, 150, 255), 0.9 * (1 - u))
		return
	var p := pre()
	if u < p:
		var s_ := (float(_tm["windup"]) + float(_tm["strike"])) / p
		var k := u / p
		var soft: bool = tool in Content.consts.get("read_tools", []) or tool in ["hands", "pencil"]
		if k >= s_ and not soft:
			UI.draw_glow(_add, pos, 26, Color8(255, 220, 150), 0.7 * (1 - (k - s_) / (1 - s_)))
		return
	u = (u - p) / (1 - p)
	if tool == "pump" and sin(u * PI * 3) > 0.9:
		UI.draw_glow(_add, pos + Vector2(24, 10), 16, Color8(200, 220, 240), 0.8)
	elif tool == "cloth" and u > 0.6:
		for i in 3:
			UI.draw_glow(_add, pos + Vector2(-20 + i * 20, -18 + 10 * sin(u * 9 + i)), 8, Color8(255, 255, 230), 1 - u)
	elif tool == "patch" and u > 0.4:
		UI.draw_glow(_add, pos, 30, Color8(120, 200, 140), 1 - (u - 0.4) / 0.6)
	elif tool == "charger":
		UI.draw_glow(_add, pos, 34, Color8(120, 200, 255), 0.5 + 0.5 * sin(u * 30))
