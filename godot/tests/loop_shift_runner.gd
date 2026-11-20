extends Node
## Стык «живых» слоёв героя в Godot — рисует слои для tools/loop_shift.py (загрузчик — tests/loop_shift.gd):
## картинка, кадр 0 спокойной петли (Figure), кадр 0 «волшебства» (MagicPortrait) — каждый слой отдельно на
## прозрачном SubViewport размера окна (масштаб canvas_items, как у игры: окно / 1280×720, полосы по краям — сдвиг)
## -> PNG; сдвиг меряет Python по альфе. Слои рисуются прежним расчётом (old) и нынешним (new) — таблица «было/стало».
## С окном (рендер), звук — Dummy:
##   Godot_v4.7.2-stable_win64_console.exe --audio-driver Dummy --path godot -s res://tests/loop_shift.gd -- <папка>

const SIZES := [[1280, 720], [1920, 1080], [2340, 1080]]
const PLACES := {
	"job": ["martin.png", "martin_idle", [24, 70, 150, 190], true],
	"result": ["martin.png", "martin_idle", [24, 300, 210, 250], true],
	"ride": ["martin.png", "martin_idle", [525.5, 275, 230, 250], false],
	"brenna": ["master.png", "brenna_wave", [980, 130, 200, 280], false],
}

var _out := ""
var _vp: SubViewport
var _cv: Control
var _what := {}


func _ready() -> void:
	var a := OS.get_cmdline_user_args()
	_out = a[0] if a.size() > 0 else OS.get_user_data_dir().path_join("loop_shift")
	DirAccess.make_dir_recursive_absolute(_out)
	_start.call_deferred()


func _frames(n: int) -> void:
	for i in n:
		await get_tree().process_frame


func _start() -> void:
	var places := PLACES.duplicate()
	for sc: String in ["intro", "ending"]:                 # петли экранов Мартина (лес, праздник)
		var e := Figure.scene_loop(sc)
		if not e.is_empty():
			places["forest" if sc == "intro" else "party"] = [str(e["art"]), str(e["loop"]), e["box"], false]
	var need := ["magic_martin"]
	for k: String in places:
		need.append(places[k][1])
	for n: String in need:
		Frames.want_loop(n)
	Frames.flush()
	for i in 600:
		var ok := true
		for n: String in need:
			Frames.want_loop(n)
			ok = ok and Frames.loop_ready(n)
		if ok:
			break
		await _frames(1)
	_vp = SubViewport.new()
	_vp.transparent_bg = true
	_vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	_vp.canvas_item_default_texture_filter = Viewport.DEFAULT_CANVAS_ITEM_TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
	add_child(_vp)
	_cv = Control.new()
	_cv.draw.connect(_draw)
	_vp.add_child(_cv)
	var lines: Array = []
	for wh: Array in SIZES:
		var w: int = wh[0]
		var h: int = wh[1]
		var s := minf(w / 1280.0, h / 720.0)
		var off := Vector2(roundf((w - 1280 * s) / 2), roundf((h - 720 * s) / 2))
		_vp.size = Vector2i(w, h)
		_vp.canvas_transform = Transform2D(0.0, Vector2(s, s), 0.0, off)
		for pl: String in places:
			var p: Array = places[pl]
			var b: Array = p[2]
			var bx := Rect2(float(b[0]), float(b[1]), float(b[2]), float(b[3]))
			var layers := ["pic", "loop_old", "loop_new"] + (["magic_old", "magic_new"] if p[3] else [])
			for ly: String in layers:
				_what = {"layer": ly, "art": p[0], "loop": p[1], "box": bx}
				_cv.queue_redraw()
				await _frames(3)
				var img := _vp.get_texture().get_image()
				var fn := "%dx%d_%s_%s.png" % [w, h, pl, ly]
				img.save_png(_out.path_join(fn))
				lines.append(fn)
	print("LOOP SHIFT LAYERS: %d -> %s" % [lines.size(), _out])
	get_tree().quit(0)


func _draw() -> void:
	if _what.is_empty():
		return
	var art: String = _what["art"]
	var bx: Rect2 = _what["box"]
	var ly: String = _what["layer"]
	var st := Content.texture(art)
	if ly == "pic":
		_cv.draw_texture_rect(st, UI.fit_rect(st.get_size(), bx), false)
	elif ly.begins_with("loop"):
		var tex := Frames.loop_frame(str(_what["loop"]), 1e-4)
		if tex == null:
			return
		var r := UI.fit_rect(tex.get_size(), Figure.idle_box(bx)) if ly == "loop_old" else Figure.idle_rect(art, bx)
		_cv.draw_texture_rect(tex, r, false)
	else:
		var e: Dictionary = Frames.magic["magic_martin"]
		var tex := Frames.loop_frame("magic_martin", 1e-4, float(e["fps"]))
		if tex == null:
			return
		var r: Rect2
		if ly == "magic_old":                       # прежний _draw_frame: масштаб по высоте, центр портрета
			var real := UI.fit_rect(st.get_size(), bx)
			var sz: Array = e["size"]
			var pr: Array = e["portrait"]
			var sf := real.size.y / float(pr[3])
			var pos := Vector2(real.position.x + real.size.x / 2 - (float(pr[0]) + float(pr[2]) / 2) * sf,
				real.position.y + real.size.y / 2 - (float(pr[1]) + float(pr[3]) / 2) * sf)
			r = Rect2(pos, Vector2(float(sz[0]), float(sz[1])) * sf)
		else:
			var m := MagicPortrait.make(art, bx, 0.0, false)
			m.loop_name = "magic_martin"
			r = m.frame_rect()
			m.free()
		_cv.draw_texture_rect(tex, r, false)
