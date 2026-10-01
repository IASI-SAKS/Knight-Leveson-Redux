#!/usr/bin/env python3
"""
Launch Interceptor Program - Implementation of DECIDE procedure
Based on Knight & Leveson (1986) specification.
"""

import json
import math
import sys
from typing import List, Tuple

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


def distance(x1: float, y1: float, x2: float, y2: float) -> float:
    """Calculate Euclidean distance between two points."""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def triangle_area(x1: float, y1: float, x2: float, y2: float, x3: float, y3: float) -> float:
    """Calculate area of triangle using cross product formula."""
    return abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)) / 2.0


def angle_at_vertex(x1: float, y1: float, vx: float, vy: float, x3: float, y3: float) -> float:
    """
    Calculate angle at vertex (vx, vy) formed by points (x1, y1), (vx, vy), (x3, y3).
    Returns angle in radians, or -1 if undefined (coincident points).
    """
    # Vectors from vertex to first and third points
    v1x = x1 - vx
    v1y = y1 - vy
    v3x = x3 - vx
    v3y = y3 - vy

    len1 = math.sqrt(v1x * v1x + v1y * v1y)
    len3 = math.sqrt(v3x * v3x + v3y * v3y)

    # If either point coincides with vertex, angle is undefined
    if realcompare(len1, 0.0) == "EQ" or realcompare(len3, 0.0) == "EQ":
        return -1.0

    # Dot product
    dot = v1x * v3x + v1y * v3y
    cos_angle = dot / (len1 * len3)

    # Clamp to [-1, 1] to handle floating point errors
    if cos_angle > 1.0:
        cos_angle = 1.0
    if cos_angle < -1.0:
        cos_angle = -1.0

    return math.acos(cos_angle)


def circumradius(x1: float, y1: float, x2: float, y2: float, x3: float, y3: float) -> float:
    """
    Calculate the circumradius of triangle formed by three points.
    Returns the radius of the smallest circle containing all three points.
    For collinear points, returns half the maximum distance between any two points.
    """
    # Check for coincident points
    d12 = distance(x1, y1, x2, y2)
    d23 = distance(x2, y2, x3, y3)
    d13 = distance(x1, y1, x3, y3)

    area = triangle_area(x1, y1, x2, y2, x3, y3)

    # If area is zero (collinear or coincident points),
    # the minimum enclosing circle has diameter = max distance between points
    if realcompare(area, 0.0) == "EQ":
        return max(d12, d23, d13) / 2.0

    # Circumradius formula: R = (a * b * c) / (4 * Area)
    return (d12 * d23 * d13) / (4.0 * area)


def min_enclosing_circle_radius(x1: float, y1: float, x2: float, y2: float, x3: float, y3: float) -> float:
    """
    Calculate the radius of the minimum enclosing circle for three points.
    This could be the circumcircle (if acute triangle) or half the longest side (if obtuse/right).
    """
    d12 = distance(x1, y1, x2, y2)
    d23 = distance(x2, y2, x3, y3)
    d13 = distance(x1, y1, x3, y3)

    area = triangle_area(x1, y1, x2, y2, x3, y3)

    # Collinear or coincident points
    if realcompare(area, 0.0) == "EQ":
        return max(d12, d23, d13) / 2.0

    # Check if triangle is obtuse or right-angled
    # The minimum enclosing circle for an obtuse triangle has diameter = longest side
    sides = [(d12, d23, d13), (d23, d12, d13), (d13, d12, d23)]

    for longest, a, b in sides:
        if realcompare(longest * longest, a * a + b * b) != "LT":
            # Obtuse or right triangle - diameter is longest side
            return longest / 2.0

    # Acute triangle - use circumradius
    return (d12 * d23 * d13) / (4.0 * area)


def point_to_line_distance(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
    """
    Calculate perpendicular distance from point (px, py) to line defined by (x1, y1) and (x2, y2).
    """
    line_len = distance(x1, y1, x2, y2)
    if realcompare(line_len, 0.0) == "EQ":
        # Line degenerates to a point
        return distance(px, py, x1, y1)

    # Using cross product formula for area
    area = abs((x2 - x1) * (py - y1) - (px - x1) * (y2 - y1))
    return area / line_len


def get_quadrant(x: float, y: float) -> int:
    """
    Determine quadrant of point with priority I, II, III, IV.
    Quadrant I: x >= 0, y >= 0
    Quadrant II: x < 0, y >= 0
    Quadrant III: x < 0, y < 0
    Quadrant IV: x >= 0, y < 0
    """
    if x >= 0 and y >= 0:
        return 1
    elif x < 0 and y >= 0:
        return 2
    elif x < 0 and y < 0:
        return 3
    else:  # x >= 0 and y < 0
        return 4


# ============== LIC Implementations ==============

def lic_1(numpoints: int, x: List[float], y: List[float], length1: float) -> bool:
    """
    LIC 1: There exists at least one set of two consecutive data points
    that are a distance greater than LENGTH1 apart.
    """
    for i in range(numpoints - 1):
        d = distance(x[i], y[i], x[i + 1], y[i + 1])
        if realcompare(d, length1) == "GT":
            return True
    return False


def lic_2(numpoints: int, x: List[float], y: List[float], radius1: float) -> bool:
    """
    LIC 2: There exists at least one set of three consecutive data points
    that cannot all be contained within or on a circle of radius RADIUS1.
    """
    for i in range(numpoints - 2):
        r = min_enclosing_circle_radius(x[i], y[i], x[i + 1], y[i + 1], x[i + 2], y[i + 2])
        if realcompare(r, radius1) == "GT":
            return True
    return False


def lic_3(numpoints: int, x: List[float], y: List[float], epsilon: float) -> bool:
    """
    LIC 3: There exists at least one set of three consecutive data points
    which form an angle such that angle < (PI - EPSILON) or angle > (PI + EPSILON).
    """
    for i in range(numpoints - 2):
        angle = angle_at_vertex(x[i], y[i], x[i + 1], y[i + 1], x[i + 2], y[i + 2])
        if angle < 0:
            # Undefined angle (coincident points)
            continue
        if realcompare(angle, PI - epsilon) == "LT" or realcompare(angle, PI + epsilon) == "GT":
            return True
    return False


def lic_4(numpoints: int, x: List[float], y: List[float], area1: float) -> bool:
    """
    LIC 4: There exists at least one set of three consecutive data points
    that are the vertices of a triangle with area greater than AREA1.
    """
    for i in range(numpoints - 2):
        area = triangle_area(x[i], y[i], x[i + 1], y[i + 1], x[i + 2], y[i + 2])
        if realcompare(area, area1) == "GT":
            return True
    return False


def lic_5(numpoints: int, x: List[float], y: List[float], q_pts: int, quads: int) -> bool:
    """
    LIC 5: There exists at least one set of Q_PTS consecutive data points
    that lie in more than QUADS quadrants.
    """
    for i in range(numpoints - q_pts + 1):
        quadrants_used = set()
        for j in range(i, i + q_pts):
            quadrants_used.add(get_quadrant(x[j], y[j]))
        if len(quadrants_used) > quads:
            return True
    return False


def lic_6(numpoints: int, x: List[float], y: List[float]) -> bool:
    """
    LIC 6: There exists at least one set of two consecutive data points,
    (X[i], Y[i]) and (X[j], Y[j]), such that X[j] - X[i] < 0 (where i = j - 1).
    """
    for i in range(numpoints - 1):
        if realcompare(x[i + 1] - x[i], 0.0) == "LT":
            return True
    return False


def lic_7(numpoints: int, x: List[float], y: List[float], n_pts: int, dist: float) -> bool:
    """
    LIC 7: There exists at least one set of N_PTS consecutive data points such that
    at least one of the points lies a distance greater than DIST from the line joining
    the first and last of these N_PTS points.
    Condition is not met when NUMPOINTS < 3.
    """
    if numpoints < 3:
        return False

    for i in range(numpoints - n_pts + 1):
        first_idx = i
        last_idx = i + n_pts - 1

        x_first, y_first = x[first_idx], y[first_idx]
        x_last, y_last = x[last_idx], y[last_idx]

        # Check all intermediate points
        for j in range(first_idx + 1, last_idx):
            if realcompare(distance(x_first, y_first, x_last, y_last), 0.0) == "EQ":
                # First and last are coincident - use distance to coincident point
                d = distance(x[j], y[j], x_first, y_first)
            else:
                d = point_to_line_distance(x[j], y[j], x_first, y_first, x_last, y_last)

            if realcompare(d, dist) == "GT":
                return True

    return False


def lic_8(numpoints: int, x: List[float], y: List[float], k_pts: int, length1: float) -> bool:
    """
    LIC 8: There exists at least one set of two data points separated by exactly K_PTS
    consecutive intervening points that are a distance greater than LENGTH1 apart.
    Condition is not met when NUMPOINTS < 3.
    """
    if numpoints < 3:
        return False

    for i in range(numpoints - k_pts - 1):
        j = i + k_pts + 1
        d = distance(x[i], y[i], x[j], y[j])
        if realcompare(d, length1) == "GT":
            return True
    return False


def lic_9(numpoints: int, x: List[float], y: List[float], a_pts: int, b_pts: int, radius1: float) -> bool:
    """
    LIC 9: There exists at least one set of three data points separated by exactly A_PTS
    and B_PTS consecutive intervening points that cannot be contained within or on a
    circle of radius RADIUS1.
    Condition is not met when NUMPOINTS < 5.
    """
    if numpoints < 5:
        return False

    for i in range(numpoints - a_pts - b_pts - 2):
        j = i + a_pts + 1
        k = j + b_pts + 1
        r = min_enclosing_circle_radius(x[i], y[i], x[j], y[j], x[k], y[k])
        if realcompare(r, radius1) == "GT":
            return True
    return False


def lic_10(numpoints: int, x: List[float], y: List[float], c_pts: int, d_pts: int, epsilon: float) -> bool:
    """
    LIC 10: There exists at least one set of three data points separated by exactly C_PTS
    and D_PTS consecutive intervening points that form an angle such that
    angle < (PI - EPSILON) or angle > (PI + EPSILON).
    Condition is not met when NUMPOINTS < 5.
    """
    if numpoints < 5:
        return False

    for i in range(numpoints - c_pts - d_pts - 2):
        j = i + c_pts + 1
        k = j + d_pts + 1
        angle = angle_at_vertex(x[i], y[i], x[j], y[j], x[k], y[k])
        if angle < 0:
            continue
        if realcompare(angle, PI - epsilon) == "LT" or realcompare(angle, PI + epsilon) == "GT":
            return True
    return False


def lic_11(numpoints: int, x: List[float], y: List[float], e_pts: int, f_pts: int, area1: float) -> bool:
    """
    LIC 11: There exists at least one set of three data points separated by exactly E_PTS
    and F_PTS consecutive intervening points that are the vertices of a triangle with
    area greater than AREA1.
    Condition is not met when NUMPOINTS < 5.
    """
    if numpoints < 5:
        return False

    for i in range(numpoints - e_pts - f_pts - 2):
        j = i + e_pts + 1
        k = j + f_pts + 1
        area = triangle_area(x[i], y[i], x[j], y[j], x[k], y[k])
        if realcompare(area, area1) == "GT":
            return True
    return False


def lic_12(numpoints: int, x: List[float], y: List[float], g_pts: int) -> bool:
    """
    LIC 12: There exists at least one set of two data points separated by exactly G_PTS
    consecutive intervening points such that X[j] - X[i] < 0 (where i < j).
    Condition is not met when NUMPOINTS < 3.
    """
    if numpoints < 3:
        return False

    for i in range(numpoints - g_pts - 1):
        j = i + g_pts + 1
        if realcompare(x[j] - x[i], 0.0) == "LT":
            return True
    return False


def lic_13(numpoints: int, x: List[float], y: List[float], k_pts: int, length1: float, length2: float) -> bool:
    """
    LIC 13: Both conditions must be true:
    1. Exists two points separated by K_PTS with distance > LENGTH1
    2. Exists two points separated by K_PTS with distance < LENGTH2
    Condition is not met when NUMPOINTS < 3.
    """
    if numpoints < 3:
        return False

    cond1 = False
    cond2 = False

    for i in range(numpoints - k_pts - 1):
        j = i + k_pts + 1
        d = distance(x[i], y[i], x[j], y[j])
        if realcompare(d, length1) == "GT":
            cond1 = True
        if realcompare(d, length2) == "LT":
            cond2 = True
        if cond1 and cond2:
            return True

    return cond1 and cond2


def lic_14(numpoints: int, x: List[float], y: List[float], a_pts: int, b_pts: int,
           radius1: float, radius2: float) -> bool:
    """
    LIC 14: Both conditions must be true:
    1. Exists three points separated by A_PTS and B_PTS that cannot be contained in
       circle of radius RADIUS1
    2. Exists three points separated by A_PTS and B_PTS that can be contained in
       circle of radius RADIUS2
    Condition is not met when NUMPOINTS < 5.
    """
    if numpoints < 5:
        return False

    cond1 = False
    cond2 = False

    for i in range(numpoints - a_pts - b_pts - 2):
        j = i + a_pts + 1
        k = j + b_pts + 1
        r = min_enclosing_circle_radius(x[i], y[i], x[j], y[j], x[k], y[k])
        if realcompare(r, radius1) == "GT":
            cond1 = True
        if realcompare(r, radius2) != "GT":
            cond2 = True
        if cond1 and cond2:
            return True

    return cond1 and cond2


def lic_15(numpoints: int, x: List[float], y: List[float], e_pts: int, f_pts: int,
           area1: float, area2: float) -> bool:
    """
    LIC 15: Both conditions must be true:
    1. Exists three points separated by E_PTS and F_PTS with triangle area > AREA1
    2. Exists three points separated by E_PTS and F_PTS with triangle area < AREA2
    Condition is not met when NUMPOINTS < 5.
    """
    if numpoints < 5:
        return False

    cond1 = False
    cond2 = False

    for i in range(numpoints - e_pts - f_pts - 2):
        j = i + e_pts + 1
        k = j + f_pts + 1
        area = triangle_area(x[i], y[i], x[j], y[j], x[k], y[k])
        if realcompare(area, area1) == "GT":
            cond1 = True
        if realcompare(area, area2) == "LT":
            cond2 = True
        if cond1 and cond2:
            return True

    return cond1 and cond2


def compute_cmv(numpoints: int, x: List[float], y: List[float], parameters: dict) -> List[bool]:
    """Compute the Conditions Met Vector (CMV) for all 15 LICs."""
    cmv = [False] * 15

    cmv[0] = lic_1(numpoints, x, y, parameters["LENGTH1"])
    cmv[1] = lic_2(numpoints, x, y, parameters["RADIUS1"])
    cmv[2] = lic_3(numpoints, x, y, parameters["EPSILON"])
    cmv[3] = lic_4(numpoints, x, y, parameters["AREA1"])
    cmv[4] = lic_5(numpoints, x, y, parameters["Q_PTS"], parameters["QUADS"])
    cmv[5] = lic_6(numpoints, x, y)
    cmv[6] = lic_7(numpoints, x, y, parameters["N_PTS"], parameters["DIST"])
    cmv[7] = lic_8(numpoints, x, y, parameters["K_PTS"], parameters["LENGTH1"])
    cmv[8] = lic_9(numpoints, x, y, parameters["A_PTS"], parameters["B_PTS"], parameters["RADIUS1"])
    cmv[9] = lic_10(numpoints, x, y, parameters["C_PTS"], parameters["D_PTS"], parameters["EPSILON"])
    cmv[10] = lic_11(numpoints, x, y, parameters["E_PTS"], parameters["F_PTS"], parameters["AREA1"])
    cmv[11] = lic_12(numpoints, x, y, parameters["G_PTS"])
    cmv[12] = lic_13(numpoints, x, y, parameters["K_PTS"], parameters["LENGTH1"], parameters["LENGTH2"])
    cmv[13] = lic_14(numpoints, x, y, parameters["A_PTS"], parameters["B_PTS"],
                     parameters["RADIUS1"], parameters["RADIUS2"])
    cmv[14] = lic_15(numpoints, x, y, parameters["E_PTS"], parameters["F_PTS"],
                     parameters["AREA1"], parameters["AREA2"])

    return cmv


def compute_pum(cmv: List[bool], lcm: List[List[str]], pum_diag: List[bool]) -> List[List[bool]]:
    """
    Compute the Preliminary Unlocking Matrix (PUM) from CMV and LCM.
    Diagonal elements come from pum_diag input.
    Off-diagonal elements are computed from CMV and LCM.
    """
    pum = [[False] * 15 for _ in range(15)]

    for i in range(15):
        for j in range(15):
            if i == j:
                pum[i][j] = pum_diag[i]
            else:
                connector = lcm[i][j]
                if connector == "NOTUSED":
                    pum[i][j] = True
                elif connector == "ANDD":
                    pum[i][j] = cmv[i] and cmv[j]
                elif connector == "ORR":
                    pum[i][j] = cmv[i] or cmv[j]

    return pum


def compute_fuv(pum: List[List[bool]]) -> List[bool]:
    """
    Compute the Final Unlocking Vector (FUV) from PUM.
    FUV[i] is true if PUM[i,i] is false OR all elements in PUM row i are true.
    """
    fuv = [False] * 15

    for i in range(15):
        if not pum[i][i]:
            fuv[i] = True
        else:
            fuv[i] = all(pum[i][j] for j in range(15))

    return fuv


def compute_launch(fuv: List[bool]) -> bool:
    """
    Compute the final launch decision.
    Launch if all elements of FUV are true.
    """
    return all(fuv)


def decide(numpoints: int, x: List[float], y: List[float], parameters: dict,
           lcm: List[List[str]], pum_diag: List[bool]) -> Tuple[List[bool], List[List[bool]], List[bool], bool]:
    """
    Main DECIDE procedure.
    Returns (cmv, pum, fuv, launch).
    """
    cmv = compute_cmv(numpoints, x, y, parameters)
    pum = compute_pum(cmv, lcm, pum_diag)
    fuv = compute_fuv(pum)
    launch = compute_launch(fuv)

    return cmv, pum, fuv, launch


def main():
    """Read JSON input from stdin, compute decision, write JSON output to stdout."""
    input_data = json.load(sys.stdin)

    numpoints = input_data["numpoints"]
    x = input_data["x"]
    y = input_data["y"]
    parameters = input_data["parameters"]
    lcm = input_data["lcm"]
    pum_diag = input_data["pum_diag"]

    cmv, pum, fuv, launch = decide(numpoints, x, y, parameters, lcm, pum_diag)

    output = {
        "cmv": cmv,
        "pum": pum,
        "fuv": fuv,
        "launch": launch
    }

    json.dump(output, sys.stdout)


if __name__ == "__main__":
    main()
