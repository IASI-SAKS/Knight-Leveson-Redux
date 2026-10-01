"""
Launch Interceptor Program \u2014 Knight & Leveson (1986)
Standalone Python implementation of DECIDE.

Usage:
    python decide.py < input.json

Reads one JSON object from stdin, writes one JSON object to stdout.
"""

import json
import math
import sys

PI = 3.1415926535


# ---------------------------------------------------------------------------
# REALCOMPARE \u2014 fixed reference behaviour (derived from realcompare_reference.py)
# ---------------------------------------------------------------------------

def realcompare(a: float, b: float) -> str:
    """Compare two real numbers to six significant digits.

    Returns 'LT', 'EQ', or 'GT'.
    """
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

def _dist(x1, y1, x2, y2):
    """Euclidean distance between two points."""
    dx = x2 - x1
    dy = y2 - y1
    return math.sqrt(dx * dx + dy * dy)


def _circumradius(x1, y1, x2, y2, x3, y3):
    """Return the circumradius of the triangle formed by three points.

    If the points are collinear the circumradius is infinite (returns float('inf')).
    """
    ax, ay = x2 - x1, y2 - y1
    bx, by = x3 - x1, y3 - y1
    cross = ax * by - ay * bx  # 2 * signed area
    if realcompare(cross, 0.0) == "EQ":
        # Collinear \u2014 minimum enclosing circle is determined by the two
        # farthest-apart points.
        d12 = _dist(x1, y1, x2, y2)
        d13 = _dist(x1, y1, x3, y3)
        d23 = _dist(x2, y2, x3, y3)
        return max(d12, d13, d23) / 2.0
    # Standard circumradius formula
    a = _dist(x2, y2, x3, y3)
    b = _dist(x1, y1, x3, y3)
    c = _dist(x1, y1, x2, y2)
    return (a * b * c) / abs(2.0 * cross)


def _triangle_area(x1, y1, x2, y2, x3, y3):
    """Return the (positive) area of the triangle formed by three points."""
    return abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)) / 2.0


def _angle(x1, y1, xv, yv, x3, y3):
    """Return the angle at vertex (xv, yv) formed by rays to (x1,y1) and (x3,y3).

    Returns None if either endpoint coincides with the vertex.
    """
    if realcompare(x1, xv) == "EQ" and realcompare(y1, yv) == "EQ":
        return None
    if realcompare(x3, xv) == "EQ" and realcompare(y3, yv) == "EQ":
        return None
    ux, uy = x1 - xv, y1 - yv
    vx, vy = x3 - xv, y3 - yv
    dot = ux * vx + uy * vy
    mag_u = math.sqrt(ux * ux + uy * uy)
    mag_v = math.sqrt(vx * vx + vy * vy)
    cos_a = dot / (mag_u * mag_v)
    # Clamp for numerical safety
    cos_a = max(-1.0, min(1.0, cos_a))
    return math.acos(cos_a)


def _quadrant(x, y):
    """Return quadrant number (1-4) for point (x, y) with tie-break priority I > II > III > IV."""
    if x >= 0 and y >= 0:
        return 1
    if x < 0 and y >= 0:
        return 2
    if x <= 0 and y < 0:
        return 3
    # x > 0 and y < 0
    return 4


def _dist_point_to_line(px, py, x1, y1, x2, y2):
    """Distance from point (px,py) to the infinite line through (x1,y1)-(x2,y2)."""
    dx = x2 - x1
    dy = y2 - y1
    # Line length
    line_len = math.sqrt(dx * dx + dy * dy)
    if realcompare(line_len, 0.0) == "EQ":
        # Degenerate line \u2014 distance to the single point
        return _dist(px, py, x1, y1)
    # Cross product magnitude / line length
    return abs((px - x1) * dy - (py - y1) * dx) / line_len


# ---------------------------------------------------------------------------
# Launch Interceptor Conditions (LICs 0-14, spec uses 1-15 but we index 0-14)
# ---------------------------------------------------------------------------

def _lic0(numpoints, x, y, params):
    """LIC 1 (index 0): Two consecutive points farther apart than LENGTH1."""
    length1 = params["LENGTH1"]
    for i in range(numpoints - 1):
        d = _dist(x[i], y[i], x[i + 1], y[i + 1])
        if realcompare(d, length1) == "GT":
            return True
    return False


def _lic1(numpoints, x, y, params):
    """LIC 2 (index 1): Three consecutive points that cannot fit in a circle of radius RADIUS1."""
    radius1 = params["RADIUS1"]
    for i in range(numpoints - 2):
        r = _circumradius(x[i], y[i], x[i + 1], y[i + 1], x[i + 2], y[i + 2])
        if realcompare(r, radius1) == "GT":
            return True
    return False


def _lic2(numpoints, x, y, params):
    """LIC 3 (index 2): Three consecutive points forming an angle outside [PI-EPSILON, PI+EPSILON]."""
    epsilon = params["EPSILON"]
    for i in range(numpoints - 2):
        ang = _angle(x[i], y[i], x[i + 1], y[i + 1], x[i + 2], y[i + 2])
        if ang is None:
            continue
        if realcompare(ang, PI - epsilon) == "LT":
            return True
        if realcompare(ang, PI + epsilon) == "GT":
            return True
    return False


def _lic3(numpoints, x, y, params):
    """LIC 4 (index 3): Three consecutive points forming a triangle with area > AREA1."""
    area1 = params["AREA1"]
    for i in range(numpoints - 2):
        area = _triangle_area(x[i], y[i], x[i + 1], y[i + 1], x[i + 2], y[i + 2])
        if realcompare(area, area1) == "GT":
            return True
    return False


def _lic4(numpoints, x, y, params):
    """LIC 5 (index 4): Q_PTS consecutive points in more than QUADS quadrants."""
    q_pts = params["Q_PTS"]
    quads = params["QUADS"]
    for i in range(numpoints - q_pts + 1):
        seen = set()
        for j in range(q_pts):
            seen.add(_quadrant(x[i + j], y[i + j]))
        if len(seen) > quads:
            return True
    return False


def _lic5(numpoints, x, y, params):
    """LIC 6 (index 5): Two consecutive points where X[j] - X[i] < 0 (j = i+1)."""
    for i in range(numpoints - 1):
        if realcompare(x[i + 1] - x[i], 0.0) == "LT":
            return True
    return False


def _lic6(numpoints, x, y, params):
    """LIC 7 (index 6): N_PTS consecutive points with one point > DIST from the line joining first/last."""
    if numpoints < 3:
        return False
    n_pts = params["N_PTS"]
    dist = params["DIST"]
    for i in range(numpoints - n_pts + 1):
        x1, y1 = x[i], y[i]
        x2, y2 = x[i + n_pts - 1], y[i + n_pts - 1]
        # Check if first and last are coincident
        coincident = (realcompare(x1, x2) == "EQ" and realcompare(y1, y2) == "EQ")
        for k in range(1, n_pts - 1):
            if coincident:
                d = _dist(x[i + k], y[i + k], x1, y1)
            else:
                d = _dist_point_to_line(x[i + k], y[i + k], x1, y1, x2, y2)
            if realcompare(d, dist) == "GT":
                return True
    return False


def _lic7(numpoints, x, y, params):
    """LIC 8 (index 7): Two points separated by K_PTS intervening points farther than LENGTH1."""
    if numpoints < 3:
        return False
    k_pts = params["K_PTS"]
    length1 = params["LENGTH1"]
    step = k_pts + 1
    for i in range(numpoints - step):
        j = i + step
        d = _dist(x[i], y[i], x[j], y[j])
        if realcompare(d, length1) == "GT":
            return True
    return False


def _lic8(numpoints, x, y, params):
    """LIC 9 (index 8): Three points sep. by A_PTS and B_PTS not fitting in circle of RADIUS1."""
    if numpoints < 5:
        return False
    a_pts = params["A_PTS"]
    b_pts = params["B_PTS"]
    step1 = a_pts + 1
    step2 = b_pts + 1
    radius1 = params["RADIUS1"]
    for i in range(numpoints - step1 - step2):
        j = i + step1
        k = j + step2
        r = _circumradius(x[i], y[i], x[j], y[j], x[k], y[k])
        if realcompare(r, radius1) == "GT":
            return True
    return False


def _lic9(numpoints, x, y, params):
    """LIC 10 (index 9): Three points sep. by C_PTS and D_PTS with angle outside [PI-EPS, PI+EPS]."""
    if numpoints < 5:
        return False
    c_pts = params["C_PTS"]
    d_pts = params["D_PTS"]
    step1 = c_pts + 1
    step2 = d_pts + 1
    epsilon = params["EPSILON"]
    for i in range(numpoints - step1 - step2):
        j = i + step1
        k = j + step2
        ang = _angle(x[i], y[i], x[j], y[j], x[k], y[k])
        if ang is None:
            continue
        if realcompare(ang, PI - epsilon) == "LT":
            return True
        if realcompare(ang, PI + epsilon) == "GT":
            return True
    return False


def _lic10(numpoints, x, y, params):
    """LIC 11 (index 10): Three points sep. by E_PTS and F_PTS forming triangle with area > AREA1."""
    if numpoints < 5:
        return False
    e_pts = params["E_PTS"]
    f_pts = params["F_PTS"]
    step1 = e_pts + 1
    step2 = f_pts + 1
    area1 = params["AREA1"]
    for i in range(numpoints - step1 - step2):
        j = i + step1
        k = j + step2
        area = _triangle_area(x[i], y[i], x[j], y[j], x[k], y[k])
        if realcompare(area, area1) == "GT":
            return True
    return False


def _lic11(numpoints, x, y, params):
    """LIC 12 (index 11): Two points sep. by G_PTS where X[j]-X[i] < 0."""
    if numpoints < 3:
        return False
    g_pts = params["G_PTS"]
    step = g_pts + 1
    for i in range(numpoints - step):
        j = i + step
        if realcompare(x[j] - x[i], 0.0) == "LT":
            return True
    return False


def _lic12(numpoints, x, y, params):
    """LIC 13 (index 12): Two-part condition with K_PTS separation, LENGTH1 and LENGTH2."""
    if numpoints < 3:
        return False
    k_pts = params["K_PTS"]
    length1 = params["LENGTH1"]
    length2 = params["LENGTH2"]
    step = k_pts + 1
    part1 = False
    part2 = False
    for i in range(numpoints - step):
        j = i + step
        d = _dist(x[i], y[i], x[j], y[j])
        if realcompare(d, length1) == "GT":
            part1 = True
        if realcompare(d, length2) == "LT":
            part2 = True
        if part1 and part2:
            return True
    return False


def _lic13(numpoints, x, y, params):
    """LIC 14 (index 13): Two-part condition with A_PTS/B_PTS, RADIUS1 and RADIUS2."""
    if numpoints < 5:
        return False
    a_pts = params["A_PTS"]
    b_pts = params["B_PTS"]
    step1 = a_pts + 1
    step2 = b_pts + 1
    radius1 = params["RADIUS1"]
    radius2 = params["RADIUS2"]
    part1 = False
    part2 = False
    for i in range(numpoints - step1 - step2):
        j = i + step1
        k = j + step2
        r = _circumradius(x[i], y[i], x[j], y[j], x[k], y[k])
        if realcompare(r, radius1) == "GT":
            part1 = True
        if realcompare(r, radius2) != "GT":  # r <= radius2
            part2 = True
        if part1 and part2:
            return True
    return False


def _lic14(numpoints, x, y, params):
    """LIC 15 (index 14): Two-part condition with E_PTS/F_PTS, AREA1 and AREA2."""
    if numpoints < 5:
        return False
    e_pts = params["E_PTS"]
    f_pts = params["F_PTS"]
    step1 = e_pts + 1
    step2 = f_pts + 1
    area1 = params["AREA1"]
    area2 = params["AREA2"]
    part1 = False
    part2 = False
    for i in range(numpoints - step1 - step2):
        j = i + step1
        k = j + step2
        area = _triangle_area(x[i], y[i], x[j], y[j], x[k], y[k])
        if realcompare(area, area1) == "GT":
            part1 = True
        if realcompare(area, area2) == "LT":
            part2 = True
        if part1 and part2:
            return True
    return False


# Ordered list of LIC evaluators (index 0 = LIC 1 in spec, etc.)
_LIC_FUNCS = [
    _lic0, _lic1, _lic2, _lic3, _lic4, _lic5, _lic6, _lic7,
    _lic8, _lic9, _lic10, _lic11, _lic12, _lic13, _lic14,
]


# ---------------------------------------------------------------------------
# Main DECIDE procedure
# ---------------------------------------------------------------------------

def decide(numpoints, x, y, parameters, lcm, pum_diag):
    """Evaluate the Launch Interceptor Program.

    Parameters
    ----------
    numpoints : int
        Number of planar data points (2..100).
    x, y : list of float
        Coordinates of the data points (length == numpoints).
    parameters : dict
        Record of LIC parameters (Pascal-style keys: LENGTH1, RADIUS1, ...).
    lcm : list[list[str]]
        15x15 Logical Connector Matrix; each entry is 'NOTUSED', 'ORR', or 'ANDD'.
    pum_diag : list[bool]
        Length-15 list of diagonal elements of the PUM.

    Returns
    -------
    cmv : list[bool]  (length 15)
    pum : list[list[bool]]  (15x15)
    fuv : list[bool]  (length 15)
    launch : bool
    """
    N = 15

    # ------------------------------------------------------------------
    # Step 1: Compute the Conditions Met Vector (CMV)
    # ------------------------------------------------------------------
    cmv = [f(numpoints, x, y, parameters) for f in _LIC_FUNCS]

    # ------------------------------------------------------------------
    # Step 2: Compute the Preliminary Unlocking Matrix (PUM)
    # Diagonal elements come from pum_diag; off-diagonal from LCM + CMV.
    # ------------------------------------------------------------------
    pum = [[False] * N for _ in range(N)]
    for i in range(N):
        for j in range(N):
            if i == j:
                pum[i][j] = pum_diag[i]
            else:
                connector = lcm[i][j]
                if connector == "NOTUSED":
                    pum[i][j] = True
                elif connector == "ANDD":
                    pum[i][j] = cmv[i] and cmv[j]
                else:  # "ORR"
                    pum[i][j] = cmv[i] or cmv[j]

    # ------------------------------------------------------------------
    # Step 3: Compute the Final Unlocking Vector (FUV)
    # FUV[i] = True if pum_diag[i] is False, OR all elements in row i are True.
    # ------------------------------------------------------------------
    fuv = [False] * N
    for i in range(N):
        if not pum_diag[i]:
            fuv[i] = True
        else:
            fuv[i] = all(pum[i][j] for j in range(N))

    # ------------------------------------------------------------------
    # Step 4: Launch decision
    # ------------------------------------------------------------------
    launch = all(fuv)

    return cmv, pum, fuv, launch


# ---------------------------------------------------------------------------
# CLI entry point
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

    result = {
        "cmv": cmv,
        "pum": pum,
        "fuv": fuv,
        "launch": launch,
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
