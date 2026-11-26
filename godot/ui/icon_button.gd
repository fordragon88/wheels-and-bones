class_name IconButton
extends GameButton
## Значки в углах экрана (как в game.py): «◂ назад» (8, 8), флажок ⚑ «Сообщить о неточности» (W−154),
## язык RU/EN (W−104), шестерёнка настроек (W−50). Полупрозрачная плашка, цвет значка — от призрачного к янтарному
## (у флажка — к фиолетовому) при наведении; у «назад» и флажка — подсказка под значком.

enum Kind { BACK, FLAG, LANG, GEAR }

var kind: Kind = Kind.GEAR
var tip: String = ""


static func make_icon(k: Kind) -> IconButton:
	var b := IconButton.new()
	b.kind = k
	match k:
		Kind.BACK:
			b.position = Vector2(8, 8)
			b.size = Vector2(38, 38)
			b.tip = "Назад (Esc)"
			b.label = "Назад"
			b.name = "Back"
		Kind.FLAG:
			b.position = Vector2(UI.W - 154, 8)
			b.size = Vector2(38, 38)
			b.tip = "Сообщить о неточности"
			b.label = "Сообщить о неточности"
			b.name = "Flag"
		Kind.LANG:
			b.position = Vector2(UI.W - 104, 8)
			b.size = Vector2(46, 38)
			b.name = "Lang"
		Kind.GEAR:
			b.position = Vector2(UI.W - 50, 8)
			b.size = Vector2(38, 38)
			b.label = "НАСТРОЙКИ"
			b.name = "Gear"
	if UI.phone():                             # телефонный режим: значки 56×56 от верха экрана, зазор 8
		var ph := {Kind.BACK: Rect2(4, 0, 56, 56), Kind.FLAG: Rect2(UI.W - 192, 0, 56, 56),
			Kind.LANG: Rect2(UI.W - 128, 0, 60, 56), Kind.GEAR: Rect2(UI.W - 60, 0, 56, 56)}
		b.position = ph[k].position
		b.size = ph[k].size
	if k != Kind.LANG:                         # Game._tap: «назад», ⚑, ⚙ на сенсоре шире пальца (язык — точно)
		b.touch_grow = UI.TOUCH_TAP_GROW
	UI.touch_skip(b)                           # не цель переноса тапа, но зона, где тап не трогают (Nav.touch_snap)
	b.update_a11y()
	if k == Kind.GEAR:                         # значок «без звука» и имя для чтеца — сразу после M (game.py рисует каждый кадр)
		Settings.changed.connect(b._on_settings)
	return b


func _on_settings(key: String) -> void:
	if key == "vol":
		update_a11y()
		queue_redraw()


func update_a11y() -> void:
	match kind:
		Kind.LANG:
			accessibility_name = Loc.t("Язык: русский. Переключить на английский") if Loc.code == "ru" \
				else "Language: English. Switch to Russian"
			set_meta("a11y_group", "Меню")
		Kind.GEAR:
			var on: bool = Settings.vol.get("on", true) and float(Settings.vol.get("master", 1)) > 0.001
			accessibility_name = Loc.t("Настройки: звук, графика, доступность") + ("" if on else ". " + Loc.t("Звук выключен"))
			set_meta("a11y_group", "Меню")
		Kind.FLAG:
			accessibility_name = Loc.t("Сообщить о неточности")
			set_meta("a11y_group", "Меню")
		_:
			accessibility_name = Loc.t("Назад")


func _draw() -> void:
	var h := hover_k
	var r := Rect2(Vector2.ZERO, size)
	if UI.phone():                             # плашка — в шапке (54 px), зона пальца — 56
		r = Rect2(0, 1, size.x, 52)
	UI.draw_round_rect(self, r, Color8(30, 28, 40, int(150 + 90 * h) if kind != Kind.BACK else int(170 + 80 * h)),
		Color(), 0, 10)
	var col := UI.lerp_color(UI.GHOST, UI.PURPLE if kind == Kind.FLAG else UI.AMBER, h)
	var c := r.get_center()
	var gk := 1.25 if UI.phone() else 1.0      # значок крупнее вместе с плашкой (подпись RU/EN — прежним кеглем)
	match kind:
		Kind.BACK:
			UI.draw_text(self, "◂", c + Vector2(-1, 0), roundi(24 * gk), col, true, 1)
		Kind.FLAG:
			UI.draw_text(self, "⚑", c, roundi(22 * gk), col, false, 1)
		Kind.LANG:
			UI.draw_text(self, "EN" if Loc.code == "en" else "RU", c, 15, col, true, 1)
		Kind.GEAR:
			var ang0 := float(Time.get_ticks_msec()) / 1000.0 * 0.8 * h
			var pts := PackedVector2Array()
			for i in 16:                   # 8 зубцов
				var a := ang0 + i * PI / 8.0
				var rad := (12.0 if i % 2 == 0 else 9.0) * gk
				pts.append(c + Vector2(cos(a), sin(a)) * rad)
			draw_colored_polygon(pts, col)
			draw_circle(c, 9 * gk, col, true, -1.0, true)
			draw_circle(c, 4 * gk, Color8(30, 28, 40), true, -1.0, true)
			if not Settings.vol.get("on", true) or float(Settings.vol.get("master", 1.0)) <= 0.001:
				var s := Vector2(-20 - ((68 if UI.phone() else 54) if get_meta("lang_left", false) else 0), size.y / 2.0)
				draw_rect(Rect2(s + Vector2(-9, -4), Vector2(6, 8)), UI.GHOST)
				draw_colored_polygon(PackedVector2Array([s + Vector2(-3, -4), s + Vector2(4, -10), s + Vector2(4, 10),
					s + Vector2(-3, 4)]), UI.GHOST)
				draw_line(s + Vector2(-11, -11), s + Vector2(9, 11), UI.BAD, 3.0, true)
	if is_hovered() and tip != "":
		var tt := Loc.t(tip)
		var w := UI.text_width(tt, 13) + 16
		var tr := Rect2(Vector2(size.x - w if kind != Kind.BACK else 0.0, size.y + 6), Vector2(w, 24))
		UI.draw_round_rect(self, tr, Color8(18, 16, 24, 240), Color(), 0, 6)
		UI.draw_text(self, tt, tr.get_center(), 13, UI.WHITE, false, 1)
	if has_focus() and UI.kb_active:
		UI.draw_round_rect(self, r.grow(3), Color(0, 0, 0, 0), UI.WHITE, 2, 12)


func _process(dt: float) -> void:
	super._process(dt)
	if kind == Kind.GEAR and hover_k > 0.01:
		queue_redraw()
