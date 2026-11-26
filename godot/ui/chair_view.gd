class_name ChairView
extends Control
## Коляска на кадрах поворота (Turntable + _draw_turntable + _m3d_spots из game.py): 36 кадров Blender, ближайший к
## ракурсу; масштаб, смещения кадров (offsets) и тень на полу — как у живой модели; кружки деталей считаются той же
## проекцией (project_point по centers/pivot модели). Вращение — перетаскиванием мышью/пальцем и ←/→ (когда коляска
## в фокусе), масштаб — колесом, кнопками +/− и клавишами +/−, сброс — правой кнопкой или R.
## Сам Control занимает прямоугольник коляски (_chair_rect); рисует шире (поля под поворот), координаты — экранные.

signal part_pressed(pid: String)

const PAD := 40.0                # модель может выходить за рамку
const WIDE := 1.18               # при повороте — шире окна на 18 %
const ZOOM := [0.75, 1.65, 1.10] # мин., макс., шаг масштаба

var art: String = ""
var parts: Array = []
var inspected: Dictionary = {}
var show_spots: bool = true
var pulse: bool = true           # кружки неосмотренных деталей «зовут» пульсом
var yaw: float = -0.75
var pitch: float = 0.26
var zoom_k: float = 1.0
var t0: float = 0.0              # начало вводного доворота (−1e9 — без него)
var t: float = 0.0
var drag: bool = false
var tt: Dictionary = {}          # запись turntable_index
var _last: Vector2
var _tick_yaw: float = 0.0
var _spots_key: String = ""
var _spots: Array = []           # [pid, x, y, r, ax, ay]
var _shadow_key: String = ""
var _shadow: Texture2D
var _buttons: Dictionary = {}    # pid → HotspotButton
var _inside: bool = false
var _sig: Array = []             # от чего зависит картинка: перерисовка только при смене (поворот, зум, кадр, наведение)


func setup(chair_art: String, part_ids: Array, rect: Rect2, inspected_set: Dictionary) -> void:
	art = chair_art
	parts = part_ids
	inspected = inspected_set
	position = rect.position
	size = rect.size
	tt = Frames.turntable(art)
	var m: Dictionary = Content.consts.get("m3d", {})
	yaw = float(m.get("yaw", -0.75))
	pitch = float(tt.get("pitch", m.get("pitch", 0.26)))
	t0 = 0.0
	name = "Chair"
	focus_mode = Control.FOCUS_ALL
	set_meta("kb_skip", true)                 # в списке клавиатуры game.py коляски нет (стрелки — по пунктам)
	mouse_filter = Control.MOUSE_FILTER_STOP
	mouse_default_cursor_shape = Control.CURSOR_DRAG
	accessibility_name = Loc.t("Коляска") + ". " + Loc.t("← → — повернуть, + − — масштаб")
	if not tt.is_empty():
		Frames.want_turntable(art, Frames.tt_index_for(art, view_yaw()))


func _ready() -> void:
	if show_spots:
		_make_buttons()
	mouse_entered.connect(func() -> void: _inside = true)
	mouse_exited.connect(func() -> void: _inside = false)


func has_frames() -> bool:
	return not tt.is_empty()


func _make_buttons() -> void:
	for pid: String in parts:
		if not tt.get("centers", {}).has(pid):
			continue
		var b := HotspotButton.new()
		b.pid = pid
		b.num = parts.find(pid) + 1
		b.view = self
		b.name = "Spot_" + pid
		b.pressed.connect(func() -> void: part_pressed.emit(pid))
		add_child(b)
		_buttons[pid] = b


func spot_button(pid: String) -> HotspotButton:
	return _buttons.get(pid)


## Ракурс: при открытии коляска плавно доворачивается к зрителю (1,1 с).
func view_yaw() -> float:
	var k := UI.ease_out(clampf((t - t0) / 1.1, 0.0, 1.0))
	return yaw - 1.3 * (1.0 - k)


func rect() -> Rect2:
	return Rect2(position, size)


## Прямоугольник проекции с полями и зум под него (кружки и картинка считаются одинаково).
func frame_and_zoom() -> Array:
	var r := rect()
	var ext := ceilf(r.size.x / 2.0 * (WIDE - 1.0))
	var fr := r.grow_individual(PAD + ext, PAD, PAD + ext, PAD)
	var z0 := float(tt.get("z0", 1.0))
	return [fr, z0 * zoom_k * r.size.y / (r.size.y + PAD * 2)]


## project_point из game.py: точка модели (мм) → экран; z — глубина (больше — ближе к зрителю).
static func project(p: Array, yw: float, pt: float, r: Rect2, zoom: float, center: Array) -> Vector3:
	var cy := cos(yw)
	var sy := sin(yw)
	var cp := cos(pt)
	var sp := sin(pt)
	var x := float(p[0]) - float(center[0])
	var y := float(p[1]) - float(center[1])
	var z := float(p[2]) - float(center[2])
	var X := x * cy + z * sy
	var Z := -x * sy + z * cy
	var Y := y * cp - Z * sp
	var Z2 := y * sp + Z * cp
	var k := 2600.0 / (2600.0 - Z2)
	var scale := r.size.y / 1250.0 * zoom
	return Vector3(r.position.x + r.size.x / 2.0 + X * k * scale, r.position.y + r.size.y * 0.54 - Y * k * scale, Z2)


func spot_radius() -> int:
	var r := clampi(int(size.y * 0.05), 17, 20)          # крупные кружки — под палец
	return int(clampf(r * zoom_k, 14, 30))


## Кружки деталей на модели: [[деталь, x, y, r, ax, ay]] (экранные). Пересекающиеся раздвигаются, скопления —
## веером вокруг центра, к детали ведёт выноска (_m3d_spots).
func spots() -> Array:
	var yw := view_yaw()
	var key := "%.4f|%.3f|%s|%s" % [yw, zoom_k, rect(), parts]
	if key == _spots_key:
		return _spots
	var fz := frame_and_zoom()
	var fr: Rect2 = fz[0]
	var zoom: float = fz[1]
	var rect_ := rect()
	var r := spot_radius()
	var centers: Dictionary = tt.get("centers", {})
	var pivot: Array = tt.get("pivot", [180, 470, 0])
	var pts: Array = []
	for pid: String in parts:
		var cs: Array = centers.get(pid, [])
		if cs.is_empty():
			continue
		var best: Array = cs[0]
		var best_y := -INF
		for c: Array in cs:                       # ближняя к низу экрана точка детали (как max по y)
			var q := project(c, yw, pitch, fr, zoom, pivot)
			if q.y > best_y:
				best_y = q.y
				best = c
		var p := project(best, yw, pitch, fr, zoom, pivot)
		pts.append([pid, p.x, p.y, p.x, p.y])
	var need := 2.0 * r + maxf(8, r)
	var groups: Array = []
	for p: Array in pts:
		var near: Array = []
		var rest: Array = []
		for g: Array in groups:
			var hit := false
			for q: Array in g:
				if Vector2(p[3] - q[3], p[4] - q[4]).length() < need:
					hit = true
					break
			if hit:
				near.append(g)
			else:
				rest.append(g)
		var merged: Array = [p]
		for g: Array in near:
			merged.append_array(g)
		rest.append(merged)
		groups = rest
	for g: Array in groups:
		var k := g.size()
		if k < 2:
			continue
		var cx := 0.0
		var cy := 0.0
		for q: Array in g:
			cx += q[3]
			cy += q[4]
		cx /= k
		cy /= k
		var rad := need / (2.0 * sin(PI / k)) + int(r / 2.0)
		g.sort_custom(func(a: Array, b: Array) -> bool: return atan2(a[4] - cy, a[3] - cx) < atan2(b[4] - cy, b[3] - cx))
		var a0 := atan2(g[0][4] - cy, g[0][3] - cx) if Vector2(g[0][3] - cx, g[0][4] - cy).length() > 1 else -PI / 2.0
		for i in k:
			g[i][1] = cx + rad * cos(a0 + TAU * i / k)
			g[i][2] = cy + rad * sin(a0 + TAU * i / k)
	for _it in 60:
		var moved := false
		for i in pts.size():
			for j in range(i + 1, pts.size()):
				var a: Array = pts[i]
				var b: Array = pts[j]
				var dx: float = b[1] - a[1]
				var dy: float = b[2] - a[2]
				var d := sqrt(dx * dx + dy * dy)
				if d >= need:
					continue
				if d < 0.01:
					dx = cos(i + j)
					dy = sin(i + j)
					d = 1.0
				var push := (need - d) / 2.0 + 0.5
				a[1] -= dx / d * push
				a[2] -= dy / d * push
				b[1] += dx / d * push
				b[2] += dy / d * push
				moved = true
		for q: Array in pts:
			q[1] = clampf(q[1], rect_.position.x + r, rect_.end.x - r)
			q[2] = clampf(q[2], rect_.position.y + r, rect_.end.y - r)
		if not moved:
			break
	_spots = []
	for q: Array in pts:
		_spots.append([q[0], int(q[1]), int(q[2]), r, int(q[3]), int(q[4])])
	_spots_key = key
	return _spots


## _hotspot_at из game.py: деталь под точкой p (координаты экрана задания): ближайший кружок, у которого
## расстояние до центра ≤ r + pad (выбор — по наименьшему d − r). Нет — "".
func hotspot_at(p: Vector2, pad: float) -> String:
	var best := ""
	var bd := INF
	for s: Array in spots():
		var d := p.distance_to(Vector2(s[1], s[2]))
		if d <= s[3] + pad and d - s[3] < bd:
			best = s[0]
			bd = d - s[3]
	return best


func spot_of(pid: String) -> Array:
	for s: Array in spots():
		if s[0] == pid:
			return s
	return []


func _process(dt: float) -> void:
	t += dt
	if show_spots:
		for s: Array in spots():
			var b: HotspotButton = _buttons.get(s[0])
			if b:
				b.r = s[3]
				b.size = Vector2(s[3] * 2 + 8, s[3] * 2 + 8)
				b.position = Vector2(s[1], s[2]) - position - b.size / 2.0
	var yw := view_yaw()
	var tex: Texture2D = null
	var n := int(tt.get("n", 0))
	if n > 0:
		var i := Frames.tt_index_for(art, yw)
		tex = Frames.tt_frame(art, i)
		if tex == null:
			tex = Frames.tt_frame(art, Frames.tt_nearest_index(art, i))
	var hov := false
	for b: HotspotButton in _buttons.values():
		if b.is_hovered():
			hov = true
	var sig := [yw, zoom_k, tex, position, size, drag, _mouse_inside(), hov, has_focus() and UI.kb_active, show_spots]
	if sig != _sig:
		_sig = sig
		queue_redraw()


func _draw() -> void:
	draw_set_transform(-position)            # дальше — экранные координаты
	var r := rect()
	var fz := frame_and_zoom()
	var fr: Rect2 = fz[0]
	var zoom: float = fz[1]
	var yw := view_yaw()
	var n := int(tt.get("n", 0))
	if n == 0:                                # нет кадров поворота — рисунок коляски
		var tex := Content.texture(art)
		if tex:
			draw_texture_rect(tex, UI.fit_rect(tex.get_size(), r), false)
		return
	var i := Frames.tt_index_for(art, yw)
	var tex := Frames.tt_frame(art, i)
	if tex == null:
		i = Frames.tt_nearest_index(art, i)
		tex = Frames.tt_frame(art, i)
	_draw_shadow(fr, zoom, i)
	if tex == null:                           # кадры ещё идут: рисунок — тот же ракурс, то же место
		var a := Content.texture(art)
		if a:
			draw_texture_rect(a, UI.fit_rect(a.get_size(), r), false)
	else:
		var scale := fr.size.y / 1250.0 * zoom
		var ax := fr.position.x + fr.size.x / 2.0
		var ay := fr.position.y + fr.size.y * 0.54
		var off: Array = tt["offsets"][i]
		var k := scale / float(tt["ref"])
		draw_texture_rect(tex, Rect2(Vector2(ax + float(off[0]) * scale, ay + float(off[1]) * scale), tex.get_size() * k), false)
	if show_spots:
		for s: Array in spots():               # выноска к детали и тёмная подложка под кружком
			var c := Vector2(s[1], s[2])
			var anc := Vector2(s[4], s[5])
			if absf(anc.x - c.x) + absf(anc.y - c.y) > s[3] * 0.6:
				draw_line(anc, c, UI.INK, 4.0, true)
				draw_line(anc, c, UI.AMBER, 2.0, true)
				draw_circle(anc, 5, UI.INK, true, -1, true)
				draw_circle(anc, 3, UI.AMBER, true, -1, true)
			draw_circle(c, s[3], Color8(12, 12, 18, 110), true, -1, true)
	var hovering_spot := false
	for b: HotspotButton in _buttons.values():
		if b.is_hovered():
			hovering_spot = true
	if not drag and _mouse_inside() and not hovering_spot:
		UI.draw_text(self, Loc.t("⟲ тяни — повернуть"), Vector2(r.position.x + 4, r.end.y - 18), 12, Color8(200, 196, 180))
	if has_focus() and UI.kb_active:
		UI.draw_round_rect(self, r.grow(2), Color(0, 0, 0, 0), UI.WHITE, 2, 10)


func _mouse_inside() -> bool:
	return _inside and Rect2(Vector2.ZERO, size).has_point(get_local_mouse_position())


## Мягкая тень на полу: четырёхугольник под колёсами, растр 1/10 и растяжение — размытие (как smoothscale).
func _draw_shadow(fr: Rect2, zoom: float, i: int) -> void:
	var key := "%d|%s|%.4f" % [i, fr, zoom]
	if key != _shadow_key:
		_shadow_key = key
		var n := int(tt["n"])
		var yw := float(tt["yaw0"]) + i * TAU / n
		var pivot: Array = tt["pivot"]
		var px := float(pivot[0])
		var loc := Rect2(Vector2.ZERO, fr.size)
		var poly := PackedVector2Array()
		for f: Array in [[-470, -310], [470, -310], [470, 310], [-470, 310]]:
			var q := project([px + f[0], 0, f[1]], yw, pitch, loc, zoom, pivot)
			poly.append(Vector2(q.x, q.y) / 10.0)
		var w := maxi(1, int(fr.size.x / 10))
		var h := maxi(1, int(fr.size.y / 10))
		var img := Image.create(w, h, false, Image.FORMAT_RGBA8)
		for y in h:
			for x in w:
				if Geometry2D.is_point_in_polygon(Vector2(x + 0.5, y + 0.5), poly):
					img.set_pixel(x, y, Color(0, 0, 0, 110.0 / 255.0))
		img.generate_mipmaps()
		_shadow = ImageTexture.create_from_image(img)
	draw_texture_rect(_shadow, fr, false)


func zoom(steps: int) -> bool:
	var old := zoom_k
	zoom_k = clampf(zoom_k * pow(ZOOM[2], steps), ZOOM[0], ZOOM[1])
	return zoom_k != old


func rotate_step(d: int) -> void:
	var n := maxi(1, int(tt.get("n", 36)))
	yaw = view_yaw() + d * TAU / n
	t0 = -1e9
	_ratchet()


func reset_view() -> void:
	var m: Dictionary = Content.consts.get("m3d", {})
	yaw = float(m.get("yaw", -0.75))
	zoom_k = 1.0
	t0 = -1e9
	drag = false


func _ratchet() -> void:
	if absf(yaw - _tick_yaw) > 0.35:
		_tick_yaw = yaw
		Audio.sfx("ratchet")


func _gui_input(e: InputEvent) -> void:
	if e is InputEventMouseButton:
		var mb := e as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_LEFT:
			if mb.pressed:
				yaw = view_yaw()                    # вводный поворот прерываем там, где он сейчас
				t0 = -1e9
				drag = true
				_last = mb.position
				_tick_yaw = yaw
			else:
				drag = false
			accept_event()
		elif mb.pressed and mb.button_index in [MOUSE_BUTTON_WHEEL_UP, MOUSE_BUTTON_WHEEL_DOWN]:
			zoom(1 if mb.button_index == MOUSE_BUTTON_WHEEL_UP else -1)
			accept_event()
		elif mb.pressed and mb.button_index == MOUSE_BUTTON_RIGHT:
			reset_view()
			Audio.sfx("tick")
			accept_event()
	elif e is InputEventMouseMotion and drag:
		var mm := e as InputEventMouseMotion
		yaw += (mm.position.x - _last.x) * 0.012
		_last = mm.position
		_ratchet()
		accept_event()
	elif e is InputEventKey and e.pressed:
		var k := e as InputEventKey
		if k.keycode == KEY_LEFT or k.keycode == KEY_RIGHT:
			rotate_step(-1 if k.keycode == KEY_LEFT else 1)
			accept_event()
		elif k.keycode == KEY_HOME:             # R — «где я» (сводка, как в game.py), не сброс вида
			reset_view()
			accept_event()
