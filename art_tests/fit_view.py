"""Насколько 3D-модель совпадает с артом коляски.
python art_tests/fit_view.py <model> [<model> ...]   (model: basic, elf, ..., aeroz, f5 ...)
Ищет ракурс (yaw, pitch), в котором силуэт 3D лучше всего совпадает с силуэтом арта assets/chair_<model>.png,
печатает IoU силуэтов и сохраняет art_tests/fit/<model>.png: арт | 3D в этом ракурсе | наложение
(зелёный — совпало, красный — есть только на арте, синий — есть только в 3D). Цель: IoU >= 0.75."""
import os, sys, json, math
os.environ["SDL_VIDEODRIVER"] = "dummy"
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
import numpy as np
import pygame
pygame.init(); pygame.display.set_mode((8, 8))
import game
N = 200


def norm_mask(m):
    ys, xs = np.nonzero(m)
    if len(xs) == 0:
        return np.zeros((N, N), bool), None
    crop = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = crop.shape
    k = (N - 8) / max(w, h)
    surf = pygame.Surface((w, h)); pygame.surfarray.blit_array(surf, (crop.T * 255).astype(np.uint8)[..., None].repeat(3, 2))
    sm = pygame.transform.smoothscale(surf, (max(1, int(w * k)), max(1, int(h * k))))
    out = np.zeros((N, N), bool)
    arr = pygame.surfarray.array3d(sm)[..., 0].T > 127
    oy, ox = (N - arr.shape[0]) // 2, (N - arr.shape[1]) // 2
    out[oy:oy + arr.shape[0], ox:ox + arr.shape[1]] = arr
    return out, (w, h)


def art_mask(model):
    img = pygame.image.load(os.path.join(ROOT, "assets", f"chair_{model}.png")).convert_alpha()
    a = pygame.surfarray.array_alpha(img).T > 100
    return norm_mask(a)[0], img


def mesh_mask(mesh, yaw, pitch, size=240):
    s = pygame.Surface((size, size)); s.fill((0, 0, 0))
    for d, pts, col, part, fl in game.project_mesh(mesh, yaw, pitch, pygame.Rect(0, 0, size, size), 0.8, mesh.pivot):
        pygame.draw.polygon(s, (255, 255, 255), pts)
    return norm_mask(pygame.surfarray.array3d(s)[..., 0].T > 127)[0]


def iou(a, b):
    return (a & b).sum() / max(1, (a | b).sum())


def fit(model):
    mesh = game.get_ai_chair3d(f"chair_{model}.png", lod=True)
    am, art = art_mask(model)
    best = (-1, 0, 0)
    for pitch in (0.05, 0.15, 0.25, 0.35, 0.45):
        for i in range(48):
            yaw = -math.pi + i * math.pi / 24
            v = iou(am, mesh_mask(mesh, yaw, pitch))
            if v > best[0]:
                best = (v, yaw, pitch)
    v, yaw, pitch = best                                       # уточнение вокруг лучшего
    for dy in np.linspace(-0.12, 0.12, 7):
        for dp in (-0.05, 0, 0.05):
            vv = iou(am, mesh_mask(mesh, yaw + dy, max(0, pitch + dp)))
            if vv > best[0]:
                best = (vv, yaw + dy, max(0, pitch + dp))
    v, yaw, pitch = best
    mm = mesh_mask(mesh, yaw, pitch)
    os.makedirs(os.path.join(ROOT, "art_tests", "fit"), exist_ok=True)
    W = 300
    sheet = pygame.Surface((W * 3, W)); sheet.fill((34, 38, 48))
    w, h = art.get_size(); k = (W - 10) / max(w, h)
    sheet.blit(pygame.transform.smoothscale(art, (int(w * k), int(h * k))), (5, 5))
    full = game.get_ai_chair3d(f"chair_{model}.png")
    big = pygame.Surface((W * 2, W * 2)); big.fill((34, 38, 48))
    for d, pts, col, part, fl in game.project_mesh(full, yaw, pitch, pygame.Rect(0, 0, W, W), 0.8, full.pivot, ss=2):
        pygame.draw.polygon(big, col, pts)
    sheet.blit(pygame.transform.smoothscale(big, (W, W)), (W, 0))
    ov = np.zeros((N, N, 3), np.uint8)
    ov[am & mm] = (80, 200, 90); ov[am & ~mm] = (220, 70, 70); ov[~am & mm] = (70, 110, 230)
    o = pygame.surfarray.make_surface(ov.transpose(1, 0, 2))
    sheet.blit(pygame.transform.scale(o, (W - 10, W - 10)), (2 * W + 5, 5))
    f = pygame.font.SysFont("segoeui", 16, bold=True)
    sheet.blit(f.render(f"{model}: IoU {v:.2f}  yaw {yaw:.2f}  pitch {pitch:.2f}", True, (250, 230, 120)), (8, W - 24))
    pygame.image.save(sheet, os.path.join(ROOT, "art_tests", "fit", f"{model}.png"))
    return v, yaw, pitch


if __name__ == "__main__":
    res = {}
    for m in sys.argv[1:]:
        v, yaw, pitch = fit(m)
        res[m] = dict(iou=round(float(v), 3), yaw=round(float(yaw), 3), pitch=round(float(pitch), 3))
        print(f"{m:8s} IoU {v:.2f}  yaw {yaw:+.2f}  pitch {pitch:.2f}", flush=True)
    p = os.path.join(ROOT, "art_tests", "fit", "views.json")
    allv = json.load(open(p)) if os.path.exists(p) else {}
    allv.update(res); json.dump(allv, open(p, "w"), indent=1)
