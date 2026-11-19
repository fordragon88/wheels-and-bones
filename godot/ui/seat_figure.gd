class_name SeatFigure
extends Control
## Рисунок Кабинета посадки (поза → рисунок), общий для уроков, примерки и зачёта. Прямой порт рисования game.py:
## _draw_seat_scene_body (коляска сбоку, анатомический скелет: таз, позвонки, рёбра, лопатка, череп, бедро,
## надколенник, голень, стопа, рука), _draw_bone_seg (кость с эпифизами, светотенью и контуром), Мортимер с посохом и
## нитями к костям (_draw_necro_puppeteer/_draw_necro_thread), зоны давления с выносками, мерки урока, миф «90-90-90»
## (_draw_seat_909090_myth). Сам Control — рамка обрезки (clip_contents), рисунок — в экранных координатах.
## «Тело» клиента (_draw_seat_flesh, кукла) в игре выключено (SEAT_BODY_ON = False) — не переносится.
## Виды спереди (_seat_front_fit — примерка, _seat_front — урок и зачёт: дуга сколиоза, подкладка, три упора) и сверху
## (_seat_top — поворот таза).
## Сглаживание: кружки — draw_circle/draw_arc с antialiased, линии и контуры полигонов — draw_line с antialiased;
## заливки полигонов без сглаживания, но их край закрыт сглаженным контуром (как aa_* + DR.polygon в pygame).
## Свечение (add_glow) — аддитивным слоем; чтобы оно ложилось как в pygame (поверх того, что нарисовано раньше, и ПОД
## тем, что позже), рисунок делится на части: до первого свечения — в самом узле, после — в верхних слоях.
## Скорость (19.11): поза меняется редко (смена урока, ползунок, переход в зачёте), а «живой» только Мортимер (дыхание,
## посох, нити с искрой). Поэтому рисунок считается один раз при смене позы (_build) в списки команд по слоям, и слои
## перерисовываются только тогда; каждый кадр — лишь Мортимер (_n0/_n1) и свечение. Порядок слоёв = порядок рисования:
##   узел (до первого свечения) → _n0 (дыхание Мортимера, если свечений до него не было) → _add (свечение) →
##   _s1a (после свечения, до Мортимера) → _n1 (дыхание, если свечение было раньше, и нити) → _s1b (после Мортимера).

const BONE := Color8(234, 226, 206)
const BONE_D := Color8(186, 176, 154)
const BONE_SH := Color8(150, 140, 120)
const BONE_OUT := Color8(36, 30, 42)
const FR := Color8(82, 88, 104)
const UP := Color8(58, 66, 108)
const MET := Color8(178, 184, 198)
const TIRE := Color8(34, 36, 42)

var mode: String = "scene"                # scene | myth | puppet (итог зачёта: одна нить) | front_fit | top | front | none
var front_corrected: bool = false         # front (_seat_front): норма, упоры, перекос 0..1 (-1 — по норме), подкладка 0..1
var front_pads: bool = true
var front_obl: float = -1.0
var front_wedge: float = 0.0
var targets: Array = []                   # puppet: [x, y, цвет, активна]
var puppet_bad: bool = false
var rect: Rect2                           # рамка сцены (экранные координаты)
var case: Dictionary = {}
var cfg: Dictionary = {}
var pose: Dictionary = {}
var highlight: bool = true
var show_necro: bool = true
var t: float = 0.0
var _glows: Array = []                    # [центр, радиус, цвет, уровень] — неподвижные свечения (аддитивный слой)
var _add: Control
var _n0: Control
var _s1a: Control
var _n1: Control
var _s1b: Control
var _ops: Array = [[], [], []]            # команды рисования неподвижной части: узел, _s1a, _s1b
var _anim: Array = []                     # Мортимер: [рамка, цели нитей, «плохо», было ли свечение до него]
var _anim_ci: CanvasItem                  # рисуем «живое» прямо в этот слой (а не в список команд)
var _sig: Array = []
var _glowed: bool = false
var _necro_done: bool = false


func _init() -> void:
	clip_contents = true
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	name = "SeatFigure"


func _ready() -> void:
	_n0 = _layer("Necro0", _draw_n0)
	_add = _layer("Glow", _draw_glows)
	var mat := CanvasItemMaterial.new()
	mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	_add.material = mat
	_s1a = _layer("Late0", _draw_s1a)
	_n1 = _layer("Necro1", _draw_n1)
	_s1b = _layer("Late1", _draw_s1b)


func _layer(nm: String, fn: Callable) -> Control:
	var c := Control.new()
	c.name = nm
	c.size = size
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	c.draw.connect(fn)
	add_child(c)
	return c


## Рамка обрезки и сцены: clip — что видно, scene — где рисовать.
func place(clip: Rect2, scene: Rect2) -> void:
	position = clip.position
	size = clip.size
	if _add:
		for c: Control in [_n0, _add, _s1a, _n1, _s1b]:
			c.size = size
	rect = scene


func _process(dt: float) -> void:
	t += dt
	var sig := [mode, rect, position, size, case, cfg, pose, highlight, show_necro, front_corrected, front_pads, front_obl,
		front_wedge, targets, puppet_bad, Loc.code, Settings.glow, Settings.calm(), Settings.a11y.get("text", 0),
		Settings.easy_font()]
	var changed := sig != _sig
	if changed:
		var had := [not _ops[1].is_empty(), not _ops[2].is_empty()]
		_sig = sig.duplicate(true)
		_build()
		queue_redraw()
		if had[0] or not _ops[1].is_empty():
			_s1a.queue_redraw()
		if had[1] or not _ops[2].is_empty():
			_s1b.queue_redraw()
	if changed or (not _anim.is_empty() and not Settings.calm()):   # «Без анимации» — Мортимер тоже неподвижен
		_n0.queue_redraw()
		_add.queue_redraw()
		_n1.queue_redraw()


## Посчитать рисунок: команды неподвижной части по слоям, свечения, параметры Мортимера.
func _build() -> void:
	_ops = [[], [], []]
	_glows.clear()
	_anim = []
	_anim_ci = null
	_glowed = false
	_necro_done = false
	match mode:
		"scene":
			draw_scene(rect, case, cfg, pose, highlight, show_necro)
		"myth":
			draw_myth(rect)
		"puppet":
			necro_puppeteer(rect, targets, puppet_bad)
		"front_fit":
			draw_front_fit(rect, case, cfg, pose, show_necro)
		"top":
			draw_top(rect, case, cfg, pose, show_necro)
		"front":
			draw_front(rect, front_corrected, front_pads, front_obl, front_wedge)


func _draw() -> void:
	_replay(self, 0)


func _draw_s1a() -> void:
	_replay(_s1a, 1)


func _draw_s1b() -> void:
	_replay(_s1b, 2)


func _replay(ci: CanvasItem, seg: int) -> void:
	ci.draw_set_transform(-position)
	for o: Array in _ops[seg]:
		_emit(ci, o)


static func _emit(ci: CanvasItem, o: Array) -> void:
	match int(o[0]):
		0:
			ci.draw_line(o[1], o[2], o[3], o[4], true)
		1:
			ci.draw_polyline(o[1], o[2], 1.0, true)
		2:
			ci.draw_colored_polygon(o[1], o[2])
		3:
			ci.draw_circle(o[1], o[2], o[3], true, -1.0, true)
		4:
			ci.draw_arc(o[1], o[2], 0, TAU, o[3], o[4], o[5], true)
		5:
			UI.draw_round_rect(ci, o[1], o[2], o[3], o[4], o[5])
		6:
			UI.draw_text(ci, o[1], o[2], o[3], o[4], o[5], o[6])


func _draw_n0() -> void:
	if not _anim.is_empty() and not _anim[3]:
		_necro_live(_n0, false)


func _draw_n1() -> void:
	if not _anim.is_empty():
		_necro_live(_n1, true)


func _draw_glows() -> void:
	if not Settings.glow:
		return
	_add.draw_set_transform(-position)
	for g: Array in _glows:
		UI.draw_glow(_add, g[0], g[1], g[2], g[3])
	if not _anim.is_empty():                 # посох Мортимера пульсирует
		var g := _necro_geom(_anim[0])
		var pulse := 0.65 + 0.35 * UI.wsin(t * 4.5)
		UI.draw_glow(_add, g[4], int(20 * pulse), UI.PURPLE, 0.85)
		UI.draw_glow(_add, g[4], int(10 * pulse), UI.BAD if _anim[2] else UI.GHOST, 0.9)


# ---------------- примитивы как в pygame ----------------

## Толщина линии pygame: w пикселей по короткой оси (у косой линии поперёк — тоньше, до w·0,71 под 45°).
static func _pg_width(d: Vector2, w: float) -> float:
	var ln := d.length()
	if ln < 0.001 or w <= 1.0:
		return maxf(1.0, w)
	return maxf(1.0, w * maxf(absf(d.x), absf(d.y)) / ln)


## Команда рисования: «живое» (Мортимер) — сразу в слой, неподвижное — в список своего слоя (до первого свечения —
## узел, после — _s1a до Мортимера и _s1b после).
func _op(o: Array) -> void:
	if _anim_ci != null:
		_emit(_anim_ci, o)
		return
	_ops[0 if not _glowed else (2 if _necro_done else 1)].append(o)


func _line(a: Vector2, b: Vector2, col: Color, w: float) -> void:
	_op([0, a, b, col, _pg_width(b - a, w)])


func _lines(pts: Array, col: Color, w: float, closed: bool = false) -> void:
	var p := PackedVector2Array(pts)
	if closed:
		p.append(p[0])
	if w <= 1.0 or p.size() < 2:
		_op([1, p, col])
		return
	if _anim_ci != null:                      # нити Мортимера — каждый кадр, без списка команд
		for i in p.size() - 1:
			_anim_ci.draw_line(p[i], p[i + 1], col, _pg_width(p[i + 1] - p[i], w), true)
		return
	for i in p.size() - 1:                    # как DR.lines: каждый отрезок своей толщины
		_op([0, p[i], p[i + 1], col, _pg_width(p[i + 1] - p[i], w)])


func _poly(pts: Array, col: Color, outline_w: float = 0.0) -> void:
	if outline_w > 0:
		_lines(pts, col, outline_w, true)
	else:
		var p := PackedVector2Array(pts)
		if Geometry2D.triangulate_polygon(p).is_empty():
			return                             # вырожденный многоугольник — pygame его тоже не закрашивает
		_op([2, p, col])


func _circle(c: Vector2, r: float, col: Color, w: float = 0.0) -> void:
	if r <= 0:
		return
	if w <= 0 or w >= r:
		if _anim_ci != null:
			_anim_ci.draw_circle(c, r, col, true, -1.0, true)
			return
		_op([3, c, r, col])
	else:
		_op([4, c, r - w / 2.0, maxi(16, int(r * 2)), col, w])


func _glow(c: Vector2, r: float, col: Color, level: float) -> void:
	_glows.append([c, r, col, level])
	_glowed = true


func _rrect(r: Rect2, fill: Color, border: Color = Color(0, 0, 0, 0), width: int = 0, radius: int = 7) -> void:
	_op([5, r, fill, border, width, radius])


## aa_rect с дробными координатами: pygame.Rect отбрасывает дробную часть, радиус — не больше половины стороны.
func _aa_rect(x: float, y: float, w: float, h: float, col: Color, width: int = 0, radius: int = 0) -> void:
	var r := Rect2(int(x), int(y), int(w), int(h))
	if r.size.x <= 0 or r.size.y <= 0:
		return
	if width > 0:
		_rrect(r, Color(0, 0, 0, 0), col, width, radius)
	else:
		_rrect(r, col, Color(0, 0, 0, 0), 0, radius)


static func _layer_col(c: Color, a8: int) -> Color:
	var a := a8 / 255.0
	return Color(c.r * a, c.g * a, c.b * a, a)


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


## Мортимер слева с посохом-черепом и нитями к скелету (_draw_necro_puppeteer). Здесь — неподвижное (тень-круги)
## и запись для «живой» части (_necro_live): дыхание, посох со свечением, нити.
func necro_puppeteer(r: Rect2, targets_: Array, bad_flag: bool) -> void:
	var g := _necro_geom(r)
	var rc := Vector2(g[2] + int(g[1] / 2.0), r.end.y - 20)
	_ellipse(Rect2(rc.x - 54, rc.y - 9, 108, 18), Color8(68, 46, 98), 2)
	_ellipse(Rect2(rc.x - 38, rc.y - 5, 76, 10), Color8(118, 80, 166), 1)
	_anim = [r, targets_.duplicate(true), bad_flag, _glowed]
	_necro_done = true
	_glowed = true                            # свечение посоха — дальше всё поверх него


## [высота, ширина, x, y, посох] картинки Мортимера в рамке r (посох качается со временем).
func _necro_geom(r: Rect2) -> Array:
	var nh := mini(232, maxi(164, int(r.size.y * 0.65)))
	var nw := int(nh * 288 / 540.0)
	var nx := r.position.x + 8
	var ny := r.end.y - nh - 22
	var staff := Vector2(nx + int(nw * 0.14), ny + int(nh * 0.08) + int(3.0 * UI.wsin(t * 2.5)))
	return [nh, nw, nx, ny, staff]


## «Живой» Мортимер в слой ci: дыхание (в _n0 — если до него свечений не было, иначе в _n1) и нити (_n1).
func _necro_live(ci: CanvasItem, late: bool) -> void:
	ci.draw_set_transform(-position)
	var g := _necro_geom(_anim[0])
	var tex := Content.texture("mentor_necro.png")
	if tex and late == bool(_anim[3]):
		breathe(ci, tex, Rect2(g[2], g[3], g[1], g[0]), t, 0.0)
	if not late:
		return
	_anim_ci = ci
	var tg_all: Array = _anim[1]
	for i in tg_all.size():
		var tg: Array = tg_all[i]
		necro_thread(g[4], Vector2(tg[0], tg[1]), tg[2], tg[3], i * 1.3)
	_anim_ci = null


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


func _text(s: String, pos: Vector2, size_: float, col: Color, bold: bool = false, align: int = 0) -> void:
	_op([6, s, pos, size_, col, bold, align])


func _plate(r: Rect2) -> void:
	_rrect(r.grow_individual(8, 4, 8, 4), Color8(14, 12, 20, 175), Color(), 0, 8)


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
		_rrect(Rect2(p_b0, Vector2(bw, bh_px)), Color8(44, 46, 56), Color(), 0, maxi(4, int(6 * k)))
		_rrect(Rect2(p_b0 + Vector2(4, 3), Vector2(bw - 8, maxi(3, int(5 * k)))), Color8(112, 74, 156), Color(), 0, 3)
		_rrect(Rect2(p_b0, Vector2(bw, bh_px)), Color(0, 0, 0, 0), Color8(88, 92, 106), 2, maxi(4, int(6 * k)))
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
		# в pygame колесо рисуется на прозрачном слое и потом накладывается: на пустом месте цвет смешивается с
		# чёрным по своей прозрачности (c·a при прозрачности a) — спицы видны сквозь ступицу «звёздочкой»
		for a_sp in range(0, 360, 20):
			var ra := deg_to_rad(a_sp)
			_line(wc, wc + Vector2(cos(ra), sin(ra)) * (R - 3.5) * k, _layer_col(Color8(150, 158, 176), 95), 1)
		_circle(wc, int(R * k), _layer_col(TIRE, 155), maxf(2, int(3.2 * k)))
		_circle(wc, int((R - 4) * k), _layer_col(MET, 165), maxf(1, int(1.4 * k)))
		_circle(wc, maxf(3, int(3.5 * k)), _layer_col(MET, 210))
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
		_rrect(Rect2(rx + 134, ry + 10, sw + 12, UI.line_height(12, true) + 4), Color8(16, 12, 24, 225), Color(), 0, 4)
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
		_rrect(Rect2(lb[0] - int(tw / 2.0), lb[1] - int(lab_h / 2.0), tw, lab_h), Color8(16, 12, 24, 235), Color(), 0, 4)
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
		_rrect(sub, Color8(24, 26, 36), Color8(58, 66, 86), 1, 8)
		draw_scene(sub, presets[i][1], presets[i][2], {"p": 0, "slide": 0}, false, false)
		_text(Loc.t(presets[i][0]), Vector2(sub.get_center().x, sub.position.y + 10), 12, UI.CYAN, true, 1)
		targets.append([sub.get_center().x, sub.get_center().y - 20, UI.GHOST if i == 2 else UI.PURPLE, i == 1])
	necro_puppeteer(r, targets, false)


# ---------------- виды спереди и сверху ----------------

func _grid(r: Rect2) -> void:
	var gx := r.position.x + 20
	while gx < r.end.x - 10:
		_line(Vector2(gx, r.position.y + 8), Vector2(gx, r.end.y - 26), Color8(26, 29, 40), 1)
		gx += 36
	var gy := r.position.y + 16
	while gy < r.end.y - 26:
		_line(Vector2(r.position.x + 10, gy), Vector2(r.end.x - 10, gy), Color8(26, 29, 40), 1)
		gy += 36


## Вид спереди для примерки (_seat_front_fit): основа (гамак/жёсткая), ширина, две подножки, подкладка под седалищную
## кость; скелет с перекосом таза pose.obl, изгибом позвоночника и наклоном головы pose.lean.
func draw_front_fit(r: Rect2, case_: Dictionary, cfg_: Dictionary, pose_: Dictionary, show_necro_: bool) -> void:
	_grid(r)
	var BN := Color8(234, 226, 206)
	var BD := Color8(188, 178, 156)
	var OUT := Color8(38, 32, 44)
	var b: Dictionary = case_["body"]
	var fl := float(cfg_.get("foot_l", b["shank"]))
	var fr := float(cfg_.get("foot_r", b["shank"]))
	var s := (r.size.y - 34) / float(maxf(fl, fr) + float(b["shoulder"]) + 26)
	var cx := int(r.get_center().x) + (66 if show_necro_ else 0)
	var seat_y := r.end.y - 14 - maxf(fl, fr) * s
	var w := float(cfg_.get("seat_w", float(b["hip"]) + 1))
	var half := w * s / 2
	var sling := int(cfg_.get("base", 1)) == 0
	var sag := 3.0 * s if sling else 0.0
	var bh := (float(case_["back"][0]) + float(case_["back"][1])) / 2.0
	_aa_rect(cx - half, seat_y - bh * s - 6 * s, w * s, bh * s + 4 * s, Color8(44, 48, 72), 0, 10)
	_aa_rect(cx - half, seat_y - bh * s - 6 * s, w * s, bh * s + 4 * s, Color8(76, 84, 122), 2, 10)
	for sd: int in [-1, 1]:
		var wx := cx + sd * (half + 6 * s)
		_aa_rect(wx - 2.4 * s, seat_y - 34 * s, 4.8 * s, 62 * s, Color8(34, 36, 44), 0, 6)
		_aa_rect(wx - 0.9 * s, seat_y - 32 * s, 1.8 * s, 58 * s, Color8(168, 174, 188), 0, 3)
		_line(Vector2(cx + sd * half, seat_y - 2 * s), Vector2(cx + sd * half, seat_y + 20 * s), Color8(168, 174, 188),
			maxf(2, int(0.8 * s)))
	var base: Array = []
	for i in 13:
		base.append(Vector2(cx - half + (2 * half) * i / 12.0, seat_y + sag * sin(PI * i / 12.0)))
	var cush := 5 * s
	var top_pts: Array = []
	for p: Vector2 in base:
		top_pts.append(Vector2(p.x, p.y - cush))
	var rb := base.duplicate()
	rb.reverse()
	_poly(top_pts + rb, Color8(58, 66, 112))
	_poly(top_pts + rb, Color8(98, 110, 168), 2)
	_lines(base, Color8(130, 136, 156) if sling else Color8(210, 186, 130), maxf(3, int(1.0 * s)))
	if sling:
		_text(Loc.t("гамак провисает"), Vector2(cx + half + 10 * s, seat_y + sag - 6), 11, UI.AMBER, true)
	var bld := float(cfg_.get("build", 0))
	var it_dx := 7.5 * s
	if bld != 0:
		var sd := 1 if bld > 0 else -1
		var bx := cx + sd * it_dx
		var by_top := seat_y - cush - absf(bld) * s
		_aa_rect(bx - 5 * s, by_top, 10 * s, absf(bld) * s + 1, UI.CYAN, 0, 3)
		_aa_rect(bx - 5 * s, by_top, 10 * s, absf(bld) * s + 1, UI.WHITE, 1, 3)
	var obl := deg_to_rad(float(pose_.get("obl", 0.0)))
	var pc := Vector2(cx + float(pose_.get("shift", 0.0)) * s, seat_y - cush - 7 * s - sag * 0.5)
	var rp := func(dx: float, dy: float) -> Vector2:
		return Vector2(pc.x + dx * cos(-obl) - dy * sin(-obl), pc.y + dx * sin(-obl) + dy * cos(-obl))
	var ok: bool = pose_.get("ok", false)
	var p_col := UI.GOOD if ok else UI.AMBER
	var hw := float(b["hip"]) * 0.38 * s
	for sd: int in [-1, 1]:
		var wing := [rp.call(sd * 1.5 * s, -2 * s), rp.call(sd * hw * 0.55, -9 * s), rp.call(sd * hw * 1.05, -11 * s),
			rp.call(sd * hw * 1.12, -6 * s), rp.call(sd * hw * 0.7, 4 * s), rp.call(sd * 2 * s, 6 * s)]
		_poly(wing, BN)
		_poly(wing, OUT, 2)
		var fo: Vector2 = rp.call(sd * hw * 0.45, 1 * s)
		_circle(Vector2(int(fo.x), int(fo.y)), maxf(2, int(1.6 * s)), Color8(44, 48, 72))
	var sac := [rp.call(-3.5 * s, -9 * s), rp.call(3.5 * s, -9 * s), rp.call(0, 4 * s)]
	_poly(sac, BD)
	_poly(sac, OUT, 2)
	_line(rp.call(-hw * 1.05, -11 * s), rp.call(hw * 1.05, -11 * s), p_col, maxf(3, int(0.9 * s)))
	_line(Vector2(pc.x - hw * 1.3, pc.y - 11 * s), Vector2(pc.x + hw * 1.3, pc.y - 11 * s), Color8(96, 104, 132), 1)
	var ischia := {-1: rp.call(-it_dx, 6 * s), 1: rp.call(it_dx, 6 * s)}
	for leg: Array in [[-1, fl], [1, fr]]:
		var sd: int = leg[0]
		var foot: float = leg[1]
		var hp: Vector2 = rp.call(sd * hw * 0.85, 2 * s)
		var kx := cx + sd * (hw * 0.95)
		var ky := seat_y - cush + 1 * s
		var plate_y := seat_y + foot * s
		var ank := minf(plate_y - 1.2 * s, ky + float(b["shank"]) * s)
		bone_seg(hp, Vector2(kx, ky), 2.2 * s, 1.9 * s, BN, OUT)
		bone_seg(Vector2(kx, ky + 1 * s), Vector2(kx, ank), 1.7 * s, 1.4 * s, BN, OUT)
		_aa_rect(kx - 3 * s, ank - 0.6 * s, 6 * s, 2.4 * s, BN, 0, 3)
		_aa_rect(kx - 3 * s, ank - 0.6 * s, 6 * s, 2.4 * s, OUT, 1, 3)
		_aa_rect(kx - 6 * s, plate_y, 12 * s, 2.2 * s, Color8(96, 100, 116), 0, 2)
		if ank < plate_y - 2 * s:
			_line(Vector2(kx, ank + 2.5 * s), Vector2(kx, plate_y), UI.AMBER, 2)
	for sd: int in [-1, 1]:
		var over: bool = pose_.get("press_l" if sd < 0 else "press_r", false)
		var ip: Vector2 = ischia[sd]
		_circle(Vector2(int(ip.x), int(ip.y)), maxf(3, int(1.5 * s)), UI.BAD if over else UI.GOOD)
		if over:
			_glow(ip, int(7 * s), Color8(200, 40, 40), 0.85)
	var lean := float(pose_.get("lean", 0.0))
	var base_pt: Vector2 = rp.call(0, -9 * s)
	var sh_c := Vector2(cx + lean * 1.3 * s, seat_y - cush - float(b["shoulder"]) * 0.86 * s)
	var apex := Vector2(base_pt.x - sin(obl) * 22 * s + lean * 0.3 * s, (base_pt.y + sh_c.y) / 2)
	var spine: Array = []
	for i in 15:
		var tt := i / 14.0
		var u := 1 - tt
		spine.append(Vector2(u * u * base_pt.x + 2 * u * tt * apex.x + tt * tt * sh_c.x,
			u * u * base_pt.y + 2 * u * tt * apex.y + tt * tt * sh_c.y))
	_lines(spine, BD, maxf(3, int(1.4 * s)))
	var ri := 0
	for vi in range(6, 13):
		var rv: Vector2 = spine[vi]
		var rw := (11 - absi(ri - 3) * 1.2) * s
		for sd: int in [-1, 1]:
			var mid := Vector2(rv.x + sd * rw * 0.95, rv.y + 2.5 * s)
			var inn := Vector2(rv.x + sd * rw * 0.38, rv.y + 5.5 * s)
			_lines([rv, mid, inn], OUT, maxf(2, int(1.0 * s)))
			_lines([rv, mid, inn], BN, maxf(1, int(0.6 * s)))
		ri += 1
	for v: Vector2 in spine:
		var vc := Vector2(int(v.x), int(v.y))
		_circle(vc, maxf(3, int(1.3 * s)), BN)
		_circle(vc, maxf(3, int(1.3 * s)), OUT, 1)
	var tl := deg_to_rad(-lean * 1.1)
	var shl := Vector2(sh_c.x - 19 * s * cos(tl), sh_c.y - 19 * s * sin(tl))
	var shr := Vector2(sh_c.x + 19 * s * cos(tl), sh_c.y + 19 * s * sin(tl))
	bone_seg(Vector2(sh_c.x, sh_c.y + 1 * s), shl, 1.2 * s, 1.3 * s, BN, OUT)
	bone_seg(Vector2(sh_c.x, sh_c.y + 1 * s), shr, 1.2 * s, 1.3 * s, BN, OUT)
	for pr: Array in [[shl, -1], [shr, 1]]:
		var sp: Vector2 = pr[0]
		bone_seg(sp, Vector2(sp.x + pr[1] * 2 * s, sp.y + 26 * s), 1.5 * s, 1.2 * s, BD, OUT)
	var hx_ := sh_c.x + lean * 0.9 * s
	var hy_ := sh_c.y - 13 * s
	var hr := 8.5 * s
	var hc := Vector2(int(hx_), int(hy_))
	_circle(hc, int(hr), BN)
	_circle(hc, int(hr), OUT, 2)
	_aa_rect(hx_ - 4.5 * s, hy_ + 2.5 * s, 9 * s, 6.5 * s, BN, 0, 4)
	_aa_rect(hx_ - 4.5 * s, hy_ + 2.5 * s, 9 * s, 6.5 * s, OUT, 2, 4)
	for sd: int in [-1, 1]:
		var e := Vector2(int(hx_ + sd * 2.8 * s), int(hy_ - 0.5 * s))
		_circle(e, maxf(3, int(1.8 * s)), Color8(26, 22, 34))
		_circle(e, maxf(1, int(0.7 * s)), UI.GHOST)
	var gap := float(pose_.get("gap_cm", 0))
	if gap > 0.4:
		var sd: int = int(pose_.get("gap_side", 1))
		var gp: Vector2 = ischia[sd]
		_line(Vector2(gp.x, gp.y + 1.6 * s), Vector2(gp.x, seat_y - cush), UI.AMBER, 2)
		_text(Loc.t("зазор под костью %s см" % SeatLogic.fmt0(gap)), Vector2(gp.x + sd * 3 * s, gp.y + 2), 12, UI.AMBER, true,
			2 if sd < 0 else 0)
	var status := str(pose_.get("status", ""))
	if status != "":
		_text(Loc.t(status), Vector2(r.position.x + 150, r.position.y + 12), 12, UI.GOOD if ok else UI.AMBER, true)
	if show_necro_:
		var low := -1 if float(pose_.get("obl", 0)) >= 0 else 1
		var il: Vector2 = ischia[low]
		necro_puppeteer(r, [[hx_, hy_ - hr, UI.PURPLE, false], [apex.x, apex.y, UI.CYAN, false],
			[il.x, il.y, p_col, not ok]], not ok)
	_text(Loc.t("Вид спереди"), Vector2(r.end.x - 14, r.position.y + 12), 12, UI.GREY, true, 2)


## Вид сверху (_seat_top): сиденье (глубина слева и справа своя), спинка, колёса, таз и бёдра; pose.rot — поворот таза.
func draw_top(r: Rect2, case_: Dictionary, cfg_: Dictionary, pose_: Dictionary, show_necro_: bool) -> void:
	_grid(r)
	var BN := Color8(234, 226, 206)
	var BD := Color8(188, 178, 156)
	var OUT := Color8(38, 32, 44)
	var b: Dictionary = case_["body"]
	var cx := int(r.get_center().x) + (70 if show_necro_ else 0)
	var top := r.position.y + 64
	var s := (r.end.y - 36 - top) / 68.0
	var seat_w := float(cfg_.get("seat_w", float(b["hip"]) + 1))
	var dl := float(cfg_.get("depth_l", float(b["thigh"]) - 5))
	var dr := float(cfg_.get("depth_r", float(b["thigh"]) - 5))
	var half := seat_w * s / 2
	for sd: int in [-1, 1]:
		var wx := cx + sd * (half + 5 * s)
		_aa_rect(wx - 2.2 * s, top - 8 * s, 4.4 * s, 58 * s, Color8(34, 36, 44), 0, 6)
		_aa_rect(wx - 0.8 * s, top - 6 * s, 1.6 * s, 54 * s, Color8(150, 156, 170), 0, 3)
		_aa_rect(cx + sd * (half - 1 * s) - 1.6 * s, top + 52 * s, 3.2 * s, 7 * s, Color8(40, 42, 50), 0, 3)
	_aa_rect(cx - half - 2 * s, top - 8 * s, seat_w * s + 4 * s, 6 * s, Color8(52, 58, 92), 0, 5)
	_aa_rect(cx - half - 2 * s, top - 8 * s, seat_w * s + 4 * s, 6 * s, Color8(98, 110, 168), 2, 5)
	for pr: Array in [[-1, dl], [1, dr]]:
		var x0 := float(cx) if pr[0] > 0 else cx - half
		_aa_rect(x0, top - 2 * s, half, pr[1] * s, Color8(58, 66, 112), 0, 6)
		_aa_rect(x0, top - 2 * s, half, pr[1] * s, Color8(98, 110, 168), 2, 6)
	for sd: int in [-1, 1]:
		var fx := cx + sd * half * 0.5
		_aa_rect(fx - 6 * s, top + 58 * s, 12 * s, 5 * s, Color8(90, 94, 108), 0, 3)
	var rot := deg_to_rad(float(pose_.get("rot", 0.0)))
	var pc := Vector2(cx + float(pose_.get("shift", 0.0)) * s, top + 7 * s)
	var hip_hw := (float(b["hip"]) / 2 - 6) * s
	var rp := func(dx: float, dy: float) -> Vector2:
		return Vector2(pc.x + dx * cos(rot) - dy * sin(rot), pc.y + dx * sin(rot) + dy * cos(rot))
	var ok: bool = pose_.get("ok", false)
	var p_col := UI.GOOD if ok else UI.AMBER
	for sd: int in [-1, 1]:
		var crest: Array = []
		for tt: float in [0.0, 0.25, 0.5, 0.75, 1.0]:
			crest.append(rp.call(sd * (2 + 13 * tt) * s, (-6 + 9 * tt * tt) * s))
		_lines(crest, OUT, maxf(5, int(2.2 * s)))
		_lines(crest, BN, maxf(3, int(1.5 * s)))
	var sac := [rp.call(-3 * s, -6 * s), rp.call(3 * s, -6 * s), rp.call(0, 2 * s)]
	_poly(sac, BD)
	_poly(sac, OUT, 2)
	var hips := {-1: rp.call(-hip_hw, 3 * s), 1: rp.call(hip_hw, 3 * s)}
	_line(rp.call(-15 * s, 3 * s), rp.call(15 * s, 3 * s), p_col, maxf(3, int(0.6 * s)))
	var knees := {}
	var kp: Dictionary = pose_.get("knee_press", {})
	for sd: int in [-1, 1]:
		var L := (float(b.get("thigh_l" if sd < 0 else "thigh_r", b["thigh"])) - 7) * s
		var hp: Vector2 = hips[sd]
		knees[sd] = Vector2(hp.x, hp.y + L)
		var kk: Vector2 = knees[sd]
		bone_seg(hp, kk, 1.4 * s, 1.1 * s, BN, OUT)
		var kc := Vector2(int(kk.x), int(kk.y))
		_circle(kc, maxf(3, int(2.0 * s)), BN)
		_circle(kc, maxf(3, int(2.0 * s)), OUT, 2)
		if kp.get(sd, kp.get(str(sd), false)):
			_glow(Vector2(kk.x, kk.y - 1 * s), int(5 * s), Color8(200, 40, 40), 0.8)
	var sh_rot := rot * 0.6
	var shl := Vector2(cx - 18 * s * cos(sh_rot), top - 4 * s - 18 * s * sin(sh_rot))
	var shr := Vector2(cx + 18 * s * cos(sh_rot), top - 4 * s + 18 * s * sin(sh_rot))
	bone_seg(shl, shr, 1.1 * s, 1.1 * s, BD, OUT)
	var hcc := Vector2(int(cx), int(top - 4 * s))
	_circle(hcc, maxf(4, int(6 * s)), BN)
	_circle(hcc, maxf(4, int(6 * s)), OUT, 2)
	var kl: Vector2 = knees[-1]
	var kr: Vector2 = knees[1]
	var dk := (kl.y - kr.y) / s
	if absf(dk) >= 1:
		var fwd: Vector2 = kl if dk > 0 else kr
		var back: Vector2 = kr if dk > 0 else kl
		var lab := Loc.t(("левое колено впереди на %s см" if dk > 0 else "правое колено впереди на %s см") % SeatLogic.fmt0(absf(dk)))
		var ly := (back.y + fwd.y) / 2 - 8
		var xl := maxf(kl.x, kr.x) + 7 * s
		var lw := UI.text_width(lab, 12, true)
		var lh := UI.line_height(12, true)
		var left := xl + 2.5 * s + lw > r.end.x - 10
		if left:
			xl = minf(kl.x, kr.x) - 7 * s
		_line(Vector2(xl, back.y), Vector2(xl, fwd.y), UI.AMBER, 2)
		for yy: float in [back.y, fwd.y]:
			_line(Vector2(xl - 1.5 * s, yy), Vector2(xl + 1.5 * s, yy), UI.AMBER, 2)
		var lx: float
		if left:
			lx = (kl.x + kr.x) / 2 - lw / 2
			ly = fwd.y + 3 * s
		else:
			lx = xl + 2.5 * s
		_aa_rect(lx - 5, ly - 2, lw + 10, lh + 4, Color8(16, 12, 24, 220), 0, 4)
		_text(lab, Vector2(int(lx), int(ly)), 12, UI.AMBER, true)
	var status := str(pose_.get("status", ""))
	if status != "":
		_text(Loc.t(status), Vector2(r.position.x + 150, r.position.y + 12), 12, UI.GOOD if ok else UI.AMBER, true)
	if show_necro_:
		necro_puppeteer(r, [[kl.x, kl.y, p_col, not ok], [kr.x, kr.y, p_col, false], [pc.x, pc.y, UI.CYAN, false]], not ok)
	_text(Loc.t("Вид сверху"), Vector2(r.end.x - 14, r.position.y + 12), 12, UI.GREY, true, 2)


## Схема спереди урока и зачёта (_seat_front): перекос таза, дуга сколиоза, грудная клетка, череп, три точки боковой
## поддержки, Мортимер с нитями. obl — перекос 0..1 (меньше 0 — по corrected), wedge 0..1 — подкладка под высокую
## сторону без выпрямления таза (неисправимый перекос учитывают).
func draw_front(r: Rect2, corrected: bool, show_pads: bool, obl: float, wedge: float) -> void:
	_grid(r)
	var cx := r.get_center().x + 46
	var by := r.end.y - 56
	var k := r.size.y / 310.0
	var BN := Color8(234, 226, 206)
	var BD := Color8(188, 178, 156)
	var OUT := Color8(38, 32, 44)
	for sd: int in [-1, 1]:
		var wx := int(cx + sd * 124 * k)
		_aa_rect(wx - int(6 * k), by - int(78 * k), int(12 * k), int(112 * k), Color8(34, 36, 42), 0, 4)
		_aa_rect(wx - int(9 * k), by - int(72 * k), int(4 * k), int(98 * k), Color8(168, 174, 188), 0, 2)
	_aa_rect(cx - 96 * k, by - 236 * k, 192 * k, 228 * k, Color8(44, 48, 72), 0, 10)
	_aa_rect(cx - 96 * k, by - 236 * k, 192 * k, 228 * k, Color8(76, 84, 122), 2, 10)
	_aa_rect(cx - 106 * k, by - 14 * k, 212 * k, 22 * k, Color8(58, 66, 112), 0, 7)
	_aa_rect(cx - 106 * k, by - 14 * k, 212 * k, 22 * k, Color8(98, 110, 168), 2, 7)
	if obl < 0:
		obl = 0.12 if corrected else 1.0
	if wedge > 0.0:
		var wh := 13.0 * wedge
		var wpoly := [Vector2(cx + 4 * k, by - 14 * k), Vector2(cx + 100 * k, by - 14 * k), Vector2(cx + 100 * k, by - (14 + wh) * k),
			Vector2(cx + 4 * k, by - (14 + 2.0 * wedge) * k)]
		_poly(wpoly, Color8(70, 150, 110))
		_poly(wpoly, Color8(150, 230, 180), 2)
	var accom := wedge >= 0.5
	var pl := Vector2(cx - 58 * k, by - (36 - 8 * (1 - obl)) * k)
	var pr := Vector2(cx + 58 * k, by - (36 + 14 * obl) * k)
	var pel := Vector2((pl.x + pr.x) * 0.5, (pl.y + pr.y) * 0.5 + 8 * k)
	for pair: Array in [[-1, pl], [1, pr]]:
		var sd: int = pair[0]
		var pt: Vector2 = pair[1]
		var wing := [Vector2(pel.x + sd * 12 * k, pel.y - 6 * k), Vector2(pt.x - sd * 6 * k, pt.y - 12 * k),
			Vector2(pt.x + sd * 8 * k, pt.y + 2 * k), Vector2(pel.x + sd * 42 * k, pel.y + 16 * k),
			Vector2(pel.x + sd * 10 * k, pel.y + 18 * k)]
		_poly(wing, BN)
		_poly(wing, OUT, 2)
		var fo := Vector2(int(pel.x + sd * 24 * k), int(pel.y + 9 * k))
		_circle(fo, maxf(2, int(4.2 * k)), Color8(44, 48, 72))
		_circle(fo, maxf(2, int(4.2 * k)), OUT, 1)
	var sac := [Vector2(pel.x - 14 * k, pel.y - 10 * k), Vector2(pel.x + 14 * k, pel.y - 10 * k), Vector2(pel.x, pel.y + 14 * k)]
	_poly(sac, BD)
	_poly(sac, OUT, 2)
	var p_col := UI.GOOD if (corrected or accom) else UI.AMBER
	_line(pl, pr, p_col, maxf(3, int(4 * k)))
	_circle(Vector2(int(pl.x), int(pl.y)), 4, p_col)
	_circle(Vector2(int(pr.x), int(pr.y)), 4, p_col)
	var apex := Vector2(cx + 28 * k * obl, by - 114 * k)
	var sh_c := Vector2(cx - 8 * k * obl, by - 208 * k)
	var sp: Array = []
	for vi in 13:
		var tt := vi / 12.0
		var u := 1.0 - tt
		sp.append(Vector2(u * u * pel.x + 2 * u * tt * apex.x + tt * tt * sh_c.x,
			u * u * (pel.y - 8 * k) + 2 * u * tt * apex.y + tt * tt * sh_c.y))
	_lines(sp, BD, maxf(3, int(4.5 * k)))
	for v: Vector2 in sp:
		var vc := Vector2(int(v.x), int(v.y))
		_circle(vc, maxf(3, int(3.8 * k)), BN)
		_circle(vc, maxf(3, int(3.8 * k)), OUT, 1)
	var ri := 0
	for vi: int in [5, 6, 7, 8, 9, 10]:
		var rv: Vector2 = sp[vi]
		var rw := (46 - absf(ri - 2.5) * 5.5) * k
		var tilt_r := 0.16 * obl * (1.0 - 0.1 * ri)
		for sd: int in [-1, 1]:
			var mid := Vector2(rv.x + sd * rw * 0.95, rv.y + (sd * rw * tilt_r) + 6 * k)
			var inn := Vector2(rv.x + sd * rw * 0.38, rv.y + (sd * rw * tilt_r * 0.5) + 14 * k)
			_lines([rv, mid, inn], OUT, maxf(2, int(2.8 * k)))
			_lines([rv, mid, inn], BN, maxf(1, int(1.8 * k)))
		ri += 1
	var sh_l := Vector2(sh_c.x - 62 * k, sh_c.y + 6 * k * obl)
	var sh_r := Vector2(sh_c.x + 58 * k, sh_c.y - 8 * k * obl)
	bone_seg(Vector2(sh_c.x, sh_c.y + 4 * k), sh_l, 2.8 * k, 3.2 * k, BN, OUT)
	bone_seg(Vector2(sh_c.x, sh_c.y + 4 * k), sh_r, 2.8 * k, 3.2 * k, BN, OUT)
	for tr: Array in [[-1, sh_l, pl], [1, sh_r, pr]]:
		var sd: int = tr[0]
		var ssh: Vector2 = tr[1]
		var hip: Vector2 = tr[2]
		bone_seg(ssh, Vector2(ssh.x - sd * 6 * k, ssh.y + 68 * k), 3.2 * k, 2.8 * k, BD, OUT)
		bone_seg(Vector2(hip.x, hip.y + 10 * k), Vector2(hip.x + sd * 4 * k, by + 12 * k), 4.2 * k, 3.8 * k, BN, OUT)
	var hc := Vector2(int(sh_c.x - 3 * k * obl), int(sh_c.y - 34 * k))
	var hr := int(20 * k)
	_circle(hc, hr, BN)
	_circle(hc, hr, OUT, 2)
	_aa_rect(hc.x - int(11 * k), hc.y + int(6 * k), int(22 * k), int(16 * k), BN, 0, 5)
	_aa_rect(hc.x - int(11 * k), hc.y + int(6 * k), int(22 * k), int(16 * k), OUT, 2, 5)
	for sd: int in [-1, 1]:
		var e := Vector2(hc.x + int(sd * 6.5 * k), hc.y - int(1 * k))
		_circle(e, maxf(3, int(4.2 * k)), Color8(26, 22, 34))
		_circle(e, maxf(1, int(1.6 * k)), UI.GHOST)
	_poly([Vector2(hc.x, hc.y + int(3 * k)), Vector2(hc.x - int(2.5 * k), hc.y + int(8 * k)),
		Vector2(hc.x + int(2.5 * k), hc.y + int(8 * k))], Color8(26, 22, 34))
	var labels: Array = []
	if show_pads:
		var pads := [[Vector2(apex.x + 42 * k, apex.y), -1, "1. Вершина изгиба"],
			[Vector2(sh_l.x - 18 * k, by - 184 * k), 1, "2. Под мышкой (зазор)"],
			[Vector2(pl.x - 24 * k, by - 44 * k), 1, "3. Низко у таза"]]
		for pd: Array in pads:
			var pp: Vector2 = pd[0]
			var dir_s: int = pd[1]
			var pad_r := Rect2(int(pp.x - 8 * k), int(pp.y - 20 * k), int(16 * k), int(40 * k))
			_rrect(pad_r, UI.CYAN, Color(0, 0, 0, 0), 0, 5)
			_rrect(pad_r, Color(0, 0, 0, 0), UI.WHITE, 1, 5)
			_line(Vector2(pp.x - dir_s * 22 * k, pp.y), Vector2(pp.x - dir_s * 10 * k, pp.y), UI.GOOD, 2)
			var lw := UI.text_width(Loc.t(pd[2]), 12, true)
			var tx := pp.x + (16 if dir_s < 0 else -16) * k
			if dir_s > 0:
				tx = maxf(tx, r.position.x + 8 + lw)
			else:
				tx = minf(tx, r.end.x - 8 - lw)
			labels.append([tx, pp.y, lw, pd[2], dir_s])
	necro_puppeteer(r, [[hc.x, hc.y - hr, UI.PURPLE, false], [apex.x, apex.y, UI.GOOD if corrected else UI.CYAN, true],
		[pl.x, pl.y, p_col, not corrected], [sh_l.x, sh_l.y, UI.CYAN, false]], not (corrected or accom))
	if accom:
		labels.append([cx + 104 * k, by - 30 * k, UI.text_width(Loc.t("Подкладка"), 12, true), "Подкладка", -1])
	for lb: Array in labels:
		var x0: float = lb[0] - lb[2] if lb[4] > 0 else lb[0]
		_aa_rect(x0 - 4, lb[1] - 9, lb[2] + 8, 20, Color8(16, 12, 24, 215), 0, 4)
		_text(Loc.t(lb[3]), Vector2(int(lb[0]), int(lb[1] - 7)), 12, UI.CYAN, true, 2 if lb[4] > 0 else 0)
	var status := "Три точки держат ось позвоночника" if corrected else \
		("Подкладка заполнила зазор" if accom else "Таз перекошен → дуга сколиоза")
	_text(Loc.t(status), Vector2(r.position.x + 140, r.position.y + 12), 12, UI.GOOD if (corrected or accom) else UI.AMBER, true)
