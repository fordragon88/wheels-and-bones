class_name Chrome
## Значки в углах экрана с их действиями (как в Game.draw): «◂ назад» = Esc, флажок замечаний (кроме титула),
## язык (титул, мастерская, Гильдия, гараж), шестерёнка настроек (везде).


static func add(parent: Control, back: bool, flag: bool, lang: bool) -> void:
	if back:
		var b := IconButton.make_icon(IconButton.Kind.BACK)
		b.pressed.connect(func() -> void:
			Audio.sfx("tick")
			Nav.back())
		parent.add_child(b)
	if flag:
		var f := IconButton.make_icon(IconButton.Kind.FLAG)
		f.pressed.connect(func() -> void:
			Audio.sfx("tick")
			Nav.open_flag())
		parent.add_child(f)
	if lang:
		var l := IconButton.make_icon(IconButton.Kind.LANG)
		l.pressed.connect(func() -> void:
			Audio.sfx("tick")
			Loc.toggle())
		parent.add_child(l)
	var sr := IconButton.sound_place(lang, flag)   # кнопка звука (выключатель, как M; 28.11)
	if lang:                                   # левее флажка: название шапки всегда левее неё
		var bar := parent.get_node_or_null("TopBar") as TopBar
		if bar:
			bar.right_edge = minf(bar.right_edge, sr.position.x - 10)
	var so := IconButton.make_icon(IconButton.Kind.SOUND)
	so.position = sr.position
	so.size = sr.size
	so.pressed.connect(IconButton.toggle_sound)
	parent.add_child(so)
	var g := IconButton.make_icon(IconButton.Kind.GEAR)
	g.pressed.connect(func() -> void:
		Audio.sfx("tick")
		Nav.open_settings())
	parent.add_child(g)
