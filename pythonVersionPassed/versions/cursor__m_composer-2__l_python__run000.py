#!/usr/bin/env python3
"""
Launch Interceptor Program (Knight & Leveson, 1986).
Standalone stdin/stdout JSON driver and importable `decide` with no import-time I/O.
"""

from __future__ import annotations

import json
import math
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Spec constant (Pascal `PI`)
PI = 3.1415926535


def realcompare(a: float, b: float) -> str:
    """Tolerance-based six-significant-digit comparison (matches realcompare_reference)."""
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


def _rc_lt(a: float, b: float) -> bool:
    return realcompare(a, b) == "LT"


def _rc_gt(a: float, b: float) -> bool:
    return realcompare(a, b) == "GT"


def _rc_eq(a: float, b: float) -> bool:
    return realcompare(a, b) == "EQ"


def _rc_le(a: float, b: float) -> bool:
    c = realcompare(a, b)
    return c == "LT" or c == "EQ"


def _rc_ge(a: float, b: float) -> bool:
    c = realcompare(a, b)
    return c == "GT" or c == "EQ"


def _dist(ax: float, ay: float, bx: float, by: float) -> float:
    return math.hypot(bx - ax, by - ay)


def _triangle_area(ax: float, ay: float, bx: float, by: float, cx: float, cy: float) -> float:
    return abs((bx - ax) * (cy - ay) - (by - ay) * (cx - ax)) / 2.0


def _smallest_enclosing_circle_radius_3(
    ax: float, ay: float, bx: float, by: float, cx: float, cy: float
) -> float:
    """Minimum radius of a circle that contains the three planar points (on or inside)."""
    d12 = _dist(ax, ay, bx, by)
    d23 = _dist(bx, by, cx, cy)
    d13 = _dist(ax, ay, cx, cy)
    cross = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
    if _rc_eq(cross, 0.0):
        return max(d12, d23, d13) / 2.0

    a, b, c = d23, d13, d12  # lengths opposite vertices A, B, C respectively
    cos_a_num = b * b + c * c - a * a
    cos_b_num = a * a + c * c - b * b
    cos_c_num = a * a + b * b - c * c
    longest = max(d12, d23, d13)
    if _rc_le(cos_a_num, 0.0) or _rc_le(cos_b_num, 0.0) or _rc_le(cos_c_num, 0.0):
        return longest / 2.0
    return (a * b * c) / abs(cross)


def _can_fit_circle_radius_r(
    ax: float, ay: float, bx: float, by: float, cx: float, cy: float, r: float
) -> bool:
    """True iff the three points fit in some circle of radius r (on or inside)."""
    sec_r = _smallest_enclosing_circle_radius_3(ax, ay, bx, by, cx, cy)
    return _rc_le(sec_r, r)


def _cannot_fit_circle_radius_r(
    ax: float, ay: float, bx: float, by: float, cx: float, cy: float, r: float
) -> bool:
    sec_r = _smallest_enclosing_circle_radius_3(ax, ay, bx, by, cx, cy)
    return _rc_gt(sec_r, r)


def _quadrant(px: float, py: float) -> int:
    """Return 0..3 for quadrants I..IV per spec tie-breaking."""
    if _rc_eq(px, 0.0) and _rc_eq(py, 0.0):
        return 0
    if _rc_eq(px, 0.0):
        return 0 if _rc_gt(py, 0.0) else 2
    if _rc_eq(py, 0.0):
        return 0 if _rc_gt(px, 0.0) else 1
    if _rc_gt(px, 0.0):
        return 0 if _rc_gt(py, 0.0) else 3
    return 1 if _rc_gt(py, 0.0) else 2


def _angle_at_vertex(
    x0: float, y0: float, xv: float, yv: float, x2: float, y2: float
) -> Optional[float]:
    """
    Angle at vertex (xv,yv) with rays through (x0,y0) and (x2,y2).
    None if undefined (coincident with vertex or zero-length ray).
    """
    if (_rc_eq(x0, xv) and _rc_eq(y0, yv)) or (_rc_eq(x2, xv) and _rc_eq(y2, yv)):
        return None
    ax, ay = x0 - xv, y0 - yv
    bx, by = x2 - xv, y2 - yv
    n1 = math.hypot(ax, ay)
    n2 = math.hypot(bx, by)
    if _rc_eq(n1, 0.0) or _rc_eq(n2, 0.0):
        return None
    dot = ax * bx + ay * by
    cosv = dot / (n1 * n2)
    if _rc_lt(cosv, -1.0):
        cosv = -1.0
    elif _rc_gt(cosv, 1.0):
        cosv = 1.0
    return math.acos(cosv)


def _dist_point_to_line(
    px: float, py: float, x0: float, y0: float, x1: float, y1: float
) -> float:
    if _rc_eq(x0, x1) and _rc_eq(y0, y1):
        return _dist(px, py, x0, y0)
    num = abs((x1 - x0) * (y0 - py) - (x0 - px) * (y1 - y0))
    den = math.hypot(x1 - x0, y1 - y0)
    return num / den


def _compute_cmv(
    numpoints: int,
    x: Sequence[float],
    y: Sequence[float],
    p: Dict[str, float],
) -> List[bool]:
    length1 = float(p["LENGTH1"])
    radius1 = float(p["RADIUS1"])
    epsilon = float(p["EPSILON"])
    area1 = float(p["AREA1"])
    q_pts = int(p["Q_PTS"])
    quads = int(p["QUADS"])
    dist_param = float(p["DIST"])
    n_pts = int(p["N_PTS"])
    k_pts = int(p["K_PTS"])
    a_pts = int(p["A_PTS"])
    b_pts = int(p["B_PTS"])
    c_pts = int(p["C_PTS"])
    d_pts = int(p["D_PTS"])
    e_pts = int(p["E_PTS"])
    f_pts = int(p["F_PTS"])
    g_pts = int(p["G_PTS"])
    length2 = float(p["LENGTH2"])
    radius2 = float(p["RADIUS2"])
    area2 = float(p["AREA2"])

    cmv = [False] * 15

    # LIC 1
    for i in range(numpoints - 1):
        d = _dist(x[i], y[i], x[i + 1], y[i + 1])
        if _rc_gt(d, length1):
            cmv[0] = True
            break

    # LIC 2
    for i in range(numpoints - 2):
        if _cannot_fit_circle_radius_r(x[i], y[i], x[i + 1], y[i + 1], x[i + 2], y[i + 2], radius1):
            cmv[1] = True
            break

    # LIC 3
    pi_m_eps = PI - epsilon
    pi_p_eps = PI + epsilon
    for i in range(numpoints - 2):
        ang = _angle_at_vertex(x[i], y[i], x[i + 1], y[i + 1], x[i + 2], y[i + 2])
        if ang is None:
            continue
        if _rc_lt(ang, pi_m_eps) or _rc_gt(ang, pi_p_eps):
            cmv[2] = True
            break

    # LIC 4
    for i in range(numpoints - 2):
        ar = _triangle_area(x[i], y[i], x[i + 1], y[i + 1], x[i + 2], y[i + 2])
        if _rc_gt(ar, area1):
            cmv[3] = True
            break

    # LIC 5
    for i in range(numpoints - q_pts + 1):
        seen = [False, False, False, False]
        for j in range(i, i + q_pts):
            qd = _quadrant(x[j], y[j])
            seen[qd] = True
        if sum(seen) > quads:
            cmv[4] = True
            break

    # LIC 6
    for i in range(numpoints - 1):
        if _rc_lt(x[i + 1] - x[i], 0.0):
            cmv[5] = True
            break

    # LIC 7
    if numpoints >= 3:
        for s in range(numpoints - n_pts + 1):
            x0, y0 = x[s], y[s]
            x1, y1 = x[s + n_pts - 1], y[s + n_pts - 1]
            for j in range(s, s + n_pts):
                dpl = _dist_point_to_line(x[j], y[j], x0, y0, x1, y1)
                if _rc_gt(dpl, dist_param):
                    cmv[6] = True
                    break
            if cmv[6]:
                break

    # LIC 8
    if numpoints >= 3:
        span = k_pts + 1
        for i in range(numpoints - span):
            d = _dist(x[i], y[i], x[i + span], y[i + span])
            if _rc_gt(d, length1):
                cmv[7] = True
                break

    # LIC 9
    if numpoints >= 5:
        span2 = a_pts + b_pts + 2
        for i in range(numpoints - span2):
            j = i + a_pts + 1
            k = i + a_pts + b_pts + 2
            if _cannot_fit_circle_radius_r(x[i], y[i], x[j], y[j], x[k], y[k], radius1):
                cmv[8] = True
                break

    # LIC 10
    if numpoints >= 5:
        span10 = c_pts + d_pts + 2
        for i in range(numpoints - span10):
            j = i + c_pts + 1
            k = i + c_pts + d_pts + 2
            ang = _angle_at_vertex(x[i], y[i], x[j], y[j], x[k], y[k])
            if ang is None:
                continue
            if _rc_lt(ang, pi_m_eps) or _rc_gt(ang, pi_p_eps):
                cmv[9] = True
                break

    # LIC 11
    if numpoints >= 5:
        span11 = e_pts + f_pts + 2
        for i in range(numpoints - span11):
            j = i + e_pts + 1
            k = i + e_pts + f_pts + 2
            ar = _triangle_area(x[i], y[i], x[j], y[j], x[k], y[k])
            if _rc_gt(ar, area1):
                cmv[10] = True
                break

    # LIC 12
    if numpoints >= 3:
        span12 = g_pts + 1
        for i in range(numpoints - span12):
            if _rc_lt(x[i + span12] - x[i], 0.0):
                cmv[11] = True
                break

    # LIC 13
    if numpoints >= 3:
        span = k_pts + 1
        part_a = False
        part_b = False
        for i in range(numpoints - span):
            d = _dist(x[i], y[i], x[i + span], y[i + span])
            if _rc_gt(d, length1):
                part_a = True
            if _rc_lt(d, length2):
                part_b = True
            if part_a and part_b:
                break
        cmv[12] = part_a and part_b

    # LIC 14
    if numpoints >= 5:
        span14 = a_pts + b_pts + 2
        part_a = False
        part_b = False
        for i in range(numpoints - span14):
            j = i + a_pts + 1
            k = i + a_pts + b_pts + 2
            if _cannot_fit_circle_radius_r(x[i], y[i], x[j], y[j], x[k], y[k], radius1):
                part_a = True
            if _can_fit_circle_radius_r(x[i], y[i], x[j], y[j], x[k], y[k], radius2):
                part_b = True
            if part_a and part_b:
                break
        cmv[13] = part_a and part_b

    # LIC 15
    if numpoints >= 5:
        span15 = e_pts + f_pts + 2
        part_a = False
        part_b = False
        for i in range(numpoints - span15):
            j = i + e_pts + 1
            k = i + e_pts + f_pts + 2
            ar = _triangle_area(x[i], y[i], x[j], y[j], x[k], y[k])
            if _rc_gt(ar, area1):
                part_a = True
            if _rc_lt(ar, area2):
                part_b = True
            if part_a and part_b:
                break
        cmv[14] = part_a and part_b

    return cmv


def _build_pum(
    cmv: Sequence[bool],
    lcm: Sequence[Sequence[str]],
    pum_diag: Sequence[bool],
) -> List[List[bool]]:
    n = 15
    pum: List[List[bool]] = [[False] * n for _ in range(n)]
    for i in range(n):
        pum[i][i] = bool(pum_diag[i])
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            conn = lcm[i][j]
            if conn == "NOTUSED":
                pum[i][j] = True
            elif conn == "ANDD":
                pum[i][j] = bool(cmv[i] and cmv[j])
            elif conn == "ORR":
                pum[i][j] = bool(cmv[i] or cmv[j])
            else:
                raise ValueError(f"Unknown LCM connector: {conn!r}")
    return pum


def _compute_fuv(pum: Sequence[Sequence[bool]]) -> List[bool]:
    n = 15
    fuv: List[bool] = []
    for i in range(n):
        row_all = all(pum[i][j] for j in range(n))
        fuv.append((not pum[i][i]) or row_all)
    return fuv


def decide(
    numpoints: int,
    x: Sequence[float],
    y: Sequence[float],
    parameters: Dict[str, Any],
    lcm: Sequence[Sequence[str]],
    pum_diag: Sequence[bool],
) -> Tuple[List[bool], List[List[bool]], List[bool], bool]:
    """
    Evaluate LIP decision logic.

    Returns (cmv, pum, fuv, launch) using 0-based LIC indices 0..14
    matching JSON array order (LIC 1 -> index 0).
    """
    cmv = _compute_cmv(numpoints, x, y, parameters)
    pum = _build_pum(cmv, lcm, pum_diag)
    fuv = _compute_fuv(pum)
    launch = all(fuv)
    return cmv, pum, fuv, launch


def _stdin_json_to_output(data: Dict[str, Any]) -> Dict[str, Any]:
    numpoints = int(data["numpoints"])
    x = data["x"]
    y = data["y"]
    parameters = data["parameters"]
    lcm = data["lcm"]
    pum_diag = data["pum_diag"]
    cmv, pum, fuv, launch = decide(numpoints, x, y, parameters, lcm, pum_diag)
    return {"cmv": cmv, "pum": pum, "fuv": fuv, "launch": launch}


def main() -> None:
    payload = json.load(sys.stdin)
    out = _stdin_json_to_output(payload)
    json.dump(out, sys.stdout)
    sys.stdout.write("\
")


if __name__ == "__main__":
    main()
