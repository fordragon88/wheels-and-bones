extends Node
## Озвучка для незрячих (класс Speech и Game.say/a11y_frame в game.py). Speech.say(text, interrupt) — в очередь кадра;
## в конце кадра всё сказанное за кадр уходит одной фразой (interrupt — если хоть одна фраза его просила).
## Чем говорит (как в game.py: чтец игрока важнее голоса системы):
##   test   — самопроверка и снимки (--test): НИЧЕГО не звучит, фразы только пишутся в журнал (history);
##   web    — браузер: фраза всегда уходит в скрытую область aria-live страницы (её читает чтец страницы), голосом
##            браузера (Web Speech, wnbSay) — только при F2; проверено web_smoke (текст в #wnb-live, вызов голоса);
##   reader — на компьютере работает чтец экрана (NVDA, JAWS, Экранный диктор): фразы — в «живую область» Godot
##            (AccessKit), фокус чтец читает сам по именам элементов — своим голосом фокус НЕ дублируем;
##   tts    — чтеца нет: голос системы (Windows — SAPI/OneCore) на языке игры, скорость из настроек;
##   ""     — голосов нет: «Озвучка недоступна».
## Говорит только при включённой озвучке (F2, Settings.a11y.on); журнал ведётся всегда.

signal spoke(text: String)

var history: Array[String] = []           # что сказано (для тестов и повтора), до 200 фраз
var kind: String = ""
var _queue: Array = []                    # [текст, interrupt]
var _voice: String = ""
var _live: Label                          # «живая область» для чтеца экрана (AccessKit)
var _uid: int = 0

const SUBS := [["✔", ""], ["⚑", ""], ["◉", ""], ["○", ""], ["✉", ""], ["⚠", ""], ["▶", ""], ["◀", ""], ["★", ""],
	["☆", ""], ["⟲", ""], ["•", ""], ["[", ""], ["]", ""], ["…", "..."], ["·", ","], ["″", ""]]


func _ready() -> void:
	process_priority = 1000                # после экранов: очередь кадра — одной фразой
	init()


## Выбор голоса (Speech.init в game.py).
func init() -> void:
	if OS.get_cmdline_user_args().has("--test"):
		kind = "test"
	elif OS.has_feature("web"):
		kind = "web"
		_web_setup()
	elif DisplayServer.has_method("accessibility_screen_reader_active") and DisplayServer.accessibility_screen_reader_active() > 0:
		kind = "reader"
	elif not DisplayServer.tts_get_voices().is_empty():
		kind = "tts"
	else:
		kind = ""
	set_voice()


## Голос на языке игры (русский — Irina/Pavel, английский — David/Zira…).
func set_voice() -> void:
	_voice = ""
	if kind in ["tts", "web"] and not OS.get_cmdline_user_args().has("--test"):
		var vs := DisplayServer.tts_get_voices_for_language("ru" if Loc.code == "ru" else "en")
		if not vs.is_empty():
			_voice = vs[0]
	if kind == "web":
		JavaScriptBridge.eval("document.documentElement.setAttribute('data-wnb-lang', '%s')" %
			("ru-RU" if Loc.code == "ru" else "en-US"), true)


## Чем говорит — для подписи «Озвучка: …» (Speech.label в game.py).
func label() -> String:
	match kind:
		"web":
			return "экранный чтец страницы" + (" + голос браузера" if Settings.a11y.get("on", false) else "")
		"reader":
			return "экранный чтец"
		"tts":
			return "голос Windows" if OS.get_name() == "Windows" else "голос системы"
	return "недоступна"


## Текст для голоса: без значков, «1920×1080» — словами (speech_clean).
static func clean(text: String) -> String:
	var t := text
	for s: Array in SUBS:
		t = t.replace(s[0], s[1])
	t = RegEx.create_from_string("(\\d)\\s*×\\s*(\\d)").sub(t, "$1 " + ("на" if Loc.code == "ru" else "by") + " $2", true)
	t = RegEx.create_from_string("\\s*—\\s*").sub(t, ", ", true)
	t = RegEx.create_from_string("\\s+").sub(t, " ", true)
	t = RegEx.create_from_string("\\s+([,.!?:;])").sub(t, "$1", true)
	t = RegEx.create_from_string("([.!?])[.,]+(?=\\s|$)").sub(t, "$1", true)
	t = RegEx.create_from_string(",\\s*,").sub(t, ",", true)
	while t.begins_with(" ") or t.begins_with(","):
		t = t.substr(1)
	while t.ends_with(" ") or t.ends_with(","):
		t = t.substr(0, t.length() - 1)
	return t


## В очередь кадра (Game.say). Текст уже на языке игры.
func say(text: String, interrupt: bool = false) -> void:
	if text.strip_edges() == "":
		return
	_queue.append([text, interrupt])


## Сразу, мимо очереди (Speech.say в game.py — «Озвучка выключена» и т. п.).
func say_now(text: String, interrupt: bool = true) -> void:
	_output(clean(text), interrupt)


func _process(_dt: float) -> void:
	if _queue.is_empty():
		return
	var parts: Array = []
	var intr := false
	for q: Array in _queue:
		parts.append(q[0])
		intr = intr or q[1]
	_queue.clear()
	_output(clean(" ".join(parts)), intr)


func _output(text: String, interrupt: bool) -> void:
	if text == "":
		return
	history.append(text)
	if history.size() > 200:
		history = history.slice(history.size() - 200)
	spoke.emit(text)
	var on: bool = Settings.a11y.get("on", false)
	match kind:
		"web":                                 # чтец страницы читает всегда, голос браузера — по F2
			JavaScriptBridge.eval("window.wnbSay && wnbSay(%s, %s, %s)" % [JSON.stringify(text), str(interrupt).to_lower(),
				str(on).to_lower()], true)
		"reader":
			if on:
				_live_say(text)
		"tts":
			if on:
				_uid += 1
				DisplayServer.tts_speak(text, _voice, 100, 1.0, rate_k(), _uid, interrupt)


## Скорость голоса: −10…10 как у SAPI → множитель tts (0 — обычная; 10 — втрое быстрее, −10 — втрое медленнее).
static func rate_k() -> float:
	return clampf(pow(3.0, float(Settings.a11y.get("rate", 0)) / 10.0), 0.1, 10.0)


## Чтец экрана: фраза — в «живую область» (AccessKit объявляет её голосом чтеца, с его скоростью и брайлем).
func _live_say(text: String) -> void:
	if _live == null:
		_live = Label.new()
		_live.name = "SpeechLive"
		_live.modulate = Color(1, 1, 1, 0)
		_live.mouse_filter = Control.MOUSE_FILTER_IGNORE
		_live.accessibility_live = AccessibilityServer.AccessibilityLiveMode.LIVE_ASSERTIVE
		var layer := CanvasLayer.new()
		layer.layer = 100
		layer.add_child(_live)
		get_tree().root.add_child.call_deferred(layer)
	_live.text = ""
	_live.text = text


func stop() -> void:
	_queue.clear()
	if kind == "tts":
		DisplayServer.tts_stop()


func last() -> String:
	return history[-1] if not history.is_empty() else ""


## Браузер: скрытая область aria-live + голос браузера по F2 (wnbSay в game.py; проверено web_smoke: текст появляется
## в #wnb-live, голос — speechSynthesis, в проверке подменён заглушкой).
func _web_setup() -> void:
	JavaScriptBridge.eval("""(function(){
	  if (window.wnbSay) return;
	  var live = document.getElementById('wnb-live');   // есть в странице сборки (web/shell.html)
	  if (!live) {
	    live = document.createElement('div');
	    live.id = 'wnb-live'; live.setAttribute('aria-live', 'assertive'); live.setAttribute('role', 'status');
	    live.style.cssText = 'position:absolute;left:-9999px;width:1px;height:1px;overflow:hidden';
	    document.body.appendChild(live);
	  }
	  window.wnbSay = function(t, intr, voice){
	    live.textContent = ''; setTimeout(function(){ live.textContent = t; }, 30);
	    if (!voice || !window.speechSynthesis || !window.SpeechSynthesisUtterance) return;   // браузер без голоса
	    if (intr) speechSynthesis.cancel();
	    var u = new SpeechSynthesisUtterance(t);
	    u.lang = document.documentElement.getAttribute('data-wnb-lang') || 'en-US';
	    speechSynthesis.speak(u);
	  };
	})()""", true)
