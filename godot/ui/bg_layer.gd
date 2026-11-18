class_name BgLayer
extends Control
## Фон сцены (_bg в game.py): картинка 1280×720 + затемнение (контрастный режим — почти чёрное) + «жизнь» фона
## (draw_ambient): у мастерской — луч из круглого окна и пылинки. Частицы — аддитивное свечение, выключаются
## «Без анимации», контрастным фоном и «Свечением».

var image: String = "bg_workshop.png"
var t: float = 0.0
var _amb: Control


static func make(img: String) -> BgLayer:
	var b := BgLayer.new()
	b.image = img
	b.name = "Bg"
	return b


func _init() -> void:
	size = Vector2(UI.W, UI.H)
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func _ready() -> void:
	Audio.ambient(image)                     # фоновая петля сцены (как set_ambient в _bg)
	_amb = Control.new()
	_amb.size = size
	_amb.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var mat := CanvasItemMaterial.new()
	mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	_amb.material = mat
	_amb.draw.connect(_draw_ambient)
	add_child(_amb)


func _process(dt: float) -> void:
	t += dt
	if _amb.visible:
		_amb.queue_redraw()


func _draw() -> void:
	var tex := Content.texture(image)
	if tex:
		draw_texture_rect(tex, Rect2(0, 0, UI.W, UI.H), false)
	else:
		draw_rect(Rect2(0, 0, UI.W, UI.H), UI.WOOD)
	var contrast: bool = Settings.a11y.get("contrast", false)
	draw_rect(Rect2(0, 0, UI.W, UI.H), Color8(10, 9, 14, 222) if contrast else Color8(18, 16, 24, 150))
	_amb.visible = Settings.glow_on() and not contrast


static func _h01(i: int, k: int = 0) -> float:
	var v := sin(i * 12.9898 + k * 78.233) * 43758.5453
	return v - floorf(v)


func _draw_ambient() -> void:
	if image == "bg_workshop.png":         # луч из круглого окна и пылинки в нём
		UI.draw_glow(_amb, Vector2(150, 170), 200, Color8(70, 55, 28), 0.6 + 0.15 * sin(t * 0.7))
		for i in 34:
			var sp := 6 + 10 * _h01(i, 1)
			var x := 40 + 420 * _h01(i, 2) + 30 * sin(t * 0.3 + i)
			var y := 560 - fmod(t * sp + 600 * _h01(i, 3), 540.0)
			var tw := 0.5 + 0.5 * sin(t * 2 + i * 1.7)
			UI.draw_glow(_amb, Vector2(x, y), 5, Color8(255, 230, 170), 0.3 + 0.5 * tw)
	elif image == "bg_road.png":           # светлячки и сияние луны
		UI.draw_glow(_amb, Vector2(480, 104), 110, Color8(40, 50, 75), 0.55 + 0.1 * sin(t * 0.5))
		for i in 26:
			var x := UI.W * _h01(i, 1) + 45 * sin(t * (0.3 + 0.4 * _h01(i, 3)) + i)
			var y := 300 + 380 * _h01(i, 2) + 25 * sin(t * (0.5 + 0.5 * _h01(i, 4)) + i * 2)
			var p := 0.5 + 0.5 * sin(t * (1.5 + 2 * _h01(i, 5)) + i * 3)
			UI.draw_glow(_amb, Vector2(x, y), 14, Color8(190, 255, 110), 0.1 + 0.9 * p * p)
