class_name SpeechBubble
extends Control
## Пузыри реплик. Строка — «Имя: «текст»» по-русски (переводится целиком, потом делится на «кто: что»), печатается
## по буквам (кроме «текст сразу»).
##   CLIENT — пузырь клиента под портретом (_draw_client_bubble): выпрыгивает, хвостик к портрету.
##   MENTOR — пузырь наставника внизу (_draw_ghost_bubble): портрет говорящего (Барти машет петлёй) и рамка.
## Невидимая «живая» надпись дублирует реплику для чтеца экрана.

enum Kind { CLIENT, MENTOR }

var kind: Kind = Kind.CLIENT
var line: String = ""
var t: float = 0.0
var t0: float = 0.0
var bottom: float = 572.0                 # CLIENT: нижняя граница (в ремонте — выше)
var top_y: float = 584.0                  # MENTOR: верх пузыря
var job: Dictionary = {}                  # MENTOR: чей портрет у реплики клиента
var col: Rect2 = Rect2()                  # MENTOR: узкий пузырь в правой колонке (ремонт); пусто — внизу
var _typing: Array = ["", 0.0]
var _live: Label
var _spk: Control                         # MENTOR: портрет говорящего — свой слой, рисуется каждый кадр (машет, парит)
var _sig: Array = []                      # пузырь с текстом — только пока выпрыгивает/печатается и при смене реплики


static func make(k: Kind) -> SpeechBubble:
	var b := SpeechBubble.new()
	b.kind = k
	b.name = "ClientBubble" if k == Kind.CLIENT else "MentorBubble"
	return b


func _init() -> void:
	size = Vector2(UI.W, UI.H)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_live = Label.new()
	_live.modulate = Color(1, 1, 1, 0)
	_live.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_live.accessibility_live = AccessibilityServer.AccessibilityLiveMode.LIVE_OFF   # реплики говорит A11y/Speech
	add_child(_live)
	_spk = Control.new()
	_spk.name = "Speaker"
	_spk.size = size
	_spk.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_spk.draw.connect(_draw_spk)
	add_child(_spk)


## Новая реплика (пусто — пузыря нет). Возврат: true — реплика сменилась.
func say(s: String) -> bool:
	if s == line:
		return false
	line = s
	t0 = t
	_live.text = Loc.t(s)
	return true


func _process(dt: float) -> void:
	t += dt
	var on := shown()
	var cps := 80.0 if kind == Kind.CLIENT else 90.0
	var tl := Loc.t(line)                     # выпрыгивает 0,35 с, печатается по буквам (typed: с первого рисования)
	var typing := str(_typing[0])
	var typed_all: bool = Settings.a11y.get("instant", false) or (typing != "" and tl.contains(typing)
		and (t - float(_typing[1])) * cps >= typing.length() + 1)
	var anim := on and (t - t0 < 0.4 or not typed_all)
	var sig := [line, on, bottom, top_y, col, t if anim else 0.0]
	if sig != _sig:
		_sig = sig
		queue_redraw()
	if kind == Kind.MENTOR and (on or _spk.visible):
		_spk.visible = on
		_spk.queue_redraw()


func typed(text: String, cps: float) -> int:
	if Settings.a11y.get("instant", false):
		return 1 << 30
	if _typing[0] != text:
		_typing = [text, t]
		return 0
	return int((t - float(_typing[1])) * cps)


## Чей портрет у реплики наставника: Бренна, Мартин, клиент задания или Барти (_speaker_img).
func speaker_img(s: String) -> String:
	if s.begins_with("Бренна"):
		return "master.png"
	if s.begins_with("Мартин"):
		return "martin.png"
	var colon := s.find(":")
	var nm := s.substr(0, colon).strip_edges() if colon >= 0 else ""
	if nm != "" and colon < 40 and not job.is_empty():
		var parts := nm.split(" ")
		if str(job.get("client", "")).contains(parts[parts.size() - 1]):
			return job["client_art"]
	return "ghost.png"


func shown() -> bool:
	if line == "":
		return false
	return kind == Kind.CLIENT or Settings.barty_on() or speaker_img(line) != "ghost.png"


func _draw() -> void:
	if not shown():
		return
	if kind == Kind.CLIENT:
		_draw_client()
	else:
		_draw_mentor()


func _draw_client() -> void:
	var tl := Loc.t(line)
	var colon := tl.find(":")
	var nm := tl.substr(0, colon).strip_edges() if colon >= 0 else ""
	var text := tl.substr(colon + 1).strip_edges() if colon >= 0 else tl
	var w := 300.0
	var tw := 272.0
	var sz := 13
	var lines: PackedStringArray = []
	var lh := 0.0
	for s: int in [15, 14, 13]:
		sz = s
		lines = UI.wrap_lines(text, tw, s)
		lh = UI.line_height(s) + 2
		if 34 + lines.size() * lh + 12 <= bottom - 296:
			break
	var h := 34 + lines.size() * lh + 12
	var k := UI.ease_back((t - t0) / 0.35)
	if k <= 0.01:
		return
	var top := 296 + int(h * (1 - k) / 2)
	draw_colored_polygon(PackedVector2Array([Vector2(70, 284), Vector2(60, top + 2), Vector2(92, top + 2)]), UI.AMBER)
	draw_colored_polygon(PackedVector2Array([Vector2(70, 289), Vector2(63, top + 4), Vector2(89, top + 4)]),
		Color8(44, 36, 28))
	draw_set_transform(Vector2(18 + w / 2, 296 + h / 2), 0.0, Vector2(k, k))
	var box := Rect2(-w / 2, -h / 2, w, h)
	UI.draw_round_rect(self, box, Color8(44, 36, 28, 235), UI.AMBER, 2, 12)
	UI.draw_text(self, nm, box.position + Vector2(14, 9), 14, UI.AMBER, true)
	UI.draw_wrapped(self, text, box.position + Vector2(14, 32), tw, sz, Color8(240, 232, 214), false, 2, typed(text, 80))
	draw_set_transform(Vector2.ZERO)


func _draw_mentor() -> void:
	if col.size != Vector2.ZERO:
		_draw_mentor_col()
		return
	var bubble := Rect2(120, top_y, 740, 86)
	draw_rect(bubble, Color8(24, 30, 36, 220))
	UI.draw_round_rect(self, bubble, Color(0, 0, 0, 0), UI.CYAN, 2, 8)
	var text := Loc.t(line)
	var sz := 13
	var lh := 0.0
	for s: int in [16, 15, 14, 13]:          # крупный текст: длинная реплика — мельче, но в рамке
		sz = s
		lh = UI.line_height(s) + 2
		if UI.wrap_lines(text, bubble.size.x - 28, s).size() * lh <= bubble.size.y - 20:
			break
	UI.draw_wrapped(self, text, bubble.position + Vector2(14, 10), bubble.size.x - 28, sz, UI.GHOST, false, 2,
		typed(text, 90), maxi(1, int((bubble.size.y - 20) / lh)))


## Портрет говорящего в боксе bx: Барти — машущей петлёй, Бренна — своей петлёй в боксе с полем и без покачивания
## (клип сам парит; blit_hero в game.py), остальные — картинкой. «Без анимации» — картинки, парят как раньше.
func _draw_speaker(img: String, bx: Rect2) -> void:
	var ci := _spk
	var tex: Texture2D = Frames.loop_frame("barty_wave", t) if img == "ghost.png" else null
	if tex == null:
		var p := Figure.idle_pick(img, bx, t)
		tex = p["tex"]
		if tex != null and p["live"]:
			ci.draw_texture_rect(tex, p["rect"], false)     # точно на месте картинки (Figure.idle_rect)
			return
	if tex == null:
		return
	var r := UI.fit_rect(tex.get_size(), bx)
	var dy := 7.0 * UI.wsin(t * 1.6 + 1.3)
	var ang := 2.5 * UI.wsin(t * 1.1 + 1.3)
	ci.draw_set_transform(bx.get_center() + Vector2(0, dy), deg_to_rad(-ang))
	ci.draw_texture_rect(tex, Rect2(r.position - bx.get_center(), r.size), false)
	ci.draw_set_transform(Vector2.ZERO)


## Слой портрета наставника (поверх пузыря: в узком пузыре портрет внутри рамки — как раньше, после фона).
func _draw_spk() -> void:
	if kind != Kind.MENTOR or not shown():
		return
	if col.size != Vector2.ZERO:
		_draw_speaker(speaker_img(line), Rect2(col.position + Vector2(6, 6), Vector2(46, 56)))
	else:
		_draw_speaker(speaker_img(line), Rect2(24, top_y, 90, 110))


## Узкий пузырь наставника в правой колонке (ремонт): портрет 46×56 и текст рядом.
func _draw_mentor_col() -> void:
	draw_rect(col, Color8(24, 30, 36, 220))
	UI.draw_round_rect(self, col, Color(0, 0, 0, 0), UI.CYAN, 2, 8)
	var text := Loc.t(line)
	var tw := col.size.x - 70
	var sz := 12
	for s: int in [15, 14, 13, 12]:
		sz = s
		if UI.wrap_lines(text, tw, s).size() * (UI.line_height(s) + 2) <= col.size.y - 16:
			break
	UI.draw_wrapped(self, text, col.position + Vector2(60, 8), tw, sz, UI.GHOST, false, 2, typed(text, 90))
