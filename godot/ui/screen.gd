class_name Screen
extends Control
## Основа экрана: корневой Control 1280×720; содержимое собирает build() кодом. При смене языка, размера текста
## или шрифта экран пересобирается (rebuild) — состояние экрана живёт в его переменных, не в элементах.
## Nav зовёт go_back() на Esc/«назад», music_theme() — тема музыки, toast_bounds() — где сообщение сверху.

var params: Dictionary = {}
var screen_name: String = ""
var st: float = 0.0                       # секунд с начала экрана (появления, как self.st в game.py)
var t: float = 0.0                        # общие часы экрана (качание, мерцание)


func _init() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_PASS
	focus_mode = Control.FOCUS_NONE


func _ready() -> void:
	Loc.changed.connect(_on_lang)
	Settings.changed.connect(_on_settings)
	build()
	_focus_default()


func _process(dt: float) -> void:
	st += dt
	t += dt
	Figure.want_scene_loops(screen_name)      # петли Мартина экранов — заранее (браузер: качаются с сайта)
	if Prof.on:
		var p0 := Prof.t0()
		tick(dt)
		Prof.add("tick:" + screen_name, p0)
		return
	tick(dt)


## Собрать содержимое (переопределяется).
func build() -> void:
	pass


## Логика экрана каждый кадр (переопределяется).
func tick(_dt: float) -> void:
	pass


## Элемент, который получает фокус при входе (клавиатура/геймпад/чтец экрана); null — никакой.
func first_focus() -> Control:
	return null


## Esc / кнопка «назад».
func go_back() -> void:
	pass


func music_theme() -> String:
	return "workshop"


## Потолок крупного текста на экране (text_cap в game.py: плотные экраны — 1,25), 0 — нет.
func text_cap() -> float:
	return 0.0


## Сообщение сверху: [левый край, запас справа] (как reserve в _draw_toast).
func toast_bounds() -> Vector2:
	return Vector2(54, 164)


## Клавиши экрана (до общих: Esc, M). true — обработано.
func handle_key(_e: InputEventKey) -> bool:
	return false


## Сенсорный экран: где тап чуть мимо цели переносится в ближайшую (_touch_snap в game.py) — узел, чьи кнопки
## считаются целями (Nav.touch_snap). null — не переносить (экраны и окна, где game.py этого не делает).
func touch_scope() -> Control:
	return null


## Для флажка ⚑: где игрок (как open_feedback в game.py).
func feedback_context() -> Dictionary:
	return {"kind": "general", "job": "", "title": "", "phase": screen_name, "step": "", "expected": "", "got": "",
		"msg": "", "scene": screen_name}


## Что сказать при входе на экран (a11y_summary): где ты и что делать.
func summary() -> String:
	return ""


## Сводка экрана: full — полная (новый экран, R), иначе — короткая (сменилось состояние экрана).
func summary_full(_full: bool) -> String:
	return summary()


## Состояние экрана для озвучки: изменилось — сказать сводку снова (_a11y_sig в game.py).
func a11y_sig() -> Array:
	return []


## Реплики героев на экране сейчас (вслух при «Реплики героев вслух»): клиент, Барти, Мортимер.
func a11y_lines() -> Array:
	return []


## H — подсказка призрака; C — что сказал клиент.
func hint_line() -> String:
	return ""


func client_now() -> String:
	return ""


func rebuild() -> void:
	var fo := get_viewport().gui_get_focus_owner() if is_inside_tree() else null
	var path := get_path_to(fo) if fo != null and is_ancestor_of(fo) else NodePath()
	for c in get_children():
		remove_child(c)
		c.queue_free()
	build()
	if not path.is_empty() and has_node(path):
		var n := get_node(path)
		if n is Control and (n as Control).focus_mode != Control.FOCUS_NONE:
			UI.focus_later(n as Control)
			return
	_focus_default()


func _focus_default() -> void:
	var f := first_focus()
	UI.focus_later(f)


func _on_lang() -> void:
	UI.clear_font_cache()                 # шрифт для лёгкого чтения — только в английском
	rebuild()


func _on_settings(key: String) -> void:
	if key in ["text", "font", "contrast", "calm", "barty", "phone"]:
		UI.clear_font_cache()
		rebuild()


## Перерисовать ci, только если подпись sig (всё, от чего зависит его рисунок) изменилась с прошлого раза.
## Неподвижное каждый кадр не перерисовываем: на слабом процессоре это и есть кадр (скорость, 19.11).
static func redraw_on(ci: CanvasItem, sig: Array) -> void:
	if not ci.has_meta("redraw_sig") or ci.get_meta("redraw_sig") != sig:
		ci.set_meta("redraw_sig", sig)
		ci.queue_redraw()


## Подпись для чтеца экрана (accessibility_name), переведённая.
static func a11y(ctl: Control, ru: String, desc: String = "") -> void:
	ctl.accessibility_name = Loc.t(ru)
	if desc != "":
		ctl.accessibility_description = Loc.t(desc)
