extends Node
## Ссылки и коды (docs/SHARE_LINKS.md, блок «Ссылки и коды» game.py) — формат один в один с pygame-версией:
##   код «<вид>.<тело>.<crc>»: вид P (прогресс), J (задание), R (результат); тело — base64url без «=» от
##   zlib(JSON с ключами по алфавиту, без пробелов); crc — 6 hex = crc32(соль + вид + "." + тело + соль) & 0xFFFFFF,
##   соль только у R. Чтение: пробелы и кавычки вокруг игнорируются, длина ≤ SHARE_MAX, распаковка ≤ 200 000 байт,
##   "v" == 1. Сжатые байты у Godot другие, но код читается в обе стороны: сумма считается от того тела, какое есть.
## Здесь же: прогресс в код и обратно, задание по ссылке (assign_parse/id/code/params), ссылка и её разбор, итог
## задания (result_pack/unpack/text), буфер обмена (в тестах — в памяти: системный буфер не трогаем), ссылка запуска
## (браузер — адрес страницы, компьютер — «-- --link=?jobs=…»).

const KINDS := ["P", "J", "R"]
const QUOTES := "\"'<>«»"
const ZW := ["​", "‌", "‍", "⁠", "﻿"]

var clip_mem: String = ""                 # тесты: «буфер обмена» в памяти
var test_mode: bool = false
var _crc_table: PackedInt64Array = []


func _ready() -> void:
	test_mode = OS.get_cmdline_user_args().has("--test")


func cfg(key: String, fallback: Variant) -> Variant:
	return Content.consts.get("share", {}).get(key, fallback)


func base_url() -> String:
	return str(cfg("base_url", "https://www.openassistivetech.org/wheels-and-bones/"))


func max_len() -> int:
	return int(cfg("max", 8000))


func params_allowed() -> Array:
	return cfg("params", ["load", "jobs", "seat", "from", "title"])


# ---------------- crc32, base64url ----------------

func crc32(data: PackedByteArray) -> int:
	if _crc_table.is_empty():
		_crc_table.resize(256)
		for n in 256:
			var c := n
			for k in 8:
				c = (0xEDB88320 ^ (c >> 1)) if (c & 1) else (c >> 1)
			_crc_table[n] = c
	var crc := 0xFFFFFFFF
	for b in data:
		crc = _crc_table[(crc ^ b) & 0xFF] ^ (crc >> 8)
	return crc ^ 0xFFFFFFFF


func share_crc(kind: String, body: String) -> String:
	var salt := str(cfg("result_salt", "wnb-result-2026")) if kind == "R" else ""
	return "%06x" % (crc32((salt + kind + "." + body + salt).to_utf8_buffer()) & 0xFFFFFF)


static func b64u(raw: PackedByteArray) -> String:
	return Marshalls.raw_to_base64(raw).replace("+", "-").replace("/", "_").rstrip("=")


# ---------------- коды ----------------

## dict → код «P.тело.crc» (share_encode). JSON — ключи по алфавиту, без пробелов (как json.dumps sort_keys).
func encode(kind: String, data: Dictionary) -> String:
	var raw := JSON.stringify(_ints(data), "", true).to_utf8_buffer()
	var body := b64u(raw.compress(FileAccess.COMPRESSION_DEFLATE))
	return "%s.%s.%s" % [kind, body, share_crc(kind, body)]


## Целые числа остаются целыми (после JSON Godot числа дробные: 3 → 3.0).
static func _ints(v: Variant) -> Variant:
	if v is float and is_finite(v) and v == floorf(v) and absf(v) < 1e15:
		return int(v)
	if v is Array:
		return (v as Array).map(func(x: Variant) -> Variant: return _ints(x))
	if v is Dictionary:
		var o := {}
		for k: Variant in v:
			o[k] = _ints(v[k])
		return o
	return v


## Код → [вид, dict] или [] (share_decode): битый код, чужая сумма, неизвестный вид или версия.
func decode(code: Variant) -> Array:
	var s := _strip_ws(str(code) if code != null else "")
	while s != "" and QUOTES.contains(s[0]):
		s = s.substr(1)
	while s != "" and QUOTES.contains(s[s.length() - 1]):
		s = s.substr(0, s.length() - 1)
	if s == "" or s.length() > max_len():
		return []
	var parts := s.split(".")
	if parts.size() != 3:
		return []
	var kind := parts[0]
	var body := parts[1]
	if not kind in KINDS or body == "" or not _b64_ok(body) or parts[2].to_lower() != share_crc(kind, body):
		return []
	if body.length() % 4 == 1:
		return []
	var std := body.replace("-", "+").replace("_", "/")
	std += "=".repeat((4 - std.length() % 4) % 4)
	var packed := Marshalls.base64_to_raw(std)
	if packed.is_empty():
		return []
	var raw := packed.decompress_dynamic(200000, FileAccess.COMPRESSION_DEFLATE)
	if raw.is_empty() or raw.size() >= 200000:
		return []
	var txt := raw.get_string_from_utf8()
	var json := JSON.new()
	if json.parse(txt) != OK or not json.data is Dictionary:
		return []
	var data: Dictionary = json.data
	var v: Variant = data.get("v")
	if not ((v is float or v is int or v is bool) and float(v) == 1.0):
		return []
	return [kind, data]


static func _strip_ws(s: String) -> String:
	var out := ""
	for ch in s:
		if not ch in [" ", "\t", "\n", "\r", "\u000b", "\u000c"]:
			out += ch
	return out


static func _b64_ok(s: String) -> bool:
	for ch in s:
		var c := ch.unicode_at(0)
		if not ((c >= 48 and c <= 57) or (c >= 65 and c <= 90) or (c >= 97 and c <= 122) or ch == "-" or ch == "_"):
			return false
	return true


# ---------------- строки из ссылки ----------------

## Печатный ли знак (str.isprintable в Python): без управляющих, форматных и «невидимых» пробелов (кроме обычного).
static func _printable(ch: String) -> bool:
	var c := ch.unicode_at(0)
	if c < 32 or (c >= 127 and c <= 160) or c == 0xAD:
		return false
	if c == 0x1680 or c == 0x180E or (c >= 0x2000 and c <= 0x200F) or (c >= 0x2028 and c <= 0x202F):
		return false
	if (c >= 0x205F and c <= 0x206F) or c == 0x3000 or c == 0xFEFF or (c >= 0xFFF9 and c <= 0xFFFB):
		return false
	if (c >= 0xD800 and c <= 0xF8FF) or c >= 0xF0000:
		return false
	return true


## Имя/заголовок из ссылки: одна строка печатных символов, не длиннее n (_clean_line).
static func clean_line(v: Variant, n: int) -> String:
	var s := pystr(v) if v != null else ""
	var o := ""
	for ch in s:
		if _printable(ch) and not ch in ZW:
			o += ch
	var re := RegEx.create_from_string("\\s+")
	return re.sub(o, " ", true).strip_edges().substr(0, n).strip_edges(false, true)   # обрезка на пробеле — без хвоста


## str() как в Python для чисел (5.0 → «5»), bool → True/False.
static func pystr(v: Variant) -> String:
	if v is bool:
		return "True" if v else "False"
	if v is float and v == floorf(v) and absf(v) < 1e15:
		return str(int(v))
	return str(v)


func job_ids() -> Array:
	return Content.jobs.map(func(j: Dictionary) -> String: return j["id"])


func seat_ids() -> Array:
	return SeatLogic.cases().map(func(c: Dictionary) -> String: return c["id"])


# ---------------- прогресс ----------------

## Прогресс → данные кода «P» (progress_pack): только то, что в save.json.
func progress_pack() -> Dictionary:
	var d: Array = SaveGame.done.keys()
	d.sort()
	var s: Array = SaveGame.seat_done.keys()
	s.sort()
	var g: Array = []
	for e: Array in SaveGame.garage:
		g.append([e[0], int(e[1])])
	return {"v": 1, "d": d, "g": g, "e": SaveGame.exam_passed, "s": s, "q": SaveGame.seat_quiz_ok,
		"t": SaveGame.tutorial_skipped}


## Данные кода «P» → проверенные поля (progress_unpack) или {}: неизвестное и битое — мимо.
func progress_unpack(d: Variant) -> Dictionary:
	if not d is Dictionary:
		return {}
	var valid := {}
	for j: Dictionary in Content.all_jobs():
		valid[j["id"]] = true
	for jid: String in Content.folk_ids:
		valid[jid] = true
	var lst := func(k: String) -> Array: return d.get(k) if d.get(k) is Array else []
	var garage: Array = []
	var seen := {}
	for e: Variant in lst.call("g"):
		if e is Array and e.size() == 2 and e[0] is String and valid.has(e[0]) and not seen.has(e[0]):
			var st: Variant = e[1]
			if st is float or st is int or st is bool:
				garage.append([e[0], clampi(int(st), 1, 3)])
				seen[e[0]] = true
			elif st is String and st.strip_edges().is_valid_int():
				garage.append([e[0], clampi(st.strip_edges().to_int(), 1, 3)])
				seen[e[0]] = true
	var done := {}
	for j: Variant in lst.call("d"):
		if j is String and valid.has(j):
			done[j] = true
	var seats := {}
	var sid := seat_ids()
	for c: Variant in lst.call("s"):
		if c is String and c in sid:
			seats[c] = true
	var dk: Array = done.keys()
	dk.sort()
	var sk: Array = seats.keys()
	sk.sort()
	return {"done": dk, "garage": garage, "exam_passed": d.get("e") is bool and d["e"] == true,
		"seat_done": sk, "seat_quiz_ok": d.get("q") is bool and d["q"] == true,
		"tutorial_skipped": d.get("t") is bool and d["t"] == true}


# ---------------- задание ----------------

## Имя и заголовок задания — текст игрока (самопроверка перевода не считает его кириллицу пропуском).
func _user(s: String) -> void:
	if s != "" and Loc.audit:
		Loc.user_text[s] = true


## Номер задания — crc32 от [jobs, seat, from, title] (assign_id), 8 hex.
func assign_id(jobs: Array, seat: Array, frm: String, title: String) -> String:
	var key := JSON.stringify([jobs, seat, frm, title])
	return "%08x" % crc32(key.to_utf8_buffer())


## Параметры ссылки-задания → задание или {} (нет ни одного известного id); повторы и неизвестные — мимо.
func assign_parse(params: Variant) -> Dictionary:
	if not params is Dictionary:
		return {}
	var ids := func(key: String, valid: Array) -> Array:
		var v: Variant = params.get(key)
		var s := ""
		if v is Array:
			s = ",".join((v as Array).map(func(x: Variant) -> String: return pystr(x)))
		elif v != null and not (v is String and v == "") and not (v is bool and not v):
			s = pystr(v)
		var out: Array = []
		for x: String in RegEx.create_from_string("[,;\\s]+").sub(s, "\u0001", true).split("\u0001"):
			if x in valid and not x in out:
				out.append(x)
		return out
	var jobs: Array = ids.call("jobs", job_ids())
	var seat: Array = ids.call("seat", seat_ids())
	if jobs.is_empty() and seat.is_empty():
		return {}
	var frm := clean_line(params.get("from"), 40) if params.get("from") else ""
	var title := clean_line(params.get("title"), 80) if params.get("title") else ""
	_user(frm)
	_user(title)
	return {"id": assign_id(jobs, seat, frm, title), "jobs": jobs, "seat": seat, "from": frm, "title": title}


func assign_code(a: Dictionary) -> String:
	return encode("J", {"v": 1, "j": a["jobs"], "s": a["seat"], "f": a.get("from", ""), "ti": a.get("title", "")})


## Задание → параметры адреса (jobs, seat, from, title; пустые — без них). Порядок ключей важен для ссылки.
func assign_params(a: Dictionary) -> Array:
	var out: Array = []
	for p: Array in [["jobs", ",".join(a["jobs"])], ["seat", ",".join(a["seat"])], ["from", a.get("from", "")],
			["title", a.get("title", "")]]:
		if str(p[1]) != "":
			out.append(p)
	return out


func assign_items(a: Dictionary) -> Array:
	return (a.get("jobs", []) as Array) + (a.get("seat", []) as Array)


## urllib.parse.quote(s, safe=","): всё, кроме A-Z a-z 0-9 _ . - ~ и запятой, — %XX по байтам UTF-8.
static func quote(s: String) -> String:
	var out := ""
	for b in s.to_utf8_buffer():
		if (b >= 48 and b <= 57) or (b >= 65 and b <= 90) or (b >= 97 and b <= 122) or b in [95, 46, 45, 126, 44]:
			out += char(b)
		else:
			out += "%%%02X" % b
	return out


## Ссылка на игру с параметрами [[ключ, значение]…] (share_link).
func share_link(params: Array, base: String = "") -> String:
	var q: Array = []
	for p: Array in params:
		if str(p[1]) != "":
			q.append("%s=%s" % [p[0], quote(str(p[1]))])
	return (base if base != "" else base_url()) + ("?" + "&".join(q) if not q.is_empty() else "")


## Адрес целиком, «?a=b&…» или «a=b&…» → {параметр: значение} только для SHARE_PARAMS (parse_link, parse_qs).
func parse_link(text: Variant) -> Dictionary:
	var s := (str(text) if text != null else "").strip_edges()
	var q := s.find("?")
	if q >= 0:
		s = s.substr(q + 1)
	var h := s.find("#")
	if h >= 0:
		s = s.substr(0, h)
	if not s.contains("="):
		return {}
	var out := {}
	for pair: String in s.split("&"):
		var eq := pair.find("=")
		if eq < 0:
			continue
		var k := _unquote_plus(pair.substr(0, eq))
		var v := _unquote_plus(pair.substr(eq + 1))
		if v == "":
			continue
		if k in params_allowed():
			out[k] = v
	return out


## unquote_plus: «+» → пробел, %XX → байты UTF-8 (битые последовательности — знак замены, как errors="replace").
static func _unquote_plus(s: String) -> String:
	var bytes := PackedByteArray()
	var src := s.replace("+", " ").to_utf8_buffer()
	var i := 0
	while i < src.size():
		var b := src[i]
		if b == 37 and i + 2 < src.size() and _hex(src[i + 1]) >= 0 and _hex(src[i + 2]) >= 0:
			bytes.append(_hex(src[i + 1]) * 16 + _hex(src[i + 2]))
			i += 3
		else:
			bytes.append(b)
			i += 1
	return bytes.get_string_from_utf8()


static func _hex(c: int) -> int:
	if c >= 48 and c <= 57:
		return c - 48
	if c >= 65 and c <= 70:
		return c - 55
	if c >= 97 and c <= 102:
		return c - 87
	return -1


# ---------------- итог задания ----------------

## Состояние задания → данные кода результата (result_pack).
func result_pack(a: Dictionary) -> Dictionary:
	var rows: Array = []
	for k: String in assign_items(a):
		if (a["done"] as Dictionary).has(k):
			rows.append([k, int(a["errors"].get(k, 0)), int(a["secs"].get(k, 0))])
	return {"v": 1, "a": a["id"], "f": a.get("from", ""), "ti": a.get("title", ""), "it": assign_items(a), "r": rows,
		"gv": str(Content.consts.get("version", ""))}


func result_code(a: Dictionary) -> String:
	return encode("R", result_pack(a))


## Данные кода результата → {id, from, title, version, rows: [[пункт, сделано, ошибок, секунд]]} или {}.
func result_unpack(d: Variant) -> Dictionary:
	if not d is Dictionary or not d.get("it") is Array or not d.get("r") is Array:
		return {}
	var items: Array = (d["it"] as Array).map(func(x: Variant) -> String: return pystr(x)).slice(0, 60)
	var got := {}
	for r: Variant in d["r"]:
		if not r is Array or r.size() != 3:
			return {}
		var e: Variant = _pyint(r[1])
		var s: Variant = _pyint(r[2])
		if e == null or s == null:
			return {}
		got[pystr(r[0])] = [e, s]
	var rows: Array = []
	for k: String in items:
		var g: Array = got.get(k, [0, 0])
		rows.append([k, got.has(k), g[0], g[1]])
	var frm := clean_line(d.get("f"), 40) if d.get("f") else ""
	var title := clean_line(d.get("ti"), 80) if d.get("ti") else ""
	_user(frm)
	_user(title)
	return {"id": pystr(d.get("a", "")), "from": frm, "title": title, "version": pystr(d.get("gv", "")), "rows": rows}


## int() как в Python: число (дробное — к нулю), bool, строка с целым; иначе null.
static func _pyint(v: Variant) -> Variant:
	if v is bool:
		return 1 if v else 0
	if v is int:
		return v
	if v is float and is_finite(v):
		return int(v)
	if v is String and v.strip_edges().is_valid_int():
		return v.strip_edges().to_int()
	return null


## «Клиент — поломка» или «Посадка: клиент» (share_item_label).
func item_label(k: String) -> String:
	var j := Content.job_by_id(k)
	if not j.is_empty() and Content.jobs.has(j):
		return Loc.t(j["client"]) + " — " + Loc.t(j["title"])
	for c: Dictionary in SeatLogic.cases():
		if c["id"] == k:
			return Loc.t("Посадка") + ": " + Loc.t(c["client"])
	return k


static func fmt_secs(s: Variant) -> String:
	var n := maxi(0, int(s))
	@warning_ignore("integer_division")
	return "%d:%02d" % [n / 60, n % 60]


## «3/3, ошибок 2» (result_summary).
func result_summary(rows: Array) -> String:
	var n := 0
	var e := 0
	for r: Array in rows:
		if r[1]:
			n += 1
			e += int(r[2])
	return Loc.t("%d/%d, ошибок %d" % [n, rows.size(), e])


## «Задание от Имя: «Тема»» (assign_head).
func assign_head(frm: String, title: String) -> String:
	if frm != "" and title != "":
		return Loc.t("Задание от %s: «%s»" % [frm, title])
	if frm != "":
		return Loc.t("Задание от %s" % frm)
	return Loc.t("Задание: «%s»" % title) if title != "" else Loc.t("Задание")


## Итог читаемым текстом (result_text).
func result_text(res: Dictionary, code: String = "") -> String:
	var lines: Array = [Loc.t("Колёса и Кости — итог задания") + ". " + assign_head(res.get("from", ""), res.get("title", "")),
		result_summary(res["rows"])]
	for r: Array in res["rows"]:
		lines.append(("✔ " if r[1] else "— ") + item_label(r[0]) + ((" · " + Loc.t("ошибок %d" % int(r[2])) + " · " +
			fmt_secs(r[3])) if r[1] else " · " + Loc.t("не сделано")))
	if code != "":
		lines.append(Loc.t("Код результата") + ": " + code)
	return "\n".join(lines)


## То же на другом языке (таблица — на английском).
func in_lang(code: String, f: Callable) -> Variant:
	var old := Loc.code
	Loc.code = code
	var v: Variant = f.call()
	Loc.code = old
	return v


# ---------------- буфер обмена, ссылка запуска ----------------

## Текст в буфер обмена: в тестах — в память (системный буфер владельца не трогаем). true — получилось.
func clip_put(text: String) -> bool:
	if test_mode:
		clip_mem = text
		return true
	DisplayServer.clipboard_set(text)
	if OS.has_feature("web"):
		return true                        # браузер: ответ приходит позже, Godot копирует через navigator.clipboard
	return DisplayServer.clipboard_get() == text


func clip_get() -> String:
	if test_mode:
		return clip_mem
	return DisplayServer.clipboard_get()


## Ссылка запуска: в браузере — параметры адреса страницы (?jobs=…), на компьютере — «-- --link=?jobs=…»
## или «-- --link ?jobs=…» (web_link_query).
func launch_query(args: PackedStringArray = OS.get_cmdline_user_args()) -> String:
	if OS.has_feature("web"):
		var v: Variant = JavaScriptBridge.eval("window.location.search || ''", true)
		return str(v) if v != null else ""
	for i in args.size():
		if args[i].begins_with("--link="):
			return args[i].trim_prefix("--link=")
		if args[i] == "--link" and i + 1 < args.size():
			return args[i + 1]
	return ""



# ================= действия (окно кодов, задание по ссылке) =================

var dlg: ShareDialog                       # открытое окно кодов и ссылок (одно)
var link_launch: bool = false              # игру запустили со ссылкой-заданием или кодом
var resume_asked: bool = false             # вопрос «продолжить задание / обычная игра» уже был в этом запуске
var summary_seen: String = ""              # итог задания уже показан сам (id задания)


## Отправка итога в таблицу есть, если в игре задан адрес таблицы (FEEDBACK_URL; в тестах запрос копится в памяти).
func can_send() -> bool:
	return str(Content.consts.get("feedback_url", "")) != ""


func open(state: Dictionary) -> void:
	var st := state.duplicate()
	if not st.has("err"):
		st["err"] = ""
	if st["mode"] == "paste" and not st.has("text"):
		st["text"] = ""
	if st["mode"] == "builder":
		if not st.has("sel"):
			st["sel"] = []
		if not st.has("name"):
			st["name"] = ""
	_close_dlg()
	dlg = ShareDialog.make(st)
	Nav.show_modal(dlg)
	Audio.sfx("tick")


func _close_dlg() -> void:
	if dlg != null and is_instance_valid(dlg):
		Nav.hide_modal(dlg)
	dlg = null


## Закрыть окно; окно «скопировано» возвращает к тому, откуда копировали (итог, конструктор).
func close() -> void:
	var back: Variant = dlg.ui.get("back") if dlg != null else null
	_close_dlg()
	if back is Dictionary:
		dlg = ShareDialog.make(back)
		Nav.show_modal(dlg)
	Audio.sfx("tick")


## Скопировать и показать то же в окне (буфер недоступен — переписать с экрана).
func copy_show(text: String, title: String, note: String = "", kind: String = "code") -> void:
	var ok := clip_put(text)
	var back: Variant = dlg.ui if dlg != null else null
	open({"mode": "show", "text": text, "title": title, "note": note, "kind": kind, "ok": ok, "back": back})
	if ok:
		Audio.sfx("ok")


func copy_progress_code() -> void:
	copy_show(encode("P", progress_pack()), "КОД ПРОГРЕССА",
		"Вставь его в игре на другом устройстве: Настройки → Игра → «Вставить код».")


func copy_progress_link() -> void:
	copy_show(share_link([["load", encode("P", progress_pack())]]), "ССЫЛКА С ПРОГРЕССОМ",
		"Открой ссылку на другом устройстве — игра предложит загрузить прогресс.", "link")


## «Вставить код»: код прогресса, задания, результата или ссылка с ними. false — не распознан (apply_code).
func apply_code(text: String) -> bool:
	text = text.strip_edges()
	var params := parse_link(text)
	if params.get("load", "") != "":
		text = params["load"]
	elif not params.is_empty():
		var a := assign_parse(params)
		if a.is_empty():
			return false
		ask_assignment(a)
		return true
	var got := decode(text)
	if got.is_empty():
		return false
	if got[0] == "P":
		var p := progress_unpack(got[1])
		if p.is_empty():
			return false
		ask_load(p)
	elif got[0] == "J":
		var d: Dictionary = got[1]
		var a := assign_parse({"jobs": d.get("j"), "seat": d.get("s"), "from": d.get("f"), "title": d.get("ti")})
		if a.is_empty():
			return false
		ask_assignment(a)
	else:
		var res := result_unpack(got[1])
		if res.is_empty():
			return false
		open({"mode": "result", "res": res})
	return true


## Запуск со ссылкой: ?jobs=…&seat=… — задание (сразу), ?load=код — спросить, загрузить ли прогресс (apply_link).
func apply_link(query: String) -> void:
	var params := parse_link(query)
	if params.is_empty():
		return
	var a := assign_parse(params)
	if not a.is_empty():
		link_launch = true
		start_assignment(a)
	var code: String = params.get("load", "")
	if code == "":
		return
	link_launch = true
	var got := decode(code)
	var p := progress_unpack(got[1]) if not got.is_empty() and got[0] == "P" else {}
	if p.is_empty():
		Nav.flash("Код в ссылке не распознан — прогресс не тронут.", UI.BAD, 6.0)
		return
	if OS.has_feature("web"):               # на эту ссылку уже ответили (перезагрузка страницы)
		var seen: Variant = JavaScriptBridge.eval("localStorage.getItem('wnb:load_seen') || ''", true)
		if str(seen) == code.right(6):
			return
	ask_load(p, code.right(6))


func ask_load(p: Dictionary, link: String = "") -> void:
	var n := 0
	for j: Dictionary in Content.jobs:
		if j["id"] in p["done"]:
			n += 1
	var q := "Загрузить прогресс из ссылки? Текущий прогресс будет заменён." if link != "" else \
		"Загрузить прогресс из кода? Текущий прогресс будет заменён."
	var sub := "В коде: починено %d из %d, примерки %d/%d. Прежний прогресс сохранится — его можно вернуть в настройках." % [
		n, Content.jobs.size(), (p["seat_done"] as Array).size(), seat_ids().size()]
	open({"mode": "confirm", "q": q, "sub": sub, "yes": ["load", p], "link": link})


func ask_assignment(a: Dictionary) -> void:
	var n := assign_items(a).size()
	var q := ("Начать задание от %s?" % a["from"]) if a.get("from", "") != "" else "Начать задание?"
	open({"mode": "confirm", "q": q, "sub": "Пунктов: %d. Твой обычный прогресс не изменится." % n, "yes": ["assign", a]})


func start_assignment(a: Dictionary) -> void:
	SaveGame.start_assignment(a)
	summary_seen = ""
	resume_asked = true
	var n := assign_items(SaveGame.assign).size()
	var frm: String = SaveGame.assign.get("from", "")
	var msg := "Задание, пунктов в нём: %d. Выйти в обычную игру — кнопка «Выйти из задания» в мастерской." % n
	if frm != "":
		msg = "Задание от %s, пунктов в нём: %d. Выйти в обычную игру — кнопка «Выйти из задания» в мастерской." % [frm, n]
	Nav.flash(msg, UI.GOOD, 6.0)


## «Выйти из задания»: обычная игра, обычный прогресс на месте (прогресс задания сохранён до той же ссылки).
func exit_assignment() -> void:
	SaveGame.exit_assignment()
	_close_dlg()
	if Nav.settings != null:
		Nav.close_settings()
	if Nav.current_name in ["hub", "seating", "result"]:
		Nav.go("hub")
	Audio.sfx("whoosh")
	Nav.flash("Ты вышел из задания. Твой обычный прогресс — на месте.", UI.GOOD, 4.0)


func assign_result() -> Dictionary:
	return result_unpack(result_pack(SaveGame.assign))


## Всё выполнено — показать итог (сам — один раз; again — и повторно: «К итогу задания»).
func maybe_summary(again: bool = false) -> void:
	if not (SaveGame.assign_on() and SaveGame.assign_complete()):
		return
	var first: bool = summary_seen != SaveGame.assign["id"]
	if first or again:
		summary_seen = SaveGame.assign["id"]
		open({"mode": "summary"})
		if first:
			Audio.sfx("fanfare")


## Итог для таблицы — те же поля, что у замечания + type "result" (_result_payload).
func result_payload() -> Dictionary:
	var a := SaveGame.assign
	var res := assign_result()
	var en: Array = in_lang("en", func() -> Array: return [result_text(res, result_code(a)), result_summary(res["rows"])])
	var jobs := {}
	for r: Array in res["rows"]:
		jobs[r[0]] = {"done": r[1], "errors": r[2], "secs": r[3]}
	return {"key": Feedback.key, "type": "result", "time": Time.get_datetime_string_from_system(false, false),
		"lang": Loc.code, "scene": "assignment", "job": a["id"], "title": a.get("title", ""), "phase": "", "step": "",
		"kind": "result", "reason": ("From: " + a["from"]) if a.get("from", "") != "" else "", "expected": "",
		"got": en[1], "game_message": "", "comment": en[0], "assignment": a["id"], "from": a.get("from", ""),
		"jobs": jobs, "version": str(Content.consts.get("version", "")), "platform": Feedback.platform()}


## «Отправить в таблицу»: тот же канал, что у замечаний (очередь, досылка); один раз на задание.
func send_result() -> void:
	var a := SaveGame.assign
	if a.is_empty() or not can_send() or a.get("sent", false):
		return
	var sent_now := Feedback.send(result_payload())
	a["sent"] = true
	SaveGame.save()
	Audio.sfx("ok")
	var ok := sent_now or Feedback.url == ""         # в тестах — в памяти (как headless в game.py)
	Nav.flash("Итог отправлен в таблицу." if ok else "Не отправилось — нет связи. Скопируй код результата.",
		UI.GOOD if ok else UI.AMBER, 4.0)


func _builder_assign(ui: Dictionary) -> Dictionary:
	var jobs: Array = (ui["sel"] as Array).filter(func(k: String) -> bool: return not k.begins_with("seat_"))
	var seat: Array = (ui["sel"] as Array).filter(func(k: String) -> bool: return k.begins_with("seat_"))
	return assign_parse({"jobs": jobs, "seat": seat, "from": ui.get("name", "")})


func _seen_link(ui: Dictionary) -> void:
	if ui.get("link", "") != "" and OS.has_feature("web"):
		JavaScriptBridge.eval("localStorage.setItem('wnb:load_seen', %s)" % JSON.stringify(ui["link"]))


## Кнопка окна (_share_action).
func dlg_action(d: ShareDialog, key: String) -> void:
	var ui := d.ui
	var m: String = ui["mode"]
	match key:
		"close", "cancel", "no":
			if m == "confirm":
				_seen_link(ui)
			close()
		"copy":
			ui["ok"] = clip_put(ui["text"])
			if ui["ok"]:
				Audio.sfx("ok")
			d.queue_redraw()
		"clip":
			ui["text"] = clip_get().strip_edges().substr(0, max_len())
			ui["err"] = "" if ui["text"] != "" else "Буфер обмена пуст."
			Audio.sfx("tick")
			d.queue_redraw()
		"apply":
			var text: String = ui.get("text", "")
			_close_dlg()
			if not apply_code(text):
				open({"mode": "paste", "text": text, "err": "Код не распознан — прогресс не тронут."})
				Audio.sfx("bad")
		"yes":
			var what: String = ui["yes"][0]
			var val: Dictionary = ui["yes"][1]
			_seen_link(ui)
			_close_dlg()
			if what == "load":
				SaveGame.apply_progress(val)
				_progress_reset_scene()
				Audio.sfx("fanfare")
				Nav.flash("Прогресс загружен. Прежний можно вернуть: Настройки → Игра.", UI.GOOD, 5.0)
			else:
				if Nav.settings != null:
					Nav.close_settings()
				start_assignment(val)
				if Nav.current_name != "title":
					_progress_reset_scene()
		"resume":
			_close_dlg()
			Audio.sfx("tick")
			Nav.go("hub")
		"normal":
			_close_dlg()
			SaveGame.exit_assignment()
			Audio.sfx("whoosh")
			Nav.go("hub")
			Nav.flash("Ты вышел из задания. Твой обычный прогресс — на месте.", UI.GOOD, 4.0)
		"rcode":
			copy_show(result_code(SaveGame.assign), "КОД РЕЗУЛЬТАТА",
				"Отправь его тому, кто дал задание: он вставит код в игре (Настройки → Игра → «Вставить код»).")
		"rtext":
			var res: Dictionary = ui.get("res", {}) if m == "result" else assign_result()
			copy_show(result_text(res, result_code(SaveGame.assign) if m == "summary" else ""), "ИТОГ ТЕКСТОМ",
				"Вставь в мессенджер или письмо.", "text")
		"send":
			send_result()
			d.build()
		"exit":
			exit_assignment()
		"clear":
			ui["sel"] = []
			Audio.sfx("tick")
			d.build()
		"make":
			var a := _builder_assign(ui)
			if a.is_empty():
				ui["err"] = "Отметь хотя бы одно задание."
				Audio.sfx("bad")
				d.queue_redraw()
				return
			if OS.has_feature("web"):
				copy_show(share_link(assign_params(a)), "ССЫЛКА-ЗАДАНИЕ",
					"Отправь ссылку ученику: игра откроется сразу с этими заданиями.", "link")
			else:
				copy_show(assign_code(a), "КОД ЗАДАНИЯ",
					"Ученик вставит его в игре: Настройки → Игра → «Вставить код». В браузерной версии игры ту же подборку можно отправить ссылкой.")


## Прогресс заменили — окна закрыть, вернуться в мастерскую (с титула — остаться на титуле).
func _progress_reset_scene() -> void:
	if Nav.settings != null:
		Nav.close_settings()
	if Nav.current_name != "title":
		Nav.go("hub")


## Запуск без ссылки, а в сохранении — активное незаконченное задание: при входе в мастерскую спросить
## «продолжить задание или обычная игра» (отступление от релиза по просьбе владельца, 12.11).
func maybe_ask_resume() -> bool:
	if resume_asked or link_launch or not SaveGame.assign_on() or SaveGame.assign_complete():
		return false
	resume_asked = true
	var a := SaveGame.assign
	var n := assign_items(a).size()
	var k := (a["done"] as Dictionary).size()
	var q := "Продолжить задание (%d/%d) или обычная игра?" % [k, n]
	if a.get("from", "") != "":
		q = "Продолжить задание от %s (%d/%d) или обычная игра?" % [a["from"], k, n]
	open({"mode": "resume", "q": q,
		"sub": "Обычная игра — твой прогресс; задание сохранится, та же ссылка вернёт его с места."})
	return true
