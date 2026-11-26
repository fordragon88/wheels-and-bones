class_name ManualDialog
extends Control
## Мануал Гильдии Колёсников (_draw_manual_overlay в game.py): слева страницы задания (manual.json: заголовок и
## строки), справа текст страницы — шрифт подбирается, чтобы влезло. Открытая страница отмечается прочитанной
## (viewed — общий словарь экрана: «сначала мануал» для спек). «ЗАКРЫТЬ [Esc]».

signal closed

const P := Rect2(40, 62, 1200, 646)

var pages: Array = []                       # ключи страниц manual.json
var page: String = ""
var viewed: Dictionary = {}                 # ключ → true (общий с экраном задания)
var _close: GameButton
var _btns: Array[GameButton] = []


static func make(keys: Array, open_page: String, seen: Dictionary) -> ManualDialog:
	var d := ManualDialog.new()
	d.pages = keys
	d.page = open_page if open_page in keys else (keys[0] if not keys.is_empty() else "")
	d.viewed = seen
	if d.page != "":
		seen[d.page] = true
	return d


func _init() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	name = "Manual"


func _ready() -> void:
	for i in pages.size():
		var key: String = pages[i]
		var b := GameButton.make(Rect2(P.position.x + 20, P.position.y + 70 + i * 64, 270, 56) if UI.phone()
			else Rect2(P.position.x + 20, P.position.y + 70 + i * 54, 270, 46), "", UI.PURPLE)
		b.name = "Page_" + key
		b.plain = true
		b.set_meta("key", key)
		b.on_draw = _draw_page_btn
		b.redraw_sig = func() -> String: return page          # подсветка открытой страницы
		b.set_meta("a11y_group", "Страницы")
		b.pressed.connect(func() -> void:
			page = key
			viewed[key] = true
			Audio.sfx("tick")
			_update())
		add_child(b)
		_btns.append(b)
	_close = GameButton.make(Rect2(P.end.x - 200, P.end.y - 72, 180, 56) if UI.phone() else Rect2(P.end.x - 200, P.end.y - 64, 180, 46),
		"ЗАКРЫТЬ [Esc]", UI.AMBER)
	_close.name = "Close"
	_close.pressed.connect(close)
	add_child(_close)
	accessibility_name = Loc.t("МАНУАЛ ГИЛЬДИИ КОЛЁСНИКОВ")
	_update()
	UI.focus_later(get_node_or_null("Page_" + page) if page != "" else _close)


## Список клавиатуры: страницы, «закрыть», «◂ назад» экрана (как a11y_items game.py при открытом мануале).
func kb_order(items: Array) -> Array:
	return A11y.with_screen_back(items)


func first_focus() -> Control:
	return get_node_or_null("Page_" + page) as Control if page != "" else _close


static func title_of(key: String) -> String:
	return str(Content.manual.get(key, {}).get("title", key))


static func lines_of(key: String) -> Array:
	return Content.manual.get(key, {}).get("lines", [])


func _update() -> void:
	accessibility_description = Loc.t(title_of(page)) + ". " + ". ".join(lines_of(page).map(func(l: String) -> String: return Loc.t(l)))
	for b in _btns:
		var k: String = b.get_meta("key")
		b.accessibility_name = Loc.t(title_of(k)) + (", " + Loc.t("открыта") if k == page else "")
		b.queue_redraw()
	queue_redraw()


func close() -> void:
	if is_queued_for_deletion():                # второй close() в том же кадре (двойное нажатие) — уже закрыто
		return
	Audio.sfx("tick")
	closed.emit()
	queue_free()


func _gui_input(_e: InputEvent) -> void:
	accept_event()


func _draw_page_btn(b: GameButton, _r: Rect2) -> void:
	var key: String = b.get_meta("key")
	var active := key == page
	var r := Rect2(Vector2.ZERO, b.size)
	UI.draw_round_rect(b, r, UI.PANEL2 if active else UI.PANEL, UI.PURPLE if active else UI.DIM, 2, 6)
	var nm := Loc.t(title_of(key))
	if UI.text_width(nm, 14) <= r.size.x - 20:
		UI.draw_text(b, nm, Vector2(10, 13), 14, UI.WHITE if active else UI.GREY)
	else:
		UI.draw_wrapped(b, nm, Vector2(10, 5), r.size.x - 20, 13, UI.WHITE if active else UI.GREY, false, 2, -1, 2)


func _draw() -> void:
	draw_rect(Rect2(0, 0, UI.W, UI.H), Color8(8, 8, 12, 180))
	draw_rect(P, Color8(26, 24, 34, 250))
	UI.draw_round_rect(self, P, Color(0, 0, 0, 0), UI.PURPLE, 2, 10)
	UI.draw_text(self, Loc.t("МАНУАЛ ГИЛЬДИИ КОЛЁСНИКОВ"), P.position + Vector2(24, 20), 22, UI.PURPLE, true)
	if page == "":
		return
	var x0 := P.position.x + 320
	var tw := P.end.x - 24 - x0
	var f: Array = UI.fit_text(Loc.t(title_of(page)), tw, 20, true)
	UI.draw_text(self, f[0], Vector2(x0, P.position.y + 70 + floorf((20 - int(f[1])) / 2.0)), f[1], UI.AMBER, true)
	var y0 := P.position.y + 110
	var bottom := _close.position.y - 10
	var ls: Array = lines_of(page).map(func(l: String) -> String: return Loc.t(l))
	var size_ := 11
	var gap := 4.0
	for s in range(17, 10, -1):
		var g := 8.0 if s >= 15 else 5.0
		var h := 0.0
		for ln: String in ls:
			h += UI.wrap_lines("• " + ln, tw, s).size() * (UI.line_height(s) + 2) + g
		size_ = s
		gap = g
		if h <= bottom - y0:
			break
	var y := y0
	for ln: String in ls:
		y = UI.draw_wrapped(self, "• " + ln, Vector2(x0, y), tw, size_, UI.WHITE) + gap
