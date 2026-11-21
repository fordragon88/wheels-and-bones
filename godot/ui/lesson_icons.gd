extends RefCounted
## Пиктограммы семи уроков Кабинета посадки на кнопках списка (телефонный режим, 21.11; утверждены владельцем вместо
## мини-скелетов SeatFigure). Рисунки — из эскиза lesson_icons.py (поле 256×256, те же точки и толщины линий; PIL-
## помощники: line — ломаная со скруглёнными стыками и концами, dash — пунктир, dot — круг, ring — кольцо, arc — дуга
## с углами по часовой от оси X, head — наконечник стрелки, poly — многоугольник). Отличие от эскиза: зев ключа (урок 5)
## — честный разрыв кольца на 70° в сторону от ручки (в PIL «вырез» прозрачным многоугольником не сработал).
##
## Каждая пиктограмма — одна пачка треугольников со сглаженными кромками (кромка 1,25 px до прозрачного, как у
## сглаживания Godot), считается раз на (урок, размер в px) и рисуется одним вызовом canvas_item_add_triangle_array —
## без draw_polyline/draw_circle (каждый такой сглаженный — 2–3 вызова WebGL, PORT_PLAN «Сглаженные круги»).
## Номер урока n — 1…7 (порядок в lessons.json); для других номеров пиктограммы нет (has() = false).

const COUNT := 7

static var _cache := {}                   # "n|px" → [точки от (0, 0), цвета]

static func has(n: int) -> bool:
	return n >= 1 and n <= COUNT


## Рисует пиктограмму урока n в квадрат box (на холсте ci): поле 256×256 → box целиком.
static func draw(ci: CanvasItem, n: int, box: Rect2) -> void:
	if not has(n):
		return
	var px := box.size.x
	var key := "%d|%s" % [n, px]
	if not _cache.has(key):
		var b := _B.new()
		b.k = px / 256.0
		b.call("_i%d" % n)
		_cache[key] = [b.v, b.c]
	var m: Array = _cache[key]
	RenderingServer.canvas_item_add_triangle_array(ci.get_canvas_item(), PackedInt32Array(),
		Transform2D(0.0, box.position) * (m[0] as PackedVector2Array), m[1])


## Построитель одной пиктограммы: точки и цвета треугольников по порядку перекрытия.
class _B extends RefCounted:
	var v := PackedVector2Array()
	var c := PackedColorArray()
	var k := 1.0                          # px на единицу поля 256

	# ---------------- примитивы (координаты — в поле 256, толщины — тоже) ----------------

	func _tri(a: Vector2, b: Vector2, d: Vector2, ca: Color, cb: Color, cd: Color) -> void:
		v.append(a)
		v.append(b)
		v.append(d)
		c.append(ca)
		c.append(cb)
		c.append(cd)


	## Четырёхугольник a-b-d-e (по контуру), цвет у a и b — ca, у d и e — cd.
	func _quad(a: Vector2, b: Vector2, d: Vector2, e: Vector2, ca: Color, cd: Color) -> void:
		_tri(a, b, d, ca, ca, cd)
		_tri(a, d, e, ca, cd, cd)


	## Полуширина сердцевины и цвет при толщине hw (px): тоньше кромки — сердцевины нет, цвет прозрачнее.
	static func _core(hw: float, col: Color) -> Array:
		var t := hw - F / 2.0
		if t < 0.0:
			col.a *= clampf(hw * 2.0 / F, 0.0, 1.0)
			t = 0.0
		return [t, col]


	## Отрезок толщины w без концов (концы — круги в line).
	func _seg(a: Vector2, b: Vector2, w: float, col: Color) -> void:
		var p := a * k
		var q := b * k
		var d := q - p
		if d.length() < 0.001:
			return
		var nv := Vector2(-d.y, d.x).normalized()
		var cc: Array = _core(w * k / 2.0, col)
		var t: float = cc[0]
		var cl: Color = cc[1]
		var clear := Color(cl, 0.0)
		if t > 0.0:
			_quad(p + nv * t, q + nv * t, q - nv * t, p - nv * t, cl, cl)
		for s: float in [1.0, -1.0]:
			_quad(p + nv * t * s, q + nv * t * s, q + nv * (t + F) * s, p + nv * (t + F) * s, cl, clear)


	## Закрашенный круг (center, r — в поле 256).
	func dot(center: Vector2, r: float, col: Color) -> void:
		var o := center * k
		var cc: Array = _core(r * k, col)
		var t: float = cc[0]
		var cl: Color = cc[1]
		var clear := Color(cl, 0.0)
		var ns := clampi(int(r * k * 1.5) + 12, 16, 40)
		for i in ns:
			var u := Vector2.from_angle(TAU * i / ns)
			var w := Vector2.from_angle(TAU * (i + 1) / ns)
			if t > 0.0:
				_tri(o, o + u * t, o + w * t, cl, cl, cl)
			_quad(o + u * t, o + w * t, o + w * (t + F), o + u * (t + F), cl, clear)


	## Ломаная со скруглёнными стыками и концами (как line в эскизе: отрезки + круг радиуса w/2 в каждой точке).
	func line(pts: Array, col: Color, w: float = 16.0) -> void:
		for i in range(pts.size() - 1):
			_seg(pts[i], pts[i + 1], w, col)
		for p: Vector2 in pts:
			dot(p, w / 2.0, col)


	func dash(a: Vector2, b: Vector2, col: Color, w: float = 8.0, n: int = 7) -> void:
		for i in n:
			line([a.lerp(b, float(i) / n), a.lerp(b, (i + 0.55) / n)], col, w)


	## Точка эллипса с полуосями rx, ry под углом ang (рад, по часовой от оси X — y вниз).
	static func _ell(center: Vector2, rx: float, ry: float, ang: float) -> Vector2:
		var cs := cos(ang)
		var sn := sin(ang)
		var r := rx * ry / maxf(0.001, sqrt(ry * cs * ry * cs + rx * sn * rx * sn))
		return center + Vector2(cs, sn) * r


	## Дуга эллипса толщины w внутрь от рамки box (как arc/ellipse(outline) в PIL), углы a0 → a1 в градусах по часовой.
	func arc(box: Rect2, a0: float, a1: float, col: Color, w: float = 10.0) -> void:
		while a1 < a0:
			a1 += 360.0
		var full := a1 - a0 >= 359.99
		var o := box.get_center() * k
		var rx := box.size.x / 2.0 * k
		var ry := box.size.y / 2.0 * k
		var cc: Array = _core(w * k / 2.0, col)
		var t: float = cc[0]
		var cl: Color = cc[1]
		var clear := Color(cl, 0.0)
		var mid := w * k / 2.0                       # средняя линия кольца — на w/2 внутрь от рамки
		# радиальные уровни от средней линии: −(t+F), −t, +t, +(t+F)
		var lv := [-(t + F), -t, t, t + F]
		var ns := clampi(int((a1 - a0) / 8.0), 4, 48)
		var rows: Array = []
		for i in ns + 1:
			var ang := deg_to_rad(lerpf(a0, a1, float(i) / ns))
			var row: Array = []
			for d: float in lv:
				row.append(_ell(o, rx - mid + d, ry - mid + d, ang))
			rows.append(row)
		for i in ns:
			var r0: Array = rows[i]
			var r1: Array = rows[i + 1]
			_quad(r0[1], r1[1], r1[0], r0[0], cl, clear)
			if t > 0.0:
				_quad(r0[1], r1[1], r1[2], r0[2], cl, cl)
			_quad(r0[2], r1[2], r1[3], r0[3], cl, clear)
		if full:
			return
		for e: Array in [[rows[0], deg_to_rad(a0), -1.0], [rows[ns], deg_to_rad(a1), 1.0]]:   # кромки торцов
			var row: Array = e[0]
			var tg := Vector2(-sin(e[1]), cos(e[1])) * F * float(e[2])
			_quad(row[1], row[2], row[2] + tg, row[1] + tg, cl, clear)


	func ring(center: Vector2, r: float, col: Color, w: float = 12.0) -> void:
		arc(Rect2(center - Vector2(r, r), Vector2(r, r) * 2.0), 0.0, 360.0, col, w)


	## Закрашенный выпуклый многоугольник с кромкой наружу.
	func poly(pts: Array, col: Color) -> void:
		var p: Array = []
		for q: Vector2 in pts:
			p.append(q * k)
		var clear := Color(col, 0.0)
		for i in range(1, p.size() - 1):
			_tri(p[0], p[i], p[i + 1], col, col, col)
		var cen := Vector2.ZERO
		for q: Vector2 in p:
			cen += q / p.size()
		for i in p.size():
			var a: Vector2 = p[i]
			var b: Vector2 = p[(i + 1) % p.size()]
			var nv := Vector2(b.y - a.y, a.x - b.x).normalized() * F
			if nv.dot((a + b) / 2.0 - cen) < 0.0:
				nv = -nv
			_quad(a, b, b + nv, a + nv, col, clear)


	## Наконечник стрелки: tip — остриё, ang — куда смотрит (градусы, 0 = вправо, 90 = вниз).
	func head(tip: Vector2, ang: float, col: Color, sz: float = 20.0) -> void:
		var a := deg_to_rad(ang)
		poly([tip, tip - sz * Vector2(cos(a + 0.5), sin(a + 0.5)), tip - sz * Vector2(cos(a - 0.5), sin(a - 0.5))], col)


	static func _rot(p: Vector2, center: Vector2, deg: float) -> Vector2:
		return center + (p - center).rotated(deg_to_rad(deg))


	# ---------------- семь уроков (как i1…i7 эскиза) ----------------

	const F := 1.25                       # ширина сглаженной кромки, px холста
	const BONE := SeatFigure.BONE
	const CY := UI.CYAN
	const GOLD := UI.AMBER
	const RED := UI.BAD
	const GREEN := UI.GOOD


	func _i1() -> void:                          # таз спереди: два крыла, крестец, два кольца, «тазобедренные» точки
		for m: float in [-1.0, 1.0]:
			line([Vector2(128 + m * 20, 104), Vector2(128 + m * 72, 58), Vector2(128 + m * 100, 98),
				Vector2(128 + m * 84, 144), Vector2(128 + m * 44, 166)], GREEN, 15)
			ring(Vector2(128 + m * 30, 188), 22, GREEN, 13)
			dot(Vector2(128 + m * 92, 178), 15, BONE)
		poly([Vector2(104, 98), Vector2(152, 98), Vector2(128, 158)], GREEN)
		dash(Vector2(24, 240), Vector2(232, 240), CY, 7, 8)


	func _i2() -> void:                          # сидение на крестце: спина дугой, красная точка под крестцом
		line([Vector2(48, 60), Vector2(58, 196), Vector2(196, 196)], CY, 12)
		line([Vector2(100, 186), Vector2(84, 150), Vector2(86, 116), Vector2(104, 88), Vector2(130, 72)], BONE, 16)
		dot(Vector2(156, 62), 23, BONE)
		line([Vector2(100, 186), Vector2(190, 180), Vector2(206, 240)], BONE, 16)
		dot(Vector2(90, 190), 17, RED)


	func _i3() -> void:                          # подножка: колено, голень, стопа на площадке, длина
		line([Vector2(30, 84), Vector2(140, 84)], BONE, 18)
		dot(Vector2(146, 86), 17, BONE)
		line([Vector2(148, 90), Vector2(158, 190), Vector2(214, 194)], BONE, 16)
		line([Vector2(132, 218), Vector2(236, 218)], GOLD, 16)
		line([Vector2(70, 112), Vector2(70, 206)], GOLD, 8)
		head(Vector2(70, 104), 270, GOLD, 22)
		head(Vector2(70, 216), 90, GOLD, 22)


	func _i4() -> void:                          # перекос таза: уровень пунктиром, наклонённая «перекладина», поворот
		dash(Vector2(22, 150), Vector2(234, 150), CY, 7, 8)
		line([Vector2(60, 176), Vector2(196, 124)], GREEN, 18)
		ring(Vector2(52, 182), 20, BONE, 11)
		ring(Vector2(204, 118), 20, BONE, 11)
		line([Vector2(128, 146), Vector2(118, 96), Vector2(134, 44)], BONE, 14)
		arc(Rect2(70, 176, 116, 74), 20, 150, GOLD, 9)
		head(Vector2(74, 214), 245, GOLD, 22)


	func _i5() -> void:                          # исправить (ключ) или учесть (подушка по форме)
		line([Vector2(44, 214), Vector2(104, 124)], GOLD, 20)
		# головка ключа — кольцо с зевом 70° в сторону от ручки (ручка → центр кольца смотрит на −57°)
		var gap := rad_to_deg(Vector2(104, 124).direction_to(Vector2(120, 98)).angle())
		arc(Rect2(90, 68, 60, 60), gap + 35.0, gap - 35.0 + 360.0, GOLD, 16)
		line([Vector2(146, 184), Vector2(146, 216), Vector2(240, 216), Vector2(240, 170), Vector2(214, 186),
			Vector2(184, 198), Vector2(160, 194), Vector2(146, 184)], CY, 12)        # подушка с выемкой
		dot(Vector2(180, 170), 13, BONE)                                            # тело ложится в выемку


	func _i6() -> void:                          # мерки: линейка с делениями и размер
		# рамка со скруглением 10 и толщиной 12 внутрь (rounded_rectangle эскиза) — средняя линия на 6 внутрь, радиус 4
		var pts: Array = []
		for cn: Array in [[Vector2(222, 106), -90.0], [Vector2(222, 158), 0.0], [Vector2(34, 158), 90.0],
				[Vector2(34, 106), 180.0]]:
			for j in 3:
				pts.append((cn[0] as Vector2) + Vector2.from_angle(deg_to_rad(float(cn[1]) + 45.0 * j)) * 4.0)
		pts.append(pts[0])
		line(pts, GOLD, 12)
		for i in 9:
			var x := 46.0 + i * 21
			line([Vector2(x, 104), Vector2(x, 138 if i % 2 == 0 else 124)], GOLD, 7)
		line([Vector2(40, 206), Vector2(216, 206)], CY, 8)
		head(Vector2(30, 206), 180, CY, 22)
		head(Vector2(226, 206), 0, CY, 22)


	func _i7() -> void:                          # давление и наклон: сиденье наклонено назад, стрелки наклона и давления
		var cc := Vector2(112, 176)
		line([Vector2(60, 62), Vector2(60, 176), Vector2(184, 176)].map(
			func(p: Vector2) -> Vector2: return _rot(p, cc, -24)), CY, 16)
		ring(Vector2(120, 214), 22, CY, 11)
		line([Vector2(34, 242), Vector2(226, 242)], CY, 7)
		arc(Rect2(-8, 56, 240, 240), 262, 312, GOLD, 9)
		head(Vector2(86, 58), 174, GOLD, 24)
		for q: Vector2 in [Vector2(118, 128), Vector2(158, 110)]:
			line([Vector2(q.x - 10, q.y - 34), q], RED, 8)
			head(Vector2(q.x + 2, q.y + 8), 74, RED, 20)
