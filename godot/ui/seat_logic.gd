class_name SeatLogic
## Кабинет посадки — правила (seat_eval и оценки по видам из game.py, один в один; эталон — content/seat_ref.json):
## список проверок [ключ, верно?, текст] и параметры позы для рисунка. Плюс поза уроков и вопросов зачёта
## (_seat_demo_pose, _seat_fix_pose), подпись значения ползунка (seat_val_text), строка мерок.

## Сколько верных ответов нужно для зачёта: game.py SEAT_QUIZ_PASS (game_consts.json → seat_quiz_pass).
static func quiz_pass() -> int:
	return int(Content.consts.get("seat_quiz_pass", 6))


static func sliders() -> Dictionary:
	return Content.consts.get("seat_sliders", {})


static func cases() -> Array:
	return Content.seating.get("cases", [])


## Python: round() по-банковски и формат «:.0f» — половинки к чётному.
static func fmt0(x: float) -> String:
	var r := roundf(x)
	if absf(x - floorf(x) - 0.5) < 1e-9:
		r = floorf(x) if int(floorf(x)) % 2 == 0 else ceilf(x)
	return "%d" % int(r)


static func seat_eval(case: Dictionary, cfg: Dictionary) -> Array:
	match case.get("view", ""):
		"front":
			return eval_front(case, cfg)
		"top":
			return eval_top(case, cfg)
	return eval_side(case, cfg)


## Клиент с перекосом/поворотом сбоку: по меркам посадка ровная.
@warning_ignore("integer_division")
static func side_cfg(case: Dictionary) -> Dictionary:
	var b: Dictionary = case["body"]
	return {"depth": b["thigh"] - 5, "leg": b["shank"], "back_h": int(int(case["back"][0]) + int(case["back"][1])) / 2,
		"back_a": int(int(case["angle"][0]) + int(case["angle"][1])) / 2, "tilt": 0}


static func eval_front(case: Dictionary, cfg: Dictionary) -> Array:
	var b: Dictionary = case["body"]
	var fx: Dictionary = case.get("fixed", {})
	var keys: Array = case["sliders"]
	var hip := float(b["hip"])
	var sh := float(b["shank"])
	var checks: Array = []
	var obl := 0.0
	var shift := 0.0
	if "base" in keys:
		if cfg["base"]:
			checks.append(["base", true, "Жёсткая основа: таз не проваливается"])
		else:
			checks.append(["base", false, "Гамак провисает: таз проваливается к одной стороне"])
			obl += 4
	if "seat_w" in keys:
		var w := float(cfg["seat_w"])
		if w < hip:
			checks.append(["seat_w", false, "Сиденье уже бёдер: давит на бёдра"])
		elif w > hip + 2:
			checks.append(["seat_w", false, "Сиденье шире бёдер: таз съезжает и опускается на одну сторону"])
			obl += 0.8 * (w - hip - 2)
			shift = -0.5 * (w - hip - 2)
		else:
			checks.append(["seat_w", true, "Ширина сиденья по бёдрам"])
	if "foot_l" in keys:
		var fl := float(cfg["foot_l"])
		var fr := float(cfg["foot_r"])
		for row: Array in [["foot_l", fl, "Левая подножка высоко: колено задрано", "Левая подножка низко: стопа не стоит",
				"Левая подножка по голени"], ["foot_r", fr, "Правая подножка высоко: колено задрано",
				"Правая подножка низко: стопа не стоит", "Правая подножка по голени"]]:
			var v: float = row[1]
			if v < sh - 1.5:
				checks.append([row[0], false, row[2]])
			elif v > sh + 1.5:
				checks.append([row[0], false, row[3]])
			else:
				checks.append([row[0], true, row[4]])
		if absf(fl - fr) > 1:
			checks.append(["feet", false, "Подножки на разной высоте: таз перекашивается"])
			obl += 1.2 * (fl - fr)
	var pose := {"shift": shift}
	var status: String
	if not fx.is_empty():
		var high := float(fx["high"])
		var gap := float(fx["gap"])
		obl = float(fx["obl"]) * high
		var build := float(cfg.get("build", 0))
		var filled := build * high
		if build == 0:
			checks.append(["build", false, "Под высокой стороной зазор: вся нагрузка на нижнюю седалищную кость"])
		elif filled < 0:
			checks.append(["build", false, "Подкладка под НИЖНЕЙ стороной: неисправимый перекос так не выпрямить — боль и давление"])
		elif filled < gap - 0.5:
			checks.append(["build", false, "Зазор под высокой стороной заполнен не до конца"])
		elif filled > gap + 0.5:
			checks.append(["build", false, "Подкладка выше зазора: теперь перегружена высокая сторона"])
		else:
			checks.append(["build", true, "Высокая сторона заполнена: давление ровное, голова ровнее"])
		var ok_b := gap - 0.5 <= filled and filled <= gap + 0.5
		pose["gap_cm"] = maxf(0.0, gap - maxf(0, filled))
		pose["gap_side"] = high
		pose["lean"] = obl * (0.15 if ok_b else (0.9 if filled < 0 else 0.6))
		var low_key := "press_l" if high > 0 else "press_r"
		var high_key := "press_r" if high > 0 else "press_l"
		pose[low_key] = filled < gap - 0.5
		pose[high_key] = filled > gap + 0.5
		status = "Перекос неисправимый: учитываем, не выпрямляем"
	else:
		pose["lean"] = obl * 0.6
		pose["press_l"] = obl > 2
		pose["press_r"] = obl < -2
		status = "Таз ровный" if absf(obl) < 1 else "Перекос таза: %s°" % fmt0(absf(obl))
	var ok := checks.all(func(c: Array) -> bool: return c[1])
	pose["obl"] = clampf(obl, -14.0, 14.0)
	pose["ok"] = ok
	pose["status"] = status
	return [checks, pose]


static func eval_top(case: Dictionary, cfg: Dictionary) -> Array:
	var b: Dictionary = case["body"]
	var fx: Dictionary = case.get("fixed", {})
	var hip := float(b["hip"])
	var rot := float(fx.get("rot", 0.0))
	var checks: Array = []
	var shift := 0.0
	var w := float(cfg["seat_w"])
	if w < hip:
		checks.append(["seat_w", false, "Сиденье уже бёдер: таз разворачивается, чтобы поместиться"])
		rot += 1.5 * (hip - w) * (-1.0 if rot < 0 else 1.0)
	elif w > hip + 2:
		checks.append(["seat_w", false, "Сиденье шире бёдер: таз съезжает вбок"])
		shift = 0.5 * (w - hip - 2)
	else:
		checks.append(["seat_w", true, "Ширина сиденья по бёдрам"])
	var press := {}
	for row: Array in [["depth_l", -1, float(b.get("thigh_l", b["thigh"])), "Слева край подушки давит под колено",
			"Слева бедру не хватает опоры", "Глубина слева по бедру"], ["depth_r", 1, float(b.get("thigh_r", b["thigh"])),
			"Справа край подушки давит под колено", "Справа бедру не хватает опоры", "Глубина справа по бедру"]]:
		var tgt: float = row[2] - 5
		var d := float(cfg[row[0]])
		press[row[1]] = d > tgt + 2
		if d > tgt + 2:
			checks.append([row[0], false, row[3]])
		elif d < tgt - 3:
			checks.append([row[0], false, row[4]])
		else:
			checks.append([row[0], true, row[5]])
	var ok := checks.all(func(c: Array) -> bool: return c[1])
	var status := "Поворот учли: глубина своя для каждой ноги" if ok else (
		"Таз развёрнут сильнее: сиденье узкое" if w < hip else (
		"Сиденье широкое: таз съезжает вбок" if w > hip + 2 else "Поворот таза: подстрой сиденье под ноги"))
	return [checks, {"rot": clampf(rot, -16.0, 16.0), "shift": shift, "ok": ok, "status": status, "knee_press": press}]


static func eval_side(case: Dictionary, cfg: Dictionary) -> Array:
	var b: Dictionary = case["body"]
	var tgt_depth := float(b["thigh"]) - 5
	var tgt_leg := float(b["shank"])
	var d := float(cfg["depth"])
	var lg := float(cfg["leg"])
	var bh := float(cfg["back_h"])
	var ba := float(cfg["back_a"])
	var tl := float(cfg.get("tilt", 0))
	var lo_b := float(case["back"][0])
	var hi_b := float(case["back"][1])
	var lo_a := float(case["angle"][0])
	var hi_a := float(case["angle"][1])
	var plate := float(case["seat_h"]) - lg - 1
	var checks: Array = []
	if d > tgt_depth + 2:
		checks.append(["depth", false, "Сиденье глубже нормы: край давит под колени, тело сползает"])
	elif d < tgt_depth - 3:
		checks.append(["depth", false, "Сиденье коротко: бёдра без опоры, давление на седалищные бугры"])
	else:
		checks.append(["depth", true, "Глубина сиденья по мерке"])
	if lg < tgt_leg - 1.5:
		checks.append(["leg", false, "Подножка высоко: колени выше бёдер, давление на бугры и крестец"])
	elif lg > tgt_leg + 1.5:
		checks.append(["leg", false, "Подножка низко: стопы не стоят, тело сползает к краю"])
	else:
		checks.append(["leg", true, "Стопы стоят на подножке, бедро лежит на сиденье"])
	if plate < 5:
		checks.append(["floor", false, "До пола %s см: подножка цепляет пороги (нужно ≥ 5 см)" % fmt0(maxf(0, plate))])
	if bh < lo_b:
		checks.append(["back_h", false, "Спинка низко: корпусу не на что опереться"])
	elif bh > hi_b:
		checks.append(["back_h", false, "Спинка выше, чем в карте терапевта"
			+ (": мешает лопаткам и толчку" if case["kind"] == "manual" and not case.get("tilt") else "")])
	else:
		checks.append(["back_h", true, "Высота спинки по карте"])
	if ba < lo_a:
		checks.append(["back_a", false, "Спинка слишком прямая: корпус «стекает» вниз"])
	elif ba > hi_a:
		checks.append(["back_a", false, "Спинка слишком откинута" + (" без наклона сиденья: сдвиг тканей" if tl < 20 else "")])
	else:
		checks.append(["back_a", true, "Угол спинки по карте"])
	if case.get("tilt"):
		var need := float(case["tilt"])
		checks.append(["tilt", tl >= need, ("Позиция разгрузки: наклон ≥ %s°" % _num(case["tilt"])) if tl >= need
			else "Нет разгрузки: наклон %s° — нужно не меньше %s°" % [_num(cfg.get("tilt", 0)), _num(case["tilt"])]])
	var deep := maxf(0.0, d - tgt_depth - 2)
	var high := maxf(0.0, tgt_leg - 1.5 - lg)
	var low := maxf(0.0, lg - tgt_leg - 1.5)
	var p := 3.0 * deep + 2.5 * high + 2.0 * low + 2.5 * maxf(0, lo_b - bh) + 1.5 * maxf(0, lo_a - ba)
	p += 0.8 * maxf(0, ba - hi_a) if tl < 20 else 0.0
	var slide := 0.8 * deep + 0.8 * low + (0.25 * maxf(0, ba - hi_a) if tl < 20 else 0.0)
	return [checks, {"p": minf(26.0, p), "slide": minf(10.0, slide), "deep": deep > 0, "short": d < tgt_depth - 3,
		"knee_up": high > 0, "dangle": low > 0}]


## Число как в Python f"{x}": целое без «.0».
static func _num(x: Variant) -> String:
	var f := float(x)
	return str(int(f)) if f == floorf(f) else str(f)


## Мерки клиента одной строкой (_seat_measure_text; уже переведённая).
static func measure_text(case: Dictionary) -> String:
	var b: Dictionary = case["body"]
	if case.get("view") == "top":
		return Loc.t("Мерки: бедро слева %s см · справа %s см · ширина бёдер %s см · голень %s см"
			% [_num(b["thigh_l"]), _num(b["thigh_r"]), _num(b["hip"]), _num(b["shank"])])
	if case.get("view") == "front":
		return Loc.t("Мерки: ширина бёдер %s см · голень %s см · бедро %s см" % [_num(b["hip"]), _num(b["shank"]), _num(b["thigh"])])
	var cm := Loc.t("см")
	return "%s: %s %s %s · %s %s %s · %s %s %s · %s %s %s" % [Loc.t("Мерки"), Loc.t("бедро"), _num(b["thigh"]), cm,
		Loc.t("голень"), _num(b["shank"]), cm, Loc.t("лопатка"), _num(b["scap"]), cm, Loc.t("плечо"), _num(b["shoulder"]), cm]


## Значение ползунка словами или числом с единицей (seat_val_text; переведённое).
static func val_text(key: String, v: Variant) -> String:
	if key == "base":
		return Loc.t("жёсткая") if v else Loc.t("гамак (провисает)")
	if key == "build":
		if int(v) == 0:
			return Loc.t("без подкладки")
		return Loc.t(("под левую: %d см" if int(v) < 0 else "под правую: %d см") % absi(int(v)))
	var unit := Loc.t(str(sliders()[key][1]))
	return ("%s%s" % [_num(v), unit]) if unit == "°" else ("%s %s" % [_num(v), unit]).strip_edges()


## Поза к уроку/вопросу: типовая коляска первого случая и поза по описанию; force_good — эталонная (_seat_demo_pose).
static func demo_pose(spec: Dictionary, force_good: bool = false) -> Array:
	var case: Dictionary = (cases()[0] as Dictionary).duplicate(true)
	var b: Dictionary = case["body"]
	var cfg := {"depth": float(b["thigh"]) - 5, "leg": float(b["shank"]), "back_h": 45.0, "back_a": 100.0,
		"tilt": float(spec.get("tilt", 0))}
	if not force_good:
		if spec.get("deep"):
			cfg["depth"] += 7
		if spec.get("knee_up"):
			cfg["leg"] -= 8
		if spec.get("dangle"):
			cfg["leg"] += 7
			case["seat_h"] = maxf(float(case["seat_h"]), cfg["leg"] + 4)
	case["back"] = [40, 50]
	case["angle"] = [95, 105]
	case["kind"] = "power" if spec.get("tilt") else "manual"
	var pose: Dictionary = eval_side(case, cfg)[1]
	if spec.get("measure"):
		pose["measure"] = true
	if not force_good:
		if spec.has("p"):
			pose["p"] = float(spec["p"])
		if spec.has("slide"):
			pose["slide"] = float(spec["slide"])
	return [case, cfg, pose]


## Кадр перехода ошибочная поза → норма (_seat_fix_pose): числа плавно, флаги — до середины как у ошибки.
static func fix_pose(spec: Dictionary, t: float) -> Array:
	var bad := demo_pose(spec)
	if t <= 0.0:
		return bad
	var good := demo_pose(spec, true)
	if t >= 1.0:
		return good
	var case: Dictionary = (good[0] as Dictionary).duplicate()
	case["seat_h"] = lerpf(float(bad[0]["seat_h"]), float(good[0]["seat_h"]), t)
	var cfg := {}
	for k: String in good[1]:
		cfg[k] = lerpf(float(bad[1][k]), float(good[1][k]), t) if bad[1].has(k) else good[1][k]
	var pose: Dictionary = (bad[2] if t < 0.5 else good[2]).duplicate()
	for k: String in ["p", "slide"]:
		pose[k] = lerpf(float(bad[2].get(k, 0)), float(good[2].get(k, 0)), t)
	return [case, cfg, pose]


## Как показать исправление после ответа (_seat_fix_kind): "side", "wedge"/"pads" (спереди) или "".
static func fix_kind(q: Dictionary) -> String:
	var qp: Variant = q.get("pose")
	if not qp is Dictionary or (qp as Dictionary).is_empty() or qp.get("tilt"):
		return ""
	if qp.get("front"):
		return str(q.get("fix_front", ""))
	return "side"
