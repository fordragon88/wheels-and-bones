extends Node
## Настройки игрока: user://settings.json. Имена ключей — как в settings.json pygame-версии (volume, lang, glow,
## a11y{…}), чтобы файл можно было перенести как есть; незнакомые ключи (fullscreen, res, gpu3d…) сохраняются нетронутыми.

signal changed(key: String)

const PATH := "user://settings.json"
const TEXT_K: Array[float] = [1.0, 1.12, 1.25, 1.5]   # game.TEXT_K: 100/112/125/150 %

var vol: Dictionary = {"master": 0.8, "music": 0.45, "sfx": 0.9, "amb": 0.45, "on": true}
var lang: String = "en"                # как в pygame: по умолчанию английский (аудитория), русский — переключателем
var glow: bool = true                  # «Свечение и частицы»
var a11y: Dictionary = {
	"on": false, "voices": true, "rate": 0, "contrast": false, "instant": false, "speech_set": false,
	"text": 0, "text_set": false, "calm": false, "calm_set": false, "scan": 0, "font": false,
	"barty": true, "quiet": false, "quiet_set": false,
}
var persist: bool = true               # тесты (--test): файл не читаем и не пишем
var text_cap: float = 0.0              # потолок крупного текста для плотных окон (как text_cap() в game.py); 0 — нет
var _extra: Dictionary = {}            # ключи pygame-версии, которых тут нет: пишем обратно как были
var _sys_thread: Thread                # Windows: опрос «Эффектов анимации» в фоне


func _init() -> void:
	var args := OS.get_cmdline_user_args()
	persist = not args.has("--test")
	if OS.has_feature("web"):
		a11y["text"] = 2               # в браузере окно мельче — сразу 125 % (как в game.py)
	if persist:
		_load()
	var i := args.find("--lang")
	if i >= 0 and i + 1 < args.size():
		lang = "ru" if args[i + 1] == "ru" else "en"
	if OS.has_feature("web"):
		lang = "en"                        # как game.py: set_lang("en" if IS_WEB …) — в браузере всегда по-английски,
		                                   # русский — только переключателем в игре (решение владельца 20.11)
	# «Без анимации» по системе, пока игрок не выбрал сам (calm_set) — как system_reduced_motion() в game.py:
	# браузер — prefers-reduced-motion; Windows — «Эффекты анимации» (SPI_GETCLIENTAREAANIMATION). В тестах (--test)
	# система не спрашивается; «-- --system-calm=0|1» — подменить ответ системы (проверка приоритета выбора игрока).
	var sys_arg := ""
	for a: String in args:
		if a.begins_with("--system-calm="):
			sys_arg = a.trim_prefix("--system-calm=")
	if sys_arg != "":
		apply_system_calm(sys_arg == "1")
	elif not args.has("--test"):
		if OS.has_feature("web"):
			apply_system_calm(bool(JavaScriptBridge.eval("!!(window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches)", true)))
		elif OS.get_name() == "Windows" and not a11y.get("calm_set", false):
			_sys_thread = Thread.new()          # PowerShell отвечает ~0,6–1 с — не держать запуск игры
			_sys_thread.start(func() -> void:
				var v: Variant = windows_animations_off()
				if v != null:
					apply_system_calm.call_deferred(v))
	if args.has("--calm"):
		a11y["calm"] = true


## Ответ системы «анимации выключены» → «Без анимации», если игрок не выбирал сам (calm_set — его выбор главнее).
func apply_system_calm(off: bool) -> void:
	if a11y.get("calm_set", false) or bool(a11y.get("calm", false)) == off:
		return
	a11y["calm"] = off
	changed.emit("calm")


## Windows: SystemParametersInfo(SPI_GETCLIENTAREAANIMATION) — тот же вызов, что в game.py (ctypes). Из GDScript
## user32 не позвать, поэтому — через PowerShell (есть в каждой Windows, без сторонних библиотек): true —
## анимации выключены, false — включены, null — не удалось узнать (тогда как раньше: решает игрок).
static func windows_animations_off() -> Variant:
	var ps := "Add-Type -Name W -Namespace WnbSpi -MemberDefinition '[DllImport(\"user32.dll\")] public static extern " 		+ "bool SystemParametersInfo(int a, int b, ref int c, int d);'; $v = 1; " 		+ "if ([WnbSpi.W]::SystemParametersInfo(0x1042, 0, [ref]$v, 0)) { [Console]::Out.Write($v) } else { [Console]::Out.Write('x') }"
	var out: Array = []
	var code := OS.execute("powershell.exe", ["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
		"-EncodedCommand", Marshalls.raw_to_base64(ps.to_utf16_buffer())], out)
	var r := str(out[0]).strip_edges() if code == 0 and not out.is_empty() else ""
	if r == "0":
		return true
	if r == "1":
		return false
	return null


func _exit_tree() -> void:
	if _sys_thread != null and _sys_thread.is_started():
		_sys_thread.wait_to_finish()


# ---------------- хранилище файлов игрока (save.json, settings.json, копии) ----------------
# Компьютер — файлы user:// (как было). Браузер — localStorage, ключ на файл «wnb-godot:<имя>» (как game.py хранит
# «wnb:<имя>»; «wnb:» — ключи pygame-версии, их только читаем при переносе). Почему не user://: там IDBFS — каждая
# вкладка держит копию всей папки и при любой записи синхронизирует её в IndexedDB целиком, удаляя файлы, которых у
# неё нет: вторая открытая вкладка, сменив настройку, стирала прогресс первой. localStorage синхронен и пишется по
# ключу. Нет localStorage (SecurityError: запрет cookie, сторонний фрейм) — запасной путь user://.

const STORE_NS := "wnb-godot:"
const STORE_FILES: Array[String] = ["save.json", "save.prev.json", "save.bak.json", "settings.json"]
static var _ls: int = -1                   # localStorage: -1 не проверяли, 0 нет, 1 есть
static var _moved: bool = false           # перенос user:// → localStorage проверен в этом запуске


## Браузер и localStorage доступен (запись пробным ключом) — хранение по ключам; иначе файлы user://.
static func store_ls() -> bool:
	if _ls < 0:
		_ls = 0
		if OS.has_feature("web"):
			var v: Variant = JavaScriptBridge.eval("(function(){try{var k='wnb-godot:probe';localStorage.setItem(k,'1');"
				+ "localStorage.removeItem(k);return 1}catch(e){return 0}})()", true)
			_ls = 1 if v != null and int(v) == 1 else 0
	return _ls == 1


static func _js_key(name: String) -> String:
	return JSON.stringify(STORE_NS + name)


## Один раз: сохранения Godot-версии, записанные до 20.11 в user:// (IndexedDB), — в ключи localStorage. Файлы
## user:// не удаляются (на случай отката). Отметка «wnb-godot:moved» — переносим только раз (иначе после «Сбросить
## прогресс» и удаления копии старый файл вернулся бы) и только если все файлы записались: место в localStorage
## кончилось — отметки нет, перенос повторится при следующем запуске (обзор 26.11, E3; раньше отметка ставилась
## всегда, и прогресс из user:// больше не переносился).
static func _move_once() -> void:
	if _moved:
		return
	_moved = true
	var done: Variant = JavaScriptBridge.eval("(function(){try{return localStorage.getItem('wnb-godot:moved')||''}catch(e){return ''}})()", true)
	if str(done) == "1":
		return
	var ok := true
	for name: String in STORE_FILES:
		var p := "user://" + name
		if FileAccess.file_exists(p) and not _ls_has(name):
			if not _ls_set(name, FileAccess.get_file_as_string(p)):
				ok = false
				push_warning("%s не перенесён из user:// в localStorage (место кончилось?) — повторю при следующем запуске" % name)
	if ok:
		JavaScriptBridge.eval("(function(){try{localStorage.setItem('wnb-godot:moved','1')}catch(e){}})()", true)


static func _ls_has(name: String) -> bool:
	return bool(JavaScriptBridge.eval("(function(){try{return localStorage.getItem(%s)!==null}catch(e){return false}})()"
		% _js_key(name), true))


static func _ls_set(name: String, text: String) -> bool:
	var ok: Variant = JavaScriptBridge.eval("(function(){try{localStorage.setItem(%s,%s);return 1}catch(e){return 0}})()"
		% [_js_key(name), JSON.stringify(text)], true)
	return ok != null and int(ok) == 1


## Текст файла игрока; "" — нет файла.
static func store_read(name: String) -> String:
	if store_ls():
		_move_once()
		var v: Variant = JavaScriptBridge.eval("(function(){try{return localStorage.getItem(%s)||''}catch(e){return ''}})()"
			% _js_key(name), true)
		return str(v) if v != null else ""
	var p := "user://" + name
	return FileAccess.get_file_as_string(p) if FileAccess.file_exists(p) else ""


static func store_has(name: String) -> bool:
	if store_ls():
		_move_once()
		return _ls_has(name)
	return FileAccess.file_exists("user://" + name)


## Записать файл игрока целиком (компьютер — во временный файл и переименованием).
static func store_write(name: String, text: String) -> bool:
	if store_ls():
		_move_once()
		if _ls_set(name, text):
			return true
		push_warning("%s не записан в localStorage (место кончилось?)" % name)
		return false
	var path := "user://" + name
	var tmp := path + ".tmp"
	var f := FileAccess.open(tmp, FileAccess.WRITE)
	if f == null:
		push_warning("%s не записан: %s" % [name, error_string(FileAccess.get_open_error())])
		return false
	f.store_string(text)
	f.close()
	return DirAccess.rename_absolute(tmp, path) == OK


static func store_remove(name: String) -> void:
	if store_ls():
		_move_once()
		JavaScriptBridge.eval("(function(){try{localStorage.removeItem(%s)}catch(e){}})()" % _js_key(name), true)
		return
	if FileAccess.file_exists("user://" + name):
		DirAccess.remove_absolute("user://" + name)


## Браузер: файл pygame-версии с того же сайта (она хранит save.json/settings.json в localStorage «wnb:<имя>»,
## game.web_persist); "" — нет. Только читаем — старое не трогаем.
static func web_legacy(name: String) -> String:
	if not OS.has_feature("web"):
		return ""
	var v: Variant = JavaScriptBridge.eval("(function(){try{return localStorage.getItem(%s)||''}catch(e){return ''}})()" %
		JSON.stringify("wnb:" + name), true)
	return str(v) if v != null else ""


func _load() -> void:
	var text := ""
	var legacy := false
	if store_has("settings.json"):
		text = store_read("settings.json")
	else:
		text = web_legacy("settings.json")       # первый запуск в браузере — настройки pygame-версии, если были
		legacy = text != ""
	if load_text(text) and legacy:
		save.call_deferred()                     # дальше — свой файл


## Разбор текста settings.json (как load_settings в game.py: каждое поле отдельно, неверный тип — значение по
## умолчанию). false — не словарь JSON (битый/пустой файл): ничего не меняется. Сверка с game.py — tests/save_compat.gd.
func load_text(text: String) -> bool:
	var data: Variant = parse_json(text)
	if not data is Dictionary:
		return false
	var d: Dictionary = data
	for k: String in d:
		if not k in ["volume", "lang", "glow", "a11y"]:
			_extra[k] = d[k]
	# как game.py: float(x) (числа, флажки, строки с числом), «on»/«glow» — bool(x) (пустое/0/null — нет)
	var v: Variant = d.get("volume")
	if v is Dictionary:
		for k: String in ["master", "music", "sfx", "amb"]:
			if v.has(k):
				var x: Variant = py_float(v[k])
				if x != null and is_finite(x):
					vol[k] = clampf(x, 0.0, 1.0)
		if v.has("on"):
			vol["on"] = py_bool(v["on"])
	if d.has("glow"):
		glow = py_bool(d["glow"])
	var lv: Variant = d.get("lang")             # set_lang(str(x).lower()): незнакомый — английский
	if py_bool(lv):
		lang = "ru" if str(lv).to_lower() == "ru" else "en"
	var acc: Variant = d.get("a11y")
	if acc is Dictionary:
		for k: String in a11y:
			if k == "calm" and not acc.get("calm_set", false):
				continue                   # анимацию игрок сам не выключал — по умолчанию
			if k == "text" and not acc.get("text_set", false):
				continue
			var x: Variant = acc.get(k)
			if a11y[k] is bool:
				if x is bool:
					a11y[k] = x
			elif (x is float or x is int) and not x is bool and is_finite(float(x)):
				a11y[k] = int(clampf(float(x), -10, 10))
	a11y["scan"] = 0                       # режим одной кнопки выключен (SCAN_ENABLED = False в game.py)
	return true


func save() -> void:
	if not persist:
		return
	var d: Dictionary = _extra.duplicate()
	d["volume"] = vol.duplicate()
	d["lang"] = lang
	d["glow"] = glow
	d["a11y"] = a11y.duplicate()
	store_write("settings.json", JSON.stringify(d, "  "))


## Разбор JSON без ERROR в журнале (битый файл сохранения — обычное дело, а не ошибка движка): null — не JSON.
static func parse_json(text: String) -> Variant:
	if text.strip_edges() == "":
		return null
	var j := JSON.new()
	return j.data if j.parse(text) == OK else null


## bool(x) Python для значения JSON: null, false, 0, "", [], {} — ложь.
static func py_bool(x: Variant) -> bool:
	if x == null:
		return false
	if x is bool:
		return x
	if x is int or x is float:
		return x != 0
	if x is String or x is Array or x is Dictionary:
		return not x.is_empty()
	return true


## float(x) Python для значения JSON (флажок → 0/1, строка с числом); нельзя — null.
static func py_float(x: Variant) -> Variant:
	if x is bool:
		return 1.0 if x else 0.0
	if x is int or x is float:
		return float(x)
	if x is String:
		var t: String = x.strip_edges()
		if t.is_valid_float() or t.is_valid_int():
			return t.to_float()
	return null


## int(x) Python для значения JSON (дробь — к нулю, флажок → 0/1, строка — только целое); нельзя — null.
static func py_int(x: Variant) -> Variant:
	if x is bool:
		return 1 if x else 0
	if x is int or (x is float and is_finite(x)):
		return int(x)
	if x is String:
		var t: String = x.strip_edges().replace("_", "")
		if t.is_valid_int():
			return t.to_int()
	return null


## Поменять настройку и сохранить: set_a11y("calm", true) / set_vol("music", 0.3)
func set_a11y(key: String, value: Variant) -> void:
	a11y[key] = value
	var marks := {"calm": "calm_set", "text": "text_set", "quiet": "quiet_set", "on": "speech_set"}
	if marks.has(key):
		a11y[marks[key]] = true            # игрок выбрал сам — не перекрывать системным/по умолчанию
	save()
	changed.emit(key)


func set_vol(key: String, value: Variant) -> void:
	vol[key] = value
	save()
	changed.emit("vol")


func set_lang(code: String) -> void:
	lang = "ru" if code == "ru" else "en"
	save()
	changed.emit("lang")


## Множитель крупного текста (TEXT_K по выбору игрока, не больше потолка text_cap).
func text_k() -> float:
	var k: float = TEXT_K[clampi(int(a11y.get("text", 0)), 0, TEXT_K.size() - 1)]
	return minf(k, text_cap) if text_cap > 0.0 else k


## Окно второго Esc (выйти из ремонта / из игры): с «Одной кнопкой» — 10 с, иначе 2,5 с (как esc_timer в game.py).
func esc_secs() -> float:
	return 10.0 if int(a11y.get("scan", 0)) != 0 else 2.5


func calm() -> bool:
	return bool(a11y.get("calm", false))


func barty_on() -> bool:
	return bool(a11y.get("barty", true))


## Клиент говорит одну фразу при входе (по умолчанию — вместе с «Без анимации»).
func quiet_talk() -> bool:
	return bool(a11y.get("quiet", false)) if a11y.get("quiet_set", false) else calm()


## Шрифт для лёгкого чтения — только в английском (в Atkinson нет кириллицы), как easy_font_on().
func easy_font() -> bool:
	return bool(a11y.get("font", false)) and lang == "en"


func glow_on() -> bool:
	return glow and not calm()
