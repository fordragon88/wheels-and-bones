extends Node
## Находки внешней проверки 26.11 — клавиатура, окна, чтец экрана, ввод (E7–E13, E15, E18, E20, E21, E26, E27, E29):
## каждая проверка падала до починки. Зовёт самопроверка (tests/selftest_runner.gd, и отдельно
## «-- --test --only review-kb»). run(R) → строка для итога; ошибки — R.err().

var R: Node
var said: Array[String] = []                   # что сказала озвучка за проверку (Speech.history — не больше 200)


func _on_spoke(text: String) -> void:
	said.append(text)


func run(runner: Node) -> String:
	R = runner
	Speech.spoke.connect(_on_spoke)
	var done: PackedStringArray = []
	var lang0 := Loc.code
	if Loc.code != "ru":
		Loc.set_lang("ru")
	SaveGame.reset()
	SaveGame.tutorial_skipped = true
	await _e7_settings_rebuild()
	done.append("смена настройки не уводит фокус под окно (E7)")
	await _e21_kb_cur()
	done.append("↓ после переключателя — следующий пункт (E21)")
	await _e9_layers()
	done.append("справка над замечанием и настройками, Start, карточка гаража (E9)")
	await _e8_manual_over_spec()
	done.append("мануал из спеки — свои пункты (E8)")
	await _e12_header()
	done.append("шапка поверх окон задания (E12)")
	await _e18_wheel()
	done.append("колёсико не гасит улику и не закрывает окна (E18)")
	await _e10_e11_keys()
	done.append("Enter/пробел/A закрывают справку, F2/R/F11 в окнах (E10, E11)")
	await _e13_twice()
	done.append("двойная отправка, Alt+Enter в комментарии (E13)")
	await _e20_stick()
	done.append("дрожь стика (E20)")
	await _e15_speech()
	done.append("голос при RU/EN, чтец включает озвучку, повтор фразы (E15)")
	await _e26_e27_settings()
	done.append("значок без звука, ползунок громкости вслух, подсказки, Esc при вопросе (E26, E27)")
	await _e29_misc()
	done.append("коляска ← →/R, сообщение на титрах и при RU/EN (E29)")
	if Loc.code != lang0:
		Loc.set_lang(lang0)
	Nav.go("hub")
	await _frames(2)
	Speech.spoke.disconnect(_on_spoke)
	return "внешняя проверка 26.11 (клавиатура и окна): " + ", ".join(done)


func _fail(msg: String) -> void:
	R.err("внешняя проверка 26.11: " + msg)


func _frames(n: int) -> void:
	for i in n:
		await get_tree().process_frame


func _key(code: Key, unicode: int = 0, alt: bool = false) -> void:
	for pressed: bool in [true, false]:
		var e := InputEventKey.new()
		e.keycode = code
		e.physical_keycode = code
		e.unicode = unicode
		e.alt_pressed = alt
		e.pressed = pressed
		get_viewport().push_input(e)
	await get_tree().process_frame


func _pad_button(b: JoyButton) -> void:
	for pressed: bool in [true, false]:
		var e := InputEventJoypadButton.new()
		e.button_index = b
		e.pressed = pressed
		get_viewport().push_input(e)
		await get_tree().process_frame
	await _frames(2)                              # клавиша геймпада приходит отложенно (Nav._pad_key)


func _mouse(pos: Vector2, button: MouseButton = MOUSE_BUTTON_LEFT) -> void:
	var m := InputEventMouseMotion.new()
	m.position = pos
	m.global_position = pos
	get_viewport().push_input(m, true)
	for pressed: bool in [true, false]:
		var e := InputEventMouseButton.new()
		e.button_index = button
		e.pressed = pressed
		e.position = pos
		e.global_position = pos
		get_viewport().push_input(e, true)
	await get_tree().process_frame


func _fo() -> Control:
	return get_viewport().gui_get_focus_owner()


func _fo_name() -> String:
	var f := _fo()
	return str(f.get_path()) if f != null else "null"


func _close_all() -> void:
	if Nav.help != null:
		Nav.toggle_help()
	if Nav.feedback != null:
		Nav.feedback.close()
	if Share.dlg != null:
		Share.close()
	if Nav.settings != null:
		Nav.close_settings()
	await _frames(2)


# ---- E7: пункт доступности, пересобирающий экран, — фокус остаётся в окне настроек ----
func _e7_settings_rebuild() -> void:
	Nav.go("hub")
	await _frames(2)
	Nav.open_settings()
	await _frames(2)
	Nav.settings.get_node("Tab_access").pressed.emit()
	await _frames(2)
	(Nav.settings.get_node("Acc_text") as Control).grab_focus()
	await _frames(1)
	await _key(KEY_ENTER)
	await _frames(2)
	var f := _fo()
	if Nav.settings == null or f == null or not Nav.settings.is_ancestor_of(f) or f.name != "Acc_text":
		_fail("E7: после Enter на «Размер текста» фокус %s (ждали Settings/Acc_text)" % _fo_name())
	await _key(KEY_ENTER)
	await _frames(2)
	if Nav.current_name != "hub" or Nav.settings == null:
		_fail("E7: второй Enter открыл «%s», настройки открыты: %s" % [Nav.current_name, Nav.settings != null])
	# экран под окном пересобран — фокуса у его кнопок нет
	for c: Control in A11y.focusables(Nav.current):
		_fail("E7: у кнопки экрана под настройками фокус включён: %s" % c.name)
		break
	if Nav.settings != null:
		(Nav.settings.get_node("Acc_calm") as BaseButton).pressed.emit()
		await _frames(2)
		f = _fo()
		if f == null or not Nav.settings.is_ancestor_of(f):
			_fail("E7: «Без анимации» нажатием — фокус %s (ждали в настройках)" % _fo_name())
	await _close_all()
	Settings.set_a11y("text", 0)
	Settings.set_a11y("calm", false)
	await _frames(2)
	# мини-игра в задании, поверх — настройки: пересборка экрана не включает фокус мини-игре под настройками
	Nav.go("job", {"job": "flat", "variant": 0})
	await _frames(2)
	var js: Node = Nav.current
	js.phase = "repair"
	for st: Dictionary in js.steps():
		if st.get("mini") is Dictionary:
			js.start_mini(st)
			break
	await _frames(2)
	Nav.open_settings()
	await _frames(2)
	Settings.set_a11y("contrast", not Settings.a11y.get("contrast", false))
	await _frames(3)
	f = _fo()
	if f == null or not Nav.settings.is_ancestor_of(f):
		_fail("E7: мини-игра под настройками, контраст — фокус %s" % _fo_name())
	if js.mini != null and not A11y.focusables(js.mini).is_empty():
		_fail("E7: у мини-игры под настройками включён фокус")
	Nav.close_settings()
	await _frames(2)
	if js.mini != null:
		f = _fo()
		if f == null or not js.mini.is_ancestor_of(f):
			_fail("E7: настройки закрыты над мини-игрой — фокус %s (ждали в мини-игре)" % _fo_name())
		if A11y.focusables(js).filter(func(c: Control) -> bool: return not js.mini.is_ancestor_of(c)).size() > 1:
			_fail("E7: после настроек у экрана под мини-игрой включился фокус")
	Settings.set_a11y("contrast", not Settings.a11y.get("contrast", false))
	await _frames(2)
	js.close_mini()
	await _frames(2)


# ---- E21: пункт клавиатуры переживает пересборку окна ----
func _e21_kb_cur() -> void:
	Nav.go("hub")
	await _frames(2)
	Nav.open_settings()
	await _frames(2)
	Nav.settings.get_node("Tab_access").pressed.emit()
	await _frames(3)
	var names: Array = A11y.kb_items().map(func(c: Control) -> String: return str(c.name))
	var target := names.find("Acc_quiet")
	for i in target + 1:
		await _key(KEY_DOWN)
	await _frames(1)
	var q0: bool = Settings.quiet_talk()
	await _key(KEY_ENTER)
	await _frames(3)
	if not is_instance_valid(A11y.kb_cur) or A11y.kb_cur.name != "Acc_quiet":
		_fail("E21: после Enter пункт клавиатуры потерян")
	await _key(KEY_DOWN)
	await _frames(1)
	if _fo() == null or _fo().name != "Acc_barty":
		_fail("E21: ↓ после Enter на «Клиент: одна фраза» — %s (ждали Acc_barty)" % _fo_name())
	if Settings.quiet_talk() != q0:
		Settings.a11y["quiet_set"] = true
		Settings.set_a11y("quiet", q0)
	await _close_all()
	# окно кодов: «СНЯТЬ ВСЁ» пересобирает окно — пункт клавиатуры и фокус те же
	Share.open({"mode": "builder"})
	await _frames(3)
	var clear := Share.dlg.get_node("Btn_clear") as Control
	A11y.kb_focus(clear)
	await _frames(1)
	await _key(KEY_ENTER)
	await _frames(3)
	if not is_instance_valid(A11y.kb_cur) or A11y.kb_cur.name != "Btn_clear":
		_fail("E21: окно кодов после «СНЯТЬ ВСЁ» — пункт клавиатуры потерян")
	if _fo() == null or _fo().name != "Btn_clear":
		_fail("E21: окно кодов после «СНЯТЬ ВСЁ» — фокус %s" % _fo_name())
	await _close_all()


# ---- E9: окна друг над другом ----
func _e9_layers() -> void:
	Nav.go("hub")
	await _frames(2)
	# (1) справка над замечанием: буквы и Enter не уходят в замечание; закрыли — фокус снова в поле
	var sent := [0]
	Nav.open_feedback({"kind": "general", "scene": "hub"}, func(s: bool, _o: bool) -> void: sent[0] += 1 if s else 0)
	await _frames(2)
	var fb: FeedbackDialog = Nav.feedback
	(fb.text as Control).grab_focus()
	await _frames(1)
	await _key(KEY_F1)
	await _key(KEY_A, 97)
	if fb.text.text != "":
		_fail("E9: буква под справкой ушла в комментарий: «%s»" % fb.text.text)
	await _key(KEY_ENTER)
	await _frames(2)
	if sent[0] != 0 or Nav.feedback == null:
		_fail("E9: Enter под справкой отправил замечание")
	if Nav.help != null:
		_fail("E9: Enter не закрыл справку над замечанием")
	elif _fo() != fb.text:
		_fail("E9: справка закрыта — фокус %s (ждали поле комментария)" % _fo_name())
	await _close_all()
	# (2) справка над настройками: Esc — фокус в настройках, Enter не открывает задание
	Nav.open_settings()
	await _frames(2)
	await _key(KEY_F1)
	await _key(KEY_ESCAPE)
	await _frames(2)
	var f := _fo()
	if Nav.settings == null or f == null or not Nav.settings.is_ancestor_of(f):
		_fail("E9: F1→Esc над настройками — фокус %s" % _fo_name())
	await _key(KEY_ENTER)
	await _frames(2)
	if Nav.current_name != "hub" or Nav.settings == null:
		_fail("E9: Enter после справки над настройками — экран %s, настройки %s" % [Nav.current_name, Nav.settings != null])
	# (3) Start при справке над настройками — ничего не закрывает
	await _key(KEY_F1)
	await _pad_button(JOY_BUTTON_START)
	if Nav.settings == null or Nav.help == null:
		_fail("E9: Start при справке над настройками закрыл настройки (help=%s)" % [Nav.help != null])
	await _close_all()
	UI.kb_active = false
	# (4) гараж: RU/EN при открытой карточке — карточки под окном без фокуса, подписи окна на новом языке
	SaveGame.mark_job("flat", 3)
	Nav.go("garage")
	await _frames(2)
	var g: Node = Nav.current
	g.open_card(0)
	await _frames(2)
	Loc.toggle()
	await _frames(2)
	g = Nav.current
	for c: Control in g._cards:
		if c.focus_mode != Control.FOCUS_NONE:
			_fail("E9: гараж после RU/EN при открытой карточке — у карточки %s фокус" % c.name)
			break
	if str(g._popup.accessibility_name) != Loc.t(Content.job_by_id(SaveGame.garage[0][0]).get("client", "")) \
			or str(g._popup.accessibility_name) == "":
		_fail("E9: гараж после RU/EN — имя окна урока «%s»" % g._popup.accessibility_name)
	Loc.toggle()
	await _frames(2)
	Nav.current.close_card()
	Nav.go("hub")
	await _frames(1)
	SaveGame.reset()
	SaveGame.tutorial_skipped = true
	await _frames(1)


# ---- E8: мануал из спеки — его пункты ----
func _e8_manual_over_spec() -> void:
	Nav.go("tech", {"job": "truing"})
	await _frames(2)
	var ts: Node = Nav.current
	var spec_st: Dictionary = {}
	for st: Dictionary in ts.job["steps"]:
		if st.get("spec") is Dictionary:
			spec_st = st
			break
	ts.open_spec(spec_st)
	await _frames(2)
	ts.spec_dlg.open_manual.emit(str(spec_st["spec"].get("manual", "")))
	await _frames(2)
	if A11y.active_root() != ts.manual_dlg:
		_fail("E8: мануал из спеки — пункты клавиатуры у %s" % A11y.active_root().name)
	var names: Array = A11y.kb_items().map(func(c: Control) -> String: return str(c.name))
	if names.size() < 3:
		_fail("E8: в мануале из спеки пунктов клавиатуры %s" % [names])
	await _key(KEY_DOWN)
	var f := _fo()
	if f == null or not ts.manual_dlg.is_ancestor_of(f) and f.name != "Back":
		_fail("E8: ↓ в мануале из спеки — фокус %s" % _fo_name())
	ts.manual_dlg.close()
	await _frames(2)
	f = _fo()
	if ts.spec_dlg == null or f == null or not ts.spec_dlg.is_ancestor_of(f):
		_fail("E8: мануал закрыт — фокус %s (ждали в спеке)" % _fo_name())
	ts.close_spec()
	await _frames(2)


# ---- E12: «Я НЕ СОГЛАСЕН», ⚙ нажимаются поверх мини-игры и спеки ----
func _e12_header() -> void:
	UI.kb_active = false
	Nav.go("job", {"job": "flat", "variant": 0})
	await _frames(2)
	var js: Node = Nav.current
	js.phase = "repair"
	for st: Dictionary in js.steps():
		if st.get("mini") is Dictionary:
			js.start_mini(st)
			break
	await _frames(2)
	js.note_dispute("mistake", "", "", "проверка")
	await _frames(2)
	await _mouse((js._dispute_btn as Control).get_global_rect().get_center())
	await _frames(2)
	if Nav.feedback == null:
		_fail("E12: щелчок по «Я НЕ СОГЛАСЕН» при мини-игре не открыл замечание")
	await _close_all()
	await _mouse((js.get_node("Gear") as Control).get_global_rect().get_center())
	await _frames(2)
	if Nav.settings == null:
		_fail("E12: щелчок по ⚙ при мини-игре не открыл настройки")
	await _close_all()
	js.close_mini()
	await _frames(2)
	Nav.go("tech", {"job": "truing"})
	await _frames(2)
	var ts: Node = Nav.current
	for st: Dictionary in ts.job["steps"]:
		if st.get("spec") is Dictionary:
			ts.open_spec(st)
			break
	await _frames(2)
	await _mouse((ts.get_node("Flag") as Control).get_global_rect().get_center())
	await _frames(2)
	if Nav.feedback == null:
		_fail("E12: щелчок по ⚑ при спеке не открыл замечание")
	await _close_all()
	ts.close_spec()
	await _frames(2)


# ---- E18: колёсико мыши ----
func _e18_wheel() -> void:
	Nav.go("job", {"job": "flat", "variant": 0})
	await _frames(3)
	var j: Node = Nav.current
	Nav.flash("Улика", UI.WHITE, 4.0, true)
	await _frames(1)
	await _mouse(j.chair_rect().get_center(), MOUSE_BUTTON_WHEEL_UP)
	await _frames(1)
	if not Nav.toast.sticky:
		_fail("E18: колёсико над коляской погасило улику")
	Nav.toggle_help()
	await _frames(2)
	await _mouse(Vector2(640, 360), MOUSE_BUTTON_WHEEL_DOWN)
	await _frames(1)
	if Nav.help == null:
		_fail("E18: колёсико закрыло справку")
	await _close_all()
	Nav.open_flag()
	await _frames(2)
	(Nav.feedback.text as TextEdit).text = "текст"
	await _mouse(Vector2(20, 700), MOUSE_BUTTON_WHEEL_UP)
	await _frames(1)
	if Nav.feedback == null:
		_fail("E18: колёсико мимо окна закрыло замечание с набранным текстом")
	await _close_all()
	SaveGame.mark_job("flat", 3)
	Nav.go("garage")
	await _frames(2)
	var g: Node = Nav.current
	g.open_card(0)
	await _frames(1)
	await _mouse(Vector2(640, 360), MOUSE_BUTTON_WHEEL_DOWN)
	await _frames(1)
	if g.open_idx < 0:
		_fail("E18: колёсико закрыло карточку гаража")
	await _mouse(Vector2(640, 360), MOUSE_BUTTON_LEFT)   # щелчок левой — по-прежнему закрывает
	await _frames(1)
	if g.open_idx >= 0:
		_fail("E18: щелчок не закрыл карточку гаража")
		g.close_card()
	Nav.go("hub")
	await _frames(1)
	SaveGame.reset()
	SaveGame.tutorial_skipped = true
	await _frames(1)


# ---- E10, E11: клавиши в окнах ----
func _e10_e11_keys() -> void:
	Nav.go("hub")
	await _frames(2)
	for k: Key in [KEY_ENTER, KEY_SPACE, KEY_KP_ENTER]:
		await _key(KEY_F1)
		await _key(k)
		await _frames(1)
		if Nav.help != null:
			_fail("E10: клавиша %s не закрыла справку" % OS.get_keycode_string(k))
			Nav.toggle_help()
	await _key(KEY_F1)
	await _pad_button(JOY_BUTTON_A)
	if Nav.help != null:
		_fail("E10: A геймпада не закрыла справку")
		Nav.toggle_help()
	UI.kb_active = false
	await _key(KEY_F1)
	await _key(KEY_ENTER, 0, true)                     # Alt+Enter в справке — это Enter: закрыть (как game.py)
	if Nav.help != null:
		_fail("E10: Alt+Enter не закрыл справку")
		Nav.toggle_help()
	# F2 — везде
	for where: String in ["help", "settings", "feedback", "share"]:
		match where:
			"help":
				Nav.toggle_help()
			"settings":
				Nav.open_settings()
			"feedback":
				Nav.open_flag()
			"share":
				Share.open({"mode": "paste"})
		await _frames(2)
		var on0: bool = Settings.a11y.get("on", false)
		await _key(KEY_F2)
		if Settings.a11y.get("on", false) == on0:
			_fail("E11: F2 не переключил озвучку (%s)" % where)
		else:
			A11y.toggle_speech()
		await _close_all()
	# R/T — в настройках (как game.py), F11 — в настройках и справке
	Nav.open_settings()
	await _frames(2)
	var h0 := said.size()
	await _key(KEY_R)
	await _frames(1)
	if said.size() == h0 or not said[-1].contains(Speech.clean(Loc.t("Настройки."))):
		_fail("E11: R в настройках не сказал сводку")
	var fs0: int = Nav.get("fullscreen_toggles") if "fullscreen_toggles" in Nav else 0
	await _key(KEY_F11)
	if not "fullscreen_toggles" in Nav or Nav.get("fullscreen_toggles") != fs0 + 1:
		_fail("E11: F11 в настройках не переключил весь экран")
	await _close_all()
	Nav.toggle_help()
	await _frames(1)
	fs0 = Nav.get("fullscreen_toggles") if "fullscreen_toggles" in Nav else 0
	await _key(KEY_F11)
	if not "fullscreen_toggles" in Nav or Nav.get("fullscreen_toggles") != fs0 + 1 or Nav.help == null:
		_fail("E11: F11 в справке не переключил весь экран (или закрыл справку)")
	h0 = said.size()
	await _key(KEY_R)
	await _frames(1)
	if said.size() != h0 or Nav.help == null:
		_fail("E11: R в справке — не съеден (как game.py)")
	await _close_all()


# ---- E13: повтор в одном кадре, Alt+Enter в поле ----
func _e13_twice() -> void:
	Nav.go("job", {"job": "flat", "variant": 0})
	await _frames(2)
	var js: Node = Nav.current
	js.mistakes = 2
	js.note_dispute("mistake", "", "", "проверка")
	await _frames(2)
	var n0: int = Feedback.captured.size()
	js.open_dispute()
	await _frames(2)
	var fb: FeedbackDialog = Nav.feedback
	fb.send()
	fb.send()
	await _frames(2)
	if Feedback.captured.size() - n0 != 1 or js.mistakes != 1:
		_fail("E13: два «Отправить» в кадре — замечаний %d, ошибок %d (ждали 1 и 1)" % [Feedback.captured.size() - n0, js.mistakes])
	js.note_dispute("mistake", "", "", "проверка 2")
	js.dispute["t"] = js.t
	await _frames(2)
	js.open_dispute()
	await _frames(2)
	n0 = Feedback.captured.size()
	(Nav.feedback.text as Control).grab_focus()
	await _frames(1)
	await _key(KEY_ENTER, 0, true)
	await _frames(1)
	if Nav.feedback == null or Feedback.captured.size() != n0:
		_fail("E13: Alt+Enter в комментарии отправил замечание")
	await _close_all()
	# мануал: второй close() в кадре — окно закрыто один раз
	Nav.go("tech", {"job": "truing"})
	await _frames(2)
	var ts: Node = Nav.current
	ts.open_manual()
	await _frames(2)
	var md: Node = ts.manual_dlg
	var closes := [0]
	md.closed.connect(func() -> void: closes[0] += 1)
	md.close()
	md.close()
	await _frames(2)
	if closes[0] != 1 or ts.manual_dlg != null:
		_fail("E13: два close() мануала в кадре — сигналов %d" % closes[0])


# ---- E20: дрожь стика ----
func _e20_stick() -> void:
	Nav.go("hub")
	await _frames(2)
	var mm := InputEventMouseMotion.new()
	mm.position = Vector2(300, 300)
	mm.relative = Vector2(1, 0)
	get_viewport().push_input(mm, true)
	await _frames(1)
	for ax: JoyAxis in [JOY_AXIS_LEFT_X, JOY_AXIS_RIGHT_X]:
		var jm := InputEventJoypadMotion.new()
		jm.axis = ax
		jm.axis_value = 0.02
		get_viewport().push_input(jm)
		await _frames(2)
		if UI.kb_active:
			_fail("E20: дрожь стика (ось %d, 0,02) включила режим клавиатуры" % ax)
			UI.kb_active = false
	var jm2 := InputEventJoypadMotion.new()
	jm2.axis = JOY_AXIS_LEFT_Y
	jm2.axis_value = 0.9
	get_viewport().push_input(jm2)
	await _frames(3)
	if not UI.kb_active:
		_fail("E20: стик вниз до упора не включил режим клавиатуры")
	jm2 = InputEventJoypadMotion.new()
	jm2.axis = JOY_AXIS_LEFT_Y
	jm2.axis_value = 0.0
	get_viewport().push_input(jm2)
	await _frames(2)
	UI.kb_active = false


# ---- E15: озвучка ----
func _e15_speech() -> void:
	if not Loc.changed.is_connected(Speech.set_voice):
		_fail("E15: смена RU/EN не меняет голос озвучки (Speech.set_voice)")
	var on0: bool = Settings.a11y.get("on", false)
	var set0: bool = Settings.a11y.get("speech_set", false)
	var kind0: String = Speech.kind
	Settings.a11y["on"] = false
	Settings.a11y["speech_set"] = false
	Speech.kind = "reader"
	if Speech.has_method("reader_auto_on"):
		Speech.call("reader_auto_on")
	if not Settings.a11y.get("on", false):
		_fail("E15: при работающем чтеце экрана озвучка не включилась сама")
	Settings.a11y["on"] = false
	Settings.a11y["speech_set"] = true
	if Speech.has_method("reader_auto_on"):
		Speech.call("reader_auto_on")
	if Settings.a11y.get("on", false):
		_fail("E15: чтец включил озвучку, которую игрок выключил сам")
	Speech.kind = kind0
	Settings.a11y["on"] = on0
	Settings.a11y["speech_set"] = set0
	Speech._live_say("Где я")
	var t1: String = Speech._live.text
	Speech._live_say("Где я")
	if Speech._live.text == t1:
		_fail("E15: та же фраза второй раз — текст живой области не изменился (чтец её не повторит)")
	await _frames(1)


# ---- E26, E27: шестерёнка, окно настроек ----
func _e26_e27_settings() -> void:
	Nav.go("hub")
	await _frames(2)
	var g := Nav.current.get_node("Gear") as Control
	var n0 := str(g.accessibility_name)
	await _key(KEY_M)
	await _frames(1)
	if str(g.accessibility_name) == n0:
		_fail("E26: после M имя шестерёнки для чтеца прежнее: «%s»" % n0)
	await _key(KEY_M)
	await _frames(1)
	Nav.open_settings()
	await _frames(2)
	Nav.settings.get_node("Tab_sound").pressed.emit()
	await _frames(2)
	var s: SettingsDialog = Nav.settings
	var vm := s.get_node("Vol_master") as Control
	A11y.kb_focus(vm)
	UI.kb_active = true
	await _frames(2)
	var v0: float = Settings.vol["master"]
	var h0 := said.size()
	Audio.played.clear()
	await _key(KEY_RIGHT if v0 < 1.0 else KEY_LEFT)
	await _frames(2)
	var pct := "%d%%" % int(float(Settings.vol["master"]) * 100)
	if not "tick" in Audio.played:
		_fail("E27: ← → на ползунке громкости без щелчка")
	if said.slice(h0).filter(func(x: String) -> bool: return x.contains(pct)).is_empty():
		_fail("E27: ← → на ползунке — новое значение %s не сказано: %s" % [pct, said.slice(h0)])
	Settings.set_vol("master", v0)
	await _frames(1)
	# «Без звука»: зона подсказки — только кнопка (наведение на «ГОТОВО» не показывает её подсказку)
	s = Nav.settings
	var done_c := (s.get_node("Done") as Control).get_global_rect().get_center()
	for z: Array in s._zones:
		if z[0] == "mute" and (z[1] as Rect2).has_point(done_c):
			_fail("E27: зона подсказки «Без звука» накрывает «ГОТОВО»")
	s.get_node("Tab_game").pressed.emit()
	await _frames(2)
	s = Nav.settings
	var keys: Array = s._zones.map(func(z: Array) -> String: return z[0])
	if not "share_code" in keys or not "share_paste" in keys:
		_fail("E27: у кнопок кодов нет подсказки: %s" % [keys])
	# подсказка пункта вслух, когда фокус клавиатуры задержался (при включённой озвучке)
	var on0: bool = Settings.a11y.get("on", false)
	Settings.a11y["on"] = true
	A11y.kb_focus(s.get_node("Share_code") as Control)
	UI.kb_active = true
	h0 = said.size()
	var t0 := Time.get_ticks_msec()
	while Time.get_ticks_msec() - t0 < 1600:
		await _frames(1)
	var want := Speech.clean(Loc.t(Content.consts.get("setting_help", {}).get("share_code", "")))
	if said.slice(h0).filter(func(x: String) -> bool: return x.contains(want.substr(0, 30))).is_empty():
		_fail("E27: подсказка «Скопировать код» не прочитана вслух (фокус 1,5 с)")
	Settings.a11y["on"] = on0
	# Esc при вопросе о сбросе — снимает вопрос, окно остаётся
	(s.get_node("Reset") as BaseButton).pressed.emit()
	await _frames(2)
	await _key(KEY_ESCAPE)
	await _frames(2)
	if Nav.settings == null or Nav.settings.reset_ask:
		_fail("E27: Esc при вопросе о сбросе закрыл настройки (ждали: вопрос снят, окно открыто)")
	# щелчок мимо окна — закрыть (как game.py)
	if Nav.settings != null:
		UI.kb_active = false
		await _mouse(Vector2(6, 700))
		await _frames(2)
		if Nav.settings != null:
			_fail("E27: щелчок мимо окна настроек не закрыл его")
	await _close_all()
	UI.kb_active = false


# ---- E29: коляска с фокусом, сообщение сверху ----
func _e29_misc() -> void:
	Nav.go("job", {"job": "flat", "variant": 0})
	await _frames(3)
	var j: Node = Nav.current
	j.chair.t0 = -1e9
	j.chair.grab_focus()
	await _frames(1)
	var y0: float = j.chair.yaw
	await _key(KEY_RIGHT)
	await _frames(1)
	if is_equal_approx(j.chair.yaw, y0) or _fo() != j.chair:
		_fail("E29: → при фокусе на коляске не повернул её (фокус ушёл на %s)" % _fo_name())
	var y1: float = j.chair.yaw
	var h0 := said.size()
	await _key(KEY_R)
	await _frames(1)
	if not is_equal_approx(j.chair.yaw, y1) or said.size() == h0:
		_fail("E29: R при фокусе на коляске сбросил вид вместо сводки")
	if Nav.current_name == "job":
		j.chair.release_focus()
	var cr: Node = (load("res://screens/credits.gd") as GDScript).new()
	if cr.toast_bounds().y < 164:
		_fail("E29: сообщение на титрах ложится на ⚑ (запас справа меньше 164)")
	cr.free()
	Nav.go("hub")
	await _frames(2)
	Nav.flash("Звук включён", UI.GHOST, 30.0)
	var t0 := Time.get_ticks_msec()
	while Time.get_ticks_msec() - t0 < 500 or Nav.toast.t - Nav.toast.t0 < 0.4:   # въезд закончился — подпись стоит
		await _frames(1)
	var sig0: Variant = Nav.toast.get_meta("redraw_sig", [])
	Loc.toggle()
	await _frames(2)
	if Nav.toast.get_meta("redraw_sig", []) == sig0:
		_fail("E29: сообщение сверху не перерисовано на новом языке")
	Loc.toggle()
	await _frames(2)
