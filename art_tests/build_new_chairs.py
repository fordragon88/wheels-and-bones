"""8 новых колясок для «Колёса и Кости» в стиле build_9_chairs.py.

Использует хелперы из build_9_chairs.py (не меняя его) и пишет
assets/models/chair_<key>_ai.json + chair_<key>_ai_lod.json для ключей:
aeroz, cross6, iris, focuscr, whillc2, f5, pulse6, q6edge.
Оси: мм, x — вперёд, y — вверх (пол y=0), z — вбок (правая сторона = +z).
"""
import math, json, os, sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_9_chairs import (  # noqa: E402
    TriMeshBuilder, _norm, add_spline_tube, add_torus, add_disc, add_rounded_box,
    add_contoured_cushion, add_contoured_backrest, add_wheel_fender, add_manual_rear_wheel,
    add_front_caster, add_wheel_brake, add_power_drive_wheel, add_power_caster, add_power_controller,
    smooth_curve,
)

GOLD = (218, 182, 92)


# --------------------------------------------------------------------------- #
# Extra helpers
# --------------------------------------------------------------------------- #
def add_cyl(b, p0, p1, r, part, col, sides=8):
    add_spline_tube(b, [p0, p1], r, part, col, sides=sides, smooth=0, caps=True)


def add_obox(b, center, u, v, hu, hv, hw, part, col):
    """Box with arbitrary orientation: u, v given; w = u x v."""
    c = np.asarray(center, float)
    u = _norm(u)
    v = _norm(np.asarray(v, float) - np.dot(v, u) * u)
    w = np.cross(u, v)
    idx = {}
    for i in (-1, 1):
        for j in (-1, 1):
            for k in (-1, 1):
                idx[(i, j, k)] = b.v(c + u * hu * i + v * hv * j + w * hw * k)
    for q in (((-1, -1, -1), (-1, 1, -1), (1, 1, -1), (1, -1, -1)),
              ((-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)),
              ((-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)),
              ((-1, 1, -1), (-1, 1, 1), (1, 1, 1), (1, 1, -1)),
              ((-1, -1, -1), (-1, -1, 1), (-1, 1, 1), (-1, 1, -1)),
              ((1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1))):
        b.poly([idx[t] for t in q], part, col)


def add_profile_tube(b, pts, a, bz, part, col, sides=12, power=0.55, smooth=2, caps=True, z_axis=(0, 0, 1)):
    """Sweep of a rounded-rectangle (superellipse) profile along a path lying in a plane
    perpendicular to z_axis (default: path in the x/y side plane). a = half-size in-plane
    (perpendicular to path), bz = half-size along z_axis. a / bz may be [start, end] lists."""
    sides = b.segs(sides, 8)
    path = smooth_curve(pts, smooth) if smooth > 0 and len(pts) > 2 else [np.asarray(p, float) for p in pts]
    n = len(path)
    W = _norm(z_axis)
    rings = []
    for i, p in enumerate(path):
        if i == 0:
            t = path[1] - path[0]
        elif i == n - 1:
            t = path[-1] - path[-2]
        else:
            t = path[i + 1] - path[i - 1]
        t = _norm(t - np.dot(t, W) * W)
        U = np.cross(W, t)
        f = i / max(1, n - 1)
        aa = a[0] * (1 - f) + a[-1] * f if isinstance(a, (list, tuple)) else a
        bb = bz[0] * (1 - f) + bz[-1] * f if isinstance(bz, (list, tuple)) else bz
        ring = []
        for k in range(sides):
            ang = 2 * math.pi * (k + 0.5) / sides
            ca, sa = math.cos(ang), math.sin(ang)
            cu = math.copysign(abs(ca) ** power, ca)
            sw = math.copysign(abs(sa) ** power, sa)
            ring.append(b.v(p + U * aa * cu + W * bb * sw))
        rings.append(ring)
    for i in range(n - 1):
        R0, R1 = rings[i], rings[i + 1]
        for k in range(sides):
            kk = (k + 1) % sides
            b.quad(R0[k], R0[kk], R1[kk], R1[k], part, col)
    if caps:
        b.poly(list(reversed(rings[0])), part, col)
        b.poly(rings[-1], part, col)


def add_small_wheel(b, cx, cy, z, R, part, tire_col=(36, 38, 44), hub_col=(170, 176, 188), width=12.0):
    add_torus(b, (cx, cy, z), R - width * 0.5, width * 0.5, part, tire_col, segs=16, sides=5, z_scale=1.4)
    add_cyl(b, (cx, cy, z - width), (cx, cy, z + width), R * 0.45, part, hub_col, sides=8)


def add_coil_spring(b, p0, p1, r_coil, r_wire, turns, part, col):
    p0 = np.asarray(p0, float)
    p1 = np.asarray(p1, float)
    ax = _norm(p1 - p0)
    ref = np.array([1.0, 0, 0]) if abs(ax[0]) < 0.9 else np.array([0, 0, 1.0])
    u = _norm(np.cross(ax, ref))
    w = np.cross(ax, u)
    n = max(10, int(turns * b.segs(6, 5)))
    L = np.linalg.norm(p1 - p0)
    pts = []
    for i in range(n + 1):
        t = i / n
        a = 2 * math.pi * turns * t
        pts.append(p0 + ax * L * t + (u * math.cos(a) + w * math.sin(a)) * r_coil)
    add_spline_tube(b, pts, r_wire, part, col, sides=5, smooth=0, caps=False)


def add_gear(b, cx, cy, z0, z1, R, teeth, part, col, tooth_col=None):
    """Toothed cog with its axis along z."""
    add_cyl(b, (cx, cy, z0), (cx, cy, z1), R, part, col, sides=16)
    zc, hw = (z0 + z1) * 0.5, abs(z1 - z0) * 0.5
    for i in range(b.segs(teeth, 10)):
        a = 2 * math.pi * i / b.segs(teeth, 10)
        u = (math.cos(a), math.sin(a), 0.0)
        add_obox(b, (cx + (R + 5.0) * u[0], cy + (R + 5.0) * u[1], zc), u, (0, 0, 1), 6.0, hw, 4.0,
                 part, tooth_col or col)
    add_cyl(b, (cx, cy, z0 - 4.0 * np.sign(z1 - z0)), (cx, cy, z1 + 4.0 * np.sign(z1 - z0)), R * 0.32, part, (60, 62, 70), sides=8)


def add_drive_wheel_lugged(b, cx, cy, z, R, rim_col, tire_col, hub_col, n_spokes=3, lugs=34, tire_part="tire",
                           hub_part="axle", width=1.15):
    """Power-chair drive wheel with knobby tread lugs and a Y-spoke rim (tyre is its own part)."""
    sgn = 1 if z > 0 else -1
    add_torus(b, (cx, cy, z), R - 32.0, 32.0, tire_part, tire_col, segs=32, sides=9, z_scale=width)
    nl = b.segs(lugs, 18)
    for i in range(nl):
        a = 2 * math.pi * (i + 0.5) / nl
        u = (math.cos(a), math.sin(a), 0.0)
        for zz in ((-14.0, 10.0) if i % 2 == 0 else (14.0, 10.0),):
            off, hz = zz
            add_obox(b, (cx + (R - 6.0) * u[0], cy + (R - 6.0) * u[1], z + off), u, (0, 0, 1), 5.0, 16.0, 7.0,
                     tire_part, tuple(c + 6 for c in tire_col))
    r_rim = R - 60.0
    add_torus(b, (cx, cy, z + 16.0 * sgn), r_rim, 9.0, hub_part, rim_col, segs=26, sides=6)
    add_disc(b, cx, cy, z + 6.0 * sgn, r_rim - 4.0, hub_part, (40, 42, 50), segs=20)
    add_cyl(b, (cx, cy, z + 12.0 * sgn), (cx, cy, z + 26.0 * sgn), 30.0, hub_part, hub_col, sides=12)
    for i in range(n_spokes):
        a = 2 * math.pi * i / n_spokes + math.pi / 2
        for d in (-0.16, 0.16):
            p0 = (cx + 22.0 * math.cos(a), cy + 22.0 * math.sin(a), z + 22.0 * sgn)
            p1 = (cx + (r_rim - 2.0) * math.cos(a + d), cy + (r_rim - 2.0) * math.sin(a + d), z + 20.0 * sgn)
            add_spline_tube(b, [p0, p1], [17.0, 12.0], hub_part, rim_col, sides=6, smooth=0, caps=True)
    add_cyl(b, (cx, cy, z + 24.0 * sgn), (cx, cy, z + 31.0 * sgn), 13.0, hub_part, (44, 46, 54), sides=10)


def add_omni_wheel(b, cx, cy, z, R, roller_part, hub_part, roller_col=(150, 154, 162),
                   hub_col=(64, 66, 74), cover_col=(226, 228, 232), n_rollers=24):
    n = b.segs(n_rollers, 16)
    rr = 15.0
    Rc = R - rr
    for i in range(n):
        a = 2 * math.pi * i / n
        ca, sa = math.cos(a), math.sin(a)
        t = np.array([-sa, ca, 0.0])
        c = np.array([cx + Rc * ca, cy + Rc * sa, z + (9.0 if i % 2 else -9.0)])
        L = math.pi * Rc / n * 1.05
        pts = [c - t * L, c - t * L * 0.45, c + t * L * 0.45, c + t * L]
        add_spline_tube(b, pts, [7.0, 14.0, 14.0, 7.0], roller_part, roller_col, sides=6, smooth=0, caps=True)
        # roller axle bracket
        add_obox(b, (cx + (Rc - 18.0) * ca, cy + (Rc - 18.0) * sa, z), (ca, sa, 0), t, 8.0, 4.0, 22.0,
                 hub_part, hub_col)
    add_cyl(b, (cx, cy, z - 26.0), (cx, cy, z + 26.0), Rc - 22.0, hub_part, hub_col, sides=18)
    sgn = 1 if z > 0 else -1
    add_disc(b, cx, cy, z + 28.0 * sgn, Rc - 34.0, hub_part, cover_col, segs=18)
    for i in range(5):
        a = 2 * math.pi * i / 5 + 0.3
        add_cyl(b, (cx + 42.0 * math.cos(a), cy + 42.0 * math.sin(a), z + 27.0 * sgn),
                (cx + 42.0 * math.cos(a), cy + 42.0 * math.sin(a), z + 33.0 * sgn), 6.0, hub_part, (120, 124, 132), sides=6)


def add_anti_tip(b, p_start, p_mid, p_end, z, col, wheel_R=26.0, tube_r=11.0):
    add_spline_tube(b, [(p_start[0], p_start[1], z), (p_mid[0], p_mid[1], z), (p_end[0], p_end[1], z)],
                    tube_r, "anti_tip", col, sides=6, smooth=1)
    ex, ey = p_end
    add_small_wheel(b, ex - 6.0, ey - wheel_R * 0.9, z, wheel_R, "anti_tip", hub_col=(150, 156, 166), width=12.0)
    add_cyl(b, (ex, ey + 6.0, z - 8.0), (ex, ey + 6.0, z + 8.0), tube_r + 3.0, "anti_tip", (60, 62, 70), sides=6)


def add_hex_nut(b, x, y, z, sgn, size=9.5, length=11.0, part="bolts", col=GOLD):
    add_spline_tube(b, [(x, y, z), (x, y, z + length * sgn)], size, part, col, sides=6, smooth=0, caps=True)


def add_mwd_drivetrain(b, x, y, W, s, motor_col, brake_col=(46, 48, 56), lever_col=(236, 198, 52),
                       brushes=True, cap_col=(30, 32, 38)):
    """Transverse mid-wheel-drive motor: gearbox at wheel, motor body, electromagnetic brake at inner end,
    carbon-brush caps on the housing and the freewheel lever on the brake."""
    z_gear0, z_gear1 = (W - 95.0) * s, (W - 55.0) * s
    z_mot0 = 108.0 * s
    z_brk0 = 66.0 * s
    add_cyl(b, (x, y, z_gear0), (x, y, z_gear1), 60.0, "motor", tuple(int(c * 0.85) for c in motor_col), sides=12)
    add_cyl(b, (x, y, z_mot0), (x, y, z_gear0), 50.0, "motor", motor_col, sides=12)
    for zr in np.linspace(z_mot0 + 18.0 * s, z_gear0 - 18.0 * s, 2):
        add_torus(b, (x, y, zr), 50.0, 3.2, "motor", tuple(min(255, c + 22) for c in motor_col), segs=18, sides=4)
    # electromagnetic brake (inner end)
    add_cyl(b, (x, y, z_brk0), (x, y, z_mot0), 46.0, "mag_brake", brake_col, sides=12)
    add_disc(b, x, y, z_brk0 - 1.0 * s, 40.0, "mag_brake", (88, 92, 102), segs=14)
    add_cyl(b, (x, y, z_brk0 - 2.0 * s), (x, y, z_brk0 - 16.0 * s), 16.0, "mag_brake", (150, 156, 168), sides=8)
    # brush caps on the motor housing (top + back)
    if brushes:
        zc = (z_mot0 + z_gear0) * 0.5
        for ang in (math.pi * 0.5, math.pi * 0.95):
            ca, sa = math.cos(ang), math.sin(ang)
            add_cyl(b, (x + 44.0 * ca, y + 44.0 * sa, zc), (x + 64.0 * ca, y + 64.0 * sa, zc), 13.0, "brushes", cap_col, sides=8)
            add_cyl(b, (x + 62.0 * ca, y + 62.0 * sa, zc), (x + 70.0 * ca, y + 70.0 * sa, zc), 15.5, "brushes", cap_col, sides=8)
    # freewheel lever on top of the brake
    add_cyl(b, (x, y + 44.0, (z_brk0 + z_mot0) * 0.5), (x - 42.0, y + 128.0, (z_brk0 + z_mot0) * 0.5), 8.0,
            "freewheel", lever_col, sides=6)
    add_cyl(b, (x - 40.0, y + 122.0, (z_brk0 + z_mot0) * 0.5), (x - 50.0, y + 148.0, (z_brk0 + z_mot0) * 0.5), 14.0,
            "freewheel", lever_col, sides=8)


def add_padded_armrest(b, x0, x1, y0, y1, z, half_w, col, trim, part="frame"):
    add_rounded_box(b, x0, x1, y0, y1, z - half_w, z + half_w, part, col, top_col=trim, bevel=9.0)


# --------------------------------------------------------------------------- #
# 1. TiLite Aero Z (aeroz) — rigid titanium active chair
# --------------------------------------------------------------------------- #
def build_aeroz(lod=1.0):
    """TiLite Aero Z as drawn in the art: warm-silver frame, tall black back with vertical push-handle grips,
    loop armrests with pads, black side guards over the wheels, 24-spoke wheels, long legrest hangers."""
    b = TriMeshBuilder(lod)
    TI = (172, 164, 162)
    TI_D = (138, 132, 132)
    TIRE = (54, 52, 55)
    UPH = (46, 44, 49)
    UPH_T = (62, 60, 66)
    GUARD = (38, 37, 41)
    zf_abs = 212.0
    zw_abs = 262.0
    wx = 34.0
    wR = 306.0
    wy = wR
    ya = 739.5               # armrest tube height
    yt = 1040.0              # push grip top
    xcs = 364.0              # caster axle ahead of the rear axle
    fpx = 590.0              # footplate start ahead of the rear axle
    ytc = 606.0              # cushion top
    xp = wx - 78.0           # back post
    xf = wx + 412.0          # front frame / caster housing
    y_rail = 442.0           # seat rail
    y_low = 266.0            # lower side rail

    for s in (-1, 1):
        zf, zw = zf_abs * s, zw_abs * s
        add_manual_rear_wheel(b, wx, wy, zw, wR, style="wire", rim_col=(150, 146, 146), pushrim_col=(186, 180, 178),
                              hub_col=(120, 116, 116), tire_col=TIRE, spoke_col=(212, 210, 210), n_spokes=28)
        # back post (vertical) with black push-handle grip on top
        add_spline_tube(b, [(xp, y_low, zf), (xp, 600.0, zf), (xp - 2.0, 890.0, zf)], 13.0, "frame", TI, sides=9, smooth=1)
        add_spline_tube(b, [(xp - 2.0, 878.0, zf), (xp - 3.0, yt, zf)], 17.5, "frame", (40, 40, 44), sides=9, smooth=0)
        add_rounded_box(b, xp - 16.0, xp + 16.0, 860.0, 884.0, zf - 18.0, zf + 18.0, "frame", (52, 52, 56), bevel=4.0)
        # seat rail + lower rail into the front frame
        add_spline_tube(b, [(xp, y_rail, zf), (xf - 30.0, y_rail, zf), (xf, y_rail + 18.0, zf), (xf + 4.0, y_rail + 26.0, zf)],
                        12.5, "frame", TI, sides=9, smooth=1)
        add_spline_tube(b, [(xp, y_low, zf), (xf, y_low, zf)], 12.0, "frame", TI, sides=8, smooth=0)
        add_spline_tube(b, [(xf, y_rail + 26.0, zf), (xf, 236.0, zf)], 13.5, "frame", TI, sides=9, smooth=0)
        # axle plate / camber clamp
        add_rounded_box(b, wx - 34.0, wx + 36.0, wy - 28.0, wy + 40.0, zf + 4.0 * s, (zw_abs - 62.0) * s,
                        "frame", TI_D, bevel=5.0)
        add_spline_tube(b, [(wx, wy, zf), (wx, y_low, zf)], 10.0, "frame", TI_D, sides=7, smooth=0)
        # caster
        add_front_caster(b, wx + xcs, 82.0, zf, 82.0, (xf, 236.0), fork_col=TI, tire_col=(44, 42, 46),
                         hub_col=(150, 146, 146), n_spokes=5, three_window=False)
        # loop armrest: from back post forward, rounded bend down to the seat rail; black pad on top
        za = zf + 6.0 * s
        add_spline_tube(b, [(xp, ya, za), (wx + 300.0, ya, za), (wx + 330.0, ya - 4.0, za), (wx + 342.0, ya - 32.0, za),
                            (wx + 344.0, y_rail + 10.0, za)], 11.5, "frame", TI, sides=8, smooth=2)
        add_padded_armrest(b, wx - 22.0, wx + 312.0, ya + 10.0, ya + 44.0, za, 24.0, UPH, UPH_T)
        add_rounded_box(b, wx + 40.0, wx + 90.0, ya, ya + 12.0, za - 10.0, za + 10.0, "frame", TI_D, bevel=2.0)
        # black side guard over the wheel
        add_wheel_fender(b, wx, wy, (zf_abs + 12.0) * s, s, wR + 18.0, 38.0, 106.0, 26.0, y_rail + 10.0, GUARD,
                         edge_col=(56, 54, 58), part="frame")
        # legrest hanger and footplate
        add_rounded_box(b, xf - 14.0, xf + 22.0, y_rail - 8.0, y_rail + 30.0, zf - 17.0, zf + 17.0, "footrest", TI_D, bevel=4.0)
        add_spline_tube(b, [(xf + 6.0, y_rail + 14.0, zf * 0.98), (wx + 470.0, y_rail - 2.0, zf * 0.96),
                            (wx + 500.0, 420.0, zf * 0.94), (wx + 580.0, 180.0, zf * 0.88), (wx + 598.0, 100.0, zf * 0.86)],
                        12.0, "footrest", TI, sides=8, smooth=2)
        add_spline_tube(b, [(wx + 470.0, 300.0, zf * 0.92), (wx + 520.0, 300.0, zf * 0.91)], 9.0, "footrest", TI, sides=6, smooth=0)
        za0, zb0 = sorted([24.0 * s, zf_abs * 0.86 * s])
        add_rounded_box(b, wx + fpx, wx + fpx + 162.0, 70.0, 98.0, za0, zb0, "footrest", (52, 50, 54), bevel=6.0)
        # wheel lock on the seat rail
        add_wheel_brake(b, wx + 318.0, y_rail - 18.0, (zf_abs + 18.0) * s, s, col_clamp=(58, 56, 60), col_knob=(44, 42, 46))
        # anti-tip tube (kept inside the wheel silhouette)
        add_anti_tip(b, (xp, y_low), (wx - 140.0, 200.0), (wx - 184.0, 96.0), (zf_abs - 8.0) * s, TI, wheel_R=24.0, tube_r=10.0)
        # bolts
        for bx, by in ((wx - 16.0, wy + 26.0), (wx + 20.0, wy + 26.0), (wx - 16.0, wy - 14.0), (wx + 20.0, wy - 14.0)):
            add_hex_nut(b, bx, by, (zw_abs - 62.0) * s, s, size=8.5, length=9.0)
        for bx, by in ((xf, 300.0), (xp, 760.0), (xp, y_rail)):
            add_hex_nut(b, bx, by, zf + 13.0 * s, s, size=8.0, length=8.0)
    # cross tubes
    add_cyl(b, (wx + 2.0, wy + 2.0, -zf_abs), (wx + 2.0, wy + 2.0, zf_abs), 15.0, "frame", TI_D, sides=10)
    add_cyl(b, (xp, 640.0, -zf_abs), (xp, 640.0, zf_abs), 9.0, "frame", TI, sides=8)
    add_cyl(b, (xf, y_low, -zf_abs), (xf, y_low, zf_abs), 11.0, "frame", TI, sides=8)
    # sling + thick cushion + tall contoured back (lumbar bulge low)
    add_rounded_box(b, xp + 6.0, xf - 6.0, y_rail + 10.0, y_rail + 26.0, -zf_abs + 12.0, zf_abs - 12.0, "seat", UPH_T, bevel=4.0)
    add_contoured_cushion(b, xp + 14.0, xf + 30.0, y_rail + 24.0, ytc, -zf_abs + 6.0, zf_abs - 6.0,
                          "cushion", UPH, trim_col=UPH_T, bolster=12.0, ribs=0)
    add_contoured_backrest(b, xp + 20.0, xp - 8.0, 600.0, yt - 16.0, -zf_abs + 8.0, zf_abs - 8.0,
                           44.0, "seat", UPH, trim_col=UPH_T, bolster=3.0, ribs=0)
    add_contoured_backrest(b, xp + 78.0, xp + 30.0, 600.0, 820.0, -zf_abs + 20.0, zf_abs - 20.0,
                           64.0, "seat", UPH, trim_col=UPH_T, bolster=10.0, ribs=0)
    # dark under-seat sling pouch seen through the spokes
    add_rounded_box(b, xp - 14.0, wx + 300.0, 330.0, y_rail + 12.0, -zf_abs + 18.0, zf_abs - 18.0, "seat", (40, 39, 43), bevel=14.0)
    return b


# --------------------------------------------------------------------------- #
# 2. Etac Cross 6 (cross6) — folding cross-brace chair
# --------------------------------------------------------------------------- #
def build_cross6(lod=1.0):
    """Etac Cross 6 as drawn: light-grey frame and upholstery, tall push handles bent back with dark grips,
    padded flip-up armrests over dark side-guard panels, vertical legrest hangers, two big footplates."""
    b = TriMeshBuilder(lod)
    GR = (142, 140, 140)
    GR_D = (104, 102, 104)
    UPH = (128, 126, 125)
    UPH_B = (104, 103, 104)
    UPH_T = (88, 87, 89)
    PANEL = (60, 60, 64)
    TIRE = (40, 40, 44)
    zf_abs = 236.0
    zw_abs = 286.0
    wx = 80.0
    wR = 330.0
    wy = wR
    ya = 728.0               # armrest pad bottom
    yh = 1030.0              # push handle height
    yu = 875.0               # back upholstery top
    xp = wx - 84.0
    y_rail = 436.0

    for s in (-1, 1):
        zf, zw = zf_abs * s, zw_abs * s
        add_manual_rear_wheel(b, wx, wy, zw, wR, style="wire", rim_col=(178, 178, 182), pushrim_col=(196, 196, 200),
                              hub_col=(150, 150, 156), tire_col=TIRE, spoke_col=(200, 200, 206), n_spokes=36)
        # rear lower post (frame) + back post with push handle (backrest)
        add_spline_tube(b, [(xp, 300.0, zf), (xp, y_rail + 2.0, zf)], 12.5, "frame", GR, sides=8, smooth=0)
        add_spline_tube(b, [
            (xp, y_rail, zf),
            (xp - 16.0, 760.0, zf),
            (xp - 80.0, yh - 40.0, zf),
            (xp - 104.0, yh - 8.0, zf),
            (xp - 150.0, yh, zf),
        ], 12.5, "backrest", GR, sides=8, smooth=2)
        add_spline_tube(b, [(xp - 128.0, yh, zf), (xp - 208.0, yh + 3.0, zf)], 17.0, "backrest", (78, 78, 80), sides=8, smooth=0)
        add_rounded_box(b, xp - 22.0, xp + 8.0, 700.0, 770.0, zf - 15.0, zf + 15.0, "backrest", GR_D, bevel=4.0)
        # seat rail down to caster housing, lower rail
        add_spline_tube(b, [(xp, y_rail, zf), (414.0, y_rail, zf), (434.0, y_rail - 18.0, zf), (440.0, 268.0, zf)],
                        12.5, "frame", GR, sides=8, smooth=2)
        add_spline_tube(b, [(xp, 322.0, zf), (440.0, 322.0, zf)], 12.0, "frame", GR, sides=8, smooth=0)
        # axle mount plate with 13 mm nuts
        add_rounded_box(b, wx - 58.0, wx + 40.0, wy - 34.0, wy + 50.0, zf - 8.0 * s, zf + 16.0 * s, "frame", GR_D, bevel=5.0)
        for bx, by in ((wx - 36.0, wy + 30.0), (wx + 18.0, wy + 30.0), (wx - 36.0, wy - 18.0), (wx + 18.0, wy - 18.0)):
            add_hex_nut(b, bx, by, zf + 16.0 * s, s, size=10.0, length=10.0)
        add_cyl(b, (wx, wy, zf), (wx, wy, zw - 30.0 * s), 14.0, "frame", (170, 170, 176), sides=8)
        # flip-up armrest: dark side-guard panel + two posts + padded top
        za = zf + 16.0 * s
        add_rounded_box(b, xp + 4.0, wx + 236.0, y_rail - 70.0, ya - 20.0, za - 4.0, za + 4.0, "frame", PANEL, bevel=3.0)
        add_spline_tube(b, [(xp + 2.0, ya + 7.0, za), (xp + 2.0, y_rail, za)], 10.0, "frame", GR, sides=6, smooth=0)
        add_spline_tube(b, [(wx + 230.0, ya + 7.0, za), (wx + 230.0, y_rail, za)], 10.0, "frame", GR, sides=6, smooth=0)
        add_rounded_box(b, xp - 6.0, wx + 268.0, ya, ya + 34.0, za - 24.0, za + 24.0, "frame",
                        (52, 52, 56), top_col=(66, 66, 70), bevel=10.0)
        # legrest: hanger almost vertical from the seat front down to a big footplate
        add_rounded_box(b, 422.0, 456.0, y_rail - 30.0, y_rail + 8.0, zf - 18.0, zf + 18.0, "footrest", GR_D, bevel=5.0)
        add_spline_tube(b, [(442.0, y_rail - 10.0, zf), (470.0, 380.0, zf * 0.97), (500.0, 200.0, zf * 0.93),
                            (508.0, 128.0, zf * 0.92)], 12.0, "footrest", GR, sides=8, smooth=2)
        za0, zb0 = sorted([16.0 * s, zf_abs * 0.94 * s])
        add_rounded_box(b, 500.0, 680.0, 98.0, 120.0, za0, zb0, "footrest", (56, 56, 60), top_col=(72, 72, 76), bevel=5.0)
        add_cyl(b, (510.0, 122.0, zf * 0.92 - 16.0), (510.0, 122.0, zf * 0.92 + 16.0), 15.0, "footrest", GR_D, sides=8)
        # caster + brake
        add_front_caster(b, 432.0, 74.0, (zf_abs - 2.0) * s, 74.0, (440.0, 268.0), fork_col=GR, tire_col=TIRE,
                         hub_col=(120, 120, 126), n_spokes=5, three_window=True)
        add_wheel_brake(b, wx + 222.0, y_rail, (zf_abs + 20.0) * s, s, col_clamp=GR_D, col_knob=(70, 70, 74))
        # anti-tip
        add_anti_tip(b, (xp, 322.0), (wx - 118.0, 230.0), (wx - 166.0, 96.0), (zf_abs - 10.0) * s, GR)
        for bx, by in ((440.0, 322.0), (440.0, 470.0)):
            add_hex_nut(b, bx, by, zf + 12.0 * s, s, size=8.0, length=9.0)
    # cross brace
    for s in (-1, 1):
        add_spline_tube(b, [(200.0, 326.0, -zf_abs * s), (232.0, y_rail + 26.5, (zf_abs - 26.0) * s)], 11.0, "frame", GR, sides=8, smooth=0)
        add_spline_tube(b, [(xp + 14.0, y_rail + 34.5, (zf_abs - 26.0) * s), (420.0, y_rail + 34.5, (zf_abs - 26.0) * s)], 11.0, "frame", GR, sides=8, smooth=0)
    add_spline_tube(b, [(196.0, 408.0, 0.0), (238.0, 408.0, 0.0)], 11.0, "bolts", GOLD, sides=6, smooth=0)
    # front cross bar under the seat front (between the legrest receivers)
    add_cyl(b, (446.0, y_rail - 40.0, -zf_abs), (446.0, y_rail - 40.0, zf_abs), 13.0, "frame", GR, sides=8)
    # upholstery: grey sling seat with cushion, tall grey back
    add_rounded_box(b, xp + 18.0, 420.0, y_rail + 6.0, y_rail + 22.0, -zf_abs + 10.0, zf_abs - 10.0, "seat", UPH_T, bevel=4.0)
    add_contoured_cushion(b, xp + 24.0, 424.0, y_rail + 18.0, y_rail + 60.0, -zf_abs + 12.0, zf_abs - 12.0, "cushion", UPH,
                          trim_col=UPH_T, bolster=8.0, ribs=0)
    add_contoured_backrest(b, xp + 0.0, xp - 30.0, y_rail + 40.0, yu, -zf_abs + 10.0, zf_abs - 10.0, 26.0, "backrest",
                           UPH_B, trim_col=UPH_T, bolster=8.0, ribs=2)
    return b


# --------------------------------------------------------------------------- #
# Tilt-in-space shared bits
# --------------------------------------------------------------------------- #
def _arc_pts(cx, cy, R, x0, x1, n=9):
    pts = []
    for i in range(n):
        x = x0 + (x1 - x0) * i / (n - 1)
        pts.append((x, cy - math.sqrt(max(0.0, R * R - (x - cx) ** 2))))
    return pts


# --------------------------------------------------------------------------- #
# 3. Quickie / Zippie Iris (iris) — pediatric tilt-in-space
# --------------------------------------------------------------------------- #
def add_transit_wheel(b, cx, cy, z, R, tire_col=(40, 40, 44), mag_col=(46, 46, 52), hub_col=(70, 72, 80), n_spokes=3,
                      disc=True, spoke_w=17.0, disc_col=(30, 30, 34)):
    """Attendant / transit wheel: solid tread tyre, 3-spoke composite mag, optional recessed dark disc
    (without it the hub flange carries the rear_wheel label)."""
    sgn = 1 if z > 0 else -1
    add_torus(b, (cx, cy, z), R - 22.0, 22.0, "tire", tire_col, segs=30, sides=8, z_scale=1.2,
              inner=("tube", (60, 60, 66)))
    add_torus(b, (cx, cy, z), R - 46.0, 8.0, "rim", mag_col, segs=26, sides=6, z_scale=1.4)
    if disc:
        add_disc(b, cx, cy, z - 4.0 * sgn, R - 48.0, "rear_wheel", disc_col, segs=20)
    else:
        add_torus(b, (cx, cy, z + 8.0 * sgn), 34.0, 8.0, "rear_wheel", mag_col, segs=16, sides=5)
    for i in range(n_spokes):
        a = 2 * math.pi * i / n_spokes + 0.5
        ca, sa = math.cos(a), math.sin(a)
        add_spline_tube(b, [(cx + 20.0 * ca, cy + 20.0 * sa, z + 6.0 * sgn),
                            (cx + (R - 50.0) * ca, cy + (R - 50.0) * sa, z + 4.0 * sgn)],
                        [spoke_w, spoke_w * 0.7], "spokes", mag_col, sides=6, smooth=0, caps=True)
    add_cyl(b, (cx, cy, z - 22.0), (cx, cy, z + 22.0), 24.0, "axle", hub_col, sides=10)
    for fz in (z - 25.0, z + 25.0):
        add_torus(b, (cx, cy, fz), 14.0, 5.0, "bearing", (218, 182, 92), segs=12, sides=5)
    add_cyl(b, (cx, cy, z - 40.0 * sgn), (cx, cy, z + 30.0 * sgn), 8.0, "axle", (160, 164, 176), sides=8)


def _tilt_verts(b, i0, pivot, ang_deg):
    """Rotate every vertex added since index i0 about pivot (x, y) in the side plane (tilt-in-space)."""
    a = math.radians(ang_deg)
    ca, sa = math.cos(a), math.sin(a)
    px, py = pivot
    for i in range(i0, len(b.verts)):
        x, y, z = b.verts[i]
        dx, dy = x - px, y - py
        b.verts[i] = (round(px + dx * ca - dy * sa, 1), round(py + dx * sa + dy * ca, 1), z)


def build_iris(lod=1.0, tilt=14.0):
    """Quickie Iris as drawn: purple frame, small 12" 3-spoke transit rear wheels, curved rocker rails under
    the seat (seat shown tilted back a little), black cushion / tall rounded back / headrest, T-armrests with
    side guards, curved push handles with grips and tilt triggers, looped front hangers, one flip footplate."""
    b = TriMeshBuilder(lod)
    PURPLE = (118, 64, 170)
    PURPLE_D = (90, 50, 132)
    BLACK = (36, 36, 40)
    PAD = (48, 47, 52)
    PAD_T = (64, 63, 68)
    TIRE = (40, 40, 44)
    zf_abs = 172.0
    wx = -70.0
    wR = 166.0
    wz = 284.5
    y_base = 236.0
    y_seat = 400.0
    arc_c, arc_R = (70.0, 512.0), 292.0     # rocker circle (concave up)
    xb = -58.0                               # back post foot
    lx, ly = 70.0, arc_c[1] - arc_R          # rocker lock
    xc = 200.0                               # front caster axle
    fx = -30.0                                 # footplate offset fwd
    fy = 30.0                                 # footplate offset up
    hr = 90.0                               # headrest half width
    ya = 606.0                               # armrest pad bottom
    hy = 70.0                                # hanger loop rise above the seat rail
    bt = 0.0                                 # backrest / headrest height offset
    ph = 0.0                                 # push handle height offset
    cz = -20.0                                 # caster track offset

    # ---- base: wheels, side rails, casters, rocker rollers, brake, anti-tip
    for s in (-1, 1):
        zf = zf_abs * s
        add_transit_wheel(b, wx, wR, wz * s, wR, tire_col=TIRE)
        add_rounded_box(b, wx - 30.0, wx + 40.0, wR - 30.0, y_base + 18.0, zf, (wz - 34.0) * s, "frame", PURPLE_D, bevel=5.0)
        add_spline_tube(b, [(wx - 40.0, y_base, zf), (xc + 30.0, y_base, zf)], 14.0, "frame", PURPLE, sides=8, smooth=0)
        add_rounded_box(b, xc + 12.0, xc + 52.0, y_base - 20.0, y_base + 70.0, zf - 18.0, zf + 18.0, "frame", (52, 50, 58), bevel=5.0)
        add_front_caster(b, xc, 72.0, zf + cz * s, 72.0, (xc + 32.0, y_base + 40.0), fork_col=(150, 152, 160), tire_col=TIRE,
                         hub_col=(56, 56, 62), n_spokes=5, three_window=True)
        for rx in (-40.0, 200.0):
            ry = arc_c[1] - math.sqrt(arc_R ** 2 - (rx - arc_c[0]) ** 2) - 22.0
            add_spline_tube(b, [(rx, y_base, zf), (rx, ry, zf)], 11.0, "frame", PURPLE, sides=7, smooth=0)
            add_cyl(b, (rx, ry, zf - 20.0 * s), (rx, ry, zf + 20.0 * s), 17.0, "frame", (50, 50, 56), sides=10)
        add_wheel_brake(b, wx + 120.0, y_base + 10.0, (wz - 40.0) * s, s, col_clamp=(52, 52, 58), col_knob=(50, 50, 56))
        add_anti_tip(b, (wx - 30.0, y_base), (wx - 120.0, 150.0), (wx - 190.0, 64.0), (zf_abs - 30.0) * s, PURPLE,
                     wheel_R=26.0, tube_r=10.0)
        for bx, by in ((wx - 10.0, wR + 12.0), (wx + 22.0, wR + 12.0), (xc + 32.0, y_base + 10.0)):
            add_hex_nut(b, bx, by, zf + 13.0 * s, s, size=7.5, length=8.0)
    add_cyl(b, (wx + 10.0, y_base, -zf_abs), (wx + 10.0, y_base, zf_abs), 13.0, "frame", PURPLE, sides=8)
    add_cyl(b, (xc, y_base, -zf_abs), (xc, y_base, zf_abs), 13.0, "frame", PURPLE, sides=8)
    # central gas tilt lock between base and seat frame
    add_cyl(b, (230.0, y_base + 12.0, 0.0), (120.0, 320.0, 0.0), 19.0, "tilt_lock", (46, 48, 56), sides=10)
    add_rounded_box(b, 106.0, 136.0, 306.0, 336.0, -24.0, 24.0, "tilt_lock", (58, 60, 68), bevel=4.0)
    add_cyl(b, (230.0, y_base + 12.0, -20.0), (230.0, y_base + 12.0, 20.0), 10.0, "tilt_lock", GOLD, sides=6)

    # ---- seat assembly on the rockers (tilted back about the rocker centre at the end)
    i_seat = len(b.verts)
    add_cyl(b, (120.0, 320.0, 0.0), (40.0, y_seat - 26.0, 0.0), 8.0, "tilt_lock", (196, 202, 214), sides=8)
    for s in (-1, 1):
        zf = zf_abs * s
        arc = _arc_pts(arc_c[0], arc_c[1], arc_R, -205.0, 318.0, 13)
        add_profile_tube(b, [(x, y, zf + 6.0 * s) for x, y in arc], 17.0, 14.0, "frame", PURPLE, sides=10, smooth=0)
        add_spline_tube(b, [(arc[-1][0], arc[-1][1], zf), (300.0, y_seat - 16.0, zf)], 13.0, "frame", PURPLE, sides=8, smooth=0)
        add_spline_tube(b, [(arc[0][0], arc[0][1], zf), (xb - 30.0, y_seat + 10.0, zf)], 13.0, "frame", PURPLE, sides=8, smooth=0)
        add_rounded_box(b, lx - 34.0, lx + 34.0, ly - 24.0, ly + 36.0, zf - 18.0, zf + 18.0, "tilt_lock", (54, 54, 60), bevel=5.0)
        add_cyl(b, (lx, ly + 8.0, zf + 18.0 * s), (lx, ly + 8.0, zf + 34.0 * s), 9.0, "tilt_lock", (180, 186, 198), sides=8)
        add_spline_tube(b, [(xb - 20.0, y_seat - 16.0, zf), (330.0, y_seat - 16.0, zf)], 12.5, "frame", PURPLE, sides=8, smooth=0)
        # back post and curved push handle with grip + tilt trigger
        add_spline_tube(b, [(xb, y_seat - 20.0, zf), (xb - 40.0, 760.0, zf), (xb - 62.0, 940.0, zf)], 12.0, "frame",
                        PURPLE, sides=8, smooth=1)
        zh = zf * 0.98
        add_spline_tube(b, [(xb - 70.0, y_seat - 10.0, zh), (xb - 100.0, 760.0, zh), (xb - 116.0, 960.0 + ph, zh),
                            (xb - 150.0, 1010.0 + ph, zh), (xb - 200.0, 1022.0 + ph, zh)], 12.0, "frame", PURPLE, sides=8, smooth=2)
        add_spline_tube(b, [(xb - 180.0, 1021.0 + ph, zh), (xb - 262.0, 1024.0 + ph, zh)], 17.0, "frame", BLACK, sides=8, smooth=0)
        add_obox(b, (xb - 218.0, 1000.0 + ph, zh), (1, 0.08, 0), (0, 1, 0), 24.0, 6.0, 8.0, "tilt_lever", (60, 60, 68))
        add_rounded_box(b, xb - 192.0, xb - 176.0, 996.0, 1034.0, zh - 18.0, zh + 18.0, "tilt_lever", (196, 200, 210), bevel=3.0)
        add_spline_tube(b, [(xb - 186.0, 1000.0 + ph, zh + 14.0 * s), (xb - 128.0, 940.0 + ph, zf * 1.1),
                            (xb - 100.0, 700.0, zf * 1.1), (xb - 60.0, y_seat - 40.0, zf * 1.06),
                            (0.0, 330.0, zf * 0.6), (lx - 20.0, ly + 30.0, zf - 6.0 * s)],
                        3.6, "tilt_cable", (30, 30, 34), sides=5, smooth=1, caps=False)
        # T-armrest + side guard with stripes
        za = zf + 8.0 * s
        add_spline_tube(b, [(150.0, y_seat - 10.0, za), (150.0, ya + 4.0, za)], 11.0, "frame", (60, 60, 66), sides=7, smooth=0)
        add_padded_armrest(b, -30.0, 236.0, ya, ya + 34.0, za, 26.0, BLACK, PAD_T)
        add_rounded_box(b, xb - 6.0, 160.0, y_seat + 6.0, ya - 20.0, za - 3.0, za + 3.0, "frame", (40, 40, 46), bevel=2.0)
        for i in range(3):
            add_rounded_box(b, 20.0 + i * 30.0, 140.0, 500.0 + i * 22.0, 506.0 + i * 22.0, za + 2.0 * s, za + 4.0 * s,
                            "frame", (78, 78, 86), bevel=1.0)
        # front loop under the seat front and the footrest hanger
        add_spline_tube(b, [(316.0, y_seat - 16.0, zf), (356.0, y_seat - 60.0, zf), (352.0, y_base + 80.0, zf * 0.98),
                            (320.0, y_base + 50.0, zf * 0.96)], 11.0, "footrest", PURPLE, sides=8, smooth=2)
        add_spline_tube(b, [(330.0, y_seat - 16.0, zf), (420.0, y_seat + hy, zf * 0.96), (510.0, y_seat - 20.0, zf * 0.9), (545.0, 330.0, zf * 0.86),
                            (556.0 + fx, 220.0 + fy, zf * 0.84), (568.0 + fx, 196.0 + fy, zf * 0.82)], 11.5, "footrest", PURPLE, sides=8, smooth=2)
        add_rounded_box(b, 544.0 + fx, 586.0 + fx, 178.0 + fy, 222.0 + fy, zf * 0.82 - 16.0, zf * 0.82 + 16.0, "footrest", BLACK, bevel=5.0)
        add_hex_nut(b, xb - 20.0, y_seat - 14.0, zf + 13.0 * s, s, size=7.5, length=8.0)
    add_rounded_box(b, 556.0 + fx, 716.0 + fx, 176.0 + fy, 194.0 + fy, -zf_abs * 0.96, zf_abs * 0.96, "footrest", BLACK, top_col=(58, 58, 64), bevel=5.0)
    add_cyl(b, (20.0, y_seat - 16.0, -zf_abs), (20.0, y_seat - 16.0, zf_abs), 11.0, "frame", PURPLE, sides=8)
    add_cyl(b, (300.0, y_seat - 16.0, -zf_abs), (300.0, y_seat - 16.0, zf_abs), 11.0, "frame", PURPLE, sides=8)
    add_cyl(b, (70.0, arc_c[1] - arc_R + 4.0, -zf_abs), (70.0, arc_c[1] - arc_R + 4.0, zf_abs), 10.0, "frame", PURPLE_D, sides=8)
    add_cyl(b, (xb - 116.0, 960.0 + ph, -zf_abs * 1.04), (xb - 116.0, 960.0 + ph, zf_abs * 1.04), 9.0, "frame", PURPLE, sides=8)
    # padded seat / tall rounded back / headrest
    add_rounded_box(b, xb - 16.0, 330.0, y_seat - 8.0, y_seat + 10.0, -zf_abs + 8.0, zf_abs - 8.0, "seat", (52, 54, 62), bevel=4.0)
    add_contoured_cushion(b, xb - 6.0, 344.0, y_seat + 8.0, y_seat + 78.0, -zf_abs - 4.0, zf_abs + 4.0, "cushion",
                          PAD, trim_col=PAD_T, bolster=14.0, ribs=0)
    add_contoured_backrest(b, xb - 16.0, xb - 76.0, y_seat + 50.0, 940.0 + bt, -zf_abs + 2.0, zf_abs - 2.0, 56.0,
                           "seat", PAD, trim_col=PAD_T, bolster=26.0, ribs=0)
    add_contoured_backrest(b, xb - 74.0, xb - 80.0, 900.0 + bt, 968.0 + bt, -zf_abs * 0.8, zf_abs * 0.8, 50.0,
                           "seat", PAD, trim_col=PAD_T, bolster=20.0, ribs=0)
    add_spline_tube(b, [(xb - 92.0, 900.0 + bt, 0.0), (xb - 104.0, 1000.0 + bt, 0.0), (xb - 92.0, 1030.0 + bt, 0.0)], 9.0, "frame",
                    (170, 176, 188), sides=7, smooth=1)
    add_contoured_backrest(b, xb - 86.0, xb - 92.0, 1030.0 + bt, 1120.0 + bt, -hr, hr, 46.0, "seat", PAD, trim_col=PAD_T,
                           bolster=26.0, ribs=0)
    _tilt_verts(b, i_seat, arc_c, tilt)
    return b


# --------------------------------------------------------------------------- #
# 4. Ki Mobility Focus CR (focuscr) — adult tilt-in-space
# --------------------------------------------------------------------------- #
def build_focuscr(lod=1.0):
    """Ki Mobility Focus CR as drawn: silver frame, navy seat and tall tapered back with integrated headrest,
    16" black 3-spoke MAG rear wheels and 3-spoke casters with light tan tyres, tall push handles with
    tilt triggers, box armrests with navy pads, CR rocker rails under the seat, straight elevating legrests."""
    b = TriMeshBuilder(lod)
    SIL = (196, 196, 202)
    SIL_D = (150, 150, 158)
    NAVY = (40, 48, 82)
    NAVY_T = (56, 66, 108)
    TAN = (196, 180, 158)
    MAG = (30, 30, 34)
    zf_abs = 210.0
    wx = 15.0
    wR = 250.0
    wz = 271.0
    y_base = 206.0
    y_seat = 438.0
    xc = 430.0                 # front caster axle
    cR = 88.0
    xf = 470.0                 # seat front / legrest receiver
    yh = 1030.0                # push handle height
    lr = 160.0                 # legrest forward reach
    hb = -45.0                   # push handle top set-back
    ya = 681.0                 # armrest pad bottom
    arc_c, arc_R = (190.0, 900.0), 560.0

    for s in (-1, 1):
        zf = zf_abs * s
        add_transit_wheel(b, wx, wR, wz * s, wR, tire_col=TAN, mag_col=MAG, hub_col=(60, 60, 66), disc=True,
                          spoke_w=24.0, disc_col=(92, 92, 98))
        # base frame: axle plate, side rail to the caster housing
        add_rounded_box(b, wx - 36.0, wx + 40.0, wR - 34.0, y_base + 20.0, zf, (wz - 40.0) * s, "frame", SIL_D, bevel=5.0)
        add_spline_tube(b, [(wx - 60.0, y_base, zf), (xc + 20.0, y_base, zf)], 14.0, "frame", SIL, sides=8, smooth=0)
        add_rounded_box(b, xc - 8.0, xc + 40.0, y_base - 18.0, y_base + 60.0, zf - 18.0, zf + 18.0, "frame", SIL_D, bevel=4.0)
        add_front_caster(b, xc - 12.0, cR, zf, cR, (xc + 16.0, y_base + 30.0), fork_col=SIL, tire_col=TAN,
                         hub_col=(110, 110, 116), n_spokes=3, three_window=False)
        # curved CR rails on the base, rollers, links up to the seat rail
        arc = _arc_pts(arc_c[0], arc_c[1], arc_R, 0.0, 380.0, 11)
        add_profile_tube(b, [(x, y, zf - 6.0 * s) for x, y in arc], 16.0, 11.0, "frame", SIL_D, sides=8, smooth=0)
        for rx in (50.0, 330.0):
            ry = arc_c[1] - math.sqrt(arc_R ** 2 - (rx - arc_c[0]) ** 2) - 34.0
            add_spline_tube(b, [(rx, y_base, zf), (rx, ry, zf)], 11.0, "frame", SIL, sides=7, smooth=0)
            add_cyl(b, (rx, ry, zf - 22.0 * s), (rx, ry, zf + 22.0 * s), 18.0, "frame", (52, 54, 62), sides=10)
        for x, y in (arc[0], arc[-1]):
            add_spline_tube(b, [(x, y, zf), (x + (16.0 if x < 100 else -16.0), y_seat - 18.0, zf)], 13.0, "frame", SIL, sides=8, smooth=0)
        # pivot plate with toothed tilt-lock cog
        gx, gy = 190.0, arc_c[1] - arc_R + 34.0
        add_rounded_box(b, gx - 70.0, gx + 70.0, gy - 22.0, y_seat - 22.0, zf - 8.0, zf + 8.0, "frame", SIL_D, bevel=4.0)
        add_gear(b, gx, gy + 30.0, zf + 8.0 * s, zf + 24.0 * s, 40.0, 12, "tilt_lock", (120, 126, 138), tooth_col=(150, 156, 168))
        add_obox(b, (gx + 52.0, gy + 64.0, zf + 16.0 * s), (0.6, -0.8, 0), (0, 0, 1), 26.0, 9.0, 8.0, "tilt_lock", (60, 62, 70))
        # seat rail
        add_spline_tube(b, [(wx - 30.0, y_seat - 18.0, zf), (xf, y_seat - 18.0, zf)], 13.0, "frame", SIL, sides=8, smooth=0)
        # tall push handles with grips and tilt triggers
        add_spline_tube(b, [(wx - 40.0, y_seat - 24.0, zf), (wx - 50.0, 760.0, zf), (wx - 62.0 - hb, yh - 40.0, zf),
                            (wx - 84.0 - hb, yh, zf), (wx - 130.0 - hb, yh + 6.0, zf)], 13.5, "frame", SIL, sides=8, smooth=2)
        add_spline_tube(b, [(wx - 110.0 - hb, yh + 5.0, zf), (wx - 200.0 - hb, yh + 8.0, zf)], 18.0, "frame", (40, 40, 44), sides=8, smooth=0)
        add_obox(b, (wx - 150.0 - hb, yh - 22.0, zf), (1, 0.1, 0), (0, 1, 0), 26.0, 6.0, 9.0, "tilt_lever", (58, 60, 70))
        add_rounded_box(b, wx - 122.0 - hb, wx - 104.0 - hb, yh - 22.0, yh + 16.0, zf - 19.0, zf + 19.0, "tilt_lever", (196, 200, 210), bevel=3.0)
        add_spline_tube(b, [(wx - 116.0 - hb, yh - 14.0, zf + 16.0 * s), (wx - 70.0 - hb, yh - 80.0, zf + 22.0 * s),
                            (wx - 54.0, 720.0, zf + 22.0 * s), (wx - 40.0, 470.0, zf + 18.0 * s),
                            (60.0, 400.0, zf * 0.75), (gx - 20.0, gy + 60.0, zf + 26.0 * s)],
                        3.8, "tilt_cable", (28, 28, 32), sides=5, smooth=1, caps=False)
        # backrest recline gas springs (behind the back)
        zg = 120.0 * s
        add_cyl(b, (wx - 50.0, y_seat - 22.0, zg), (wx - 84.0, 620.0, zg), 13.0, "gas_spring", (44, 46, 54), sides=8)
        add_cyl(b, (wx - 84.0, 620.0, zg), (wx - 100.0, 720.0, zg), 5.5, "gas_spring", (210, 214, 224), sides=6)
        add_cyl(b, (wx - 100.0, 720.0, zg - 12.0), (wx - 100.0, 720.0, zg + 12.0), 8.0, "gas_spring", (60, 62, 70), sides=6)
        add_spline_tube(b, [(wx - 100.0, 720.0, zg), (wx - 56.0, 720.0, zf * 0.95)], 9.0, "frame", SIL_D, sides=6, smooth=0)
        # box armrest: two posts, lower bar, navy pad
        za = zf + 10.0 * s
        for px in (60.0, 330.0):
            add_spline_tube(b, [(px, y_seat - 14.0, za), (px, ya + 4.0, za)], 11.0, "frame", SIL, sides=7, smooth=0)
        add_spline_tube(b, [(60.0, 640.0, za), (330.0, 640.0, za)], 9.0, "frame", SIL, sides=7, smooth=0)
        add_padded_armrest(b, 30.0, 360.0, ya, ya + 36.0, za, 30.0, NAVY, NAVY_T)
        # elevating legrest: receiver clamp + straight tube down to an angled footplate
        add_rounded_box(b, xf - 30.0, xf + 10.0, y_seat - 48.0, y_seat + 6.0, zf - 20.0, zf + 20.0, "footrest", (44, 44, 50), bevel=6.0)
        add_spline_tube(b, [(xf - 10.0, y_seat - 20.0, zf), (xf + 24.0, y_seat - 4.0, zf * 0.98),
                            (xf + 60.0, y_seat - 30.0, zf * 0.96), (xf + lr, 150.0, zf * 0.9)], 13.0, "footrest", SIL,
                        sides=8, smooth=1)
        add_rounded_box(b, xf + lr - 20.0, xf + lr + 8.0, 130.0, 200.0, zf * 0.9 - 16.0, zf * 0.9 + 16.0, "footrest", (44, 44, 50), bevel=5.0)
        za0, zb0 = sorted([24.0 * s, zf_abs * 0.94 * s])
        add_obox(b, (xf + lr + 54.0, 128.0, (za0 + zb0) * 0.5), (0.97, 0.24, 0), (-0.24, 0.97, 0), 64.0, 10.0, (zb0 - za0) * 0.5,
                 "footrest", (44, 44, 50))
        # brake + anti-tip
        add_wheel_brake(b, wx + 150.0, y_base + 30.0, (zf_abs + 20.0) * s, s, col_clamp=SIL_D, col_knob=(50, 52, 60))
        add_anti_tip(b, (wx - 60.0, y_base), (wx - 140.0, 170.0), (wx - 220.0, 80.0), (zf_abs - 24.0) * s, SIL,
                     wheel_R=26.0, tube_r=12.0)
        for bx, by in ((wx - 16.0, wR + 14.0), (wx + 22.0, wR + 14.0), (xc + 16.0, y_base + 10.0), (gx, gy + 30.0)):
            add_hex_nut(b, bx, by, zf + (26.0 if bx == gx else 14.0) * s, s, size=8.0, length=8.0)
    for xx in (wx + 10.0, xc):
        add_cyl(b, (xx, y_base, -zf_abs), (xx, y_base, zf_abs), 14.0, "frame", SIL, sides=8)
    for xx in (30.0, xf - 30.0):
        add_cyl(b, (xx, y_seat - 18.0, -zf_abs), (xx, y_seat - 18.0, zf_abs), 12.0, "frame", SIL, sides=8)
    add_cyl(b, (wx - 100.0, 720.0, -zf_abs * 0.95), (wx - 100.0, 720.0, zf_abs * 0.95), 8.0, "frame", SIL_D, sides=6)
    add_spline_tube(b, [(60.0, 400.0, -zf_abs * 0.75), (110.0, 380.0, 0.0), (60.0, 400.0, zf_abs * 0.75)], 3.6,
                    "tilt_cable", (28, 28, 32), sides=5, smooth=1, caps=False)
    # navy seat pan, cushion, tall back narrowing into the headrest
    add_rounded_box(b, wx - 24.0, xf + 10.0, y_seat - 10.0, y_seat + 10.0, -zf_abs + 6.0, zf_abs - 6.0, "seat", NAVY, bevel=4.0)
    add_contoured_cushion(b, wx - 14.0, xf - 120.0, y_seat + 6.0, y_seat + 74.0, -zf_abs + 10.0, zf_abs - 10.0, "cushion",
                          NAVY, trim_col=NAVY_T, bolster=16.0, ribs=0)
    add_contoured_backrest(b, wx - 10.0, wx - 40.0, y_seat + 50.0, 860.0, -zf_abs + 30.0, zf_abs - 30.0, 60.0,
                           "seat", NAVY, trim_col=NAVY_T, bolster=26.0, ribs=0)
    add_contoured_backrest(b, wx - 38.0, wx - 52.0, 830.0, yh - 20.0, -132.0, 132.0, 56.0, "seat", NAVY,
                           trim_col=NAVY_T, bolster=24.0, ribs=0)
    return b


# --------------------------------------------------------------------------- #
# 5. WHILL Model C2 (whillc2)
# --------------------------------------------------------------------------- #
def build_whillc2(lod=1.0):
    """WHILL Model C2 as drawn: pearl-white body, white back shell and big diagonal white arm pods,
    black seat, grey-tyred rear drive wheels with chevron hubs, grey omni front wheels, white fenders."""
    b = TriMeshBuilder(lod)
    PEARL = (236, 234, 230)
    PEARL_D = (204, 202, 198)
    BLACK = (32, 32, 36)
    BLACK2 = (48, 48, 54)
    DGREY = (76, 76, 82)
    GTYRE = (112, 112, 118)
    fx = 430.0
    fR = 145.0
    fz = 256.0
    rx = -250.0
    rR = 165.0
    rz = 262.0
    ys = 450.0                  # seat pan top
    yb = 940.0                  # back shell top
    pr = 58.0                   # arm pod radius
    p0x = -140.0                # arm pod rear-low end
    p0y = 330.0
    p1x = 230.0                 # arm pod front-high end
    p1y = 690.0
    zp = 262.0                  # arm pod z

    for s in (-1, 1):
        # front omni wheels: grey rollers, dark hub with bolt circle, white fender
        add_omni_wheel(b, fx, fR, fz * s, fR, "omni_wheel", "omni_wheel", roller_col=(150, 150, 156),
                       hub_col=(92, 92, 98), cover_col=(62, 62, 68))
        add_cyl(b, (fx, fR, 80.0 * s), (fx, fR, (fz - 30.0) * s), 24.0, "frame", PEARL_D, sides=10)
        add_wheel_fender(b, fx, fR, (fz - 40.0) * s, s, fR + 4.0, 20.0, 150.0, 76.0, fR + 40.0, PEARL, edge_col=PEARL_D,
                         part="frame")
        # rear driven wheels: grey tyre, dark grey hub disc with chevron, white fender
        add_torus(b, (rx, rR, rz * s), rR - 32.0, 32.0, "tire", GTYRE, segs=34, sides=9, z_scale=1.15)
        add_disc(b, rx, rR, (rz + 32.0) * s, rR - 36.0, "axle", (84, 84, 90), segs=22)
        add_disc(b, rx, rR, (rz - 28.0) * s, rR - 42.0, "axle", (56, 56, 62), segs=18)
        add_obox(b, (rx + 7.0, rR + 4.0, (rz + 35.0) * s), (0.7, -0.7, 0), (0, 0, 1), 17.0, 3.0, 4.0, "axle", (170, 172, 178))
        add_obox(b, (rx - 7.0, rR + 4.0, (rz + 35.0) * s), (0.7, 0.7, 0), (0, 0, 1), 17.0, 3.0, 4.0, "axle", (170, 172, 178))
        add_cyl(b, (rx, rR, 70.0 * s), (rx, rR, (rz - 28.0) * s), 54.0, "motor", DGREY, sides=12)
        add_wheel_fender(b, rx, rR, (rz - 50.0) * s, s, rR + 2.0, 20.0, 165.0, 92.0, rR + 120.0, PEARL, edge_col=PEARL_D,
                         part="frame")
        # freewheel levers at the back of the base
        add_cyl(b, (rx - 95.0, 200.0, 118.0 * s), (rx - 142.0, 262.0, 118.0 * s), 7.5, "freewheel", DGREY, sides=6)
        add_cyl(b, (rx - 138.0, 256.0, 118.0 * s), (rx - 150.0, 278.0, 118.0 * s), 13.0, "freewheel", (96, 96, 102), sides=8)
        # anti-tip wheels on a white rear bar
        add_small_wheel(b, rx - 190.0, 30.0, 104.0 * s, 30.0, "anti_tip", hub_col=DGREY, width=14.0)
        add_spline_tube(b, [(rx - 80.0, 130.0, 100.0 * s), (rx - 150.0, 80.0, 104.0 * s), (rx - 190.0, 34.0, 96.0 * s)], 11.0,
                        "anti_tip", PEARL_D, sides=7, smooth=1)
        # low white side rail from the rear fender to the front fender
        add_spline_tube(b, [(rx + 40.0, 150.0, 150.0 * s), (40.0, 120.0, 150.0 * s), (fx - 40.0, 118.0, 150.0 * s)], 18.0,
                        "frame", PEARL, sides=8, smooth=1)
    add_cyl(b, (rx - 190.0, 34.0, -112.0), (rx - 190.0, 34.0, 112.0), 9.0, "anti_tip", PEARL_D, sides=7)

    # low chassis spine + black footplate between the front wheels
    add_profile_tube(b, [(rx - 110.0, 170.0, 0.0), (rx + 100.0, 160.0, 0.0), (120.0, 130.0, 0.0), (fx + 20.0, 126.0, 0.0)],
                     [42.0, 30.0], [120.0, 92.0], "frame", PEARL_D, sides=14, smooth=1)
    add_rounded_box(b, 150.0, fx + 110.0, 92.0, 118.0, -168.0, 168.0, "footrest", BLACK2, bevel=6.0)
    add_rounded_box(b, 166.0, fx + 96.0, 117.0, 121.0, -150.0, 150.0, "footrest", (70, 70, 76), bevel=1.0)
    # slanted white column from the base up to the seat; battery pack with black handle on its back
    add_profile_tube(b, [(rx + 40.0, 170.0, 0.0), (-130.0, 300.0, 0.0), (-50.0, 420.0, 0.0)], [66.0, 52.0], [96.0, 82.0],
                     "frame", PEARL, sides=14, smooth=1)
    add_obox(b, (-120.0, 215.0, 0.0), (1, 0, 0), (0, 1, 0), 70.0, 50.0, 70.0, "frame", PEARL_D)
    add_obox(b, (-205.0, 300.0, 0.0), (0.85, -0.53, 0), (0.53, 0.85, 0), 26.0, 86.0, 64.0, "battery", (58, 60, 66))
    add_obox(b, (-232.0, 314.0, 0.0), (0.85, -0.53, 0), (0.53, 0.85, 0), 6.0, 46.0, 18.0, "battery", BLACK)
    add_obox(b, (-222.0, 238.0, 0.0), (0.85, -0.53, 0), (0.53, 0.85, 0), 6.0, 14.0, 38.0, "battery", (20, 20, 24))
    # seat post + seat connector cable
    add_cyl(b, (-50.0, 400.0, 0.0), (-50.0, ys + 10.0, 0.0), 40.0, "frame", (170, 172, 178), sides=12)
    add_rounded_box(b, -132.0, -98.0, ys - 26.0, ys + 2.0, 40.0, 76.0, "seat_cable", BLACK, bevel=4.0)
    add_rounded_box(b, -186.0, -154.0, 336.0, 362.0, 68.0, 98.0, "seat_cable", BLACK, bevel=4.0)
    add_spline_tube(b, [(-115.0, ys - 26.0, 58.0), (-150.0, 386.0, 86.0), (-170.0, 364.0, 84.0)], 6.0, "seat_cable",
                    (40, 42, 48), sides=6, smooth=1)
    # seat pan, black cushion and backrest; white shell wrapping the back
    add_rounded_box(b, -215.0, 250.0, ys - 5.0, ys + 18.0, -232.0, 232.0, "frame", PEARL_D, bevel=8.0)
    add_contoured_cushion(b, -205.0, 240.0, ys + 16.0, ys + 76.0, -226.0, 226.0, "seat", (38, 38, 42), trim_col=(54, 54, 60),
                          bolster=14.0)
    add_contoured_backrest(b, -196.0, -236.0, ys + 60.0, yb - 40.0, -210.0, 210.0, 44.0, "seat", (40, 40, 44),
                           trim_col=(56, 56, 62), bolster=20.0, ribs=0)
    add_contoured_backrest(b, -232.0, -278.0, ys + 70.0, yb, -232.0, 232.0, 26.0, "frame", PEARL,
                           trim_col=PEARL_D, bolster=26.0, ribs=0)
    add_rounded_box(b, -258.0, -246.0, ys + 100.0, ys + 170.0, -70.0, 70.0, "frame", (128, 128, 134), bevel=4.0)
    # arm pods: white cylinders rising from the column (rear, low) to the front at armrest height
    p0 = np.array([p0x, p0y])
    p1 = np.array([p1x, p1y])
    d = (p1 - p0) / np.linalg.norm(p1 - p0)
    n_up = np.array([-d[1], d[0]])
    for s in (-1, 1):
        za = zp * s
        part = "armrest" if s > 0 else "frame"
        q0, q1 = p0 + d * 30.0, p1 - d * 4.0
        add_profile_tube(b, [(q0[0], q0[1], za), (q1[0], q1[1], za)], pr, pr, part, PEARL, sides=16, power=1.0,
                         smooth=0, caps=False)
        for q in (q0, q1):
            add_spline_tube(b, [(q[0] - d[0] * 3.0, q[1] - d[1] * 3.0, za), (q[0] + d[0] * 3.0, q[1] + d[1] * 3.0, za)],
                            pr + 2.0, part, DGREY, sides=16, smooth=0, caps=False)
        e0 = p0 - d * 6.0
        add_spline_tube(b, [(e0[0], e0[1], za), (q0[0], q0[1], za)], [pr - 8.0, pr], part, PEARL_D, sides=16, smooth=0, caps=True)
        cap_part = "controller" if s > 0 else "frame"
        e1 = p1 + d * 30.0
        add_spline_tube(b, [(p1[0], p1[1], za), (e1[0], e1[1], za)], [pr, pr - 4.0], cap_part, BLACK2, sides=16, smooth=0, caps=True)
        f1 = p1 + d * 32.0
        add_spline_tube(b, [(e1[0], e1[1], za), (f1[0], f1[1], za)], pr - 20.0, cap_part, (22, 22, 26), sides=12, smooth=0, caps=True)
        # mount bracket from the pod to the seat column
        mid = p0 + d * 150.0
        add_rounded_box(b, mid[0] - 40.0, mid[0] + 40.0, mid[1] - 30.0, mid[1] + 30.0, 70.0 * s, (zp - 40.0) * s,
                        "frame", PEARL_D, bevel=6.0)
        # armrest: dark grey bent bar loop above the pod, back to behind the seat
        top0 = p1 + n_up * (pr + 4.0) + d * 10.0
        add_profile_tube(b, [(top0[0], top0[1], za), (60.0, p1y + 44.0, za), (-210.0, p1y + 52.0, za)], 8.0, 24.0, part, DGREY,
                         sides=10, smooth=1)
        add_profile_tube(b, [(-210.0, p1y + 52.0, za), (-186.0, p1y - 48.0, za * 0.98), (-60.0, ys + 126.0, za * 0.98)], 8.0,
                         18.0, part, DGREY, sides=10, smooth=1)
        # front post under the pod tip
        add_rounded_box(b, p1x - 4.0, p1x + 22.0, p1y - 170.0, p1y - 60.0, za - 12.0, za + 12.0, part, BLACK, bevel=5.0)
    # right arm: display panel on the end cap + joystick knob on top
    tip = p1 + d * 33.0
    add_obox(b, (tip[0] + d[0] * 1.0, tip[1] + d[1] * 1.0, zp), (d[0], d[1], 0), (n_up[0], n_up[1], 0),
             2.0, 14.0, 20.0, "controller", (110, 200, 236))
    add_obox(b, (tip[0] - n_up[0] * 30.0, tip[1] - n_up[1] * 30.0, zp), (d[0], d[1], 0), (n_up[0], n_up[1], 0),
             3.0, 5.0, 5.0, "controller", (226, 72, 60))
    jt = p1 + d * 14.0 + n_up * (pr - 6.0)
    add_cyl(b, (jt[0], jt[1], zp), (jt[0], jt[1] + 22.0, zp), 22.0, "joystick", BLACK, sides=12)
    add_cyl(b, (jt[0], jt[1] + 20.0, zp), (jt[0], jt[1] + 44.0, zp), 7.0, "joystick", (150, 154, 162), sides=8)
    add_cyl(b, (jt[0], jt[1] + 40.0, zp), (jt[0], jt[1] + 62.0, zp), 19.0, "joystick", (66, 68, 74), sides=10)
    add_spline_tube(b, [(p1[0] - 30.0, p1[1] - 50.0, zp - 38.0), (40.0, 500.0, 200.0), (-60.0, 440.0, 120.0)], 4.5, "wiring",
                    (40, 42, 48), sides=5, smooth=1)
    return b


# --------------------------------------------------------------------------- #
# 6. Permobil F5 Corpus (f5) — front-wheel drive
# --------------------------------------------------------------------------- #
def build_f5(lod=1.0):
    """Permobil F5 Corpus as drawn: front-wheel drive (big knobby Y-spoke drive wheels at the front, grey-tyred
    casters on trailing arms at the back), dark graphite chassis with fenders, Corpus seat with tall narrow
    back, headrest on a bent bracket, side armrests, joystick on the right, low front anti-tip footplate."""
    b = TriMeshBuilder(lod)
    BODY = (66, 60, 60)
    BODY_D = (48, 44, 45)
    BODY_L = (84, 78, 78)
    RED = (190, 46, 44)
    SIL = (150, 146, 150)
    UPH = (62, 58, 60)
    UPH_T = (80, 74, 76)
    W = 315.0
    dx = 175.0
    dR = 190.0
    cx = -425.0
    cR = 110.0
    ys = 380.0                 # seat plate
    yb = 1120.0                # backrest top
    xbk = -160.0               # backrest centre x

    # chassis: wedge behind the drive wheels, tapering towards the rear caster arms
    add_profile_tube(b, [(dx + 120.0, 300.0, 0.0), (dx - 80.0, 300.0, 0.0), (-200.0, 270.0, 0.0), (cx + 90.0, 240.0, 0.0)],
                     [130.0, 90.0], [200.0, 176.0], "frame", BODY, sides=16, power=0.35, smooth=1)
    add_rounded_box(b, cx + 60.0, dx + 40.0, 84.0, 200.0, -170.0, 170.0, "frame", BODY_D, bevel=20.0)
    add_rounded_box(b, -300.0, dx - 20.0, 150.0, 330.0, -186.0, 186.0, "battery", (74, 70, 72), bevel=10.0)
    for s in (-1, 1):
        add_rounded_box(b, -260.0, 40.0, 240.0, 256.0, 186.0 * s, 192.0 * s, "battery", (200, 170, 70), bevel=1.5)
        # side shroud panels with a raised styling rib
        add_obox(b, (-170.0, 230.0, 204.0 * s), (0.97, 0.25, 0), (0, 0, 1), 200.0, 20.0, 6.0, "frame", BODY_L)
        add_rounded_box(b, -330.0, dx - 60.0, 120.0, 300.0, 196.0 * s, 206.0 * s, "frame", BODY, bevel=4.0)
    # main circuit breaker at the rear of the base
    add_rounded_box(b, cx + 40.0, cx + 66.0, 220.0, 300.0, -46.0, 46.0, "breaker", BODY_D, bevel=5.0)
    add_cyl(b, (cx + 40.0, 262.0, -14.0), (cx + 4.0, 300.0, -14.0), 8.0, "breaker", (60, 62, 70), sides=6)
    add_cyl(b, (cx + 8.0, 296.0, -14.0), (cx - 6.0, 310.0, -14.0), 13.0, "breaker", RED, sides=8)
    add_rounded_box(b, cx + 34.0, cx + 42.0, 236.0, 252.0, 14.0, 36.0, "breaker", (220, 220, 224), bevel=1.0)

    for s in (-1, 1):
        add_drive_wheel_lugged(b, dx, dR, (W - 15.0) * s, dR, rim_col=(70, 64, 64), tire_col=(56, 52, 52),
                               hub_col=(90, 84, 84), n_spokes=3)
        add_cyl(b, (dx, dR + 2.0, 100.0 * s), (dx, dR + 2.0, (W - 60.0) * s), 56.0, "motor", (78, 74, 76), sides=12)
        add_cyl(b, (dx, dR + 2.0, 60.0 * s), (dx, dR + 2.0, 100.0 * s), 46.0, "motor", (54, 52, 56), sides=12)
        add_cyl(b, (dx - 40.0, dR + 48.0, 150.0 * s), (dx - 92.0, dR + 128.0, 150.0 * s), 8.5, "freewheel", (60, 62, 70), sides=6)
        add_cyl(b, (dx - 88.0, dR + 122.0, 150.0 * s), (dx - 98.0, dR + 146.0, 150.0 * s), 14.0, "freewheel", RED, sides=8)
        add_wheel_fender(b, dx, dR, (W - 62.0) * s, s, dR + 6.0, 20.0, 160.0, 40.0, 320.0, BODY, edge_col=BODY_L, part="frame")
        # rear caster on a trailing arm, with a small fender
        add_power_caster(b, cx, cR, (W - 70.0) * s, cR, (cx + 150.0, 240.0), arm_col=BODY_D, hub_col=(60, 58, 60), spring_col=None)
        add_torus(b, (cx, cR, (W - 70.0) * s), cR - 16.0, 17.0, "frame", (150, 144, 140), segs=22, sides=6)
        add_wheel_fender(b, cx, cR, (W - 100.0) * s, s, cR + 8.0, 10.0, 120.0, 56.0, cR + 120.0, BODY, edge_col=BODY_L,
                         part="frame")
    # seat lift column + Corpus seat frame
    add_spline_tube(b, [(-60.0, 300.0, 0.0), (-60.0, ys, 0.0)], 62.0, "frame", BODY_D, sides=12, smooth=0, caps=True)
    add_rounded_box(b, -300.0, 300.0, ys - 10.0, ys + 26.0, -232.0, 232.0, "frame", (52, 48, 50), bevel=6.0)
    for s in (-1, 1):
        add_rounded_box(b, -310.0, 310.0, ys - 4.0, ys + 24.0, 236.0 * s, 244.0 * s, "frame", BODY_L, bevel=2.0)
        add_spline_tube(b, [(xbk - 40.0, ys + 30.0, 150.0 * s), (xbk - 60.0, yb - 30.0, 150.0 * s)], 14.0, "frame", BODY_D,
                        sides=8, smooth=0)
        # recline strut behind the back
        add_cyl(b, (-280.0, ys + 20.0, 160.0 * s), (-250.0, 700.0, 160.0 * s), 12.0, "frame", (40, 38, 40), sides=8)
    add_contoured_cushion(b, -200.0, 285.0, ys + 26.0, ys + 140.0, -236.0, 236.0, "frame", UPH, trim_col=UPH_T,
                          bolster=30.0, ribs=0)
    add_contoured_backrest(b, xbk + 20.0, xbk - 30.0, ys + 100.0, yb, -200.0, 200.0, 110.0, "frame", UPH, trim_col=UPH_T,
                           bolster=40.0, ribs=0)
    # headrest on a bent bracket
    add_spline_tube(b, [(xbk - 70.0, yb - 80.0, 0.0), (xbk - 160.0, yb + 20.0, 0.0), (xbk - 150.0, yb + 110.0, 0.0),
                        (xbk - 110.0, yb + 120.0, 0.0)], 13.0, "frame", (40, 38, 40), sides=8, smooth=1)
    add_contoured_backrest(b, xbk - 74.0, xbk - 80.0, yb + 50.0, yb + 140.0, -130.0, 130.0, 60.0, "frame", UPH,
                           trim_col=UPH_T, bolster=22.0, ribs=0)
    # armrests (on the back frame)
    for s in (-1, 1):
        za = 262.0 * s
        add_spline_tube(b, [(xbk - 60.0, 620.0, 210.0 * s), (xbk - 50.0, 680.0, za), (xbk - 10.0, 690.0, za)], 13.0, "frame",
                        (44, 42, 44), sides=8, smooth=1)
        add_spline_tube(b, [(xbk - 40.0, ys + 30.0, za), (xbk - 40.0, 690.0, za)], 11.0, "frame", (44, 42, 44), sides=8, smooth=0)
        add_padded_armrest(b, xbk - 70.0, 170.0, 684.0, 712.0, za, 34.0, UPH, UPH_T)
    # R-net joystick module (right) with charging socket at front
    jz = 290.0
    add_rounded_box(b, 120.0, 200.0, 684.0, 696.0, jz - 22.0, jz + 22.0, "frame", (44, 42, 44), bevel=3.0)
    add_rounded_box(b, 180.0, 310.0, 692.0, 736.0, jz - 44.0, jz + 44.0, "joystick", (34, 34, 38), bevel=12.0)
    add_rounded_box(b, 194.0, 246.0, 734.0, 739.0, jz - 30.0, jz + 30.0, "joystick", (90, 180, 220), bevel=1.5)
    add_cyl(b, (272.0, 734.0, jz), (272.0, 752.0, jz), 20.0, "joystick", (28, 30, 34), sides=10)
    add_cyl(b, (272.0, 748.0, jz), (272.0, 788.0, jz), 6.5, "joystick", (180, 186, 196), sides=8)
    add_cyl(b, (272.0, 784.0, jz), (272.0, 814.0, jz), 17.0, "joystick", (44, 46, 54), sides=10)
    add_cyl(b, (308.0, 714.0, jz), (322.0, 714.0, jz), 11.0, "joystick", (30, 30, 34), sides=10)
    add_cyl(b, (320.0, 714.0, jz), (324.0, 714.0, jz), 6.0, "joystick", (200, 160, 60), sides=6)
    add_spline_tube(b, [(190.0, 700.0, jz - 30.0), (120.0, 620.0, jz - 50.0), (40.0, 420.0, 200.0), (0.0, 320.0, 160.0)],
                    6.0, "wiring", (50, 52, 58), sides=6, smooth=2)
    # low front footplate on a bar with the front anti-tip roller
    add_spline_tube(b, [(dx + 110.0, 150.0, 0.0), (dx + 170.0, 70.0, 0.0), (dx + 200.0, 50.0, 0.0)], 18.0, "footrest", BODY_D,
                    sides=8, smooth=1)
    add_rounded_box(b, dx + 170.0, dx + 370.0, 30.0, 46.0, -150.0, 150.0, "footrest", (40, 38, 40), bevel=4.0)
    for s in (-1, 1):
        add_small_wheel(b, dx + 215.0, 28.0, 120.0 * s, 28.0, "footrest", tire_col=(40, 38, 40), hub_col=SIL, width=12.0)
    return b


# --------------------------------------------------------------------------- #
# 7 & 8. Mid-wheel drive: Quickie Pulse 6 (pulse6), Quantum Q6 Edge (q6edge)
# --------------------------------------------------------------------------- #
def add_cast_caster(b, cx, cR, z, pivot, arm_col, tire_col, hub_col=(150, 150, 156)):
    """Power-chair suspension caster: cast arm from the chassis pivot to a black stem housing, fork, tyre."""
    sgn = 1 if z > 0 else -1
    px, py = pivot
    hy = cR * 2.0 + 40.0
    add_torus(b, (cx, cR, z), cR - 17.0, 17.0, "frame", tire_col, segs=22, sides=6, z_scale=1.2)
    add_disc(b, cx, cR, z + 10.0 * sgn, cR - 26.0, "frame", hub_col, segs=14)
    add_disc(b, cx, cR, z - 10.0 * sgn, cR - 26.0, "frame", hub_col, segs=14)
    sx = cx + (24.0 if cx > px else -24.0)
    for fz in (z - 24.0, z + 24.0):
        add_spline_tube(b, [(sx, hy - 30.0, fz), (cx, cR, fz)], 9.0, "frame", arm_col, sides=6, smooth=0)
    add_cyl(b, (sx, hy - 34.0, z), (sx, hy + 24.0, z), 26.0, "frame", (40, 40, 44), sides=12)
    add_profile_tube(b, [(px, py, z), ((px + sx) * 0.5, hy + 6.0, z), (sx, hy - 6.0, z)], 22.0, 18.0, "frame", arm_col,
                     sides=10, smooth=1)


def build_pulse6(lod=1.0):
    """Quickie Pulse 6 as drawn: black mid-wheel-drive base with black fenders and front battery box, silver cast
    caster arms, light-grey tyres and silver 5-spoke rims, red shocks; raised tilting seat, tall back with lateral
    supports and headrest on a stalk, push handles, armrests (joystick + pouch on the right), centre-mount
    elevating legrest with calf pads and one big footplate."""
    b = TriMeshBuilder(lod)
    BASE = (40, 40, 44)
    BASE_T = (56, 56, 60)
    SIL = (176, 176, 182)
    GTYRE = (158, 156, 154)
    SPRING = (200, 46, 46)
    UPH, UPH_T = (52, 50, 54), (70, 68, 72)
    W = 280.0
    dR = 172.0
    xcf = 300.0                # front caster axle
    xcr = -300.0               # rear caster axle
    cR = 72.0
    ys = 560.0                 # seat frame
    yb = 1100.0                # backrest top
    tilt = 9.0
    xl = 410.0                 # footplate x
    yl = 250.0                 # footplate height

    # chassis: low body, fenders over the drive wheels, front battery box with badge
    add_rounded_box(b, -330.0, 300.0, 96.0, 290.0, -196.0, 196.0, "frame", BASE, top_col=BASE_T, bevel=18.0)
    add_rounded_box(b, -300.0, -110.0, 180.0, 318.0, -150.0, 150.0, "battery", (50, 50, 56), bevel=8.0)
    add_rounded_box(b, 160.0, xcf + 40.0, 100.0, 330.0, -160.0, 160.0, "battery", (34, 34, 38), top_col=(46, 46, 50), bevel=12.0)
    add_rounded_box(b, xcf + 38.0, xcf + 42.0, 220.0, 260.0, -50.0, 50.0, "battery", (150, 150, 156), bevel=1.0)
    for i in range(3):
        add_rounded_box(b, xcf + 38.0, xcf + 41.0, 140.0 + i * 20.0, 148.0 + i * 20.0, -60.0, 60.0, "battery", (70, 70, 76), bevel=1.0)
    for xb in (-205.0, 230.0):
        for zt in (-70.0, 70.0):
            add_cyl(b, (xb, 318.0 if xb < 0 else 330.0, zt), (xb, 340.0, zt), 9.0, "battery",
                    (200, 60, 50) if zt > 0 else (40, 40, 44), sides=6)
    add_rounded_box(b, -352.0, -330.0, 200.0, 246.0, -40.0, 40.0, "fuse", (228, 92, 84), bevel=5.0)

    for s in (-1, 1):
        add_power_drive_wheel(b, 0.0, dR, (W - 15.0) * s, dR, style="alloy5", rim_col=SIL, tire_col=GTYRE)
        add_mwd_drivetrain(b, 0.0, dR + 4.0, W, s, motor_col=(84, 88, 100), lever_col=SIL)
        add_wheel_fender(b, 0.0, dR, (W - 70.0) * s, s, dR + 4.0, 10.0, 170.0, 56.0, dR + 140.0, BASE, edge_col=BASE_T, part="frame")
        # silver cast caster arms front and rear
        add_cast_caster(b, xcf, cR, (W - 50.0) * s, (150.0, 200.0), SIL, GTYRE)
        add_cast_caster(b, xcr, cR, (W - 50.0) * s, (-150.0, 200.0), SIL, GTYRE)
        for xs in (180.0, -180.0):
            add_coil_spring(b, (xs, 196.0, (W - 64.0) * s), (xs - (20.0 if xs > 0 else -20.0), 300.0, (W - 72.0) * s),
                            17.0, 4.0, 6, "frame", SPRING)
            add_cyl(b, (xs, 196.0, (W - 64.0) * s), (xs - (20.0 if xs > 0 else -20.0), 300.0, (W - 72.0) * s), 7.0, "frame",
                    (60, 62, 70), sides=6)
        add_spline_tube(b, [(-110.0, 250.0, 120.0 * s), (-70.0, 240.0, 100.0 * s), (-30.0, 228.0, 86.0 * s)], 5.5,
                        "wiring", (40, 40, 46), sides=6, smooth=1)
        add_spline_tube(b, [(160.0, 250.0, 120.0 * s), (60.0, 238.0, 140.0 * s), (30.0, 228.0, 150.0 * s)], 5.5,
                        "wiring", (150, 40, 40), sides=6, smooth=1)
        add_rounded_box(b, -40.0, -16.0, 220.0, 240.0, 76.0 * s, 100.0 * s, "wiring", (30, 30, 34), bevel=3.0)

    # tilt mechanism: actuator, scissor frame between base and seat
    add_spline_tube(b, [(0.0, 290.0, 0.0), (0.0, ys - 20.0, 0.0)], 46.0, "frame", BASE, sides=12, smooth=0, caps=True)
    for s in (-1, 1):
        add_spline_tube(b, [(-180.0, 300.0, 150.0 * s), (160.0, ys - 20.0, 150.0 * s)], 13.0, "frame", (60, 60, 66), sides=6, smooth=0)
        add_spline_tube(b, [(-180.0, ys - 20.0, 150.0 * s), (160.0, 300.0, 150.0 * s)], 13.0, "frame", (60, 60, 66), sides=6, smooth=0)
    add_cyl(b, (-140.0, 320.0, 0.0), (120.0, ys - 40.0, 0.0), 18.0, "frame", (70, 72, 80), sides=8)

    i_seat = len(b.verts)
    add_rounded_box(b, -250.0, 270.0, ys - 10.0, ys + 26.0, -232.0, 232.0, "frame", BASE, bevel=6.0)
    add_rounded_box(b, -244.0, 266.0, ys + 24.0, ys + 104.0, -236.0, 236.0, "frame", UPH, top_col=UPH_T, bevel=18.0)
    add_contoured_backrest(b, -222.0, -270.0, ys + 90.0, yb - 80.0, -226.0, 226.0, 64.0, "frame", UPH, trim_col=UPH_T,
                           bolster=20.0, ribs=3)
    for s in (-1, 1):
        add_obox(b, (-210.0, yb - 330.0, 240.0 * s), (0.1, 0.99, 0), (1, -0.1, 0), 80.0, 54.0, 16.0, "frame", UPH)
        # push handles behind the back
        add_spline_tube(b, [(-262.0, ys + 40.0, 205.0 * s), (-292.0, yb - 200.0, 205.0 * s), (-320.0, yb - 150.0, 205.0 * s),
                            (-380.0, yb - 140.0, 205.0 * s)], 11.0, "frame", (50, 50, 56), sides=8, smooth=2)
        add_spline_tube(b, [(-350.0, yb - 140.0, 205.0 * s), (-410.0, yb - 138.0, 205.0 * s)], 16.0, "frame", (30, 30, 34),
                        sides=8, smooth=0)
    add_spline_tube(b, [(-282.0, yb - 120.0, 0.0), (-300.0, yb - 20.0, 0.0), (-292.0, yb + 40.0, 0.0)], 12.0, "frame",
                    (40, 42, 48), sides=8, smooth=1)
    add_contoured_backrest(b, -282.0, -290.0, yb + 10.0, yb + 120.0, -130.0, 130.0, 44.0, "frame", UPH, trim_col=UPH_T,
                           bolster=22.0, ribs=0)
    # armrests; right one carries the joystick and a pouch underneath
    for s in (-1, 1):
        za = (W - 36.0) * s
        add_spline_tube(b, [(-200.0, ys + 20.0, za), (-200.0, ys + 230.0, za)], 13.0, "frame", BASE, sides=8, smooth=0)
        add_spline_tube(b, [(60.0, ys + 20.0, za), (60.0, ys + 230.0, za)], 12.0, "frame", BASE, sides=8, smooth=0)
        add_padded_armrest(b, -230.0, 170.0, ys + 226.0, ys + 266.0, za, 32.0, UPH, UPH_T)
    add_rounded_box(b, -150.0, 100.0, ys + 70.0, ys + 200.0, W - 36.0 + 12.0, W - 36.0 + 60.0, "frame", (34, 34, 38), bevel=10.0)
    add_power_controller(b, 220.0, ys + 268.0, W - 36.0, (40.0, 300.0, 140.0))
    # centre-mount elevating legrest: perforated bar, two calf pads, one big footplate
    add_rounded_box(b, 230.0, 280.0, ys - 40.0, ys + 10.0, -40.0, 40.0, "footrest", BASE, bevel=8.0)
    p0 = np.array([262.0, ys - 20.0])
    p1 = np.array([xl - 10.0, yl + 30.0])
    d = (p1 - p0) / np.linalg.norm(p1 - p0)
    nrm = np.array([-d[1], d[0]])
    L = np.linalg.norm(p1 - p0)
    mid = (p0 + p1) * 0.5
    add_obox(b, (mid[0], mid[1], 0.0), (d[0], d[1], 0), (nrm[0], nrm[1], 0), L * 0.5, 16.0, 26.0, "footrest", (36, 36, 40))
    for i in range(6):
        q = p0 + d * (L * (0.15 + 0.13 * i))
        add_cyl(b, (q[0], q[1], -27.0), (q[0], q[1], 27.0), 5.0, "footrest", (90, 90, 96), sides=6)
    for s in (-1, 1):
        q = p0 + d * (L * 0.42) + nrm * 30.0
        add_obox(b, (q[0], q[1], 110.0 * s), (d[0], d[1], 0), (nrm[0], nrm[1], 0), 90.0, 14.0, 80.0, "footrest", (44, 44, 48))
    add_obox(b, (xl + 90.0, yl + 20.0, 0.0), (0.97, 0.24, 0), (-0.24, 0.97, 0), 120.0, 12.0, 190.0, "footrest", (40, 40, 44))
    for i in range(5):
        add_obox(b, (xl + 30.0 + i * 32.0, yl + 18.0 + i * 8.0, 0.0), (0.97, 0.24, 0), (-0.24, 0.97, 0), 8.0, 13.0, 150.0,
                 "footrest", (66, 66, 72))
    _tilt_verts(b, i_seat, (0.0, ys), tilt)
    return b


def build_q6edge(lod=1.0):
    """Quantum Q6 Edge as drawn: black mid-wheel-drive base with dark purple side trim and a glossy yellow
    front shroud, black tyres with grey 5-spoke rims, six black casters, high-back contoured black seat,
    padded armrests, swing-in joystick on the right, low single footplate in front."""
    b = TriMeshBuilder(lod)
    BASE = (36, 36, 40)
    BASE_T = (50, 50, 56)
    PURPLE = (74, 52, 88)
    YEL = (236, 180, 40)
    RIM = (150, 150, 156)
    TIRE = (40, 40, 44)
    UPH, UPH_T = (44, 40, 42), (62, 58, 60)
    W = 330.0
    dR = 210.0
    xcf = 330.0
    xcr = -390.0
    cR = 66.0
    ys = 440.0                 # seat frame
    yb = 1150.0                # backrest top
    xl = 380.0                 # footplate centre x
    yl = 110.0                 # footplate height

    # chassis with purple side trims, glossy yellow front shroud with black grille, rear lights
    add_rounded_box(b, -345.0, 250.0, 100.0, 300.0, -200.0, 200.0, "frame", BASE, top_col=BASE_T, bevel=18.0)
    add_rounded_box(b, -300.0, -110.0, 180.0, 318.0, -150.0, 150.0, "battery", (50, 50, 56), bevel=8.0)
    add_rounded_box(b, 60.0, 250.0, 180.0, 312.0, -150.0, 150.0, "battery", (50, 50, 56), bevel=8.0)
    for xb in (-205.0, 160.0):
        for zt in (-70.0, 70.0):
            add_cyl(b, (xb, 312.0 if xb > 0 else 318.0, zt), (xb, 326.0, zt), 9.0, "battery",
                    (200, 60, 50) if zt > 0 else (40, 40, 44), sides=6)
    add_rounded_box(b, 230.0, 362.0, 112.0, 330.0, -186.0, 186.0, "frame", YEL, top_col=(250, 206, 80), bevel=44.0)
    add_rounded_box(b, 356.0, 366.0, 250.0, 280.0, -34.0, 34.0, "frame", (30, 30, 34), bevel=6.0)
    add_rounded_box(b, 364.0, 368.0, 258.0, 272.0, -20.0, 20.0, "frame", (210, 214, 222), bevel=2.0)
    add_rounded_box(b, -362.0, -340.0, 200.0, 246.0, -40.0, 40.0, "fuse", (228, 92, 84), bevel=5.0)

    for s in (-1, 1):
        # purple side rails along the base, from rear caster pivot to front caster pivot
        add_profile_tube(b, [(xcr + 40.0, 170.0, 210.0 * s), (-100.0, 150.0, 214.0 * s), (100.0, 150.0, 214.0 * s),
                             (xcf - 40.0, 170.0, 210.0 * s)], 22.0, 12.0, "frame", PURPLE, sides=10, smooth=1)
        add_power_drive_wheel(b, 0.0, dR, (W - 15.0) * s, dR, style="alloy5", rim_col=RIM, tire_col=TIRE)
        add_mwd_drivetrain(b, 0.0, dR + 4.0, W, s, motor_col=(84, 88, 100), lever_col=YEL)
        add_wheel_fender(b, 0.0, dR, (W - 70.0) * s, s, dR + 4.0, 10.0, 170.0, 56.0, dR + 140.0, BASE, edge_col=BASE_T, part="frame")
        add_cast_caster(b, xcf, cR, (W - 60.0) * s, (150.0, 190.0), PURPLE, TIRE, hub_col=(70, 70, 76))
        add_cast_caster(b, xcr, cR, (W - 60.0) * s, (-150.0, 190.0), PURPLE, TIRE, hub_col=(70, 70, 76))
        for xs in (200.0, -200.0):
            add_coil_spring(b, (xs, 190.0, (W - 72.0) * s), (xs - (20.0 if xs > 0 else -20.0), 290.0, (W - 80.0) * s),
                            16.0, 4.0, 6, "frame", (186, 190, 198))
        add_spline_tube(b, [(-110.0, 250.0, 120.0 * s), (-70.0, 240.0, 100.0 * s), (-30.0, 228.0, 86.0 * s)], 5.5,
                        "wiring", (40, 40, 46), sides=6, smooth=1)
        add_spline_tube(b, [(92.0, 250.0, 120.0 * s), (60.0, 238.0, 140.0 * s), (30.0, 228.0, 150.0 * s)], 5.5,
                        "wiring", (150, 40, 40), sides=6, smooth=1)
        add_rounded_box(b, -40.0, -16.0, 220.0, 240.0, 76.0 * s, 100.0 * s, "wiring", (30, 30, 34), bevel=3.0)

    # seat: actuator column, black seat frame, contoured cushion, high back narrowing into the headrest
    add_spline_tube(b, [(0.0, 300.0, 0.0), (0.0, ys, 0.0)], 46.0, "frame", BASE, sides=12, smooth=0, caps=True)
    for s in (-1, 1):
        add_spline_tube(b, [(-160.0, 320.0, 120.0 * s), (150.0, ys, 120.0 * s)], 12.0, "frame", (70, 70, 76), sides=6, smooth=0)
    add_rounded_box(b, -250.0, 260.0, ys - 20.0, ys + 30.0, -238.0, 238.0, "frame", BASE, bevel=6.0)
    add_contoured_cushion(b, -244.0, 266.0, ys + 26.0, ys + 110.0, -240.0, 240.0, "frame", UPH, trim_col=UPH_T, bolster=26.0, ribs=0)
    add_contoured_backrest(b, -215.0, -262.0, ys + 90.0, yb - 220.0, -232.0, 232.0, 64.0, "frame", UPH, trim_col=UPH_T,
                           bolster=34.0, ribs=0)
    add_contoured_backrest(b, -258.0, -282.0, yb - 260.0, yb, -170.0, 170.0, 58.0, "frame", UPH, trim_col=UPH_T,
                           bolster=26.0, ribs=0)
    for s in (-1, 1):
        add_spline_tube(b, [(-262.0, ys, 200.0 * s), (-290.0, yb - 300.0, 200.0 * s)], 12.0, "frame", (50, 52, 60), sides=8, smooth=0)
    # armrests on posts at the back
    for s in (-1, 1):
        za = (W - 40.0) * s
        add_spline_tube(b, [(-215.0, ys + 40.0, za), (-210.0, ys + 300.0, za)], 14.0, "frame", BASE, sides=8, smooth=0)
        add_padded_armrest(b, -240.0, 200.0, ys + 296.0, ys + 340.0, za, 36.0, UPH, UPH_T)
    # swing-in joystick on the right armrest
    zj = W - 120.0
    add_spline_tube(b, [(196.0, ys + 300.0, W - 40.0), (240.0, ys + 290.0, W - 60.0), (262.0, ys + 286.0, zj)], 10.0,
                    "controller", (40, 40, 44), sides=8, smooth=1)
    add_power_controller(b, 280.0, ys + 300.0, zj, (40.0, 300.0, 140.0))
    add_rounded_box(b, 224.0, 240.0, ys + 322.0, ys + 328.0, zj - 30.0, zj + 30.0, "controller", YEL, bevel=1.5)
    # low centre-mount footplate in front of the shroud
    add_spline_tube(b, [(250.0, ys - 10.0, 0.0), (340.0, 300.0, 0.0), (xl - 60.0, yl + 30.0, 0.0)], 20.0, "footrest", BASE,
                    sides=10, smooth=1)
    add_obox(b, (xl, yl, 0.0), (0.98, 0.18, 0), (-0.18, 0.98, 0), 120.0, 12.0, 200.0, "footrest", (32, 32, 36))
    for i in range(4):
        add_obox(b, (xl - 70.0 + i * 46.0, yl + 4.0 + i * 8.5, 0.0), (0.98, 0.18, 0), (-0.18, 0.98, 0), 10.0, 12.0, 70.0,
                 "footrest", (64, 64, 70))
    return b


def build_mwd(variant="pulse6", lod=1.0):
    """Mid-wheel-drive chairs: Quickie Pulse 6 or Quantum Q6 Edge."""
    return build_pulse6(lod) if variant == "pulse6" else build_q6edge(lod)


BUILDERS = {
    "aeroz":   lambda lod=1.0: build_aeroz(lod),
    "cross6":  lambda lod=1.0: build_cross6(lod),
    "iris":    lambda lod=1.0: build_iris(lod),
    "focuscr": lambda lod=1.0: build_focuscr(lod),
    "whillc2": lambda lod=1.0: build_whillc2(lod),
    "f5":      lambda lod=1.0: build_f5(lod),
    "pulse6":  lambda lod=1.0: build_mwd("pulse6", lod),
    "q6edge":  lambda lod=1.0: build_mwd("q6edge", lod),
}


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    default_dir = os.path.join(here, "assets", "models") if os.path.isdir(os.path.join(here, "assets")) else os.path.join(here, "..", "assets", "models")
    out_dir = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else default_dir
    only = sys.argv[2].split(",") if len(sys.argv) > 2 else None
    os.makedirs(out_dir, exist_ok=True)
    for name, fn in BUILDERS.items():
        if only and name not in only:
            continue
        full_b = fn(1.0)
        d_full = full_b.to_dict()
        full_path = os.path.join(out_dir, f"chair_{name}_ai.json")
        with open(full_path, "w", encoding="utf-8") as f:
            json.dump(d_full, f, separators=(",", ":"))

        lod_b = fn(0.65)
        d_lod = lod_b.to_dict()
        lod_path = os.path.join(out_dir, f"chair_{name}_ai_lod.json")
        with open(lod_path, "w", encoding="utf-8") as f:
            json.dump(d_lod, f, separators=(",", ":"))

        print(f"{name:8s}: full={len(d_full['faces']):5d} faces ({len(d_full['verts']):4d} verts), "
              f"lod={len(d_lod['faces']):5d} faces ({len(d_lod['verts']):4d} verts), parts={len(d_full['parts'])}")
