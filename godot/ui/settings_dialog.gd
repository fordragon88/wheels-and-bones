class_name SettingsDialog
extends Control
## Окно настроек (_draw_sound_panel/handle_sound_event в game.py): вкладки ЗВУК, ГРАФИКА, ДОСТУПНОСТЬ, ИГРА.
##   ЗВУК — громкости (общая, музыка, эффекты, атмосфера сцен), «БЕЗ ЗВУКА / ВКЛЮЧИТЬ ЗВУК».
##   ГРАФИКА — в окне / весь экран (F11, Alt+Enter), «Свечение и частицы». (Разрешения рендера и 3D через видеокарту
##             в Godot нет: картинка всегда в разрешении экрана — пункты не показываются.)
##   ДОСТУПНОСТЬ — озвучка, реплики вслух, скорость голоса (значения хранятся, сама озвучка — позже), контрастный
##             фон, текст сразу, без анимации, клиент: одна фраза, призрак Барти, размер текста, лёгкий шрифт.
##   ИГРА — прогресс, коды и ссылки (_share_set_rects: «СКОПИРОВАТЬ КОД», «ВСТАВИТЬ КОД», «ССЫЛКА-ЗАДАНИЕ», в браузере —
##             «ССЫЛКА С ПРОГРЕССОМ», «ВЕРНУТЬ ПРЕЖНИЙ ПРОГРЕСС», пока есть копия) и «СБРОСИТЬ ПРОГРЕСС» с подтверждением.
## Справа — карточка «что делает эта настройка» (наведение или фокус). Esc / «ГОТОВО» — закрыть.

signal closed

const P := Rect2(UI.W / 2.0 - 290, UI.H / 2.0 - 250, 580, 500)
const TABS := ["sound", "graphics", "access", "game"]
const TAB_NAMES := {"sound": "ЗВУК", "graphics": "ГРАФИКА", "access": "ДОСТУПНОСТЬ", "game": "ИГРА"}
const ACCESS_ROWS := ["on", "voices", "rate", "contrast", "instant", "calm", "quiet", "barty", "text", "font"]
const ACCESS_NAMES := {"on": "Озвучка (F2)", "voices": "Реплики героев вслух", "rate": "Скорость голоса",
	"contrast": "Контрастный фон", "instant": "Текст сразу", "calm": "Без анимации", "quiet": "Клиент: одна фраза",
	"barty": "Призрак Барти", "text": "Размер текста", "font": "Лёгкий шрифт"}
const SHARE_LABELS := {"share_code": "СКОПИРОВАТЬ КОД", "share_paste": "ВСТАВИТЬ КОД", "share_build": "ССЫЛКА-ЗАДАНИЕ",
	"share_link": "ССЫЛКА С ПРОГРЕССОМ", "share_restore": "ВЕРНУТЬ ПРЕЖНИЙ ПРОГРЕСС"}
const VOL_NAMES := {"master": "Общая громкость", "music": "Музыка", "sfx": "Эффекты", "amb": "Атмосфера сцен"}

static var tab: String = "sound"

var reset_ask: bool = false
var _first: Control
var _help: Control
var _zones: Array = []                      # [ключ подсказки, строка настройки, элемент]


func _init() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	name = "Settings"


func _ready() -> void:
	Settings.changed.connect(_on_settings)
	Loc.changed.connect(_rebuild)
	_build()


func _on_settings(key: String) -> void:
	if key in ["text", "font", "lang", "calm", "contrast", "vol", "glow"]:
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


func _btn(nm: String, r: Rect2, lbl: String, col: Color, cb: Callable, active := false, help := "") -> GameButton:
	var b := GameButton.make(r, lbl, col)
	b.name = nm
	b.active = active
	b.pressed.connect(cb)
	add_child(b)
	if help != "":
		_zones.append([help, Rect2(P.position.x + 24, r.position.y - 4, P.size.x - 48, r.size.y + 8), b])
	return b


func _build() -> void:
	_zones.clear()
	_first = null
	for i in TABS.size():
		var tb: String = TABS[i]
		var b := _btn("Tab_" + tb, Rect2(P.position.x + 32 + i * 130, P.position.y + 64, 122, 36), TAB_NAMES[tb], UI.CYAN,
			func() -> void:
				Audio.sfx("tick")
				tab = tb
				reset_ask = false
				_rebuild(), tb == tab)
		b.accessibility_name = Loc.t({"sound": "Вкладка: звук", "graphics": "Вкладка: графика", "access": "Вкладка: доступность",
			"game": "Вкладка: игра и прогресс"}[tb]) + (", " + Loc.t("открыта") if tb == tab else "")
		b.set_meta("a11y_group", "Вкладки")
		if tb == tab:
			_first = b
	match tab:
		"sound":
			var keys := ["master", "music", "sfx", "amb"]
			for i in 4:
				var key: String = keys[i]
				var s := VolSlider.new()
				s.name = "Vol_" + key
				s.position = Vector2(P.position.x + 225 - 12, P.position.y + 146 + i * 58 - 16)
				s.size = Vector2(230 + 24, 40)
				s.value = float(Settings.vol[key])
				s.muted = not Settings.vol.get("on", true)
				s.set_meta("a11y_group", "Громкость")
				s.accessibility_name = "%s: %d%%" % [Loc.t(VOL_NAMES[key]), int(s.value * 100)]   # как a11y_items
				s.changed.connect(func(v: float) -> void:
					s.accessibility_name = "%s: %d%%" % [Loc.t(VOL_NAMES[key]), int(v * 100)]
					Settings.vol[key] = v
					Settings.save()
					Audio.apply_volume()
					queue_redraw())
				UI.touch_block(s, Vector2(0, -1))     # handle_sound_event: block — дорожка 230×8 inflate(24, 30)
				add_child(s)
				_zones.append(["vol_" + key, Rect2(P.position.x + 24, P.position.y + 146 + i * 58 - 20, P.size.x - 48, 40), s])
			var on: bool = Settings.vol.get("on", true)
			_btn("Mute", Rect2(P.position.x + 32, P.end.y - 70, 220, 44), "БЕЗ ЗВУКА" if on else "ВКЛЮЧИТЬ ЗВУК",
				UI.GREY if on else UI.GOOD, func() -> void:
					Audio.toggle_sound()
					Audio.sfx("tick"), false, "mute")
		"graphics":
			var fs := DisplayServer.window_get_mode() == DisplayServer.WINDOW_MODE_FULLSCREEN
			if OS.has_feature("web"):
				_btn("Fullscreen", Rect2(P.position.x + 230, P.position.y + 196, 230, 38), "ВКЛ / ВЫКЛ  (F11)", UI.AMBER,
					func() -> void: Nav._toggle_fullscreen(), false, "web_fs")
			else:
				for i in 2:
					var full := i == 1
					_btn("Mode_%d" % i, Rect2(P.position.x + 230 + i * 160, P.position.y + 128, 150, 38),
						"ВЕСЬ ЭКРАН" if full else "В ОКНЕ", UI.CYAN, func() -> void:
							Audio.sfx("tick")
							if full != (DisplayServer.window_get_mode() == DisplayServer.WINDOW_MODE_FULLSCREEN):
								Nav._toggle_fullscreen()
							_rebuild(), full == fs, "mode")
			_btn("Glow", Rect2(P.position.x + 310, P.position.y + 320, 216, 38), "ВКЛ" if Settings.glow else "ВЫКЛ",
				UI.AMBER if Settings.glow else UI.GREY, func() -> void:
					Audio.sfx("tick")
					Settings.glow = not Settings.glow
					Settings.save()
					Settings.changed.emit("glow"), Settings.glow, "glow")
		"access":
			for i in ACCESS_ROWS.size():
				var k: String = ACCESS_ROWS[i]
				var r := Rect2(P.position.x + 330, P.position.y + 102 + i * 27, 216, 24)
				var label := _access_value(k)
				var on := k in ["rate", "text"] or _access_on(k)
				var b := _btn("Acc_" + k, r, label, UI.GOOD if on else UI.GREY, _access_toggle.bind(k),
					on and not k in ["rate", "text"])
				b.label_size = 14
				b.accessibility_name = _access_label(k)
				b.set_meta("a11y_group", "Доступность")
				_zones.append(["acc_" + k, Rect2(P.position.x + 24, r.position.y - 1, r.end.x - P.position.x - 24, r.size.y + 2), b])
		"game":
			@warning_ignore("integer_division")
			var sw := int((P.size.x - 64 - 12) / 2)
			var col := func(i: int) -> float: return P.position.x + 32 + i * (sw + 12)
			var specs: Array = [["share_code", Rect2(col.call(0), P.position.y + 212, sw, 40)],
				["share_paste", Rect2(col.call(1), P.position.y + 212, sw, 40)],
				["share_build", Rect2(col.call(0), P.position.y + 258, sw, 40)]]
			if OS.has_feature("web"):
				specs.append(["share_link", Rect2(col.call(1), P.position.y + 258, sw, 40)])
			if SaveGame.has_backup() and not reset_ask:
				specs.append(["share_restore", Rect2(col.call(0), P.position.y + 304, P.size.x - 64, 40)])
			for sp: Array in specs:
				var k: String = sp[0]
				_btn("Share_" + k.trim_prefix("share_"), sp[1], SHARE_LABELS[k], UI.PURPLE if k == "share_restore" else UI.CYAN,
					_share_action.bind(k))
			if reset_ask:
				var w := (P.size.x - 80) / 2
				_btn("ResetYes", Rect2(P.position.x + 32, P.position.y + 352, w, 42), "ДА, СБРОСИТЬ", UI.BAD, reset_progress)
				_btn("ResetNo", Rect2(P.end.x - 32 - w, P.position.y + 352, w, 42), "НЕТ", UI.GOOD, func() -> void:
					reset_ask = false
					Audio.sfx("tick")
					Speech.say(Loc.t("Сброс отменён."), true)
					_rebuild())
			else:
				_btn("Reset", Rect2(P.position.x + 32, P.position.y + 352, P.size.x - 64, 42), "СБРОСИТЬ ПРОГРЕСС", UI.BAD,
					func() -> void:
						reset_ask = true
						Audio.sfx("bad")
						Speech.say(Loc.t("Сбросить весь прогресс? Это нельзя отменить. Да или нет."), true)
						_rebuild(), false, "reset")
	var done := _btn("Done", Rect2(P.end.x - 192, P.end.y - 70, 160, 44), "ГОТОВО", UI.AMBER, close)
	if _first == null:
		_first = done
	_help = Control.new()
	_help.name = "Help"
	_help.size = size
	_help.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_help.draw.connect(_draw_help)
	add_child(_help)
	queue_redraw()


## Кнопки кодов и ссылок вкладки «ИГРА» (_share_set_action).
func _share_action(k: String) -> void:
	match k:
		"share_code":
			Share.copy_progress_code()
		"share_paste":
			Share.open({"mode": "paste"})
		"share_build":
			Share.open({"mode": "builder"})
		"share_link":
			Share.copy_progress_link()
		"share_restore":
			SaveGame.restore_backup()
			Audio.sfx("whoosh")
			close()
			if Nav.current_name != "title":
				Nav.go("hub")
			Nav.flash("Прежний прогресс возвращён.", UI.GOOD, 4.0)


func _access_on(k: String) -> bool:
	if k == "quiet":
		return Settings.quiet_talk()
	if k == "barty":
		return Settings.barty_on()
	return bool(Settings.a11y.get(k, false))


func _text_pct() -> int:
	return roundi(100 * Settings.TEXT_K[clampi(int(Settings.a11y.get("text", 0)), 0, Settings.TEXT_K.size() - 1)])


func _access_value(k: String) -> String:
	if k == "rate":
		return str(Settings.a11y.get("rate", 0))
	if k == "text":
		return "%d%%" % _text_pct()
	return "ВКЛ" if _access_on(k) else "ВЫКЛ"


## Подпись пункта для чтеца экрана (_access_label).
func _access_label(k: String) -> String:
	var on := Loc.t("включено") if _access_on(k) else Loc.t("выключено")
	match k:
		"on":
			return "%s: %s. F2" % [Loc.t("Озвучка"), Loc.t("включена") if Settings.a11y.get("on", false) else Loc.t("выключена")]
		"voices":
			return "%s: %s" % [Loc.t("Реплики персонажей вслух"), on]
		"rate":
			return "%s: %s. %s" % [Loc.t("Скорость голоса Windows"), Settings.a11y.get("rate", 0),
				Loc.t("Enter — быстрее, после 10 — снова медленно")]
		"contrast":
			return "%s: %s" % [Loc.t("Тёмный контрастный фон"), on]
		"text":
			return "%s: %d%%" % [Loc.t("Размер текста"), _text_pct()]
		"calm":
			return "%s: %s" % [Loc.t("Без анимации"), on]
		"quiet":
			return "%s: %s" % [Loc.t("Клиент говорит только одну фразу при входе"), on]
		"barty":
			return "%s: %s" % [Loc.t("Призрак Барти и его шутки в мастерской"), on]
		"font":
			return "%s: %s" % [Loc.t("Шрифт для лёгкого чтения (Atkinson Hyperlegible)"), on] + \
				("" if Loc.code == "en" else ". " + Loc.t("Только для английского языка"))
	return "%s: %s" % [Loc.t("Текст сразу, без печати по буквам"), on]


## Переключить пункт доступности (_access_toggle).
func _access_toggle(k: String) -> void:
	match k:
		"on":
			A11y.toggle_speech()
			Audio.sfx("tick")
			_rebuild()
			return
		"rate":
			var r := int(Settings.a11y.get("rate", 0))
			Settings.set_a11y("rate", mini(10, r + 2) if r < 10 else -4)
			Speech.set_voice()
			Speech.say("%s: %d" % [Loc.t("Скорость"), int(Settings.a11y["rate"])], true)
			Audio.sfx("tick")
			_rebuild()
			return
		"text":
			Settings.set_a11y("text", (int(Settings.a11y.get("text", 0)) + 1) % Settings.TEXT_K.size())
		"quiet":
			Settings.a11y["quiet_set"] = true
			Settings.set_a11y("quiet", not Settings.quiet_talk())
		_:
			Settings.set_a11y(k, not bool(Settings.a11y.get(k, false)))
	Audio.sfx("tick")
	Speech.say(_access_label(k), true)
	_rebuild()


func reset_progress() -> void:
	reset_ask = false
	SaveGame.reset_progress()
	SaveGame.save()
	close()
	Audio.sfx("whoosh")
	Nav.go("title")
	Nav.flash("Прогресс сброшен. Начинаем с начала — настройки сохранены.", UI.AMBER, 4.0)


func first_focus() -> Control:
	return _first


func close() -> void:
	Audio.sfx("tick")
	closed.emit()
	queue_free()


func _gui_input(_e: InputEvent) -> void:
	accept_event()                          # клики мимо элементов окна — не на экран под ним


func _process(_dt: float) -> void:
	Screen.redraw_on(_help, [_help_zone(), UI.kb_active, tab, _zones.size()])   # карточка — только когда сменился пункт


## Пункт под мышью (или в фокусе клавиатуры), о котором карточка справа; -1 — нет.
func _help_zone() -> int:
	var fo := get_viewport().gui_get_focus_owner()
	for i in _zones.size():
		var z: Array = _zones[i]
		var ctl: Control = z[2]
		if (UI.kb_active and fo == ctl) or (not UI.kb_active and (z[1] as Rect2).has_point(get_local_mouse_position())):
			return i
	return -1


func progress_summary() -> PackedStringArray:
	var g := Loc.tf("Гильдия: {0} из {1}", [SaveGame.tech_done_count(), Content.tech_jobs.size()])
	if SaveGame.exam_passed:
		g += Loc.t(", диплом получен")
	var s := Loc.tf("Кабинет посадки: примерки {0}/{1}", [SaveGame.seat_done.size(), 9])
	if SaveGame.seat_quiz_ok:
		s += Loc.t(" · зачёт ✔")
	return [Loc.tf("Починено колясок: {0} из {1}", [SaveGame.user_done_count(), Content.jobs.size()]), g, s]


func _draw() -> void:
	draw_rect(Rect2(0, 0, UI.W, UI.H), Color8(8, 8, 12, 168))
	UI.draw_round_rect(self, P, Color8(18, 18, 26, 250), UI.AMBER, 2, 14)
	UI.draw_text(self, Loc.t("НАСТРОЙКИ"), P.position + Vector2(32, 22), 24, UI.AMBER, true)
	var x := P.position.x + 32
	match tab:
		"sound":
			var muted: bool = not Settings.vol.get("on", true)
			var keys := ["master", "music", "sfx", "amb"]
			for i in 4:
				var y := P.position.y + 146 + i * 58
				UI.draw_text_w(self, Loc.t(VOL_NAMES[keys[i]]), Vector2(x, y - 8), P.position.x + 225 - 14 - x, 17,
					UI.GREY if muted else UI.WHITE)               # 150 %: подпись не касается ползунка
				UI.draw_text(self, "%d%%" % int(float(Settings.vol[keys[i]]) * 100), Vector2(P.position.x + 225 + 230 + 56, y - 8), 16,
					UI.GREY if muted else UI.WHITE, false, 2)
			UI.draw_text(self, Loc.t("M — быстро выключить / включить звук"), Vector2(x, P.position.y + 374), 13, UI.GREY)
			UI.draw_text(self, Loc.t("За работой мелодия через минуту стихает до фона"), Vector2(x, P.position.y + 392), 13, UI.GREY)
		"graphics":
			if OS.has_feature("web"):
				UI.draw_text(self, Loc.t("Полный экран"), Vector2(x, P.position.y + 205), 17, UI.WHITE)
			else:
				UI.draw_text(self, Loc.t("Режим экрана"), Vector2(x, P.position.y + 137), 17, UI.WHITE)
				UI.draw_text(self, Loc.t("F11 или Alt+Enter — переключить"), Vector2(P.position.x + 230, P.position.y + 172), 12, UI.GREY)
			UI.draw_text(self, Loc.t("Свечение и частицы"), Vector2(x, P.position.y + 329), 17, UI.WHITE)
		"access":
			var last := 0.0
			for i in ACCESS_ROWS.size():
				var r := Rect2(P.position.x + 330, P.position.y + 102 + i * 27, 216, 24)
				UI.draw_text(self, Loc.t(ACCESS_NAMES[ACCESS_ROWS[i]]), Vector2(x, r.get_center().y - floorf(UI.line_height(16) / 2)),
					16, UI.WHITE)
				last = r.end.y
			var y0 := last + 6
			var tw := (P.end.x - 192) - P.position.x - 48
			var note := Loc.t("Вся игра проходится с клавиатуры: стрелки, Tab, Enter. F1 — все клавиши.")
			var sz := 10
			for s: int in [13, 12, 11, 10]:
				sz = s
				var lh := UI.line_height(s)
				if y0 + lh + 2 + UI.wrap_lines(note, tw, s).size() * (lh + 2) <= P.end.y - 8:
					break
			UI.draw_text(self, Loc.t("Озвучка: " + Speech.label()), Vector2(x, y0), sz, UI.GREY)
			UI.draw_wrapped(self, note, Vector2(x, y0 + UI.line_height(sz) + 2), tw, sz, UI.GREY, false, 2, -1,
				maxi(1, int((P.end.y - 8 - y0) / (UI.line_height(sz) + 2)) - 1))
		"game":
			UI.draw_text(self, Loc.t("Прогресс"), Vector2(x, P.position.y + 114), 19, UI.WHITE, true)
			var y := P.position.y + 142
			for line in progress_summary():
				UI.draw_text(self, line, Vector2(x, y), 15, UI.GREY)
				y += 22
			if reset_ask:
				UI.draw_text(self, Loc.t("Сбросить весь прогресс? Это нельзя отменить."), Vector2(x, P.position.y + 318), 16, UI.BAD, true)
			UI.draw_wrapped(self, Loc.t("Сотрёт починенные коляски, гараж, Гильдию и Кабинет посадки. Звук, графика, язык и доступность останутся."),
				Vector2(x, P.position.y + 402), P.size.x - 64 - 210, 12, UI.GREY, false, 2, -1, 4)


## Карточка «что делает настройка» справа от окна (_draw_setting_help): пункт в фокусе клавиатуры или под мышью.
func _draw_help() -> void:
	var hi := _help_zone()
	if hi < 0:
		return
	var hit: Array = _zones[hi]
	var text := Loc.t(Content.consts.get("setting_help", {}).get(hit[0], ""))
	if text == "":
		return
	var zone: Rect2 = hit[1]
	var x := P.end.x + 10
	var w := UI.W - P.end.x - 18
	var sz := 12
	var h := 0.0
	for s: int in [15, 14, 13, 12]:
		sz = s
		h = UI.wrap_lines(text, w - 24, s).size() * (UI.line_height(s) + 2) + 18
		if h <= UI.H - 16:
			break
	var y := maxf(8, minf(zone.get_center().y - h / 2, UI.H - 8 - h))
	var box := Rect2(x, y, w, h)
	UI.draw_round_rect(_help, box, Color8(24, 26, 36, 250), UI.CYAN, 2, 10)
	_help.draw_line(Vector2(P.end.x - 2, zone.get_center().y), Vector2(x, maxf(y + 12, minf(zone.get_center().y, y + h - 12))),
		UI.CYAN, 2.0)
	UI.draw_wrapped(_help, text, box.position + Vector2(12, 9), w - 24, sz, UI.WHITE)
