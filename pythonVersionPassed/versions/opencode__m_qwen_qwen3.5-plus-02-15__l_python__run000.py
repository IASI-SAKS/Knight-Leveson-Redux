#!/usr/bin/env python3
"""
Launch Interceptor Program - Implementation of Knight & Leveson (1986)
This module implements the DECIDE procedure as specified.
"""

import json
import sys
import math
from typing import List, Dict, Any, Tuple

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


def get_quadrant(x: float, y: float) -> int:
    """
    Determine which quadrant a point is in.
    Priority by quadrant number for axis points: I, II, III, IV
    """
    if x >= 0 and y >= 0:
        return 1
    elif x < 0 and y >= 0:
        return 2
    elif x < 0 and y < 0:
        return 3
    else:
        return 4


def triangle_area(x1: float, y1: float, x2: float, y2: float, x3: float, y3: float) -> float:
    """Calculate the area of a triangle given three vertices."""
    return 0.5 * abs(x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))


def circumcircle_radius(x1: float, y1: float, x2: float, y2: float, x3: float, y3: float) -> float:
    """
    Calculate the radius of the circumcircle passing through three points.
    Returns float('inf') if points are collinear.
    """
    a = distance(x1, y1, x2, y2)
    b = distance(x2, y2, x3, y3)
    c = distance(x3, y3, x1, y1)
    
    area = triangle_area(x1, y1, x2, y2, x3, y3)
    
    if realcompare(area, 0.0) == "EQ":
        return float('inf')
    
    return (a * b * c) / (4.0 * area)


def angle_at_vertex(x1: float, y1: float, x2: float, y2: float, x3: float, y3: float) -> float:
    """
    Calculate the angle at vertex (x2, y2) formed by points (x1,y1), (x2,y2), (x3,y3).
    Returns the angle in radians.
    """
    dx1 = x1 - x2
    dy1 = y1 - y2
    dx2 = x3 - x2
    dy2 = y3 - y2
    
    dot = dx1 * dx2 + dy1 * dy2
    mag1 = math.sqrt(dx1 * dx1 + dy1 * dy1)
    mag2 = math.sqrt(dx2 * dx2 + dy2 * dy2)
    
    if realcompare(mag1, 0.0) == "EQ" or realcompare(mag2, 0.0) == "EQ":
        return -1.0
    
    cos_angle = dot / (mag1 * mag2)
    cos_angle = max(-1.0, min(1.0, cos_angle))
    
    return math.acos(cos_angle)


def point_to_line_distance(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
    """Calculate the perpendicular distance from point (px, py) to line through (x1,y1) and (x2,y2)."""
    if realcompare(x1, x2) == "EQ" and realcompare(y1, y2) == "EQ":
        return distance(px, py, x1, y1)
    
    numerator = abs((y2 - y1) * px - (x2 - x1) * py + x2 * y1 - y2 * x1)
    denominator = math.sqrt((y2 - y1) ** 2 + (x2 - x1) ** 2)
    
    if realcompare(denominator, 0.0) == "EQ":
        return distance(px, py, x1, y1)
    
    return numerator / denominator


def lic1(numpoints: int, x: List[float], y: List[float], length1: float) -> bool:
    """
    LIC 1: There exists at least one set of two consecutive data points
    that are a distance greater than LENGTH1 apart.
    """
    for i in range(numpoints - 1):
        d = distance(x[i], y[i], x[i + 1], y[i + 1])
        if realcompare(d, length1) == "GT":
            return True
    return False


def lic2(numpoints: int, x: List[float], y: List[float], radius1: float) -> bool:
    """
    LIC 2: There exists at least one set of three consecutive data points
    that cannot all be contained within or on a circle of radius RADIUS1.
    """
    for i in range(numpoints - 2):
        r = circumcircle_radius(x[i], y[i], x[i + 1], y[i + 1], x[i + 2], y[i + 2])
        if realcompare(r, radius1) == "GT":
            return True
    return False


def lic3(numpoints: int, x: List[float], y: List[float], epsilon: float) -> bool:
    """
    LIC 3: There exists at least one set of three consecutive data points
    which form an angle such that: angle < (PI - EPSILON) or angle > (PI + EPSILON).
    If either the first point or the last point coincides with the vertex,
    the angle is undefined and the LIC is not satisfied.
    """
    for i in range(numpoints - 2):
        angle = angle_at_vertex(x[i], y[i], x[i + 1], y[i + 1], x[i + 2], y[i + 2])
        if angle < 0:
            continue
        lower = PI - epsilon
        upper = PI + epsilon
        if realcompare(angle, lower) == "LT" or realcompare(angle, upper) == "GT":
            return True
    return False


def lic4(numpoints: int, x: List[float], y: List[float], area1: float) -> bool:
    """
    LIC 4: There exists at least one set of three consecutive data points
    that are the vertices of a triangle with area greater than AREA1.
    """
    for i in range(numpoints - 2):
        area = triangle_area(x[i], y[i], x[i + 1], y[i + 1], x[i + 2], y[i + 2])
        if realcompare(area, area1) == "GT":
            return True
    return False


def lic5(numpoints: int, x: List[float], y: List[float], q_pts: int, quads: int) -> bool:
    """
    LIC 5: There exists at least one set of Q_PTS consecutive data points
    that lie in more than QUADS quadrants.
    """
    for i in range(numpoints - q_pts + 1):
        quadrant_set = set()
        for j in range(q_pts):
            quadrant_set.add(get_quadrant(x[i + j], y[i + j]))
        if len(quadrant_set) > quads:
            return True
    return False


def lic6(numpoints: int, x: List[float], y: List[float]) -> bool:
    """
    LIC 6: There exists at least one set of two consecutive data points,
    (X[i], Y[i]) and (X[j], Y[j]), such that X[j] - X[i] < 0 (where i = j - 1).
    """
    for i in range(numpoints - 1):
        if realcompare(x[i + 1] - x[i], 0.0) == "LT":
            return True
    return False


def lic7(numpoints: int, x: List[float], y: List[float], n_pts: int, dist: float) -> bool:
    """
    LIC 7: There exists at least one set of N_PTS consecutive data points such that
    at least one of the points lies a distance greater than DIST from the line
    joining the first and last of these N_PTS points.
    If the first and last points are identical, compare distance from that point to all others.
    The condition is not met when NUMPOINTS < 3.
    """
    if numpoints < 3:
        return False
    
    for i in range(numpoints - n_pts + 1):
        first_x, first_y = x[i], y[i]
        last_x, last_y = x[i + n_pts - 1], y[i + n_pts - 1]
        
        for j in range(1, n_pts - 1):
            px, py = x[i + j], y[i + j]
            d = point_to_line_distance(px, py, first_x, first_y, last_x, last_y)
            if realcompare(d, dist) == "GT":
                return True
    return False


def lic8(numpoints: int, x: List[float], y: List[float], k_pts: int, length1: float) -> bool:
    """
    LIC 8: There exists at least one set of two data points separated by exactly
    K_PTS consecutive intervening points that are a distance greater than LENGTH1 apart.
    The condition is not met when NUMPOINTS < 3.
    """
    if numpoints < 3:
        return False
    
    for i in range(numpoints - k_pts - 1):
        j = i + k_pts + 1
        d = distance(x[i], y[i], x[j], y[j])
        if realcompare(d, length1) == "GT":
            return True
    return False


def lic9(numpoints: int, x: List[float], y: List[float], a_pts: int, b_pts: int, radius1: float) -> bool:
    """
    LIC 9: There exists at least one set of three data points separated by exactly
    A_PTS and B_PTS consecutive intervening points, respectively, that cannot be
    contained within or on a circle of radius RADIUS1.
    The condition is not met when NUMPOINTS < 5.
    """
    if numpoints < 5:
        return False
    
    for i in range(numpoints - a_pts - b_pts - 2):
        j = i + a_pts + 1
        k = j + b_pts + 1
        r = circumcircle_radius(x[i], y[i], x[j], y[j], x[k], y[k])
        if realcompare(r, radius1) == "GT":
            return True
    return False


def lic10(numpoints: int, x: List[float], y: List[float], c_pts: int, d_pts: int, epsilon: float) -> bool:
    """
    LIC 10: There exists at least one set of three data points separated by exactly
    C_PTS and D_PTS consecutive intervening points, respectively, that form an angle
    such that: angle < (PI - EPSILON) or angle > (PI + EPSILON).
    The second point is the vertex. If either first or last point coincides with vertex,
    the angle is undefined. The condition is not met when NUMPOINTS < 5.
    """
    if numpoints < 5:
        return False
    
    for i in range(numpoints - c_pts - d_pts - 2):
        j = i + c_pts + 1
        k = j + d_pts + 1
        angle = angle_at_vertex(x[i], y[i], x[j], y[j], x[k], y[k])
        if angle < 0:
            continue
        lower = PI - epsilon
        upper = PI + epsilon
        if realcompare(angle, lower) == "LT" or realcompare(angle, upper) == "GT":
            return True
    return False


def lic11(numpoints: int, x: List[float], y: List[float], e_pts: int, f_pts: int, area1: float) -> bool:
    """
    LIC 11: There exists at least one set of three data points separated by exactly
    E_PTS and F_PTS consecutive intervening points, respectively, that are the vertices
    of a triangle with area greater than AREA1.
    The condition is not met when NUMPOINTS < 5.
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


def lic12(numpoints: int, x: List[float], y: List[float], g_pts: int) -> bool:
    """
    LIC 12: There exists at least one set of two data points, (X[i], Y[i]) and (X[j], Y[j]),
    separated by exactly G_PTS consecutive intervening points, such that X[j] - X[i] < 0.
    The condition is not met when NUMPOINTS < 3.
    """
    if numpoints < 3:
        return False
    
    for i in range(numpoints - g_pts - 1):
        j = i + g_pts + 1
        if realcompare(x[j] - x[i], 0.0) == "LT":
            return True
    return False


def lic13(numpoints: int, x: List[float], y: List[float], k_pts: int, length1: float, length2: float) -> bool:
    """
    LIC 13: There exists at least one set of two data points, separated by exactly
    K_PTS consecutive intervening points, which are a distance greater than LENGTH1 apart.
    In addition, there exists at least one set of two data points (can be same or different),
    separated by exactly K_PTS consecutive intervening points, that are a distance less
    than LENGTH2 apart. Both parts must be true.
    The condition is not met when NUMPOINTS < 3.
    """
    if numpoints < 3:
        return False
    
    has_greater = False
    has_less = False
    
    for i in range(numpoints - k_pts - 1):
        j = i + k_pts + 1
        d = distance(x[i], y[i], x[j], y[j])
        if realcompare(d, length1) == "GT":
            has_greater = True
        if realcompare(d, length2) == "LT":
            has_less = True
    
    return has_greater and has_less


def lic14(numpoints: int, x: List[float], y: List[float], a_pts: int, b_pts: int, radius1: float, radius2: float) -> bool:
    """
    LIC 14: There exists at least one set of three data points, separated by exactly
    A_PTS and B_PTS consecutive intervening points, respectively, that cannot be contained
    within or on a circle of radius RADIUS1. In addition, there exists at least one set
    of three data points (can be same or different) separated by exactly A_PTS and B_PTS
    consecutive intervening points, respectively, that can be contained in or on a circle
    of radius RADIUS2. Both parts must be true.
    The condition is not met when NUMPOINTS < 5.
    """
    if numpoints < 5:
        return False
    
    has_outside = False
    has_inside = False
    
    for i in range(numpoints - a_pts - b_pts - 2):
        j = i + a_pts + 1
        k = j + b_pts + 1
        r = circumcircle_radius(x[i], y[i], x[j], y[j], x[k], y[k])
        if realcompare(r, radius1) == "GT":
            has_outside = True
        if realcompare(r, radius2) != "GT":
            has_inside = True
    
    return has_outside and has_inside


def lic15(numpoints: int, x: List[float], y: List[float], e_pts: int, f_pts: int, area1: float, area2: float) -> bool:
    """
    LIC 15: There exists at least one set of three data points, separated by exactly
    E_PTS and F_PTS consecutive intervening points, respectively, that are the vertices
    of a triangle with area greater than AREA1. In addition, there exist three data points
    (can be same or different) separated by exactly E_PTS and F_PTS consecutive intervening
    points, respectively, that are the vertices of a triangle with area less than AREA2.
    Both parts must be true.
    The condition is not met when NUMPOINTS < 5.
    """
    if numpoints < 5:
        return False
    
    has_greater = False
    has_less = False
    
    for i in range(numpoints - e_pts - f_pts - 2):
        j = i + e_pts + 1
        k = j + f_pts + 1
        area = triangle_area(x[i], y[i], x[j], y[j], x[k], y[k])
        if realcompare(area, area1) == "GT":
            has_greater = True
        if realcompare(area, area2) == "LT":
            has_less = True
    
    return has_greater and has_less


def compute_cmv(numpoints: int, x: List[float], y: List[float], parameters: Dict[str, Any]) -> List[bool]:
    """Compute the Conditions Met Vector (CMV) for all 15 LICs."""
    cmv = []
    
    cmv.append(lic1(numpoints, x, y, parameters["LENGTH1"]))
    cmv.append(lic2(numpoints, x, y, parameters["RADIUS1"]))
    cmv.append(lic3(numpoints, x, y, parameters["EPSILON"]))
    cmv.append(lic4(numpoints, x, y, parameters["AREA1"]))
    cmv.append(lic5(numpoints, x, y, parameters["Q_PTS"], parameters["QUADS"]))
    cmv.append(lic6(numpoints, x, y))
    cmv.append(lic7(numpoints, x, y, parameters["N_PTS"], parameters["DIST"]))
    cmv.append(lic8(numpoints, x, y, parameters["K_PTS"], parameters["LENGTH1"]))
    cmv.append(lic9(numpoints, x, y, parameters["A_PTS"], parameters["B_PTS"], parameters["RADIUS1"]))
    cmv.append(lic10(numpoints, x, y, parameters["C_PTS"], parameters["D_PTS"], parameters["EPSILON"]))
    cmv.append(lic11(numpoints, x, y, parameters["E_PTS"], parameters["F_PTS"], parameters["AREA1"]))
    cmv.append(lic12(numpoints, x, y, parameters["G_PTS"]))
    cmv.append(lic13(numpoints, x, y, parameters["K_PTS"], parameters["LENGTH1"], parameters["LENGTH2"]))
    cmv.append(lic14(numpoints, x, y, parameters["A_PTS"], parameters["B_PTS"], parameters["RADIUS1"], parameters["RADIUS2"]))
    cmv.append(lic15(numpoints, x, y, parameters["E_PTS"], parameters["F_PTS"], parameters["AREA1"], parameters["AREA2"]))
    
    return cmv


def compute_pum(cmv: List[bool], lcm: List[List[str]], pum_diag: List[bool]) -> List[List[bool]]:
    """
    Compute the Preliminary Unlocking Matrix (PUM).
    lcm[i][j] represents the Boolean operator to be applied to cmv[i] and cmv[j].
    - NOTUSED: PUM[i][j] = true
    - ANDD: PUM[i][j] = cmv[i] AND cmv[j]
    - ORR: PUM[i][j] = cmv[i] OR cmv[j]
    """
    pum = [[False for _ in range(15)] for _ in range(15)]
    
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


def compute_fuv(pum: List[List[bool]], pum_diag: List[bool]) -> List[bool]:
    """
    Compute the Final Unlocking Vector (FUV).
    FUV[i] = true if PUM[i][i] is false OR if all elements in PUM row i are true.
    """
    fuv = []
    
    for i in range(15):
        if not pum_diag[i]:
            fuv.append(True)
        else:
            all_true = all(pum[i][j] for j in range(15))
            fuv.append(all_true)
    
    return fuv


def compute_launch(fuv: List[bool]) -> bool:
    """
    Compute the launch decision.
    LAUNCH = true if and only if all elements of FUV are true.
    """
    return all(fuv)


def decide(numpoints: int, x: List[float], y: List[float], parameters: Dict[str, Any],
           lcm: List[List[str]], pum_diag: List[bool]) -> Tuple[List[bool], List[List[bool]], List[bool], bool]:
    """
    Main DECIDE procedure.
    
    Args:
        numpoints: Number of data points (2..100)
        x: X coordinates of data points
        y: Y coordinates of data points
        parameters: Dictionary of LIC parameters
        lcm: 15x15 Logical Connector Matrix
        pum_diag: 15-element list of diagonal PUM values
    
    Returns:
        Tuple of (cmv, pum, fuv, launch)
    """
    cmv = compute_cmv(numpoints, x, y, parameters)
    pum = compute_pum(cmv, lcm, pum_diag)
    fuv = compute_fuv(pum, pum_diag)
    launch = compute_launch(fuv)
    
    return cmv, pum, fuv, launch


def main():
    """Main entry point for stdin/stdout JSON interface."""
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
