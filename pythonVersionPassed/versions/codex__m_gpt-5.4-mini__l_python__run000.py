"""Launch Interceptor Program implementation.

This module is self-contained and provides:
- realcompare(a, b) -> str
- decide(numpoints, x, y, parameters, lcm, pum_diag)

When run as a script, it reads one JSON object from stdin and writes one
JSON object to stdout.
"""

import json
import math
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

PI = 3.1415926535


def realcompare(a: float, b: float) -> str:
    """Tolerance-based six-significant-digit comparison from the oracle."""
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


def _param(parameters: Dict[str, Any], name: str) -> Any:
    if name in parameters:
        return parameters[name]
    lower = name.lower()
    if lower in parameters:
        return parameters[lower]
    raise KeyError(name)


def _distance(ax: float, ay: float, bx: float, by: float) -> float:
    return math.hypot(ax - bx, ay - by)


def _area2(ax: float, ay: float, bx: float, by: float, cx: float, cy: float) -> float:
    return abs((bx - ax) * (cy - ay) - (by - ay) * (cx - ax))


def _triangle_area(ax: float, ay: float, bx: float, by: float, cx: float, cy: float) -> float:
    return _area2(ax, ay, bx, by, cx, cy) / 2.0


def _quadrant(x: float, y: float) -> int:
    x_cmp = realcompare(x, 0.0)
    y_cmp = realcompare(y, 0.0)
    if y_cmp in ("GT", "EQ"):
        return 1 if x_cmp in ("GT", "EQ") else 2
    return 3 if x_cmp in ("LT", "EQ") else 4


def _angle_at(ax: float, ay: float, vx: float, vy: float, cx: float, cy: float) -> Optional[float]:
    ux = ax - vx
    uy = ay - vy
    wx = cx - vx
    wy = cy - vy
    if realcompare(ux, 0.0) == "EQ" and realcompare(uy, 0.0) == "EQ":
        return None
    if realcompare(wx, 0.0) == "EQ" and realcompare(wy, 0.0) == "EQ":
        return None
    dot = ux * wx + uy * wy
    nu = math.hypot(ux, uy)
    nw = math.hypot(wx, wy)
    if nu == 0.0 or nw == 0.0:
        return None
    cos_theta = dot / (nu * nw)
    if cos_theta > 1.0:
        cos_theta = 1.0
    elif cos_theta < -1.0:
        cos_theta = -1.0
    return math.acos(cos_theta)


def _min_enclosing_radius_three(
    ax: float,
    ay: float,
    bx: float,
    by: float,
    cx: float,
    cy: float,
) -> float:
    ab = _distance(ax, ay, bx, by)
    bc = _distance(bx, by, cx, cy)
    ca = _distance(cx, cy, ax, ay)
    longest = max(ab, bc, ca)

    # For obtuse or right triangles, the minimum enclosing circle is the one
    # with the longest side as diameter.
    dot_a = (bx - ax) * (cx - ax) + (by - ay) * (cy - ay)
    dot_b = (ax - bx) * (cx - bx) + (ay - by) * (cy - by)
    dot_c = (ax - cx) * (bx - cx) + (ay - cy) * (by - cy)

    if (
        realcompare(dot_a, 0.0) in ("LT", "EQ")
        or realcompare(dot_b, 0.0) in ("LT", "EQ")
        or realcompare(dot_c, 0.0) in ("LT", "EQ")
    ):
        return longest / 2.0

    area = _triangle_area(ax, ay, bx, by, cx, cy)
    if realcompare(area, 0.0) in ("LT", "EQ"):
        return longest / 2.0
    return ab * bc * ca / (4.0 * area)


def _triple_fits_circle(
    ax: float,
    ay: float,
    bx: float,
    by: float,
    cx: float,
    cy: float,
    radius: float,
) -> bool:
    return realcompare(_min_enclosing_radius_three(ax, ay, bx, by, cx, cy), radius) != "GT"


def decide(
    numpoints: int,
    x: Sequence[float],
    y: Sequence[float],
    parameters: Dict[str, Any],
    lcm: Sequence[Sequence[str]],
    pum_diag: Sequence[bool],
) -> Tuple[List[bool], List[List[bool]], List[bool], bool]:
    length1 = float(_param(parameters, "LENGTH1"))
    radius1 = float(_param(parameters, "RADIUS1"))
    epsilon = float(_param(parameters, "EPSILON"))
    area1 = float(_param(parameters, "AREA1"))
    q_pts = int(_param(parameters, "Q_PTS"))
    quads = int(_param(parameters, "QUADS"))
    dist = float(_param(parameters, "DIST"))
    n_pts = int(_param(parameters, "N_PTS"))
    k_pts = int(_param(parameters, "K_PTS"))
    a_pts = int(_param(parameters, "A_PTS"))
    b_pts = int(_param(parameters, "B_PTS"))
    c_pts = int(_param(parameters, "C_PTS"))
    d_pts = int(_param(parameters, "D_PTS"))
    e_pts = int(_param(parameters, "E_PTS"))
    f_pts = int(_param(parameters, "F_PTS"))
    g_pts = int(_param(parameters, "G_PTS"))
    length2 = float(_param(parameters, "LENGTH2"))
    radius2 = float(_param(parameters, "RADIUS2"))
    area2 = float(_param(parameters, "AREA2"))

    cmv = [False] * 15

    # LIC 1
    for i in range(numpoints - 1):
        if realcompare(_distance(x[i], y[i], x[i + 1], y[i + 1]), length1) == "GT":
            cmv[0] = True
            break

    # LIC 2
    if numpoints >= 3:
        for i in range(numpoints - 2):
            if not _triple_fits_circle(x[i], y[i], x[i + 1], y[i + 1], x[i + 2], y[i + 2], radius1):
                cmv[1] = True
                break

    # LIC 3
    if numpoints >= 3:
        threshold = PI - epsilon
        upper = PI + epsilon
        for i in range(numpoints - 2):
            angle = _angle_at(x[i], y[i], x[i + 1], y[i + 1], x[i + 2], y[i + 2])
            if angle is None:
                continue
            if realcompare(angle, threshold) == "LT" or realcompare(angle, upper) == "GT":
                cmv[2] = True
                break

    # LIC 4
    if numpoints >= 3:
        for i in range(numpoints - 2):
            area = _triangle_area(x[i], y[i], x[i + 1], y[i + 1], x[i + 2], y[i + 2])
            if realcompare(area, area1) == "GT":
                cmv[3] = True
                break

    # LIC 5
    if q_pts <= numpoints:
        for i in range(numpoints - q_pts + 1):
            quadrant_set = set()
            for j in range(i, i + q_pts):
                quadrant_set.add(_quadrant(x[j], y[j]))
                if len(quadrant_set) > quads:
                    cmv[4] = True
                    break
            if cmv[4]:
                break

    # LIC 6
    for i in range(numpoints - 1):
        if realcompare(x[i + 1] - x[i], 0.0) == "LT":
            cmv[5] = True
            break

    # LIC 7
    if numpoints >= 3:
        for i in range(numpoints - n_pts + 1):
            x0 = x[i]
            y0 = y[i]
            x1 = x[i + n_pts - 1]
            y1 = y[i + n_pts - 1]
            if realcompare(x0, x1) == "EQ" and realcompare(y0, y1) == "EQ":
                for j in range(i + 1, i + n_pts - 1):
                    if realcompare(_distance(x0, y0, x[j], y[j]), dist) == "GT":
                        cmv[6] = True
                        break
            else:
                denom = math.hypot(y1 - y0, x1 - x0)
                for j in range(i + 1, i + n_pts - 1):
                    num = abs((y1 - y0) * x[j] - (x1 - x0) * y[j] + x1 * y0 - y1 * x0)
                    d = num / denom
                    if realcompare(d, dist) == "GT":
                        cmv[6] = True
                        break
            if cmv[6]:
                break

    # LIC 8
    if numpoints >= 3:
        for i in range(numpoints - k_pts - 1):
            if realcompare(_distance(x[i], y[i], x[i + k_pts + 1], y[i + k_pts + 1]), length1) == "GT":
                cmv[7] = True
                break

    # LIC 9
    if numpoints >= 5:
        for i in range(numpoints - a_pts - b_pts - 2):
            if not _triple_fits_circle(
                x[i],
                y[i],
                x[i + a_pts + 1],
                y[i + a_pts + 1],
                x[i + a_pts + b_pts + 2],
                y[i + a_pts + b_pts + 2],
                radius1,
            ):
                cmv[8] = True
                break

    # LIC 10
    if numpoints >= 5:
        threshold = PI - epsilon
        upper = PI + epsilon
        for i in range(numpoints - c_pts - d_pts - 2):
            angle = _angle_at(
                x[i],
                y[i],
                x[i + c_pts + 1],
                y[i + c_pts + 1],
                x[i + c_pts + d_pts + 2],
                y[i + c_pts + d_pts + 2],
            )
            if angle is None:
                continue
            if realcompare(angle, threshold) == "LT" or realcompare(angle, upper) == "GT":
                cmv[9] = True
                break

    # LIC 11
    if numpoints >= 5:
        for i in range(numpoints - e_pts - f_pts - 2):
            area = _triangle_area(
                x[i],
                y[i],
                x[i + e_pts + 1],
                y[i + e_pts + 1],
                x[i + e_pts + f_pts + 2],
                y[i + e_pts + f_pts + 2],
            )
            if realcompare(area, area1) == "GT":
                cmv[10] = True
                break

    # LIC 12
    if numpoints >= 3:
        for i in range(numpoints - g_pts - 1):
            if realcompare(x[i + g_pts + 1] - x[i], 0.0) == "LT":
                cmv[11] = True
                break

    # LIC 13
    if numpoints >= 3:
        greater = False
        lesser = False
        for i in range(numpoints - k_pts - 1):
            d = _distance(x[i], y[i], x[i + k_pts + 1], y[i + k_pts + 1])
            if realcompare(d, length1) == "GT":
                greater = True
            if realcompare(d, length2) == "LT":
                lesser = True
            if greater and lesser:
                cmv[12] = True
                break

    # LIC 14
    if numpoints >= 5:
        greater = False
        lesser = False
        for i in range(numpoints - a_pts - b_pts - 2):
            r = _min_enclosing_radius_three(
                x[i],
                y[i],
                x[i + a_pts + 1],
                y[i + a_pts + 1],
                x[i + a_pts + b_pts + 2],
                y[i + a_pts + b_pts + 2],
            )
            if realcompare(r, radius1) == "GT":
                greater = True
            if realcompare(r, radius2) != "GT":
                lesser = True
            if greater and lesser:
                cmv[13] = True
                break

    # LIC 15
    if numpoints >= 5:
        greater = False
        lesser = False
        for i in range(numpoints - e_pts - f_pts - 2):
            area = _triangle_area(
                x[i],
                y[i],
                x[i + e_pts + 1],
                y[i + e_pts + 1],
                x[i + e_pts + f_pts + 2],
                y[i + e_pts + f_pts + 2],
            )
            if realcompare(area, area1) == "GT":
                greater = True
            if realcompare(area, area2) == "LT":
                lesser = True
            if greater and lesser:
                cmv[14] = True
                break

    pum = [[False] * 15 for _ in range(15)]
    for i in range(15):
        for j in range(15):
            if i == j:
                pum[i][j] = bool(pum_diag[i])
                continue
            connector = lcm[i][j]
            if connector == "NOTUSED":
                pum[i][j] = True
            elif connector == "ANDD":
                pum[i][j] = cmv[i] and cmv[j]
            elif connector == "ORR":
                pum[i][j] = cmv[i] or cmv[j]
            else:
                raise ValueError(f"Unknown LCM connector: {connector!r}")

    fuv = []
    for i in range(15):
        if not pum[i][i]:
            fuv.append(True)
        else:
            fuv.append(all(pum[i]))

    launch = all(fuv)
    return cmv, pum, fuv, launch


def _load_input() -> Tuple[int, List[float], List[float], Dict[str, Any], List[List[str]], List[bool]]:
    obj = json.load(sys.stdin)
    return (
        int(obj["numpoints"]),
        list(obj["x"]),
        list(obj["y"]),
        dict(obj["parameters"]),
        list(obj["lcm"]),
        list(obj["pum_diag"]),
    )


def main() -> None:
    numpoints, x, y, parameters, lcm, pum_diag = _load_input()
    cmv, pum, fuv, launch = decide(numpoints, x, y, parameters, lcm, pum_diag)
    json.dump(
        {"cmv": cmv, "pum": pum, "fuv": fuv, "launch": launch},
        sys.stdout,
    )


if __name__ == "__main__":
    main()
