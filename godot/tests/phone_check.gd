extends Node
## Телефонный режим (UI.phone(), 21.11): замер целей для пальца. Состояния — те же, что у сверки порядка обхода
## (content/kb_order_ref.json, ставит tests/shots.gd stage()). Цели — видимые включённые кнопки активного окна
## (A11y.active_root: окно поверх экрана или сам экран; у окон внутри экрана — ещё значки шапки), ползунки и
## кружки деталей (зона попадания пальца r + 16). Для каждой — меньшая сторона; итог «целей мельче 56: N;
## пересечений: M; зазор < 8: K». Исключения (осознанно мельче 56 или вплотную) — EXCEPT с причиной.
##   … -s res://tests/selftest.gd -- --test --only phone-measure [--phone 0|1] [--langs ru,en]  → tests/out/phone_targets_<0|1>.txt
##   … --only phone-ref — записать tests/phone_off_ref.json (размеры при выключенном режиме, эталон «как было»)
##   в полной самопроверке — run(): телефон на ключевых экранах (мельче 56 и пересечений — 0), выключен — как эталон.

var R: Node
var _stager: Node
static var lay_info := ""
static var lines_pc_labels := ""             # pc_repair_layout: подписи плиток (кегль и строки) — в отчёт                    # repair_layout: что сверено в последний раз (для строки отчёта)

## Осознанно мельче 56 / вплотную: «имя цели» (или «состояние:имя»; * в конце — начало имени) → причина.
const EXCEPT := {
	"Slider_*": "Кабинет посадки, примерка с 4–5 ползунками: строки ползунков и «ГОТОВО» 52 через 60 (с 56 через 64 предупреждения при 100 % мельче на 3 ступени; разрешено владельцем 21.11); при 5 ползунках (Голем, Искра) строки 48 через 56 — иначе у Искры не помещаются все «⚠» (25.11, «шероховатости»)",
	"WarnPage&Slider_*": "Кабинет посадки, примерка: блок списка «⚠» по страницам (касание — следующая) — всё место между ползунками и «ГОТОВО», вплотную к ним (появляется, только когда «⚠» не помещаются целиком)",
	"WarnPage&Check": "Кабинет посадки, примерка: блок списка «⚠» по страницам (касание — следующая) — всё место между ползунками и «ГОТОВО», вплотную к ним (появляется, только когда «⚠» не помещаются целиком)",
	"Check": "Кабинет посадки, примерка с 4–5 ползунками: строки ползунков и «ГОТОВО» 52 через 60 (с 56 через 64 предупреждения при 100 % мельче на 3 ступени; разрешено владельцем 21.11)",
	"Case_*": "решение владельца 21.11: кнопки клиентов меньше (Кабинет посадки, примерка: 153×48 через 56, зазор 8; освободившиеся 24 px — предупреждениям)",
	"Lesson_*": "решение владельца: кнопки списков меньше (Кабинет посадки, уроки: 234×48 через 56, как у клиентов, зазор 8; освободившиеся 32 px — тексту урока; 25.11)",
}

## Ключевые экраны самопроверки (телефон): то, что перестроено.
const KEY_STATES := ["title", "intro_1", "ending", "credits", "guild_open", "guild_diploma", "tech_ops", "tech_manual",
	"tech_spec", "tech_failed", "tech_ops_t_battery", "tech_ops_t_battery_q6", "tech_ops_t_pulse6",
	"tech_ops_t_q6brake",
	"seat_lessons", "seat_lesson_slump", "seat_lesson_measure", "seat_lesson_front", "seat_fit_troll", "seat_fit_golem",
	"seat_fit_dryad", "seat_fit_dryad_side", "seat_fit_owl", "seat_fit_orc", "seat_quiz_q1", "seat_quiz_wrong", "seat_quiz_pass", "scan_seat",
	"exam_ticket", "hub", "job_flat_diagnose", "job_flat_inspected", "job_joystick_inspected", "job_flat_repair",
	"result_lift", "garage", "garage_open", "mini_pump", "mini_gap", "mini_ping", "mini_meter", "settings_sound", "settings_graphics", "settings_access", "settings_game",
	"feedback_general", "feedback_dispute", "share_paste", "share_confirm", "hub_assign", "share_summary", "share_builder",
	"rep_flat_tool", "rep_flat_none", "rep_flat_tutor", "rep_dracul_speed_note", "rep_aeroz_lock_tool", "rep_aeroz_lock_note",
	"rep_cross6_back_note", "rep_f5_charge_tool"]          # ремонт на телефоне: плитки 86, полоса, сноска (27.11)

## Ремонт на телефоне — ещё и при тексте 125/150 % (RU и EN): плитки, полоса, сноска (27.11).
const REP_STATES := ["rep_flat_tool", "rep_flat_none", "rep_flat_tutor", "rep_dracul_speed_note", "rep_aeroz_lock_tool",
	"rep_aeroz_lock_note", "rep_cross6_back_note", "rep_f5_charge_tool", "job_flat_diagnose", "mini_pump"]


func _ensure_stager() -> void:
	if _stager == null:
		_stager = (load("res://tests/shots.gd") as GDScript).new()
		_stager.set("stage_only", true)
		add_child(_stager)


static func _label(c: Control, root: Node) -> String:
	var n := str(c.name)
	if n.begins_with("@") or n == "":
		var p := str(c.get_parent().name) if c.get_parent() else "?"
		n = "%s/%s" % [p, c.accessibility_name.left(24)]
	return n


## Цели для пальца сейчас: [{name, rect, kind}] (rect — зона попадания в px холста).
static func targets() -> Array:
	var out: Array = []
	var root: Node = A11y.active_root()
	if Nav.help != null:
		root = Nav.help
	if root == null:
		return out
	var scr: Node = Nav.current
	if root == scr and scr != null and scr.get("open_idx") is int and int(scr.get("open_idx")) >= 0 			and scr.get("_popup") is Control:           # гараж: открытая карточка закрывает экран (любой тап — закрыть)
		root = scr.get("_popup")
	var roots: Array = [root]
	if root != scr and scr != null and (root as Node).get_parent() != null and scr.is_ancestor_of(root):
		for c: Node in scr.get_children():          # окно внутри экрана (мини-игра, спека…): значки шапки нажимаются
			if c is IconButton:
				roots.append(c)
	var seen := {}
	for r0: Node in roots:
		var nodes: Array = [r0] + r0.find_children("*", "Control", true, false)
		for n: Node in nodes:
			var c := n as Control
			if c == null or seen.has(c) or not c.is_visible_in_tree() or c.mouse_filter == Control.MOUSE_FILTER_IGNORE:
				continue
			var kind := ""
			var rect := c.get_global_rect()
			if c is HotspotButton:
				var hb := c as HotspotButton
				kind = "spot"
				var rr: float = hb.r + (UI.TOUCH_SPOT_PAD if UI.touch() else 4)
				rect = Rect2(rect.get_center() - Vector2(rr, rr), Vector2(rr, rr) * 2.0)
			elif c is BaseButton:
				if (c as BaseButton).disabled:
					continue
				kind = "circle" if c is GameButton and (c as GameButton).hit_circle else "btn"
			elif A11y.is_slider(c) or str(c.name).begins_with("Slider_"):
				kind = "slider"
			elif c.has_meta("phone_target"):              # своя зона попадания (спицы, шкала…): Rect2 холста
				kind = "zone"
				var z: Variant = c.get_meta("phone_target")
				if z is Rect2:
					rect = z
			else:
				continue
			seen[c] = true
			out.append({"name": _label(c, root), "rect": rect, "kind": kind})
			if c.has_meta("phone_zones"):                 # несколько зон в одном узле (спицы мини-игры)
				for zr: Rect2 in c.get_meta("phone_zones"):
					out.append({"name": _label(c, root) + "#z", "rect": zr, "kind": "zone"})
	return out


static func _except(state: String, name: String) -> String:
	for k: String in EXCEPT:
		var key := k
		var st := ""
		if ":" in k:
			st = k.get_slice(":", 0)
			key = k.get_slice(":", 1)
		if st != "" and st != state:
			continue
		if key.ends_with("*") and name.begins_with(key.trim_suffix("*")) or key == name:
			return EXCEPT[k]
	return ""


## Разбор: мелкие, пересечения, зазор < 8 (кружки деталей между собой не считаются: палец — к ближайшему).
static func analyze(state: String, ts: Array) -> Dictionary:
	var small: Array = []
	var small_ex: Array = []
	var over: Array = []
	var close: Array = []
	for t: Dictionary in ts:
		var r: Rect2 = t["rect"]
		if minf(r.size.x, r.size.y) < UI.PHONE_MIN - 0.01:
			var why := _except(state, t["name"])
			(small_ex if why != "" else small).append(t)
	for i in ts.size():
		for j in range(i + 1, ts.size()):
			var a: Dictionary = ts[i]
			var b: Dictionary = ts[j]
			if a["kind"] == "spot" and b["kind"] == "spot":
				continue
			var ra: Rect2 = a["rect"]
			var rb: Rect2 = b["rect"]
			if a["kind"] == "circle" and b["kind"] == "circle":      # круглые зоны: по расстоянию центров
				var dc := ra.get_center().distance_to(rb.get_center())
				var rs := (minf(ra.size.x, ra.size.y) + minf(rb.size.x, rb.size.y)) / 2.0
				if dc < rs - 0.01:
					over.append([a["name"], b["name"]])
				elif dc < rs + UI.PHONE_GAP - 0.01:
					close.append([a["name"], b["name"]])
				continue
			var ex := _except(state, a["name"] + "&" + b["name"]) != "" or _except(state, b["name"] + "&" + a["name"]) != ""
			if ex:
				continue
			if ra.intersection(rb).has_area():
				over.append([a["name"], b["name"]])
			elif ra.grow(UI.PHONE_GAP / 2.0 - 0.01).intersection(rb.grow(UI.PHONE_GAP / 2.0 - 0.01)).has_area():
				close.append([a["name"], b["name"]])
	return {"small": small, "small_ex": small_ex, "over": over, "close": close}


## Телефон, обычный ремонт (27.11): кнопка рук и плитки кучек (по tile_rects(), ≥ 56, зазор в кучке 8, между кучками 16,
## подписи и заголовки помещаются), заголовки кучек и полоса над ними не пересекают и не ближе 8 к кнопке
## «СНОСКИ МАНУАЛА», строкам деталей (с книжками), колонке Барти, кружкам деталей, «+»/«−», пузырю клиента, окну
## коляски; текст шага — над коляской; открытая сноска — не на плитках, полосе, коляске и кружке своей детали.
## Возврат — список нарушений (пусто — всё на месте).
static func repair_layout(scr: Node) -> PackedStringArray:
	var bad: PackedStringArray = []
	lay_info = ""
	if scr == null or scr.get("phase") != "repair" or scr.get("tools") == null or scr.get("mini") != null:
		return bad
	var tp: ToolPanel = scr.tools
	if not tp.big():
		return bad
	var o: Vector2 = scr.get_global_transform().origin
	var obst: Array = []                                    # [имя, прямоугольник экрана]
	var nb: Control = scr.get_node_or_null("Notes")
	if nb:
		obst.append(["Notes", nb.get_global_rect()])
	for b: Control in scr._part_btns:
		obst.append([str(b.name), b.get_global_rect()])
	for zn: String in ["ZoomIn", "ZoomOut"]:
		var z: Control = scr.get_node_or_null(zn)
		if z and z.visible:
			obst.append([zn, z.get_global_rect()])
	var cr: Rect2 = scr.chair.get_global_rect()
	if scr.chair.visible:
		obst.append(["Chair", cr])
		for sp: Array in scr.chair.spots():
			var c: Vector2 = Vector2(sp[1], sp[2]) + scr.chair.get_parent().global_position
			obst.append(["Spot_" + str(sp[0]), Rect2(c - Vector2(sp[3], sp[3]), Vector2(sp[3], sp[3]) * 2.0)])
	var cb: Rect2 = scr._client_bubble.client_rect()
	if cb.has_area() and scr._client_bubble.visible:
		obst.append(["ClientBubble", Rect2(cb.position + o, cb.size)])
	var mc: Rect2 = scr._mentor.col
	if mc.has_area():
		obst.append(["MentorCol", Rect2(mc.position + o, mc.size)])
	var mine: Array = []                                    # плитки (с кнопкой рук), заголовки кучек и полоса
	var want_r := tp.tile_rects()
	var trs: Dictionary = {}
	for tid: String in tp.tiles:
		var tr: Rect2 = (tp.tiles[tid] as Control).get_global_rect()
		trs[tid] = tr
		if not want_r.has(tid) or not tr.is_equal_approx(Rect2(want_r[tid].position + o, want_r[tid].size)):
			bad.append("плитка %s не на своём месте tile_rects(): %s" % [tid, _fmt_r(tr)])
		if minf(tr.size.x, tr.size.y) < UI.PHONE_MIN - 0.01:
			bad.append("плитка %s мельче 56: %s" % [tid, _fmt_r(tr)])
		if tid != "hands" and not bool(tp.ph_label_fit(tid)[4]):
			bad.append("подпись плитки %s не помещается: %s" % [tid, str(tp.ph_label_fit(tid)[1])])
		if tid != "hands":                                  # рисунок — та же раскладка, что рисует плитку
			var fit: Array = tp.ph_icon_fit(tid)
			var u: Vector2 = ToolPanel.ph_icon_used(tid) * float(fit[0])
			if float(fit[0]) < ToolPanel.PH_ICON_MIN:
				bad.append("рисунок плитки %s мельче %d: %d" % [tid, ToolPanel.PH_ICON_MIN, fit[0]])
			if u.y > float(fit[1]) + 0.01 or u.x > ToolPanel.PH_TW - 6 + 0.01:
				bad.append("рисунок плитки %s (%d×%d) не в своём месте (%d в высоту)" % [tid, u.x, u.y, fit[1]])
			for ang: float in [7.0, -7.0, 29.0]:                 # покачивание в руке и вздрагивание после ошибки
				var kk: float = minf(1.08, tp.ph_icon_room_k(tid, float(fit[0]), ang))
				var a := deg_to_rad(absf(ang))
				if kk * (u.y * cos(a) + u.x * sin(a)) > float(fit[1]) + 0.01:
					bad.append("рисунок плитки %s при повороте %d° выходит из места" % [tid, ang])
		mine.append(["Tool_" + tid, tr.grow_individual(0, 6, 0, 0)])      # выбранная приподнята на 6
	if not bool(tp.ph_hands_fit()[4]):
		bad.append("подпись кнопки «Руки и глаза» не помещается: %s" % str(tp.ph_hands_fit()[1]))
	var gid: Dictionary = {}                                # инструмент → кучка («hands» — своя)
	for g: Array in tp.ph_groups():
		var gr: Rect2 = g[2]
		var hr := Rect2(gr.position + o, Vector2(gr.size.x, ToolPanel.PH_HEAD_H))
		mine.append(["Head_" + str(g[0]), hr])
		if str(g[1]) != "" and not bool(ToolPanel.ph_head_fit(str(g[1]), gr.size.x)[1]):
			bad.append("заголовок кучки %s шире кучки" % g[0])
		for x: String in g[3]:
			gid[x] = g[0]
			if trs.has(x) and trs[x].grow_individual(0, 6, 0, 0).intersection(hr).has_area():
				bad.append("плитка %s (поднятая) заходит на заголовок своей кучки" % x)
	var ks: Array = trs.keys()
	for i in ks.size():                                     # зазоры: в кучке ≥ 8, между кучками и до рук ≥ 16
		for j in range(i + 1, ks.size()):
			var a: Rect2 = trs[ks[i]]
			var b: Rect2 = trs[ks[j]]
			var need: float = UI.PHONE_GAP if gid.get(ks[i], "hands") == gid.get(ks[j], "hands") else 16.0
			if a.grow(need / 2.0 - 0.01).intersection(b.grow(need / 2.0 - 0.01)).has_area():
				bad.append("зазор %s ↔ %s меньше %d" % [ks[i], ks[j], need])
	for m: Array in mine:                                   # заголовки — не на плитках чужих кучек
		if str(m[0]).begins_with("Head_"):
			for tid: String in trs:
				if (trs[tid] as Rect2).grow_individual(0, 6, 0, 0).intersection(m[1]).has_area():
					bad.append("%s заходит на плитку %s" % [m[0], tid])
	var sr := tp.info_rect()
	mine.append(["Strip", Rect2(sr.position + o, sr.size)])
	for m: Array in mine:                                   # полоса — не на плитках и заголовках
		if m[0] != "Strip" and (m[1] as Rect2).intersection(mine[-1][1]).has_area():
			bad.append("полоса пересекает %s" % m[0])
	var isz: Array = tp.tiles.keys().filter(func(x: String) -> bool: return x != "hands").map(
		func(x: String) -> int: return int(tp.ph_icon_fit(x)[0]))
	lay_info = "рисунки кучек %d…%d, плиток %d, полоса %s, препятствий %d (%s), сноска %s" % [isz.min(), isz.max(),
		tp.tiles.size(), _fmt_r(sr), obst.size(),
		", ".join(obst.map(func(x: Array) -> String: return str(x[0]))), _fmt_r(tp.note_rect())]
	for m: Array in mine:
		for ob: Array in obst:
			var a: Rect2 = m[1]
			var b: Rect2 = ob[1]
			if a.intersection(b).has_area():
				bad.append("%s пересекает %s (%s / %s)" % [m[0], ob[0], _fmt_r(a), _fmt_r(b)])
			elif a.grow(UI.PHONE_GAP - 0.01).intersection(b).has_area() and not str(ob[0]).begins_with("Spot_"):
				bad.append("%s ближе 8 к %s (%s / %s)" % [m[0], ob[0], _fmt_r(a), _fmt_r(b)])
	var instr := Loc.t(scr.cur_step().get("instr", ""))
	var js: GDScript = scr.get_script()
	var sz: int = js.instr_size(instr, -1, scr.ph_instr_room())
	var end_y: float = js.INSTR_Y + js.instr_h(instr, sz) + o.y
	if scr.chair.visible and end_y > cr.position.y:
		bad.append("текст шага (низ %d) заходит на коляску (верх %d)" % [end_y, cr.position.y])
	var nr := tp.note_rect()
	if nr.has_area():
		nr.position += o
		var pid: String = tp.note_pid()
		for m: Array in mine.slice(0, mine.size() - 1) + [["Chair", cr]] + obst.filter(
				func(x: Array) -> bool: return x[0] in ["ZoomIn", "ZoomOut", "Notes", "Spot_" + pid] or str(x[0]).begins_with("Part_")):
			if nr.intersection(m[1]).has_area():
				bad.append("сноска %s пересекает %s (%s / %s)" % [pid, m[0], _fmt_r(nr), _fmt_r(m[1])])
		if nr.position.y < ToolPanel.PH_NOTE_TOP - 0.5:
			bad.append("сноска %s выше y 70: %s" % [pid, _fmt_r(nr)])
	return bad


## Компьютер, обычный ремонт (28.11): кнопка рук и плитки кучек — по tile_rects(), зазор в кучке ≥ 6, между кучками и до
## рук ≥ 14, подписи и заголовки помещаются, рисунок ≥ 40 (ph_icon_fit), заголовки не под поднятой плиткой; плитки,
## заголовки и карточка не задевают коляску (окно), кружки деталей, «+»/«−», строки деталей, колонку Барти, пузырь
## клиента, «СНОСКИ МАНУАЛА» (карточка обтекает её углом); карточка вмещает текст (pc_card) — для каждого инструмента
## (в руке и наведённого), каждой сноски задания, подсказки обучения и общей, и кегль не мельче прежней карточки
## 642×108 (pc_old_*). Возврат — нарушения.
static func pc_repair_layout(scr: Node) -> PackedStringArray:
	var bad: PackedStringArray = []
	lay_info = ""
	if scr == null or scr.get("phase") != "repair" or scr.get("tools") == null or scr.get("mini") != null:
		return bad
	var tp: ToolPanel = scr.tools
	if not tp.grouped() or UI.phone():
		return bad
	var g_ := ToolPanel.geo()
	var o: Vector2 = scr.get_global_transform().origin
	var obst: Array = []
	var nb: Control = scr.get_node_or_null("Notes")
	for b: Control in scr._part_btns:
		obst.append([str(b.name), b.get_global_rect()])
	for zn: String in ["ZoomIn", "ZoomOut"]:
		var z: Control = scr.get_node_or_null(zn)
		if z and z.visible:
			obst.append([zn, z.get_global_rect()])
	var cr: Rect2 = scr.chair.get_global_rect()
	if scr.chair.visible:
		obst.append(["Chair", cr])
		for sp: Array in scr.chair.spots():
			var c: Vector2 = Vector2(sp[1], sp[2]) + scr.chair.get_parent().global_position
			obst.append(["Spot_" + str(sp[0]), Rect2(c - Vector2(sp[3], sp[3]), Vector2(sp[3], sp[3]) * 2.0)])
	var cb: Rect2 = scr._client_bubble.client_rect()
	if cb.has_area() and scr._client_bubble.visible:
		obst.append(["ClientBubble", Rect2(cb.position + o, cb.size)])
	var mc: Rect2 = scr._mentor.col
	if mc.has_area() and not tp.pc_hides_mentor():       # карточка выросла — пузырь Барти скрыт
		obst.append(["MentorCol", Rect2(mc.position + o, mc.size)])
	var card := Rect2(tp.info_rect().position + o, tp.info_rect().size)
	var want_r := tp.tile_rects()
	var trs: Dictionary = {}
	var mine: Array = []
	for tid: String in tp.tiles:
		var tr: Rect2 = (tp.tiles[tid] as Control).get_global_rect()
		trs[tid] = tr
		if not want_r.has(tid) or not tr.is_equal_approx(Rect2(want_r[tid].position + o, want_r[tid].size)):
			bad.append("плитка %s не на своём месте tile_rects(): %s" % [tid, _fmt_r(tr)])
		if tid == "hands":
			if not bool(tp.ph_hands_fit()[4]):
				bad.append("подпись кнопки «Руки и глаза» не помещается: %s" % str(tp.ph_hands_fit()[1]))
		else:
			if not bool(tp.ph_label_fit(tid)[4]):
				bad.append("подпись плитки %s не помещается: %s" % [tid, str(tp.ph_label_fit(tid)[1])])
			var fit: Array = tp.ph_icon_fit(tid)
			if float(fit[0]) < float(g_["icon_min"]):
				bad.append("рисунок плитки %s мельче %d: %d" % [tid, g_["icon_min"], fit[0]])
			var u: Vector2 = ToolPanel.ph_icon_used(tid) * float(fit[0])
			for ang: float in [0.0, 7.0, 29.0]:
				var kk: float = minf(1.0 + float(g_["grow"]) if ang != 0.0 else 1.0, tp.ph_icon_room_k(tid, float(fit[0]), ang))
				var a := deg_to_rad(ang)
				if kk * (u.y * cos(a) + u.x * sin(a)) > float(fit[1]) + 0.01:
					bad.append("рисунок плитки %s при повороте %d° выходит из места" % [tid, ang])
		mine.append(["Tool_" + tid, tr.grow_individual(0, 6, 0, 0)])
	var gid: Dictionary = {}
	for g: Array in tp.ph_groups():
		var gr: Rect2 = g[2]
		var hr := Rect2(gr.position + o, Vector2(gr.size.x, float(g_["head_h"])))
		mine.append(["Head_" + str(g[0]), hr])
		if str(g[1]) != "" and not bool(ToolPanel.ph_head_fit(str(g[1]), gr.size.x)[1]):
			bad.append("заголовок кучки %s не помещается" % g[0])
		for x: String in g[3]:
			gid[x] = g[0]
	var ks: Array = trs.keys()
	for i in ks.size():
		for j in range(i + 1, ks.size()):
			var a: Rect2 = trs[ks[i]]
			var b: Rect2 = trs[ks[j]]
			var need: float = float(g_["gin"]) if gid.get(ks[i], "hands") == gid.get(ks[j], "hands") else float(g_["ggrp"])
			if a.grow(need / 2.0 - 0.01).intersection(b.grow(need / 2.0 - 0.01)).has_area():
				bad.append("зазор %s ↔ %s меньше %d" % [ks[i], ks[j], need])
	for m: Array in mine:
		if str(m[0]).begins_with("Head_"):
			for tid: String in trs:
				if (trs[tid] as Rect2).grow_individual(0, 6, 0, 0).intersection(m[1]).has_area():
					bad.append("%s заходит на плитку %s" % [m[0], tid])
	mine.append(["Card", card])
	if nb:
		obst.append(["Notes", nb.get_global_rect()])
	for m: Array in mine:
		for ob: Array in obst:
			if (m[1] as Rect2).intersection(ob[1]).has_area():
				if m[0] == "Card" and ob[0] == "Notes":       # кнопка — в вырезе карточки: текст её обтекает
					var cn: Vector2 = tp.pc_corner() + card.position
					if tp.pc_corner() == Vector2.ZERO or ob[1].position.x < cn.x or ob[1].position.y < cn.y:
						bad.append("карточка заходит на «СНОСКИ МАНУАЛА»")
					continue
				bad.append("%s пересекает %s (%s / %s)" % [m[0], ob[0], _fmt_r(m[1]), _fmt_r(ob[1])])
		if m[0] != "Card" and (m[1] as Rect2).intersection(card).has_area():
			bad.append("%s пересекает карточку" % m[0])
	# карточка: всё содержимое помещается и не мельче прежней карточки 642×108 (высота — по содержимому, pc_need_h)
	var job: Dictionary = scr.job
	var n_tool := 0
	var grown := 0
	var whats: Array = [["hint"]]
	for tid: String in Content.tools:
		for in_hand: bool in [true, false]:
			whats.append(["tool", tid, in_hand])
	for pid: String in Content.manual_notes.get(job["id"], {}):
		whats.append(["note", pid])
	if tp.job_screen.tutor_step().size() > 0:
		whats.append(["tutor"])
	for w: Array in whats:
		var hh: float = tp.pc_need_h(w)
		var d: Dictionary = tp.pc_card_lay(w, hh)
		n_tool += 1
		if hh > ToolPanel.PC_CARD.size.y + 0.5:
			grown += 1
		if not bool(d["ok"]) or not bool(d["ge_old"]):
			bad.append("карточка: %s — %s (высота %d из %d)" % [str(w), str(d), hh, tp.pc_max_h()])
		var top: float = ToolPanel.PC_CARD.end.y - hh + o.y
		if hh > ToolPanel.PC_CARD.size.y + 0.5 and top < mc.position.y + o.y - 0.5 and mc.has_area():
			bad.append("карточка %s выше колонки Барти" % str(w))
	var labs: PackedStringArray = []                       # подписи: кегль и строки («-» на конце — перенос)
	for tid: String in tp.tiles:
		if tid != "hands":
			var lf: Array = tp.ph_label_fit(tid)
			var cut := ""
			for ln: String in lf[1]:
				if ln.ends_with("-"):                          # перенос: ширина слова целиком кеглем 9 и место
					var word: String = (ToolPanel.PH_LABEL[tid][1 if Loc.code == "en" else 0] as String).replace("|", "")
					for wd: String in word.split(" "):
						if wd.begins_with(ln.trim_suffix("-")):
							cut = " (целиком кеглем 9 — %.1f из %.1f)" % [UI.px_width(wd, 9, true), ToolPanel.geo()["tw"] - 6]
			labs.append("%s %d %s%s" % [tid, lf[0], "/".join(lf[1]), cut])
	lines_pc_labels = ", ".join(labs)
	lay_info = "ПК: плиток %d, рисунки %d…%d, карточка %s, вариантов карточки %d (выше 156 — %d), препятствий %d" % [
		tp.tiles.size(), tp.tiles.keys().filter(func(x: String) -> bool: return x != "hands").map(
		func(x: String) -> int: return int(tp.ph_icon_fit(x)[0])).min(), tp.tiles.keys().filter(
		func(x: String) -> bool: return x != "hands").map(func(x: String) -> int: return int(tp.ph_icon_fit(x)[0])).max(),
		_fmt_r(card), n_tool, grown, obst.size()]
	return bad


## Значок «без звука» (28.11, отзыв с iPhone: лежал на флажке): при выключенном звуке его прямоугольник
## (IconButton.mute_rect) не пересекает ни одну кнопку шапки (верх 56) и текст названия/бренда шапки
## (TopBar.text_rects) — на всех ключевых экранах, RU/EN, обычный вид и телефон. Возврат: [проверено, нарушения].
func mute_check(runner: Node) -> Array:
	R = runner
	_ensure_stager()
	var t0: int = UI._touch
	var p0: int = UI._phone
	var vol0: Dictionary = Settings.vol.duplicate()
	var lang0 := Loc.code
	var n := 0
	var bad: PackedStringArray = []
	Engine.time_scale = 25.0
	for ph: bool in [false, true]:
		UI._touch = 1 if ph else 0
		UI.set_phone(ph)
		for lang: String in ["ru", "en"]:
			SaveGame.reset()
			for name: String in ["title"] + KEY_STATES:
				SaveGame.tutorial_skipped = true
				Settings.lang = lang
				Loc.code = lang
				var sname: String = "title_en" if lang == "en" and name == "title" else name
				await _stager.stage(sname)
				Settings.lang = lang
				Loc.code = lang
				Settings.vol["on"] = false
				Settings.changed.emit("vol")
				await R._frames(2)
				var scr: Node = Nav.current
				var gear: IconButton = null
				for c: Node in scr.find_children("Gear", "IconButton", true, false):
					gear = c
				if gear == null or not gear.is_visible_in_tree():
					_stager.unstage(sname)
					continue
				n += 1
				var mr: Rect2 = gear.mute_rect()
				mr.position += (gear.get_parent() as CanvasItem).get_global_transform().origin
				for c: Node in scr.find_children("*", "BaseButton", true, false):
					var b := c as Control
					if b == gear or not b.is_visible_in_tree() or (b as BaseButton).disabled:
						continue
					var br := b.get_global_rect()
					if br.position.y < 56 and br.intersects(mr):
						bad.append("%s %s %s: значок «без звука» %s на кнопке %s %s" % ["телефон" if ph else "ПК", lang, name,
							_fmt_r(mr), b.name, _fmt_r(br)])
				for c: Node in scr.find_children("TopBar", "TopBar", true, false):
					var tb := c as TopBar
					for tr: Rect2 in tb.text_rects:
						var g := Rect2(tr.position + tb.get_global_transform().origin, tr.size)
						if g.intersects(mr):
							bad.append("%s %s %s: значок «без звука» %s на тексте шапки %s" % ["телефон" if ph else "ПК", lang,
								name, _fmt_r(mr), _fmt_r(g)])
				_stager.unstage(sname)
	Engine.time_scale = 1.0
	if Share.dlg != null:                          # окна от состояний — закрыть (дальше идут проверки фокуса)
		Share._close_dlg()
	if Nav.settings != null:
		Nav.close_settings()
	if Nav.feedback != null:
		Nav.feedback.close()
	if Nav.help != null:
		Nav.toggle_help()
	Settings.vol = vol0
	Settings.changed.emit("vol")
	Loc.code = lang0
	Settings.lang = lang0
	UI._touch = t0
	UI._phone = p0
	Settings.changed.emit("phone")
	return [n, bad]


static func _fmt_r(r: Rect2) -> String:
	return "%d,%d %d×%d" % [roundi(r.position.x), roundi(r.position.y), roundi(r.size.x), roundi(r.size.y)]


## Замер по состояниям: строки отчёта и итог.
func measure(runner: Node, states: Array, langs: Array, on: bool) -> Dictionary:
	R = runner
	_ensure_stager()
	var t0: int = UI._touch
	var p0: int = UI._phone
	UI._touch = 1 if on else t0
	UI.set_phone(on)
	var lang0 := Loc.code
	var voices0: bool = Settings.a11y.get("voices", true)
	Settings.a11y["voices"] = false
	seed(1)
	Figure.idle_t = 1.6
	Engine.time_scale = 25.0
	if Share.dlg != null:                          # окна от прошлого замера — закрыть (эталон снят с чистого старта)
		Share._close_dlg()
	if Nav.settings != null:
		Nav.close_settings()
	if Nav.feedback != null:
		Nav.feedback.close()
	if Nav.help != null:
		Nav.toggle_help()
	await R._frames(2)
	var lines: PackedStringArray = []
	var per: Dictionary = {}
	var tot := {"n": 0, "small": 0, "small_ex": 0, "over": 0, "close": 0, "layout": 0}
	var lay: Dictionary = {}                     # телефон, ремонт: нарушения раскладки плиток/полосы/сноски
	var rects: Dictionary = {}
	for lang: String in langs:
		SaveGame.reset()
		for name: String in states:
			if lang == "ru" and name == "title_en":
				continue
			SaveGame.tutorial_skipped = true
			Settings.lang = lang
			Loc.code = lang
			var sname: String = "title_en" if lang == "en" and name == "title" else name
			await _stager.stage(sname)
			Settings.lang = lang
			Loc.code = lang
			await R._frames(2)
			var ts := targets()
			var an := analyze(name, ts)
			var key := "%s %s" % [lang, name]
			per[key] = {"n": ts.size(), "small": an["small"].size(), "small_ex": an["small_ex"].size(),
				"over": an["over"].size(), "close": an["close"].size()}
			for k: String in ["small", "small_ex", "over", "close"]:
				tot[k] += per[key][k]
			tot["n"] += ts.size()
			var rr: Array = []
			for t: Dictionary in ts:
				var r: Rect2 = t["rect"]
				rr.append([t["name"], roundi(r.position.x), roundi(r.position.y), roundi(r.size.x), roundi(r.size.y)])
			rects[key] = rr
			lines.append("== %s: целей %d, мельче 56: %d (+исключений %d), пересечений %d, зазор < 8: %d" % [key, ts.size(),
				an["small"].size(), an["small_ex"].size(), an["over"].size(), an["close"].size()])
			for t: Dictionary in ts:
				var r: Rect2 = t["rect"]
				var m := minf(r.size.x, r.size.y)
				var mark := "  "
				if m < UI.PHONE_MIN - 0.01:
					mark = "e " if _except(name, t["name"]) != "" else "! "
				lines.append("%s%-6s %-34s %-18s min %d" % [mark, t["kind"], str(t["name"]).left(34), _fmt_r(r), roundi(m)])
			for o: Array in an["over"]:
				lines.append("  X пересечение: %s ↔ %s" % o)
			for o: Array in an["close"]:
				lines.append("  ~ зазор < 8: %s ↔ %s" % o)
			if true:
				var lb := repair_layout(Nav.current) if on else pc_repair_layout(Nav.current)
				if lay_info != "":
					lines.append("  L раскладка ремонта сверена: " + lay_info)
					if not on and lines_pc_labels != "":
						lines.append("  L подписи плиток: " + lines_pc_labels)
				if not lb.is_empty():
					lay[key] = lb
					tot["layout"] += lb.size()
					for x: String in lb:
						lines.append("  L раскладка ремонта: " + x)
			_stager.unstage(sname)
	Engine.time_scale = 1.0
	Loc.code = lang0
	Settings.lang = lang0
	Settings.a11y["voices"] = voices0
	UI._touch = t0
	UI._phone = p0
	Settings.changed.emit("phone")
	return {"lines": lines, "per": per, "tot": tot, "rects": rects, "layout": lay}


static func summary(on: bool, d: Dictionary) -> String:
	var t: Dictionary = d["tot"]
	return "PHONE TARGETS (%s): состояний %d, целей %d, мельче 56: %d (исключений %d), пересечений: %d, зазор < 8: %d%s" % [
		"телефон" if on else "выкл", d["per"].size(), t["n"], t["small"], t["small_ex"], t["over"], t["close"],
		"; раскладка ремонта (рук, кучки, полоса, сноска): нарушений %d" % t["layout"] if on else ""]


static func write_out(fname: String, text: String) -> void:
	var out := ProjectSettings.globalize_path("res://tests/out")
	DirAccess.make_dir_recursive_absolute(out)
	var f := FileAccess.open(out.path_join(fname), FileAccess.WRITE)
	f.store_string(text)
	f.close()


## Самопроверка: телефон на ключевых экранах — мельче 56 (кроме исключений) и пересечений нет; выключен — размеры
## и места целей как в эталоне tests/phone_off_ref.json (записан до телефонной раскладки).
func run(runner: Node) -> String:
	R = runner
	var on := await measure(runner, KEY_STATES, ["ru"], true)
	write_out("phone_targets_1.txt", "\n".join(on["lines"]) + "\n")
	for key: String in on["per"]:
		var p: Dictionary = on["per"][key]
		if p["small"] > 0 or p["over"] > 0:
			R.err("телефон %s: мельче 56 — %d, пересечений — %d (tests/out/phone_targets_1.txt)" % [key, p["small"], p["over"]])
	for key: String in on["layout"]:
		R.err("телефон %s, раскладка ремонта: %s" % [key, "; ".join(on["layout"][key])])
	var text0: int = Settings.a11y.get("text", 0)          # ремонт при тексте 125 и 150 %, RU и EN
	var n_big := 0
	var n_lay := 0
	for tx: int in [2, 3]:
		Settings.a11y["text"] = tx
		UI.clear_font_cache()
		var bg := await measure(runner, REP_STATES, ["ru", "en"], true)
		write_out("phone_targets_1_text%d.txt" % tx, "
".join(bg["lines"]) + "
")
		n_big += bg["per"].size()
		n_lay += int(bg["tot"]["layout"])
		for key: String in bg["per"]:
			var p: Dictionary = bg["per"][key]
			if p["small"] > 0 or p["over"] > 0:
				R.err("телефон, текст %d %%, %s: мельче 56 — %d, пересечений — %d" % [[100, 112, 125, 150][tx], key, p["small"], p["over"]])
		for key: String in bg["layout"]:
			R.err("телефон, текст %d %%, %s, раскладка ремонта: %s" % [[100, 112, 125, 150][tx], key,
				"; ".join(bg["layout"][key])])
	Settings.a11y["text"] = text0
	UI.clear_font_cache()
	var ref_path := "res://tests/phone_off_ref.json"
	var n_off := 0
	var n_diff := 0
	if not FileAccess.file_exists(ref_path):
		R.err("нет tests/phone_off_ref.json (… --only phone-ref)")
	else:
		var ref: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(ref_path))
		var states: Array = []
		for key: String in ref:
			if key.begins_with("ru "):
				states.append(key.substr(3))
		var off := await measure(runner, states, ["ru"], false)
		for key: String in ref:
			if not off["rects"].has(key):
				continue
			n_off += 1
			if _norm(off["rects"][key]) != _norm(ref[key]):
				n_diff += 1
				R.err("телефон выключен, %s: цели не как были\n  было  %s\n  стало %s" % [key, JSON.stringify(ref[key]),
					JSON.stringify(off["rects"][key])])
	var n_pc := 0                                          # компьютер (28.11): ремонт с кучками при 100/125/150 %, RU и EN
	var n_pc_lay := 0
	for tx: int in [0, 2, 3]:
		Settings.a11y["text"] = tx
		UI.clear_font_cache()
		var pc := await measure(runner, REP_STATES, ["ru", "en"], false)
		write_out("pc_repair_text%d.txt" % tx, "
".join(pc["lines"]) + "
")
		n_pc += pc["per"].size()
		n_pc_lay += int(pc["tot"]["layout"])
		for key: String in pc["layout"]:
			R.err("компьютер, текст %d %%, %s, раскладка ремонта: %s" % [[100, 112, 125, 150][tx], key,
				"; ".join(pc["layout"][key])])
	Settings.a11y["text"] = text0
	UI.clear_font_cache()
	return summary(true, on) + "; ремонт при тексте 125/150 %%: состояний %d, нарушений раскладки %d" % [n_big, n_lay] + 		"; компьютер, ремонт с кучками (100/125/150 %%, RU/EN): состояний %d, нарушений %d" % [n_pc, n_pc_lay] + 		"; выключен: %d состояний как эталон (расхождений %d)" % [n_off, n_diff]


## Кегли текста Кабинета посадки (seating.gd text_sizes): каждый урок, клиент, вопрос — при RU/EN, 100/112/125/150 %,
## обычный и «лёгкий» шрифт; у примерки — и подписи кнопок клиентов («cases»: портрет/кегль, 0 — без портрета).
## Ключ «ru 150 lesson 3» → {lesson|warn|q|say|cases: кегль}.
##   … --only seat-sizes [--phone 0|1]  → tests/out/seat_sizes_<0|1>.json
func seat_sizes(runner: Node, on: bool) -> Dictionary:
	R = runner
	var t0: int = UI._touch
	var p0: int = UI._phone
	UI._touch = 1 if on else t0
	UI._phone = 1 if on else 0                    # не set_phone: при _phone = −1 (не определён) set_phone(false) ничего
	Settings.changed.emit("phone")                # не ставил, и без окна телефон определялся сам (21.11)
	var keep := [Settings.lang, Loc.code, Settings.a11y.get("text", 0), Settings.a11y.get("font", false)]
	var instant0: bool = Settings.a11y.get("instant", false)
	Settings.a11y["instant"] = true
	var out := {}
	for lang: String in ["ru", "en"]:
		for t: int in [0, 1, 2, 3]:
			for easy: bool in [false, true]:
				Settings.lang = lang
				Loc.code = lang
				Settings.a11y["text"] = t
				Settings.a11y["font"] = easy
				UI.clear_font_cache()
				SaveGame.reset()
				SaveGame.done["flat"] = true
				Nav.go("seating")
				await R._frames(3)
				var scr: Node = Nav.current
				scr.quiz = Content.seating["quiz"].duplicate(true)
				var pre := "%s %d%s" % [lang, [100, 112, 125, 150][t], " easy" if easy else ""]
				for i in scr.lessons().size():
					scr.pick_lesson(i)
					await R._frames(2)
					if not on:                                # компьютер: значки в списке (без окна _draw кнопок нет)
						scr.desk_icon("lessons")
					var row: Dictionary = scr.text_sizes.duplicate()
					if on:                                    # телефон: подпись кнопки урока — «значок/кегль/строк» (25.11:
						var lt := "%d. %s" % [i + 1, Loc.t(scr.lessons()[i]["title"])]   # кнопки 48; 56 — для сравнения)
						for hh: float in [48.0, 56.0]:
							var f: Array = scr._row_fit(lt, 234.0, 15, false, i < 7, hh, hh < 56.0)
							row["row%d" % int(hh)] = "%d/%d/%d" % [int(f[0]), int(f[1]), (f[2] as PackedStringArray).size()]
					out["%s lesson %d" % [pre, i + 1]] = row
				scr.set_tab("fit")
				for i in scr.cases().size():
					scr.pick_case(i)
					await R._frames(2)
					if not on:
						scr.desk_icon("fit")
					out["%s fit %d" % [pre, i + 1]] = scr.text_sizes.duplicate()
				for c: Dictionary in scr.cases():             # все клиенты пройдены — подписи «✔ Имя» (длиннее)
					SaveGame.seat_done[c["id"]] = true
				scr.refresh()
				await R._frames(2)
				if not on:
					scr.desk_icon("fit")
				out["%s fit done" % pre] = scr.text_sizes.duplicate()
				SaveGame.seat_done.clear()
				scr.set_tab("quiz")
				for i in scr.quiz.size():
					scr.quiz_i = i
					scr.refresh()
					await R._frames(2)
					out["%s quiz %d" % [pre, i + 1]] = scr.text_sizes.duplicate()
	Settings.lang = keep[0]
	Loc.code = keep[1]
	Settings.a11y["text"] = keep[2]
	Settings.a11y["font"] = keep[3]
	Settings.a11y["instant"] = instant0
	UI.clear_font_cache()
	UI._touch = t0
	UI._phone = p0
	Settings.changed.emit("phone")
	return out


## Телефон, про-задания 13–16 шагов (3 столбца): кегли карточек шагов (наименьший/наибольший, строк до), пузырь и
## коляска в левой колонке — при RU/EN, 100/112/125/150 %, обычный и «лёгкий» шрифт.
##   … --only tech-sizes  → tests/out/tech_sizes_1.json; ключ «ru 150 easy t_battery» → {fs_min, fs_max, lines_max, …}
func tech_sizes(runner: Node) -> Dictionary:
	R = runner
	var t0: int = UI._touch
	var p0: int = UI._phone
	UI._touch = 1
	UI.set_phone(true)
	var keep := [Settings.lang, Loc.code, Settings.a11y.get("text", 0), Settings.a11y.get("font", false)]
	var instant0: bool = Settings.a11y.get("instant", false)
	Settings.a11y["instant"] = true
	var out := {}
	for lang: String in ["ru", "en"]:
		for t: int in [0, 1, 2, 3]:
			for easy: bool in [false, true]:
				Settings.lang = lang
				Loc.code = lang
				Settings.a11y["text"] = t
				Settings.a11y["font"] = easy
				UI.clear_font_cache()
				for jid: String in ["t_battery", "t_battery_q6", "t_pulse6", "t_q6brake"]:
					Nav.go("tech", {"job": jid})
					await R._frames(3)
					var scr: Node = Nav.current
					var fss: Array = scr.op_fs.values().map(func(v: Array) -> int: return v[0])
					var lns: Array = scr.op_fs.values().map(func(v: Array) -> int: return v[1])
					var mb: SpeechBubble = scr.get_node("MentorBubble")
					out["%s %d%s %s" % [lang, [100, 112, 125, 150][t], " easy" if easy else "", jid]] = {
						"steps": scr.step_order.size(), "fs_min": fss.min(), "fs_max": fss.max(), "lines_max": lns.max(),
						"op0": str(scr.op_rect(0)), "bubble": str(Rect2(mb.side.position, Vector2(mb.side.size.x,
						mb.side_height()))), "bubble_fs": mb.side_layout()[1], "chair": str(scr.chair.get_rect())}
	Settings.lang = keep[0]
	Loc.code = keep[1]
	Settings.a11y["text"] = keep[2]
	Settings.a11y["font"] = keep[3]
	Settings.a11y["instant"] = instant0
	UI.clear_font_cache()
	UI._touch = t0
	UI._phone = p0
	Settings.changed.emit("phone")
	return out


## Строки целей с числами целыми (JSON читает их как float).
static func _norm(rows: Array) -> String:
	var out: PackedStringArray = []
	for r: Array in rows:
		out.append("%s %d %d %d %d" % [r[0], int(r[1]), int(r[2]), int(r[3]), int(r[4])])
	return "|".join(out)
