"""Канонический скелет электроколяски со средним приводом, вид сбоку (перёд вправо), мм."""
import os, sys, math
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
pygame.init()
W = H = 1024; SS = 2; K = 0.78; OX, OY = 470, 930
def P(x, y): return (int((OX + x * K) * SS), int((OY - y * K) * SS))
def R(r): return max(1, int(r * K * SS))
def t(mm): return max(2, int(mm * K * SS))
def rect(x0, y0, x1, y1):
    a, b = P(x0, y1), P(x1, y0); return pygame.Rect(a[0], a[1], b[0] - a[0], b[1] - a[1])

def draw(s):
    s.fill((255, 255, 255))
    BASE, SHROUD, TIRE = (58, 62, 74), (78, 84, 100), (40, 40, 48)
    MET, UPH, CUS = (175, 180, 192), (70, 60, 90), (110, 90, 140)
    # касторы (сзади и спереди) с вилками
    for cx in (-330, 330):
        pygame.draw.line(s, MET, P(cx + 20, 175), P(cx + 20, 120), t(18))
        pygame.draw.line(s, MET, P(cx + 20, 120), P(cx, 75), t(14))
        pygame.draw.circle(s, TIRE, P(cx, 75), R(75)); pygame.draw.circle(s, MET, P(cx, 75), R(35))
        pygame.draw.circle(s, (90, 90, 100), P(cx, 75), R(10))
    # база-шасси и батарейный отсек
    pygame.draw.rect(s, BASE, rect(-390, 150, 400, 270), border_radius=t(40))
    pygame.draw.rect(s, SHROUD, rect(-250, 170, 230, 250), border_radius=t(18))   # крышка батарей
    pygame.draw.rect(s, (110, 210, 235), rect(-60, 200, 60, 215), border_radius=t(6))  # индикатор
    pygame.draw.circle(s, (224, 120, 112), P(-200, 230), R(14))                   # предохранитель
    # мотор-редуктор за колесом + рычаг расцепления
    pygame.draw.rect(s, (90, 90, 104), rect(-170, 130, -20, 220), border_radius=t(20))
    pygame.draw.line(s, (232, 200, 64), P(-150, 215), P(-185, 300), t(16))
    pygame.draw.circle(s, (232, 200, 64), P(-185, 300), R(16))
    # стойка сиденья (за колесом)
    pygame.draw.rect(s, BASE, rect(-50, 270, 50, 430))
    # ведущее колесо (по центру)
    pygame.draw.circle(s, TIRE, P(0, 175), R(175))
    pygame.draw.circle(s, MET, P(0, 175), R(120))
    pygame.draw.circle(s, (130, 135, 150), P(0, 175), R(120), t(10))
    for i in range(5):
        a = 2 * math.pi * i / 5 + 0.3
        pygame.draw.line(s, (130, 135, 150), P(0, 175), P(105 * math.cos(a), 175 + 105 * math.sin(a)), t(22))
    pygame.draw.circle(s, (90, 90, 104), P(0, 175), R(32))
    # стойка сиденья, сиденье, спинка
    pygame.draw.rect(s, (60, 60, 72), rect(-240, 420, 240, 450), border_radius=t(10))
    pygame.draw.rect(s, CUS, rect(-235, 445, 235, 520), border_radius=t(30))
    pygame.draw.polygon(s, UPH, [P(-250, 470), P(-150, 470), P(-200, 960), P(-300, 960)])
    # подлокотник, контроллер, джойстик, проводка
    pygame.draw.line(s, (60, 60, 72), P(-150, 520), P(-150, 650), t(26))
    pygame.draw.line(s, (60, 60, 72), P(140, 520), P(140, 650), t(26))
    pygame.draw.rect(s, UPH, rect(-200, 640, 200, 680), border_radius=t(18))
    pygame.draw.rect(s, (42, 42, 52), rect(180, 640, 300, 700), border_radius=t(14))
    pygame.draw.rect(s, (110, 210, 235), rect(195, 668, 240, 684), border_radius=t(4))
    pygame.draw.polygon(s, (36, 36, 44), [P(250, 700), P(290, 700), P(282, 725), P(258, 725)])  # пыльник
    pygame.draw.line(s, MET, P(270, 722), P(270, 775), t(10))
    pygame.draw.circle(s, (224, 120, 112), P(270, 790), R(22))
    pygame.draw.lines(s, MET, False, [P(230, 640), P(260, 560), P(250, 440), P(220, 270)], t(7))  # кабель
    # подножка
    pygame.draw.line(s, MET, P(230, 430), P(430, 150), t(20))
    pygame.draw.line(s, (36, 36, 44), P(400, 140), P(560, 140), t(20))

out = sys.argv[1]
big = pygame.Surface((W * SS, H * SS)); draw(big)
pygame.image.save(pygame.transform.smoothscale(big, (W, H)), os.path.join(out, "power_skel_flat.png"))
print("done")
