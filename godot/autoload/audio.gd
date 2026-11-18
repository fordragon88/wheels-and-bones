extends Node
## Звук: Audio.sfx("ok") — эффекты из content/sfx/*.wav (выгружены из синтезатора pygame-версии);
## музыка сцен из content/music с плавной сменой (старая тема гаснет ~0,7 с, новая вступает ~1,5 с — как
## music_update) и приглушением в рабочих сценах (полная громкость первые 45 с, потом за 12 с — в тихий фон 18 %).
## Громкости — из Settings.vol (master/music/sfx, on). Атмосферные петли (amb) pygame синтезирует кодом — пока нет.

const SFX_DIR := "res://content/sfx/"
const MUSIC_DIR := "res://content/music/"
const POOL := 8

var _sfx: Dictionary = {}
var _players: Array[AudioStreamPlayer] = []
var _next := 0
var _music: AudioStreamPlayer
var _cur_theme := ""
var _want_theme := ""
var _xf := 1.0                          # громкость перехода между темами
var _duck := 1.0
var _scene := ""
var _scene_t := 0.0
var _loud_scenes: Array = ["title", "intro", "ending", "credits"]
var _full := 45.0
var _fade := 12.0
var _bed := 0.18
var played: Array[String] = []          # последние эффекты (для тестов)


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	for b: String in ["Music", "Sfx"]:
		if AudioServer.get_bus_index(b) < 0:
			AudioServer.add_bus()
			AudioServer.set_bus_name(AudioServer.bus_count - 1, b)
			AudioServer.set_bus_send(AudioServer.bus_count - 1, "Master")
	for i in POOL:
		var p := AudioStreamPlayer.new()
		p.bus = "Sfx"
		add_child(p)
		_players.append(p)
	_music = AudioStreamPlayer.new()
	_music.bus = "Music"
	add_child(_music)
	var m: Dictionary = Content.consts.get("music", {})
	_full = float(m.get("full", _full))
	_fade = float(m.get("fade", _fade))
	_bed = float(m.get("bed", _bed))
	_loud_scenes = m.get("loud_scenes", _loud_scenes)
	var dir := DirAccess.open(SFX_DIR)
	if dir:
		for f in dir.get_files():
			var name := f.trim_suffix(".import").trim_suffix(".remap")   # в экспорте лежат .import/.remap
			if name.ends_with(".wav") and not _sfx.has(name.get_basename()):
				var s: AudioStream = load(SFX_DIR + name) as AudioStream
				if s:
					_sfx[name.get_basename()] = s
	Settings.changed.connect(func(_k: String) -> void: apply_volume())
	apply_volume()


func has_sfx(name: String) -> bool:
	return _sfx.has(name)


func sfx(name: String) -> void:
	played.append(name)
	if played.size() > 40:
		played.remove_at(0)
	if not Settings.vol.get("on", true):
		return
	var s: AudioStream = _sfx.get(name)
	if s == null:
		return
	var p := _players[_next]
	_next = (_next + 1) % POOL
	p.stream = s
	p.volume_db = linear_to_db(maxf(0.0001, float(Settings.vol["master"]) * float(Settings.vol["sfx"])))
	p.play()


## Остановить всё (выход из тестов: иначе проигрываемые звуки «текут» при закрытии).
func stop_all() -> void:
	for p in _players:
		p.stop()
		p.stream = null
	_music.stop()
	_music.stream = null
	_sfx.clear()
	_cur_theme = ""
	_want_theme = ""


func toggle_sound() -> bool:
	Settings.set_vol("on", not Settings.vol.get("on", true))
	return Settings.vol["on"]


## Сцена сменилась: тема музыки и отсчёт приглушения заново.
func scene(name: String, theme: String) -> void:
	if name != _scene:
		_scene = name
		_scene_t = 0.0
	_want_theme = theme


func _process(dt: float) -> void:
	_scene_t += dt
	dt = minf(dt, 0.1)
	if _want_theme != _cur_theme:
		if _cur_theme != "" and _xf > 0.0:
			_xf = maxf(0.0, _xf - dt / 0.7)           # старая тема гаснет
		else:
			_cur_theme = _want_theme
			_music.stop()
			var path := MUSIC_DIR + _cur_theme + ".mp3"
			if _cur_theme != "" and ResourceLoader.exists(path):
				var st := load(path) as AudioStreamMP3
				if st:
					st = st.duplicate() as AudioStreamMP3
					st.loop = true
					_music.stream = st
					_xf = 0.0
					_music.play()
	elif _xf < 1.0:
		_xf = minf(1.0, _xf + dt / 1.5)              # новая тема вступает
	var want := 1.0
	if not _scene in _loud_scenes and _scene_t >= _full:
		want = maxf(_bed, 1.0 - (_scene_t - _full) / _fade * (1.0 - _bed))
	_duck = minf(want, _duck + dt / 2.5) if want > _duck else want
	apply_volume()


func music_level() -> float:
	var v: Dictionary = Settings.vol
	return float(v["master"]) * float(v["music"]) * _duck * _xf if v.get("on", true) else 0.0


func apply_volume() -> void:
	if _music:
		var lvl := music_level()
		_music.volume_db = linear_to_db(maxf(0.0001, lvl))
		_music.stream_paused = lvl <= 0.0001 and _music.playing
