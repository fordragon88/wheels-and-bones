"""Канонический скелет ручной коляски, вид сбоку (перёд вправо), реальные мм.
Рисует: lineart (чёрное на белом), control (белое на чёрном) и flat-цветной вариант."""
import os, sys, math
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
pygame.init()
W = H = 1024
SS = 2                       # суперсэмплинг
K = 0.78                     # px на мм
OX, OY = 330, 930            # где на картинке точка (0 мм, пол)
def P(x, y): return (int((OX + x * K) * SS), int((OY - y * K) * SS))
def R(r): return int(r * K * SS)

# --- геометрия (мм) ---
RW = (0, 305); RW_R = 305; RIM_R = 280; PUSH_R = 268
CAST = (430, 95); CAST_R = 95
SEAT_Y = 490; SEAT_X0, SEAT_X1 = -30, 420
G = dict(
  back=[(-30, SEAT_Y), (-55, 905)],                       # задняя стойка/спинка
  handle=[(-55, 905), (-150, 915)],                       # ручка толкания
  seat_rail=[(-30, SEAT_Y), (SEAT_X1, SEAT_Y)],
  lower_rail=[(-20, 330), (430, 330)],                    # нижняя труба рамы
  axle_plate=[(-30, SEAT_Y), (-20, 330), (0, RW[1])],
  front_post=[(SEAT_X1, SEAT_Y), (430, 330), (462, 250)], # передняя стойка до вилки
  fork=[(462, 250), (462, 150), (CAST[0], CAST[1])],
  hanger=[(SEAT_X1 - 10, SEAT_Y - 20), (590, 150)],       # подножка (хэнгер)
  arm_post=[(20, SEAT_Y), (20, 700), (330, 700), (330, SEAT_Y)],
  brake=[(250, SEAT_Y), (215, 470), (205, 520)],          # кронштейн тормоза
  brake_lever=[(250, SEAT_Y), (285, 600)],
)
FOOTPLATE = [(545, 150), (690, 150)]
BACK_CANVAS = [(-25, SEAT_Y + 40), (-50, 860)]

def draw(surface, mode):
    ink = (0, 0, 0) if mode == "line" else (255, 255, 255)
    bg = (255, 255, 255) if mode == "line" else (0, 0, 0)
    flat = mode == "flat"
    if flat: bg = (255, 255, 255)
    surface.fill(bg)
    t = lambda mm: max(2, int(mm * K * SS))
    FR = (60, 130, 190) if flat else ink         # рама
    TI = (40, 40, 48) if flat else ink           # шины
    ME = (175, 180, 192) if flat else ink        # металл
    UP = (70, 60, 90) if flat else ink           # обивка
    # заднее колесо: шина, обод, спицы, ступица, обруч
    pygame.draw.circle(surface, TI, P(*RW), R(RW_R), t(32) if flat else t(9))
    if not flat: pygame.draw.circle(surface, ink, P(*RW), R(RW_R - 32), t(6))
    pygame.draw.circle(surface, ME, P(*RW), R(RIM_R - 8), t(10) if flat else t(6))
    for i in range(18):
        a = 2 * math.pi * i / 18
        h = 2 * math.pi * (i % 2) / 18 * 0.6
        x0 = RW[0] + 32 * math.cos(a + h); y0 = RW[1] + 32 * math.sin(a + h)
        x1 = RW[0] + (RIM_R - 22) * math.cos(a); y1 = RW[1] + (RIM_R - 22) * math.sin(a)
        pygame.draw.line(surface, ME, P(x0, y0), P(x1, y1), t(3))
    pygame.draw.circle(surface, ME, P(*RW), R(40))
    if not flat: pygame.draw.circle(surface, bg, P(*RW), R(40) - t(6))
    pygame.draw.circle(surface, ink if not flat else (90, 90, 100), P(*RW), R(12))
    pygame.draw.circle(surface, ME, P(*RW), R(PUSH_R), t(7))       # обруч
    # кастор
    pygame.draw.circle(surface, TI, P(*CAST), R(CAST_R), t(24) if flat else t(8))
    pygame.draw.circle(surface, ME, P(*CAST), R(30))
    if not flat: pygame.draw.circle(surface, bg, P(*CAST), R(30) - t(6))
    # трубы
    for name, pts in G.items():
        col = (210, 90, 80) if (flat and name.startswith("brake")) else (ME if name == "fork" else FR)
        pygame.draw.lines(surface, col, False, [P(*p) for p in pts], t(22 if name not in ("brake", "brake_lever") else 14))
    pygame.draw.circle(surface, (40, 40, 48) if flat else ink, P(285, 600), R(16))  # ручка тормоза
    # подножка
    pygame.draw.line(surface, (40, 40, 48) if flat else ink, P(*FOOTPLATE[0]), P(*FOOTPLATE[1]), t(16))
    # обивка: спинка и сиденье+подушка, подлокотник
    pygame.draw.line(surface, UP, P(*BACK_CANVAS[0]), P(*BACK_CANVAS[1]), t(55))
    cus = (130, 100, 200) if flat else ink
    x0, y0 = P(SEAT_X0 + 10, SEAT_Y + 75); x1, y1 = P(SEAT_X1 - 5, SEAT_Y + 10)
    rect = pygame.Rect(x0, y0, x1 - x0, y1 - y0)
    if flat: pygame.draw.rect(surface, cus, rect, border_radius=t(25))
    else: pygame.draw.rect(surface, ink, rect, t(7), border_radius=t(25))
    pad = (70, 60, 90) if flat else ink
    pygame.draw.line(surface, pad, P(30, 715), P(320, 715), t(30))
    if not flat: pygame.draw.line(surface, bg, P(45, 715), P(305, 715), t(16))
    # грипса
    pygame.draw.line(surface, (40, 40, 48) if flat else ink, P(-95, 913), P(-160, 916), t(30))
    # ниппель
    pygame.draw.line(surface, ME, P(RW[0], RW[1] - RIM_R + 10), P(RW[0], RW[1] - RIM_R - 18), t(10))

out = sys.argv[1]
for mode in ("line", "control", "flat"):
    big = pygame.Surface((W * SS, H * SS))
    draw(big, mode)
    pygame.image.save(pygame.transform.smoothscale(big, (W, H)), os.path.join(out, f"skel_{mode}.png"))
print("done")
