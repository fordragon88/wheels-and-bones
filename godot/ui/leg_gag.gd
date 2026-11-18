class_name LegGag
extends Control
## Сценка с ногой Мартина (draw_leg_gag в game.py), ~4,6 с, один раз: drop — отваливается и уползает, peek —
## выглядывает из-под верстака, roll — пустая коляска катится, нога кувыркается следом, hop — упрыгивает.
## «Без анимации» — нет.

const P := 4.6

var kind: String = "drop"
var area: Rect2
var t: float = -1.0                        # время сценки (с начала); <0 — ещё не началась
var _add: Control


static func make(k: String, r: Rect2) -> LegGag:
	var g := LegGag.new()
	g.kind = k
	g.area = r
	return g


func _init() -> void:
	size = Vector2(UI.W, UI.H)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	name = "LegGag"


func _ready() -> void:
	_add = Control.new()
	_add.size = size
	_add.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var mat := CanvasItemMaterial.new()
	mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	_add.material = mat
	_add.draw.connect(_draw_add)
	add_child(_add)


func _process(_dt: float) -> void:
	queue_redraw()
	_add.queue_redraw()


func _leg(c: Vector2, ang: float = 0.0, scale: float = 1.0) -> void:
	var tex := Content.texture("gag_leg.png")
	if tex == null:
		return
	var r := UI.fit_rect(tex.get_size(), Rect2(-85, -35, 170, 70))
	draw_set_transform(c, deg_to_rad(-ang), Vector2(scale, scale))
	draw_texture_rect(tex, r, false)
	draw_set_transform(Vector2.ZERO)


func _draw() -> void:
	if Settings.calm() or t < 0.0 or t >= P:
		return
	var u := t
	var floor_ := area.end.y - 30
	var cx := area.get_center().x
	match kind:
		"drop":
			if u < 0.55:
				var k := u / 0.55
				_leg(Vector2(cx, area.position.y - 40 + (floor_ - area.position.y + 40) * k * k), -200 * k)
			elif u < 2.6:
				var v := u - 0.55
				var h := 70 * absf(sin(PI * v * 2.2)) * exp(-2.6 * v)
				_leg(Vector2(cx, floor_ - h), 12 * sin(v * 9) * exp(-2 * v))
			else:
				var k := UI.ease_out((u - 2.6) / 1.4)
				_leg(Vector2(cx + k * (area.size.x / 2 + 120), floor_ - 6 * absf(sin(u * 14))), 8 * sin(u * 14))
		"peek":
			var bench := Rect2(area.position.x, floor_ - 70, 260, 26)
			UI.draw_round_rect(self, bench, Color8(118, 82, 52), Color(), 0, 6)
			draw_rect(Rect2(bench.position.x + 20, bench.end.y, 16, 50), Color8(96, 66, 42))
			draw_rect(Rect2(bench.end.x - 36, bench.end.y, 16, 50), Color8(96, 66, 42))
			var out := 90 * clampf(sin(PI * clampf((u - 0.3) / 3.6, 0, 1)) * 1.4, 0, 1)
			_leg(Vector2(bench.end.x - 70 + out, floor_ - 10 + 4 * sin(u * 10)), 4 * sin(u * 7))
			UI.draw_text(self, "?" if u < 2.0 else "!", Vector2(bench.end.x + 40 + int(out), floor_ - 80 - int(6 * sin(u * 5))),
				34, Color(UI.AMBER, clampf((u - 0.6) / 0.3, 0, 1)), true, 1)
		"roll":
			var k := u / P
			var x := area.position.x - 160 + (area.size.x + 380) * k
			var chair := Content.texture("chair_basic.png")
			if chair:
				draw_texture_rect(chair, UI.fit_rect(chair.get_size(), Rect2(x - 65, floor_ + 18 - 103 - 2 * absf(sin(u * 12)), 130, 103)), false)
			_leg(Vector2(x - 170, floor_ - 14 - 8 * absf(sin(u * 6))), -u * 420, 0.6)
		"hop":
			var k := u / P
			var x := area.position.x - 100 + (area.size.x + 200) * k
			var ph := fmod(k * 6, 1.0)
			_leg(Vector2(x, floor_ - 22 - 40 * sin(PI * ph)), -90 + 20 * sin(PI * ph), 0.6)


func _draw_add() -> void:
	if Settings.calm() or t < 0.0 or t >= P or not Settings.glow:
		return
	var floor_ := area.end.y - 30
	if kind == "drop" and t >= 0.55 and t - 0.55 < 0.1:
		UI.draw_glow(_add, Vector2(area.get_center().x, floor_ + 18), 30, Color8(90, 80, 60), 0.8)
	elif kind == "roll":
		var x := area.position.x - 160 + (area.size.x + 380) * t / P
		for i in 3:
			UI.draw_glow(_add, Vector2(x - 70 - i * 18, floor_ + 14), 10, Color8(70, 62, 50), 0.6 - 0.18 * i)
	elif kind == "hop":
		var k := t / P
		if fmod(k * 6, 1.0) < 0.12:
			UI.draw_glow(_add, Vector2(area.position.x - 100 + (area.size.x + 200) * k, floor_ + 22), 22, Color8(90, 80, 60), 0.7)
