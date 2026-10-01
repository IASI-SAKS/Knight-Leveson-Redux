"""
Launch Interceptor Program (DECIDE) implementation from Knight & Leveson (1986).

This module is self-contained, uses only the Python standard library, and is
designed to be importable with no side effects at import time.

Runtime behavior (when executed as a script):
  - Reads exactly one JSON object from stdin (matching the shape of an `input`
    object in prompt_examples.json).
  - Writes exactly one JSON object to stdout (matching the shape of an
    `expected` object in prompt_examples.json).

Primary source snapshot for archival is included at the bottom of this file.
"""

from __future__ import annotations

import json
import math
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple


# Pascal constant from the spec (radians in 180 degrees).
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


def _le(a: float, b: float) -> bool:
    return realcompare(a, b) != "GT"


def _ge(a: float, b: float) -> bool:
    return realcompare(a, b) != "LT"


Point = Tuple[float, float]


def _points_equal(p: Point, q: Point) -> bool:
    return realcompare(p[0], q[0]) == "EQ" and realcompare(p[1], q[1]) == "EQ"


def _distance(p: Point, q: Point) -> float:
    return math.hypot(q[0] - p[0], q[1] - p[1])


def _triangle_area(p1: Point, p2: Point, p3: Point) -> float:
    # Area = |(p2 - p1) x (p3 - p1)| / 2
    cross = (p2[0] - p1[0]) * (p3[1] - p1[1]) - (p2[1] - p1[1]) * (p3[0] - p1[0])
    return abs(cross) * 0.5


def _angle_at_vertex(p1: Point, vertex: Point, p3: Point) -> Optional[float]:
    # Undefined if either endpoint coincides with the vertex.
    if _points_equal(p1, vertex) or _points_equal(p3, vertex):
        return None

    v1x, v1y = p1[0] - vertex[0], p1[1] - vertex[1]
    v2x, v2y = p3[0] - vertex[0], p3[1] - vertex[1]
    mag1 = math.hypot(v1x, v1y)
    mag2 = math.hypot(v2x, v2y)
    if realcompare(mag1, 0.0) == "EQ" or realcompare(mag2, 0.0) == "EQ":
        return None

    dot = v1x * v2x + v1y * v2y
    cos_theta = dot / (mag1 * mag2)
    # Numerical safety.
    if cos_theta > 1.0:
        cos_theta = 1.0
    elif cos_theta < -1.0:
        cos_theta = -1.0
    return math.acos(cos_theta)  # In [0, PI]


def _distance_point_to_line(p: Point, a: Point, b: Point) -> float:
    # Distance from point p to the (infinite) line through points a and b.
    if _points_equal(a, b):
        return _distance(p, a)

    x0, y0 = p
    x1, y1 = a
    x2, y2 = b
    num = abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1)
    den = math.hypot(y2 - y1, x2 - x1)
    if realcompare(den, 0.0) == "EQ":
        return _distance(p, a)
    return num / den


def _required_radius_three_points(p1: Point, p2: Point, p3: Point) -> float:
    """
    Radius of the smallest circle that contains p1, p2, p3 (in or on).
    """
    # Handle coincident points via distances naturally.
    d12 = _distance(p1, p2)
    d23 = _distance(p2, p3)
    d13 = _distance(p1, p3)
    longest = max(d12, d23, d13)

    area = _triangle_area(p1, p2, p3)
    if realcompare(area, 0.0) == "EQ":
        # Collinear or duplicate points: minimal enclosing circle is defined by
        # the endpoints of the longest segment.
        return longest * 0.5

    # Check for obtuse/right triangle using squared lengths:
    # longest^2 >= sum(other^2)  => angle opposite longest is >= 90 degrees.
    d12_2 = d12 * d12
    d23_2 = d23 * d23
    d13_2 = d13 * d13
    if realcompare(longest, d12) == "EQ":
        if _ge(d12_2, d23_2 + d13_2):
            return longest * 0.5
    elif realcompare(longest, d23) == "EQ":
        if _ge(d23_2, d12_2 + d13_2):
            return longest * 0.5
    else:
        if _ge(d13_2, d12_2 + d23_2):
            return longest * 0.5

    # Acute triangle: circumradius R = (a*b*c) / (4*Area)
    return (d12 * d23 * d13) / (4.0 * area)


def _quadrant(p: Point) -> int:
    x, y = p
    x_ge_0 = _ge(x, 0.0)
    y_ge_0 = _ge(y, 0.0)

    # Priority rules on axes: I, II, III, IV.
    if x_ge_0 and y_ge_0:
        return 1
    if (not x_ge_0) and y_ge_0:
        return 2
    if (not y_ge_0) and (not x_ge_0 or realcompare(x, 0.0) == "EQ"):
        # x <= 0 and y < 0  (x==0 goes to III, not IV)
        return 3
    return 4


def _lic_1(points: Sequence[Point], length1: float) -> bool:
    for i in range(len(points) - 1):
        if _gt(_distance(points[i], points[i + 1]), length1):
            return True
    return False


def _lic_2(points: Sequence[Point], radius1: float) -> bool:
    for i in range(len(points) - 2):
        if _gt(_required_radius_three_points(points[i], points[i + 1], points[i + 2]), radius1):
            return True
    return False


def _lic_3(points: Sequence[Point], epsilon: float) -> bool:
    lower = PI - epsilon
    upper = PI + epsilon
    for i in range(len(points) - 2):
        ang = _angle_at_vertex(points[i], points[i + 1], points[i + 2])
        if ang is None:
            continue
        if _lt(ang, lower) or _gt(ang, upper):
            return True
    return False


def _lic_4(points: Sequence[Point], area1: float) -> bool:
    for i in range(len(points) - 2):
        if _gt(_triangle_area(points[i], points[i + 1], points[i + 2]), area1):
            return True
    return False


def _lic_5(points: Sequence[Point], q_pts: int, quads: int) -> bool:
    if q_pts <= 0:
        return False
    for i in range(len(points) - q_pts + 1):
        qs = {_quadrant(points[j]) for j in range(i, i + q_pts)}
        if len(qs) > quads:
            return True
    return False


def _lic_6(points: Sequence[Point]) -> bool:
    for i in range(len(points) - 1):
        if _lt(points[i + 1][0] - points[i][0], 0.0):
            return True
    return False


def _lic_7(points: Sequence[Point], dist: float, n_pts: int) -> bool:
    if len(points) < 3:
        return False
    for i in range(len(points) - n_pts + 1):
        first = points[i]
        last = points[i + n_pts - 1]
        if _points_equal(first, last):
            for j in range(i, i + n_pts):
                if _gt(_distance(points[j], first), dist):
                    return True
        else:
            for j in range(i + 1, i + n_pts - 1):
                d = _distance_point_to_line(points[j], first, last)
                if _gt(d, dist):
                    return True
    return False


def _lic_8(points: Sequence[Point], length1: float, k_pts: int) -> bool:
    if len(points) < 3:
        return False
    step = k_pts + 1
    for i in range(len(points) - step):
        if _gt(_distance(points[i], points[i + step]), length1):
            return True
    return False


def _lic_9(points: Sequence[Point], radius1: float, a_pts: int, b_pts: int) -> bool:
    if len(points) < 5:
        return False
    step1 = a_pts + 1
    step2 = b_pts + 1
    span = step1 + step2
    for i in range(len(points) - span):
        p1 = points[i]
        p2 = points[i + step1]
        p3 = points[i + span]
        if _gt(_required_radius_three_points(p1, p2, p3), radius1):
            return True
    return False


def _lic_10(points: Sequence[Point], epsilon: float, c_pts: int, d_pts: int) -> bool:
    if len(points) < 5:
        return False
    step1 = c_pts + 1
    step2 = d_pts + 1
    span = step1 + step2
    lower = PI - epsilon
    upper = PI + epsilon
    for i in range(len(points) - span):
        p1 = points[i]
        vertex = points[i + step1]
        p3 = points[i + span]
        ang = _angle_at_vertex(p1, vertex, p3)
        if ang is None:
            continue
        if _lt(ang, lower) or _gt(ang, upper):
            return True
    return False


def _lic_11(points: Sequence[Point], area1: float, e_pts: int, f_pts: int) -> bool:
    if len(points) < 5:
        return False
    step1 = e_pts + 1
    step2 = f_pts + 1
    span = step1 + step2
    for i in range(len(points) - span):
        p1 = points[i]
        p2 = points[i + step1]
        p3 = points[i + span]
        if _gt(_triangle_area(p1, p2, p3), area1):
            return True
    return False


def _lic_12(points: Sequence[Point], g_pts: int) -> bool:
    if len(points) < 3:
        return False
    step = g_pts + 1
    for i in range(len(points) - step):
        if _lt(points[i + step][0] - points[i][0], 0.0):
            return True
    return False


def _lic_13(points: Sequence[Point], length1: float, length2: float, k_pts: int) -> bool:
    if len(points) < 3:
        return False
    step = k_pts + 1
    exists_gt = False
    exists_lt = False
    for i in range(len(points) - step):
        d = _distance(points[i], points[i + step])
        if _gt(d, length1):
            exists_gt = True
        if _lt(d, length2):
            exists_lt = True
        if exists_gt and exists_lt:
            return True
    return False


def _lic_14(points: Sequence[Point], radius1: float, radius2: float, a_pts: int, b_pts: int) -> bool:
    if len(points) < 5:
        return False
    step1 = a_pts + 1
    step2 = b_pts + 1
    span = step1 + step2
    exists_gt = False
    exists_le = False
    for i in range(len(points) - span):
        p1 = points[i]
        p2 = points[i + step1]
        p3 = points[i + span]
        r = _required_radius_three_points(p1, p2, p3)
        if _gt(r, radius1):
            exists_gt = True
        if _le(r, radius2):
            exists_le = True
        if exists_gt and exists_le:
            return True
    return False


def _lic_15(points: Sequence[Point], area1: float, area2: float, e_pts: int, f_pts: int) -> bool:
    if len(points) < 5:
        return False
    step1 = e_pts + 1
    step2 = f_pts + 1
    span = step1 + step2
    exists_gt = False
    exists_lt = False
    for i in range(len(points) - span):
        p1 = points[i]
        p2 = points[i + step1]
        p3 = points[i + span]
        a = _triangle_area(p1, p2, p3)
        if _gt(a, area1):
            exists_gt = True
        if _lt(a, area2):
            exists_lt = True
        if exists_gt and exists_lt:
            return True
    return False


def decide(
    numpoints: int,
    x: Sequence[float],
    y: Sequence[float],
    parameters: Dict[str, Any],
    lcm: Sequence[Sequence[str]],
    pum_diag: Sequence[bool],
) -> Tuple[List[bool], List[List[bool]], List[bool], bool]:
    """
    Compute (CMV, PUM, FUV, LAUNCH) per the specification.

    Returns JSON-serializable Python structures:
      - cmv: length-15 list[bool]
      - pum: 15x15 list[list[bool]]
      - fuv: length-15 list[bool]
      - launch: bool
    """
    points: List[Point] = [(float(x[i]), float(y[i])) for i in range(numpoints)]

    length1 = float(parameters["LENGTH1"])
    radius1 = float(parameters["RADIUS1"])
    epsilon = float(parameters["EPSILON"])
    area1 = float(parameters["AREA1"])
    q_pts = int(parameters["Q_PTS"])
    quads = int(parameters["QUADS"])
    dist = float(parameters["DIST"])
    n_pts = int(parameters["N_PTS"])
    k_pts = int(parameters["K_PTS"])
    a_pts = int(parameters["A_PTS"])
    b_pts = int(parameters["B_PTS"])
    c_pts = int(parameters["C_PTS"])
    d_pts = int(parameters["D_PTS"])
    e_pts = int(parameters["E_PTS"])
    f_pts = int(parameters["F_PTS"])
    g_pts = int(parameters["G_PTS"])
    length2 = float(parameters["LENGTH2"])
    radius2 = float(parameters["RADIUS2"])
    area2 = float(parameters["AREA2"])

    cmv = [False] * 15
    cmv[0] = _lic_1(points, length1)
    cmv[1] = _lic_2(points, radius1)
    cmv[2] = _lic_3(points, epsilon)
    cmv[3] = _lic_4(points, area1)
    cmv[4] = _lic_5(points, q_pts, quads)
    cmv[5] = _lic_6(points)
    cmv[6] = _lic_7(points, dist, n_pts)
    cmv[7] = _lic_8(points, length1, k_pts)
    cmv[8] = _lic_9(points, radius1, a_pts, b_pts)
    cmv[9] = _lic_10(points, epsilon, c_pts, d_pts)
    cmv[10] = _lic_11(points, area1, e_pts, f_pts)
    cmv[11] = _lic_12(points, g_pts)
    cmv[12] = _lic_13(points, length1, length2, k_pts)
    cmv[13] = _lic_14(points, radius1, radius2, a_pts, b_pts)
    cmv[14] = _lic_15(points, area1, area2, e_pts, f_pts)

    pum: List[List[bool]] = [[False for _ in range(15)] for _ in range(15)]
    for i in range(15):
        pum[i][i] = bool(pum_diag[i])
    for i in range(15):
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
            else:
                # Per spec, inputs are valid; keep a conservative default.
                pum[i][j] = False

    fuv: List[bool] = [False] * 15
    for i in range(15):
        if pum[i][i] is False:
            fuv[i] = True
        else:
            fuv[i] = all(pum[i][j] for j in range(15))

    launch = all(fuv)
    return cmv, pum, fuv, launch


def _main() -> None:
    raw = sys.stdin.read()
    inp = json.loads(raw)
    cmv, pum, fuv, launch = decide(
        numpoints=int(inp["numpoints"]),
        x=inp["x"],
        y=inp["y"],
        parameters=inp["parameters"],
        lcm=inp["lcm"],
        pum_diag=inp["pum_diag"],
    )
    out = {"cmv": cmv, "pum": pum, "fuv": fuv, "launch": launch}
    sys.stdout.write(json.dumps(out))


if __name__ == "__main__":
    _main()


# ---------------------------------------------------------------------------
# Primary source snapshot (verbatim) for archival.
# ---------------------------------------------------------------------------

PRIMARY_SOURCE_SNAPSHOT: Dict[str, str] = {
    "spec.md": r"""# Launch Interceptor Program Specification

## Functional Requirements

All communication with software which calls your procedure is to be accomplished through the global variables and constant defined in this section.

### Constant

The value of the global constant `PI` is available to your procedure, representing the number of radians in 180 degrees.

### Input Variables

The values of the following global variables are available to your procedure:

| Variable                   | Description                                  |
| -------------------------- | -------------------------------------------- |
| `X`, `Y`                  | Parallel arrays containing the coordinates of data points |
| `NUMPOINTS`               | The number of planar data points             |
| `PARAMETERS`              | Record holding parameters for LICs           |
| `LCM`                     | Logical Connector Matrix                     |
| `PUM` (diagonal elements) | Preliminary Unlocking Matrix                 |

### Output Variables

The values of the following global variables are to be set by your procedure:

| Variable                       | Description                    |
| ------------------------------ | ------------------------------ |
| `PUM` (off-diagonal elements)  | Preliminary Unlocking Matrix   |
| `CMV`                          | Conditions Met Vector          |
| `FUV`                          | Final Unlocking Vector         |
| `LAUNCH`                       | Final launch/no launch decision |

### Global Declarations

The global declarations have been made as follows:

```pascal
const
  PI = 3.1415926535;

type
  POINTRANGE  = 1..100;
  LICRANGE    = 1..15;
  NPOINTS     = 2..100;
  NPTYPE      = 3..100;
  CONNECTORS  = (NOTUSED, ORR, ANDD);
  NUMQUADS    = 1..3;
  COORDINATE  = array[POINTRANGE] of real;
  CMATRIX     = array[LICRANGE, LICRANGE] of CONNECTORS;
  BMATRIX     = array[LICRANGE, LICRANGE] of boolean;
  VECTOR      = array[LICRANGE] of boolean;
  COMPTYPE    = (LT, EQ, GT);

var
  X          : COORDINATE;  {X coordinates of data points}
  Y          : COORDINATE;  {Y coordinates of data points}
  NUMPOINTS  : NPOINTS;     {Number of data points}
  PARAMETERS : record
    LENGTH1  : real;         {Length in LICs 1, 8, 13}
    RADIUS1  : real;         {Radius in LICs 2, 9, 14}
    EPSILON  : real;         {Deviation from PI in LICs 3, 10}
    AREA1    : real;         {Area in LICs 4, 11, 15}
    Q_PTS    : NPOINTS;      {No. of consecutive points in LIC 5}
    QUADS    : NUMQUADS;     {No. of quadrants in LIC 5}
    DIST     : real;         {Distance in LIC 7}
    N_PTS    : NPTYPE;       {No. of consecutive pts. in LIC 7}
    K_PTS    : POINTRANGE;   {No. of int. pts. in LICs 8, 13}
    A_PTS    : POINTRANGE;   {No. of int. pts. in LICs 9, 14}
    B_PTS    : POINTRANGE;   {No. of int. pts. in LICs 9, 14}
    C_PTS    : POINTRANGE;   {No. of int. pts. in LIC 10}
    D_PTS    : POINTRANGE;   {No. of int. pts. in LIC 10}
    E_PTS    : POINTRANGE;   {No. of int. pts. in LICs 11, 15}
    F_PTS    : POINTRANGE;   {No. of int. pts. in LICs 11, 15}
    G_PTS    : POINTRANGE;   {No. of int. pts. in LIC 12}
    LENGTH2  : real;         {Maximum length in LIC 13}
    RADIUS2  : real;         {Maximum radius in LIC 14}
    AREA2    : real;         {Maximum area in LIC 15}
  end;
  LCM     : CMATRIX;     {Logical Connector Matrix}
  PUM     : BMATRIX;     {Preliminary Unlocking Matrix}
  CMV     : VECTOR;      {Conditions Met Vector}
  FUV     : VECTOR;      {Final Unlocking Vector}
  LAUNCH  : boolean;     {Decision: Launch or No Launch}

function REALCOMPARE(A, B : real) : COMPTYPE;
  {compares real numbers - see Nonfunctional Requirements}
```

### Required Computations

It can be assumed that all input data and parameters that are measured in some form of units use the same, consistent units. For example, all lengths are measured in the same units that are used to define the planar space from which the input data comes. Therefore, no unit conversion is necessary.

Given the parameter values in the global record `PARAMETERS`, the procedure `DECIDE` must evaluate each of the Launch Interceptor Conditions (LICs) described below for the set of `NUMPOINTS` points:

```
(X[1], Y[1]), ..., (X[NUMPOINTS], Y[NUMPOINTS])
```

where 2 <= `NUMPOINTS` <= 100.

The Conditions Met Vector (CMV) should be set according to the results of these calculations, i.e., the global array element `CMV[i]` should be set to true if and only if the i-th LIC is met.

#### Launch Interceptor Conditions (LICs)

**LIC 1:** There exists at least one set of two consecutive data points that are a distance greater than the length, `LENGTH1`, apart.

> Constraints: (0 <= LENGTH1)

**LIC 2:** There exists at least one set of three consecutive data points that cannot all be contained within or on a circle of radius `RADIUS1`.

> Constraints: (0 <= RADIUS1)

**LIC 3:** There exists at least one set of three consecutive data points which form an angle such that:

- angle < (PI - EPSILON), or
- angle > (PI + EPSILON)

The second of the three consecutive points is always the vertex of the angle. If either the first point or the last point (or both) coincides with the vertex, the angle is undefined and the LIC is not satisfied by those three points.

> Constraints: (0 <= EPSILON < PI)

**LIC 4:** There exists at least one set of three consecutive data points that are the vertices of a triangle with area greater than `AREA1`.

> Constraints: (0 <= AREA1)

**LIC 5:** There exists at least one set of `Q_PTS` consecutive data points that lie in more than `QUADS` quadrants. Where there is ambiguity as to which quadrant contains a given point, priority of decision will be by quadrant number, i.e., I, II, III, IV. For example, the data point (0,0) is in quadrant I, the point (-1,0) is in quadrant II, the point (0,-1) is in quadrant III, the point (0,1) is in quadrant I, and the point (1,0) is in quadrant I.

> Constraints: (2 <= Q_PTS <= NUMPOINTS), (1 <= QUADS <= 3)

**LIC 6:** There exists at least one set of two consecutive data points, (X[i], Y[i]) and (X[j], Y[j]), such that X[j] - X[i] < 0 (where i = j - 1).

**LIC 7:** There exists at least one set of `N_PTS` consecutive data points such that at least one of the points lies a distance greater than `DIST` from the line joining the first and last of these `N_PTS` points. If the first and last points of these `N_PTS` are identical, then the calculated distance to compare with `DIST` will be the distance from the coincident point to all other points of the `N_PTS` consecutive points. The condition is not met when NUMPOINTS < 3.

> Constraints: (3 <= N_PTS <= NUMPOINTS), (0 <= DIST)

**LIC 8:** There exists at least one set of two data points separated by exactly `K_PTS` consecutive intervening points that are a distance greater than the length, `LENGTH1`, apart. The condition is not met when NUMPOINTS < 3.

> Constraints: (1 <= K_PTS <= NUMPOINTS - 2)

**LIC 9:** There exists at least one set of three data points separated by exactly `A_PTS` and `B_PTS` consecutive intervening points, respectively, that cannot be contained within or on a circle of radius `RADIUS1`. The condition is not met when NUMPOINTS < 5.

> Constraints: (1 <= A_PTS), (1 <= B_PTS), A_PTS + B_PTS <= NUMPOINTS - 3

**LIC 10:** There exists at least one set of three data points separated by exactly `C_PTS` and `D_PTS` consecutive intervening points, respectively, that form an angle such that:

- angle < (PI - EPSILON), or
- angle > (PI + EPSILON)

The second point of the set of three points is always the vertex of the angle. If either the first point or the last point (or both) coincide with the vertex, the angle is undefined and the LIC is not satisfied by those three points. The condition is not met when NUMPOINTS < 5.

> Constraints: (1 <= C_PTS), (1 <= D_PTS), C_PTS + D_PTS <= NUMPOINTS - 3

**LIC 11:** There exists at least one set of three data points separated by exactly `E_PTS` and `F_PTS` consecutive intervening points, respectively, that are the vertices of a triangle with area greater than `AREA1`. The condition is not met when NUMPOINTS < 5.

> Constraints: (1 <= E_PTS), (1 <= F_PTS), E_PTS + F_PTS <= NUMPOINTS - 3

**LIC 12:** There exists at least one set of two data points, (X[i], Y[i]) and (X[j], Y[j]), separated by exactly `G_PTS` consecutive intervening points, such that X[j] - X[i] < 0 (where i < j). The condition is not met when NUMPOINTS < 3.

> Constraints: (1 <= G_PTS <= NUMPOINTS - 2)

**LIC 13:** There exists at least one set of two data points, separated by exactly `K_PTS` consecutive intervening points, which are a distance greater than the length, `LENGTH1`, apart. In addition, there exists at least one set of two data points (which can be the same or different from the two data points just mentioned), separated by exactly `K_PTS` consecutive intervening points, that are a distance less than the length, `LENGTH2`, apart. Both parts must be true for the LIC to be true. The condition is not met when NUMPOINTS < 3.

> Constraints: (0 <= LENGTH2)

**LIC 14:** There exists at least one set of three data points, separated by exactly `A_PTS` and `B_PTS` consecutive intervening points, respectively, that cannot be contained within or on a circle of radius `RADIUS1`. In addition, there exists at least one set of three data points (which can be the same or different from the three data points just mentioned) separated by exactly `A_PTS` and `B_PTS` consecutive intervening points, respectively, that can be contained in or on a circle of radius `RADIUS2`. Both parts must be true for the LIC to be true. The condition is not met when NUMPOINTS < 5.

> Constraints: (0 <= RADIUS2)

**LIC 15:** There exists at least one set of three data points, separated by exactly `E_PTS` and `F_PTS` consecutive intervening points, respectively, that are the vertices of a triangle with area greater than `AREA1`. In addition, there exist three data points (which can be the same or different from the three data points just mentioned) separated by exactly `E_PTS` and `F_PTS` consecutive intervening points, respectively, that are the vertices of a triangle with area less than `AREA2`. Both parts must be true for the LIC to be true. The condition is not met when NUMPOINTS < 5.

> Constraints: (0 <= AREA2)

#### Combining LICs: The Preliminary Unlocking Matrix (PUM)

The Conditions Met Vector (CMV) can now be used in conjunction with the Logical Connector Matrix (LCM) to form the off-diagonal elements of the Preliminary Unlocking Matrix (PUM). The entries in the LCM represent the logical connectors to be used between pairs of LICs to determine the corresponding entry in the PUM, i.e., `LCM[i, j]` represents the Boolean operator to be applied to `CMV[i]` and `CMV[j]`. `PUM[i, j]` is set according to the result of this operation:

- If `LCM[i, j]` is **NOTUSED**, then `PUM[i, j]` should be set to **true**.
- If `LCM[i, j]` is **ANDD**, `PUM[i, j]` should be set to true only if (`CMV[i]` AND `CMV[j]`) is true.
- If `LCM[i, j]` is **ORR**, `PUM[i, j]` should be set to true if (`CMV[i]` OR `CMV[j]`) is true.

Note that the LCM is symmetric, i.e., `LCM[i, j]` = `LCM[j, i]` for all i and j.

#### Final Unlocking Vector (FUV)

The Final Unlocking Vector (FUV) is generated from the Preliminary Unlocking Matrix. The input diagonal elements of the PUM indicate whether the corresponding LIC is to be considered as a factor in signaling interceptor launch. `FUV[i]` should be set to true if `PUM[i, i]` is false (indicating that the associated LIC should not hold back launch) or if all elements in PUM row i are true.

#### Launch Decision

The final launch/no launch decision is based on the FUV. The decision to launch requires that all elements in the FUV be true, i.e., `LAUNCH` should be set to true if and only if `FUV[i]` is true for all i, 1 <= i <= 15.

## Nonfunctional Requirements

2. Whenever real numbers must be compared within the procedure `DECIDE`, that comparison should be made with a fixed amount of precision. The program which calls `DECIDE` will provide a function called `REALCOMPARE`. This function compares two real numbers, A and B, with respect to the six most significant digits. `REALCOMPARE` returns `LT` if A < B, `EQ` if A = B, or `GT` if A > B. `DECIDE` should call this function for all comparisons of real numbers.
""",
    "realcompare_reference.py": r"""def realcompare(a: float, b: float) -> str:
    \\"\\"\\"Tolerance-based six-significant-digit comparison from the oracle.\\"\\"\\"
    scale = max(abs(a), abs(b))
    if scale == 0.0:
        return \\"EQ\\"
    eps = 0.5e-5 * scale
    diff = a - b
    if diff > eps:
        return \\"GT\\"
    if diff < -eps:
        return \\"LT\\"
    return \\"EQ\\"
""",
}

# Hashes of the provided primary source files in the workspace at build time.
# These allow later verification that the embedded snapshot text corresponds to
# the exact inputs used for this deliverable.
PRIMARY_SOURCE_SNAPSHOT_SHA256: Dict[str, str] = {
    "spec.md": "67f076d1d3d5d0d2e380510c003c6707dee3a5e4da27f97ad56c09c12db5c964",
    "realcompare_reference.py": "560b8203287d3c8a066d1b70bf3b45ab3e78b0a7423fac3640faf391208fef05",
}
