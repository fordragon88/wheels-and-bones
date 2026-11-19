class_name Figure
extends Control
## Персонаж на экране: картинка из content/img, вписанная в бокс с сохранением пропорций (load_image(name, size)),
## «живая» (blit_idle: breathe — дышит торс, float — парит призрак), или петля кадров (Frames.loop_frame), пока она
## есть и не «Без анимации». У петли свой бокс (у машущего Мартина кадры с полями — бокс выше).
## Позиция Control = левый верх бокса картинки (как pos у blit_idle).

var image: String = ""
var loop: String = ""
var box: Vector2 = Vector2(150, 190)       # бокс статичной картинки
var loop_box: Rect2 = Rect2()              # бокс петли относительно position (пусто — тот же, что картинка)
var mode: String = "breathe"               # breathe | float | none
var phase: float = 0.0
var appear_k: float = 1.0                  # масштаб появления (ease_back), 0 — не видно
var t: float = 0.0
var flip: bool = false
var loop_still: bool = false               # петля «живого» персонажа (Бренна): клип сам парит — без своего покачивания

## Снимки (tests/shots.gd): ≥ 0 — петли «живых» персонажей берут кадр на это время (как ref_shots.py), иначе свой t.
static var idle_t: float = -1.0


## Петля «живого» персонажа для картинки (IDLE_LOOPS в game.py: master.png → brenna_wave) или "".
static func idle_loop(img: String) -> String:
	return str(Content.consts.get("idle", {}).get("loops", {}).get(img, ""))


## Бокс кадра петли для картинки в боксе bx (idle_loop_box в game.py): шире и выше на поле IDLE_PAD с каждой стороны,
## поле округлено до целых логических px, центр тот же.
static func idle_box(bx: Rect2) -> Rect2:
	var pad := float(Content.consts.get("idle", {}).get("pad", 0.0))
	var p := Vector2(roundf(bx.size.x * pad), roundf(bx.size.y * pad))
	return Rect2(bx.position - p, bx.size + 2 * p)


## Персонаж img для бокса bx на время t (idle_img в game.py): {tex, box, live} — кадр петли в боксе с полем или
## статичная картинка в самом bx («Без анимации», петли нет или ещё не загружена).
static func idle_pick(img: String, bx: Rect2, t: float) -> Dictionary:
	var n := idle_loop(img)
	if n != "":
		var tex := Frames.loop_frame(n, idle_t if idle_t >= 0.0 else t)
		if tex != null:
			return {"tex": tex, "box": idle_box(bx), "live": true}
	return {"tex": Content.texture(img), "box": bx, "live": false}


static func make(img: String, pos: Vector2, bx: Vector2, md: String = "breathe", loop_name: String = "") -> Figure:
	var f := Figure.new()
	f.image = img
	f.position = pos
	f.box = bx
	f.size = bx
	f.mode = md
	f.loop = loop_name
	if loop_name == "" and idle_loop(img) != "":     # Бренна — своей петлёй, в боксе с полем, без покачивания
		f.loop = idle_loop(img)
		f.loop_box = idle_box(Rect2(Vector2.ZERO, bx))
		f.loop_still = true
	return f


func _init() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func _process(dt: float) -> void:
	t += dt
	queue_redraw()


func _draw() -> void:
	if appear_k <= 0.01:
		return
	var tex: Texture2D = null
	var bx := Rect2(Vector2.ZERO, box)
	if loop != "":
		tex = Frames.loop_frame(loop, idle_t if loop_still and idle_t >= 0.0 else t)
		if tex != null and loop_box.size != Vector2.ZERO:
			bx = loop_box
	var live := tex != null
	if tex == null:
		tex = Content.texture(image)
		bx = Rect2(Vector2.ZERO, box)
	if tex == null:
		return
	var r := UI.fit_rect(tex.get_size(), bx)
	if live and loop_still:                              # blit_hero: только появление k (призрак — из центра)
		if appear_k == 1.0:
			draw_texture_rect(tex, r, false)
			return
		var o := bx.get_center() if mode == "float" else Vector2(bx.get_center().x, bx.end.y)
		draw_set_transform(o, 0.0, Vector2(appear_k, appear_k))
		draw_texture_rect(tex, Rect2(r.position - o, r.size), false)
		draw_set_transform(Vector2.ZERO)
		return
	if mode == "float":
		var dy := 7.0 * UI.wsin(t * 1.6 + phase)
		var ang := 2.5 * UI.wsin(t * 1.1 + phase)
		var c := bx.get_center() + Vector2(0, dy)
		draw_set_transform(c, deg_to_rad(-ang), Vector2(appear_k, appear_k))
		draw_texture_rect(tex, Rect2(r.position - bx.get_center(), r.size), false)
		draw_set_transform(Vector2.ZERO)
		return
	if appear_k != 1.0:
		var mb := Vector2(bx.get_center().x, bx.end.y)       # midbottom
		draw_set_transform(mb, 0.0, Vector2(appear_k, appear_k))
		draw_texture_rect(tex, Rect2(r.position - mb, r.size), false)
		draw_set_transform(Vector2.ZERO)
		return
	var sy := 1.0 + 0.014 * UI.wsin(t * 2.1 + phase) if mode == "breathe" else 1.0
	if sy == 1.0:
		draw_texture_rect(tex, r, false)
		return
	# дышит верх (торс): верхние 55 % бокса тянутся вверх от линии разреза, низ с коляской стоит
	var ts := tex.get_size()
	var cut := bx.size.y * 0.55                               # разрез — по боксу (как по картинке load_image)
	var cut_tex := clampf((cut - (r.position.y - bx.position.y)) / r.size.y, 0.0, 1.0) * ts.y
	var cut_y := r.position.y + cut_tex / ts.y * r.size.y
	draw_texture_rect_region(tex, Rect2(r.position.x, cut_y, r.size.x, r.end.y - cut_y),
		Rect2(0, cut_tex, ts.x, ts.y - cut_tex))
	var top_h := (cut_y - r.position.y) * sy
	draw_texture_rect_region(tex, Rect2(r.position.x, cut_y - top_h, r.size.x, top_h + 0.5), Rect2(0, 0, ts.x, cut_tex + 0.5))
