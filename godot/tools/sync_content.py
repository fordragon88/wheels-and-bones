# -*- coding: utf-8 -*-
"""Перенос ресурсов игры (../assets) в проект Godot (godot/content/). Содержание правится ТОЛЬКО в assets/ — папка
content/ целиком сгенерирована и в git не хранится.

  python godot/tools/sync_content.py            # всё (кадры и петли — только изменившиеся)
  python godot/tools/sync_content.py --no-frames  # без кадров поворота и петель (быстро: данные, картинки, звуки)
  python godot/tools/sync_content.py --force      # пересобрать и кадры заново

Что делает:
  data/        копия assets/data (задания, Гильдия, посадка, мануал, инструменты, детали, титры) и lang_en.json;
               из game.py: game_consts.json (цвета, правила, громкости, PART_CENTER_FIX) и talk.json (CLIENT_TALK,
               BARTY_TALK, MARTIN_TALK, LEG_GAGS — живые реплики, в pygame-версии пока в коде)
  img/         портреты, коляски, фоны, инструменты и прочие PNG из корня assets (обычный импорт Godot)
  frames/turntable/<коляска>_NN.webp   кадры поворота: JPEG + маска .a.png → один WebP с прозрачностью
  frames/anim/<петля>/NN.webp          петли (машут, проезд, волшебство) — так же
  frames/*.json                        индексы: кружки деталей (turntable), волшебство, проезд (из game.py)
  sfx/<имя>.wav  звуки, которые pygame-версия синтезирует кодом (game.build_sounds)
  music/, fonts/ копия
  manifest.json  что и из какого коммита перенесено

Папка frames/ скрыта от редактора Godot (.gdignore): тысячи кадров не импортируются, игра читает WebP сама.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import wave

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
GODOT = os.path.dirname(HERE)
ROOT = os.path.dirname(GODOT)
SRC = os.path.join(ROOT, "assets")
DST = os.path.join(GODOT, "content")
WEBP_Q = 85                    # качество цвета кадров (исходники — JPEG 90)
ANIM_MAX_H = 400               # петли: как в браузерной сборке (build_web.shrink_anim), машущие — без уменьшения


def newer(src_files, dst):
    return not os.path.exists(dst) or any(os.path.getmtime(s) > os.path.getmtime(dst) for s in src_files)


def copy_tree(src, dst, pred=lambda rel: True):
    n = 0
    for dp, _, files in os.walk(src):
        for fn in files:
            full = os.path.join(dp, fn)
            rel = os.path.relpath(full, src)
            if not pred(rel.replace("\\", "/")):
                continue
            out = os.path.join(dst, rel)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            if newer([full], out):
                shutil.copy2(full, out)
            n += 1
    return n


def merge_frame(jpg, mask, out, max_h=None):
    """JPEG + белая маска с альфой (может быть меньшего размера) → WebP с прозрачностью."""
    rgb = Image.open(jpg).convert("RGB")
    a = Image.open(mask).convert("RGBA").split()[3]
    if a.size != rgb.size:
        a = a.resize(rgb.size, Image.LANCZOS)
    if max_h and rgb.height > max_h:
        size = (round(rgb.width * max_h / rgb.height), max_h)
        rgb, a = rgb.resize(size, Image.LANCZOS), a.resize(size, Image.LANCZOS)
    im = rgb.copy()
    im.putalpha(a)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    im.save(out, "WEBP", quality=WEBP_Q, alpha_quality=90, method=4, exact=False)


def sync_frames(force):
    made = kept = 0
    tt_src, tt_dst = os.path.join(SRC, "turntable"), os.path.join(DST, "frames", "turntable")
    os.makedirs(tt_dst, exist_ok=True)
    for fn in sorted(os.listdir(tt_src)):
        full = os.path.join(tt_src, fn)
        if fn.endswith(".json"):
            shutil.copy2(full, os.path.join(DST, "frames", "turntable_" + fn))
        elif fn.endswith(".jpg"):
            mask = full[:-4] + ".a.png"
            out = os.path.join(tt_dst, fn[:-4] + ".webp")
            if force or newer([full, mask], out):
                merge_frame(full, mask, out)
                made += 1
            else:
                kept += 1
        elif fn.endswith(".png") and not fn.endswith(".a.png"):      # старый формат кадров: готовый PNG с альфой
            out = os.path.join(tt_dst, fn[:-4] + ".webp")
            if force or newer([full], out):
                Image.open(full).convert("RGBA").save(out, "WEBP", quality=WEBP_Q, alpha_quality=90, method=4)
                made += 1
            else:
                kept += 1
    an_src, an_dst = os.path.join(SRC, "anim"), os.path.join(DST, "frames", "anim")
    loops = {}
    for name in sorted(os.listdir(an_src)):
        d = os.path.join(an_src, name)
        if not os.path.isdir(d):
            if name.endswith(".json"):
                os.makedirs(an_dst, exist_ok=True)
                shutil.copy2(d, os.path.join(DST, "frames", "anim_" + name))
            continue
        n = 0
        while os.path.exists(os.path.join(d, f"{n:02d}.jpg")) and os.path.exists(os.path.join(d, f"{n:02d}.a.png")):
            jpg, mask = os.path.join(d, f"{n:02d}.jpg"), os.path.join(d, f"{n:02d}.a.png")
            out = os.path.join(an_dst, name, f"{n:02d}.webp")
            if force or newer([jpg, mask], out):
                merge_frame(jpg, mask, out, None if name.endswith("_wave") else ANIM_MAX_H)
                made += 1
            else:
                kept += 1
            n += 1
        if n:
            loops[name] = {"n": n, "size": list(Image.open(os.path.join(an_dst, name, "00.webp")).size)}
    json.dump(loops, open(os.path.join(DST, "frames", "anim_loops.json"), "w", encoding="utf-8"), ensure_ascii=False,
              indent=1, sort_keys=True)
    open(os.path.join(DST, "frames", ".gdignore"), "w").close()
    return made, kept, len(loops)


def game_tables():
    """Таблицы, которые в pygame-версии зашиты в код: проезд героев и общие числа анимаций."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    sys.path.insert(0, ROOT)
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        import pygame
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        pygame.display.set_mode((1280, 720))
        import game
        G = game.Game
        ride = {"anim": G.RIDE_ANIM, "loop": {k: list(v) for k, v in G.RIDE_LOOP.items()},
                "scale": getattr(G, "RIDE_SCALE", {}), "aspect": getattr(G, "RIDE_ASPECT", {}),
                "secs": G.RIDE_ANIM_SECS, "secs_plain": G.RIDE_SECS, "height": G.RIDE_ANIM_H, "floor": G.RIDE_FLOOR,
                "cruise": G.RIDE_CRUISE, "flip": sorted(getattr(G, "RIDE_FLIP", [])), "anim_fps": game.ANIM_FPS}
        json.dump(ride, open(os.path.join(DST, "frames", "ride.json"), "w", encoding="utf-8"), ensure_ascii=False,
                  indent=1, sort_keys=True)
        # звуки: синтез pygame-версии → WAV 22 050 Гц моно 16 бит
        sfx = os.path.join(DST, "sfx")
        os.makedirs(sfx, exist_ok=True)
        game.build_sounds()
        n = 0
        for name, s in sorted(getattr(game, "SOUND", {}).items()):
            raw = s.get_raw()
            freq, size, chans = pygame.mixer.get_init()
            with wave.open(os.path.join(sfx, name + ".wav"), "wb") as w:
                w.setnchannels(chans)
                w.setsampwidth(abs(size) // 8)
                w.setframerate(freq)
                w.writeframes(raw)
            n += 1
        freq, size, chans = pygame.mixer.get_init()

        def wav(name, snd_obj):
            with wave.open(os.path.join(sfx, name + ".wav"), "wb") as w:
                w.setnchannels(chans)
                w.setsampwidth(abs(size) // 8)
                w.setframerate(freq)
                w.writeframes(snd_obj.get_raw())

        # фоновые петли сцен (set_ambient): amb_<фон>.wav, громкость петли уже внутри (как _to_sound(…, vol))
        for bg, (fn, vol) in game._AMB_BUILD.items():
            wav("amb_" + os.path.splitext(bg)[0], game._to_sound(game._loop_fade(fn()), vol))
            n += 1
        # тон насоса по давлению (snd_pitch): pitch_00 … pitch_20
        for step in range(21):
            wav("pitch_%02d" % step, game._to_sound(game._tone(330 * 2 ** (step / 10), 0.12, decay=0.08), 0.3))
            n += 1
        walkthrough(game)
        feedback_ref(game)
        guild_ref(game)
        seat_ref(game)
        consts = {"version": game.GAME_VERSION, "width": game.WIDTH, "height": game.HEIGHT,
                  "colors": {k: list(getattr(game, k)) for k in ("BG", "PANEL", "PANEL2", "WOOD", "GHOST", "AMBER", "RUST",
                                                                 "GOOD", "BAD", "CYAN", "PURPLE", "WHITE", "GREY", "DIM")
                             if isinstance(getattr(game, k, None), tuple)},
                  "guild_req": game.GUILD_REQ, "inspect_req": game.INSPECT_REQ,
                  "exam_max_mistakes": game.EXAM_MAX_MISTAKES, "text_k": list(game.TEXT_K),
                  "anim_fps": game.ANIM_FPS, "anim_keep_ms": game.ANIM_KEEP_MS,
                  "vol": dict(game.VOL),
                  "music": {"full": game.MUSIC_FULL, "fade": game.MUSIC_FADE, "bed": game.MUSIC_BED,
                            "loud_scenes": list(game.MUSIC_LOUD_SCENES)},
                  "part_center_fix": {art: {p: [list(c) for c in cs] for p, cs in fix.items()}
                                      for art, fix in game.PART_CENTER_FIX.items()},
                  "m3d": {"yaw": G.M3D_YAW, "pitch": G.M3D_PITCH, "pad": G.M3D_PAD, "wide": G.M3D_WIDE,
                          "zoom": list(G.M3D_ZOOM)},
                  "support_url": game.SUPPORT_URL,
                  "feedback_url": feedback_url(), "feedback_key": game.FEEDBACK_KEY,
                  "feedback_reasons": list(G.FEEDBACK_REASONS), "dispute_reasons": list(G.DISPUTE_REASONS),
                  "rank_names": ["Ученик Гильдии", "Младший подмастерье", "Подмастерье", "Старший подмастерье"],
                  "tt_spin": G.TT_SPIN,
                  "seat_sliders": {k: list(v) for k, v in game.SEAT_SLIDERS.items()},
                  "seat_quiz_pass": game.SEAT_QUIZ_PASS, "seat_fix": [G.SEAT_FIX_DUR, G.SEAT_FIX_WAIT],
                  "intro_slides": [list(x) for x in game.Game(headless=True).intro_slides],
                  "help_keys": [list(x) for x in G.A11Y_KEYS], "setting_help": dict(G.SETTING_HELP),
                  "tool_sound": dict(game.TOOL_SOUND), "rot_tools": sorted(game.ROT_TOOLS),
                  "read_tools": sorted(game.READ_TOOLS), "electric_parts": sorted(game.ELECTRIC_PARTS),
                  "tool_timing": {"windup": game.TOOL_WINDUP, "strike": game.TOOL_STRIKE, "hold": game.TOOL_HOLD,
                                  "ok_secs": game.TOOL_OK_SECS},
                  "leg_gag_kind": list(game.LEG_GAG_KIND), "amb_vol": {k: v[1] for k, v in game._AMB_BUILD.items()},
                  "magic": {"box": list(G.PORTRAIT_BOX), "delay": G.MAGIC_DELAY, "auto_secs": G.MAGIC_AUTO_SECS,
                            "fade": G.MAGIC_FADE, "top": G.MAGIC_TOP, "result_box": list(G.RESULT_BOX),
                            "result_hop": G.RESULT_HOP, "result_delay": G.RESULT_DELAY, "repeat": G.MAGIC_REPEAT}}
        json.dump(consts, open(os.path.join(DST, "data", "game_consts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        # живые реплики (в pygame-версии пока в коде): клиенты по заданиям, Барти, Мартин, шутки про ногу
        talk = {"client": game.CLIENT_TALK, "barty": game.BARTY_TALK, "martin": game.MARTIN_TALK,
                "leg_gags": list(game.LEG_GAGS)}
        json.dump(talk, open(os.path.join(DST, "data", "talk.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return n
    finally:
        os.chdir(cwd)


def feedback_url():
    """FEEDBACK_URL из исходника game.py: при импорте без окна (SDL dummy) game.py его обнуляет — тесты не шлют."""
    import re
    src = open(os.path.join(ROOT, "game.py"), encoding="utf-8").read()
    m = re.search(r'^FEEDBACK_URL = "([^"]*)"', src, re.M)
    return m.group(1) if m else ""


def walkthrough(game):
    """Эталонное прохождение pygame-версии: каждое задание мастерской и каждый вариант поломки проходится самой игрой
    (Game: осмотр двух деталей, верный диагноз, шаги do_action, мини-игры решены, тест-драйв, finish_test).
    Пишет content/walkthrough_ref.json: «id:вариант» → шаги [инструмент, деталь, мини, alt, alt_tools], звёзды, done.
    Самопроверка Godot проходит те же задания и сравнивает."""
    g = game.Game(headless=True)
    g.tutorial_skipped = True
    out = {}
    for job in game.JOBS:
        for v in range(max(1, len(job.get("variants", [])))):
            g.start_job(job["id"], v if job.get("variants") else None)
            for pid in g.cur["parts"][:2]:
                g.inspect_part(pid)
            right = next(i for i, o in enumerate(g.cur["diagnosis"]) if o["correct"])
            assert g.choose_diagnosis(right) and g.phase == "repair", job["id"]
            steps = []
            for st in list(g.cur["steps"]):
                steps.append([st["tool"], st["part"], (st.get("mini") or {}).get("kind", ""),
                              sorted(st.get("alt", ())), sorted(st.get("alt_tools", ()))])
                r = g.do_action(st["tool"], st["part"])
                if r == "mini":
                    m = g.mini_pending
                    cfg = m["cfg"]
                    if m["kind"] == "pump":
                        m["value"] = cfg["lo"]
                        g.mini_pump_done()
                    elif m["kind"] == "gap":
                        m["value"] = cfg["lo"]
                        g.mini_gap_check()
                    elif m["kind"] == "ping":
                        for i in sorted(m["dull"]):
                            g.mini_ping(i)
                    elif m["kind"] == "meter":
                        g.mini_meter(next(i for i, o in enumerate(cfg["options"]) if o[1]))
                elif r != "ok":
                    raise AssertionError(f"{job['id']}:{v}: шаг {st['tool']} → {st['part']} не принят")
            assert g.phase == "test", job["id"]
            g.start_ride()
            g.finish_test()
            out[f"{job['id']}:{v}"] = {"steps": steps, "n": len(steps), "stars": g.cur_stars,
                                       "done": job["id"] in g.done, "mistakes": g.mistakes}
    json.dump(out, open(os.path.join(DST, "walkthrough_ref.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def feedback_ref(game):
    """Эталон замечаний игроков: game.py сама собирает запрос (feedback_payload) для нескольких случаев —
    флажок ⚑ в мастерской и в гараже (EN), «Я не согласен» после неверного диагноза и после неверного хода в ремонте.
    Сети нет (в тестовом режиме FEEDBACK_URL пуст). Пишет content/feedback_ref.json без time/uid/platform."""
    out = {}

    def send(g, reason, text):
        g.dispute_ui["reason"] = reason
        g.dispute_ui["text"] = text
        g.send_dispute()
        p = game.feedback_payload(g.feedback_mem[-1])
        for k in ("time", "platform"):
            p.pop(k, None)
        return p, g.mistakes

    g = game.Game(headless=True)
    g.tutorial_skipped = True
    game.set_lang("ru")
    g.scene = "hub"
    g.open_feedback()
    out["general_hub"], _ = send(g, 1, "Проверка: карточка съехала")
    g.start_job("flat", 0)
    for pid in g.cur["parts"][:2]:
        g.inspect_part(pid)
    wrong = next(i for i, o in enumerate(g.cur["diagnosis"]) if o["text"].startswith("Погнут обод"))
    g.choose_diagnosis(wrong)
    g.open_dispute()
    out["dispute_diagnosis"], m = send(g, 0, "Мой вариант")
    out["dispute_diagnosis"]["_mistakes_after"] = m
    g.choose_diagnosis(next(i for i, o in enumerate(g.cur["diagnosis"]) if o["correct"]))
    g.select_tool("hands")
    g.do_action("hands", "brake")
    g.open_dispute()
    out["dispute_repair"], m = send(g, 2, "")
    out["dispute_repair"]["_mistakes_after"] = m
    g.do_action("pump", "valve")
    g.open_dispute()
    out["dispute_repair_tool"], m = send(g, 1, "x")
    out["dispute_repair_tool"]["_mistakes_after"] = m
    game.set_lang("en")
    g.scene = "garage"
    g.open_feedback()
    out["general_garage_en"], _ = send(g, 3, "Garage note")
    game.set_lang("ru")
    json.dump(out, open(os.path.join(DST, "feedback_ref.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def guild_ref(game):
    """Эталон Гильдии: game.py сама проходит все 6 про-заданий (порядок данных и «другой допустимый» — на каждом шаге
    последняя доступная операция), пробует каждую операцию, у которой в after есть шаг техники безопасности, раньше
    срока (провал и текст разбора), и собирает замечание из Гильдии. Пишет content/guild_ref.json."""
    out = {"jobs": {}, "fails": {}, "feedback": {}}

    def fresh(jid):
        g = game.Game(headless=True)
        g.tutorial_skipped = True
        g.start_job(jid)
        for key in g._manual_pages():
            g.open_manual(key)
        g.show_manual = False
        return g

    def run(g, order):
        for sid in order:
            st = g.step_by_id(sid)
            r = g.do_tech_action(st["tool"], sid)
            if r == "spec":
                g.choose_spec(next(i for i, o in enumerate(st["spec"]["options"]) if o[1]))
            elif r == "mini":
                m = g.mini_pending
                cfg = m["cfg"]
                if m["kind"] in ("pump", "gap"):
                    m["value"] = cfg["lo"]
                    (g.mini_pump_done if m["kind"] == "pump" else g.mini_gap_check)()
                elif m["kind"] == "ping":
                    for i in sorted(m["dull"]):
                        g.mini_ping(i)
                else:
                    g.mini_meter(next(i for i, o in enumerate(cfg["options"]) if o[1]))
            elif r != "ok":
                raise AssertionError(f"{g.cur['id']}: {sid} → {r}")
        return g

    for job in game.TECH_JOBS:
        jid = job["id"]
        order = [s["id"] for s in job["steps"]]
        g = run(fresh(jid), order)
        assert g.phase == "test", jid
        g.start_ride()
        g.finish_test()
        alt, done = [], set()                     # другой допустимый порядок: всегда последняя доступная операция
        while len(alt) < len(order):
            ok = [s["id"] for s in job["steps"] if s["id"] not in done and all(a in done for a in s["after"])]
            alt.append(ok[-1])
            done.add(ok[-1])
        g2 = run(fresh(jid), alt)
        out["jobs"][jid] = {
            "steps": [[s["id"], s["tool"], s["part"], list(s["after"]), bool(s["safety"]),
                       bool(s.get("spec")), (s.get("mini") or {}).get("kind", "")] for s in job["steps"]],
            "alt_order": alt, "alt_ok": g2.phase == "test", "stars": g.cur_stars, "done": jid in g.done}
        for st in job["steps"]:
            if any(g.step_by_id(a)["safety"] for a in st["after"]):
                g3 = fresh(jid)
                r = g3.do_tech_action(st["tool"], st["id"])
                out["fails"][f"{jid}:{st['id']}"] = {"result": r, "scene": g3.scene, "msg": g3.fail_msg}
    # замечание из Гильдии: сделан один шаг, потом неверный инструмент
    g = fresh("t_battery")
    first = game.TECH_JOBS[[j["id"] for j in game.TECH_JOBS].index("t_battery")]["steps"][0]
    g.do_tech_action(first["tool"], first["id"])
    nxt = next(s for s in g.cur["steps"] if s["id"] not in g.done_steps and all(a in g.done_steps for a in s["after"]))
    g.do_tech_action("lube", nxt["id"])
    g.open_dispute()
    g.dispute_ui["reason"] = 1
    g.dispute_ui["text"] = "Гильдия"
    g.send_dispute()
    p = game.feedback_payload(g.feedback_mem[-1])
    for k in ("time", "platform"):
        p.pop(k, None)
    p["_mistakes_after"] = g.mistakes
    p["_after_step"] = first["id"]
    p["_wrong_on"] = nxt["id"]
    out["feedback"]["dispute_tech"] = p
    json.dump(out, open(os.path.join(DST, "guild_ref.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def seat_ref(game):
    """Эталон Кабинета посадки: game.Game.seat_eval для каждого случая на сетке положений ползунков (исходное, «по
    меркам», каждый ползунок в минимум и максимум, 8 случайных с зерном 7) и поза уроков/вопросов зачёта
    (_seat_demo_pose, _seat_fix_pose). Пишет content/seat_ref.json."""
    import random as _r
    rnd = _r.Random(7)
    G = game.Game
    out = {"cases": {}, "demo": [], "sliders": {k: list(v) for k, v in game.SEAT_SLIDERS.items()}}
    for case in game.SEAT_CASES:
        keys = case.get("sliders") or ["depth", "leg", "back_h", "back_a"] + (["tilt"] if case.get("tilt") else [])
        start = dict(case["start"])
        start.setdefault("tilt", 0)
        grid = [dict(start)]
        if not case.get("view"):
            b = case["body"]
            grid.append(dict(start, depth=b["thigh"] - 5, leg=b["shank"], back_h=sum(case["back"]) // 2,
                             back_a=sum(case["angle"]) // 2, tilt=case.get("tilt", 0)))
        for k in keys:
            _, _, lo, hi = game.SEAT_SLIDERS[k]
            grid += [dict(start, **{k: lo}), dict(start, **{k: hi})]
        for _ in range(8):
            c = dict(start)
            for k in keys:
                _, _, lo, hi = game.SEAT_SLIDERS[k]
                c[k] = rnd.randint(lo, hi)
            grid.append(c)
        rows = []
        for cfg in grid:
            checks, pose = G.seat_eval(case, cfg)
            rows.append({"cfg": cfg, "checks": [list(c) for c in checks], "pose": pose})
        side = None
        if case.get("view"):
            scfg = G._seat_side_cfg(case)
            side = {"cfg": scfg, "pose": G._seat_eval_side(case, scfg)[1]}
        out["cases"][case["id"]] = {"keys": keys, "rows": rows, "side": side,
                                    "measure": G._seat_measure_text(case)}
    g = game.Game(headless=True)
    for src, items in (("lesson", game.SEAT_LESSONS), ("quiz", game.SEAT_QUIZ)):
        for i, it in enumerate(items):
            spec = it.get("pose")
            if not spec or spec.get("front"):
                continue
            rect = game.pygame.Rect(24, 176, 730, 488)
            frames = {}
            for tt in (0.0, 0.25, 0.5, 0.75, 1.0):
                case, cfg, pose = g._seat_fix_pose(rect, spec, tt)
                frames[str(tt)] = {"seat_h": case["seat_h"], "kind": case["kind"], "cfg": cfg, "pose": pose}
            out["demo"].append({"src": src, "i": i, "frames": frames})
    # замечание из Кабинета посадки: флажок ⚑ на вкладке «Примерка» (в сеть — ничего: FEEDBACK_URL пуст в тестах)
    g = game.Game(headless=True)
    g.tutorial_skipped = True
    game.set_lang("ru")
    g.open_seating()
    g.seatc["tab"] = "fit"
    g.open_feedback()
    g.dispute_ui["reason"] = 2
    g.dispute_ui["text"] = "Посадка"
    g.send_dispute()
    p = game.feedback_payload(g.feedback_mem[-1])
    for k in ("time", "platform"):
        p.pop(k, None)
    out["feedback"] = p
    json.dump(out, open(os.path.join(DST, "seat_ref.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-frames", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    os.makedirs(DST, exist_ok=True)
    out = {}
    out["data"] = copy_tree(os.path.join(SRC, "data"), os.path.join(DST, "data"), lambda r: r.endswith(".json"))
    shutil.copy2(os.path.join(SRC, "lang_en.json"), os.path.join(DST, "data", "lang_en.json"))
    out["img"] = copy_tree(SRC, os.path.join(DST, "img"), lambda r: "/" not in r and r.endswith(".png"))
    out["music"] = copy_tree(os.path.join(SRC, "music"), os.path.join(DST, "music"))
    out["fonts"] = copy_tree(os.path.join(SRC, "fonts"), os.path.join(DST, "fonts"), lambda r: r.endswith(".ttf"))
    os.makedirs(os.path.join(DST, "frames"), exist_ok=True)
    out["sfx"] = game_tables()
    if not args.no_frames:
        made, kept, loops = sync_frames(args.force)
        out["frames_made"], out["frames_kept"], out["loops"] = made, kept, loops
    try:
        out["commit"] = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    except Exception:
        out["commit"] = "?"
    json.dump(out, open(os.path.join(DST, "manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("content:", json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
