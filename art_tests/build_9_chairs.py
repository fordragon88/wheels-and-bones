import math, json, os
import numpy as np

M_DOUBLE, M_METAL, M_EDGE = 1, 2, 4


class TriMeshBuilder:
    def __init__(self, lod_scale=1.0):
        self.verts = []
        self.faces = []   # [a, b, c, pi, r, g, bl]
        self.parts = ["frame"]
        self.part_map = {"frame": 0}
        self.lod = lod_scale

    def segs(self, n, min_n=5):
        return max(min_n, int(round(n * self.lod)))

    def pid(self, part):
        p = part or "frame"
        if p not in self.part_map:
            self.part_map[p] = len(self.parts)
            self.parts.append(p)
        return self.part_map[p]

    def v(self, pt):
        self.verts.append((round(float(pt[0]), 1), round(float(pt[1]), 1), round(float(pt[2]), 1)))
        return len(self.verts) - 1

    def tri(self, a, b, c, part, col):
        if a == b or b == c or a == c:
            return
        pi = self.pid(part)
        r, g, bl = int(np.clip(col[0], 0, 255)), int(np.clip(col[1], 0, 255)), int(np.clip(col[2], 0, 255))
        self.faces.append([a, b, c, pi, r, g, bl])

    def quad(self, a, b, c, d, part, col):
        self.tri(a, b, c, part, col)
        self.tri(a, c, d, part, col)

    def poly(self, idxs, part, col):
        for i in range(1, len(idxs) - 1):
            self.tri(idxs[0], idxs[i], idxs[i + 1], part, col)

    def to_dict(self, source="Custom3D"):
        V = np.asarray(self.verts, dtype=np.float64)
        F = np.asarray(self.faces, dtype=np.int64)
        key, inv = np.unique(V.round(1), axis=0, return_inverse=True)
        inv = inv.ravel()
        F_idx = inv[F[:, :3]]
        ok = (F_idx[:, 0] != F_idx[:, 1]) & (F_idx[:, 1] != F_idx[:, 2]) & (F_idx[:, 0] != F_idx[:, 2])
        F_clean = np.concatenate([F_idx[ok], F[ok, 3:]], axis=1)
        return {
            "verts": key.round(1).tolist(),
            "faces": F_clean.tolist(),
            "parts": self.parts,
            "cull": False,
            "source": source,
        }


def _norm(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else np.array([1.0, 0.0, 0.0])


def smooth_curve(pts, subdiv=2):
    arr = [np.asarray(p, float) for p in pts]
    if len(arr) <= 2 or subdiv <= 0:
        return arr
    for _ in range(subdiv):
        out = [arr[0]]
        for i in range(len(arr) - 1):
            p0, p1 = arr[i], arr[i + 1]
            out.append(0.75 * p0 + 0.25 * p1)
            out.append(0.25 * p0 + 0.75 * p1)
        out.append(arr[-1])
        arr = out
    return arr


def add_spline_tube(b, pts, r, part, col, sides=8, smooth=2, caps=True):
    sides = b.segs(sides, 5)
    path = smooth_curve(pts, smooth) if smooth > 0 and len(pts) > 2 else [np.asarray(p, float) for p in pts]
    n_pts = len(path)
    if n_pts < 2:
        return
    tangents = []
    for i in range(n_pts):
        if i == 0:
            t = path[1] - path[0]
        elif i == n_pts - 1:
            t = path[-1] - path[-2]
        else:
            t = path[i + 1] - path[i - 1]
        tangents.append(_norm(t))

    t0 = tangents[0]
    up = np.array([0.0, 1.0, 0.0]) if abs(t0[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = _norm(np.cross(t0, up))
    w = _norm(np.cross(t0, u))

    rings = []
    for i, p in enumerate(path):
        if i > 0:
            ti = tangents[i]
            u = u - np.dot(u, ti) * ti
            if np.linalg.norm(u) < 1e-6:
                up = np.array([0.0, 1.0, 0.0]) if abs(ti[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
                u = np.cross(ti, up)
            u = _norm(u)
            w = _norm(np.cross(ti, u))
        ring = []
        if isinstance(r, (list, tuple, np.ndarray)):
            t_frac = i / max(1, n_pts - 1)
            r_cur = r[0] * (1.0 - t_frac) + r[-1] * t_frac if len(r) == 2 else r[min(i, len(r) - 1)]
        else:
            r_cur = r
        for k in range(sides):
            ang = 2 * math.pi * k / sides
            offset = (math.cos(ang) * u + math.sin(ang) * w) * r_cur
            ring.append(b.v(p + offset))
        rings.append(ring)

    for i in range(n_pts - 1):
        R0, R1 = rings[i], rings[i + 1]
        for k in range(sides):
            kk = (k + 1) % sides
            b.quad(R0[k], R0[kk], R1[kk], R1[k], part, col)
    if caps:
        b.poly(list(reversed(rings[0])), part, col)
        b.poly(rings[-1], part, col)


def add_torus(b, center, R, r_tube, part, col, segs=32, sides=8, z_scale=1.0, inner=None):
    segs = b.segs(segs, 18)
    sides = b.segs(sides, 5)
    cx, cy, cz = center
    rings = []
    for i in range(segs):
        a = 2 * math.pi * i / segs
        ca, sa = math.cos(a), math.sin(a)
        ring = []
        for k in range(sides):
            ang = 2 * math.pi * k / sides
            rr = R + r_tube * math.cos(ang)
            ring.append(b.v((cx + rr * ca, cy + rr * sa, cz + r_tube * math.sin(ang) * z_scale)))
        rings.append(ring)
    for i in range(segs):
        A, B = rings[i], rings[(i + 1) % segs]
        for k in range(sides):
            kk = (k + 1) % sides
            pp, cc = part, col
            if inner is not None and math.cos(2 * math.pi * (k + 0.5) / sides) < -0.45:
                pp, cc = inner
            b.quad(A[k], B[k], B[kk], A[kk], pp, cc)


def add_disc(b, cx, cy, z, R, part, col, segs=20, R_in=0.0):
    segs = b.segs(segs, 12)
    r_steps = [R_in, (R_in + R) * 0.5, R] if R_in > 1.0 else [6.0, R * 0.52, R]
    rings = []
    for rr in r_steps:
        ring = []
        for i in range(segs):
            a = 2 * math.pi * i / segs
            ring.append(b.v((cx + rr * math.cos(a), cy + rr * math.sin(a), z)))
        rings.append(ring)
    if R_in <= 1.0:
        c_idx = b.v((cx, cy, z))
        for i in range(segs):
            ii = (i + 1) % segs
            b.tri(c_idx, rings[0][i], rings[0][ii], part, col)
    for r_i in range(len(rings) - 1):
        R0, R1 = rings[r_i], rings[r_i + 1]
        for i in range(segs):
            ii = (i + 1) % segs
            b.quad(R0[i], R1[i], R1[ii], R0[ii], part, col)


def add_rounded_box(b, x0, x1, y0, y1, z0, z1, part, col, bevel=8.0, top_col=None):
    if x0 > x1:
        x0, x1 = x1, x0
    if y0 > y1:
        y0, y1 = y1, y0
    if z0 > z1:
        z0, z1 = z1, z0
    dx, dy, dz = (x1 - x0), (y1 - y0), (z1 - z0)
    bv = min(bevel, dx * 0.25, dy * 0.25, dz * 0.25)
    if bv < 1.2:
        p = [b.v(q) for q in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                              (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
        for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (3, 7, 6, 2), (1, 2, 6, 5), (0, 4, 7, 3)):
            b.poly([p[i] for i in q], part, col)
        return
    ys = [y0, y0 + bv, y1 - bv, y1]
    insets = [bv, 0.0, 0.0, bv]
    rings = []
    for y, ins in zip(ys, insets):
        xa, xb = x0 + ins, x1 - ins
        za, zb = z0 + ins, z1 - ins
        c = bv * 0.55
        pts = [
            (xa + c, y, za), (xb - c, y, za),
            (xb, y, za + c), (xb, y, zb - c),
            (xb - c, y, zb), (xa + c, y, zb),
            (xa, y, zb - c), (xa, y, za + c),
        ]
        rings.append([b.v(pt) for pt in pts])
    n = len(rings[0])
    for j in range(len(rings) - 1):
        R0, R1 = rings[j], rings[j + 1]
        c_use = (top_col or col) if j == len(rings) - 2 and top_col else col
        for i in range(n):
            ii = (i + 1) % n
            b.quad(R0[i], R0[ii], R1[ii], R1[i], part, c_use)
    b.poly(list(reversed(rings[0])), part, col)
    b.poly(rings[-1], part, top_col or col)


def add_contoured_cushion(b, x0, x1, y0, y1, z0, z1, part, col, trim_col=None, bolster=12.0, ribs=0):
    nx, nz = b.segs(9, 6), b.segs(9, 6)
    xs = np.linspace(x0, x1, nx)
    zs = np.linspace(z0, z1, nz)
    top_grid = np.zeros((nx, nz), int)
    bot_grid = np.zeros((nx, nz), int)
    zc = (z0 + z1) / 2
    zh = max(1.0, (z1 - z0) / 2)
    xc = (x0 + x1) / 2
    xh = max(1.0, (x1 - x0) / 2)
    for i, x in enumerate(xs):
        u = (x - xc) / xh
        for k, z in enumerate(zs):
            w = (z - zc) / zh
            edge = max(0.2, 1.0 - 0.16 * (u ** 4 + w ** 4))
            lat = bolster * (w ** 2) * (1.0 - 0.32 * (w ** 4))
            pom = bolster * 0.30 * math.exp(-((w / 0.28) ** 2)) * max(0.0, u)
            rib_h = 3.5 * abs(math.sin(ribs * math.pi * (x - x0) / (x1 - x0))) if ribs > 0 else 0.0
            yt = y0 + (y1 - y0 + lat + pom + rib_h) * edge
            yb = y0 + (1.0 - edge) * (y1 - y0) * 0.25
            top_grid[i, k] = b.v((x, yt, z))
            bot_grid[i, k] = b.v((x, yb, z))

    for i in range(nx - 1):
        for k in range(nz - 1):
            c_use = trim_col if (trim_col and (k == 0 or k == nz - 2)) else col
            b.quad(top_grid[i, k], top_grid[i + 1, k], top_grid[i + 1, k + 1], top_grid[i, k + 1], part, c_use)
            b.quad(bot_grid[i, k], bot_grid[i, k + 1], bot_grid[i + 1, k + 1], bot_grid[i + 1, k], part, col)
    for i in range(nx - 1):
        b.quad(bot_grid[i, 0], top_grid[i, 0], top_grid[i + 1, 0], bot_grid[i + 1, 0], part, trim_col or col)
        b.quad(top_grid[i, -1], bot_grid[i, -1], bot_grid[i + 1, -1], top_grid[i + 1, -1], part, trim_col or col)
    for k in range(nz - 1):
        b.quad(top_grid[0, k], bot_grid[0, k], bot_grid[0, k + 1], top_grid[0, k + 1], part, col)
        b.quad(bot_grid[-1, k], top_grid[-1, k], top_grid[-1, k + 1], bot_grid[-1, k + 1], part, trim_col or col)


def add_contoured_backrest(b, x_bot, x_top, y_bot, y_top, z0, z1, thick, part, col, trim_col=None, bolster=16.0, ribs=4):
    ny, nz = b.segs(10, 6), b.segs(9, 6)
    ys = np.linspace(y_bot, y_top, ny)
    zs = np.linspace(z0, z1, nz)
    front_grid = np.zeros((ny, nz), int)
    back_grid = np.zeros((ny, nz), int)
    zc = (z0 + z1) / 2
    zh = max(1.0, (z1 - z0) / 2)
    for j, y in enumerate(ys):
        t = (y - y_bot) / max(1.0, y_top - y_bot)
        x_base = x_bot + (x_top - x_bot) * t + 9.0 * math.sin(math.pi * t)
        w_scale = 1.0 - 0.05 * (t ** 2)
        for k, z0_val in enumerate(zs):
            w = (z0_val - zc) / zh
            z = zc + (z0_val - zc) * w_scale
            y_cur = y - 14.0 * (w ** 4) * (t ** 3)
            wrap = bolster * (w ** 2) * (1.0 - 0.25 * (t ** 2))
            puff = 4.8 * abs(math.sin(ribs * math.pi * t)) * (1.0 - w ** 2) if (ribs > 0 and abs(w) < 0.84) else 0.0
            edge = max(0.25, 1.0 - 0.15 * (w ** 4))
            xf = x_base + (thick * 0.55 + wrap + puff) * edge
            xb = x_base - (thick * 0.45 - wrap * 0.35) * edge
            front_grid[j, k] = b.v((xf, y_cur, z))
            back_grid[j, k] = b.v((xb, y_cur, z))

    for j in range(ny - 1):
        for k in range(nz - 1):
            is_seam = (ribs > 0 and j in (2, 5, 7) and 0 < k < nz - 2)
            c_use = (trim_col or col) if (trim_col and (k == 0 or k == nz - 2)) or is_seam else col
            b.quad(front_grid[j, k], front_grid[j, k + 1], front_grid[j + 1, k + 1], front_grid[j + 1, k], part, c_use)
            b.quad(back_grid[j, k], back_grid[j + 1, k], back_grid[j + 1, k + 1], back_grid[j, k + 1], part, col)
    for j in range(ny - 1):
        b.quad(back_grid[j, 0], front_grid[j, 0], front_grid[j + 1, 0], back_grid[j + 1, 0], part, trim_col or col)
        b.quad(front_grid[j, -1], back_grid[j, -1], back_grid[j + 1, -1], front_grid[j + 1, -1], part, trim_col or col)
    for k in range(nz - 1):
        b.quad(front_grid[0, k], back_grid[0, k], back_grid[0, k + 1], front_grid[0, k + 1], part, col)
        b.quad(back_grid[-1, k], front_grid[-1, k], front_grid[-1, k + 1], back_grid[-1, k + 1], part, trim_col or col)


def add_wheel_fender(b, cx, cy, z_inner, side, R, a0_deg, a1_deg, width, seat_y, col, edge_col=None, part="frame"):
    n = b.segs(14, 9)
    angs = np.linspace(math.radians(a0_deg), math.radians(a1_deg), n)
    z0 = z_inner
    z1 = z_inner + width * side
    r_outer = R + 14.0
    pts_out_0, pts_out_1, pts_base_0 = [], [], []
    for a in angs:
        ca, sa = math.cos(a), math.sin(a)
        px, py = cx + r_outer * ca, cy + r_outer * sa
        pts_out_0.append(b.v((px, py, z0)))
        pts_out_1.append(b.v((px, py, z1)))
        bx = np.clip(px, cx - 25.0, cx + 225.0)
        by = min(py - 20.0, max(cy + 15.0, seat_y))
        pts_base_0.append(b.v((bx, by, z0)))
    for i in range(n - 1):
        b.quad(pts_out_0[i], pts_out_0[i + 1], pts_out_1[i + 1], pts_out_1[i], part, edge_col or col)
        b.quad(pts_base_0[i], pts_out_0[i], pts_out_0[i + 1], pts_base_0[i + 1], part, col)


def add_manual_rear_wheel(b, cx, cy, z, R, style="wire", rim_col=(200, 205, 218),
                          pushrim_col=(192, 198, 212), hub_col=(165, 170, 184),
                          tire_col=(38, 40, 46), spoke_col=(192, 198, 210),
                          n_spokes=18, has_valve=True):
    sgn = 1 if z > 0 else -1
    add_torus(b, (cx, cy, z), R - 17.0, 17.0, "tire", tire_col, segs=36, sides=8,
              inner=("tube", (136, 58, 50)))
    add_torus(b, (cx, cy, z), R - 38.0, 12.5, "rim", rim_col, segs=36, sides=6, z_scale=1.25)

    r_inner = 30.0
    r_outer = R - 44.0
    if style == "mag8":
        # 8 sculpted composite Mag spokes with raised ridge so all 8 spokes catch light at every angle!
        ridge_col = tuple(min(255, c + 24) for c in spoke_col)
        for i in range(8):
            a = 2 * math.pi * i / 8 + 0.18
            ca, sa = math.cos(a), math.sin(a)
            p0 = (cx + r_inner * ca, cy + r_inner * sa, z)
            p1 = (cx + r_outer * ca, cy + r_outer * sa, z)
            add_spline_tube(b, [p0, p1], [15.0, 11.0], "spokes", spoke_col, sides=8, smooth=0, caps=False)
            # Outer highlight rib on both sides of the Mag spoke
            for sz in (-1, 1):
                q0 = (cx + (r_inner + 4.0) * ca, cy + (r_inner + 4.0) * sa, z + 6.5 * sz)
                q1 = (cx + (r_outer - 4.0) * ca, cy + (r_outer - 4.0) * sa, z + 5.0 * sz)
                add_spline_tube(b, [q0, q1], [6.5, 4.5], "spokes", ridge_col, sides=5, smooth=0, caps=False)
    elif style == "mag12":
        # 12 thin straight composite Mag spokes (Invacare 9000 style), small hub
        for i in range(12):
            a = 2 * math.pi * i / 12 + 0.13
            ca, sa = math.cos(a), math.sin(a)
            p0 = (cx + 24.0 * ca, cy + 24.0 * sa, z + 6.0 * (1 if i % 2 else -1))
            p1 = (cx + (r_outer + 4.0) * ca, cy + (r_outer + 4.0) * sa, z)
            add_spline_tube(b, [p0, p1], [9.0, 7.0], "spokes", spoke_col, sides=6, smooth=0, caps=False)
    elif style == "paired":
        sp_r = 1.30 if b.lod < 0.9 else 2.2
        for pair in range(8):
            base_a = 2 * math.pi * pair / 8
            for sub in (-1, 1):
                a_rim = base_a + sub * 0.085
                a_hub = base_a + sub * 0.20
                fz = z + (20.0 if sub > 0 else -20.0)
                h_pt = (cx + 30.0 * math.cos(a_hub), cy + 30.0 * math.sin(a_hub), fz)
                r_pt = (cx + r_outer * math.cos(a_rim), cy + r_outer * math.sin(a_rim), z)
                add_spline_tube(b, [h_pt, r_pt], sp_r, "spokes", spoke_col, sides=4, smooth=0, caps=False)
    else:
        sp_r = 2.5 if n_spokes >= 32 else (1.20 if b.lod < 0.9 else 2.1)
        for i in range(n_spokes):
            a = 2 * math.pi * i / n_spokes
            fz = z + (22.0 if i % 2 == 0 else -22.0)
            a_hub = a + (0.30 if i % 2 == 0 else -0.30)
            h_pt = (cx + 30.0 * math.cos(a_hub), cy + 30.0 * math.sin(a_hub), fz)
            r_pt = (cx + r_outer * math.cos(a), cy + r_outer * math.sin(a), z)
            add_spline_tube(b, [h_pt, r_pt], sp_r, "spokes", spoke_col, sides=4, smooth=0, caps=False)

    add_spline_tube(b, [(cx, cy, z - 26.0), (cx, cy, z + 26.0)], 24.0, "axle", hub_col, sides=10, smooth=0, caps=True)
    for fz in (z - 22.0, z + 22.0):
        add_torus(b, (cx, cy, fz), 27.0, 5.5, "axle", hub_col, segs=14, sides=5)
    for fz in (z - 29.0, z + 29.0):
        add_torus(b, (cx, cy, fz), 16.5, 6.5, "bearing", (218, 182, 92), segs=14, sides=5)
    add_spline_tube(b, [(cx, cy, z - 55.0 * sgn), (cx, cy, z + 44.0 * sgn)], 8.5, "axle", (165, 172, 186), sides=8, smooth=0, caps=True)
    add_spline_tube(b, [(cx, cy, z + 42.0 * sgn), (cx, cy, z + 52.0 * sgn)], 11.0, "axle", (44, 46, 54), sides=8, smooth=0, caps=True)

    if has_valve:
        va = -math.pi * 0.42
        v0 = (cx + (R - 50.0) * math.cos(va), cy + (R - 50.0) * math.sin(va), z)
        v1 = (cx + (R - 18.0) * math.cos(va), cy + (R - 18.0) * math.sin(va), z)
        add_spline_tube(b, [v0, v1], 6.0, "valve", (228, 190, 88), sides=6, smooth=0, caps=True)

    pz = z + 30.0 * sgn
    add_torus(b, (cx, cy, pz), R - 48.0, 6.5, "rear_wheel", pushrim_col, segs=36, sides=6)
    for i in range(6):
        ang = 2 * math.pi * i / 6 + 0.25
        px, py = cx + (R - 46.0) * math.cos(ang), cy + (R - 46.0) * math.sin(ang)
        add_spline_tube(b, [(px, py, z + 6.0 * sgn), (px, py, pz)], 3.8, "rear_wheel", pushrim_col, sides=5, smooth=0, caps=False)


def add_front_caster(b, cx, cy, z, R, stem_top, fork_col=(180, 186, 198), tire_col=(38, 40, 46),
                     hub_col=(60, 62, 70), n_spokes=5, part_wheel="caster", part_stem="caster_stem",
                     three_window=False, stem_col=None):
    add_torus(b, (cx, cy, z), R - 13.0, 13.0, part_wheel, tire_col, segs=22, sides=6)
    add_spline_tube(b, [(cx, cy, z - 14.0), (cx, cy, z + 14.0)], R * 0.28, part_wheel, hub_col, sides=10, smooth=0, caps=True)
    for i in range(n_spokes):
        a = 2 * math.pi * i / n_spokes
        p1 = (cx + (R - 18.0) * math.cos(a), cy + (R - 18.0) * math.sin(a), z)
        add_spline_tube(b, [(cx, cy, z), p1], 5.0, part_wheel, hub_col, sides=5, smooth=0, caps=False)
    add_spline_tube(b, [(cx, cy, z - 26.0), (cx, cy, z + 26.0)], 6.5, part_wheel, (190, 196, 208), sides=6, smooth=0, caps=True)

    sx, sy = stem_top
    crown_y = sy - 38.0
    for fz in (z - 21.0, z + 21.0):
        pts = [(sx, crown_y, fz), ((sx + cx) * 0.5 + 8.0, (crown_y + cy) * 0.5, fz), (cx, cy, fz)]
        add_spline_tube(b, pts, 7.5 if not three_window else 9.0, part_stem, fork_col, sides=6, smooth=2, caps=True)
    add_rounded_box(b, sx - 16.0, sx + 16.0, crown_y - 8.0, crown_y + 10.0, z - 25.0, z + 25.0, part_stem, fork_col, bevel=3.0)
    add_spline_tube(b, [(sx, crown_y + 6.0, z), (sx, sy + 24.0, z)], 14.5, part_stem,
                    stem_col if stem_col is not None else ((52, 54, 62) if three_window else fork_col),
                    sides=10, smooth=0, caps=True)
    add_spline_tube(b, [(sx, sy + 22.0, z), (sx, sy + 32.0, z)], 11.0, part_stem, (200, 205, 218), sides=6, smooth=0, caps=True)


def add_wheel_brake(b, bx, by, bz, sgn, col_clamp=(70, 74, 84), col_knob=(215, 72, 64)):
    add_rounded_box(b, bx - 22.0, bx + 22.0, by - 16.0, by + 16.0, bz - 14.0, bz + 14.0, "brake", col_clamp, bevel=3.0)
    add_rounded_box(b, bx - 38.0, bx - 8.0, by - 10.0, by + 10.0,
                    bz if sgn > 0 else bz - 36.0, bz + 36.0 if sgn > 0 else bz, "brake", (44, 46, 54), bevel=2.0)
    add_spline_tube(b, [(bx + 4.0, by + 8.0, bz), (bx + 28.0, by + 95.0, bz)], 7.0, "brake", (185, 190, 202), sides=6, smooth=0, caps=True)
    add_spline_tube(b, [(bx + 24.0, by + 82.0, bz), (bx + 36.0, by + 124.0, bz)], 12.5, "brake", col_knob, sides=8, smooth=0, caps=True)


def tilt_new_verts(b, i0, cx, cy, cz, angle):
    """Наклоняет вершины, добавленные после индекса i0, вокруг оси X через (cx, cy, cz) (развал колеса).
    angle > 0 наклоняет верх к центру коляски."""
    sgn = 1.0 if cz > 0 else -1.0
    a = -angle * sgn
    ca, sa = math.cos(a), math.sin(a)
    for i in range(i0, len(b.verts)):
        x, y, z = b.verts[i]
        dy, dz = y - cy, z - cz
        b.verts[i] = (x, round(cy + dy * ca - dz * sa, 1), round(cz + dy * sa + dz * ca, 1))


# --------------------------------------------------------------------------- #
# 1 & 2. Invacare 9000 (basic) & Invacare 9000 XDT (troll)
# --------------------------------------------------------------------------- #
FOLD_FX, FOLD_FY = 200.0, 188.0
FOLD_TR = 12.5
FOLD_DZ, FOLD_XF, FOLD_YS = 20.0, 470.0, 466.0


def build_chair_folding(lod=1.0, is_troll=False):
    """Invacare 9000 / 9000 XDT по арту: чёрные 12-спицевые маг-колёса, хромированная складная рама,
    подлокотники-«петли» с чёрными боковинами, далеко вынесенные откидные подножки (две пластины)."""
    b = TriMeshBuilder(lod)
    CHROME = (196, 198, 204)
    NAVY = (40, 54, 104)
    NAVY_TRIM = (28, 36, 72)
    DARK = (40, 40, 44)
    PANEL_DARK = (36, 36, 40)
    MAG = (50, 48, 50)
    TIRE_COL = (32, 32, 34)
    GRIP = (34, 34, 38)

    zf_abs = (252.0 if is_troll else 232.0) + FOLD_DZ
    zw_abs = (292.0 if is_troll else 272.0) + FOLD_DZ
    wx, wy, wR = 45.0, 305.0, 305.0
    x_post = wx - 46.0            # задняя стойка (спинка)
    x_front = FOLD_XF             # передняя стойка / шток кастора
    y_seat = FOLD_YS
    FX, FY = FOLD_FX, FOLD_FY     # вынос и высота подножки

    for s in (-1, 1):
        zf = zf_abs * s
        zw = zw_abs * s
        add_manual_rear_wheel(b, wx, wy, zw, wR, style="mag12",
                              rim_col=(46, 44, 46), pushrim_col=(62, 62, 66), hub_col=MAG,
                              tire_col=TIRE_COL, spoke_col=MAG, has_valve=(not is_troll))
        # задняя стойка + ручка толкателя (ручки уходят назад почти горизонтально)
        add_spline_tube(b, [
            (x_post + 1.0, 300.0, zf),
            (x_post - 2.0, 520.0, zf),
            (x_post - 18.0, 880.0, zf),
            (x_post - 30.0, 912.0, zf),
            (x_post - 95.0, 930.0, zf)
        ], FOLD_TR, "frame", CHROME, sides=8, smooth=2)
        add_spline_tube(b, [(x_post - 52.0, 921.0, zf), (x_post - 128.0, 938.0, zf)], 16.0, "frame", GRIP, sides=8, smooth=0)

        # боковая рама: сиденье -> передняя стойка -> гнездо кастора
        add_spline_tube(b, [
            (x_post, y_seat - 2.0, zf),
            (x_front - 22.0, y_seat - 2.0, zf),
            (x_front, y_seat - 22.0, zf),
            (x_front, 262.0, zf)
        ], FOLD_TR, "frame", CHROME, sides=8, smooth=2)
        # нижняя тяга
        add_spline_tube(b, [(x_post + 2.0, 322.0, zf), (x_front, 322.0, zf)], FOLD_TR - 0.5, "frame", CHROME, sides=8, smooth=0)
        add_rounded_box(b, wx - 50.0, wx + 22.0, wy - 22.0, wy + 22.0,
                        zf - 8.0, zw - 10.0 if s > 0 else zf + 8.0, "frame", CHROME, bevel=4.0)

        # подлокотник «петлёй»: от спинки вперёд и вниз к переднему краю сиденья
        y_arm = 708.0
        add_spline_tube(b, [
            (x_post - 4.0, y_arm, zf),
            (262.0, y_arm, zf),
            (292.0, y_arm - 22.0, zf),
            (318.0, 600.0, zf),
            (338.0, 525.0, zf),
            (352.0, y_seat, zf)
        ], FOLD_TR - 0.5, "frame", CHROME, sides=8, smooth=2)
        add_rounded_box(b, x_post + 12.0, 278.0, y_arm + 8.0, y_arm + 44.0, zf - 30.0, zf + 30.0, "frame", DARK, bevel=9.0)
        # чёрная боковина (одёжный щиток) с закруглённым низом спереди
        add_rounded_box(b, x_post + 10.0, 250.0, y_seat + 8.0, y_arm - 6.0, zf - 4.0, zf + 4.0, "frame", PANEL_DARK, bevel=2.0)
        add_rounded_box(b, 250.0, 296.0, y_seat + 60.0, y_arm - 6.0, zf - 4.0, zf + 4.0, "frame", PANEL_DARK, bevel=2.0)

        # откидная подножка: гнездо, горизонталь вперёд, крутой спуск к пластине
        add_rounded_box(b, x_front - 6.0, x_front + 40.0, y_seat - 46.0, y_seat - 6.0,
                        zf - 16.0, zf + 16.0, "footrest", DARK, bevel=4.0)
        zh = zf * 0.97
        add_spline_tube(b, [
            (x_front + 20.0, y_seat - 26.0, zf),
            (x_front + 95.0, y_seat - 30.0, zh),
            (x_front + 125.0, y_seat - 62.0, zh),
            (x_front + FX - 8.0, FY + 70.0, zh),
            (x_front + FX, FY + 30.0, zh)
        ], FOLD_TR - 0.5, "footrest", CHROME, sides=8, smooth=2)
        # кронштейн пластины (чёрный) + пластина
        xb = x_front + FX
        add_rounded_box(b, xb - 22.0, xb + 26.0, FY + 16.0, FY + 88.0, zh - 18.0 * s, zh + 14.0 * s, "footrest", DARK, bevel=5.0)
        z_in = 30.0 * s
        z_out = (zf_abs - 22.0) * s
        za, zb = min(z_in, z_out), max(z_in, z_out)
        add_rounded_box(b, xb - 20.0, xb + 185.0, FY, FY + 20.0, za, zb, "footrest", DARK,
                        top_col=(56, 56, 62), bevel=4.0)
        for rx in (xb + 25.0, xb + 60.0, xb + 95.0, xb + 130.0):
            add_rounded_box(b, rx - 5.0, rx + 5.0, FY + 19.0, FY + 24.0, za + 14.0, zb - 14.0, "footrest", (66, 66, 72), bevel=1.0)
        add_spline_tube(b, [(xb + 180.0, FY + 16.0, za + 4.0), (xb + 180.0, FY + 16.0, zb - 4.0)], 9.5, "footrest", CHROME,
                        sides=8, smooth=0, caps=True)

        add_front_caster(b, x_front - 6.0, 106.0, (zf_abs - 4.0) * s, 106.0, (x_front, 262.0),
                         fork_col=DARK, tire_col=TIRE_COL, hub_col=(46, 46, 50), n_spokes=6, stem_col=CHROME)
        add_wheel_brake(b, 278.0, y_seat + 8.0, (zf_abs + 22.0) * s, s, col_clamp=CHROME, col_knob=(40, 40, 44))

        for bx, by in ((x_post + 2.0, 322.0), (x_post, y_seat), (352.0, y_seat + 18.0), (x_front, y_seat - 30.0),
                       (x_front, 322.0)):
            add_spline_tube(b, [(bx, by, zf - 16.0 * s), (bx, by, zf + 18.0 * s)], 9.5, "bolts",
                            (218, 182, 92), sides=6, smooth=0, caps=True)

    # крестовина складывания (у XDT — двойная)
    x_positions = [150.0, 300.0] if is_troll else [215.0]
    for xp in x_positions:
        for s in (-1, 1):
            add_spline_tube(b, [(xp, 322.0, -zf_abs * s), (xp + 28.0, y_seat - 6.0, zf_abs * s)], 10.5, "frame", CHROME, sides=8, smooth=0)
        add_spline_tube(b, [(xp - 8.0, 404.0, 0.0), (xp + 36.0, 404.0, 0.0)], 11.0, "bolts", (218, 182, 92), sides=6, smooth=0)

    # спинка: тёмно-синяя стёганая обивка, сиденье — тонкий гамак
    add_contoured_backrest(b, x_post - 2.0, x_post - 20.0, y_seat + 10.0, 880.0, -zf_abs + 13.0, zf_abs - 13.0,
                           24.0, "seat", NAVY, trim_col=NAVY_TRIM, bolster=8.0, ribs=4)
    add_rounded_box(b, x_post + 8.0, x_front - 18.0, y_seat - 6.0, y_seat + 10.0, -zf_abs + 10.0, zf_abs - 10.0,
                    "seat", NAVY, top_col=NAVY, bevel=4.0)
    if is_troll:
        add_contoured_cushion(b, x_post + 22.0, x_front - 26.0, y_seat + 8.0, y_seat + 40.0, -zf_abs + 16.0, zf_abs - 16.0,
                              "cushion", (46, 62, 116), trim_col=NAVY_TRIM, bolster=8.0, ribs=3)
        for s in (-1, 1):
            vx, vy, vz = x_front - 40.0, y_seat + 22.0, (zf_abs - 48.0) * s
            add_spline_tube(b, [(vx - 14.0, vy, vz), (vx + 24.0, vy - 5.0, vz + 10.0 * s)], 9.5, "valve", (42, 44, 52), sides=8, smooth=0)
            add_spline_tube(b, [(vx + 18.0, vy - 4.0, vz + 8.0 * s), (vx + 38.0, vy - 7.0, vz + 14.0 * s)], 11.5, "valve", (228, 188, 84), sides=8, smooth=0)
    else:
        add_contoured_cushion(b, x_post + 20.0, x_front - 26.0, y_seat + 8.0, y_seat + 22.0, -zf_abs + 14.0, zf_abs - 14.0,
                              "cushion", NAVY, trim_col=NAVY_TRIM, bolster=5.0, ribs=3)
    return b


# --------------------------------------------------------------------------- #
# 3, 4, 5, 6. Active Manual Wheelchairs (elf, dwarf, fairy, orc)
# --------------------------------------------------------------------------- #
ACT = {
    ("elf", "y_sr"): 428.0, ("elf", "y_sf"): 466.0, ("elf", "fp_back"): 32.0,
    ("dwarf", "y_sr"): 436.0, ("dwarf", "y_sf"): 456.0, ("dwarf", "x_leg"): 488.0, ("dwarf", "post_back"): 92.0,
    ("fairy", "zf"): 168.0, ("fairy", "dzw"): 50.0, ("fairy", "y_sr"): 398.0, ("fairy", "y_sf"): 420.0,
    ("fairy", "back_top"): 700.0, ("fairy", "post_back"): 128.0, ("fairy", "arm_len"): 220.0, ("fairy", "arm_h"): 215.0,
    ("orc", "y_sr"): 428.0, ("orc", "y_sf"): 468.0, ("orc", "x_leg"): 518.0, ("orc", "post_back"): 102.0, ("orc", "fp_back"): 36.0,
}


def _act(variant, name, default):
    return ACT.get((variant, name), default)


def build_chair_active(variant="elf", lod=1.0):
    """Активные коляски по арту:
    elf   — Progeo Ego: жёсткая монотрубная рама (сиденье -> плавный загиб -> прямая передняя стойка),
            кастор на кронштейне позади стойки, одна платформа подножки на чёрных вставках;
    dwarf — Progeo Tekna Advance: складная, графитовая рама, медные вилки/обода, отдельная петля подножки,
            две откидные пластины, Т-подлокотники;
    fairy — Progeo Exelle Junior: розовая закрытая рама с перфорированными стойками, антиопрокидыватель,
            одна платформа, подлокотники на боковинах;
    orc   — Progeo Noir 2.0: толстая карбоновая «J»-рама, кастор на ответвлении от стойки, платформа внизу."""
    b = TriMeshBuilder(lod)
    TIRE_COL = (34, 34, 38)
    UPH = (42, 42, 46)
    UPH_TRIM = (56, 56, 62)
    CUSH = (48, 48, 54)
    BLACK = (36, 36, 40)
    BOLT = (218, 182, 92)
    arms = False
    taper = 1.0
    camber = 3.0          # развал задних колёс, градусы
    post_back = 34.0      # насколько спинка позади оси колеса
    seat_gap = 30.0       # от края подушки до передней стойки
    cush_h = 52.0         # толщина подушки

    if variant == "elf":
        LIME = (172, 204, 38)
        FR_COL = LIME; ACCENT = LIME; RIM_COL = LIME
        PUSHRIM_COL = (52, 54, 60); HUB_COL = LIME; FORK_COL = LIME
        SPOKE_COL = (88, 90, 98); SPOKE_STYLE = "wire"
        zf_abs, zw_abs = 205.0, 258.0
        wx, wR = 40.0, 305.0
        y_sr, y_sf = 448.0, 478.0           # высота рамы сиденья сзади / спереди
        x_leg, y_leg_bot = 510.0, 215.0     # передняя стойка
        back_top = 742.0
        tube_r = 16.0
        taper = 0.8
        post_back = 90.0
        seat_gap = 80.0
        cush_h = 38.0
    elif variant == "dwarf":
        COPPER = (204, 114, 52)
        FR_COL = (58, 58, 62); ACCENT = COPPER; RIM_COL = COPPER
        PUSHRIM_COL = (56, 56, 62); HUB_COL = COPPER; FORK_COL = COPPER
        SPOKE_COL = (190, 194, 204); SPOKE_STYLE = "wire"
        zf_abs, zw_abs = 222.0, 272.0
        wx, wR = 40.0, 305.0
        y_sr, y_sf = 462.0, 478.0
        x_leg, y_leg_bot = 500.0, 250.0
        back_top = 820.0
        tube_r = 13.0
        arms = True
        post_back = 80.0
    elif variant == "fairy":
        PINK = (236, 176, 186)
        FR_COL = PINK; ACCENT = PINK; RIM_COL = PINK
        PUSHRIM_COL = (240, 186, 196); HUB_COL = (190, 194, 204); FORK_COL = PINK
        SPOKE_COL = (192, 196, 206); SPOKE_STYLE = "wire"
        CUSH = (46, 46, 52)
        zf_abs, zw_abs = 190.0, 240.0
        wx, wR = 55.0, 280.0
        y_sr, y_sf = 420.0, 440.0
        x_leg, y_leg_bot = 440.0, 118.0
        back_top = 712.0
        tube_r = 13.0
        arms = True
        post_back = 120.0
    else:  # orc: Progeo Noir 2.0
        CARBON = (62, 57, 54)
        FR_COL = CARBON; ACCENT = (92, 82, 72); RIM_COL = (54, 52, 54)
        PUSHRIM_COL = (70, 66, 64); HUB_COL = (60, 58, 60); FORK_COL = CARBON
        SPOKE_COL = (138, 138, 144); SPOKE_STYLE = "paired"
        zf_abs, zw_abs = 210.0, 262.0
        wx, wR = 45.0, 305.0
        y_sr, y_sf = 452.0, 476.0
        x_leg, y_leg_bot = 530.0, 108.0
        back_top = 785.0
        tube_r = 18.0
        taper = 0.75
        post_back = 90.0
        seat_gap = 95.0
        cush_h = 34.0
        CARBON_HI = (80, 72, 66)
        FR_COL = CARBON_HI

    wy = wR
    zf_abs = _act(variant, "zf", zf_abs)
    zw_abs = zf_abs + _act(variant, "dzw", zw_abs - zf_abs)
    y_sr = _act(variant, "y_sr", y_sr)
    y_sf = _act(variant, "y_sf", y_sf)
    x_leg = _act(variant, "x_leg", x_leg)
    back_top = _act(variant, "back_top", back_top)
    camber = _act(variant, "camber", camber)
    x_post = wx - _act(variant, "post_back", post_back)
    y_seat = (y_sr + y_sf) * 0.5
    taper = _act(variant, "taper", taper)       # сужение рамы к подножке (жёсткие рамы)
    zl_abs = zf_abs * taper

    for s in (-1, 1):
        zf = zf_abs * s
        zw = zw_abs * s
        zl = zl_abs * s
        i_wheel = len(b.verts)
        add_manual_rear_wheel(b, wx, wy, zw, wR, style=SPOKE_STYLE,
                              rim_col=RIM_COL, pushrim_col=PUSHRIM_COL, hub_col=HUB_COL,
                              tire_col=TIRE_COL, spoke_col=SPOKE_COL, n_spokes=24 if variant == "elf" else 18,
                              has_valve=True)
        tilt_new_verts(b, i_wheel, wx, wy, zw, math.radians(camber))
        add_wheel_fender(b, wx, wy, (zf_abs + 6.0) * s, s, wR, 22.0, 150.0, 24.0, y_sr,
                         col=(34, 34, 38), edge_col=(52, 52, 58), part="frame")

        # задняя стойка спинки + ручка толкателя назад
        # (длина ручки по варианту: у elf — короткие «пеньки», у остальных — полноценные;
        #  у fairy ручка загибается вверх, как на арте)
        hx = {"elf": 46.0, "fairy": 108.0, "dwarf": 92.0, "orc": 78.0}[variant]
        hy = {"elf": 24.0, "fairy": 46.0, "dwarf": 26.0, "orc": 24.0}[variant]
        add_spline_tube(b, [
            (x_post + 4.0, y_sr - 30.0, zf),
            (x_post - 4.0, (y_sr + back_top) * 0.5, zf),
            (x_post - 14.0, back_top, zf),
            (x_post - 26.0, back_top + 18.0, zf),
            (x_post - 26.0 - hx, back_top + hy, zf)
        ], 11.5, "frame", BLACK if variant != "dwarf" else FR_COL, sides=8, smooth=2)
        add_spline_tube(b, [(x_post - 34.0, back_top + 22.0, zf), (x_post - 34.0 - hx, back_top + hy + 2.0, zf)],
                        15.0, "frame", (30, 30, 34), sides=8, smooth=0)

        # крепление оси к раме
        if variant == "elf":
            # Ego: гнездо оси — короткая салатовая втулка + стойка к раме сиденья
            add_spline_tube(b, [(wx, wy, zf - 30.0 * s), (wx, wy, zw - 34.0 * s)], 17.0, "frame", ACCENT, sides=10, smooth=0)
            add_rounded_box(b, wx - 26.0, wx + 50.0, wy - 22.0, wy + 26.0, zf - 14.0, zf + 14.0, "frame", ACCENT, bevel=8.0)
            add_spline_tube(b, [(wx - 8.0, wy + 20.0, zf), (x_post + 30.0, y_sr - 4.0, zf)], 12.0, "frame", (40, 40, 44),
                            sides=8, smooth=0)
        elif variant == "dwarf":
            # Tekna: медная наклонная пластина оси (от втулки вперёд-вверх к раме)
            add_spline_tube(b, [(wx - 10.0, wy, zf), (wx + 120.0, wy + 62.0, zf)], [20.0, 15.0], "frame", ACCENT,
                            sides=8, smooth=0)
            add_spline_tube(b, [(wx, wy, zf - 24.0 * s), (wx, wy, zw - 34.0 * s)], 15.0, "frame", ACCENT, sides=10, smooth=0)
            add_spline_tube(b, [(wx + 110.0, wy + 58.0, zf), (wx + 120.0, y_sr - 4.0, zf)], 11.0, "frame", FR_COL,
                            sides=8, smooth=0)
        else:
            add_rounded_box(b, wx - 32.0, wx + 40.0, wy - 26.0, y_sr - 6.0, zf - 9.0, zf + 9.0, "frame",
                            FR_COL, bevel=6.0)

        if variant == "elf":
            # монотруба: рама сиденья -> большой загиб -> вертикальная стойка
            add_spline_tube(b, [
                (x_post - 6.0, y_sr, zf),
                (x_leg - 160.0, y_sf - 2.0, zf),
                (x_leg - 62.0, y_sf + 6.0, zl),
                (x_leg - 6.0, y_sf - 52.0, zl),
                (x_leg, y_sf - 150.0, zl),
                (x_leg, y_leg_bot, zl)
            ], tube_r, "frame", FR_COL, sides=10, smooth=3)
            # чёрная вставка-подвеска подножки
            add_spline_tube(b, [(x_leg, y_leg_bot + 20.0, zl), (x_leg + 4.0, 112.0, zl)], 11.0, "footrest", BLACK,
                            sides=8, smooth=0)
            # кронштейн кастора: пластина от стойки назад-наружу
            cx_c, cz_c, c_R, c_top = x_leg - 92.0, zl + 40.0 * s, 64.0, 238.0
            add_spline_tube(b, [(x_leg, 262.0, zl), (x_leg - 45.0, 252.0, zl + 20.0 * s), (cx_c, 246.0, cz_c)],
                            [14.0, 11.0], "frame", FR_COL, sides=8, smooth=2)
            add_spline_tube(b, [(x_leg, 232.0, zl), (x_leg - 45.0, 228.0, zl + 20.0 * s), (cx_c, 224.0, cz_c)],
                            [11.0, 9.0], "frame", FR_COL, sides=8, smooth=2)
            fp = (x_leg - _act(variant, "fp_back", 80.0), x_leg + _act(variant, "fp_len", 40.0), 96.0, 114.0)
        elif variant == "orc":
            # толстая «J»-рама: сиденье -> загиб -> стойка до пола, ответвление к кастору
            add_spline_tube(b, [
                (x_post - 6.0, y_sr, zf),
                (x_leg - 165.0, y_sf - 2.0, zf),
                (x_leg - 64.0, y_sf + 8.0, zl),
                (x_leg - 6.0, y_sf - 56.0, zl),
                (x_leg + 6.0, 260.0, zl),
                (x_leg + 8.0, 140.0, zl),
                (x_leg + 20.0, y_leg_bot, zl)
            ], tube_r, "frame", FR_COL, sides=10, smooth=3)
            cx_c, cz_c, c_R, c_top = x_leg - 95.0, zl + 36.0 * s, 60.0, 160.0
            add_spline_tube(b, [
                (x_leg + 4.0, 255.0, zl),
                (x_leg - 40.0, 205.0, zl + 18.0 * s),
                (cx_c, 172.0, cz_c),
                (cx_c, c_top - 4.0, cz_c)
            ], 14.0, "frame", FR_COL, sides=9, smooth=2)
            fp = (x_leg - _act(variant, "fp_back", 100.0), x_leg + _act(variant, "fp_len", 30.0), 84.0, 100.0)
        elif variant == "dwarf":
            add_spline_tube(b, [
                (x_post - 6.0, y_sr, zf),
                (x_leg - 80.0, y_sf, zf),
                (x_leg - 10.0, y_sf - 16.0, zf),
                (x_leg, y_sf - 70.0, zf),
                (x_leg, y_leg_bot, zf)
            ], tube_r, "frame", FR_COL, sides=8, smooth=2)
            add_spline_tube(b, [(wx + 20.0, 318.0, zf), (x_leg - 60.0, 300.0, zf), (x_leg, 268.0, zf)],
                            11.5, "frame", FR_COL, sides=8, smooth=2)
            # отдельная петля подвески подножки
            zh = (zf_abs - 6.0) * s
            hx = x_leg + _act(variant, "hang_dx", 20.0)
            fl = _act(variant, "fp_len", 100.0)
            add_spline_tube(b, [
                (x_leg - 20.0, y_sf - 6.0, zh),
                (hx + 50.0, y_sf + 6.0, zh),
                (hx + 92.0, y_sf - 30.0, zh),
                (hx + 112.0, 300.0, zh),
                (hx + 128.0, 140.0, zh)
            ], 12.0, "footrest", FR_COL, sides=8, smooth=2)
            add_rounded_box(b, x_leg - 14.0, x_leg + 12.0, 330.0, 352.0, zf - 16.0, zf + 16.0, "frame", (44, 44, 48), bevel=4.0)
            add_spline_tube(b, [(x_leg, 340.0, zf), (hx + 104.0, 340.0, zh)], 9.0, "frame", FR_COL, sides=6, smooth=0)
            cx_c, cz_c, c_R, c_top = x_leg, (zf_abs + 4.0) * s, 70.0, y_leg_bot
            fp = None
            za, zb = sorted([24.0 * s, (zf_abs - 8.0) * s])
            add_rounded_box(b, hx + 100.0, hx + 100.0 + fl, 112.0, 132.0, za, zb, "footrest", BLACK,
                            top_col=(56, 56, 62), bevel=4.0)
            add_rounded_box(b, hx + 110.0, hx + 140.0, 128.0, 170.0, zh - 12.0, zh + 12.0, "footrest", BLACK, bevel=3.0)
        else:  # fairy
            add_spline_tube(b, [
                (x_post - 6.0, y_sr, zf),
                (x_leg - 85.0, y_sf, zf),
                (x_leg - 18.0, y_sf - 14.0, zf),
                (x_leg, y_sf - 75.0, zf),
                (x_leg + 14.0, 250.0, zf),
                (x_leg + 26.0, y_leg_bot, zf)
            ], tube_r, "frame", FR_COL, sides=8, smooth=2)
            # нижняя дуга закрытой рамы
            add_spline_tube(b, [
                (wx - 10.0, wy + 8.0, zf),
                (wx + 120.0, 262.0, zf),
                (x_leg - 120.0, 255.0, zf),
                (x_leg - 52.0, 268.0, zf),
                (x_leg - 30.0, y_sf - 50.0, zf),
                (x_leg - 24.0, y_sf - 4.0, zf)
            ], 11.0, "frame", FR_COL, sides=8, smooth=2)
            # отверстия регулировки на стойке
            for k in range(6):
                hy = 290.0 - k * 28.0
                hx = x_leg + 14.0 + (250.0 - hy) * (12.0 / 132.0)
                add_rounded_box(b, hx - 5.0, hx + 5.0, hy - 5.0, hy + 5.0, zf + 9.0 * s, zf + 14.0 * s, "frame",
                                (40, 34, 38), bevel=1.0)
            # антиопрокидыватель сзади
            za_t = zf - 18.0 * s
            add_spline_tube(b, [(wx - 10.0, wy - 30.0, za_t), (wx - 110.0, 185.0, za_t), (wx - 210.0, 95.0, za_t),
                                (wx - 268.0, 60.0, za_t)], 10.0, "frame", (36, 36, 40), sides=7, smooth=2)
            add_torus(b, (wx - 272.0, 40.0, za_t), 26.0, 14.0, "frame", TIRE_COL, segs=16, sides=6)
            cx_c, cz_c, c_R, c_top = x_leg - 70.0, (zf_abs + 26.0) * s, 58.0, 212.0
            z_lo, z_hi = sorted([zf - 10.0 * s, cz_c + 12.0 * s])
            add_rounded_box(b, x_leg - 70.0, x_leg + 22.0, 196.0, 226.0, z_lo, z_hi, "frame", FR_COL, bevel=6.0)
            fp = (x_leg - 32.0, x_leg + 90.0, 150.0, 170.0)

        add_front_caster(b, cx_c, c_R, cz_c, c_R, (cx_c, c_top),
                         fork_col=FORK_COL, tire_col=TIRE_COL, hub_col=(66, 66, 72), n_spokes=5, three_window=True,
                         stem_col=FR_COL if variant != "dwarf" else ACCENT)
        add_wheel_brake(b, wx + 222.0, y_sr - 96.0, (zf_abs + 18.0) * s, s,
                        col_clamp=(48, 48, 54), col_knob=(48, 48, 54))

        for bx, by in ((wx, wy + 18.0), (wx + 186.0, y_sr + 4.0), (cx_c, c_top - 10.0), (x_post, y_sr)):
            add_spline_tube(b, [(bx, by, zf - 15.0 * s), (bx, by, zf + 17.0 * s)], 8.5, "bolts",
                            BOLT, sides=6, smooth=0, caps=True)

        if arms:
            # подлокотник: стойка-гнездо + мягкая накладка
            ax0, ax1 = (x_post + 20.0, 255.0) if variant == "dwarf" else (x_post + 10.0, x_post + _act(variant, "arm_len", 200.0))
            ay = y_seat + _act(variant, "arm_h", 205.0 if variant == "dwarf" else 205.0)
            zc = zf + 8.0 * s
            add_spline_tube(b, [(ax0 + 70.0, y_seat - 10.0, zc), (ax0 + 70.0, ay, zc)], 12.0,
                            "frame", FR_COL if variant == "dwarf" else BLACK, sides=8, smooth=0)
            add_rounded_box(b, ax0, ax1, ay, ay + 40.0, zc - 32.0, zc + 32.0,
                            "frame", (64, 60, 58) if variant == "dwarf" else (44, 44, 48), bevel=10.0)
            if variant == "fairy":
                add_rounded_box(b, x_post + 20.0, ax1 - 30.0, y_seat + 10.0, ay, zf - 4.0, zf + 4.0, "frame", (40, 40, 44), bevel=2.0)

    # общие поперечины и подножки
    if variant in ("elf", "orc", "fairy"):
        add_spline_tube(b, [(wx, wy, -zf_abs), (wx, wy, zf_abs)], 15.0, "frame", ACCENT if variant == "elf" else FR_COL,
                        sides=8, smooth=0)
        add_spline_tube(b, [(x_leg - 10.0, y_sf - 60.0, -zl_abs), (x_leg - 10.0, y_sf - 60.0, zl_abs)], 11.0, "frame", FR_COL,
                        sides=8, smooth=0)
        x0, x1, y0, y1 = fp
        # платформа чуть длиннее вперёд, как на арте (кроме orc — там силуэт уже точный)
        if variant != "orc":
            x1 = x1 + 20.0
        add_rounded_box(b, x0, x1, y0, y1, -zl_abs - 6.0, zl_abs + 6.0, "footrest", BLACK, top_col=(58, 58, 64), bevel=5.0)
        for rx in np.linspace(x0 + 22.0, x1 - 22.0, 4):
            add_rounded_box(b, rx - 4.0, rx + 4.0, y1 - 1.0, y1 + 4.0, -zl_abs + 20.0, zl_abs - 20.0, "footrest",
                            (70, 70, 76), bevel=1.0)
    else:
        y_top_br, y_bot_br = y_sr - 4.0, 318.0
        for s in (-1, 1):
            add_spline_tube(b, [(185.0, y_bot_br, -zf_abs * s), (212.0, y_top_br, zf_abs * s)], 10.5, "frame", FR_COL,
                            sides=8, smooth=0)
        add_spline_tube(b, [(182.0, (y_bot_br + y_top_br) * 0.5, 0.0), (216.0, (y_bot_br + y_top_br) * 0.5, 0.0)],
                        11.0, "bolts", BOLT, sides=6, smooth=0)

    # спинка, сиденье-гамак, подушка
    add_contoured_backrest(b, x_post - 2.0, x_post - 20.0, y_sr + 14.0, back_top - 8.0,
                           -zf_abs + 10.0, zf_abs - 10.0, 34.0, "seat", UPH, trim_col=UPH_TRIM, bolster=16.0, ribs=2)
    x_seat_end = x_leg - _act(variant, "seat_gap", seat_gap)
    add_rounded_box(b, x_post + 10.0, x_seat_end - 10.0, y_seat - 12.0, y_seat + 6.0,
                    -zf_abs + 10.0, zf_abs - 10.0, "seat", UPH_TRIM, bevel=4.0)
    add_contoured_cushion(b, x_post + 14.0, x_seat_end, y_seat + 2.0, y_seat + cush_h,
                          -zf_abs + 12.0, zf_abs - 12.0, "cushion", CUSH, trim_col=UPH, bolster=12.0, ribs=0)
    return b


# --------------------------------------------------------------------------- #
# Power Wheelchair Sub-Assemblies
# --------------------------------------------------------------------------- #
def add_power_drive_wheel(b, cx, cy, z, R, style="alloy5",
                          rim_col=(196, 202, 214), tire_col=(36, 38, 44), disc_col=None, spoke_col=None):
    sgn = 1 if z > 0 else -1
    add_torus(b, (cx, cy, z), R - 30.0, 30.0, "axle", tire_col, segs=32, sides=9, z_scale=1.12)
    add_torus(b, (cx, cy, z + 18.0 * sgn), R - 18.0, 6.0, "axle", (28, 30, 36), segs=32, sides=5)

    r_rim = R - 56.0
    add_torus(b, (cx, cy, z + 20.0 * sgn), r_rim, 9.5, "axle", rim_col, segs=28, sides=6)

    add_disc(b, cx, cy, z + 4.0 * sgn, r_rim - 4.0, "axle",
             disc_col if disc_col is not None else ((150, 156, 168) if style == "m3_tri" else (48, 50, 58)), segs=20)

    if style == "m3_tri":
        add_spline_tube(b, [(cx, cy, z + 14.0 * sgn), (cx, cy, z + 26.0 * sgn)], 34.0, "axle", (38, 40, 48), sides=12, smooth=0, caps=True)
        for i in range(3):
            a = 2 * math.pi * i / 3 + math.pi / 6
            p0 = (cx + 16.0 * math.cos(a), cy + 16.0 * math.sin(a), z + 23.0 * sgn)
            p1 = (cx + (r_rim - 2.0) * math.cos(a), cy + (r_rim - 2.0) * math.sin(a), z + 23.0 * sgn)
            add_spline_tube(b, [p0, p1], [19.0, 13.0], "axle", (38, 40, 48), sides=6, smooth=0, caps=True)
        add_spline_tube(b, [(cx, cy, z + 25.0 * sgn), (cx, cy, z + 30.0 * sgn)], 14.0, "axle", (118, 68, 166), sides=10, smooth=0, caps=True)
    else:
        add_spline_tube(b, [(cx, cy, z + 14.0 * sgn), (cx, cy, z + 26.0 * sgn)], 32.0, "axle", rim_col, sides=12, smooth=0, caps=True)
        for i in range(5):
            a = 2 * math.pi * i / 5 + 0.2
            p0 = (cx + 18.0 * math.cos(a), cy + 18.0 * math.sin(a), z + 22.0 * sgn)
            p1 = (cx + (r_rim - 2.0) * math.cos(a), cy + (r_rim - 2.0) * math.sin(a), z + 22.0 * sgn)
            add_spline_tube(b, [p0, p1], [15.5, 10.5], "axle", spoke_col if spoke_col is not None else rim_col,
                            sides=6, smooth=0, caps=True)
        add_spline_tube(b, [(cx, cy, z + 24.0 * sgn), (cx, cy, z + 30.0 * sgn)], 14.0, "axle", (44, 46, 54), sides=10, smooth=0, caps=True)


def add_power_caster(b, cx, cy, z, R, arm_pivot, arm_col=(150, 156, 168), hub_col=(165, 170, 182),
                     spring_col=None, tire_col=None):
    sgn = 1 if z > 0 else -1
    add_torus(b, (cx, cy, z), R - 16.0, 16.0, "frame", tire_col if tire_col is not None else (36, 38, 44), segs=22, sides=6)
    add_disc(b, cx, cy, z + 8.0 * sgn, R - 26.0, "frame", hub_col, segs=14)
    add_disc(b, cx, cy, z - 8.0 * sgn, R - 26.0, "frame", hub_col, segs=14)
    add_spline_tube(b, [(cx, cy, z + 8.0 * sgn), (cx, cy, z + 16.0 * sgn)], 14.0, "frame", (52, 54, 62), sides=8, smooth=0, caps=True)
    px, py = arm_pivot
    add_spline_tube(b, [
        (px, py, z),
        ((px + cx) * 0.5, max(py, cy + R + 18.0), z),
        (cx, cy + R + 12.0, z),
        (cx, cy, z + 18.0 * sgn)
    ], 11.5, "frame", arm_col, sides=7, smooth=2)
    if spring_col is not None:
        sx = (px * 0.45 + cx * 0.55)
        sy0 = (py + cy + R) * 0.5
        add_spline_tube(b, [(sx, sy0 - 5.0, z), (sx - 12.0, sy0 + 68.0, z)], 14.0, "frame", spring_col, sides=8, smooth=0, caps=True)


def add_power_controller(b, cx, cy, cz, cable_end):
    add_rounded_box(b, cx - 58.0, cx + 62.0, cy - 28.0, cy + 24.0, cz - 42.0, cz + 42.0,
                    "controller", (38, 40, 48), bevel=8.0)
    add_rounded_box(b, cx - 44.0, cx - 2.0, cy + 21.0, cy + 27.0, cz - 26.0, cz + 26.0,
                    "controller", (96, 214, 242), bevel=2.0)
    jx = cx + 26.0
    for y0, y1, r_b in ((cy + 22.0, cy + 34.0, 19.0),
                        (cy + 32.0, cy + 44.0, 15.5),
                        (cy + 42.0, cy + 52.0, 12.0)):
        add_spline_tube(b, [(jx, y0, cz), (jx, y1, cz)], r_b, "boot", (28, 30, 36), sides=10, smooth=0, caps=True)
    add_spline_tube(b, [(jx, cy + 50.0, cz), (jx, cy + 86.0, cz)], 6.5, "joystick", (185, 190, 202), sides=8, smooth=0, caps=True)
    add_spline_tube(b, [(jx, cy + 82.0, cz), (jx, cy + 114.0, cz)], 19.0, "joystick", (218, 68, 60), sides=10, smooth=0, caps=True)
    ex, ey, ez = cable_end
    add_spline_tube(b, [
        (cx - 35.0, cy - 18.0, cz),
        (cx - 75.0, cy - 85.0, cz + (10.0 if cz > 0 else -10.0)),
        ((cx + ex) * 0.5 - 40.0, (cy + ey) * 0.5, ez),
        (ex, ey, ez)
    ], 7.0, "wiring", (175, 180, 192), sides=6, smooth=2)


# --------------------------------------------------------------------------- #
# 7. Quantum Edge 4 (chair_edge4)
# --------------------------------------------------------------------------- #
def add_arc_band(b, cx, cy, z0, z1, r_in, r_out, a0_deg, a1_deg, part, col, edge_col=None, segs=14):
    """Изогнутая полоса-кожух (кольцевой сектор, выдавленный по z): крылья над колёсами, обтекатели."""
    n = b.segs(segs, 8)
    angs = np.linspace(math.radians(a0_deg), math.radians(a1_deg), n)
    rings = []
    for a in angs:
        ca, sa = math.cos(a), math.sin(a)
        rings.append([b.v((cx + r * ca, cy + r * sa, z)) for r, z in ((r_in, z0), (r_out, z0), (r_out, z1), (r_in, z1))])
    ec = edge_col or col
    for i in range(n - 1):
        A, B = rings[i], rings[i + 1]
        b.quad(A[0], A[1], B[1], B[0], part, col)      # торец z0
        b.quad(A[1], A[2], B[2], B[1], part, ec)       # внешняя дуга
        b.quad(A[2], A[3], B[3], B[2], part, col)      # торец z1
        b.quad(A[3], A[0], B[0], B[3], part, col)      # внутренняя дуга
    b.poly(rings[0], part, col)
    b.poly(list(reversed(rings[-1])), part, col)


EDGE = {
    "W": 316.0, "y_lift": 755.0, "xc_f": 320.0, "sw": 190.0, "back_h": 470.0, "x_fp": 305.0,
}


def _e(name, default):
    return EDGE.get(name, default)


def build_chair_edge4(lod=1.0):
    """Quantum Edge 4 по арту: 6 колёс (средний привод 14", передние и задние касторы), чёрная база
    с красными крыльями и фарами, подъёмник сиденья «ножницы», высокое сиденье TRU-Balance с
    боковыми валиками и подголовником, центральная подставка для ног (две икроножные подушки и
    широкая площадка), подлокотники, джойстик справа (+z)."""
    b = TriMeshBuilder(lod)
    RED = (200, 46, 44)
    RED_DARK = (150, 32, 32)
    BASE_DARK = (44, 44, 48)
    SHROUD = (54, 54, 58)
    CHARCOAL = (62, 62, 68)
    SILVER = (150, 154, 164)
    UPH = (50, 50, 54)
    UPH_TRIM = (64, 64, 70)
    LAMP = (246, 236, 196)

    W = _e("W", 292.0)             # полуширина по наружной стороне колёс
    y_lift = _e("y_lift", 800.0)   # низ рамы сиденья (подъёмник поднят, как на арте)
    xc_f, xc_r = _e("xc_f", 380.0), _e("xc_r", -330.0)
    zc = _e("zc", 238.0)

    # --- база ---
    add_rounded_box(b, -300.0, 290.0, 92.0, 300.0, -196.0, 196.0, "frame", BASE_DARK, bevel=26.0)
    add_rounded_box(b, -292.0, 282.0, 290.0, 372.0, -212.0, 212.0, "frame", SHROUD, top_col=(62, 62, 66), bevel=16.0)
    add_rounded_box(b, -200.0, 170.0, 140.0, 296.0, -204.0, 204.0, "battery", CHARCOAL, bevel=10.0)
    add_rounded_box(b, -330.0, -296.0, 200.0, 246.0, -40.0, 40.0, "fuse", (226, 90, 82), bevel=5.0)
    # передний «нос» с фарами
    add_rounded_box(b, 270.0, 352.0, 150.0, 330.0, -176.0, 176.0, "frame", BASE_DARK, top_col=SHROUD, bevel=18.0)
    add_rounded_box(b, 300.0, 360.0, 168.0, 300.0, -70.0, 70.0, "frame", (36, 36, 40), bevel=10.0)
    for s in (-1, 1):
        add_rounded_box(b, 336.0, 362.0, 252.0, 282.0, (130.0 * s), (170.0 * s), "frame", LAMP, bevel=4.0)
        add_rounded_box(b, 318.0, 340.0, 246.0, 288.0, (124.0 * s), (178.0 * s), "frame", (30, 30, 34), bevel=4.0)

    for s in (-1, 1):
        zw = (W - 34.0) * s
        add_power_drive_wheel(b, 0.0, 178.0, zw, 178.0, style="alloy5",
                              rim_col=(78, 80, 88), tire_col=(36, 36, 40))
        # красное крыло над ведущим колесом + красная полоса вдоль борта к фаре
        z_in, z_out = sorted([(W - 92.0) * s, (W - 20.0) * s])
        add_arc_band(b, 0.0, 178.0, z_in, z_out, 196.0, 226.0, 18.0, 162.0, "frame", RED, edge_col=RED_DARK)
        z_in2, z_out2 = sorted([200.0 * s, 214.0 * s])
        add_rounded_box(b, 150.0, 345.0, 230.0, 300.0, z_in2, z_out2, "frame", RED, bevel=6.0)
        add_rounded_box(b, -330.0, -170.0, 220.0, 290.0, z_in2, z_out2, "frame", RED, bevel=6.0)

        add_spline_tube(b, [(-20.0, 178.0, 95.0 * s), (-20.0, 178.0, (W - 82.0) * s)],
                        56.0, "motor", (72, 74, 84), sides=12, smooth=0, caps=True)
        add_spline_tube(b, [(-85.0, 230.0, (W - 96.0) * s), (-120.0, 305.0, (W - 96.0) * s)],
                        8.5, "freewheel", (236, 198, 52), sides=6, smooth=0, caps=True)
        add_spline_tube(b, [(-117.0, 298.0, (W - 96.0) * s), (-127.0, 322.0, (W - 96.0) * s)],
                        14.0, "freewheel", (236, 198, 52), sides=8, smooth=0, caps=True)

        # передние и задние касторы 6" на рычагах подвески
        add_power_caster(b, xc_f, 76.0, zc * s, 76.0, (250.0, 205.0),
                         arm_col=(40, 40, 44), hub_col=(120, 122, 130), spring_col=None)
        add_power_caster(b, xc_r, 76.0, zc * s, 76.0, (-250.0, 205.0),
                         arm_col=(40, 40, 44), hub_col=(120, 122, 130), spring_col=None)

    # --- подъёмник сиденья: «ножницы» + центральный актуатор ---
    add_spline_tube(b, [(0.0, 360.0, 0.0), (0.0, y_lift - 40.0, 0.0)], 40.0, "actuator", CHARCOAL, sides=10, smooth=0, caps=True)
    add_rounded_box(b, -200.0, 200.0, 368.0, 392.0, -170.0, 170.0, "seat_lift", (36, 36, 40), bevel=5.0)
    for s in (-1, 1):
        zs = 150.0 * s
        add_spline_tube(b, [(-175.0, 385.0, zs), (175.0, y_lift - 8.0, zs)], 14.0, "seat_lift", (40, 40, 44), sides=6, smooth=0)
        add_spline_tube(b, [(175.0, 385.0, zs), (-175.0, y_lift - 8.0, zs)], 14.0, "seat_lift", (52, 52, 56), sides=6, smooth=0)
        add_spline_tube(b, [(0.0, (385.0 + y_lift) * 0.5, zs - 14.0 * s), (0.0, (385.0 + y_lift) * 0.5, zs + 16.0 * s)],
                        9.0, "frame", SILVER, sides=6, smooth=0)

    # --- сиденье, спинка, подголовник ---
    sw = _e("sw", 222.0)
    add_rounded_box(b, -245.0, 235.0, y_lift, y_lift + 36.0, -sw + 4.0, sw - 4.0, "frame", (38, 38, 42), bevel=6.0)
    add_contoured_cushion(b, -240.0, 250.0, y_lift + 34.0, y_lift + _e("cush_t", 150.0), -sw, sw,
                          "seat", UPH, trim_col=UPH_TRIM, bolster=26.0, ribs=0)
    back_top = y_lift + _e("back_h", 470.0)
    add_contoured_backrest(b, -232.0, -268.0, y_lift + 80.0, back_top, -sw + 4.0, sw - 4.0,
                           62.0, "frame", UPH, trim_col=UPH_TRIM, bolster=34.0, ribs=0)
    add_spline_tube(b, [(-262.0, back_top - 30.0, 0.0), (-268.0, back_top + 80.0, 0.0)], 13.0, "frame", (40, 40, 44),
                    sides=8, smooth=0)
    add_contoured_backrest(b, -262.0, -270.0, back_top + 70.0, back_top + 210.0, -128.0, 128.0,
                           52.0, "frame", UPH, trim_col=UPH_TRIM, bolster=22.0, ribs=0)

    # подлокотники (короткие накладки на стойках у спинки)
    y_arm = y_lift + _e("arm_h", 300.0)
    for s in (-1, 1):
        za = (sw + 26.0) * s
        add_spline_tube(b, [(-190.0, y_lift + 30.0, za), (-190.0, y_arm, za)], 14.0, "frame", (40, 40, 44), sides=8, smooth=0)
        add_spline_tube(b, [(-190.0, y_arm - 20.0, za), (60.0, y_arm - 20.0, za)], 11.0, "frame", (40, 40, 44), sides=8, smooth=0)
        add_rounded_box(b, -175.0, 95.0, y_arm - 10.0, y_arm + 28.0, za - 34.0, za + 34.0, "armrest", UPH, top_col=UPH_TRIM, bevel=9.0)

    # центральная подставка для ног: стойка, две икроножные подушки, широкая площадка
    y_fp = _e("y_fp", 400.0)
    x_fp = _e("x_fp", 330.0)
    for zz in (-45.0, 45.0):
        add_spline_tube(b, [(215.0, y_lift + 10.0, zz), (x_fp - 20.0, y_lift - 120.0, zz), (x_fp - 40.0, y_fp + 20.0, zz)],
                        14.0, "frame", (40, 40, 44), sides=8, smooth=2)
    add_rounded_box(b, x_fp - 62.0, x_fp - 18.0, y_fp + 60.0, y_lift - 60.0, -60.0, 60.0, "frame", (36, 36, 40), bevel=8.0)
    for s in (-1, 1):
        z0, z1 = sorted([14.0 * s, 150.0 * s])
        p_lo = y_fp + _e("pad_lo", 110.0)
        add_rounded_box(b, x_fp - 30.0, x_fp + 26.0, p_lo, p_lo + 170.0, z0, z1, "frame", UPH, top_col=UPH_TRIM, bevel=16.0)
        z0, z1 = sorted([8.0 * s, 250.0 * s])
        add_rounded_box(b, x_fp - 70.0, x_fp + 120.0, y_fp, y_fp + 16.0, z0, z1, "frame", (40, 40, 44),
                        top_col=(56, 56, 60), bevel=5.0)

    add_power_controller(b, 120.0, y_arm + 36.0, sw + 60.0, (130.0, 300.0, 200.0))
    # кронштейн джойстика (откидной) под пультом
    add_spline_tube(b, [(40.0, y_arm + 8.0, sw + 60.0), (110.0, y_arm + 8.0, sw + 60.0)], 12.0, "frame", (40, 40, 44),
                    sides=8, smooth=0)
    return b


# --------------------------------------------------------------------------- #
# 8. Permobil M3 Corpus (chair_m3)
# --------------------------------------------------------------------------- #
def add_sloped_slab(b, x0, x1, y0_rear, y0_front, thick, z0, z1, part, col, top_col=None):
    """Тонкая наклонная пластина (подножка-«клин»): низ идёт от y0_rear (x0) к y0_front (x1)."""
    p = [b.v(q) for q in ((x0, y0_rear, z0), (x1, y0_front, z0), (x1, y0_front + thick, z0), (x0, y0_rear + thick, z0),
                          (x0, y0_rear, z1), (x1, y0_front, z1), (x1, y0_front + thick, z1), (x0, y0_rear + thick, z1))]
    tc = top_col or col
    for q, c in (((0, 3, 2, 1), col), ((4, 5, 6, 7), col), ((0, 1, 5, 4), col), ((3, 7, 6, 2), tc),
                 ((1, 2, 6, 5), col), ((0, 4, 7, 3), col)):
        b.poly([p[i] for i in q], part, c)


M3P = {}


def build_chair_m3_custom(lod=1.0):
    """Permobil M3 Corpus по арту (вид сбоку): средний привод 14" с тёмной Y-ступицей, касторы 8" спереди
    и сзади на рычагах, низкие фиолетовые боковые обтекатели, тёмная надстройка с механизмом наклона,
    высокая узкая спинка Corpus с боковыми валиками, контурная подушка, подлокотник с пультом
    R-net спереди (джойстик +z), низкая наклонная подножка, штанга сзади."""
    b = TriMeshBuilder(lod)
    g = lambda n, d: M3P.get(n, d)
    PURPLE = (104, 62, 142)
    PURPLE_LIGHT = (128, 82, 168)
    BASE_DARK = (42, 42, 48)
    GRAPHITE = (64, 64, 72)
    UPH = (48, 46, 54)
    UPH_TRIM = (62, 58, 70)
    METAL = (88, 88, 96)

    W = 305.0
    y_rail = g("y_rail", 400.0)            # низ рамы сиденья
    back_top = g("back_top", 1070.0)
    x_cf, x_cr = g("x_cf", 322.0), g("x_cr", -385.0)

    # --- база ---
    add_rounded_box(b, -345.0, 380.0, 118.0, 290.0, -200.0, 200.0, "frame", BASE_DARK, bevel=20.0)
    add_rounded_box(b, -205.0, 384.0, 270.0, 382.0, -188.0, 188.0, "frame", BASE_DARK, top_col=GRAPHITE, bevel=14.0)
    add_rounded_box(b, -255.0, -40.0, 150.0, 262.0, -210.0, 210.0, "battery", GRAPHITE, bevel=8.0)
    add_rounded_box(b, -372.0, -342.0, 210.0, 255.0, -36.0, 36.0, "fuse", (226, 94, 86), bevel=5.0)
    for s in (-1, 1):
        z0, z1 = sorted([212.0 * s, 230.0 * s])
        # низкие фиолетовые обтекатели перед и за ведущим колесом
        add_rounded_box(b, -368.0, -175.0, 135.0, 272.0, z0, z1, "frame", PURPLE, top_col=PURPLE_LIGHT, bevel=10.0)
        add_rounded_box(b, 165.0, 388.0, 135.0, 272.0, z0, z1, "frame", PURPLE, top_col=PURPLE_LIGHT, bevel=10.0)
        add_rounded_box(b, -330.0, -200.0, 272.0, 300.0, z0, z1, "frame", (36, 36, 42), bevel=5.0)

        zw = (W - 40.0) * s
        add_power_drive_wheel(b, 0.0, 178.0, zw, 178.0, style="m3_tri",
                              rim_col=(56, 56, 62), tire_col=(32, 32, 36), disc_col=(72, 70, 76))
        add_spline_tube(b, [(-30.0, 178.0, 95.0 * s), (-30.0, 178.0, (W - 92.0) * s)],
                        56.0, "motor", GRAPHITE, sides=12, smooth=0, caps=True)
        add_spline_tube(b, [(-95.0, 240.0, (W - 100.0) * s), (-130.0, 312.0, (W - 100.0) * s)],
                        8.5, "freewheel", (236, 198, 52), sides=6, smooth=0, caps=True)
        add_spline_tube(b, [(-127.0, 304.0, (W - 100.0) * s), (-135.0, 328.0, (W - 100.0) * s)],
                        14.0, "freewheel", (236, 198, 52), sides=8, smooth=0, caps=True)

        zc = (W - 80.0) * s
        add_power_caster(b, x_cf, 96.0, zc, 96.0, (200.0, 205.0), arm_col=(46, 46, 52), hub_col=(60, 58, 64),
                         spring_col=(70, 70, 78), tire_col=(96, 94, 98))
        add_power_caster(b, x_cr, 96.0, zc, 96.0, (-215.0, 205.0), arm_col=(46, 46, 52), hub_col=(60, 58, 64),
                         spring_col=None, tire_col=(96, 94, 98))

    # --- механизм наклона и рама сиденья ---
    add_spline_tube(b, [(-20.0, 370.0, 0.0), (-20.0, y_rail, 0.0)], 52.0, "frame", BASE_DARK, sides=12, smooth=0, caps=True)
    for s in (-1, 1):
        zr = 196.0 * s
        add_rounded_box(b, -185.0, 378.0, y_rail, y_rail + 28.0, zr - 12.0, zr + 12.0, "frame", METAL, bevel=4.0)
        add_rounded_box(b, -175.0, 368.0, y_rail + 30.0, y_rail + 50.0, zr - 10.0, zr + 10.0, "frame", (40, 40, 46), bevel=3.0)
        add_spline_tube(b, [(-150.0, 330.0, zr * 0.8), (150.0, y_rail - 4.0, zr * 0.8)], 13.0, "frame", (52, 52, 58),
                        sides=6, smooth=0)
        add_spline_tube(b, [(330.0, y_rail + 10.0, zr), (372.0, y_rail - 40.0, zr)], 10.0, "frame", (40, 40, 46),
                        sides=6, smooth=0)
    add_rounded_box(b, -180.0, 372.0, y_rail + 36.0, y_rail + 52.0, -200.0, 200.0, "frame", (36, 36, 42), bevel=4.0)

    # контурная подушка (передний край выше) и высокая узкая спинка Corpus
    add_contoured_cushion(b, -95.0, 352.0, y_rail + 50.0, y_rail + 145.0, -222.0, 222.0,
                          "frame", UPH, trim_col=UPH_TRIM, bolster=34.0, ribs=0)
    # передний «валик» под бёдра (подушка спереди выше, как на арте)
    add_contoured_cushion(b, 170.0, 352.0, y_rail + 120.0, y_rail + 178.0, -214.0, 214.0,
                          "frame", UPH, trim_col=UPH_TRIM, bolster=8.0, ribs=0)
    y_split = y_rail + 470.0
    add_contoured_backrest(b, -128.0, -104.0, y_rail + 70.0, y_split, -198.0, 198.0,
                           96.0, "frame", UPH, trim_col=UPH_TRIM, bolster=34.0, ribs=0)
    # верхняя узкая часть спинки Corpus со скруглённым верхом
    add_contoured_backrest(b, -104.0, -92.0, y_split - 20.0, back_top - 40.0, -150.0, 150.0,
                           74.0, "frame", UPH, trim_col=UPH_TRIM, bolster=20.0, ribs=0)
    add_spline_tube(b, [(-92.0, back_top - 42.0, -118.0), (-92.0, back_top - 42.0, 118.0)], 37.0, "frame", UPH,
                    sides=10, smooth=0)
    # боковые валики нижней части спинки
    for s in (-1, 1):
        z0, z1 = sorted([150.0 * s, 214.0 * s])
        add_rounded_box(b, -180.0, -10.0, y_rail + 90.0, y_rail + 330.0, z0, z1, "frame", UPH, top_col=UPH_TRIM, bevel=22.0)
        # штанга/стойка спинки сзади
        zb = 170.0 * s
        add_spline_tube(b, [(-150.0, y_rail + 40.0, zb), (-200.0, y_rail + 160.0, zb), (-232.0, y_rail + 300.0, zb),
                            (-218.0, y_rail + 325.0, zb)], 11.0, "frame", (40, 40, 46), sides=7, smooth=2)

    # подлокотники
    y_arm = g("y_arm", 700.0)
    for s in (-1, 1):
        za = (W - 62.0) * s
        add_spline_tube(b, [(-150.0, y_rail + 120.0, za), (-120.0, y_arm - 10.0, za)], 13.0, "frame", (40, 40, 46),
                        sides=8, smooth=0)
        add_rounded_box(b, -150.0, 125.0, y_arm - 6.0, y_arm + 30.0, za - 30.0, za + 30.0, "frame", UPH,
                        top_col=UPH_TRIM, bevel=9.0)

    # низкая наклонная подножка спереди
    add_spline_tube(b, [(372.0, 300.0, 0.0), (392.0, 170.0, 0.0)], 15.0, "frame", (40, 40, 46), sides=8, smooth=0)
    add_sloped_slab(b, 376.0, 606.0, 138.0, 74.0, 11.0, -175.0, 175.0, "frame", (40, 40, 46), top_col=(56, 56, 62))

    add_power_controller(b, 186.0, y_arm + 10.0, W - 50.0, (120.0, 300.0, W - 110.0))
    return b


# --------------------------------------------------------------------------- #
# 9. Drive Trident HD (chair_trident)
# --------------------------------------------------------------------------- #
TRI = {}


def build_chair_trident(lod=1.0):
    """Drive Trident HD по арту: открытая трубчатая чёрная рама, средний привод 14" с серебристыми
    5-спицевыми дисками и чёрными крыльями, задние касторы 8" на вилках, передние антиопрокидыватели
    на жёлтых амортизаторах, широкая перфорированная площадка для ног, «капитанское» сиденье с
    толстой подушкой, высокой спинкой и отдельным подголовником, откидные подлокотники, джойстик справа (+z)."""
    b = TriMeshBuilder(lod)
    g = lambda n, d: TRI.get(n, d)
    BLACK_GLOSS = (40, 40, 46)
    CHARCOAL = (58, 58, 64)
    ALLOY_SILVER = (206, 210, 220)
    YELLOW_SPRING = (226, 186, 52)
    UPH = (54, 52, 56)
    UPH_TRIM = (70, 68, 72)

    W = 320.0
    x_dw = g("x_dw", 100.0)
    x_rc, x_fc = g("x_rc", -430.0), g("x_fc", 340.0)
    y_seat = g("y_seat", 440.0)

    # батарейный отсек под сиденьем + корпус
    add_rounded_box(b, -250.0, 160.0, 118.0, 330.0, -175.0, 175.0, "battery", CHARCOAL, bevel=14.0)
    add_rounded_box(b, -260.0, 175.0, 300.0, 352.0, -205.0, 205.0, "frame", BLACK_GLOSS, top_col=CHARCOAL, bevel=10.0)
    add_rounded_box(b, -285.0, -255.0, 190.0, 238.0, -38.0, 38.0, "fuse", (226, 92, 84), bevel=5.0)

    for s in (-1, 1):
        zf = 232.0 * s
        # трубчатая боковая рама: от вилки заднего кастора вперёд и вниз к носу
        add_spline_tube(b, [
            (x_rc + 10.0, 250.0, zf),
            (x_rc + 70.0, 318.0, zf),
            (x_dw - 40.0, 330.0, zf),
            (x_fc - 30.0, 320.0, zf),
            (x_fc + 10.0, 270.0, zf),
            (x_fc + 20.0, 200.0, zf)
        ], 15.0, "frame", BLACK_GLOSS, sides=8, smooth=2)
        add_spline_tube(b, [(x_rc + 40.0, 200.0, zf), (x_dw - 100.0, 160.0, zf), (x_fc - 40.0, 175.0, zf)],
                        13.0, "frame", BLACK_GLOSS, sides=8, smooth=2)
        add_spline_tube(b, [(x_rc + 10.0, 250.0, zf), (x_rc + 40.0, 200.0, zf)], 13.0, "frame", BLACK_GLOSS, sides=8, smooth=0)
        # золотистая надпись на раме
        add_rounded_box(b, x_rc + 120.0, x_dw - 120.0, 322.0, 340.0, zf + 10.0 * s, zf + 16.0 * s, "frame",
                        (200, 170, 80), bevel=1.5)

        # ведущее колесо 14" + чёрное крыло
        zw = (W - 40.0) * s
        add_power_drive_wheel(b, x_dw, 178.0, zw, 178.0, style="alloy5",
                              rim_col=ALLOY_SILVER, tire_col=(34, 34, 38))
        z_in, z_out = sorted([(W - 100.0) * s, (W - 8.0) * s])
        add_arc_band(b, x_dw, 178.0, z_in, z_out, 194.0, 214.0, 15.0, 165.0, "frame", BLACK_GLOSS, edge_col=CHARCOAL)
        add_spline_tube(b, [(x_dw - 30.0, 178.0, 105.0 * s), (x_dw - 30.0, 178.0, (W - 95.0) * s)],
                        56.0, "motor", (74, 76, 86), sides=12, smooth=0, caps=True)
        add_spline_tube(b, [(x_dw - 95.0, 240.0, (W - 110.0) * s), (x_dw - 130.0, 318.0, (W - 110.0) * s)],
                        9.0, "freewheel", YELLOW_SPRING, sides=6, smooth=0, caps=True)
        add_spline_tube(b, [(x_dw - 127.0, 310.0, (W - 110.0) * s), (x_dw - 135.0, 334.0, (W - 110.0) * s)],
                        14.5, "freewheel", YELLOW_SPRING, sides=8, smooth=0, caps=True)

        # задний кастор 8" на вилке со штоком
        zc = (W - 62.0) * s
        add_power_caster(b, x_rc, 100.0, zc, 100.0, (x_rc + 40.0, 250.0),
                         arm_col=BLACK_GLOSS, hub_col=ALLOY_SILVER, spring_col=None, tire_col=(34, 34, 38))
        add_spline_tube(b, [(x_rc + 10.0, 232.0, zc), (x_rc + 10.0, 262.0, zc)], 22.0, "frame", BLACK_GLOSS,
                        sides=10, smooth=0, caps=True)
        add_spline_tube(b, [(x_rc + 10.0, 250.0, zc), (x_rc + 10.0, 250.0, zf)], 13.0, "frame", BLACK_GLOSS,
                        sides=8, smooth=0)

        # передний антиопрокидыватель на жёлтом амортизаторе
        za = 190.0 * s
        add_spline_tube(b, [(x_fc - 20.0, 300.0, za), (x_fc + 40.0, 108.0, za)], 10.0, "frame", CHARCOAL, sides=6, smooth=0)
        add_spline_tube(b, [(x_fc - 10.0, 268.0, za), (x_fc + 30.0, 142.0, za)], 19.0, "frame", YELLOW_SPRING, sides=8,
                        smooth=0, caps=True)
        add_torus(b, (x_fc + 46.0, 48.0, za), 34.0, 14.0, "frame", (34, 34, 38), segs=16, sides=6)
        add_spline_tube(b, [(x_fc + 46.0, 48.0, za - 12.0), (x_fc + 46.0, 48.0, za + 12.0)], 16.0, "frame",
                        (226, 186, 52), sides=8, smooth=0, caps=True)
        add_spline_tube(b, [(x_fc + 40.0, 108.0, za), (x_fc + 46.0, 52.0, za)], 9.0, "frame", CHARCOAL, sides=6, smooth=0)

    # подвеска и широкая перфорированная площадка для ног
    x_fp0, x_fp1 = g("x_fp0", 340.0), g("x_fp1", 590.0)
    y_fp = g("y_fp", 220.0)
    for s in (-1, 1):
        add_spline_tube(b, [(x_fc - 10.0, 300.0, 150.0 * s), (x_fp0 + 20.0, y_fp + 20.0, 150.0 * s)], 12.0, "frame",
                        BLACK_GLOSS, sides=8, smooth=0)
    add_rounded_box(b, x_fp0, x_fp1, y_fp, y_fp + 18.0, -230.0, 230.0, "frame", (34, 34, 40), top_col=(48, 48, 54), bevel=6.0)
    for i in range(5):
        for j in range(4):
            hx = x_fp0 + 50.0 + i * (x_fp1 - x_fp0 - 100.0) / 4.0
            hz = -150.0 + j * 100.0
            add_rounded_box(b, hx - 12.0, hx + 12.0, y_fp + 17.0, y_fp + 20.0, hz - 18.0, hz + 18.0, "frame",
                            (22, 22, 26), bevel=1.0)

    # «капитанское» сиденье
    add_spline_tube(b, [(-40.0, 340.0, 0.0), (-40.0, y_seat - 10.0, 0.0)], 58.0, "frame", BLACK_GLOSS, sides=12,
                    smooth=0, caps=True)
    add_rounded_box(b, -270.0, 270.0, y_seat - 20.0, y_seat + 12.0, -250.0, 250.0, "frame", BLACK_GLOSS, bevel=6.0)
    add_contoured_cushion(b, -268.0, 300.0, y_seat + 8.0, y_seat + g("cush_t", 150.0), -268.0, 268.0,
                          "frame", UPH, trim_col=UPH_TRIM, bolster=24.0, ribs=0)
    back_top = y_seat + g("back_h", 560.0)
    add_contoured_backrest(b, -240.0, -320.0, y_seat + 90.0, back_top, -258.0, 258.0,
                           92.0, "frame", UPH, trim_col=UPH_TRIM, bolster=34.0, ribs=2)
    for zz in (-70.0, 70.0):
        add_spline_tube(b, [(-318.0, back_top - 30.0, zz), (-325.0, back_top + 50.0, zz)], 9.0, "frame", (150, 154, 164),
                        sides=6, smooth=0)
    add_contoured_backrest(b, -322.0, -330.0, back_top + 30.0, back_top + 175.0, -140.0, 140.0,
                           64.0, "frame", UPH, trim_col=UPH_TRIM, bolster=18.0, ribs=0)

    # откидные подлокотники на опорах от основания спинки
    y_arm = y_seat + g("arm_h", 285.0)
    for s in (-1, 1):
        za = (W - 28.0) * s
        add_spline_tube(b, [(-215.0, y_seat - 10.0, (W - 70.0) * s), (-235.0, y_seat + 120.0, za), (-225.0, y_arm, za)],
                        14.0, "frame", BLACK_GLOSS, sides=8, smooth=2)
        add_rounded_box(b, -250.0, 170.0, y_arm, y_arm + 44.0, za - 36.0, za + 36.0, "frame", UPH,
                        top_col=UPH_TRIM, bevel=11.0)

    add_power_controller(b, 150.0, y_arm + 30.0, W - 90.0, (60.0, 330.0, W - 120.0))
    add_spline_tube(b, [(100.0, y_arm + 10.0, W - 28.0), (100.0, y_arm + 10.0, W - 90.0)], 10.0, "frame", BLACK_GLOSS,
                    sides=6, smooth=0)
    return b


BUILDERS = {
    "basic":   lambda lod=1.0: build_chair_folding(lod, is_troll=False),
    "troll":   lambda lod=1.0: build_chair_folding(lod, is_troll=True),
    "elf":     lambda lod=1.0: build_chair_active("elf", lod),
    "dwarf":   lambda lod=1.0: build_chair_active("dwarf", lod),
    "fairy":   lambda lod=1.0: build_chair_active("fairy", lod),
    "orc":     lambda lod=1.0: build_chair_active("orc", lod),
    "edge4":   lambda lod=1.0: build_chair_edge4(lod),
    "m3":      lambda lod=1.0: build_chair_m3_custom(lod),
    "trident": lambda lod=1.0: build_chair_trident(lod),
}


if __name__ == "__main__":
    import sys
    here = os.path.dirname(os.path.abspath(__file__))
    default_dir = os.path.join(here, "assets", "models") if os.path.isdir(os.path.join(here, "assets")) else os.path.join(here, "..", "assets", "models")
    out_dir = sys.argv[1] if len(sys.argv) > 1 else default_dir
    os.makedirs(out_dir, exist_ok=True)
    for name, fn in BUILDERS.items():
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
