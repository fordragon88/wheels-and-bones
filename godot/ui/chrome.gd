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
			Nav.flash("Окно замечаний появится в следующих шагах переноса.", UI.PURPLE, 3.0))
		parent.add_child(f)
	if lang:
		var l := IconButton.make_icon(IconButton.Kind.LANG)
		l.pressed.connect(func() -> void:
			Audio.sfx("tick")
			Loc.toggle())
		parent.add_child(l)
	var g := IconButton.make_icon(IconButton.Kind.GEAR)
	g.set_meta("lang_left", lang)
	g.pressed.connect(func() -> void:
		Audio.sfx("tick")
		Nav.open_settings())
	parent.add_child(g)
