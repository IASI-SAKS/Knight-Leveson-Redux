#!/usr/bin/env python3
"""Launch Interceptor Program \u2014 Knight & Leveson (1986) implementation."""

import json
import math
import sys

PI = 3.1415926535


# ---------------------------------------------------------------------------
# realcompare \u2014 fixed reference behaviour (tolerance-based 6-sig-digit)
# ---------------------------------------------------------------------------
def realcompare(a: float, b: float) -> str:
    scale = max(abs(a), abs(b))
    if scale == 0.0:
        return "EQ"
    eps = 0.5e-5 * scale
    diff = a - b
    if diff > eps:
        return "GT"
    if diff < -eps:
        return "LT"
    return "EQ"


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------
def dist(x1, y1, x2, y2):
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


def triangle_area(x1, y1, x2, y2, x3, y3):
    return abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)) / 2.0


def angle_at_vertex(x1, y1, xv, yv, x3, y3):
    """Return the angle (radians) at vertex (xv,yv) formed by points 1-v-3.
    Returns None if either arm has zero length."""
    dx1 = x1 - xv
    dy1 = y1 - yv
    dx3 = x3 - xv
    dy3 = y3 - yv
    len1 = math.sqrt(dx1 * dx1 + dy1 * dy1)
    len3 = math.sqrt(dx3 * dx3 + dy3 * dy3)
    if realcompare(len1, 0.0) == "EQ" or realcompare(len3, 0.0) == "EQ":
        return None
    cos_a = (dx1 * dx3 + dy1 * dy3) / (len1 * len3)
    # Clamp for numerical safety
    if cos_a > 1.0:
        cos_a = 1.0
    if cos_a < -1.0:
        cos_a = -1.0
    return math.acos(cos_a)


def circumradius(x1, y1, x2, y2, x3, y3):
    """Minimum enclosing circle radius for three points."""
    a = dist(x1, y1, x2, y2)
    b = dist(x2, y2, x3, y3)
    c = dist(x1, y1, x3, y3)
    # Sort sides
    sides = sorted([a, b, c])
    s0, s1, s2 = sides
    # If the triangle is obtuse or degenerate, the MEC radius is half the longest side
    # Check: longest^2 >= sum of squares of the other two
    if realcompare(s2 * s2, s0 * s0 + s1 * s1) != "LT":
        return s2 / 2.0
    # Acute triangle: circumscribed circle
    area = triangle_area(x1, y1, x2, y2, x3, y3)
    if realcompare(area, 0.0) == "EQ":
        # Collinear \u2014 MEC radius is half the max distance
        return max(a, b, c) / 2.0
    return (a * b * c) / (4.0 * area)


def quadrant(x, y):
    """Return quadrant number 1-4 with priority I > II > III > IV."""
    if x >= 0 and y >= 0:
        return 1
    if x < 0 and y >= 0:
        return 2
    if x < 0 and y < 0:
        return 3
    return 4


def point_to_line_dist(px, py, x1, y1, x2, y2):
    """Distance from point (px,py) to line through (x1,y1)-(x2,y2)."""
    dx = x2 - x1
    dy = y2 - y1
    length_sq = dx * dx + dy * dy
    if realcompare(length_sq, 0.0) == "EQ":
        return dist(px, py, x1, y1)
    return abs(dx * (y1 - py) - dy * (x1 - px)) / math.sqrt(length_sq)


# ---------------------------------------------------------------------------
# LIC evaluators  (0-indexed: LIC 1 \u2192 index 0, ... LIC 15 \u2192 index 14)
# ---------------------------------------------------------------------------
def lic_0(n, x, y, p):
    """LIC 1: two consecutive points distance > LENGTH1."""
    for i in range(n - 1):
        if realcompare(dist(x[i], y[i], x[i + 1], y[i + 1]), p["LENGTH1"]) == "GT":
            return True
    return False


def lic_1(n, x, y, p):
    """LIC 2: three consecutive points cannot be contained in circle of RADIUS1."""
    for i in range(n - 2):
        r = circumradius(x[i], y[i], x[i + 1], y[i + 1], x[i + 2], y[i + 2])
        if realcompare(r, p["RADIUS1"]) == "GT":
            return True
    return False


def lic_2(n, x, y, p):
    """LIC 3: angle at middle point < PI-EPSILON or > PI+EPSILON."""
    for i in range(n - 2):
        a = angle_at_vertex(x[i], y[i], x[i + 1], y[i + 1], x[i + 2], y[i + 2])
        if a is None:
            continue
        if realcompare(a, PI - p["EPSILON"]) == "LT" or realcompare(a, PI + p["EPSILON"]) == "GT":
            return True
    return False


def lic_3(n, x, y, p):
    """LIC 4: three consecutive points form triangle with area > AREA1."""
    for i in range(n - 2):
        a = triangle_area(x[i], y[i], x[i + 1], y[i + 1], x[i + 2], y[i + 2])
        if realcompare(a, p["AREA1"]) == "GT":
            return True
    return False


def lic_4(n, x, y, p):
    """LIC 5: Q_PTS consecutive points in more than QUADS quadrants."""
    q_pts = p["Q_PTS"]
    quads = p["QUADS"]
    for i in range(n - q_pts + 1):
        qs = set()
        for j in range(i, i + q_pts):
            qs.add(quadrant(x[j], y[j]))
        if len(qs) > quads:
            return True
    return False


def lic_5(n, x, y, p):
    """LIC 6: X[j] - X[i] < 0 for consecutive points (i = j-1)."""
    for i in range(n - 1):
        if realcompare(x[i + 1] - x[i], 0.0) == "LT":
            return True
    return False


def lic_6(n, x, y, p):
    """LIC 7: N_PTS consecutive, one point > DIST from line of first-last."""
    n_pts = p["N_PTS"]
    if n < 3:
        return False
    for i in range(n - n_pts + 1):
        x1, y1 = x[i], y[i]
        x2, y2 = x[i + n_pts - 1], y[i + n_pts - 1]
        coincident = (realcompare(x1, x2) == "EQ" and realcompare(y1, y2) == "EQ")
        for k in range(i + 1, i + n_pts - 1):
            if coincident:
                d = dist(x[k], y[k], x1, y1)
            else:
                d = point_to_line_dist(x[k], y[k], x1, y1, x2, y2)
            if realcompare(d, p["DIST"]) == "GT":
                return True
    return False


def lic_7(n, x, y, p):
    """LIC 8: two points separated by K_PTS intervening, distance > LENGTH1."""
    if n < 3:
        return False
    k = p["K_PTS"]
    for i in range(n - k - 1):
        j = i + k + 1
        if realcompare(dist(x[i], y[i], x[j], y[j]), p["LENGTH1"]) == "GT":
            return True
    return False


def lic_8(n, x, y, p):
    """LIC 9: three points sep by A_PTS, B_PTS cannot fit in RADIUS1 circle."""
    if n < 5:
        return False
    a_pts = p["A_PTS"]
    b_pts = p["B_PTS"]
    for i in range(n - a_pts - b_pts - 2):
        j = i + a_pts + 1
        k = j + b_pts + 1
        r = circumradius(x[i], y[i], x[j], y[j], x[k], y[k])
        if realcompare(r, p["RADIUS1"]) == "GT":
            return True
    return False


def lic_9(n, x, y, p):
    """LIC 10: three points sep by C_PTS, D_PTS, angle condition."""
    if n < 5:
        return False
    c_pts = p["C_PTS"]
    d_pts = p["D_PTS"]
    for i in range(n - c_pts - d_pts - 2):
        j = i + c_pts + 1
        k = j + d_pts + 1
        a = angle_at_vertex(x[i], y[i], x[j], y[j], x[k], y[k])
        if a is None:
            continue
        if realcompare(a, PI - p["EPSILON"]) == "LT" or realcompare(a, PI + p["EPSILON"]) == "GT":
            return True
    return False


def lic_10(n, x, y, p):
    """LIC 11: three points sep by E_PTS, F_PTS, area > AREA1."""
    if n < 5:
        return False
    e_pts = p["E_PTS"]
    f_pts = p["F_PTS"]
    for i in range(n - e_pts - f_pts - 2):
        j = i + e_pts + 1
        k = j + f_pts + 1
        a = triangle_area(x[i], y[i], x[j], y[j], x[k], y[k])
        if realcompare(a, p["AREA1"]) == "GT":
            return True
    return False


def lic_11(n, x, y, p):
    """LIC 12: two points sep by G_PTS, X[j]-X[i] < 0."""
    if n < 3:
        return False
    g = p["G_PTS"]
    for i in range(n - g - 1):
        j = i + g + 1
        if realcompare(x[j] - x[i], 0.0) == "LT":
            return True
    return False


def lic_12(n, x, y, p):
    """LIC 13: two points sep by K_PTS, one pair > LENGTH1 AND one pair < LENGTH2."""
    if n < 3:
        return False
    k = p["K_PTS"]
    cond1 = False
    cond2 = False
    for i in range(n - k - 1):
        j = i + k + 1
        d = dist(x[i], y[i], x[j], y[j])
        if realcompare(d, p["LENGTH1"]) == "GT":
            cond1 = True
        if realcompare(d, p["LENGTH2"]) == "LT":
            cond2 = True
        if cond1 and cond2:
            return True
    return cond1 and cond2


def lic_13(n, x, y, p):
    """LIC 14: three points sep by A_PTS,B_PTS \u2014 one triple > RADIUS1 AND one triple fits RADIUS2."""
    if n < 5:
        return False
    a_pts = p["A_PTS"]
    b_pts = p["B_PTS"]
    cond1 = False
    cond2 = False
    for i in range(n - a_pts - b_pts - 2):
        j = i + a_pts + 1
        k = j + b_pts + 1
        r = circumradius(x[i], y[i], x[j], y[j], x[k], y[k])
        if realcompare(r, p["RADIUS1"]) == "GT":
            cond1 = True
        if realcompare(r, p["RADIUS2"]) != "GT":
            cond2 = True
        if cond1 and cond2:
            return True
    return cond1 and cond2


def lic_14(n, x, y, p):
    """LIC 15: three points sep by E_PTS,F_PTS \u2014 one triple area > AREA1 AND one triple area < AREA2."""
    if n < 5:
        return False
    e_pts = p["E_PTS"]
    f_pts = p["F_PTS"]
    cond1 = False
    cond2 = False
    for i in range(n - e_pts - f_pts - 2):
        j = i + e_pts + 1
        k = j + f_pts + 1
        a = triangle_area(x[i], y[i], x[j], y[j], x[k], y[k])
        if realcompare(a, p["AREA1"]) == "GT":
            cond1 = True
        if realcompare(a, p["AREA2"]) == "LT":
            cond2 = True
        if cond1 and cond2:
            return True
    return cond1 and cond2


LIC_FUNCTIONS = [
    lic_0, lic_1, lic_2, lic_3, lic_4,
    lic_5, lic_6, lic_7, lic_8, lic_9,
    lic_10, lic_11, lic_12, lic_13, lic_14,
]


# ---------------------------------------------------------------------------
# Main DECIDE procedure
# ---------------------------------------------------------------------------
def decide(numpoints, x, y, parameters, lcm, pum_diag):
    # 1. Compute CMV
    cmv = [fn(numpoints, x, y, parameters) for fn in LIC_FUNCTIONS]

    # 2. Compute PUM (15x15)
    pum = [[False] * 15 for _ in range(15)]
    for i in range(15):
        pum[i][i] = pum_diag[i]
        for j in range(15):
            if i == j:
                continue
            connector = lcm[i][j]
            if connector == "NOTUSED":
                pum[i][j] = True
            elif connector == "ANDD":
                pum[i][j] = cmv[i] and cmv[j]
            elif connector == "ORR":
                pum[i][j] = cmv[i] or cmv[j]

    # 3. Compute FUV
    fuv = [False] * 15
    for i in range(15):
        if not pum[i][i]:
            fuv[i] = True
        else:
            fuv[i] = all(pum[i][j] for j in range(15))

    # 4. Launch decision
    launch = all(fuv)

    return cmv, pum, fuv, launch


# ---------------------------------------------------------------------------
# CLI: read JSON from stdin, write JSON to stdout
# ---------------------------------------------------------------------------
def main():
    data = json.load(sys.stdin)
    numpoints = data["numpoints"]
    x = data["x"]
    y = data["y"]
    parameters = data["parameters"]
    lcm = data["lcm"]
    pum_diag = data["pum_diag"]

    cmv, pum, fuv, launch = decide(numpoints, x, y, parameters, lcm, pum_diag)

    output = {
        "cmv": cmv,
        "pum": pum,
        "fuv": fuv,
        "launch": launch,
    }
    json.dump(output, sys.stdout)
    print()


if __name__ == "__main__":
    main()
