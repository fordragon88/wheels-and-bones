"""Headless-превью анимации: непрерывно гоняет сцену (30 fps) и сохраняет кадры/GIF.
python art_tests/anim_preview.py <сцена> <секунды> [gif]"""
import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pygame
pygame.init(); pygame.display.set_mode((1280, 720))
import game
scene, secs = sys.argv[1], float(sys.argv[2])
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "anim_frames")
os.makedirs(out, exist_ok=True)
g = game.Game(headless=True)
if scene in ("job", "result"):
    g.start_job("caster", 0)
    if scene == "result":
        g.cur_stars = 3; g.result_gag = game.LEG_GAGS[0]; g.scene = "result"
elif scene == "jobpower":
    g.start_job("lift", None)
else:
    g.scene = scene
s = pygame.Surface((1280, 720))
frames, dt, t = [], 1 / 30, 0.0
while t < secs:
    g.draw(s)
    if "gif" in sys.argv and int(t * 30) % 2 == 0:
        frames.append(pygame.image.tobytes(pygame.transform.smoothscale(s, (640, 360)), "RGB"))
    g.update(dt); t += dt
g.draw(s)
pygame.image.save(s, os.path.join(out, f"{scene}_end.png"))
if frames:
    from PIL import Image
    ims = [Image.frombytes("RGB", (640, 360), f) for f in frames]
    ims[0].save(os.path.join(out, f"{scene}.gif"), save_all=True, append_images=ims[1:], duration=66, loop=0)
print(scene, "ok")
