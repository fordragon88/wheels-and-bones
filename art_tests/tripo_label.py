"""Разметка деталей облегчённой модели Tripo и запись в формат игры (assets/models/chair_<key>_ai[_lod].json).

python tripo_label.py <key> [--target N] [--dir D]   (читает D/<key>_full.npz, пишет в D и D/models; D по умолчанию
                                                      art_tests/tripo; правила — SPECS ниже)

Правила по порядку, грань берёт первую подходящую деталь (по центру грани), остальное — «frame».
  wheel  — колесо: центр (x, y) и радиус уточняются по точкам обода; по расстоянию до оси:
           шина / обод / спицы / подшипник / ось, обруч (pushrim) — снаружи плоскости колеса;
  box    — коробка x/y/|z| (мм), можно ограничить стороной (z>0 / z<0).
До разметки — правка геометрии: drop (убрать грани в коробке x/y/|z|, можно светлее lum) и move (перенести
грани в коробке x/y/z на d; общие с остальной моделью вершины копируются).
Оси игры: x — вперёд, y — вверх, пол 0, z — вбок (пульт/правая сторона = +z), мм."""
import os, sys, json, math
import numpy as np
from scipy.spatial import cKDTree
import fast_simplification
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

INF = 1e9
SPECS = {
    # Баба Яга — Vermeiren D100 (складная стальная)
    "yaga": dict(art="chair_yaga", spokes=36, wheels=[
        dict(c=(-210, 300), R=290, z=(270, 350), kind="spoked"),
        dict(c=(190, 90), R=88, z=(185, 265), kind="caster")],
        boxes=[("caster_stem", (155, 245), (120, 280), (175, 275)),
               ("footrest", (335, 540), (110, 300), (0, INF)),
               ("brake", (-15, 70), (320, 470), (240, 315)),
               ("armrest", (-140, 110), (660, 730), (0, INF)),
               ("backrest", (-290, -105), (440, 950), (0, 300)),
               ("seat", (-170, 130), (430, 580), (0, 270))]),
    # Русалка — Panthera X3 (карбон)
    "rusalka": dict(art="chair_rusalka", spokes=24, wheels=[
        dict(c=(-110, 300), R=300, z=(225, 305), kind="spoked"),
        dict(c=(265, 48), R=50, z=(205, 275), kind="caster")],
        drop=[dict(x=(-420, -322), y=(480, 680), az=(100, 230)),          # «рога» за спинкой — мусор Tripo
              dict(x=(-322, -306), y=(570, 680), az=(100, 230), lum=45)],
        boxes=[("caster_stem", (235, 305), (55, 270), (195, 280)),
               ("footrest", (320, 430), (40, 240), (0, INF)),
               ("brake", (110, 210), (330, 430), (170, 270)),
               ("backrest", (-380, -250), (440, 780), (0, INF)),
               ("seat", (-170, 240), (440, 570), (0, 240))]),
    # Ра (бог солнца) — Quickie Nitrum + колёса с мотором в ступице (e-motion): ступицу дорисовываем
    "firebird": dict(art="chair_ra", spokes=24, wheels=[
        dict(c=(-100, 300), R=300, z=(245, 325), kind="spoked", hub=dict(r=105, w=55, part="motor")),
        dict(c=(280, 45), R=46, z=(205, 270), kind="caster")],
        boxes=[("caster_stem", (255, 325), (55, 200), (195, 275)),
               ("brake", (150, 250), (320, 445), (195, 300)),
               ("footrest", (300, 430), (40, 120), (0, 210)),
               ("backrest", (-260, -110), (560, 830), (0, INF)),
               ("seat", (-200, 280), (400, 570), (0, 250))],
        recolor_frame=(205, 45, 30)),
    # Леший — Magic Mobility Extreme X8 (4×4)
    "leshy": dict(art="chair_leshy", wheels=[
        dict(c=(-430, 215), R=215, z=(215, 355), kind="power"),
        dict(c=(200, 215), R=215, z=(215, 355), kind="power")],
        # Tripo поставил пульт по центру перед сиденьем — переносим на правый подлокотник (как у X8 и под правой
        # рукой Лешего на рисунке); наклонную панель пульта убираем — на рисунке её нет
        move=[dict(x=(0, 340), y=(628, 900), z=(-110, 120), d=(-40, 0, 255))],
        drop=[dict(x=(-130, 100), y=(630, 700), az=(0, 70)),                 # остаток крепления пульта на сиденье
              dict(x=(205, 345), y=(740, 905), az=(0, 125))],                # наклонная панель пульта
        boxes=[("freewheel", (-700, -545), (250, 440), (0, 220)),
               ("joystick", (78, 300), (690, 860), (180, INF)),
               ("footrest", (300, 720), (200, 340), (0, INF)),
               ("motor", (-560, 330), (110, 320), (120, 215)),
               ("battery", (-330, 160), (140, 420), (0, 150)),
               ("backrest", (-420, -140), (720, 1400), (0, INF)),
               ("seat", (-160, 320), (600, 730), (0, INF))]),
    # Бабушка Агата — Ki Mobility Focus CR (ручная, наклон в пространстве). Tripo (Scene (5).glb) — прямое сиденье;
    # в игре показываем наклон 20° (tilt), чтобы было видно, что кресло с наклоном. Короб за спинкой — лишний.
    "focuscr": dict(art="chair_focuscr", wheels=[
        dict(c=(-330, 230), R=230, z=(250, 320), kind="spoked"),
        dict(c=(305, 100), R=85, z=(230, 320), kind="caster")],
        drop=[dict(x=(-510, -375), y=(410, 700), az=(0, 95))],
        boxes=[("tilt_lever", (-510, -370), (930, 1035), (160, 260)),
               ("tilt_cable", (-430, -310), (720, 820), (170, 260)),
               ("anti_tip", (-530, -395), (430, 545), (140, 270)),
               ("brake", (-175, -55), (255, 385), (215, 315)),
               ("gas_spring", (-210, 50), (235, 345), (0, 130)),
               ("tilt_lock", (-130, 70), (355, 435), (170, 265)),
               ("footrest", (420, 620), (40, 150), (0, INF)),
               ("seat", (-260, 340), (400, 490), (0, 230))]),
        # наклон 20° — после доработки: art_tests/model_patch.py focuscr → art_tests/tilt_model.py (целыми деталями;
        # tilt=dict(...) здесь рвёт трубы на границе по граням)
    # Матильда — Permobil F5 Corpus (передний привод). Tripo (Scene (6).glb). Пульт у F5 один — справа:
    # левый «пульт» и стержни по бокам спинки — лишние.
    "f5": dict(art="chair_f5", wheels=[
        dict(c=(105, 200), R=200, z=(190, 300), kind="power")],
        drop=[dict(x=(0, 150), y=(725, 800), z=(-285, -165)),          # второй (левый) пульт
              dict(x=(-235, -145), y=(560, 760), az=(268, 330))],      # стержни по бокам спинки
        boxes=[("controller", (0, 150), (725, 800), (165, 285), "signed"),
               ("breaker", (-560, -470), (190, 345), (0, 160)),
               ("freewheel", (-75, 0), (140, 270), (150, 285)),          # рычаг — сзади мотора, у колеса
               ("motor", (-45, 150), (110, 300), (55, 195)),
               ("battery", (-370, -50), (55, 335), (0, 185)),
               ("footrest", (380, 600), (25, 115), (0, INF))]),
    # Permobil M3 Corpus — Meshy (multi-image по art_tests/meshy_ref, Downloads/m3.glb), красный -> фиолетовый;
    # --dir art_tests/gen3d. Пульт — справа (+z): ручка, чехол, корпус; провод вниз по стойке подлокотника
    "m3": dict(art="chair_m3", wheels=[
        dict(c=(-60, 165), R=165, z=(190, 285), kind="power"),
        dict(c=(255, 75), R=75, z=(205, 290), kind="caster"),
        dict(c=(-385, 75), R=80, z=(175, 240), kind="caster")],
        boxes=[("joystick", (195, 275), (648, 720), (220, 310), "signed"),
               ("boot", (195, 275), (628, 648), (220, 310), "signed"),
               ("controller", (150, 380), (595, 700), (210, 335), "signed"),
               ("wiring", (95, 185), (430, 600), (250, 325), "signed"),
               ("freewheel", (-200, -110), (230, 340), (165, 235)),
               ("motor", (-150, 60), (95, 235), (140, 215)),
               ("fuse", (-440, -320), (190, 290), (0, 70)),
               ("battery", (-200, 110), (120, 280), (0, 150)),
               ("footrest", (380, 560), (40, 120), (0, INF))]),
    # Quantum Edge 4 — Meshy (meshy_models/quantum_edge_4.glb), сиденье поднято (iLevel), height=1430;
    # пульт справа (+z); лифт — «ножницы» под сиденьем, актуатор в их середине, провод — сзади
    "edge4": dict(art="chair_edge4", wheels=[
        dict(c=(-30, 140), R=140, z=(180, 280), kind="power"),
        dict(c=(240, 60), R=60, z=(150, 270), kind="caster"),
        dict(c=(-370, 62), R=62, z=(150, 270), kind="caster")],
        boxes=[("joystick", (270, 330), (925, 990), (225, 300), "signed"),
               ("controller", (180, 400), (880, 960), (215, 310), "signed"),
               ("armrest", (-260, 260), (840, 960), (170, 320)),
               ("actuator", (-230, -100), (380, 580), (0, 90)),
               ("seat_lift", (-340, -20), (330, 620), (0, 240)),
               ("wiring", (-420, -330), (330, 720), (0, 260)),
               ("seat", (-240, 300), (630, 810), (0, 240)),
               ("freewheel", (-160, -90), (220, 330), (170, 265)),
               ("motor", (-110, 50), (70, 210), (110, 200)),
               ("fuse", (-470, -400), (140, 260), (0, 70)),
               ("battery", (-200, 100), (110, 300), (0, 95)),
               ("footrest", (300, 560), (330, 370), (0, INF))]),
    # Quantum Edge 4 с ОПУЩЕННЫМ сиденьем — Meshy (meshy_models/quantum_edge_4_seat_down.glb), height=1180, 24.10;
    # Бренна, «Замена пары батарей» (t_battery). Чёрная с красными вставками уже у Meshy (рефы перекрашены) — без recolor.
    "edge4b": dict(art="chair_edge4b", wheels=[
        dict(c=(5, 145), R=145, z=(150, 290), kind="power"),
        dict(c=(275, 100), R=100, z=(185, 290), kind="caster"),
        dict(c=(-420, 75), R=75, z=(175, 275), kind="caster")],
        boxes=[("joystick", (255, 310), (690, 750), (215, 300), "signed"),
               ("controller", (235, 420), (625, 715), (210, 315), "signed"),
               ("armrest", (-260, 260), (605, 695), (170, 320)),
               ("actuator", (-230, -100), (325, 420), (0, 90)),
               ("seat_lift", (-340, -20), (315, 415), (0, 240)),
               ("wiring", (-460, -320), (330, 640), (0, 260)),
               ("seat", (-240, 300), (400, 570), (0, 240)),
               ("freewheel", (-170, -90), (210, 330), (160, 280)),
               ("motor", (-110, 50), (70, 210), (110, 200)),
               ("fuse", (-470, -390), (180, 285), (0, 70)),
               ("battery", (-200, 100), (110, 300), (0, 95)),
               ("footrest", (300, 560), (60, 130), (0, INF))]),
    # Permobil F5 Corpus — Meshy (meshy_models/permobil_f5_corpus.glb), передний привод, height=1260; бирюзовый -> графит
    # (как у Матильды в игре); пульт справа на подлокотнике, автомат сзади корпуса
    "f5m": dict(art="chair_f5", wheels=[
        dict(c=(215, 182), R=182, z=(235, 315), kind="power"),
        dict(c=(-440, 95), R=95, z=(180, 260), kind="caster")],
        boxes=[("controller", (330, 460), (700, 790), (240, 345), "signed"),
               ("breaker", (-300, -225), (230, 345), (0, 110)),
               ("freewheel", (40, 140), (200, 320), (150, 240)),
               ("motor", (120, 300), (100, 260), (120, 232)),
               ("battery", (-230, 100), (60, 300), (0, 140)),
               ("footrest", (380, 570), (80, 170), (0, 300))]),
    # Drive Trident HD — Meshy (meshy_models/drive_trident_hd.glb), передний привод, height=1175; пульт справа,
    # большие задние касторы, впереди — подножка и маленький антиопрокидыватель
    "trident": dict(art="chair_trident", wheels=[
        dict(c=(150, 175), R=178, z=(270, 380), kind="power"),
        dict(c=(-470, 115), R=115, z=(240, 345), kind="caster")],
        boxes=[("controller", (100, 310), (720, 840), (285, 385), "signed"),
               ("wiring", (-120, 130), (560, 720), (300, 360), "signed"),         # провод пульта под подлокотником
               ("motor", (20, 220), (90, 270), (165, 270)),
               ("freewheel", (-90, 40), (210, 340), (175, 300)),
               ("battery", (-260, 80), (100, 330), (0, 170)),
               ("footrest", (330, 630), (100, 210), (0, INF))]),
    # Quickie Pulse 6 — Meshy (meshy_models/quickie_pulse_6.glb), средний привод, height=1170; пульт VR2 справа
    "pulse6": dict(art="chair_pulse6", wheels=[
        dict(c=(-85, 135), R=135, z=(185, 265), kind="power"),
        dict(c=(240, 60), R=60, z=(165, 265), kind="caster"),
        dict(c=(-385, 62), R=62, z=(165, 265), kind="caster")],
        boxes=[("joystick", (230, 290), (655, 705), (220, 270), "signed"),
               ("boot", (230, 290), (638, 655), (220, 270), "signed"),
               ("controller", (195, 375), (595, 700), (210, 295), "signed"),
               ("wiring", (150, 245), (320, 600), (215, 270), "signed"),       # провод пульта по стойке подлокотника
               ("mag_brake", (-120, -50), (100, 180), (60, 120)),
               ("freewheel", (-130, -30), (190, 290), (120, 200)),
               ("brushes", (-170, -90), (150, 225), (120, 185)),
               ("motor", (-170, 0), (75, 205), (110, 200)),
               ("fuse", (-330, -240), (150, 290), (0, 90)),
               ("battery", (-300, 200), (100, 300), (0, 110)),
               ("footrest", (350, 570), (30, 170), (0, INF))]),
    # Змей Горыныч — Pride Jazzy (EVO) 614, Meshy (meshy_models/pride_jazzy_614.glb), height=1150; пульт справа
    "jazzy": dict(art="chair_gorynych", wheels=[
        dict(c=(-30, 140), R=140, z=(215, 320), kind="power"),
        dict(c=(310, 62), R=62, z=(200, 300), kind="caster"),
        dict(c=(-400, 64), R=64, z=(200, 300), kind="caster")],
        boxes=[("joystick", (-10, 70), (740, 810), (140, 260), "signed"),
               ("controller", (-40, 130), (690, 760), (130, 310), "signed"),
               ("backrest", (-430, -150), (560, 1010), (0, INF)),
               ("breaker", (-340, -250), (240, 340), (0, 120)),
               ("footrest", (250, 470), (60, 210), (0, INF)),
               ("battery", (-300, 160), (100, 330), (0, 175)),
               ("seat", (-260, 310), (390, 570), (0, INF))]),
    # WHILL Model C2/Ci — Meshy (meshy_models/whill_model_c2.glb), height=910: задний привод (литые шины), спереди
    # омни-колёса; пульт с джойстиком — на правом подлокотнике, батарея — под сиденьем сзади
    "whill": dict(art="chair_whillc2", wheels=[
        dict(c=(-245, 145), R=145, z=(205, 280), kind="power")],
        boxes=[("omni_wheel", (225, 500), (0, 290), (195, 290)),
               ("joystick", (160, 225), (745, 790), (255, 305), "signed"),
               ("controller", (110, 280), (650, 760), (235, 320), "signed"),
               ("armrest", (-180, 280), (640, 770), (215, 330)),
               ("freewheel", (-170, -80), (240, 340), (150, 215)),
               ("seat_cable", (-200, 10), (330, 460), (25, 120)),          # кабель сиденья у стойки под сиденьем
               ("battery", (-200, 0), (190, 330), (0, 120)),
               ("anti_tip", (-520, -400), (20, 140), (0, 200)),
               ("footrest", (120, 420), (60, 160), (0, 190)),
               ("seat", (-260, 260), (440, 580), (0, 230))]),
    # Бабушка Агата — Ki Mobility Focus CR, Meshy (meshy_models/ki_mobility_focus_cr.glb), height=1025, --pitch=2.78:
    # Meshy сделал кресло уже наклонённым (tilt-in-space) — так и оставляем. Курки наклона — на ручках сзади, трос — вниз
    # по спинке к фиксатору под сиденьем, газовая пружина — под сиденьем по центру
    "fcr": dict(art="chair_focuscr", spokes=0, wheels=[
        dict(c=(-235, 262), R=262, z=(238, 290), kind="spoked"),
        dict(c=(250, 70), R=70, z=(200, 270), kind="caster")],
        boxes=[("tilt_lever", (-720, -575), (780, 935), (0, 200)),     # ручки толкания с курками (у Meshy — ближе к центру)
               ("tilt_cable", (-600, -380), (560, 840), (120, 270)),
               ("anti_tip", (-500, -380), (20, 170), (130, 260)),
               ("brake", (-60, 80), (230, 360), (215, 300)),
               ("gas_spring", (-250, 150), (240, 400), (0, 140)),
               ("tilt_lock", (-300, 60), (250, 420), (140, 240)),
               ("footrest", (380, 720), (480, 640), (0, INF)),
               ("seat", (-280, 300), (470, 680), (0, 230))]),
    # Леший — Magic Mobility Extreme X8, Meshy (meshy_models/magic_mobility_x8.glb), height=1300; 4×4, пульт справа,
    # рычаги свободного хода — сзади; корпус в кадрах перекрашен оранжевый -> красный
    "x8": dict(art="chair_leshy", wheels=[
        dict(c=(-385, 215), R=215, z=(235, 360), kind="power", hub=None),
        dict(c=(215, 215), R=215, z=(235, 360), kind="power")],
        boxes=[("controller", (160, 400), (760, 910), (150, 360), "signed"),
               ("freewheel", (-690, -560), (150, 460), (0, 240)),
               ("motor", (-480, 300), (120, 310), (150, 235)),
               ("footrest", (380, 700), (150, 260), (0, INF)),
               ("seat", (-320, 230), (560, 760), (0, 300))]),
    # Баба Яга — Vermeiren D100, Meshy (meshy_models/vermeiren_d100.glb), height=940: складная стальная, тормоз —
    # у переднего края заднего колеса, ручки толкания сзади
    "d100": dict(art="chair_yaga", spokes=36, wheels=[
        dict(c=(-215, 300), R=290, z=(270, 350), kind="spoked"),
        dict(c=(182, 95), R=90, z=(180, 265), kind="caster")],
        boxes=[("caster_stem", (150, 262), (150, 290), (180, 265)),
               ("brake", (85, 190), (360, 515), (185, 295)),
               ("footrest", (330, 560), (100, 320), (0, INF)),
               ("armrest", (-310, 55), (655, 730), (160, 310)),
               ("backrest", (-500, -200), (430, 960), (0, 270)),
               ("seat", (-260, 180), (415, 535), (0, 235))]),
    # Русалка Ольга — Panthera X3, Meshy (meshy_models/panthera_x3.glb), height=800: ультралёгкая активная, колёса 24",
    # тормоз — на раме у верхнего переднего края колеса, подножка — трубка-петля
    "x3": dict(art="chair_rusalka", spokes=24, wheels=[
        dict(c=(-124, 314), R=306, z=(235, 305), kind="spoked"),
        dict(c=(268, 55), R=48, z=(190, 255), kind="caster")],
        boxes=[("caster_stem", (230, 360), (100, 245), (175, 255)),
               ("brake", (130, 220), (415, 515), (165, 265)),
               ("footrest", (305, 460), (60, 250), (0, 200)),
               ("backrest", (-400, -200), (430, 800), (0, 240)),
               ("seat", (-230, 280), (415, 525), (0, 215))]),
    # Мумия Сенеб — Quickie Nitrum, Meshy (meshy_models/quickie_nitrum.glb), height=850: чистая коляска, ступицы-моторы
    # Alber e-motion дорисовываем (hub; в кадрах — blender_render.add_hub с тем же центром), тормоз — рычаг у шины спереди
    "nitrum": dict(art="chair_ra", spokes=24, wheels=[
        dict(c=(-115, 328), R=310, z=(245, 300), kind="spoked", hub=dict(r=115, w=60, part="motor")),
        dict(c=(282, 58), R=50, z=(160, 245), kind="caster")],
        boxes=[("caster_stem", (280, 380), (100, 255), (150, 245)),
               ("brake", (185, 270), (395, 480), (150, 255)),
               ("footrest", (295, 450), (25, 130), (0, 205)),
               ("backrest", (-345, -175), (450, 850), (0, 230)),
               ("seat", (-200, 280), (425, 565), (0, 220))]),
    # Мартин — Invacare 9000, Meshy (meshy_models/invacare_9000.glb), height=920: литые колёса (спицы — литые лучи),
    # камера — низ шины, ниппель — участок обода внизу спереди; тормоз — колодка у переднего верха шины
    "inv9000": dict(art="chair_basic", spokes=0, wheels=[
        dict(c=(-252, 305), R=300, z=(265, 330), kind="spoked",
             sectors=[("tube", 240, 300, -32, 0), ("valve", 302, 312, -62, -28)]),
        dict(c=(137, 98), R=85, z=(210, 280), kind="caster")],
        boxes=[("caster_stem", (110, 205), (170, 325), (205, 280)),
               ("brake", (10, 115), (385, 485), (200, 290)),
               ("footrest", (370, 560), (55, 150), (0, INF)),
               ("armrest", (-310, 0), (640, 720), (150, 290)),
               ("backrest", (-440, -240), (500, 915), (0, 255)),
               ("seat", (-215, 160), (430, 500), (0, 235))]),
    # Тролль Бомм — та же модель Invacare 9000, крупнее (height=985, ×1.07 — 9000 XDT шире и выше); подушка ROHO —
    # верх сиденья, её ниппель — передний угол сиденья, «seat» — спинка
    "inv9000xdt": dict(art="chair_troll", spokes=0, wheels=[
        dict(c=(-270, 327), R=321, z=(284, 353), kind="spoked"),       # «ниппель» Бомма — у подушки, не у колеса
        dict(c=(147, 105), R=91, z=(225, 300), kind="caster")],
        boxes=[("caster_stem", (118, 219), (182, 348), (219, 300)),
               ("brake", (11, 123), (412, 519), (214, 310)),
               ("footrest", (396, 600), (59, 161), (0, INF)),
               ("armrest", (-332, 0), (685, 771), (161, 310)),
               ("valve", (118, 173), (460, 541), (161, 252)),
               ("cushion", (-230, 173), (460, 541), (0, 252)),
               ("seat", (-471, -257), (535, 980), (0, 273))]),
    # Фея Тилли — Progeo Exelle Junior, Meshy (meshy_models/progeo_exelle_junior.glb), height=760: детская активная, рама
    # в кадрах перекрашена салатовый -> розовый; болты — пластина оси на раме внутри колеса, камера — низ шины
    "exelle": dict(art="chair_fairy", spokes=24, wheels=[
        dict(c=(-93, 294), R=297, z=(180, 235), kind="spoked", sectors=[("tube", 240, 300, -30, 0)]),
        dict(c=(260, 46), R=42, z=(170, 235), kind="caster")],
        boxes=[("bolts", (-170, -20), (225, 370), (100, 172)),
               ("anti_tip", (-470, -320), (0, 130), (0, INF)),
               ("footrest", (390, 545), (160, 280), (0, 200)),
               ("backrest", (-310, -140), (450, 770), (0, 200)),
               ("seat", (-200, 260), (420, 565), (0, 190))]),
    # Кицунэ Юки — TiLite Aero Z, Meshy (meshy_models/tilite_aero_z.glb), height=880: жёсткая рама, задние колёса со
    # спицами; тормоз-замок — колодка у переднего верха шины; болты — зажим рамы перед колесом; ниппель — участок обода;
    # антиопрокидывателей в модели нет — добавлены (antitips, те же — в кадрах blender_frames)
    "aeroz": dict(art="chair_aeroz", spokes=24, wheels=[
        dict(c=(-205, 299), R=297, z=(228, 295), kind="spoked", sectors=[("valve", 300, 312, -62, -28)]),
        dict(c=(262, 52), R=52, z=(200, 262), kind="caster")],
        antitips=[dict(p0=(-235, 245, s * 172), p1=(-470, 58, s * 172), r=10, wheel=(24, 18)) for s in (1, -1)],
        boxes=[("caster_stem", (255, 410), (100, 250), (150, 262)),
               ("brake", (52, 118), (322, 458), (148, 252)),
               ("bolts", (-82, -12), (360, 448), (145, 228)),
               ("footrest", (330, 490), (10, 150), (0, 250)),
               ("backrest", (-420, -205), (450, 870), (0, 222)),
               ("seat", (-218, 180), (395, 560), (0, 222))]),
    # Дриада Ивушка — Etac Cross 6, Meshy (meshy_models/etac_cross_6.glb), height=940: складная, X-крестовина; гайка
    # 13 мм угла спинки — кольцо у оси на внутренней стороне осевой пластины; тормоз — штифт перед колесом;
    # антиопрокидыватели — в модели; подушка — верх сиденья
    "cross6": dict(art="chair_cross6", spokes=24, wheels=[
        dict(c=(-147, 322), R=305, z=(255, 335), kind="spoked"),
        dict(c=(244, 58), R=50, z=(225, 290), kind="caster")],
        boxes=[("bolts", (-190, -120), (292, 362), (165, 255)),
               ("brake", (-68, 18), (282, 428), (185, 268)),
               ("anti_tip", (-528, -340), (38, 165), (190, 335)),
               ("caster_stem", (155, 305), (100, 300), (195, 290)),
               ("footrest", (395, 530), (60, 140), (0, 245)),
               ("backrest", (-495, -150), (455, 945), (0, 248)),
               ("armrest", (-135, 50), (655, 735), (215, 265)),
               ("cushion", (-205, 270), (478, 565), (0, 222)),
               ("seat", (-205, 270), (420, 478), (0, 222))]),
    # Орк Гра — Progeo Noir 2.0, Meshy (meshy_models/progeo_noir_2.glb), height=880: карбоновая рама-петля, задние колёса
    # с развалом; тормоз — компактный замок под боковой трубой у переднего верха колеса
    "noir": dict(art="chair_orc", spokes=24, wheels=[
        dict(c=(-101, 349), R=335, z=(255, 335), kind="spoked"),
        dict(c=(378, 55), R=52, z=(200, 270), kind="caster")],
        boxes=[("brake", (92, 165), (452, 508), (150, 285)),
               ("caster_stem", (322, 428), (98, 252), (172, 268)),
               ("footrest", (372, 472), (58, 148), (0, 188)),
               ("backrest", (-325, -178), (452, 875), (0, 222)),
               ("seat", (-205, 282), (428, 566), (0, 222))]),
    # Эльфийка Аэлин — Progeo Ego, Meshy (meshy_models/progeo_ego.glb), height=900: складная активная, салатовая рама;
    # тормоз — рычаг на боковой трубе перед колесом; шток кастора — вертикальная труба над вилкой; болты — верх вилки
    "ego": dict(art="chair_elf", spokes=24, wheels=[
        dict(c=(-135, 328), R=335, z=(262, 345), kind="spoked"),
        dict(c=(332, 54), R=46, z=(245, 312), kind="caster")],
        boxes=[("brake", (148, 240), (384, 482), (205, 298)),
               ("bolts", (318, 400), (196, 268), (225, 312)),
               ("caster_stem", (345, 425), (268, 400), (220, 312)),
               ("footrest", (352, 472), (78, 148), (0, 205)),
               ("backrest", (-355, -170), (450, 890), (0, 250)),
               ("seat", (-195, 258), (418, 552), (0, 240))]),
    # Гильдия (t_q6brake) — Quantum Q6 Edge 2.0, Meshy (meshy_models/quantum_q6_edge.glb), height=1180: средний привод,
    # синий корпус, пульт справа (кривой у Meshy — выпрямляется в кадрах, blender_frames move rot); окна коляски у задания нет
    # Quantum Q6 Edge 2.0 (синяя) — Meshy (meshy_models/quantum_q6_edge.glb), height=1180. С 24.10 — своя коляска
    # chair_q6edge2: граф Дракулеску («ползёт после подъёма сиденья») и Гильдия («батареи на Q6 Edge 2.0»). Правки как
    # в кадрах blender_frames: пульт придвинут к подушке (−40 мм), площадки подножек подняты с пола (+35 мм).
    "q6m": dict(art="chair_q6edge2", wheels=[
        dict(c=(-1, 131), R=140, z=(205, 270), kind="power"),
        dict(c=(250, 62), R=62, z=(190, 290), kind="caster"),
        dict(c=(-410, 62), R=62, z=(170, 270), kind="caster")],
        move=[dict(x=(165, 410), y=(636, 775), z=(100, 300), d=(-40, 0, 0)),
              dict(x=(285, 520), y=(40, 80), z=(-180, 125), d=(0, 35, 0))],
        boxes=[("joystick", (200, 275), (705, 770), (215, 305), "signed"),
               ("controller", (170, 385), (625, 722), (195, 315), "signed"),
               ("armrest", (-200, 180), (585, 725), (170, 330)),
               ("backrest", (-420, -200), (520, 1000), (0, 260)),
               ("seat", (-250, 280), (395, 525), (0, 230)),
               ("actuator", (-230, -60), (330, 400), (0, 100)),
               ("seat_lift", (-360, 250), (330, 400), (0, 240)),
               ("wiring", (-470, -330), (290, 600), (0, 260)),
               ("breaker", (-470, -380), (200, 300), (0, 100)),
               ("freewheel", (-170, -80), (220, 330), (150, 250)),
               ("motor", (-120, 80), (60, 230), (100, 200)),
               ("footrest", (300, 520), (60, 125), (0, 160)),
               ("battery", (-400, 250), (150, 330), (0, 195))]),
    # Оборотень Вольф (было: гном Дургин, Tekna) — Quickie 2, Meshy (meshy_models/quickie_2.glb), height=950: складная,
    # литые колёса, X-крестовина; тормоз-замок — блок под боковой трубой перед колесом; болты — хомут замка на трубе
    "q2": dict(art="chair_dwarf", spokes=0, wheels=[
        dict(c=(-152, 258), R=258, z=(230, 290), kind="spoked"),
        dict(c=(335, 78), R=78, z=(180, 240), kind="caster")],
        boxes=[("brake", (108, 168), (284, 382), (168, 252)),
               ("bolts", (100, 175), (382, 410), (168, 252)),
               ("caster_stem", (210, 320), (150, 330), (165, 232)),
               ("footrest", (330, 480), (50, 125), (0, 228)),
               ("backrest", (-405, -205), (515, 940), (0, 212)),
               ("armrest", (-255, 12), (575, 632), (100, 268)),
               ("seat", (-225, 255), (385, 472), (0, 232))]),
    # Гильдия (t_q6brake) — классическая Quantum Q6 Edge, Meshy (meshy_models/quantum_q6_edge_classic.glb), height=1250:
    # жёлтый корпус, капитанское кресло; крепление пульта дорисовано в кадрах (blender_frames tubes)
    "q6c": dict(art="chair_q6edge", wheels=[
        dict(c=(-10, 160), R=160, z=(235, 330), kind="power")],
        boxes=[("joystick", (75, 290), (655, 790), (250, 370), "signed"),
               ("controller", (60, 180), (600, 660), (220, 340), "signed"),
               ("battery", (-420, 260), (130, 360), (0, 220)),
               ("seat", (-420, 300), (430, 720), (0, 260))]),
    # Змей Горыныч — Pride Jazzy 614 (среднеприводная)
    "raiju": dict(art="chair_gorynych", wheels=[
        dict(c=(20, 160), R=160, z=(215, 310), kind="power"),
        dict(c=(345, 62), R=64, z=(215, 310), kind="caster"),
        dict(c=(-400, 62), R=64, z=(215, 310), kind="caster")],
        boxes=[("joystick", (90, 220), (600, 700), (0, INF)),
               ("controller", (40, 240), (540, 640), (150, INF)),
               ("breaker", (-400, -300), (230, 340), (0, 110)),
               ("freewheel", (-110, 60), (240, 310), (120, 235)),
               ("motor", (-80, 120), (80, 250), (110, 215)),
               ("battery", (-380, 10), (40, 330), (0, 200)),
               ("footrest", (290, 500), (60, 150), (0, INF)),
               ("backrest", (-420, -190), (480, 1010), (0, INF)),
               ("armrest", (-260, 120), (540, 660), (0, INF)),
               ("seat", (-280, 300), (340, 520), (0, INF))]),
}


def fit_circle(P):
    A = np.c_[2 * P[:, 0], 2 * P[:, 1], np.ones(len(P))]
    b = (P ** 2).sum(1)
    cx, cy, c = np.linalg.lstsq(A, b, rcond=None)[0]
    return cx, cy, math.sqrt(max(c + cx * cx + cy * cy, 1))


def refine_wheel(V, w):
    cx, cy = w["c"]
    R = w["R"]
    az = np.abs(V[:, 2])
    band = (az >= w["z"][0]) & (az <= w["z"][1])
    R0 = R
    for _ in range(4):                                   # центр — по кольцу, радиус — по самой внешней точке шины
        r = np.hypot(V[:, 0] - cx, V[:, 1] - cy)
        m = band & (r > 0.8 * R0) & (r < 1.15 * R0)
        if m.sum() < 50:
            break
        cx, cy, _ = fit_circle(V[m][:, :2])
    lowest = V[band & (np.abs(V[:, 0] - cx) < 0.3 * R0), 1]
    R = cy - (lowest.min() if len(lowest) else 0.0)      # колесо стоит на полу: радиус = высота оси над низом шины
    return cx, cy, R


def edit(V, F, C, spec):
    P = V[F].mean(1)
    L = C[F][:, :, :3].mean((1, 2))                      # яркость (у C могут быть ещё столбцы — UV и т.п.)
    keep = np.ones(len(F), bool)
    for b in spec.get("drop", []):
        az = P[:, 2] if "z" in b else np.abs(P[:, 2])          # "z" — со знаком (одна сторона), "az" — обе
        zr = b.get("z", b.get("az"))
        keep &= ~((P[:, 0] >= b["x"][0]) & (P[:, 0] < b["x"][1]) & (P[:, 1] >= b["y"][0]) & (P[:, 1] <= b["y"][1])
                  & (az >= zr[0]) & (az <= zr[1]) & (L > b.get("lum", -1)))
    for b in spec.get("move", []):
        m = keep & (P[:, 0] >= b["x"][0]) & (P[:, 0] <= b["x"][1]) & (P[:, 1] >= b["y"][0]) & (P[:, 1] <= b["y"][1])             & (P[:, 2] >= b["z"][0]) & (P[:, 2] <= b["z"][1])
        vi = np.unique(F[m])
        remap = np.full(len(V), -1)
        remap[vi] = len(V) + np.arange(len(vi))
        V = np.vstack([V, V[vi] + np.asarray(b["d"], float)])
        C = np.vstack([C, C[vi]])
        F = F.copy()
        F[m] = remap[F[m]]
    F = F[keep]
    used = np.unique(F)                                  # убрать осиротевшие вершины
    remap = np.full(len(V), -1)
    remap[used] = np.arange(len(used))
    return V[used], remap[F], C[used]


def in_wheels(P, spec):
    """Грани в объёме колёс (спицы — тонкие и часто отдельные куски: их чистка не трогает)."""
    m = np.zeros(len(P), bool)
    az = np.abs(P[:, 2])
    for w in spec["wheels"]:
        r = np.hypot(P[:, 0] - w["c"][0], P[:, 1] - w["c"][1])
        m |= (r <= w["R"] * 1.08) & (az >= w["z"][0] - 25) & (az <= w["z"][1] + 25)
    return m


def despike(V, F, C, spec, small=40, ratio=12.0, min_len=18.0):
    """Мусор генерации вне колёс: маленькие отдельные куски (< small граней) и «иглы» — вытянутые грани
    с открытым краем (шипы и лохмотья; трубы рамы замкнуты, их длинные грани не трогаются)."""
    q = np.round(V * 10).astype(np.int64)
    _, inv = np.unique(q, axis=0, return_inverse=True)
    W = inv.ravel()[F]                                   # вершины, склеенные по месту
    P = V[F].mean(1)
    wh = in_wheels(P, spec)
    drop = np.zeros(len(F), bool)
    n = W.max() + 1
    r_ = np.r_[W[:, 0], W[:, 1]]
    c_ = np.r_[W[:, 1], W[:, 2]]
    k, lab = connected_components(coo_matrix((np.ones(len(r_)), (r_, c_)), shape=(n, n)), directed=False)
    fl = lab[W[:, 0]]
    size = np.bincount(fl, minlength=k)
    drop |= (size[fl] < small) & ~wh
    E = np.sort(np.r_[W[:, [0, 1]], W[:, [1, 2]], W[:, [2, 0]]], axis=1)
    key = E[:, 0] * n + E[:, 1]
    _, ei, cnt = np.unique(key, return_inverse=True, return_counts=True)
    open_edge = (cnt[ei] == 1).reshape(3, -1).T.any(1)
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    L = np.c_[np.linalg.norm(b - a, axis=1), np.linalg.norm(c - b, axis=1), np.linalg.norm(a - c, axis=1)]
    area = np.linalg.norm(np.cross(b - a, c - a), axis=1) / 2
    lmax = L.max(1)
    thin = lmax / np.maximum(2 * area / np.maximum(lmax, 1e-9), 1e-9)   # длина / высота
    drop |= open_edge & (thin > ratio) & (lmax > min_len) & ~wh
    print(f"  чистка: кусков {int(((size[fl] < small) & ~wh).sum())} граней, игл {int((drop).sum())} граней всего")
    F = F[~drop]
    used = np.unique(F)
    remap = np.full(len(V), -1)
    remap[used] = np.arange(len(used))
    return V[used], remap[F], C[used]


def label(V, F, C, spec):
    names = ["frame"]

    def pid(n):
        if n not in names:
            names.append(n)
        return names.index(n)
    P = V[F].mean(1)
    az = np.abs(P[:, 2])
    lab = np.full(len(F), -1)
    wheels = []
    for w in spec["wheels"]:
        cx, cy, R = refine_wheel(V, w)
        wheels.append((cx, cy, R, w))
        r = np.hypot(P[:, 0] - cx, P[:, 1] - cy)
        inband = (az >= w["z"][0] - 5) & (az <= w["z"][1] + 5) & (r <= R * 1.06) & (lab < 0)
        k = w["kind"]
        if k == "caster":
            lab[inband & (r > 0.55 * R)] = pid("caster")
            lab[inband & (r <= 0.55 * R)] = pid("bearing" if "caster_bearing" in w else "caster")
            continue
        tire_w = 32 if k == "spoked" else 0.3 * R
        tire_r = (r >= R - tire_w)
        plane = np.median(az[inband & tire_r]) if (inband & tire_r).any() else np.mean(w["z"])
        wheels[-1] = (cx, cy, R, dict(w, plane=float(plane)))
        if k == "spoked":
            push = inband & (az > plane + 14) & (r > 0.72 * R)
            lab[push] = pid("rear_wheel")
            rest = inband & ~push
            lab[rest & tire_r] = pid("tire")
            lab[rest & (r >= R - 52) & ~tire_r] = pid("rim")
            lab[rest & (r < 34)] = pid("axle")
            lab[rest & (r >= 34) & (r < 62)] = pid("bearing")
            lab[rest & (r >= 62) & (r < R - 52)] = pid("spokes")
        else:                                            # электро: толстая шина, диск, ось
            lab[inband & tire_r] = pid("tire")
            lab[inband & ~tire_r & (r >= 0.18 * R)] = pid("rim")
            lab[inband & (r < 0.18 * R)] = pid("axle")
        ang = np.degrees(np.arctan2(P[:, 1] - cy, P[:, 0] - cx)) % 360
        for part, a0, a1, d0, d1 in w.get("sectors", ()):  # участок колеса — своя деталь (камера внизу шины, ниппель)
            lab[inband & (ang >= a0) & (ang <= a1) & (r >= R + d0) & (r <= R + d1)] = pid(part)
    for name, (x0, x1), (y0, y1), (z0, z1), *opt in spec["boxes"]:
        zz = P[:, 2] if "signed" in opt else az
        m = (lab < 0) & (P[:, 0] >= x0) & (P[:, 0] <= x1) & (P[:, 1] >= y0) & (P[:, 1] <= y1) & (zz >= z0) & (zz <= z1)
        lab[m] = pid(name)
    lab[lab < 0] = 0
    return lab, names, wheels


def tilt_seat(V, F, C, lab, names, t):
    """Наклон в пространстве: сиденье со спинкой, подлокотниками и подножками поворачивается назад на t["deg"]
    вокруг t["pivot"] (x, y); колёса, касторы, тормоза и нижняя рама (центр грани ниже t["base_y"], кроме передних
    подвесов x > t["front_x"]) остаются. Общие вершины копируются — база не тянется за сиденьем."""
    keep = {names.index(n) for n in t.get("keep", ()) if n in names}
    P = V[F].mean(1)
    rot = ~np.isin(lab, list(keep)) & ((P[:, 1] > t["base_y"]) | (P[:, 0] > t["front_x"]))
    vi = np.unique(F[rot])
    new = np.arange(len(V), len(V) + len(vi))
    remap = np.full(len(V), -1)
    remap[vi] = new
    a = math.radians(t["deg"])
    px, py = t["pivot"]
    dx, dy = V[vi, 0] - px, V[vi, 1] - py
    Vn = V[vi].copy()
    Vn[:, 0] = px + dx * math.cos(a) - dy * math.sin(a)
    Vn[:, 1] = py + dx * math.sin(a) + dy * math.cos(a)
    F = F.copy()
    F[rot] = remap[F[rot]]
    print(f"  наклон {t['deg']}°: повёрнуто {int(rot.sum())} граней")
    return np.vstack([V, Vn]), F, np.vstack([C, C[vi]])


def add_antitips(V, F, C, lab, names, ats):
    """Антиопрокидыватели, которых нет в модели (Meshy): трубка p0→p1 и колёсико у p1, деталь anti_tip. Те же
    параметры — в blender_frames GLB[...]["antitips"] (там они рисуются в кадрах; здесь — для кружка детали)."""
    if not ats:
        return V, F, C, lab, names
    if "anti_tip" not in names:
        names.append("anti_tip")
    p = names.index("anti_tip")
    for a in ats:
        p0, p1 = np.array(a["p0"], float), np.array(a["p1"], float)
        ax = (p1 - p0) / np.linalg.norm(p1 - p0)
        u = np.cross(ax, [0, 0, 1.0]); u /= np.linalg.norm(u)
        v = np.cross(ax, u)
        n, r = 10, a.get("r", 9)
        wr, ww = a.get("wheel", (24, 18))
        pts, fs = [], []
        for q in (p0, p1):
            pts += [q + r * (math.cos(2 * math.pi * j / n) * u + math.sin(2 * math.pi * j / n) * v) for j in range(n)]
        fs += [(j, (j + 1) % n, n + (j + 1) % n) for j in range(n)] + [(j, n + (j + 1) % n, n + j) for j in range(n)]
        b = len(pts)
        for zz in (p1[2] - ww / 2, p1[2] + ww / 2):          # колёсико: ось вдоль z
            pts += [(p1[0] + wr * math.cos(2 * math.pi * j / 16), p1[1] + wr * math.sin(2 * math.pi * j / 16), zz)
                    for j in range(16)]
        fs += [(b + j, b + (j + 1) % 16, b + 16 + (j + 1) % 16) for j in range(16)]
        fs += [(b + j, b + 16 + (j + 1) % 16, b + 16 + j) for j in range(16)]
        base = len(V)
        V = np.vstack([V, np.array(pts)])
        F = np.vstack([F, np.array(fs) + base])
        C = np.vstack([C, np.tile([[28, 28, 32]], (len(pts), 1)).astype(np.float32)])
        lab = np.r_[lab, np.full(len(fs), p)]
    return V, F, C, lab, names


def add_hubs(V, F, C, lab, names, wheels):
    """Ступица с мотором и батареей (как у e-motion): толстый диск на каждом заднем колесе."""
    for cx, cy, R, w in wheels:
        h = w.get("hub")
        if not h:
            continue
        if h["part"] not in names:
            names.append(h["part"])
        p = names.index(h["part"])
        for side in (-1, 1):
            zc = side * (np.mean(w["z"]) - h["w"] * 0.25)
            n = 28
            base = len(V)
            ring = []
            for z in (zc - h["w"] / 2, zc + h["w"] / 2):
                for i in range(n):
                    a = 2 * math.pi * i / n
                    ring.append((cx + h["r"] * math.cos(a), cy + h["r"] * math.sin(a), z))
            ring += [(cx, cy, zc - h["w"] / 2), (cx, cy, zc + h["w"] / 2)]
            V = np.vstack([V, ring])
            nf = []
            for i in range(n):
                j = (i + 1) % n
                nf += [(base + i, base + j, base + n + j), (base + i, base + n + j, base + n + i),
                       (base + 2 * n, base + j, base + i), (base + 2 * n + 1, base + n + i, base + n + j)]
            F = np.vstack([F, nf])
            col = np.tile([[62, 62, 70]], (len(ring), 1)).astype(np.float32)
            col[n:2 * n] = (90, 92, 104) if side > 0 else (62, 62, 70)
            C = np.vstack([C, col])
            lab = np.r_[lab, np.full(len(nf), p)]
    return V, F, C, lab, names


def make_spokes(wheels, n_spokes):
    """Ровные спицы вместо спиц Tripo (тонкие спицы при облегчении рвутся на «чёрточки»): на каждом заднем
    колесе с обеих сторон коляски — n спиц от фланцев ступицы к ободу, перекрёстная (тангенциальная) спицовка.
    Спица — трёхгранная палочка ~5 мм (тоньше в окне игры не видно). Возврат: V, F, C."""
    Vs, Fs, Cs = [], [], []
    for cx, cy, R, w in wheels:
        if w["kind"] != "spoked":
            continue
        plane = w.get("plane", float(np.mean(w["z"])))
        r0 = (w["hub"]["r"] - 8) if w.get("hub") else 32
        r1 = R - 46                                          # внутренний край обода
        for side in (-1, 1):
            for i in range(n_spokes):
                a = 2 * math.pi * i / n_spokes
                fl = -18 if i % 2 else 8                         # два фланца ступицы
                da = 0.30 if (i // 2) % 2 else -0.30           # перекрёст: спица уходит к ободу со сдвигом
                p0 = np.array([cx + r0 * math.cos(a), cy + r0 * math.sin(a), side * (plane + fl)])
                p1 = np.array([cx + r1 * math.cos(a + da), cy + r1 * math.sin(a + da), side * plane])
                d = p1 - p0
                d /= np.linalg.norm(d)
                u = np.cross(d, [0, 0, 1.0])
                u /= np.linalg.norm(u)
                v = np.cross(d, u)
                base = sum(len(x) for x in Vs)
                ring = [2.6 * (math.cos(t) * u + math.sin(t) * v) for t in (0, 2.094, 4.189)]
                Vs.append(np.array([p0 + q for q in ring] + [p1 + q for q in ring]))
                Fs.append(np.array([(base + j, base + (j + 1) % 3, base + 3 + (j + 1) % 3) for j in range(3)] +
                                   [(base + j, base + 3 + (j + 1) % 3, base + 3 + j) for j in range(3)]))
                Cs.append(np.tile([[176, 179, 186]], (6, 1)))
    if not Vs:
        return np.zeros((0, 3)), np.zeros((0, 3), np.int64), np.zeros((0, 3))
    return np.vstack(Vs), np.vstack(Fs), np.vstack(Cs).astype(float)


def to_json(V, F, C, lab, names, src):
    Cf = np.clip(C[F].mean(1), 0, 255).astype(int)
    faces = [[int(a), int(b), int(c), int(l), int(r), int(g), int(bl)]
             for (a, b, c), l, (r, g, bl) in zip(F, lab, Cf)]
    return dict(verts=[[round(float(x), 1) for x in v] for v in V], faces=faces, parts=names, cull=False, source=src)


if __name__ == "__main__":
    key = sys.argv[1]
    spec = SPECS[key]
    D = sys.argv[sys.argv.index("--dir") + 1] if "--dir" in sys.argv else "art_tests/tripo"
    d = np.load(f"{D}/{key}_full.npz")
    V, F, C = edit(d["V"], d["F"], d["C"], spec)
    if "--target" in sys.argv:                           # меньше граней для «полной» модели игры
        t = int(sys.argv[sys.argv.index("--target") + 1])
        Vs, Fs = fast_simplification.simplify(V.astype(np.float32), F.astype(np.int32), target_reduction=1 - t / len(F))
        _, idx = cKDTree(V).query(Vs, k=4)
        V, F, C = Vs.astype(float), Fs.astype(np.int64), C[idx].mean(1)
    if "--no-despike" not in sys.argv:
        V, F, C = despike(V, F, C, spec)
    lab, names, wheels = label(V, F, C, spec)
    if spec.get("recolor_frame"):                        # перекраска светлых труб рамы
        Cf = C[F].mean(1)
        lum = Cf.mean(1)
        tgt = np.array(spec["recolor_frame"], float)
        m = (lab == 0) & (lum > 70)
        for fi in np.nonzero(m)[0]:
            k = lum[fi] / 170.0
            C[F[fi]] = np.clip(tgt * k, 0, 255)
    V, F, C, lab, names = add_hubs(V, F, C, lab, names, wheels)
    # антиопрокидыватели, которых нет в модели, — после облегчения (как спицы): мелкую деталь облегчение «съедает»
    AV, AF, AC, AL, names = add_antitips(np.zeros((0, 3)), np.zeros((0, 3), np.int64), np.zeros((0, 3), np.float32),
                                         np.zeros(0, int), names, spec.get("antitips"))
    if spec.get("tilt"):
        V, F, C = tilt_seat(V, F, C, lab, names, spec["tilt"])
    SV = np.zeros((0, 3))
    if spec.get("spokes") and "spokes" in names:          # спицы Tripo -> ровные спицы (добавляются после облегчения)
        keep = lab != names.index("spokes")
        F, lab = F[keep], lab[keep]
        SV, SF, SC = make_spokes(wheels, spec["spokes"])
    np.savez_compressed(f"{D}/{key}_labels.npz", lab=lab, names=np.array(names))
    np.savez_compressed(f"{D}/{key}_labeled_mesh.npz", V=V, F=F, C=C, lab=lab, names=np.array(names))
    for cx, cy, R, w in wheels:
        print(f"  колесо {w['kind']}: центр ({cx:.0f}, {cy:.0f}) R {R:.0f}")
    cnt = np.bincount(lab, minlength=len(names))
    print("  детали:", {n: int(c) for n, c in zip(names, cnt)})
    os.makedirs(f"{D}/models", exist_ok=True)
    out = f"{D}/models/{spec['art']}_ai.json"   # в assets/ — только официальные файлы с подписки Tripo
    def with_spokes(V, F, C, lab):
        if len(AV):
            V, F, C, lab = np.vstack([V, AV]), np.vstack([F, AF + len(V)]), np.vstack([C, AC]), np.r_[lab, AL]
        if not len(SV):
            return V, F, C, lab
        return (np.vstack([V, SV]), np.vstack([F, SF + len(V)]), np.vstack([C, SC]),
                np.r_[lab, np.full(len(SF), names.index("spokes"))])
    json.dump(to_json(*with_spokes(V, F, C, lab), names, "Tripo"), open(out, "w"), separators=(",", ":"))
    # облегчённая копия для окна диагностики: детали — по ближайшей грани полной модели
    Vs, Fs = fast_simplification.simplify(V.astype(np.float32), F.astype(np.int32), target_reduction=1 - 11000 / len(F))
    Pc_full = V[F].mean(1)
    tree = cKDTree(Pc_full)
    _, fi = tree.query(Vs[Fs].mean(1))
    labs = lab[fi]
    _, vi = cKDTree(V).query(Vs, k=4)
    json.dump(to_json(*with_spokes(Vs.astype(float), Fs.astype(np.int64), C[vi].mean(1), labs), names, "Tripo"),
              open(out.replace(".json", "_lod.json"), "w"), separators=(",", ":"))
    print("  записано:", out, len(F), "граней; lod", len(Fs))
