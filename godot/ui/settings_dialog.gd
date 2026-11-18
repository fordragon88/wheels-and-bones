class_name SettingsDialog
extends Control
## Настройки — пока простое окно (полные вкладки «Звук/Графика/Доступность/Игра» — шаг 3 плана): язык, громкости
## (общая, музыка, эффекты), размер текста, «Без анимации», шрифт для лёгкого чтения. Модальное: под ним экран
## не нажимается и не получает фокус. Esc / «ГОТОВО» — закрыть.

signal closed

const PANEL := Rect2(350, 80, 580, 560)

var _first: Control


func _init() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	name = "Settings"


func _ready() -> void:
	Settings.changed.connect(_on_settings)
	Loc.changed.connect(_rebuild)
	_build()


func _on_settings(key: String) -> void:
	if key in ["text", "font", "lang", "calm"]:
		_rebuild()


func _rebuild() -> void:
	var fo := get_viewport().gui_get_focus_owner()
	var nm := fo.name if fo != null and is_ancestor_of(fo) else StringName()
	for c in get_children():
		remove_child(c)
		c.queue_free()
	_build()
	var n := find_child(nm, true, false) if nm != StringName() else null
	if n is Control:
		UI.focus_later(n as Control)


func _draw() -> void:
	draw_rect(Rect2(0, 0, UI.W, UI.H), Color(0, 0, 0, 0.55))
	UI.draw_round_rect(self, PANEL, Color8(24, 22, 32, 248), UI.AMBER, 2, 10)
	UI.draw_text(self, Loc.t("НАСТРОЙКИ"), Vector2(PANEL.get_center().x, PANEL.position.y + 30), 22, UI.AMBER, true, 1)
	var x := PANEL.position.x + 30
	var y := PANEL.position.y + 62
	UI.draw_text(self, Loc.t("Язык"), Vector2(x, y + 8), 17, UI.WHITE)
	UI.draw_text(self, Loc.t("ЗВУК"), Vector2(x, y + 60), 16, UI.CYAN, true)
	var labels := ["Общая громкость", "Музыка", "Эффекты"]
	for i in 3:
		UI.draw_text(self, Loc.t(labels[i]), Vector2(x, y + 92 + i * 44), 16, UI.WHITE)
	UI.draw_text(self, Loc.t("ДОСТУПНОСТЬ"), Vector2(x, y + 232), 16, UI.CYAN, true)
	UI.draw_text(self, Loc.t("Размер текста"), Vector2(x, y + 264), 16, UI.WHITE)
	UI.draw_text(self, Loc.t("Без анимации"), Vector2(x, y + 312), 16, UI.WHITE)
	UI.draw_wrapped(self, Loc.t("Шрифт для лёгкого чтения (Atkinson Hyperlegible)"), Vector2(x, y + 352), 300, 15, UI.WHITE)


func _build() -> void:
	var x := PANEL.position.x + 30
	var y := PANEL.position.y + 62
	var bx := PANEL.end.x - 30 - 220
	for i in 2:
		var code: String = ["ru", "en"][i]
		var b := GameButton.make(Rect2(bx + i * 116, y, 104, 36), code.to_upper(), UI.GHOST)
		b.name = "Lang_" + code
		b.active = Loc.code == code
		b.accessibility_name = "Русский" if code == "ru" else "English"
		b.pressed.connect(func() -> void:
			Audio.sfx("tick")
			Loc.set_lang(code))
		add_child(b)
		if b.active:
			_first = b
	var keys := ["master", "music", "sfx"]
	var labels := ["Общая громкость", "Музыка", "Эффекты"]
	for i in 3:
		var s := HSlider.new()
		s.name = "Vol_" + keys[i]
		s.min_value = 0
		s.max_value = 100
		s.step = 5
		s.value = float(Settings.vol[keys[i]]) * 100
		s.position = Vector2(bx, y + 92 + i * 44)
		s.size = Vector2(220, 24)
		s.focus_mode = Control.FOCUS_ALL
		s.accessibility_name = Loc.t(labels[i])
		_style_slider(s)
		var key: String = keys[i]
		s.value_changed.connect(func(v: float) -> void:
			Settings.set_vol(key, v / 100.0)
			if key == "sfx":
				Audio.sfx("tick"))
		add_child(s)
	var ks := ["100 %", "112 %", "125 %", "150 %"]
	for i in 4:
		var b := GameButton.make(Rect2(PANEL.end.x - 30 - 4 * 85 + 7 + i * 85, y + 258, 78, 34), ks[i], UI.CYAN)
		b.name = "Text_%d" % i
		b.label_size = 15
		b.active = int(Settings.a11y.get("text", 0)) == i
		b.accessibility_name = Loc.t("Размер текста") + " " + ks[i]
		b.pressed.connect(func() -> void:
			Audio.sfx("tick")
			Settings.set_a11y("text", i))
		add_child(b)
	_toggle("Calm", y + 306, "calm", "Без анимации")
	_toggle("Font", y + 354, "font", "Шрифт для лёгкого чтения (Atkinson Hyperlegible)")
	var done := GameButton.make(Rect2(PANEL.get_center().x - 100, PANEL.end.y - 62, 200, 44), "ГОТОВО", UI.AMBER)
	done.name = "Done"
	done.pressed.connect(close)
	add_child(done)
	if _first == null:
		_first = done
	queue_redraw()


func _toggle(nm: String, y: float, key: String, title: String) -> void:
	var on: bool = Settings.a11y.get(key, false)
	var b := GameButton.make(Rect2(PANEL.end.x - 30 - 110, y, 110, 34), "ВКЛ" if on else "ВЫКЛ", UI.GOOD if on else UI.GREY)
	b.name = nm
	b.active = on
	b.accessibility_name = Loc.t(title) + ": " + Loc.t("ВКЛ" if on else "ВЫКЛ")
	b.pressed.connect(func() -> void:
		Audio.sfx("tick")
		Settings.set_a11y(key, not Settings.a11y.get(key, false))
		_rebuild())
	add_child(b)


static func _style_slider(s: HSlider) -> void:
	var track := StyleBoxFlat.new()
	track.bg_color = Color8(50, 44, 64)
	track.set_corner_radius_all(4)
	track.content_margin_top = 4
	track.content_margin_bottom = 4
	var fill := track.duplicate() as StyleBoxFlat
	fill.bg_color = UI.AMBER
	s.add_theme_stylebox_override("slider", track)
	s.add_theme_stylebox_override("grabber_area", fill)
	s.add_theme_stylebox_override("grabber_area_highlight", fill)


func first_focus() -> Control:
	return _first


func close() -> void:
	Audio.sfx("tick")
	closed.emit()
	queue_free()


func _gui_input(_e: InputEvent) -> void:
	accept_event()                          # клики мимо элементов окна — не на экран под ним
