extends Node
## Озвучка для незрячих — пока заглушка с интерфейсом pygame-версии (Speech.say(text)): экраны уже зовут её, а
## голос (экранный чтец через AccessKit Godot 4.5+ и/или DisplayServer.tts_speak) появится на шаге «Доступность».
## Сейчас только запоминает сказанное (для тестов и отладки).

var history: Array[String] = []


## Сказать фразу (interrupt — перебить текущую). Текст уже на языке игры.
func say(text: String, interrupt: bool = false) -> void:
	if text.strip_edges() == "":
		return
	if interrupt:
		history.append("…")
	history.append(text)
	if history.size() > 60:
		history = history.slice(history.size() - 60)


## Чем говорит (Speech.label() в game.py): пока озвучки нет — «недоступна».
func label() -> String:
	return "недоступна"


func stop() -> void:
	pass


func last() -> String:
	return history[-1] if not history.is_empty() else ""
