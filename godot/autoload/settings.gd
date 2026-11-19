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
	if not a11y.get("calm_set", false) and OS.has_feature("web") and not args.has("--test"):
		# «Без анимации» по системе: в браузере — prefers-reduced-motion (в Godot 4.7 своего API нет; на Windows —
		# SPI_GETCLIENTAREAANIMATION, из GDScript недоступно — остаётся выбор игрока)
		a11y["calm"] = bool(JavaScriptBridge.eval("!!(window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches)", true))
	if args.has("--calm"):
		a11y["calm"] = true


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
	if FileAccess.file_exists(PATH):
		text = FileAccess.get_file_as_string(PATH)
	else:
		text = web_legacy("settings.json")       # первый запуск в браузере — настройки pygame-версии, если были
		legacy = text != ""
	var data: Variant = JSON.parse_string(text) if text != "" else null
	if not data is Dictionary:
		return
	if legacy:
		save.call_deferred()                     # дальше — свой файл
	var d: Dictionary = data
	for k: String in d:
		if not k in ["volume", "lang", "glow", "a11y"]:
			_extra[k] = d[k]
	var v: Variant = d.get("volume")
	if v is Dictionary:
		for k: String in ["master", "music", "sfx", "amb"]:
			var x: Variant = v.get(k)
			if (x is float or x is int) and is_finite(float(x)):
				vol[k] = clampf(float(x), 0.0, 1.0)
		if v.get("on") is bool:
			vol["on"] = v["on"]
	if d.get("glow") is bool:
		glow = d["glow"]
	if d.get("lang") is String and d["lang"] in ["ru", "en"]:
		lang = d["lang"]
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


func save() -> void:
	if not persist:
		return
	var d: Dictionary = _extra.duplicate()
	d["volume"] = vol.duplicate()
	d["lang"] = lang
	d["glow"] = glow
	d["a11y"] = a11y.duplicate()
	var tmp := PATH + ".tmp"
	var f := FileAccess.open(tmp, FileAccess.WRITE)
	if f == null:
		push_warning("settings.json не записан: %s" % error_string(FileAccess.get_open_error()))
		return
	f.store_string(JSON.stringify(d, "  "))
	f.close()
	DirAccess.rename_absolute(tmp, PATH)


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
