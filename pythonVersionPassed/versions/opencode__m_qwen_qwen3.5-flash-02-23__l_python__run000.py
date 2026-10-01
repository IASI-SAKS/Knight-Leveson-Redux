#!/usr/bin/env python3
"""
Launch Interceptor Program - Implementation of Knight & Leveson (1986)

This module evaluates Launch Interceptor Conditions (LICs) for radar tracking data
and determines whether to launch an interceptor based on the computed vectors.
"""

import json
import math
from typing import List, Dict, Any, Tuple

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
    """Calculate Euclidean distance between two points."""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def angle_at_vertex(x1: float, y1: float, x2: float, y2: float, x3: float, y3: float) -> float:
    """
    Calculate the angle at point (x2, y2) formed by points (x1, y1), (x2, y2), (x3, y3).
    Returns angle in radians (0 to PI).
    """
    # Vectors from vertex to other points
    v1x, v1y = x1 - x2, y1 - y2
    v2x, v2y = x3 - x2, y3 - y2
    
    len1 = math.sqrt(v1x ** 2 + v1y ** 2)
    len2 = math.sqrt(v2x ** 2 + v2y ** 2)
    
    if len1 == 0 or len2 == 0:
        return -1  # Undefined angle
    
    # Dot product
    dot = v1x * v2x + v1y * v2y
    
    # Cosine of angle
    cos_angle = dot / (len1 * len2)
    
    # Clamp to valid range for numerical stability
    cos_angle = max(-1.0, min(1.0, cos_angle))
    
    return math.acos(cos_angle)


def triangle_area(x1: float, y1: float, x2: float, y2: float, x3: float, y3: float) -> float:
    """Calculate area of triangle using shoelace formula."""
    return 0.5 * abs(x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))


def circumradius(x1: float, y1: float, x2: float, y2: float, x3: float, y3: float) -> float:
    """
    Calculate circumradius of triangle formed by three points.
    Returns infinity if points are collinear.
    """
    a = distance(x1, y1, x2, y2)
    b = distance(x2, y2, x3, y3)
    c = distance(x1, y1, x3, y3)
    
    # Check for collinearity (area close to zero)
    area = triangle_area(x1, y1, x2, y2, x3, y3)
    if area < 1e-10:
        return float('inf')
    
    # Circumradius = (a * b * c) / (4 * area)
    return (a * b * c) / (4 * area)


def get_quadrant(x: float, y: float) -> int:
    """
    Get quadrant number for a point (1=I, 2=II, 3=III, 4=IV).
    Priority: I > II > III > IV for points on axes.
    """
    if x > 0 and y >= 0:
        return 1  # Quadrant I (including positive y-axis)
    elif x <= 0 and y > 0:
        return 2  # Quadrant II (including negative x-axis)
    elif x < 0 and y <= 0:
        return 3  # Quadrant III (including negative y-axis)
    else:
        return 4  # Quadrant IV (including positive x-axis)


def check_consecutive_points_condition(
    x: List[float], y: List[float], numpoints: int,
    check_func, window_size: int
) -> bool:
    """Check if any consecutive window satisfies the condition."""
    for i in range(numpoints - window_size + 1):
        if check_func(x, y, i, window_size):
            return True
    return False


def check_point_separation_condition(
    x: List[float], y: List[float], numpoints: int,
    check_func, separation: int
) -> bool:
    """Check if any two points separated by 'separation' intervening points satisfy the condition."""
    for i in range(numpoints - separation - 1):
        j = i + separation + 1
        if check_func(x, y, i, j):
            return True
    return False


def check_three_point_separation_condition(
    x: List[float], y: List[float], numpoints: int,
    check_func, sep1: int, sep2: int
) -> bool:
    """Check if any three points separated by sep1 and sep2 intervening points satisfy the condition."""
    for i in range(numpoints - sep1 - sep2 - 2):
        j = i + sep1 + 1
        k = j + sep2 + 1
        if check_func(x, y, i, j, k):
            return True
    return False


def evaluate_lcm_pum(lcm: List[List[str]], cmv: List[bool], pum_diag: List[bool]) -> Tuple[List[List[bool]], List[bool]]:
    """
    Compute PUM from LCM and CMV, then compute FUV from PUM and pum_diag.
    Returns (pum, fuv).
    """
    n = 15
    
    # Initialize PUM
    pum = [[False] * n for _ in range(n)]
    
    # Fill diagonal elements from pum_diag
    for i in range(n):
        pum[i][i] = pum_diag[i]
    
    # Fill off-diagonal elements based on LCM
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            connector = lcm[i][j]
            if connector == "NOTUSED":
                pum[i][j] = True
            elif connector == "ANDD":
                pum[i][j] = cmv[i] and cmv[j]
            elif connector == "ORR":
                pum[i][j] = cmv[i] or cmv[j]
    
    # Compute FUV
    fuv = [False] * n
    for i in range(n):
        # FUV[i] is true if pum_diag[i] is false OR all elements in row i are true
        if not pum_diag[i]:
            fuv[i] = True
        else:
            all_true = all(pum[i][j] for j in range(n))
            fuv[i] = all_true
    
    return pum, fuv


def decide(
    numpoints: int,
    x: List[float],
    y: List[float],
    parameters: Dict[str, float],
    lcm: List[List[str]],
    pum_diag: List[bool]
) -> Dict[str, Any]:
    """
    Main decision function that evaluates all LICs and computes launch decision.
    
    Args:
        numpoints: Number of data points (2-100)
        x: X coordinates of data points
        y: Y coordinates of data points
        parameters: Dictionary of parameter values
        lcm: 15x15 Logical Connector Matrix
        pum_diag: 15-element list of diagonal PUM values
        
    Returns:
        Dictionary with cmv, pum, fuv, and launch decision
    """
    cmv = [False] * 15
    
    # Extract parameters
    length1 = parameters["LENGTH1"]
    radius1 = parameters["RADIUS1"]
    epsilon = parameters["EPSILON"]
    area1 = parameters["AREA1"]
    q_pts = parameters["Q_PTS"]
    quads = parameters["QUADS"]
    dist = parameters["DIST"]
    n_pts = parameters["N_PTS"]
    k_pts = parameters["K_PTS"]
    a_pts = parameters["A_PTS"]
    b_pts = parameters["B_PTS"]
    c_pts = parameters["C_PTS"]
    d_pts = parameters["D_PTS"]
    e_pts = parameters["E_PTS"]
    f_pts = parameters["F_PTS"]
    g_pts = parameters["G_PTS"]
    length2 = parameters["LENGTH2"]
    radius2 = parameters["RADIUS2"]
    area2 = parameters["AREA2"]
    
    # LIC 1: Two consecutive points distance > LENGTH1
    def lic1_check(x, y, i, window):
        j = i + 1
        return realcompare(distance(x[i], y[i], x[j], y[j]), length1) == "GT"
    cmv[0] = check_consecutive_points_condition(x, y, numpoints, lic1_check, 2)
    
    # LIC 2: Three consecutive points cannot be contained in circle of radius RADIUS1
    def lic2_check(x, y, i, window):
        r = circumradius(x[i], y[i], x[i+1], y[i+1], x[i+2], y[i+2])
        return realcompare(r, radius1) == "GT"
    cmv[1] = check_consecutive_points_condition(x, y, numpoints, lic2_check, 3)
    
    # LIC 3: Three consecutive points form angle < (PI - EPSILON) or > (PI + EPSILON)
    def lic3_check(x, y, i, window):
        angle = angle_at_vertex(x[i], y[i], x[i+1], y[i+1], x[i+2], y[i+2])
        if angle < 0:  # Undefined
            return False
        lower = PI - epsilon
        upper = PI + epsilon
        return realcompare(angle, lower) == "LT" or realcompare(angle, upper) == "GT"
    cmv[2] = check_consecutive_points_condition(x, y, numpoints, lic3_check, 3)
    
    # LIC 4: Three consecutive points form triangle with area > AREA1
    def lic4_check(x, y, i, window):
        return realcompare(triangle_area(x[i], y[i], x[i+1], y[i+1], x[i+2], y[i+2]), area1) == "GT"
    cmv[3] = check_consecutive_points_condition(x, y, numpoints, lic4_check, 3)
    
    # LIC 5: Q_PTS consecutive points lie in more than QUADS quadrants
    def lic5_check(x, y, i, window):
        quadrants = set()
        for k in range(window):
            quadrants.add(get_quadrant(x[i + k], y[i + k]))
        return len(quadrants) > quads
    cmv[4] = check_consecutive_points_condition(x, y, numpoints, lic5_check, int(q_pts))
    
    # LIC 6: Two consecutive points with X[j] - X[i] < 0 (where j = i + 1)
    def lic6_check(x, y, i, window):
        return realcompare(x[i + 1] - x[i], 0) == "LT"
    cmv[5] = check_consecutive_points_condition(x, y, numpoints, lic6_check, 2)
    
    # LIC 7: N_PTS consecutive points - at least one point distance > DIST from line joining first and last
    def lic7_check(x, y, i, window):
        n = window
        if n < 3:
            return False
        
        x0, y0 = x[i], y[i]
        xn = x[i + n - 1], y[i + n - 1]
        
        # Check if first and last are identical
        if distance(x0, y0, x[i + n - 1], y[i + n - 1]) < 1e-10:
            # Distance from coincident point to all other points
            for k in range(1, n - 1):
                if realcompare(distance(x[i], y[i], x[i + k], y[i + k]), dist) == "GT":
                    return True
        else:
            # Distance from point to line
            for k in range(1, n - 1):
                # Distance from point (xk, yk) to line through (x0, y0) and (xn, yn)
                xk, yk = x[i + k], y[i + k]
                # Line equation: (y0 - yn) * x + (xn - x0) * y + x0*yn - yn*x0 = 0
                # Distance = |Ax + By + C| / sqrt(A^2 + B^2)
                A = y0 - y[i + n - 1]
                B = x[i + n - 1] - x0
                C = x0 * y[i + n - 1] - x[i + n - 1] * y0
                denom = math.sqrt(A * A + B * B)
                if denom < 1e-10:
                    continue
                d = abs(A * xk + B * yk + C) / denom
                if realcompare(d, dist) == "GT":
                    return True
        return False
    cmv[6] = check_consecutive_points_condition(x, y, numpoints, lic7_check, int(n_pts))
    
    # LIC 8: Two points separated by K_PTS intervening points with distance > LENGTH1
    def lic8_check(x, y, i, j):
        return realcompare(distance(x[i], y[i], x[j], y[j]), length1) == "GT"
    cmv[7] = check_point_separation_condition(x, y, numpoints, lic8_check, int(k_pts))
    
    # LIC 9: Three points separated by A_PTS and B_PTS cannot be contained in circle of radius RADIUS1
    def lic9_check(x, y, i, j, k):
        r = circumradius(x[i], y[i], x[j], y[j], x[k], y[k])
        return realcompare(r, radius1) == "GT"
    cmv[8] = check_three_point_separation_condition(x, y, numpoints, lic9_check, int(a_pts), int(b_pts))
    
    # LIC 10: Three points separated by C_PTS and D_PTS form angle < (PI - EPSILON) or > (PI + EPSILON)
    def lic10_check(x, y, i, j, k):
        angle = angle_at_vertex(x[i], y[i], x[j], y[j], x[k], y[k])
        if angle < 0:  # Undefined
            return False
        lower = PI - epsilon
        upper = PI + epsilon
        return realcompare(angle, lower) == "LT" or realcompare(angle, upper) == "GT"
    cmv[9] = check_three_point_separation_condition(x, y, numpoints, lic10_check, int(c_pts), int(d_pts))
    
    # LIC 11: Three points separated by E_PTS and F_PTS form triangle with area > AREA1
    def lic11_check(x, y, i, j, k):
        return realcompare(triangle_area(x[i], y[i], x[j], y[j], x[k], y[k]), area1) == "GT"
    cmv[10] = check_three_point_separation_condition(x, y, numpoints, lic11_check, int(e_pts), int(f_pts))
    
    # LIC 12: Two points separated by G_PTS with X[j] - X[i] < 0
    def lic12_check(x, y, i, j):
        return realcompare(x[j] - x[i], 0) == "LT"
    cmv[11] = check_point_separation_condition(x, y, numpoints, lic12_check, int(g_pts))
    
    # LIC 13: Two conditions:
    #   a) Two points separated by K_PTS with distance > LENGTH1
    #   b) Two points separated by K_PTS with distance < LENGTH2
    lic13a = check_point_separation_condition(x, y, numpoints, lic8_check, int(k_pts))
    
    def lic13b_check(x, y, i, j):
        return realcompare(distance(x[i], y[i], x[j], y[j]), length2) == "LT"
    lic13b = check_point_separation_condition(x, y, numpoints, lic13b_check, int(k_pts))
    cmv[12] = lic13a and lic13b
    
    # LIC 14: Two conditions:
    #   a) Three points separated by A_PTS and B_PTS cannot be contained in circle of radius RADIUS1
    #   b) Three points separated by A_PTS and B_PTS can be contained in circle of radius RADIUS2
    lic14a = check_three_point_separation_condition(x, y, numpoints, lic9_check, int(a_pts), int(b_pts))
    
    def lic14b_check(x, y, i, j, k):
        r = circumradius(x[i], y[i], x[j], y[j], x[k], y[k])
        return realcompare(r, radius2) == "LT" or realcompare(r, radius2) == "EQ"
    lic14b = check_three_point_separation_condition(x, y, numpoints, lic14b_check, int(a_pts), int(b_pts))
    cmv[13] = lic14a and lic14b
    
    # LIC 15: Two conditions:
    #   a) Three points separated by E_PTS and F_PTS form triangle with area > AREA1
    #   b) Three points separated by E_PTS and F_PTS form triangle with area < AREA2
    lic15a = check_three_point_separation_condition(x, y, numpoints, lic11_check, int(e_pts), int(f_pts))
    
    def lic15b_check(x, y, i, j, k):
        return realcompare(triangle_area(x[i], y[i], x[j], y[j], x[k], y[k]), area2) == "LT"
    lic15b = check_three_point_separation_condition(x, y, numpoints, lic15b_check, int(e_pts), int(f_pts))
    cmv[14] = lic15a and lic15b
    
    # Compute PUM and FUV
    pum, fuv = evaluate_lcm_pum(lcm, cmv, pum_diag)
    
    # Launch decision: all FUV elements must be true
    launch = all(fuv)
    
    return {
        "cmv": cmv,
        "pum": pum,
        "fuv": fuv,
        "launch": launch
    }


def main():
    """Main entry point for CLI usage."""
    input_data = json.load(sys.stdin)
    
    result = decide(
        numpoints=input_data["numpoints"],
        x=input_data["x"],
        y=input_data["y"],
        parameters=input_data["parameters"],
        lcm=input_data["lcm"],
        pum_diag=input_data["pum_diag"]
    )
    
    print(json.dumps(result))


if __name__ == "__main__":
    import sys
    main()
