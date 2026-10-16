"""Синтез всех звуков игры + демо-WAV (эффекты подряд, затем фоновые петли)."""
import os, sys, time, wave, array
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pygame
pygame.mixer.pre_init(22050, -16, 1, 512)
pygame.init()
import game
t0 = time.perf_counter(); game.build_sounds(); t1 = time.perf_counter()
print(f"эффекты: {len(game.SOUND)} шт., синтез {t1 - t0:.2f} с")
amb = {}
for bg, (fn, vol) in game._AMB_BUILD.items():
    t = time.perf_counter(); amb[bg] = game._to_sound(game._loop_fade(fn()), vol * 0.8)
    print(f"  петля {bg}: {time.perf_counter() - t:.2f} с")
if "wav" in sys.argv:
    order = ["tick", "hover", "tool_metal", "tool_soft", "tool_elec", "inspect", "ok", "bad", "ghost",
             "star0", "star1", "star2", "ping", "dull", "hiss", "pop", "whoosh", "whoosh_out", "ratchet",
             "fail", "fanfare"]
    out = array.array("h")
    gap = array.array("h", [0] * int(22050 * 0.35))
    for name in order:
        out.extend(array.array("h", game.SOUND[name].get_raw())); out.extend(gap)
    for bg in ("bg_workshop.png", "bg_road.png", "bg_guild.png", "bg_party.png"):
        raw = array.array("h", amb[bg].get_raw())[: 22050 * 4]
        out.extend(raw); out.extend(gap)
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sound_demo.wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050); w.writeframes(out.tobytes())
    print("demo:", path, f"{len(out) / 22050:.1f} с")
