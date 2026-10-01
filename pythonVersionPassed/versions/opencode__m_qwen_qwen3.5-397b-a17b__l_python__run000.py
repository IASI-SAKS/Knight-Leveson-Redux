#!/usr/bin/env python3
"""
Launch Interceptor Program - Implementation of Knight & Leveson (1986)
"""

import json
import math
import sys
from typing import List, Dict, Any

PI = 3.1415926535


def realcompare(a: float, b: float) -> str:
    """Tolerance-based six-significant-digit comparison."""
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
    """Euclidean distance between two points."""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def triangle_area(x1: float, y1: float, x2: float, y2: float, x3: float, y3: float) -> float:
    """Area of triangle formed by three points using shoelace formula."""
    return 0.5 * abs(x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))


def circumradius(x1: float, y1: float, x2: float, y2: float, x3: float, y3: float) -> float:
    """
    Circumradius of triangle formed by three points.
    Returns float('inf') if points are collinear.
    """
    a = distance(x1, y1, x2, y2)
    b = distance(x2, y2, x3, y3)
    c = distance(x3, y3, x1, y1)
    area = triangle_area(x1, y1, x2, y2, x3, y3)
    if realcompare(area, 0.0) == "EQ":
        return float('inf')
    return (a * b * c) / (4.0 * area)


def angle_at_vertex(x1: float, y1: float, vx: float, vy: float, x2: float, y2: float) -> float:
    """
    Calculate the angle at vertex (vx, vy) formed by points (x1,y1)-(vx,vy)-(x2,y2).
    Returns the angle in radians (0 to 2*PI).
    """
    dx1 = x1 - vx
    dy1 = y1 - vy
    dx2 = x2 - vx
    dy2 = y2 - vy
    
    len1 = math.sqrt(dx1 * dx1 + dy1 * dy1)
    len2 = math.sqrt(dx2 * dx2 + dy2 * dy2)
    
    if realcompare(len1, 0.0) == "EQ" or realcompare(len2, 0.0) == "EQ":
        return -1.0
    
    dot = dx1 * dx2 + dy1 * dy2
    cos_angle = dot / (len1 * len2)
    
    if cos_angle > 1.0:
        cos_angle = 1.0
    elif cos_angle < -1.0:
        cos_angle = -1.0
    
    angle = math.acos(cos_angle)
    return angle


def get_quadrant(x: float, y: float) -> int:
    """
    Get quadrant of a point (1-4).
    Priority for axis points: I, II, III, IV
    (0,0) -> I, (-1,0) -> II, (0,-1) -> III, (0,1) -> I, (1,0) -> I
    """
    if x >= 0 and y >= 0:
        return 1
    elif x < 0 and y >= 0:
        return 2
    elif x < 0 and y < 0:
        return 3
    else:
        return 4


def point_to_line_distance(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
    """Distance from point (px, py) to line through (x1,y1) and (x2,y2)."""
    if realcompare(x1, x2) == "EQ" and realcompare(y1, y2) == "EQ":
        return distance(px, py, x1, y1)
    
    numerator = abs((y2 - y1) * px - (x2 - x1) * py + x2 * y1 - y2 * x1)
    denominator = math.sqrt((y2 - y1) ** 2 + (x2 - x1) ** 2)
    return numerator / denominator


def lic_1(numpoints: int, x: List[float], y: List[float], length1: float) -> bool:
    """LIC 1: Two consecutive points with distance > LENGTH1."""
    for i in range(numpoints - 1):
        d = distance(x[i], y[i], x[i + 1], y[i + 1])
        if realcompare(d, length1) == "GT":
            return True
    return False


def lic_2(numpoints: int, x: List[float], y: List[float], radius1: float) -> bool:
    """LIC 2: Three consecutive points cannot all be contained in/on circle of radius RADIUS1."""
    for i in range(numpoints - 2):
        r = circumradius(x[i], y[i], x[i + 1], y[i + 1], x[i + 2], y[i + 2])
        if realcompare(r, radius1) == "GT":
            return True
    return False


def lic_3(numpoints: int, x: List[float], y: List[float], epsilon: float) -> bool:
    """LIC 3: Three consecutive points form angle outside (PI - EPSILON, PI + EPSILON)."""
    for i in range(numpoints - 2):
        angle = angle_at_vertex(x[i], y[i], x[i + 1], y[i + 1], x[i + 2], y[i + 2])
        if angle < 0:
            continue
        lower = PI - epsilon
        upper = PI + epsilon
        if realcompare(angle, lower) == "LT" or realcompare(angle, upper) == "GT":
            return True
    return False


def lic_4(numpoints: int, x: List[float], y: List[float], area1: float) -> bool:
    """LIC 4: Three consecutive points form triangle with area > AREA1."""
    for i in range(numpoints - 2):
        area = triangle_area(x[i], y[i], x[i + 1], y[i + 1], x[i + 2], y[i + 2])
        if realcompare(area, area1) == "GT":
            return True
    return False


def lic_5(numpoints: int, x: List[float], y: List[float], q_pts: int, quads: int) -> bool:
    """LIC 5: Q_PTS consecutive points lie in more than QUADS quadrants."""
    for i in range(numpoints - q_pts + 1):
        quadrant_set = set()
        for j in range(q_pts):
            quadrant_set.add(get_quadrant(x[i + j], y[i + j]))
        if len(quadrant_set) > quads:
            return True
    return False


def lic_6(numpoints: int, x: List[float], y: List[float]) -> bool:
    """LIC 6: Two consecutive points where X[j] - X[i] < 0 (where i = j - 1)."""
    for i in range(numpoints - 1):
        if realcompare(x[i + 1] - x[i], 0.0) == "LT":
            return True
    return False


def lic_7(numpoints: int, x: List[float], y: List[float], n_pts: int, dist: float) -> bool:
    """LIC 7: N_PTS consecutive points where at least one point is > DIST from line joining first and last."""
    if numpoints < 3:
        return False
    for i in range(numpoints - n_pts + 1):
        first_x, first_y = x[i], y[i]
        last_x, last_y = x[i + n_pts - 1], y[i + n_pts - 1]
        for j in range(i, i + n_pts):
            d = point_to_line_distance(x[j], y[j], first_x, first_y, last_x, last_y)
            if realcompare(d, dist) == "GT":
                return True
    return False


def lic_8(numpoints: int, x: List[float], y: List[float], k_pts: int, length1: float) -> bool:
    """LIC 8: Two points separated by K_PTS intervening points with distance > LENGTH1."""
    if numpoints < 3:
        return False
    for i in range(numpoints - k_pts - 1):
        j = i + k_pts + 1
        d = distance(x[i], y[i], x[j], y[j])
        if realcompare(d, length1) == "GT":
            return True
    return False


def lic_9(numpoints: int, x: List[float], y: List[float], a_pts: int, b_pts: int, radius1: float) -> bool:
    """LIC 9: Three points separated by A_PTS and B_PTS intervening points that cannot be contained in/on circle of radius RADIUS1."""
    if numpoints < 5:
        return False
    for i in range(numpoints - a_pts - b_pts - 2):
        j = i + a_pts + 1
        k = j + b_pts + 1
        r = circumradius(x[i], y[i], x[j], y[j], x[k], y[k])
        if realcompare(r, radius1) == "GT":
            return True
    return False


def lic_10(numpoints: int, x: List[float], y: List[float], c_pts: int, d_pts: int, epsilon: float) -> bool:
    """LIC 10: Three points separated by C_PTS and D_PTS forming angle outside (PI - EPSILON, PI + EPSILON)."""
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


def lic_11(numpoints: int, x: List[float], y: List[float], e_pts: int, f_pts: int, area1: float) -> bool:
    """LIC 11: Three points separated by E_PTS and F_PTS forming triangle with area > AREA1."""
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
    """LIC 12: Two points separated by G_PTS intervening points where X[j] - X[i] < 0."""
    if numpoints < 3:
        return False
    for i in range(numpoints - g_pts - 1):
        j = i + g_pts + 1
        if realcompare(x[j] - x[i], 0.0) == "LT":
            return True
    return False


def lic_13(numpoints: int, x: List[float], y: List[float], k_pts: int, length1: float, length2: float) -> bool:
    """LIC 13: Both conditions must be true:
    - Two points separated by K_PTS with distance > LENGTH1
    - Two points separated by K_PTS with distance < LENGTH2
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


def lic_14(numpoints: int, x: List[float], y: List[float], a_pts: int, b_pts: int, radius1: float, radius2: float) -> bool:
    """LIC 14: Both conditions must be true:
    - Three points separated by A_PTS and B_PTS that cannot be contained in/on circle of radius RADIUS1
    - Three points separated by A_PTS and B_PTS that can be contained in/on circle of radius RADIUS2
    """
    if numpoints < 5:
        return False
    
    has_greater = False
    has_less_or_equal = False
    
    for i in range(numpoints - a_pts - b_pts - 2):
        j = i + a_pts + 1
        k = j + b_pts + 1
        r = circumradius(x[i], y[i], x[j], y[j], x[k], y[k])
        if realcompare(r, radius1) == "GT":
            has_greater = True
        if realcompare(r, radius2) != "GT":
            has_less_or_equal = True
    
    return has_greater and has_less_or_equal


def lic_15(numpoints: int, x: List[float], y: List[float], e_pts: int, f_pts: int, area1: float, area2: float) -> bool:
    """LIC 15: Both conditions must be true:
    - Three points separated by E_PTS and F_PTS forming triangle with area > AREA1
    - Three points separated by E_PTS and F_PTS forming triangle with area < AREA2
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


def compute_cmv(numpoints: int, x: List[float], y: List[float], parameters: Dict[str, float]) -> List[bool]:
    """Compute the Conditions Met Vector (CMV) for all 15 LICs."""
    cmv = [False] * 15
    
    cmv[0] = lic_1(numpoints, x, y, parameters["LENGTH1"])
    cmv[1] = lic_2(numpoints, x, y, parameters["RADIUS1"])
    cmv[2] = lic_3(numpoints, x, y, parameters["EPSILON"])
    cmv[3] = lic_4(numpoints, x, y, parameters["AREA1"])
    cmv[4] = lic_5(numpoints, x, y, int(parameters["Q_PTS"]), int(parameters["QUADS"]))
    cmv[5] = lic_6(numpoints, x, y)
    cmv[6] = lic_7(numpoints, x, y, int(parameters["N_PTS"]), parameters["DIST"])
    cmv[7] = lic_8(numpoints, x, y, int(parameters["K_PTS"]), parameters["LENGTH1"])
    cmv[8] = lic_9(numpoints, x, y, int(parameters["A_PTS"]), int(parameters["B_PTS"]), parameters["RADIUS1"])
    cmv[9] = lic_10(numpoints, x, y, int(parameters["C_PTS"]), int(parameters["D_PTS"]), parameters["EPSILON"])
    cmv[10] = lic_11(numpoints, x, y, int(parameters["E_PTS"]), int(parameters["F_PTS"]), parameters["AREA1"])
    cmv[11] = lic_12(numpoints, x, y, int(parameters["G_PTS"]))
    cmv[12] = lic_13(numpoints, x, y, int(parameters["K_PTS"]), parameters["LENGTH1"], parameters["LENGTH2"])
    cmv[13] = lic_14(numpoints, x, y, int(parameters["A_PTS"]), int(parameters["B_PTS"]), parameters["RADIUS1"], parameters["RADIUS2"])
    cmv[14] = lic_15(numpoints, x, y, int(parameters["E_PTS"]), int(parameters["F_PTS"]), parameters["AREA1"], parameters["AREA2"])
    
    return cmv


def compute_pum(cmv: List[bool], lcm: List[List[str]], pum_diag: List[bool]) -> List[List[bool]]:
    """Compute the Preliminary Unlocking Matrix (PUM)."""
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


def compute_fuv(pum: List[List[bool]], pum_diag: List[bool]) -> List[bool]:
    """Compute the Final Unlocking Vector (FUV)."""
    fuv = [False] * 15
    
    for i in range(15):
        if not pum_diag[i]:
            fuv[i] = True
        else:
            all_true = True
            for j in range(15):
                if not pum[i][j]:
                    all_true = False
                    break
            fuv[i] = all_true
    
    return fuv


def compute_launch(fuv: List[bool]) -> bool:
    """Compute the launch decision."""
    return all(fuv)


def decide(numpoints: int, x: List[float], y: List[float], parameters: Dict[str, float], 
           lcm: List[List[str]], pum_diag: List[bool]) -> Dict[str, Any]:
    """
    Main decide function that computes CMV, PUM, FUV, and launch decision.
    
    Args:
        numpoints: Number of data points (2..100)
        x: X coordinates of data points
        y: Y coordinates of data points
        parameters: Dictionary with Pascal-style keys (LENGTH1, RADIUS1, etc.)
        lcm: 15x15 Logical Connector Matrix with "NOTUSED", "ORR", "ANDD"
        pum_diag: Length-15 list of booleans for diagonal PUM elements
    
    Returns:
        Dictionary with cmv, pum, fuv, and launch
    """
    cmv = compute_cmv(numpoints, x, y, parameters)
    pum = compute_pum(cmv, lcm, pum_diag)
    fuv = compute_fuv(pum, pum_diag)
    launch = compute_launch(fuv)
    
    return {
        "cmv": cmv,
        "pum": pum,
        "fuv": fuv,
        "launch": launch
    }


def main():
    """Main entry point for stdin/stdout JSON processing."""
    input_data = json.load(sys.stdin)
    
    numpoints = input_data["numpoints"]
    x = input_data["x"]
    y = input_data["y"]
    parameters = input_data["parameters"]
    lcm = input_data["lcm"]
    pum_diag = input_data["pum_diag"]
    
    result = decide(numpoints, x, y, parameters, lcm, pum_diag)
    
    json.dump(result, sys.stdout)


if __name__ == "__main__":
    main()
