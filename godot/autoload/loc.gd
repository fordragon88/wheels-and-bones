extends Node
## Язык: Loc.t("русская строка") → строка на текущем языке. Порт tr() из game.py: код и данные остаются на русском,
## перевод — на выводе. Словарь content/data/lang_en.json (русская → английская; строки с {0},{1}… — шаблоны) +
## i18n/lang_en_port.json (строки, которые есть только в переносе). Порядок поиска как в game.py:
## точное совпадение → шаблон целиком → шаблон внутри склейки → известные куски склейки.

signal changed

const DICT := "res://content/data/lang_en.json"
const DICT_PORT := "res://i18n/lang_en_port.json"

var code: String = "ru"
var audit: bool = false                # самопроверка: запоминать строки, у которых нет английского
var misses: Dictionary = {}            # русская строка → что вышло по-английски (с кириллицей)
var audited: Dictionary = {}           # все проверенные строки

var _tr: Dictionary = {}
var _fmt: Array = []                   # [RegEx целиком, порядок {n}, en, RegEx внутри склейки | null]
var _parts: Array = []                 # [ru, en] по убыванию длины
var _short_rx: Dictionary = {}         # короткие куски («мм», «В») — только целым словом
var _cache: Dictionary = {}
var _cyr := RegEx.create_from_string("[А-Яа-яЁё]")
var _ph := RegEx.create_from_string("\\{\\d+\\}")
var _loaded: bool = false


func _ready() -> void:
	code = Settings.lang
	Settings.changed.connect(_on_settings)
	_load()


func _on_settings(key: String) -> void:
	if key == "lang" and Settings.lang != code:
		code = Settings.lang
		DisplayServer.window_set_title(window_title())
		changed.emit()


func window_title() -> String:
	return t("Колёса и Кости") if code == "en" else "Колёса и Кости // Wheels & Bones"


func set_lang(c: String) -> void:
	Settings.set_lang(c)                   # → _on_settings → changed


func toggle() -> void:
	set_lang("ru" if code == "en" else "en")


func has_cyrillic(s: String) -> bool:
	return _cyr.search(s) != null


func _load() -> void:
	_tr.clear(); _fmt.clear(); _parts.clear(); _cache.clear()
	var merged: Dictionary = {}            # словарь игры; строки переноса — только те, которых в нём нет
	for path: String in [DICT, DICT_PORT]:
		if not FileAccess.file_exists(path):
			push_error("нет словаря " + path)
			continue
		var d: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
		if d is Dictionary:
			for ru: String in d:
				if not merged.has(ru):
					merged[ru] = str(d[ru])
	var order := 0
	for ru: String in merged:
		var en: String = merged[ru]
		if _ph.search(ru) != null:
			var pat := ""
			var nums: Array[int] = []
			var pos := 0
			for m: RegExMatch in _ph.search_all(ru):
				pat += _escape(ru.substr(pos, m.get_start() - pos).replace("{{", "{").replace("}}", "}"))
				pat += "(.*?)"
				nums.append(int(m.get_string().substr(1, m.get_string().length() - 2)))
				pos = m.get_end()
			pat += _escape(ru.substr(pos).replace("{{", "{").replace("}}", "}"))
			var lit := _ph.sub(ru, "", true)
			var inner: RegEx = RegEx.create_from_string("(?s)" + pat) if lit.length() >= 6 else null
			_fmt.append([RegEx.create_from_string("(?s)^" + pat + "$"), nums, en, inner, lit.length(), order, ru])
			order += 1
		else:
			_tr[ru] = en
			if ru.length() >= 2:
				_parts.append([ru, en])
	_parts.sort_custom(func(a: Array, b: Array) -> bool: return a[0].length() > b[0].length())
	# точный шаблон раньше общего («{0} см»): по длине постоянной части, при равенстве — порядок словаря
	_fmt.sort_custom(func(a: Array, b: Array) -> bool:
		return a[4] > b[4] or (a[4] == b[4] and a[5] < b[5]))
	_loaded = true


static func _escape(s: String) -> String:
	var out := ""
	for ch in s:
		if "\\^$.|?*+()[]{}".contains(ch):
			out += "\\"
		out += ch
	return out


## Перевод строки для вывода на экран (в режиме ru — без изменений).
func t(s: String) -> String:
	if audit and s != "" and has_cyrillic(s):
		audited[s] = true
		var en := _translate(s)
		if has_cyrillic(en):
			misses[s] = en
	if code == "ru" or s == "" or not has_cyrillic(s):
		return s
	return _translate(s)


## Строка по-английски при любом языке интерфейса (tr_en: таблица замечаний — на английском).
func to_en(s: String) -> String:
	return _translate(s)


## Шаблон с подстановкой: Loc.tf("Починено: {0}/{1}", [3, 21]) — как f-строка + tr() в game.py.
func tf(template: String, args: Array) -> String:
	return t(fmt(template, args))


static func fmt(template: String, args: Array) -> String:
	var s := template
	for i in args.size():
		s = s.replace("{%d}" % i, str(args[i]))
	return s


func _translate(s: String) -> String:
	if s == "" or not has_cyrillic(s):
		return s
	if _cache.has(s):
		return _cache[s]
	var out: Variant = _tr.get(s)
	if out == null:
		for f: Array in _fmt:
			var m: RegExMatch = (f[0] as RegEx).search(s)
			if m != null:
				out = _fill(m, f[1], f[2])
				if out != null:
					break
	if out == null:                        # шаблон внутри склейки: «✔ » + f"…"
		for f: Array in _fmt:
			if f[3] == null:
				continue
			var m: RegExMatch = (f[3] as RegEx).search(s)
			if m != null and m.get_end() > m.get_start():
				var filled: Variant = _fill(m, f[1], f[2])
				if filled != null:
					out = _translate(s.substr(0, m.get_start()) + str(filled) + s.substr(m.get_end()))
					break
	if out == null:                        # склеенные строки: переводим известные куски
		var res := s
		for p: Array in _parts:
			var ru: String = p[0]
			if res.contains(ru):
				if ru.length() < 4:
					var rx: RegEx = _short_rx.get(ru)
					if rx == null:
						rx = RegEx.create_from_string("(?<![А-Яа-яЁё])" + _escape(ru) + "(?![А-Яа-яЁё])")
						_short_rx[ru] = rx
					res = rx.sub(res, str(p[1]).replace("$", "$$"), true)
				else:
					res = res.replace(ru, p[1])
				if not has_cyrillic(res):
					break
		out = res
	_cache[s] = out
	return out


func _fill(m: RegExMatch, nums: Array[int], en: String) -> Variant:
	var vals := {}
	for i in nums.size():
		vals[nums[i]] = _translate(m.get_string(i + 1))
	var top := 0
	for n in nums:
		top = maxi(top, n)
	var res := en
	for i in range(top + 1):
		res = res.replace("{%d}" % i, str(vals.get(i, "")))
	return res.replace("{{", "{").replace("}}", "}")
