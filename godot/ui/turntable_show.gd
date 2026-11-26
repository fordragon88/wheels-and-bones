class_name TurntableShow
extends Control
## Коляска Гильдии на кадрах поворота (_draw_tt_show в game.py): медленно крутится сама (TT_SPIN 0,35 рад/с, кроме
## «Без анимации»), тянется мышью/пальцем; без кружков деталей. Окно пропорций кадров 380×300 по центру rect, зум
## z0 (в «Проверке под нагрузкой» — ×1,12), тень на полу как в окне задания. Пока кадров нет — рисунок коляски.

var art: String = ""
var tt: Dictionary = {}
var yaw: float = -0.75
var zoom_mul: float = 1.0
var drag: bool = false
var _last: Vector2
var _tick_yaw: float = 0.0
var _shadow_key := ""
var _shadow: Texture2D
var _inside := false


static func make(chair_art: String, r: Rect2, zm: float = 1.0) -> TurntableShow:
	var s := TurntableShow.new()
	s.art = chair_art
	s.position = r.position
	s.size = r.size
	s.zoom_mul = zm
	return s


func _init() -> void:
	mouse_filter = Control.MOUSE_FILTER_STOP
	mouse_default_cursor_shape = Control.CURSOR_DRAG
	name = "ChairShow"
	mouse_entered.connect(func() -> void: _inside = true)
	mouse_exited.connect(func() -> void: _inside = false)


func _ready() -> void:
	tt = Frames.turntable(art)
	yaw = float(Content.consts.get("m3d", {}).get("yaw", -0.75))
	if not tt.is_empty():
		Frames.want_turntable(art, Frames.tt_index_for(art, yaw))


func _process(dt: float) -> void:
	if not tt.is_empty() and not drag and not Settings.calm():
		yaw += float(Content.consts.get("tt_spin", 0.35)) * minf(0.1, dt)
	queue_redraw()


func _gui_input(e: InputEvent) -> void:
	if e is InputEventMouseButton and e.button_index == MOUSE_BUTTON_LEFT:
		drag = e.pressed and not tt.is_empty()
		_last = e.position
		if drag:
			_tick_yaw = yaw                      # после автоповорота первый сдвиг не щёлкает (setdefault в game.py), E29.8
		accept_event()
	elif e is InputEventMouseMotion and drag:
		yaw += (e.position.x - _last.x) * 0.012
		_last = e.position
		if absf(yaw - _tick_yaw) > 0.35:
			_tick_yaw = yaw
			Audio.sfx("ratchet")
		accept_event()


func _draw() -> void:
	var r := Rect2(Vector2.ZERO, size)
	var h := int(minf(r.size.y, r.size.x * 300 / 380))
	var fr := Rect2(Vector2.ZERO, Vector2(int(h * 380 / 300.0), h))
	fr.position = r.get_center() - fr.size / 2
	var i := Frames.tt_index_for(art, yaw)
	var tex := Frames.tt_frame(art, i) if not tt.is_empty() else null
	if tex == null and not tt.is_empty():
		i = Frames.tt_nearest_index(art, i)
		tex = Frames.tt_frame(art, i)
	if tex == null:
		var a := Content.texture(art)
		if a:
			draw_texture_rect(a, UI.fit_rect(a.get_size(), fr), false)
		return
	var zoom := float(tt["z0"]) * zoom_mul
	var scale := fr.size.y / 1250.0 * zoom
	var key := "%d|%s|%.4f" % [i, fr, zoom]
	if key != _shadow_key:
		_shadow_key = key
		var n := int(tt["n"])
		var yw := float(tt["yaw0"]) + i * TAU / n
		var pivot: Array = tt["pivot"]
		var poly := PackedVector2Array()
		for f: Array in [[-470, -310], [470, -310], [470, 310], [-470, 310]]:
			var q := ChairView.project([float(pivot[0]) + f[0], 0, f[1]], yw, float(tt["pitch"]), Rect2(Vector2.ZERO, fr.size), zoom, pivot)
			poly.append(Vector2(q.x, q.y) / 10.0)
		var w := maxi(1, int(fr.size.x / 10))
		var hh := maxi(1, int(fr.size.y / 10))
		var img := Image.create(w, hh, false, Image.FORMAT_RGBA8)
		for y in hh:
			for x in w:
				if Geometry2D.is_point_in_polygon(Vector2(x + 0.5, y + 0.5), poly):
					img.set_pixel(x, y, Color(0, 0, 0, 110.0 / 255.0))
		img.generate_mipmaps()
		_shadow = ImageTexture.create_from_image(img)
	draw_texture_rect(_shadow, fr, false)
	var off: Array = tt["offsets"][i]
	var ax := fr.position.x + fr.size.x / 2.0
	var ay := fr.position.y + fr.size.y * 0.54
	draw_texture_rect(tex, Rect2(Vector2(ax + float(off[0]) * scale, ay + float(off[1]) * scale), tex.get_size() * scale / float(tt["ref"])), false)
	if not drag and _inside and not UI.touch():  # _draw_tt_show: «наведения» на сенсоре нет — подсказки под пальцем нет
		UI.draw_text(self, Loc.t("⟲ тяни — повернуть"), Vector2(6, size.y - 16), 12, Color8(200, 196, 180))
