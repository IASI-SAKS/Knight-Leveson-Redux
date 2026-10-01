"""Launch Interceptor Program (Knight & Leveson, 1986)."""

from __future__ import annotations

import json
import math
import sys
from typing import Any

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


def _lt(a: float, b: float) -> bool:
    return realcompare(a, b) == "LT"


def _gt(a: float, b: float) -> bool:
    return realcompare(a, b) == "GT"


def _eq(a: float, b: float) -> bool:
    return realcompare(a, b) == "EQ"


def _le(a: float, b: float) -> bool:
    cmp_result = realcompare(a, b)
    return cmp_result in ("LT", "EQ")


def _ge(a: float, b: float) -> bool:
    cmp_result = realcompare(a, b)
    return cmp_result in ("GT", "EQ")


def _distance(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.hypot(x2 - x1, y2 - y1)


def _triangle_area(x1: float, y1: float, x2: float, y2: float, x3: float, y3: float) -> float:
    return abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)) / 2.0


def _quadrant(x: float, y: float) -> int:
    x_cmp = realcompare(x, 0.0)
    y_cmp = realcompare(y, 0.0)

    if x_cmp == "EQ" and y_cmp == "EQ":
        return 1

    if y_cmp == "EQ":
        if x_cmp == "LT":
            return 2
        return 1

    if x_cmp == "EQ":
        if y_cmp == "LT":
            return 3
        return 1

    if x_cmp == "GT" and y_cmp == "GT":
        return 1
    if x_cmp == "LT" and y_cmp == "GT":
        return 2
    if x_cmp == "LT" and y_cmp == "LT":
        return 3
    return 4


def _angle_at_vertex(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    x3: float,
    y3: float,
) -> float | None:
    if _eq(x1, x2) and _eq(y1, y2):
        return None
    if _eq(x3, x2) and _eq(y3, y2):
        return None

    v1x, v1y = x1 - x2, y1 - y2
    v2x, v2y = x3 - x2, y3 - y2
    len1 = math.hypot(v1x, v1y)
    len2 = math.hypot(v2x, v2y)
    if _eq(len1, 0.0) or _eq(len2, 0.0):
        return None

    dot = v1x * v2x + v1y * v2y
    cos_angle = dot / (len1 * len2)
    if cos_angle > 1.0:
        cos_angle = 1.0
    elif cos_angle < -1.0:
        cos_angle = -1.0
    return math.acos(cos_angle)


def _min_enclosing_radius(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    x3: float,
    y3: float,
) -> float:
    d12 = _distance(x1, y1, x2, y2)
    d23 = _distance(x2, y2, x3, y3)
    d13 = _distance(x1, y1, x3, y3)

    v1x, v1y = x1 - x2, y1 - y2
    v2x, v2y = x3 - x2, y3 - y2
    if _le(v1x * v2x + v1y * v2y, 0.0):
        return d13 / 2.0

    v1x, v1y = x2 - x1, y2 - y1
    v2x, v2y = x3 - x1, y3 - y1
    if _le(v1x * v2x + v1y * v2y, 0.0):
        return d23 / 2.0

    v1x, v1y = x1 - x3, y1 - y3
    v2x, v2y = x2 - x3, y2 - y3
    if _le(v1x * v2x + v1y * v2y, 0.0):
        return d12 / 2.0

    area = _triangle_area(x1, y1, x2, y2, x3, y3)
    if _eq(area, 0.0):
        return max(d12, d23, d13) / 2.0
    return (d12 * d23 * d13) / (4.0 * area)


def _point_line_distance(
    px: float,
    py: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> float:
    if _eq(x1, x2) and _eq(y1, y2):
        return _distance(px, py, x1, y1)

    numerator = abs((y2 - y1) * px - (x2 - x1) * py + x2 * y1 - y2 * x1)
    denominator = _distance(x1, y1, x2, y2)
    return numerator / denominator


def _lic1(x: list[float], y: list[float], length1: float) -> bool:
    for i in range(len(x) - 1):
        dist = _distance(x[i], y[i], x[i + 1], y[i + 1])
        if _gt(dist, length1):
            return True
    return False


def _lic2(x: list[float], y: list[float], radius1: float) -> bool:
    for i in range(len(x) - 2):
        radius = _min_enclosing_radius(x[i], y[i], x[i + 1], y[i + 1], x[i + 2], y[i + 2])
        if _gt(radius, radius1):
            return True
    return False


def _lic3(x: list[float], y: list[float], epsilon: float) -> bool:
    for i in range(len(x) - 2):
        angle = _angle_at_vertex(x[i], y[i], x[i + 1], y[i + 1], x[i + 2], y[i + 2])
        if angle is None:
            continue
        if _lt(angle, PI - epsilon) or _gt(angle, PI + epsilon):
            return True
    return False


def _lic4(x: list[float], y: list[float], area1: float) -> bool:
    for i in range(len(x) - 2):
        area = _triangle_area(x[i], y[i], x[i + 1], y[i + 1], x[i + 2], y[i + 2])
        if _gt(area, area1):
            return True
    return False


def _lic5(x: list[float], y: list[float], q_pts: int, quads: int) -> bool:
    for start in range(len(x) - q_pts + 1):
        quadrants = {_quadrant(x[start + j], y[start + j]) for j in range(q_pts)}
        if len(quadrants) > quads:
            return True
    return False


def _lic6(x: list[float], y: list[float]) -> bool:
    for i in range(len(x) - 1):
        if _lt(x[i + 1] - x[i], 0.0):
            return True
    return False


def _lic7(x: list[float], y: list[float], dist_param: float, n_pts: int) -> bool:
    if len(x) < 3:
        return False

    for start in range(len(x) - n_pts + 1):
        end = start + n_pts - 1
        x_first, y_first = x[start], y[start]
        x_last, y_last = x[end], y[end]
        for idx in range(start, end + 1):
            point_dist = _point_line_distance(
                x[idx],
                y[idx],
                x_first,
                y_first,
                x_last,
                y_last,
            )
            if _gt(point_dist, dist_param):
                return True
    return False


def _lic8(x: list[float], y: list[float], k_pts: int, length1: float) -> bool:
    if len(x) < 3:
        return False

    for i in range(len(x) - k_pts - 1):
        j = i + k_pts + 1
        dist = _distance(x[i], y[i], x[j], y[j])
        if _gt(dist, length1):
            return True
    return False


def _lic9(x: list[float], y: list[float], a_pts: int, b_pts: int, radius1: float) -> bool:
    if len(x) < 5:
        return False

    for i in range(len(x) - a_pts - b_pts - 2):
        i2 = i + a_pts + 1
        i3 = i2 + b_pts + 1
        radius = _min_enclosing_radius(x[i], y[i], x[i2], y[i2], x[i3], y[i3])
        if _gt(radius, radius1):
            return True
    return False


def _lic10(
    x: list[float],
    y: list[float],
    c_pts: int,
    d_pts: int,
    epsilon: float,
) -> bool:
    if len(x) < 5:
        return False

    for i in range(len(x) - c_pts - d_pts - 2):
        i2 = i + c_pts + 1
        i3 = i2 + d_pts + 1
        angle = _angle_at_vertex(x[i], y[i], x[i2], y[i2], x[i3], y[i3])
        if angle is None:
            continue
        if _lt(angle, PI - epsilon) or _gt(angle, PI + epsilon):
            return True
    return False


def _lic11(x: list[float], y: list[float], e_pts: int, f_pts: int, area1: float) -> bool:
    if len(x) < 5:
        return False

    for i in range(len(x) - e_pts - f_pts - 2):
        i2 = i + e_pts + 1
        i3 = i2 + f_pts + 1
        area = _triangle_area(x[i], y[i], x[i2], y[i2], x[i3], y[i3])
        if _gt(area, area1):
            return True
    return False


def _lic12(x: list[float], y: list[float], g_pts: int) -> bool:
    if len(x) < 3:
        return False

    for i in range(len(x) - g_pts - 1):
        j = i + g_pts + 1
        if _lt(x[j] - x[i], 0.0):
            return True
    return False


def _lic13(
    x: list[float],
    y: list[float],
    k_pts: int,
    length1: float,
    length2: float,
) -> bool:
    if len(x) < 3:
        return False

    found_gt = False
    found_lt = False
    for i in range(len(x) - k_pts - 1):
        j = i + k_pts + 1
        dist = _distance(x[i], y[i], x[j], y[j])
        if _gt(dist, length1):
            found_gt = True
        if _lt(dist, length2):
            found_lt = True
        if found_gt and found_lt:
            return True
    return False


def _lic14(
    x: list[float],
    y: list[float],
    a_pts: int,
    b_pts: int,
    radius1: float,
    radius2: float,
) -> bool:
    if len(x) < 5:
        return False

    found_not_in_r1 = False
    found_in_r2 = False
    for i in range(len(x) - a_pts - b_pts - 2):
        i2 = i + a_pts + 1
        i3 = i2 + b_pts + 1
        radius = _min_enclosing_radius(x[i], y[i], x[i2], y[i2], x[i3], y[i3])
        if _gt(radius, radius1):
            found_not_in_r1 = True
        if _le(radius, radius2):
            found_in_r2 = True
        if found_not_in_r1 and found_in_r2:
            return True
    return False


def _lic15(
    x: list[float],
    y: list[float],
    e_pts: int,
    f_pts: int,
    area1: float,
    area2: float,
) -> bool:
    if len(x) < 5:
        return False

    found_gt = False
    found_lt = False
    for i in range(len(x) - e_pts - f_pts - 2):
        i2 = i + e_pts + 1
        i3 = i2 + f_pts + 1
        area = _triangle_area(x[i], y[i], x[i2], y[i2], x[i3], y[i3])
        if _gt(area, area1):
            found_gt = True
        if _lt(area, area2):
            found_lt = True
        if found_gt and found_lt:
            return True
    return False


def _compute_cmv(
    numpoints: int,
    x: list[float],
    y: list[float],
    parameters: dict[str, Any],
) -> list[bool]:
    p = parameters
    return [
        _lic1(x, y, p["LENGTH1"]),
        _lic2(x, y, p["RADIUS1"]),
        _lic3(x, y, p["EPSILON"]),
        _lic4(x, y, p["AREA1"]),
        _lic5(x, y, p["Q_PTS"], p["QUADS"]),
        _lic6(x, y),
        _lic7(x, y, p["DIST"], p["N_PTS"]),
        _lic8(x, y, p["K_PTS"], p["LENGTH1"]),
        _lic9(x, y, p["A_PTS"], p["B_PTS"], p["RADIUS1"]),
        _lic10(x, y, p["C_PTS"], p["D_PTS"], p["EPSILON"]),
        _lic11(x, y, p["E_PTS"], p["F_PTS"], p["AREA1"]),
        _lic12(x, y, p["G_PTS"]),
        _lic13(x, y, p["K_PTS"], p["LENGTH1"], p["LENGTH2"]),
        _lic14(x, y, p["A_PTS"], p["B_PTS"], p["RADIUS1"], p["RADIUS2"]),
        _lic15(x, y, p["E_PTS"], p["F_PTS"], p["AREA1"], p["AREA2"]),
    ]


def _compute_pum(cmv: list[bool], lcm: list[list[str]], pum_diag: list[bool]) -> list[list[bool]]:
    size = 15
    pum = [[False] * size for _ in range(size)]
    for i in range(size):
        pum[i][i] = pum_diag[i]

    for i in range(size):
        for j in range(i + 1, size):
            connector = lcm[i][j]
            if connector == "NOTUSED":
                value = True
            elif connector == "ANDD":
                value = cmv[i] and cmv[j]
            elif connector == "ORR":
                value = cmv[i] or cmv[j]
            else:
                raise ValueError(f"Unknown connector: {connector}")
            pum[i][j] = value
            pum[j][i] = value

    return pum


def _compute_fuv(pum: list[list[bool]]) -> list[bool]:
    size = 15
    fuv: list[bool] = []
    for i in range(size):
        if not pum[i][i]:
            fuv.append(True)
        else:
            fuv.append(all(pum[i][j] for j in range(size)))
    return fuv


def decide(
    numpoints: int,
    x: list[float],
    y: list[float],
    parameters: dict[str, Any],
    lcm: list[list[str]],
    pum_diag: list[bool],
) -> dict[str, Any]:
    x = x[:numpoints]
    y = y[:numpoints]

    cmv = _compute_cmv(numpoints, x, y, parameters)
    pum = _compute_pum(cmv, lcm, pum_diag)
    fuv = _compute_fuv(pum)
    launch = all(fuv)

    return {
        "cmv": cmv,
        "pum": pum,
        "fuv": fuv,
        "launch": launch,
    }


def _main() -> None:
    data = json.load(sys.stdin)
    result = decide(
        data["numpoints"],
        data["x"],
        data["y"],
        data["parameters"],
        data["lcm"],
        data["pum_diag"],
    )
    json.dump(result, sys.stdout)


if __name__ == "__main__":
    _main()
