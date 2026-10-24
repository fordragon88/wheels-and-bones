"""2D-хотспоты CHAIR_HOTSPOTS (рамка 380×300) для коляски с кадрами поворота — из центров деталей index.json:
точка детали проецируется тем же ракурсом и масштабом, что рисует игра (как кружки на кадрах), и переводится в рамку
380×300 (chair_rect игры 428×338 → ×380/428, ×300/338). Пересекающиеся кружки разводятся.
python art_tests/tt_hotspots.py chair_q6edge2.png [chair_model] [out.png]   — печатает строку для CHAIR_HOTSPOTS и
рисует проверочную картинку с кружками (по умолчанию art_tests/_hotspots_<art>.png). Так сделаны хотспоты q6edge2 (24.10)."""
import os, sys, math, json
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"; os.environ["WNB_TT"] = "1"
sys.path.insert(0, "D:/wheels_and_bones"); os.chdir("D:/wheels_and_bones")
import pygame; pygame.init(); pygame.display.set_mode((1280, 720))
import game
g = game.Game(headless=True)
g.start_job("lift")
ART = sys.argv[1]; MODEL = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].endswith(".png") else ART[6:-4]
g.cur["chair_art"] = ART; g.cur["chair_model"] = MODEL
tt = g._m3d_mesh(); assert isinstance(tt, game.Turntable)
g._m3d_state()["t0"] = -1e9
fr, zoom = g._m3d_frame(); rect = g._chair_rect()
yaw, pitch = g._chair_default_view()
spots = {}
for pid, cs in tt.centers.items():
    near = max(cs, key=lambda c: game.project_point(c, yaw, pitch, fr, zoom, tt.pivot)[1])
    (x, y), _ = game.project_point(near, yaw, pitch, fr, zoom, tt.pivot)
    spots[pid] = [round(x - rect.x), round(y - rect.y), 10]
keys = list(spots)
for _ in range(100):           # разнести перекрывающиеся кружки
    moved = False
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            ax, ay, ar = spots[a]; bx, by, br = spots[b]
            d = math.hypot(ax - bx, ay - by)
            if d < ar + br + 2:
                dx, dy = ((bx - ax) / d, (by - ay) / d) if d > 0.1 else (1, 0)
                spots[a][0] -= round(dx * 3); spots[a][1] -= round(dy * 3)
                spots[b][0] += round(dx * 3); spots[b][1] += round(dy * 3)
                moved = True
    if not moved: break
print("rect", rect, "fr", fr, "zoom", round(zoom, 3))
kx, ky = 380 / rect.w, 300 / rect.h
out = {k: (round(x * kx), round(y * ky), 9) for k, (x, y, r) in spots.items()}
print(f'CHAIR_HOTSPOTS["{MODEL}"] = ' + json.dumps(out).replace("[", "(").replace("]", ")"))
# картинка-проверка
S = pygame.Surface((rect.w, rect.h)); S.fill((40, 40, 50))
img = pygame.transform.smoothscale(pygame.image.load(os.path.join("assets", ART)).convert_alpha(), (rect.w, rect.h))
S.blit(img, (0, 0))
f = pygame.font.SysFont("arial", 11)
for k, (x, y, r) in spots.items():
    pygame.draw.circle(S, (255, 200, 60), (x, y), r, 2); S.blit(f.render(k, True, (255, 255, 255)), (x + r, y - 6))
pygame.image.save(S, sys.argv[-1] if sys.argv[-1].endswith(".png") and len(sys.argv) > 2 and sys.argv[-1] != ART else os.path.join("art_tests", f"_hotspots_{ART}"))
