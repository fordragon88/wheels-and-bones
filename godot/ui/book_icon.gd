class_name BookIcon
## Маленькая открытая книжка (сноска из мануала): две страницы и корешок (_draw_book_icon).


static func draw_icon(ci: CanvasItem, c: Vector2, r: float, col: Color) -> void:
	for d: float in [-1.0, 1.0]:
		var pts := PackedVector2Array([c + Vector2(0, -r * 0.55), c + Vector2(d * r, -r * 0.8), c + Vector2(d * r, r * 0.6),
			c + Vector2(0, r * 0.85), c + Vector2(0, -r * 0.55)])
		ci.draw_polyline(pts, col, 2.0, true)
	ci.draw_line(c + Vector2(0, -r * 0.55), c + Vector2(0, r * 0.85), col, 2.0, true)
