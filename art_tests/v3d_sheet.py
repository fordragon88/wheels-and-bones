"""Лист 3D-моделей всех заданий (как в режиме осмотра): python art_tests/v3d_sheet.py [out.png]"""
import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pygame
pygame.init(); pygame.display.set_mode((8, 8))
import game

out = sys.argv[1] if len(sys.argv) > 1 else "art_tests/_v3d_all.png"
CW, CH, SS = 420, 340, 2
jobs = [game.resolve_job(b) for b in game.ALL_JOBS]
sheet = pygame.Surface((CW * 2 * 3, CH * 3)); sheet.fill((20, 26, 36))
font = pygame.font.SysFont("segoeui", 18, bold=True)
jobs = [j for j in jobs if game.get_ai_chair3d(j.get("chair_art"))]   # народные коляски — только кадры, без сетки
sheet = pygame.Surface((CW * 2 * 3, CH * ((len(jobs) + 2) // 3))); sheet.fill((20, 26, 36))
for n, job in enumerate(jobs):
    mesh = game.get_ai_chair3d(job.get("chair_art"))
    for k, yaw in enumerate((-0.75, 2.35)):
        x0, y0 = (n % 3) * CW * 2 + k * CW, (n // 3) * CH
        cell = pygame.Surface((CW, CH)); cell.fill((30, 38, 50))
        big = pygame.Surface((CW * SS, CH * SS)); big.fill((30, 38, 50))
        polys = game.project_mesh(mesh, yaw, 0.32, pygame.Rect(0, 0, CW, CH), 0.85, getattr(mesh, "pivot", None), ss=SS)
        for depth, pts, col, part, fl in polys:
            pygame.draw.polygon(big, col, pts)
        cell.blit(pygame.transform.smoothscale(big, (CW, CH)), (0, 0))
        if k == 0:
            cell.blit(font.render(f"{job['id']}: {job.get('chair_name') or job.get('chair_art')}", True, (235, 225, 190)), (8, 6))
        sheet.blit(cell, (x0, y0))
pygame.image.save(sheet, out); print(out)
