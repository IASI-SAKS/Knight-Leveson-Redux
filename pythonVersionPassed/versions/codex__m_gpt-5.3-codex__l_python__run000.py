import json
import math
import sys
from typing import Dict, List, Tuple

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


def _gt(a: float, b: float) -> bool:
    return realcompare(a, b) == "GT"


def _lt(a: float, b: float) -> bool:
    return realcompare(a, b) == "LT"


def _eq(a: float, b: float) -> bool:
    return realcompare(a, b) == "EQ"


def _distance(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.hypot(x2 - x1, y2 - y1)


def _triangle_area(p1: Tuple[float, float], p2: Tuple[float, float], p3: Tuple[float, float]) -> float:
    return abs(
        p1[0] * (p2[1] - p3[1])
        + p2[0] * (p3[1] - p1[1])
        + p3[0] * (p1[1] - p2[1])
    ) / 2.0


def _required_circle_radius_for_three_points(
    p1: Tuple[float, float], p2: Tuple[float, float], p3: Tuple[float, float]
) -> float:
    a = _distance(p2[0], p2[1], p3[0], p3[1])
    b = _distance(p1[0], p1[1], p3[0], p3[1])
    c = _distance(p1[0], p1[1], p2[0], p2[1])

    longest = max(a, b, c)
    if _eq(longest, 0.0):
        return 0.0

    a2 = a * a
    b2 = b * b
    c2 = c * c
    sides2 = sorted([a2, b2, c2])

    # Right or obtuse: minimal enclosing circle is half of the longest side.
    if realcompare(sides2[2], sides2[0] + sides2[1]) != "LT":
        return longest / 2.0

    area = _triangle_area(p1, p2, p3)
    if _eq(area, 0.0):
        return longest / 2.0

    return (a * b * c) / (4.0 * area)


def _angle_condition(
    p1: Tuple[float, float], p2: Tuple[float, float], p3: Tuple[float, float], epsilon: float
) -> bool:
    v1x = p1[0] - p2[0]
    v1y = p1[1] - p2[1]
    v2x = p3[0] - p2[0]
    v2y = p3[1] - p2[1]

    n1 = math.hypot(v1x, v1y)
    n2 = math.hypot(v2x, v2y)

    # Undefined angle when first or third coincides with vertex.
    if _eq(n1, 0.0) or _eq(n2, 0.0):
        return False

    dot = v1x * v2x + v1y * v2y
    cosv = dot / (n1 * n2)
    if cosv > 1.0:
        cosv = 1.0
    elif cosv < -1.0:
        cosv = -1.0

    angle = math.acos(cosv)
    return _lt(angle, PI - epsilon) or _gt(angle, PI + epsilon)


def _quadrant(x: float, y: float) -> int:
    if x >= 0.0 and y >= 0.0:
        return 1
    if x < 0.0 and y >= 0.0:
        return 2
    if x <= 0.0 and y < 0.0:
        return 3
    return 4


def _distance_point_to_line(
    p: Tuple[float, float], a: Tuple[float, float], b: Tuple[float, float]
) -> float:
    if _eq(a[0], b[0]) and _eq(a[1], b[1]):
        return _distance(p[0], p[1], a[0], a[1])
    num = abs((b[1] - a[1]) * p[0] - (b[0] - a[0]) * p[1] + b[0] * a[1] - b[1] * a[0])
    den = _distance(a[0], a[1], b[0], b[1])
    return num / den


def _lic1(n: int, x: List[float], y: List[float], p: Dict[str, float]) -> bool:
    l1 = p["LENGTH1"]
    for i in range(n - 1):
        if _gt(_distance(x[i], y[i], x[i + 1], y[i + 1]), l1):
            return True
    return False


def _lic2(n: int, x: List[float], y: List[float], p: Dict[str, float]) -> bool:
    r1 = p["RADIUS1"]
    for i in range(n - 2):
        req = _required_circle_radius_for_three_points(
            (x[i], y[i]), (x[i + 1], y[i + 1]), (x[i + 2], y[i + 2])
        )
        if _gt(req, r1):
            return True
    return False


def _lic3(n: int, x: List[float], y: List[float], p: Dict[str, float]) -> bool:
    eps = p["EPSILON"]
    for i in range(n - 2):
        if _angle_condition((x[i], y[i]), (x[i + 1], y[i + 1]), (x[i + 2], y[i + 2]), eps):
            return True
    return False


def _lic4(n: int, x: List[float], y: List[float], p: Dict[str, float]) -> bool:
    a1 = p["AREA1"]
    for i in range(n - 2):
        area = _triangle_area((x[i], y[i]), (x[i + 1], y[i + 1]), (x[i + 2], y[i + 2]))
        if _gt(area, a1):
            return True
    return False


def _lic5(n: int, x: List[float], y: List[float], p: Dict[str, float]) -> bool:
    q_pts = p["Q_PTS"]
    quads = p["QUADS"]
    for i in range(n - q_pts + 1):
        present = set()
        for j in range(i, i + q_pts):
            present.add(_quadrant(x[j], y[j]))
        if len(present) > quads:
            return True
    return False


def _lic6(n: int, x: List[float]) -> bool:
    for i in range(n - 1):
        if _lt(x[i + 1] - x[i], 0.0):
            return True
    return False


def _lic7(n: int, x: List[float], y: List[float], p: Dict[str, float]) -> bool:
    if n < 3:
        return False
    n_pts = p["N_PTS"]
    dist = p["DIST"]
    for i in range(n - n_pts + 1):
        a = (x[i], y[i])
        b = (x[i + n_pts - 1], y[i + n_pts - 1])
        for j in range(i + 1, i + n_pts - 1):
            d = _distance_point_to_line((x[j], y[j]), a, b)
            if _gt(d, dist):
                return True
    return False


def _lic8(n: int, x: List[float], y: List[float], p: Dict[str, float]) -> bool:
    if n < 3:
        return False
    k = p["K_PTS"]
    l1 = p["LENGTH1"]
    span = k + 1
    for i in range(n - span):
        if _gt(_distance(x[i], y[i], x[i + span], y[i + span]), l1):
            return True
    return False


def _lic9(n: int, x: List[float], y: List[float], p: Dict[str, float]) -> bool:
    if n < 5:
        return False
    a_pts = p["A_PTS"]
    b_pts = p["B_PTS"]
    r1 = p["RADIUS1"]
    i2 = a_pts + 1
    i3 = a_pts + b_pts + 2
    for i in range(n - i3):
        req = _required_circle_radius_for_three_points(
            (x[i], y[i]), (x[i + i2], y[i + i2]), (x[i + i3], y[i + i3])
        )
        if _gt(req, r1):
            return True
    return False


def _lic10(n: int, x: List[float], y: List[float], p: Dict[str, float]) -> bool:
    if n < 5:
        return False
    c_pts = p["C_PTS"]
    d_pts = p["D_PTS"]
    eps = p["EPSILON"]
    i2 = c_pts + 1
    i3 = c_pts + d_pts + 2
    for i in range(n - i3):
        if _angle_condition((x[i], y[i]), (x[i + i2], y[i + i2]), (x[i + i3], y[i + i3]), eps):
            return True
    return False


def _lic11(n: int, x: List[float], y: List[float], p: Dict[str, float]) -> bool:
    if n < 5:
        return False
    e_pts = p["E_PTS"]
    f_pts = p["F_PTS"]
    a1 = p["AREA1"]
    i2 = e_pts + 1
    i3 = e_pts + f_pts + 2
    for i in range(n - i3):
        area = _triangle_area((x[i], y[i]), (x[i + i2], y[i + i2]), (x[i + i3], y[i + i3]))
        if _gt(area, a1):
            return True
    return False


def _lic12(n: int, x: List[float], p: Dict[str, float]) -> bool:
    if n < 3:
        return False
    g = p["G_PTS"]
    span = g + 1
    for i in range(n - span):
        if _lt(x[i + span] - x[i], 0.0):
            return True
    return False


def _lic13(n: int, x: List[float], y: List[float], p: Dict[str, float]) -> bool:
    if n < 3:
        return False
    k = p["K_PTS"]
    l1 = p["LENGTH1"]
    l2 = p["LENGTH2"]
    span = k + 1
    any_gt_l1 = False
    any_lt_l2 = False
    for i in range(n - span):
        d = _distance(x[i], y[i], x[i + span], y[i + span])
        if _gt(d, l1):
            any_gt_l1 = True
        if _lt(d, l2):
            any_lt_l2 = True
    return any_gt_l1 and any_lt_l2


def _lic14(n: int, x: List[float], y: List[float], p: Dict[str, float]) -> bool:
    if n < 5:
        return False
    a_pts = p["A_PTS"]
    b_pts = p["B_PTS"]
    r1 = p["RADIUS1"]
    r2 = p["RADIUS2"]
    i2 = a_pts + 1
    i3 = a_pts + b_pts + 2
    any_gt_r1 = False
    any_le_r2 = False
    for i in range(n - i3):
        req = _required_circle_radius_for_three_points(
            (x[i], y[i]), (x[i + i2], y[i + i2]), (x[i + i3], y[i + i3])
        )
        if _gt(req, r1):
            any_gt_r1 = True
        if realcompare(req, r2) in ("LT", "EQ"):
            any_le_r2 = True
    return any_gt_r1 and any_le_r2


def _lic15(n: int, x: List[float], y: List[float], p: Dict[str, float]) -> bool:
    if n < 5:
        return False
    e_pts = p["E_PTS"]
    f_pts = p["F_PTS"]
    a1 = p["AREA1"]
    a2 = p["AREA2"]
    i2 = e_pts + 1
    i3 = e_pts + f_pts + 2
    any_gt_a1 = False
    any_lt_a2 = False
    for i in range(n - i3):
        area = _triangle_area((x[i], y[i]), (x[i + i2], y[i + i2]), (x[i + i3], y[i + i3]))
        if _gt(area, a1):
            any_gt_a1 = True
        if _lt(area, a2):
            any_lt_a2 = True
    return any_gt_a1 and any_lt_a2


def decide(
    numpoints: int,
    x: List[float],
    y: List[float],
    parameters: Dict[str, float],
    lcm: List[List[str]],
    pum_diag: List[bool],
):
    cmv = [False] * 15
    cmv[0] = _lic1(numpoints, x, y, parameters)
    cmv[1] = _lic2(numpoints, x, y, parameters)
    cmv[2] = _lic3(numpoints, x, y, parameters)
    cmv[3] = _lic4(numpoints, x, y, parameters)
    cmv[4] = _lic5(numpoints, x, y, parameters)
    cmv[5] = _lic6(numpoints, x)
    cmv[6] = _lic7(numpoints, x, y, parameters)
    cmv[7] = _lic8(numpoints, x, y, parameters)
    cmv[8] = _lic9(numpoints, x, y, parameters)
    cmv[9] = _lic10(numpoints, x, y, parameters)
    cmv[10] = _lic11(numpoints, x, y, parameters)
    cmv[11] = _lic12(numpoints, x, parameters)
    cmv[12] = _lic13(numpoints, x, y, parameters)
    cmv[13] = _lic14(numpoints, x, y, parameters)
    cmv[14] = _lic15(numpoints, x, y, parameters)

    pum = [[True] * 15 for _ in range(15)]
    for i in range(15):
        pum[i][i] = bool(pum_diag[i])

    for i in range(15):
        for j in range(15):
            if i == j:
                continue
            conn = lcm[i][j]
            if conn == "NOTUSED":
                pum[i][j] = True
            elif conn == "ANDD":
                pum[i][j] = cmv[i] and cmv[j]
            elif conn == "ORR":
                pum[i][j] = cmv[i] or cmv[j]
            else:
                raise ValueError(f"Unknown LCM connector: {conn}")

    fuv = [False] * 15
    for i in range(15):
        fuv[i] = (not pum[i][i]) or all(pum[i][j] for j in range(15))

    launch = all(fuv)
    return cmv, pum, fuv, launch


def _main() -> None:
    data = json.load(sys.stdin)
    cmv, pum, fuv, launch = decide(
        numpoints=data["numpoints"],
        x=data["x"],
        y=data["y"],
        parameters=data["parameters"],
        lcm=data["lcm"],
        pum_diag=data["pum_diag"],
    )
    json.dump(
        {
            "cmv": cmv,
            "pum": pum,
            "fuv": fuv,
            "launch": launch,
        },
        sys.stdout,
    )


if __name__ == "__main__":
    _main()
