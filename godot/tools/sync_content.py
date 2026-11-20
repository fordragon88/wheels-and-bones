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
                "cruise": G.RIDE_CRUISE, "anim_tech": dict(G.RIDE_ANIM_TECH), "anim_t": dict(G.RIDE_ANIM_T),
                "tech_stop": list(G.RIDE_TECH_STOP), "flip": sorted(getattr(G, "RIDE_FLIP", [])), "anim_fps": game.ANIM_FPS}
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
        share_ref(game)
        speech_ref(game)
        consts = {"version": game.GAME_VERSION, "width": game.WIDTH, "height": game.HEIGHT,
                  "colors": {k: list(getattr(game, k)) for k in ("BG", "PANEL", "PANEL2", "WOOD", "GHOST", "AMBER", "RUST",
                                                                 "GOOD", "BAD", "CYAN", "PURPLE", "WHITE", "GREY", "DIM")
                             if isinstance(getattr(game, k, None), tuple)},
                  "guild_req": game.GUILD_REQ, "inspect_req": game.INSPECT_REQ,
                  "exam_max_mistakes": game.EXAM_MAX_MISTAKES, "text_k": list(game.TEXT_K),
                  "anim_fps": game.ANIM_FPS, "anim_keep_ms": game.ANIM_KEEP_MS,
                  "idle": {"pad": game.IDLE_PAD, "loops": dict(game.IDLE_LOOPS),     # Бренна петлёй (blit_hero)
                           "cut_h": game.IDLE_CUT_H,      # высота нарезки idle_loop.py: где в кадре рисунок картинки
                           # Мартин петлёй экрана (SCENE_LOOPS): сцена -> {art, loop, box — бокс картинки}
                           "scenes": {sc: {"art": art, "loop": lp, "box": list(game.SCENE_LOOP_BOX[sc])}
                                      for sc, (art, lp) in game.SCENE_LOOPS.items()}},
                  "vol": dict(game.VOL),
                  "music": {"full": game.MUSIC_FULL, "fade": game.MUSIC_FADE, "bed": game.MUSIC_BED,
                            "loud_scenes": list(game.MUSIC_LOUD_SCENES)},
                  "part_center_fix": {art: {p: [list(c) for c in cs] for p, cs in fix.items()}
                                      for art, fix in game.PART_CENTER_FIX.items()},
                  "m3d": {"yaw": G.M3D_YAW, "pitch": G.M3D_PITCH, "pad": G.M3D_PAD, "wide": G.M3D_WIDE,
                          "zoom": list(G.M3D_ZOOM)},
                  "support_url": game.SUPPORT_URL,
                  "feedback_url": feedback_url(), "feedback_key": game.FEEDBACK_KEY,
                  "share": {"base_url": game.SHARE_BASE_URL, "direct_url": game.SHARE_DIRECT_URL,
                            "result_salt": game.RESULT_SALT, "max": game.SHARE_MAX, "params": list(game.SHARE_PARAMS)},
                  "feedback_reasons": list(G.FEEDBACK_REASONS), "dispute_reasons": list(G.DISPUTE_REASONS),
                  "rank_names": ["Ученик Гильдии", "Младший подмастерье", "Подмастерье", "Старший подмастерье"],
                  "tt_spin": G.TT_SPIN,
                  "seat_sliders": {k: list(v) for k, v in game.SEAT_SLIDERS.items()},
                  "seat_quiz_pass": game.SEAT_QUIZ_PASS, "seat_fix": [G.SEAT_FIX_DUR, G.SEAT_FIX_WAIT],
                  "talk_pace": {"client_idle": list(G.CLIENT_IDLE), "quip_idle": list(G.QUIP_IDLE), "gap": G.TALK_GAP},
                  "intro_slides": [list(x) for x in game.Game(headless=True).intro_slides],
                  "help_keys": [list(x) for x in G.A11Y_KEYS], "setting_help": dict(G.SETTING_HELP),
                  "tool_sound": dict(game.TOOL_SOUND), "rot_tools": sorted(game.ROT_TOOLS),
                  "read_tools": sorted(game.READ_TOOLS), "electric_parts": sorted(game.ELECTRIC_PARTS),
                  "tool_timing": {"windup": game.TOOL_WINDUP, "strike": game.TOOL_STRIKE, "hold": game.TOOL_HOLD,
                                  "ok_secs": game.TOOL_OK_SECS},
                  "leg_gag_kind": list(game.LEG_GAG_KIND), "amb_vol": {k: v[1] for k, v in game._AMB_BUILD.items()},
                  "magic": {"box": list(G.PORTRAIT_BOX), "delay": G.MAGIC_DELAY, "auto_secs": G.MAGIC_AUTO_SECS,
                            "fade": G.MAGIC_FADE, "top": G.MAGIC_TOP, "result_box": list(G.RESULT_BOX),
                            "result_hop": G.RESULT_HOP, "result_delay": G.RESULT_DELAY, "repeat": G.MAGIC_REPEAT,
                            # «живой» портрет (IDLE_LOOPS — Мартин) и стык с волшебством: кадр 0 до первого
                            # волшебства (не дольше hold), клик ждёт стыка ближе seam_wait
                            "hold": G.MAGIC_HOLD, "seam_wait": G.MAGIC_SEAM_WAIT}}
        json.dump(consts, open(os.path.join(DST, "data", "game_consts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        # живые реплики (в pygame-версии пока в коде): клиенты по заданиям, Барти, Мартин, шутки про ногу
        talk = {"client": game.CLIENT_TALK, "barty": game.BARTY_TALK, "martin": game.MARTIN_TALK,
                "leg_gags": list(game.LEG_GAGS)}
        json.dump(talk, open(os.path.join(DST, "data", "talk.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        # непечатные знаки по str.isprintable() этого Python (имя «от кого»/заголовок из ссылки, Share.clean_line):
        # диапазоны [от, до] — в том числе неназначенные (Cn), которых таблица в коде Godot не знает
        rng, st = [], None
        for c in range(0x110000):
            bad = not chr(c).isprintable()
            if bad and st is None:
                st = c
            elif not bad and st is not None:
                rng.append([st, c - 1])
                st = None
        if st is not None:
            rng.append([st, 0x10FFFF])
        json.dump({"python": sys.version.split()[0], "unicode": __import__("unicodedata").unidata_version, "ranges": rng},
                  open(os.path.join(DST, "data", "nonprintable.json"), "w", encoding="utf-8"), separators=(",", ":"))
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


def share_ref(game):
    """Эталон кодов и ссылок (docs/SHARE_LINKS.md): game.py сама выдаёт коды прогресса (P), задания (J), результата (R)
    и разбирает их; ссылки и их разбор; битые коды; итог задания (текст, строка, запрос «Отправить в таблицу»).
    Пишет content/share_ref.json — selftest Godot читает эти коды; обратное направление — tools/check_share.py."""
    G = game.Game
    out = {"progress": [], "assign": [], "result": [], "links": [], "bad": [], "head": [], "texts": {}}

    def norm_p(p):
        return None if p is None else {"done": sorted(p["done"]), "garage": [list(x) for x in p["garage"]],
                                       "exam_passed": p["exam_passed"], "seat_done": sorted(p["seat_done"]),
                                       "seat_quiz_ok": p["seat_quiz_ok"], "tutorial_skipped": p["tutorial_skipped"]}

    jobs = [j["id"] for j in game.JOBS]
    tech = [j["id"] for j in game.TECH_JOBS]
    seats = [c["id"] for c in game.SEAT_CASES]
    states = [
        ("пустой", dict(done=set(), garage=[], exam_passed=False, seat_done=set(), seat_quiz_ok=False, tutorial_skipped=False)),
        ("обучение пропущено", dict(done=set(), garage=[], exam_passed=False, seat_done=set(), seat_quiz_ok=False,
                                    tutorial_skipped=True)),
        ("несколько ремонтов", dict(done={"flat", "brake", "spokes"}, garage=[("flat", 3), ("brake", 1), ("spokes", 2)],
                                    exam_passed=False, seat_done={"seat_elf"}, seat_quiz_ok=False, tutorial_skipped=False)),
        ("полный", dict(done=set(jobs) | set(tech), garage=[(j, 1 + i % 3) for i, j in enumerate(jobs)], exam_passed=True,
                        seat_done=set(seats), seat_quiz_ok=True, tutorial_skipped=True)),
        ("Гильдия и посадка", dict(done=set(jobs[:6]) | set(tech[:3]), garage=[(j, 3) for j in jobs[:6]], exam_passed=False,
                                   seat_done=set(seats[:4]), seat_quiz_ok=True, tutorial_skipped=False)),
    ]
    for name, st in states:
        g = G(headless=True)
        for k, v in st.items():
            setattr(g, k, v)
        data = game.progress_pack(g)
        code = game.share_encode("P", data)
        kind, back = game.share_decode(code)
        out["progress"].append({"name": name, "code": code, "data": back, "unpack": norm_p(game.progress_unpack(back))})
    # распаковка с мусором: неизвестные id, повторы, звёзды вне 1..3, не-bool флаги
    junk = {"v": 1, "d": ["flat", "nope", 5, "brake"], "g": [["flat", 7], ["flat", 1], ["x", 2], ["brake", 0], "bad"],
            "e": 1, "s": ["seat_elf", "seat_x"], "q": True, "t": "yes"}
    out["progress"].append({"name": "мусор", "code": game.share_encode("P", junk), "data": junk,
                            "unpack": norm_p(game.progress_unpack(junk))})
    params = [
        {"jobs": "flat,caster,brake"},
        {"seat": "seat_troll,seat_elf"},
        {"jobs": "spokes,flat", "seat": "seat_owl", "from": "Анна Петровна", "title": "Неделя 1: колёса и посадка"},
        {"jobs": "flat, flat;caster nope", "seat": "seat_x,seat_elf", "from": "  Учитель\tМария  ", "title": "  "},
        {"jobs": "lift,joystick", "from": "Ms. O'Neil & \"Co\" <b>", "title": "Unit 2 — power chairs / тест"},
        {"jobs": "nope"},
        {"jobs": ",".join(jobs), "seat": ",".join(seats), "from": "Очень длинное имя учителя, которое явно длиннее сорока знаков",
         "title": "Т" * 100},
        {"jobs": "flat", "from": "И" * 39 + " Петров", "title": "т" * 79 + " хвост"},   # 40-й/80-й знак — пробел
    ]
    for p in params:
        a = game.assign_parse(p)
        row = {"params": p, "assign": a}
        if a is not None:
            row["code"] = game.assign_code(a)
            row["link_params"] = game.assign_params(a)
            row["link"] = game.share_link(game.assign_params(a))
            row["link_back"] = game.parse_link(row["link"])
            kind, d = game.share_decode(row["code"])
            row["data"] = d
            row["from_code"] = game.assign_parse({"jobs": d.get("j"), "seat": d.get("s"), "from": d.get("f"),
                                                  "title": d.get("ti")})
            row["head"] = game.assign_head(a["from"], a["title"])
        out["assign"].append(row)
    # итоги: без ошибок, с ошибками, частичный
    for name, a_params, rec in (
            ("без ошибок", {"jobs": "flat,caster", "from": "T"}, [("flat", 0, 61), ("caster", 0, 125)]),
            ("с ошибками", {"jobs": "brake", "seat": "seat_elf,seat_orc", "from": "Анна", "title": "Урок 3"},
             [("brake", 4, 300), ("seat_elf", 2, 61), ("seat_orc", 0, 3601)]),
            ("частичный", {"jobs": "spokes,lift,joystick", "seat": "seat_troll", "title": "Домашка"},
             [("lift", 1, 90)]),
            ("пустой", {"seat": "seat_owl"}, [])):
        g = G(headless=True)
        a = game.assign_parse(a_params)
        g.start_assignment(a)
        for k, e, s in rec:
            g.assign_record(k, e, s)
        code = game.result_code(g.assign)
        kind, d = game.share_decode(code)
        res = game.result_unpack(d)
        texts = {}
        for lang in ("ru", "en"):
            game.set_lang(lang)
            texts[lang] = {"text": game.result_text(res, code), "summary": game.result_summary(res["rows"]),
                           "head": game.assign_head(res["from"], res["title"]),
                           "labels": {k: game.share_item_label(k) for k in game.assign_items(a)}}
        game.set_lang("ru")
        out["result"].append({"name": name, "assign": {k: g.assign[k] for k in ("id", "jobs", "seat", "from", "title", "done",
                                                                                  "errors", "secs", "active", "sent")},
                              "code": code, "data": d, "unpack": {**res, "rows": [list(r) for r in res["rows"]]},
                              "texts": texts})
        if name == "с ошибками":                        # «Отправить в таблицу»: поля как у send_result
            url0 = game.FEEDBACK_URL
            game.FEEDBACK_URL = "test"
            try:
                g.send_result()
            finally:
                game.FEEDBACK_URL = url0
            p = dict(g.feedback_mem[-1])
            for k in ("time", "platform"):
                p.pop(k, None)
            out["payload"] = p
            out["payload_sent_after"] = g.assign["sent"]
    links = ["https://www.openassistivetech.org/wheels-and-bones/?jobs=flat,caster&seat=seat_elf&from=Anna&title=Week%201",
             "?jobs=flat%2Cbrake&from=%D0%90%D0%BD%D0%BD%D0%B0+%D0%9F.&title=a%26b",
             "jobs=spokes&jobs=lift#frag", "https://example.org/", "?foo=bar&load=", "?load=" + out["progress"][2]["code"],
             "?from=X&title=Y", "  ?seat=seat_owl ;  "]
    for s in links:
        p = game.parse_link(s)
        out["links"].append({"text": s, "params": p, "assign": game.assign_parse(p) if p else None})
    good = out["progress"][2]["code"]
    k_, body, crc = good.split(".")
    bad = ["", "P", "P..", good[:-1], good[:-1] + ("0" if good[-1] != "0" else "1"), "X." + body + "." + crc,
           "J." + body + "." + crc, k_ + "." + body[:-4] + "." + crc, k_ + "." + body + "!." + crc,
           game.share_encode("P", {"v": 2, "d": []}), game.share_encode("R", {"v": 1})[:-3] + "zzz",
           "R." + game.share_encode("R", {"v": 1, "a": "x"}).split(".")[1] + "." +
           game._share_crc("P", game.share_encode("R", {"v": 1, "a": "x"}).split(".")[1]),
           "P." + "A" * 9000 + ".000000", "P.eJw.000000", "J." + game._b64u(b"not zlib") + "." + game._share_crc("J", game._b64u(b"not zlib")),
           ]
    for b in bad:
        out["bad"].append({"code": b, "decoded": game.share_decode(b)})
    # пробелы, переносы и кавычки вокруг кода — игнорируются
    spaced = "«" + " ".join(good[i:i + 6] for i in range(0, len(good), 6)) + "»\n"
    out["spaced"] = {"code": spaced, "decoded": game.share_decode(spaced)}
    # разбор кода результата с битыми строками
    out["result_bad"] = [{"data": d, "unpack": game.result_unpack(d)} for d in (
        {"v": 1, "a": "x", "it": ["flat"], "r": [["flat", "2", 3.9]]}, {"v": 1, "it": ["flat"], "r": [["flat", None, 1]]},
        {"v": 1, "a": 5, "f": None, "it": ["flat", "seat_elf"], "r": []}, {"v": 1, "it": 3, "r": []})]
    for r in out["result_bad"]:
        if r["unpack"]:
            r["unpack"] = {**r["unpack"], "rows": [list(x) for x in r["unpack"]["rows"]]}
    out["base_url"] = game.SHARE_BASE_URL
    out["fmt_secs"] = {str(s): game.fmt_secs(s) for s in (0, 5, 61, 600, 3601)}
    json.dump(out, open(os.path.join(DST, "share_ref.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def speech_ref(game):
    """Эталон озвучки: что game.py говорит о каждом экране и окне (a11y_summary: где ты и что делать — полная и
    короткая), подписи пунктов для озвучки фокуса (a11y_items: группа и подпись) и фразы клавиш F1/F2/H/C, на RU и EN.
    Пишет content/speech_ref.json — selftest Godot ставит те же состояния и сравнивает. Голос не звучит: только текст."""
    G = game.Game
    out = {}
    game.A11Y["voices"] = False                           # реплики героев (случайные) — отдельно, без них
    for lang in ("ru", "en"):
        game.set_lang(lang)
        random_state = game.random.getstate()
        game.random.seed(5)
        rows = []

        def snap(name, g, items=False):
            g.kb["help"] = g.kb.get("help", False)
            g.draw(game.pygame.display.get_surface())
            row = {"name": name, "full": game.speech_clean(g.a11y_summary(full=True)),
                   "short": game.speech_clean(g.a11y_summary(full=False))}
            if items:
                row["items"] = [[it["group"], it["label"]] for it in g.a11y_items()]
            rows.append(row)

        g = G(headless=True)
        snap("title", g)
        g.scene = "intro"
        for i in range(len(g.intro_slides)):
            g.intro_idx = i
            snap(f"intro_{i}", g)
        g.open_credits()
        snap("credits", g)
        g.done = {"flat", "brake"}
        g.tutorial_skipped = True
        g.scene = "hub"
        snap("hub", g)
        g.start_job("flat", 0)
        snap("job_flat_diagnose", g, items=True)
        for pid in g.cur["parts"][:2]:
            g.inspect_part(pid)
        g.choose_diagnosis(next(i for i, o in enumerate(g.cur["diagnosis"]) if o["correct"]))
        g.toast_timer = 0
        snap("job_flat_repair", g, items=True)
        st = g.cur["steps"][0]
        g.do_action(st["tool"], st["part"])
        snap("job_flat_repair_2", g)
        for jid, kind in (("flat", "pump"), ("brake", "gap"), ("spokes", "ping"), ("lift", "meter")):
            g.start_job(jid, 0)
            for pid in g.cur["parts"][:2]:
                g.inspect_part(pid)
            g.choose_diagnosis(next(i for i, o in enumerate(g.cur["diagnosis"]) if o["correct"]))
            while g.phase == "repair" and not (g.cur["steps"][g.step_idx].get("mini") or {}).get("kind") == kind:
                g.step_skip()
            s = g.cur["steps"][g.step_idx]
            g.select_tool(s["tool"])
            g.do_action(s["tool"], s["part"])
            snap("mini_" + kind, g)
            g.mini_pending = None
        g.start_job("flat", 0)
        for pid in g.cur["parts"][:2]:
            g.inspect_part(pid)
        g.choose_diagnosis(next(i for i, o in enumerate(g.cur["diagnosis"]) if o["correct"]))
        while g.phase == "repair":
            g.step_skip()
        snap("job_flat_test", g)
        g.mistakes = 0
        g.finish_test()
        g.result_gag = game.MARTIN_TALK["good"][0]
        g.cur_stars = 3
        snap("result_flat", g)
        g.start_job("truing")
        snap("tech_truing", g, items=True)
        for key in g._manual_pages():
            g.manual_viewed.add(key)
        spec_i = next(i for i, s in enumerate(g.cur["steps"]) if s.get("spec"))
        for s in g.cur["steps"][:spec_i]:
            g.do_tech_action(s["tool"], s["id"])
            if g.mini_pending:
                g.mini_pending = None
        s = g.cur["steps"][spec_i]
        g.do_tech_action(s["tool"], s["id"])
        snap("tech_spec", g)
        g.spec_pending = None
        g.scene = "hub"
        g.cur = None
        g.open_seating()
        snap("seat_lessons", g)
        g.seatc["tab"] = "fit"
        g._seat_load_case(0)
        snap("seat_fit", g, items=True)
        g.seatc["tab"] = "quiz"
        snap("seat_quiz", g)
        g.seatc["quiz_done"] = True
        g.seatc["score"] = 6
        snap("seat_quiz_done", g)
        g.seatc = None
        g.scene = "hub"
        for tab in ("sound", "graphics", "access", "game"):
            g.show_sound = True
            g.settings_tab = tab
            snap("settings_" + tab, g, items=tab == "access")
        g.show_sound = False
        g.open_share("paste")
        snap("share_paste", g)
        g.share_ui = None
        g.open_share("builder")
        snap("share_builder", g)
        g.share_ui = None
        g.kb["help"] = True
        snap("help", g)
        g.kb["help"] = False
        g.open_feedback()
        snap("feedback_general", g)
        g.close_dispute()
        out[lang] = {"rows": rows}
        # фразы клавиш (game.py: toggle_speech, toggle_help, H, C)
        out[lang]["phrases"] = {
            "f2_off": game.speech_clean(game.tr("Озвучка выключена. F2 — включить.")),
            "f2_on": game.speech_clean(game.tr("Озвучка включена.") + " " + game.tr("F1 — справка по клавишам.")),
            "help": game.speech_clean(game.tr("Клавиши.") + " " + " ".join(f"{game.tr(k)}: {game.tr(v)}." for k, v in G.A11Y_KEYS)
                                      + " " + game.tr("Esc — закрыть справку.")),
            "help_closed": game.speech_clean(game.tr("Справка закрыта.")),
            "no_hint": game.speech_clean(game.tr("Подсказки сейчас нет.")),
            "no_client": game.speech_clean(game.tr("Клиент пока молчит.")),
        }
        game.random.setstate(random_state)
    game.set_lang("ru")
    game.A11Y["voices"] = True
    json.dump(out, open(os.path.join(DST, "speech_ref.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


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
