class_name SeatFigure
extends Control
## Рисунок Кабинета посадки (поза → рисунок), общий для уроков, примерки и зачёта. Прямой порт рисования game.py:
## _draw_seat_scene_body (коляска сбоку, анатомический скелет: таз, позвонки, рёбра, лопатка, череп, бедро,
## надколенник, голень, стопа, рука), _draw_bone_seg (кость с эпифизами, светотенью и контуром), Мортимер с посохом и
## нитями к костям (_draw_necro_puppeteer/_draw_necro_thread), зоны давления с выносками, мерки урока, миф «90-90-90»
## (_draw_seat_909090_myth). Сам Control — рамка обрезки (clip_contents), рисунок — в экранных координатах.
## «Тело» клиента (_draw_seat_flesh, кукла) в игре выключено (SEAT_BODY_ON = False) — не переносится.
## Сглаживание: кружки — draw_circle/draw_arc с antialiased, линии и контуры полигонов — draw_polyline с antialiased;
## заливки полигонов без сглаживания, но их край закрыт сглаженным контуром (как aa_* + DR.polygon в pygame).

const BONE := Color8(234, 226, 206)
const BONE_D := Color8(186, 176, 154)
const BONE_SH := Color8(150, 140, 120)
const BONE_OUT := Color8(36, 30, 42)
const FR := Color8(82, 88, 104)
const UP := Color8(58, 66, 108)
const MET := Color8(178, 184, 198)
const TIRE := Color8(34, 36, 42)

var mode: String = "scene"                # scene | myth | puppet (итог зачёта: одна нить) | none
var targets: Array = []                   # puppet: [x, y, цвет, активна]
var puppet_bad: bool = false
var rect: Rect2                           # рамка сцены (экранные координаты)
var case: Dictionary = {}
var cfg: Dictionary = {}
var pose: Dictionary = {}
var highlight: bool = true
var show_necro: bool = true
var t: float = 0.0
var _glows: Array = []                    # [центр, радиус, цвет, уровень] — аддитивным слоем
var _add: Control
var _ci: CanvasItem


func _init() -> void:
	clip_contents = true
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	name = "SeatFigure"


func _ready() -> void:
	_add = Control.new()
	_add.size = size
	_add.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var mat := CanvasItemMaterial.new()
	mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	_add.material = mat
	_add.draw.connect(_draw_glows)
	add_child(_add)


## Рамка обрезки и сцены: clip — что видно, scene — где рисовать.
func place(clip: Rect2, scene: Rect2) -> void:
	position = clip.position
	size = clip.size
	if _add:
		_add.size = size
	rect = scene


func _process(dt: float) -> void:
	t += dt
	queue_redraw()
	_add.queue_redraw()


func _draw() -> void:
	_glows.clear()
	_ci = self
	draw_set_transform(-position)
	match mode:
		"scene":
			draw_scene(rect, case, cfg, pose, highlight, show_necro)
		"myth":
			draw_myth(rect)
		"puppet":
			necro_puppeteer(rect, targets, puppet_bad)


func _draw_glows() -> void:
	if not Settings.glow:
		return
	_add.draw_set_transform(-position)
	for g: Array in _glows:
		UI.draw_glow(_add, g[0], g[1], g[2], g[3])


# ---------------- примитивы как в pygame ----------------

## Толщина линии pygame: w пикселей по короткой оси (у косой линии поперёк — тоньше, до w·0,71 под 45°).
static func _pg_width(d: Vector2, w: float) -> float:
	var ln := d.length()
	if ln < 0.001 or w <= 1.0:
		return maxf(1.0, w)
	return maxf(1.0, w * maxf(absf(d.x), absf(d.y)) / ln)


func _line(a: Vector2, b: Vector2, col: Color, w: float) -> void:
	_ci.draw_line(a, b, col, _pg_width(b - a, w), true)


func _lines(pts: Array, col: Color, w: float, closed: bool = false) -> void:
	var p := PackedVector2Array(pts)
	if closed:
		p.append(p[0])
	if w <= 1.0 or p.size() < 2:
		_ci.draw_polyline(p, col, 1.0, true)
		return
	for i in p.size() - 1:                    # как DR.lines: каждый отрезок своей толщины
		_ci.draw_line(p[i], p[i + 1], col, _pg_width(p[i + 1] - p[i], w), true)


func _poly(pts: Array, col: Color, outline_w: float = 0.0) -> void:
	if outline_w > 0:
		_lines(pts, col, outline_w, true)
	else:
		var p := PackedVector2Array(pts)
		if Geometry2D.triangulate_polygon(p).is_empty():
			return                             # вырожденный многоугольник — pygame его тоже не закрашивает
		_ci.draw_colored_polygon(p, col)


func _circle(c: Vector2, r: float, col: Color, w: float = 0.0) -> void:
	if r <= 0:
		return
	if w <= 0 or w >= r:
		_ci.draw_circle(c, r, col, true, -1.0, true)
	else:
		_ci.draw_arc(c, r - w / 2.0, 0, TAU, maxi(16, int(r * 2)), col, w, true)


func _glow(c: Vector2, r: float, col: Color, level: float) -> void:
	_glows.append([c, r, col, level])


static func _shade(c: Color, k: float) -> Color:
	return Color(c.r * k, c.g * k, c.b * k, c.a)


## Кость с утолщениями эпифизов, светотенью и контуром (_draw_bone_seg).
func bone_seg(p0: Vector2, p1: Vector2, r0: float, r1: float = -1.0, col: Color = Color8(232, 224, 204),
		outline: Color = Color8(36, 30, 42), joint: bool = true) -> void:
	if r1 < 0:
		r1 = r0
	var d := p1 - p0
	var L := d.length()
	if L < 1.0:
		return
	var u := d / L
	var n := Vector2(-u.y, u.x)
	var steps := [[0.0, 1.15], [0.14, 1.25], [0.30, 0.78], [0.50, 0.70], [0.70, 0.78], [0.86, 1.22], [1.0, 1.12]]
	var left: Array = []
	var right: Array = []
	var sh: Array = []
	var hi: Array = []
	for s: Array in steps:
		var tt: float = s[0]
		var c := p0 + d * tt
		var rw: float = (r0 * (1.0 - tt) + r1 * tt) * s[1]
		left.append(c + n * rw)
		right.append(c - n * rw)
		sh.append(c - n * rw * 0.25)
		hi.append(c + n * rw * 0.38)
	var rev := right.duplicate()
	rev.reverse()
	var poly := left + rev
	_poly(poly, col)
	_poly(sh + rev, _shade(col, 0.80))
	_poly(poly, outline, 2)
	_lines(hi, Color8(250, 246, 236), maxf(1, int(minf(r0, r1) * 0.45)))
	if joint:
		for j: Array in [[p0, r0 * 1.18], [p1, r1 * 1.15]]:
			var jc: Vector2 = Vector2(int(j[0].x), int(j[0].y))
			_circle(jc, maxf(2, int(j[1])), _shade(col, 0.86))
			_circle(Vector2(int(j[0].x - 0.5), int(j[0].y - 0.5)), maxf(1, int(j[1] * 0.78)), col)
			_circle(jc, maxf(2, int(j[1])), outline, 2)


## Нить от посоха Мортимера к кости (_draw_necro_thread).
func necro_thread(p_staff: Vector2, p_target: Vector2, col: Color, active: bool, phase: float) -> void:
	var m := Vector2((p_staff.x + p_target.x) * 0.5, minf(p_staff.y, p_target.y) - 26.0 - 9.0 * UI.wsin(t * 2.4 + phase))
	var pts: Array = []
	var n := 16
	for i in n + 1:
		var tt := float(i) / n
		var u := 1.0 - tt
		pts.append(Vector2(u * u * p_staff.x + 2 * u * tt * m.x + tt * tt * p_target.x,
			u * u * p_staff.y + 2 * u * tt * m.y + tt * tt * p_target.y + 3.2 * UI.wsin(tt * PI * 2 + t * 4.0 + phase)))
	var glow_c := col if active else Color8(152, 114, 218)
	_lines(pts, _shade(glow_c, 0.62), 3 if active else 2)
	_lines(pts, Color8(232, 210, 255) if active else glow_c, 1)
	if Settings.glow:                         # искра бежит по нити
		var us := 0.5 if Settings.calm() else fmod(t * 0.75 + phase * 0.23, 1.0)
		var p: Vector2 = pts[mini(n, int(us * n))]
		_circle(Vector2(int(p.x), int(p.y)), 3, UI.GHOST if not active else col)
	_circle(Vector2(int(p_target.x), int(p_target.y)), 4, glow_c)


func _ellipse(r: Rect2, col: Color, w: float) -> void:
	var pts: Array = []
	for i in 41:
		var a := TAU * i / 40.0
		pts.append(r.get_center() + Vector2(cos(a) * r.size.x / 2.0, sin(a) * r.size.y / 2.0))
	_lines(pts, col, w)


## Мортимер слева с посохом-черепом и нитями к скелету (_draw_necro_puppeteer).
func necro_puppeteer(r: Rect2, targets: Array, bad_flag: bool) -> void:
	var nh := mini(232, maxi(164, int(r.size.y * 0.65)))
	var nw := int(nh * 288 / 540.0)
	var nx := r.position.x + 8
	var ny := r.end.y - nh - 22
	var rc := Vector2(nx + int(nw / 2.0), r.end.y - 20)
	_ellipse(Rect2(rc.x - 54, rc.y - 9, 108, 18), Color8(68, 46, 98), 2)
	_ellipse(Rect2(rc.x - 38, rc.y - 5, 76, 10), Color8(118, 80, 166), 1)
	var tex := Content.texture("mentor_necro.png")
	if tex:
		breathe(_ci, tex, Rect2(nx, ny, nw, nh), t, 0.0)
	var staff := Vector2(nx + int(nw * 0.14), ny + int(nh * 0.08) + int(3.0 * UI.wsin(t * 2.5)))
	var pulse := 0.65 + 0.35 * UI.wsin(t * 4.5)
	_glow(staff, int(20 * pulse), UI.PURPLE, 0.85)
	_glow(staff, int(10 * pulse), UI.BAD if bad_flag else UI.GHOST, 0.9)
	for i in targets.size():
		var tg: Array = targets[i]
		necro_thread(staff, Vector2(tg[0], tg[1]), tg[2], tg[3], i * 1.3)


## Картинка, вписанная в бокс, «дышит» верхом (blit_idle breathe).
static func breathe(ci: CanvasItem, tex: Texture2D, box: Rect2, tt: float, phase: float) -> void:
	var r := UI.fit_rect(tex.get_size(), box)
	var sy := 1.0 + 0.014 * UI.wsin(tt * 2.1 + phase)
	if sy == 1.0:
		ci.draw_texture_rect(tex, r, false)
		return
	var ts := tex.get_size()
	var cut_tex := ts.y * 0.55
	var cut_y := r.position.y + r.size.y * 0.55
	ci.draw_texture_rect_region(tex, Rect2(r.position.x, cut_y, r.size.x, r.end.y - cut_y), Rect2(0, cut_tex, ts.x, ts.y - cut_tex))
	var top_h := (cut_y - r.position.y) * sy
	ci.draw_texture_rect_region(tex, Rect2(r.position.x, cut_y - top_h, r.size.x, top_h + 0.5), Rect2(0, 0, ts.x, cut_tex + 0.5))


func _text(s: String, pos: Vector2, size_: float, col: Color, bold: bool = false, align: int = 0) -> Rect2:
	return UI.draw_text(_ci, s, pos, size_, col, bold, align)


func _plate(r: Rect2) -> void:
	UI.draw_round_rect(_ci, r.grow_individual(8, 4, 8, 4), Color8(14, 12, 20, 175), Color(), 0, 8)


# ---------------- сцена сбоку ----------------

## Вид сбоку: коляска, скелет, Мортимер с нитями, зоны давления (_draw_seat_scene_body).
func draw_scene(rect_: Rect2, case_: Dictionary, cfg_: Dictionary, pose_: Dictionary, highlight_: bool,
		show_necro_: bool) -> void:
	var rx := rect_.position.x
	var ry := rect_.position.y
	var rr := rect_.end.x
	var rb := rect_.end.y
	var gx := rx + 20
	while gx < rr - 10:
		_line(Vector2(gx, ry + 8), Vector2(gx, rb - 26), Color8(26, 29, 40), 1)
		gx += 36
	var gy := ry + 16
	while gy < rb - 26:
		_line(Vector2(rx + 10, gy), Vector2(rr - 10, gy), Color8(26, 29, 40), 1)
		gy += 36
	var body: Dictionary = case_.get("body", {})
	var need_h := float(case_["seat_h"]) + float(body.get("shoulder", 60)) + 52
	var k := minf(rect_.size.x / 155.0, rect_.size.y / maxf(132.0, need_h))
	var floor_y := rb - 24
	var x_r := rx + rect_.size.x * (0.43 if show_necro_ else 0.36)
	var seat_h := float(case_["seat_h"])
	var depth := float(cfg_["depth"])
	var leg := float(cfg_["leg"])
	var tilt := deg_to_rad(float(cfg_.get("tilt", 0)))
	var piv := Vector2(depth * 0.45, -8.0)
	var fwd := 17.0 * sin(maxf(0.0, tilt))
	var T := func(px: float, py: float) -> Vector2:
		var dx := px - piv.x
		var dy := py - piv.y
		var qx := piv.x + dx * cos(tilt) - dy * sin(tilt) + fwd
		var qy := piv.y + dx * sin(tilt) + dy * cos(tilt)
		return Vector2(x_r + qx * k, floor_y - (seat_h + qy) * k)
	var W := func(px: float, py: float) -> Vector2:
		return Vector2(x_r + px * k, floor_y - py * k)

	_line(Vector2(rx + 10, floor_y), Vector2(rr - 10, floor_y), Color8(104, 96, 122), 3)
	for cm_x in range(-20, 90, 10):
		var px_tick: float = W.call(cm_x, 0).x
		if rx + 140 < px_tick and px_tick < rr - 16:
			_line(Vector2(px_tick, floor_y), Vector2(px_tick, floor_y + (5 if cm_x % 20 == 0 else 3)), Color8(74, 70, 90), 1)

	var ba := deg_to_rad(float(cfg_["back_a"]) - 90)
	var top := Vector2(-sin(ba) * float(cfg_["back_h"]), cos(ba) * float(cfg_["back_h"]))
	if case_["kind"] == "power":
		var p_b0: Vector2 = W.call(-16, 26)
		var bw := int((depth + 28) * k)
		var bh_px := int(18 * k)
		UI.draw_round_rect(_ci, Rect2(p_b0, Vector2(bw, bh_px)), Color8(44, 46, 56), Color(), 0, maxi(4, int(6 * k)))
		UI.draw_round_rect(_ci, Rect2(p_b0 + Vector2(4, 3), Vector2(bw - 8, maxi(3, int(5 * k)))), Color8(112, 74, 156), Color(), 0, 3)
		UI.draw_round_rect(_ci, Rect2(p_b0, Vector2(bw, bh_px)), Color(0, 0, 0, 0), Color8(88, 92, 106), 2, maxi(4, int(6 * k)))
		_line(W.call(depth * 0.45, 24), T.call(piv.x, piv.y), Color8(56, 60, 72), maxf(4, int(8 * k)))
		_line(W.call(depth * 0.45 - 3, 24), T.call(piv.x - 2, piv.y), MET, maxf(2, int(3 * k)))
		for cr: Array in [[-11.0, 8.5], [depth + 9, 8.5], [depth * 0.42, 16.5]]:
			var wc: Vector2 = W.call(cr[0], cr[1])
			_line(W.call(depth * 0.42, 18), wc, Color8(96, 100, 114), maxf(2, int(3 * k)))
			_circle(wc, int(cr[1] * k), TIRE)
			_circle(wc, int(cr[1] * k), Color8(64, 68, 78), 2)
			_circle(wc, int(cr[1] * k * 0.48), MET)
			_circle(wc, maxf(2, int(cr[1] * k * 0.18)), Color8(44, 46, 54))
	else:
		_lines([T.call(-2, -4), T.call(depth - 1, -4), W.call(depth + 3, 17), W.call(3, 19), T.call(-2, -4)], FR, maxf(2, int(3.2 * k)))
		var c_hub: Vector2 = W.call(depth + 4, 8)
		_line(W.call(depth + 3, 18), c_hub, MET, maxf(2, int(2.8 * k)))
		_circle(c_hub, int(8 * k), TIRE)
		_circle(c_hub, int(4.5 * k), MET)
		_circle(c_hub, maxf(2, int(2 * k)), Color8(40, 42, 50))

	var ub := Vector2(-sin(ba), cos(ba))
	var nb := Vector2(cos(ba), sin(ba))
	_line(T.call(-3, -4), T.call(top.x - 3 * nb.x, top.y - 3 * nb.y + 3), FR, maxf(2, int(3.2 * k)))
	_line(T.call(top.x - 3 * nb.x, top.y - 3 * nb.y + 2), T.call(top.x - 11 * nb.x, top.y - 11 * nb.y + 2), Color8(44, 46, 54), maxf(3, int(4.2 * k)))
	var b_pad := [T.call(-0.5, 1.0), T.call(top.x - 0.5 * nb.x, top.y - 0.5 * nb.y), T.call(top.x + 4.2 * nb.x, top.y + 4.2 * nb.y), T.call(4.2, 1.0)]
	_poly(b_pad, UP)
	_poly(b_pad, Color8(92, 102, 152), 2)
	if case_["kind"] == "power" or case_.get("tilt"):
		var hr0: Vector2 = T.call(top.x + 1.0 * nb.x, top.y + 1.0 * nb.y)
		var hr1: Vector2 = T.call(top.x + 8.0 * ub.x + 2.0 * nb.x, top.y + 8.0 * ub.y + 2.0 * nb.y)
		var hr2: Vector2 = T.call(top.x + 15.0 * ub.x + 4.5 * nb.x, top.y + 15.0 * ub.y + 4.5 * nb.y)
		_lines([hr0, hr1, hr2], FR, maxf(2, int(2.6 * k)))
		_line(T.call(top.x + 9.0 * ub.x + 4.5 * nb.x, top.y + 9.0 * ub.y + 4.5 * nb.y),
			T.call(top.x + 19.0 * ub.x + 4.5 * nb.x, top.y + 19.0 * ub.y + 4.5 * nb.y), UP, maxf(4, int(5.5 * k)))

	_line(T.call(-3, -4.5), T.call(depth, -4.5), FR, maxf(2, int(3.2 * k)))
	var c_pad := [T.call(0.5, -3.0), T.call(depth - 0.5, -3.0), T.call(depth - 0.5, 2.2), T.call(depth * 0.55, 1.6), T.call(0.5, 2.0)]
	_poly(c_pad, Color8(52, 60, 102))
	_poly(c_pad, Color8(96, 108, 162), 2)

	var fp := Vector2(depth + 0.26 * leg, -leg)
	_lines([T.call(depth - 1, -3.5), T.call(depth + 0.14 * leg, -leg * 0.45), T.call(fp.x, fp.y)], MET, maxf(2, int(2.8 * k)))
	var fp_p0: Vector2 = T.call(fp.x - 2, fp.y)
	var fp_p1: Vector2 = T.call(fp.x + 18, fp.y)
	_line(fp_p0, fp_p1, Color8(38, 40, 48), maxf(3, int(3.8 * k)))
	_line(fp_p0 - Vector2(0, 2), fp_p1 - Vector2(0, 2), MET, 1)
	var plate_cm := seat_h - leg - 1
	if absf(float(cfg_.get("tilt", 0))) < 5:
		var f_col := UI.BAD if plate_cm < 5 else Color8(110, 124, 146)
		_line(Vector2(fp_p1.x - 4, fp_p1.y + 2), Vector2(fp_p1.x - 4, floor_y - 2), f_col, 1)
		_text("%s %s" % [SeatLogic.fmt0(maxf(0, plate_cm)), Loc.t("см")],
			Vector2(fp_p1.x + 20, minf(floor_y - 14, (fp_p1.y + floor_y) * 0.5 - 6)), 11, f_col, false, 1)

	var b := body
	var slide := float(pose_.get("slide", 0))
	var pt := deg_to_rad(float(pose_.get("p", 0)))
	var hip := Vector2(slide + 10.0, 9.0 - slide * 0.25)
	var thigh := float(b["thigh"]) - 10.0
	var kb := maxf(0.0, float(b["shank"]) - leg)
	var th := asin(minf(0.75, kb / maxf(10.0, thigh))) if kb > 0.5 else -0.03
	var knee := Vector2(hip.x + thigh * cos(th), 5.0 + thigh * sin(th) + (hip.y - 9.0))
	var sole := knee.y - 5.0 - float(b["shank"])
	var ankle: Vector2
	var toe: Vector2
	var heel: Vector2
	if sole > -leg + 0.5:
		ankle = Vector2(knee.x + 2.0, sole + 3.0)
		toe = Vector2(ankle.x + 9.0, ankle.y - 7.5)
		heel = Vector2(ankle.x - 3.5, ankle.y - 1.5)
	else:
		ankle = Vector2(knee.x + 1.0, -leg + 3.5)
		toe = Vector2(ankle.x + 15.0, -leg + 1.2)
		heel = Vector2(ankle.x - 3.5, -leg + 1.2)
	var a1 := ba + pt
	var mid := Vector2(hip.x - sin(a1) * 20.0, hip.y + cos(a1) * 20.0)
	var a2 := a1 - pt * 2.3
	var tl_len := float(b["shoulder"]) - 24.0
	var sh := Vector2(mid.x - sin(a2) * tl_len, mid.y + cos(a2) * tl_len)
	var a3 := a2 - pt * 2.0
	var head := Vector2(sh.x - sin(a3) * 12.5 + 3.0, sh.y + cos(a3) * 12.5)
	var Tv := func(v: Vector2) -> Vector2: return T.call(v.x, v.y)

	var sacrum_base := Vector2(hip.x - 5.5 * cos(pt) - 2.0, hip.y - 4.0 * sin(pt) - 3.5)
	var spine: Array = []
	var n_vert := 13
	for vi in n_vert + 1:
		var tv := float(vi) / n_vert
		var vx: float
		var vy: float
		if tv < 0.45:
			var u := tv / 0.45
			vx = (1 - u) * sacrum_base.x + u * mid.x + 1.4 * sin(u * PI) * (1.0 - pt * 1.8)
			vy = (1 - u) * sacrum_base.y + u * mid.y
		else:
			var u := (tv - 0.45) / 0.55
			vx = (1 - u) * mid.x + u * sh.x - 2.2 * sin(u * PI) * (0.4 + pt * 1.6)
			vy = (1 - u) * mid.y + u * sh.y
		spine.append(Vector2(vx, vy))
	_lines(spine.map(func(q: Vector2) -> Vector2: return Tv.call(q)), BONE_D, maxf(3, int(3.8 * k)))
	for vi in spine.size() - 1:
		var pc: Vector2 = Tv.call(spine[vi])
		var pn: Vector2 = Tv.call(spine[vi + 1])
		var dv := pn - pc
		var lv := maxf(1.0, dv.length())
		var nv := Vector2(-dv.y / lv, dv.x / lv)
		var sp_len := maxf(3.0, (4.2 - 0.12 * vi) * k)
		_line(pc, pc - nv * sp_len, BONE, maxf(2, int(2.2 * k)))
		var vw := maxf(2, int((3.4 - 0.08 * vi) * k))
		var pci := Vector2(int(pc.x), int(pc.y))
		_circle(pci, vw, BONE)
		_circle(pci, vw, BONE_OUT, 1)
	var ri := 0
	for frac: float in [0.52, 0.62, 0.72, 0.82, 0.91]:
		var idx := mini(spine.size() - 1, int(frac * (spine.size() - 1)))
		var r0: Vector2 = spine[idx]
		var rib_w := 9.5 - absi(ri - 2) * 1.3
		var rib_end := Vector2(r0.x + rib_w * cos(a2 - 0.25), r0.y + rib_w * sin(a2 - 0.25) - 2.2)
		var rib_mid := Vector2((r0.x + rib_end.x) * 0.5 + 1.5, (r0.y + rib_end.y) * 0.5 - 1.8)
		var rib := [Tv.call(r0), Tv.call(rib_mid), Tv.call(rib_end)]
		_lines(rib, BONE_OUT, maxf(2, int(2.6 * k)))
		_lines(rib, BONE, maxf(1, int(1.6 * k)))
		ri += 1
	var scap_bot := Vector2(sh.x - 4.5 * cos(a2) + 6.0 * sin(a2), sh.y - 12.0 * cos(a2))
	var scap := [T.call(sh.x - 2.0, sh.y - 1.5), T.call(sh.x - 7.5, sh.y - 3.5), Tv.call(scap_bot)]
	_poly(scap, BONE_D)
	_poly(scap, BONE_OUT, 2)

	var ca_p := cos(-pt + 0.12)
	var sa_p := sin(-pt + 0.12)
	var TP := func(lx: float, ly: float) -> Vector2:
		return T.call(hip.x + lx * ca_p - ly * sa_p, hip.y + lx * sa_p + ly * ca_p)
	var pelvis := [TP.call(-7.5, 6.5), TP.call(-2.0, 10.5), TP.call(6.5, 7.5), TP.call(5.0, 1.5), TP.call(3.5, -5.5),
		TP.call(-2.5, -7.2), TP.call(-6.5, -2.5)]
	var fossa := [TP.call(-4.8, 5.5), TP.call(-1.2, 8.2), TP.call(4.2, 5.8), TP.call(1.5, 1.5)]
	var sacrum := [TP.call(-6.5, 6.0), TP.call(-9.5, 1.0), TP.call(-8.8, -5.2), TP.call(-5.5, -2.0)]
	_poly(sacrum, BONE_D)
	_poly(sacrum, BONE_OUT, 2)
	_poly(pelvis, BONE)
	_poly(fossa, BONE_SH)
	_poly(pelvis, BONE_OUT, 2)
	var ob: Vector2 = TP.call(0.5, -4.2)
	ob = Vector2(int(ob.x), int(ob.y))
	_circle(ob, maxf(2, int(1.9 * k)), Color8(38, 42, 64))
	_circle(ob, maxf(2, int(1.9 * k)), BONE_OUT, 1)
	var p_psis: Vector2 = TP.call(-7.2, 6.2)
	var p_asis: Vector2 = TP.call(6.2, 7.2)
	var pv := float(pose_.get("p", 0))
	var tilt_col := UI.BAD if pv > 12 else (UI.AMBER if pv > 5 else UI.GOOD)
	_line(p_psis, p_asis, tilt_col, maxf(2, int(2.6 * k)))
	_circle(Vector2(int(p_psis.x), int(p_psis.y)), 3, tilt_col)
	_circle(Vector2(int(p_asis.x), int(p_asis.y)), 3, tilt_col)

	bone_seg(Tv.call(hip), Tv.call(knee), maxf(3.5, 3.8 * k), maxf(3.2, 3.4 * k), BONE, BONE_OUT)
	var pat: Vector2 = T.call(knee.x + 2.8 * cos(th - 0.3), knee.y + 2.8 * sin(th - 0.3))
	pat = Vector2(int(pat.x), int(pat.y))
	_circle(pat, maxf(2, int(2.6 * k)), BONE)
	_circle(pat, maxf(2, int(2.6 * k)), BONE_OUT, 1)
	_line(T.call(knee.x - 1.8, knee.y - 1.5), T.call(ankle.x - 1.5, ankle.y + 1.0), BONE_D, maxf(2, int(2.2 * k)))
	bone_seg(Tv.call(knee), Tv.call(ankle), maxf(3.0, 3.2 * k), maxf(2.4, 2.5 * k), BONE, BONE_OUT)
	var foot := [Tv.call(ankle), Tv.call(heel), T.call(ankle.x + 4.0, toe.y), Tv.call(toe), T.call(ankle.x + 6.0, ankle.y - 1.0)]
	_poly(foot, BONE)
	_poly(foot, BONE_OUT, 2)

	var neck_top: Vector2 = T.call(head.x - 2.0 * cos(a3), head.y - 5.5)
	bone_seg(Tv.call(sh), neck_top, maxf(2.2, 2.4 * k), maxf(2.0, 2.2 * k), BONE_D, BONE_OUT, false)
	var hc: Vector2 = Tv.call(head)
	var hr_px := maxi(7, int(8.8 * k))
	var hcc := Vector2(int(hc.x - 1.5 * k), int(hc.y - 1.0 * k))
	_circle(hcc, hr_px, BONE)
	_circle(hcc, hr_px, BONE_OUT, 2)
	var jaw := [hc + Vector2(1.0, -2.0) * k, hc + Vector2(8.2, -1.0) * k, hc + Vector2(7.5, 5.8) * k, hc + Vector2(1.5, 7.2) * k,
		hc + Vector2(-3.0, 4.5) * k]
	_poly(jaw, BONE)
	_poly(jaw, BONE_OUT, 2)
	var eye := Vector2(int(hc.x + 4.2 * k), int(hc.y - 1.2 * k))
	_circle(eye, maxf(2, int(2.8 * k)), Color8(28, 22, 36))
	_circle(eye, maxf(1, int(1.3 * k)), UI.GHOST if pv <= 8 else UI.AMBER)
	_line(hc + Vector2(2.5, 3.6) * k, hc + Vector2(7.2, 3.4) * k, BONE_OUT, 1)

	var elbow := Vector2(sh.x + 5.0, sh.y - 24.0)
	var hand := Vector2(elbow.x + 21.0, elbow.y + 1.5)
	bone_seg(Tv.call(sh), Tv.call(elbow), maxf(2.6, 2.8 * k), maxf(2.2, 2.4 * k), BONE_D, BONE_OUT)
	bone_seg(Tv.call(elbow), Tv.call(hand), maxf(2.2, 2.4 * k), maxf(1.8, 2.0 * k), BONE, BONE_OUT)
	var hp: Vector2 = Tv.call(hand)
	var hpc := Vector2(int(hp.x + 3 * k), int(hp.y))
	_circle(hpc, maxf(2, int(2.4 * k)), BONE)
	_circle(hpc, maxf(2, int(2.4 * k)), BONE_OUT, 1)

	if case_["kind"] != "power":
		var R := 30.0 if seat_h > 45 else 26.0
		if case_.get("tilt"):
			var aa0: Vector2 = W.call(-4, 15)
			var aa1: Vector2 = W.call(-R - 6, 6.5)
			_line(aa0, aa1, FR, maxf(2, int(2.6 * k)))
			_circle(aa1, maxf(3, int(3.2 * k)), TIRE)
			_circle(aa1, maxf(1, int(1.4 * k)), MET)
		var wc: Vector2 = W.call(2, R)
		wc = Vector2(int(wc.x), int(wc.y))
		for a_sp in range(0, 360, 20):
			var ra := deg_to_rad(a_sp)
			_line(wc, wc + Vector2(cos(ra), sin(ra)) * (R - 3.5) * k, Color8(150, 158, 176, 95), 1)
		_circle(wc, int(R * k), Color(TIRE, 155 / 255.0), maxf(2, int(3.2 * k)))
		_circle(wc, int((R - 4) * k), Color(MET, 165 / 255.0), maxf(1, int(1.4 * k)))
		_circle(wc, maxf(3, int(3.5 * k)), Color(MET, 210 / 255.0))
	var has_bad: bool = pv > 8 or pose_.get("knee_up", false) or pose_.get("short", false) or pose_.get("deep", false) \
		or pose_.get("dangle", false)
	if show_necro_:
		var km: Vector2 = Tv.call(mid)
		var kk: Vector2 = Tv.call(knee)
		var ka: Vector2 = Tv.call(ankle)
		var bad_knee: bool = pose_.get("knee_up", false) or pose_.get("deep", false)
		var targets := [
			[hc.x, hc.y - hr_px, UI.PURPLE, false],
			[km.x, km.y, UI.AMBER if pv > 8 else UI.PURPLE, pv > 8],
			[p_psis.x, p_psis.y, tilt_col, pv > 8],
			[kk.x, kk.y, UI.BAD if bad_knee else UI.GHOST, bad_knee],
			[ka.x, ka.y, UI.BAD if pose_.get("dangle", false) else UI.PURPLE, bool(pose_.get("dangle", false))],
		]
		necro_puppeteer(rect_, targets, has_bad)
		var pt_deg := int(SeatLogic.fmt0(pv))
		var badge_col := UI.BAD if pt_deg > 12 else (UI.AMBER if pt_deg > 5 else UI.GOOD)
		var status := ("Завал таза назад: %d° (на крестце)" % pt_deg) if pt_deg > 5 else "Таз в нейтрали · позвоночник стабилен"
		if highlight_ and pose_.get("knee_up", false):
			status = "Подножка высоко: колени выше бёдер"
			badge_col = UI.BAD
		elif highlight_ and pose_.get("dangle", false):
			status = "Подножка низко: стопы не достают"
			badge_col = UI.BAD
		var st_t := Loc.t(status)
		var sw := UI.text_width(st_t, 12, true)
		UI.draw_round_rect(_ci, Rect2(rx + 134, ry + 10, sw + 12, UI.line_height(12, true) + 4), Color8(16, 12, 24, 225), Color(), 0, 4)
		_text(st_t, Vector2(rx + 140, ry + 12), 12, badge_col, true)

	if pose_.get("measure", false):               # урок «Мерки»: где меряют
		var MC := Color8(255, 200, 90)
		var MG := Color8(255, 120, 110)
		var labels: Array = []
		var dim := func(p0: Vector2, p1: Vector2, col: Color, label: String, lp: Vector2, right: bool) -> void:
			var q0: Vector2 = Tv.call(p0)
			var q1: Vector2 = Tv.call(p1)
			_line(q0, q1, col, 2)
			var dq := q1 - q0
			var ln := dq.length() if dq.length() > 0 else 1.0
			var o := Vector2(-dq.y / ln * 5, dq.x / ln * 5)
			for q: Vector2 in [q0, q1]:
				_line(q - o, q + o, col, 2)
			labels.append([label, Tv.call(lp), col, right])
		dim.call(Vector2(-15.0, 0.0), Vector2(-15.0, scap_bot.y), MC, "спинка", Vector2(-16.5, scap_bot.y + 3.0), true)
		var pop_x := knee.x - 3.0
		var y_th := hip.y + 8.0
		dim.call(Vector2(0.0, y_th), Vector2(pop_x, y_th), MC, "до подколенной ямки", Vector2(pop_x, y_th + 7.5), true)
		dim.call(Vector2(depth, -7.0), Vector2(pop_x, -7.0), MG, "−5 см", Vector2(pop_x + 2.0, -5.0), false)
		dim.call(Vector2(hand.x + 3.0, 2.0), Vector2(hand.x + 3.0, elbow.y - 1.5), MC, "локоть 90°", Vector2(hand.x + 5.0, elbow.y + 4.0), false)
		dim.call(Vector2(knee.x + 9.0, knee.y - 3.0), Vector2(knee.x + 9.0, -leg), MC, "голень", Vector2(knee.x + 11.0, (knee.y - leg) * 0.5), false)
		for lb: Array in labels:
			var s := Loc.t(lb[0])
			var w := UI.text_width(s, 12, true)
			var pos: Vector2 = lb[1]
			var tl := Vector2(pos.x - w, pos.y) if lb[3] else pos
			_plate(Rect2(tl, Vector2(w, UI.line_height(12, true))))
			_text(s, pos, 12, lb[2], true, 2 if lb[3] else 0)

	if not highlight_:
		return
	var zones: Array = []
	if pv > 8:
		zones.append([Vector2(hip.x - 6.5, 1.5), UI.BAD if pv > 14 else UI.AMBER, "крестец (риск пролежня)", -92, -42])
	if pose_.get("knee_up", false) or pose_.get("short", false):
		zones.append([Vector2(hip.x + 1.5, -0.5), UI.BAD, "седалищные бугры", -56, 24])
	if pose_.get("deep", false):
		zones.append([Vector2(depth - 1.0, 0.0), UI.BAD, "давление под коленями", 78, -26])
	if pose_.get("dangle", false):
		zones.append([Vector2(ankle.x + 4.0, ankle.y - 3.0), UI.AMBER, "стопы висят без опоры", 84, -30])
	var used: Array = []
	var lab_h := UI.line_height(12, true) + 4
	var labs: Array = []
	for z: Array in zones:
		var p_: Vector2 = Tv.call(z[0])
		var pi := Vector2(int(p_.x), int(p_.y))
		_glow(pi, int(10 * k), z[1], 0.9)
		_circle(pi, maxf(3, int(2.6 * k)), z[1])
		_circle(pi, maxf(4, int(4.2 * k)), UI.WHITE, 1)
		var lx := maxf(rx + 205, minf(rr - 95, int(p_.x + z[3])))
		var ly := maxf(ry + 48, minf(floor_y - 24, int(p_.y + z[4])))
		var sorted_used := used.duplicate()
		sorted_used.sort()
		for uy: float in sorted_used:
			if absf(ly - uy) < lab_h + 2:
				ly = minf(floor_y - 24, uy + lab_h + 3)
		used.append(ly)
		_line(pi, Vector2(lx, ly), z[1], 1)
		labs.append([lx, ly, z[2], z[1]])
	for lb: Array in labs:
		var s := Loc.t(lb[2])
		var tw := UI.text_width(s, 12, true) + 10
		UI.draw_round_rect(_ci, Rect2(lb[0] - int(tw / 2.0), lb[1] - int(lab_h / 2.0), tw, lab_h), Color8(16, 12, 24, 235), Color(), 0, 4)
		_text(s, Vector2(lb[0], lb[1]), 12, lb[3], true, 1)


## Миф «90-90-90»: Мортимер и три скелета с разной целью посадки (_draw_seat_909090_myth).
func draw_myth(r: Rect2) -> void:
	var gx := r.position.x + 20
	while gx < r.end.x - 10:
		_line(Vector2(gx, r.position.y + 8), Vector2(gx, r.end.y - 26), Color8(26, 29, 40), 1)
		gx += 36
	var myth := Loc.t("Мортимер: «Три скелета — три цели. Подойдёт ли им один шаблон?»")
	var msz := 14
	while msz > 11 and UI.text_width(myth, msz, true) > r.size.x - 60:
		msz -= 1
	_text(myth, Vector2(r.get_center().x + 20, r.position.y + 16), msz, UI.AMBER, true, 1)
	var presets := [
		["Активный толчок", {"seat_h": 48, "kind": "manual", "body": {"thigh": 45, "shank": 42, "scap": 35, "shoulder": 54}},
			{"depth": 40, "leg": 42, "back_h": 35, "back_a": 93, "tilt": 0}],
		["Комфорт и опора", {"seat_h": 49, "kind": "manual", "body": {"thigh": 47, "shank": 43, "scap": 40, "shoulder": 58}},
			{"depth": 42, "leg": 43, "back_h": 46, "back_a": 102, "tilt": 0}],
		["Разгрузка 45° Tilt", {"seat_h": 50, "kind": "power", "body": {"thigh": 48, "shank": 44, "scap": 43, "shoulder": 60}},
			{"depth": 43, "leg": 44, "back_h": 58, "back_a": 104, "tilt": 45}],
	]
	var w_sub := int((r.size.x - 150) / 3)
	var targets: Array = []
	for i in presets.size():
		var sub := Rect2(r.position.x + 142 + i * w_sub, r.position.y + 42, w_sub - 6, r.size.y - 68)
		UI.draw_round_rect(_ci, sub, Color8(24, 26, 36), Color8(58, 66, 86), 1, 8)
		draw_scene(sub, presets[i][1], presets[i][2], {"p": 0, "slide": 0}, false, false)
		_text(Loc.t(presets[i][0]), Vector2(sub.get_center().x, sub.position.y + 10), 12, UI.CYAN, true, 1)
		targets.append([sub.get_center().x, sub.get_center().y - 20, UI.GHOST if i == 2 else UI.PURPLE, i == 1])
	necro_puppeteer(r, targets, false)
