import json
import math
import sys


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


def _le(a: float, b: float) -> bool:
    return realcompare(a, b) != "GT"


def _point(x: list[float], y: list[float], idx: int) -> tuple[float, float]:
    return x[idx], y[idx]


def _same_point(p1: tuple[float, float], p2: tuple[float, float]) -> bool:
    return _eq(p1[0], p2[0]) and _eq(p1[1], p2[1])


def _distance(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def _triangle_area(
    p1: tuple[float, float], p2: tuple[float, float], p3: tuple[float, float]
) -> float:
    return abs(
        p1[0] * (p2[1] - p3[1])
        + p2[0] * (p3[1] - p1[1])
        + p3[0] * (p1[1] - p2[1])
    ) / 2.0


def _angle_condition(
    p1: tuple[float, float],
    vertex: tuple[float, float],
    p3: tuple[float, float],
    epsilon: float,
) -> bool:
    if _same_point(p1, vertex) or _same_point(p3, vertex):
        return False
    v1x = p1[0] - vertex[0]
    v1y = p1[1] - vertex[1]
    v2x = p3[0] - vertex[0]
    v2y = p3[1] - vertex[1]
    cross = v1x * v2y - v1y * v2x
    dot = v1x * v2x + v1y * v2y
    angle = math.atan2(abs(cross), dot)
    return _lt(angle, PI - epsilon) or _gt(angle, PI + epsilon)


def _quadrant(p: tuple[float, float]) -> int:
    x, y = p
    if _ge_zero(x) and _ge_zero(y):
        return 1
    if _lt(x, 0.0) and _ge_zero(y):
        return 2
    if _le(x, 0.0) and _lt(y, 0.0):
        return 3
    return 4


def _ge_zero(v: float) -> bool:
    return realcompare(v, 0.0) != "LT"


def _line_distance(
    p: tuple[float, float], start: tuple[float, float], end: tuple[float, float]
) -> float:
    if _same_point(start, end):
        return _distance(p, start)
    numerator = abs(
        (end[1] - start[1]) * p[0]
        - (end[0] - start[0]) * p[1]
        + end[0] * start[1]
        - end[1] * start[0]
    )
    denominator = _distance(start, end)
    return numerator / denominator


def _minimal_enclosing_radius(
    p1: tuple[float, float], p2: tuple[float, float], p3: tuple[float, float]
) -> float:
    a = _distance(p2, p3)
    b = _distance(p1, p3)
    c = _distance(p1, p2)
    sides = [a, b, c]
    max_side = max(sides)
    max_sq = max_side * max_side
    other_sq_sum = sum(side * side for side in sides) - max_sq
    if realcompare(max_sq, other_sq_sum) != "LT":
        return max_side / 2.0
    double_area = abs(
        (p2[0] - p1[0]) * (p3[1] - p1[1]) - (p2[1] - p1[1]) * (p3[0] - p1[0])
    )
    if _eq(double_area, 0.0):
        return max_side / 2.0
    return (a * b * c) / (2.0 * double_area)


def _lic1(numpoints: int, x: list[float], y: list[float], params: dict) -> bool:
    for i in range(numpoints - 1):
        if _gt(_distance(_point(x, y, i), _point(x, y, i + 1)), params["LENGTH1"]):
            return True
    return False


def _lic2(numpoints: int, x: list[float], y: list[float], params: dict) -> bool:
    for i in range(numpoints - 2):
        if _gt(
            _minimal_enclosing_radius(
                _point(x, y, i), _point(x, y, i + 1), _point(x, y, i + 2)
            ),
            params["RADIUS1"],
        ):
            return True
    return False


def _lic3(numpoints: int, x: list[float], y: list[float], params: dict) -> bool:
    for i in range(numpoints - 2):
        if _angle_condition(
            _point(x, y, i), _point(x, y, i + 1), _point(x, y, i + 2), params["EPSILON"]
        ):
            return True
    return False


def _lic4(numpoints: int, x: list[float], y: list[float], params: dict) -> bool:
    for i in range(numpoints - 2):
        if _gt(
            _triangle_area(_point(x, y, i), _point(x, y, i + 1), _point(x, y, i + 2)),
            params["AREA1"],
        ):
            return True
    return False


def _lic5(numpoints: int, x: list[float], y: list[float], params: dict) -> bool:
    q_pts = params["Q_PTS"]
    quads = params["QUADS"]
    for start in range(numpoints - q_pts + 1):
        used = {
            _quadrant(_point(x, y, idx))
            for idx in range(start, start + q_pts)
        }
        if len(used) > quads:
            return True
    return False


def _lic6(numpoints: int, x: list[float], y: list[float], params: dict) -> bool:
    del y, params
    for i in range(numpoints - 1):
        if _lt(x[i + 1] - x[i], 0.0):
            return True
    return False


def _lic7(numpoints: int, x: list[float], y: list[float], params: dict) -> bool:
    if numpoints < 3:
        return False
    n_pts = params["N_PTS"]
    dist = params["DIST"]
    for start in range(numpoints - n_pts + 1):
        first = _point(x, y, start)
        last = _point(x, y, start + n_pts - 1)
        for idx in range(start + 1, start + n_pts - 1):
            if _gt(_line_distance(_point(x, y, idx), first, last), dist):
                return True
    return False


def _lic8(numpoints: int, x: list[float], y: list[float], params: dict) -> bool:
    if numpoints < 3:
        return False
    gap = params["K_PTS"] + 1
    for i in range(numpoints - gap):
        if _gt(_distance(_point(x, y, i), _point(x, y, i + gap)), params["LENGTH1"]):
            return True
    return False


def _lic9(numpoints: int, x: list[float], y: list[float], params: dict) -> bool:
    if numpoints < 5:
        return False
    gap1 = params["A_PTS"] + 1
    gap2 = params["B_PTS"] + 1
    for i in range(numpoints - gap1 - gap2):
        if _gt(
            _minimal_enclosing_radius(
                _point(x, y, i),
                _point(x, y, i + gap1),
                _point(x, y, i + gap1 + gap2),
            ),
            params["RADIUS1"],
        ):
            return True
    return False


def _lic10(numpoints: int, x: list[float], y: list[float], params: dict) -> bool:
    if numpoints < 5:
        return False
    gap1 = params["C_PTS"] + 1
    gap2 = params["D_PTS"] + 1
    for i in range(numpoints - gap1 - gap2):
        if _angle_condition(
            _point(x, y, i),
            _point(x, y, i + gap1),
            _point(x, y, i + gap1 + gap2),
            params["EPSILON"],
        ):
            return True
    return False


def _lic11(numpoints: int, x: list[float], y: list[float], params: dict) -> bool:
    if numpoints < 5:
        return False
    gap1 = params["E_PTS"] + 1
    gap2 = params["F_PTS"] + 1
    for i in range(numpoints - gap1 - gap2):
        if _gt(
            _triangle_area(
                _point(x, y, i),
                _point(x, y, i + gap1),
                _point(x, y, i + gap1 + gap2),
            ),
            params["AREA1"],
        ):
            return True
    return False


def _lic12(numpoints: int, x: list[float], y: list[float], params: dict) -> bool:
    del y
    if numpoints < 3:
        return False
    gap = params["G_PTS"] + 1
    for i in range(numpoints - gap):
        if _lt(x[i + gap] - x[i], 0.0):
            return True
    return False


def _lic13(numpoints: int, x: list[float], y: list[float], params: dict) -> bool:
    if numpoints < 3:
        return False
    gap = params["K_PTS"] + 1
    has_gt = False
    has_lt = False
    for i in range(numpoints - gap):
        dist = _distance(_point(x, y, i), _point(x, y, i + gap))
        if _gt(dist, params["LENGTH1"]):
            has_gt = True
        if _lt(dist, params["LENGTH2"]):
            has_lt = True
    return has_gt and has_lt


def _lic14(numpoints: int, x: list[float], y: list[float], params: dict) -> bool:
    if numpoints < 5:
        return False
    gap1 = params["A_PTS"] + 1
    gap2 = params["B_PTS"] + 1
    has_gt = False
    has_le = False
    for i in range(numpoints - gap1 - gap2):
        radius = _minimal_enclosing_radius(
            _point(x, y, i),
            _point(x, y, i + gap1),
            _point(x, y, i + gap1 + gap2),
        )
        if _gt(radius, params["RADIUS1"]):
            has_gt = True
        if _le(radius, params["RADIUS2"]):
            has_le = True
    return has_gt and has_le


def _lic15(numpoints: int, x: list[float], y: list[float], params: dict) -> bool:
    if numpoints < 5:
        return False
    gap1 = params["E_PTS"] + 1
    gap2 = params["F_PTS"] + 1
    has_gt = False
    has_lt = False
    for i in range(numpoints - gap1 - gap2):
        area = _triangle_area(
            _point(x, y, i),
            _point(x, y, i + gap1),
            _point(x, y, i + gap1 + gap2),
        )
        if _gt(area, params["AREA1"]):
            has_gt = True
        if _lt(area, params["AREA2"]):
            has_lt = True
    return has_gt and has_lt


_LICS = [
    _lic1,
    _lic2,
    _lic3,
    _lic4,
    _lic5,
    _lic6,
    _lic7,
    _lic8,
    _lic9,
    _lic10,
    _lic11,
    _lic12,
    _lic13,
    _lic14,
    _lic15,
]


def decide(
    numpoints: int,
    x: list[float],
    y: list[float],
    parameters: dict,
    lcm: list[list[str]],
    pum_diag: list[bool],
) -> tuple[list[bool], list[list[bool]], list[bool], bool]:
    cmv = [lic(numpoints, x, y, parameters) for lic in _LICS]

    pum = [[False] * 15 for _ in range(15)]
    for i in range(15):
        for j in range(15):
            if i == j:
                pum[i][j] = bool(pum_diag[i])
            else:
                connector = lcm[i][j]
                if connector == "NOTUSED":
                    pum[i][j] = True
                elif connector == "ANDD":
                    pum[i][j] = cmv[i] and cmv[j]
                elif connector == "ORR":
                    pum[i][j] = cmv[i] or cmv[j]
                else:
                    raise ValueError(f"Unknown connector: {connector}")

    fuv = []
    for i in range(15):
        fuv.append((not pum[i][i]) or all(pum[i]))

    launch = all(fuv)
    return cmv, pum, fuv, launch


def _main() -> None:
    payload = json.load(sys.stdin)
    cmv, pum, fuv, launch = decide(
        payload["numpoints"],
        payload["x"],
        payload["y"],
        payload["parameters"],
        payload["lcm"],
        payload["pum_diag"],
    )
    json.dump({"cmv": cmv, "pum": pum, "fuv": fuv, "launch": launch}, sys.stdout)


if __name__ == "__main__":
    _main()
