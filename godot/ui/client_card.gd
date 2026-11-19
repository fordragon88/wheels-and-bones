class_name ClientCard
extends GameButton
## Карточка клиента в очереди мастерской (draw_hub): крупно коляска, в кружке — портрет, имя (до 2 строк),
## поломка, «РУЧНАЯ»/«ЭЛЕКТРО», «✔ готово». Рамка янтарная, у починенных — зелёная. Нажатие — открыть задание.

var jid: String = ""


static func make_card(job_id: String, rect: Rect2) -> ClientCard:
	var c := ClientCard.new()
	c.jid = job_id
	c.position = rect.position
	c.size = rect.size
	c.name = "Card_" + job_id
	c.on_draw = c._draw_content
	c.redraw_sig = c._content_sig                # содержимое меняется только с наведением/сдвигом (их видит кнопка)
	c.refresh()
	return c


func refresh() -> void:
	var job := Content.job_by_id(jid)
	var done := SaveGame.is_done(jid)
	color = UI.GOOD if done else UI.AMBER
	active = done
	var intro: Array = Content.client_talk(jid).get("intro", [""])
	var note: String = intro[0] if not intro.is_empty() else ""
	accessibility_name = "%s. %s. %s" % [Loc.t(job["client"]), Loc.t(job["title"]),
		Loc.t("Электроколяска" if job.get("kind") == "power" else "Ручная коляска")] + \
		((". " + Loc.t("Уже починено")) if done else "") + ((". " + Loc.t(note)) if note != "" and not done else "")
	set_meta("a11y_group", "Клиенты")
	queue_redraw()


func _content_sig() -> int:
	return 0


func _draw_content(b: GameButton, r: Rect2) -> void:
	var job := Content.job_by_id(jid)
	var done := SaveGame.is_done(jid)
	var hov := b.is_hovered()
	var chair := Content.texture(job["chair_art"])
	if chair:
		b.draw_texture_rect(chair, UI.fit_rect(chair.get_size(), Rect2(r.position + Vector2(8, 6 - (3 if hov else 0)),
			Vector2(184, 145))), false)
	var ring := r.position + Vector2(6 + 29, 104 + 29)
	b.draw_circle(ring, 31, Color8(20, 18, 26), true, -1, true)
	UI.draw_ring(b, ring, 31, UI.GOOD if done else UI.AMBER, 2)
	var face := Content.texture(job["client_art"])
	if face:
		b.draw_texture_rect(face, UI.fit_rect(face.get_size(), Rect2(ring - Vector2(26, 26), Vector2(52, 52))), false)
	var client := Loc.t(job["client"])
	var title := Loc.t(job["title"])
	var avail := 250 - 26 - 162
	var nsz := 11
	var nl := 1
	var tl := 1
	for s: int in [15, 14, 13, 12, 11]:       # имя — до 2 строк, поломка — хотя бы строка (крупный текст — мельче)
		nsz = s
		nl = UI.wrap_lines(client, r.size.x - 24, s).size()
		tl = int((avail - nl * UI.line_height(s) - 2) / UI.line_height(12))
		if nl <= 2 and tl >= 1:
			break
	var ny := UI.draw_wrapped(b, client, r.position + Vector2(12, 162), r.size.x - 24, nsz, UI.WHITE, false, 0, -1, 2)
	UI.draw_wrapped(b, title, Vector2(r.position.x + 12, ny + 2), r.size.x - 24, 12, UI.GREY, false, 2, -1,
		maxi(1, mini(4 - mini(nl, 2), tl)))
	var power: bool = job.get("kind") == "power"
	UI.draw_text(b, Loc.t("ЭЛЕКТРО" if power else "РУЧНАЯ"), Vector2(r.position.x + 12, r.end.y - 22), 12,
		UI.CYAN if power else UI.AMBER, true)
	if done:
		UI.draw_text(b, Loc.t("✔ готово"), Vector2(r.end.x - 12, r.end.y - 22), 13, UI.GOOD, false, 2)
