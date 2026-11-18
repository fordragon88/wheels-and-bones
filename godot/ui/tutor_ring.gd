class_name TutorRing
## Зелёная пульсирующая рамка «вот это» (обучение в первом задании, _draw_tutor_ring); без анимации — неподвижная.


static func _k(t: float) -> float:
	return 0.5 + 0.5 * UI.wsin(t * 4.5)


## Вокруг прямоугольника (плитка инструмента, строка детали).
static func draw_rect_ring(ci: CanvasItem, r: Rect2, t: float) -> void:
	var grow := int(3 + 5 * _k(t))
	var rr := r.grow(grow)
	UI.draw_round_rect(ci, rr.grow(2), Color(0, 0, 0, 0), UI.INK, 5, 16)   # тёмная подложка: видно на любом фоне
	UI.draw_round_rect(ci, rr, Color(0, 0, 0, 0), UI.GOOD, 3, 14)


## Вокруг кружка детали на коляске.
static func draw_circle_ring(ci: CanvasItem, c: Vector2, radius: float, t: float) -> void:
	var rr := radius + int(3 + 5 * _k(t)) + 2
	UI.draw_ring(ci, c, rr + 2, UI.INK, 5)
	UI.draw_ring(ci, c, rr, UI.GOOD, 3)
