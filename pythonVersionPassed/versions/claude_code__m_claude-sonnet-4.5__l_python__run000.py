#!/usr/bin/env python3
"""
Launch Interceptor Program - DECIDE
Implementation according to Knight & Leveson (1986) specification.
"""

import sys
import json
import math


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


def distance(x1, y1, x2, y2):
    """Compute Euclidean distance between two points."""
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)


def triangle_area(x1, y1, x2, y2, x3, y3):
    """Compute area of triangle using cross product formula."""
    return abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)) / 2.0


def angle_at_vertex(x1, y1, x_vertex, y_vertex, x3, y3):
    """
    Compute angle at vertex formed by three points.
    Returns None if the angle is undefined (first or last point coincides with vertex).
    """
    # Check if first or last point coincides with vertex
    if (x1 == x_vertex and y1 == y_vertex) or (x3 == x_vertex and y3 == y_vertex):
        return None

    # Compute vectors from vertex to first and third points
    v1_x = x1 - x_vertex
    v1_y = y1 - y_vertex
    v2_x = x3 - x_vertex
    v2_y = y3 - y_vertex

    # Compute dot product and magnitudes
    dot_product = v1_x * v2_x + v1_y * v2_y
    mag1 = math.sqrt(v1_x**2 + v1_y**2)
    mag2 = math.sqrt(v2_x**2 + v2_y**2)

    # Avoid division by zero
    if mag1 == 0 or mag2 == 0:
        return None

    # Compute angle using arccos
    cos_angle = dot_product / (mag1 * mag2)
    # Clamp to [-1, 1] to avoid numerical errors
    cos_angle = max(-1.0, min(1.0, cos_angle))
    angle = math.acos(cos_angle)

    return angle


def smallest_enclosing_circle_radius(x1, y1, x2, y2, x3, y3):
    """
    Compute radius of smallest circle that can contain three points.
    """
    # Check if all three points are identical
    if x1 == x2 == x3 and y1 == y2 == y3:
        return 0.0

    # Compute distances between all pairs
    d12 = distance(x1, y1, x2, y2)
    d23 = distance(x2, y2, x3, y3)
    d13 = distance(x1, y1, x3, y3)

    # Check if any two points are identical
    if d12 == 0:
        return max(d13, d23) / 2.0
    if d23 == 0:
        return max(d12, d13) / 2.0
    if d13 == 0:
        return max(d12, d23) / 2.0

    # The smallest enclosing circle is either:
    # 1. Circle with diameter as one of the sides (if triangle is obtuse or right)
    # 2. Circumcircle of the triangle (if triangle is acute)

    # Check if triangle is obtuse by checking if any angle is > 90 degrees
    # Using dot product: if dot product is negative, angle is obtuse

    # Angle at point 1
    v1_x = x2 - x1
    v1_y = y2 - y1
    v2_x = x3 - x1
    v2_y = y3 - y1
    if v1_x * v2_x + v1_y * v2_y < 0:
        return d23 / 2.0

    # Angle at point 2
    v1_x = x1 - x2
    v1_y = y1 - y2
    v2_x = x3 - x2
    v2_y = y3 - y2
    if v1_x * v2_x + v1_y * v2_y < 0:
        return d13 / 2.0

    # Angle at point 3
    v1_x = x1 - x3
    v1_y = y1 - y3
    v2_x = x2 - x3
    v2_y = y2 - y3
    if v1_x * v2_x + v1_y * v2_y < 0:
        return d12 / 2.0

    # All angles are acute, so use circumradius formula
    # R = (a * b * c) / (4 * Area)
    area = triangle_area(x1, y1, x2, y2, x3, y3)
    if area == 0:
        # Points are collinear
        return max(d12, d23, d13) / 2.0

    radius = (d12 * d23 * d13) / (4.0 * area)
    return radius


def point_to_line_distance(px, py, x1, y1, x2, y2):
    """
    Compute distance from point (px, py) to line segment from (x1, y1) to (x2, y2).
    If the line endpoints are identical, return distance to that point.
    """
    if x1 == x2 and y1 == y2:
        return distance(px, py, x1, y1)

    # Distance from point to line (not segment)
    # Using formula: |ax + by + c| / sqrt(a^2 + b^2)
    # Line equation: (y2-y1)x - (x2-x1)y + (x2-x1)y1 - (y2-y1)x1 = 0
    numerator = abs((y2 - y1) * px - (x2 - x1) * py + x2 * y1 - y2 * x1)
    denominator = math.sqrt((y2 - y1)**2 + (x2 - x1)**2)
    return numerator / denominator


def get_quadrant(x, y):
    """
    Get quadrant number (1-4) for a point.
    Priority: I, II, III, IV for ambiguous cases.
    """
    if x >= 0 and y >= 0:
        return 1
    elif x < 0 and y >= 0:
        return 2
    elif x < 0 and y < 0:
        return 3
    else:  # x >= 0 and y < 0
        return 4


def lic1(numpoints, x, y, length1):
    """
    LIC 1: There exists at least one set of two consecutive data points
    that are a distance greater than LENGTH1 apart.
    """
    for i in range(numpoints - 1):
        dist = distance(x[i], y[i], x[i + 1], y[i + 1])
        if realcompare(dist, length1) == "GT":
            return True
    return False


def lic2(numpoints, x, y, radius1):
    """
    LIC 2: There exists at least one set of three consecutive data points
    that cannot all be contained within or on a circle of radius RADIUS1.
    """
    for i in range(numpoints - 2):
        radius = smallest_enclosing_circle_radius(x[i], y[i], x[i + 1], y[i + 1], x[i + 2], y[i + 2])
        if realcompare(radius, radius1) == "GT":
            return True
    return False


def lic3(numpoints, x, y, epsilon):
    """
    LIC 3: There exists at least one set of three consecutive data points
    which form an angle such that: angle < (PI - EPSILON) or angle > (PI + EPSILON).
    """
    for i in range(numpoints - 2):
        angle = angle_at_vertex(x[i], y[i], x[i + 1], y[i + 1], x[i + 2], y[i + 2])
        if angle is not None:
            if realcompare(angle, PI - epsilon) == "LT" or realcompare(angle, PI + epsilon) == "GT":
                return True
    return False


def lic4(numpoints, x, y, area1):
    """
    LIC 4: There exists at least one set of three consecutive data points
    that are the vertices of a triangle with area greater than AREA1.
    """
    for i in range(numpoints - 2):
        area = triangle_area(x[i], y[i], x[i + 1], y[i + 1], x[i + 2], y[i + 2])
        if realcompare(area, area1) == "GT":
            return True
    return False


def lic5(numpoints, x, y, q_pts, quads):
    """
    LIC 5: There exists at least one set of Q_PTS consecutive data points
    that lie in more than QUADS quadrants.
    """
    for i in range(numpoints - q_pts + 1):
        quadrants = set()
        for j in range(i, i + q_pts):
            quadrants.add(get_quadrant(x[j], y[j]))
        if len(quadrants) > quads:
            return True
    return False


def lic6(numpoints, x, y):
    """
    LIC 6: There exists at least one set of two consecutive data points
    (X[i], Y[i]) and (X[j], Y[j]) such that X[j] - X[i] < 0 (where i = j - 1).
    """
    for i in range(numpoints - 1):
        if realcompare(x[i + 1], x[i]) == "LT":
            return True
    return False


def lic7(numpoints, x, y, n_pts, dist):
    """
    LIC 7: There exists at least one set of N_PTS consecutive data points
    such that at least one of the points lies a distance greater than DIST
    from the line joining the first and last of these N_PTS points.
    """
    if numpoints < 3:
        return False

    for i in range(numpoints - n_pts + 1):
        x_first = x[i]
        y_first = y[i]
        x_last = x[i + n_pts - 1]
        y_last = y[i + n_pts - 1]

        # Check all points in between
        for j in range(i, i + n_pts):
            d = point_to_line_distance(x[j], y[j], x_first, y_first, x_last, y_last)
            if realcompare(d, dist) == "GT":
                return True

    return False


def lic8(numpoints, x, y, k_pts, length1):
    """
    LIC 8: There exists at least one set of two data points separated by
    exactly K_PTS consecutive intervening points that are a distance greater
    than LENGTH1 apart.
    """
    if numpoints < 3:
        return False

    for i in range(numpoints - k_pts - 1):
        j = i + k_pts + 1
        dist = distance(x[i], y[i], x[j], y[j])
        if realcompare(dist, length1) == "GT":
            return True
    return False


def lic9(numpoints, x, y, a_pts, b_pts, radius1):
    """
    LIC 9: There exists at least one set of three data points separated by
    exactly A_PTS and B_PTS consecutive intervening points that cannot be
    contained within or on a circle of radius RADIUS1.
    """
    if numpoints < 5:
        return False

    for i in range(numpoints - a_pts - b_pts - 2):
        j = i + a_pts + 1
        k = j + b_pts + 1
        if k < numpoints:
            radius = smallest_enclosing_circle_radius(x[i], y[i], x[j], y[j], x[k], y[k])
            if realcompare(radius, radius1) == "GT":
                return True
    return False


def lic10(numpoints, x, y, c_pts, d_pts, epsilon):
    """
    LIC 10: There exists at least one set of three data points separated by
    exactly C_PTS and D_PTS consecutive intervening points that form an angle
    such that: angle < (PI - EPSILON) or angle > (PI + EPSILON).
    """
    if numpoints < 5:
        return False

    for i in range(numpoints - c_pts - d_pts - 2):
        j = i + c_pts + 1
        k = j + d_pts + 1
        if k < numpoints:
            angle = angle_at_vertex(x[i], y[i], x[j], y[j], x[k], y[k])
            if angle is not None:
                if realcompare(angle, PI - epsilon) == "LT" or realcompare(angle, PI + epsilon) == "GT":
                    return True
    return False


def lic11(numpoints, x, y, e_pts, f_pts, area1):
    """
    LIC 11: There exists at least one set of three data points separated by
    exactly E_PTS and F_PTS consecutive intervening points that are the vertices
    of a triangle with area greater than AREA1.
    """
    if numpoints < 5:
        return False

    for i in range(numpoints - e_pts - f_pts - 2):
        j = i + e_pts + 1
        k = j + f_pts + 1
        if k < numpoints:
            area = triangle_area(x[i], y[i], x[j], y[j], x[k], y[k])
            if realcompare(area, area1) == "GT":
                return True
    return False


def lic12(numpoints, x, y, g_pts):
    """
    LIC 12: There exists at least one set of two data points separated by
    exactly G_PTS consecutive intervening points such that X[j] - X[i] < 0.
    """
    if numpoints < 3:
        return False

    for i in range(numpoints - g_pts - 1):
        j = i + g_pts + 1
        if realcompare(x[j], x[i]) == "LT":
            return True
    return False


def lic13(numpoints, x, y, k_pts, length1, length2):
    """
    LIC 13: There exists at least one set of two data points separated by
    exactly K_PTS consecutive intervening points which are a distance greater
    than LENGTH1 apart. In addition, there exists at least one set of two data
    points separated by exactly K_PTS consecutive intervening points that are
    a distance less than LENGTH2 apart. Both parts must be true.
    """
    if numpoints < 3:
        return False

    condition1 = False
    condition2 = False

    for i in range(numpoints - k_pts - 1):
        j = i + k_pts + 1
        dist = distance(x[i], y[i], x[j], y[j])
        if realcompare(dist, length1) == "GT":
            condition1 = True
        if realcompare(dist, length2) == "LT":
            condition2 = True
        if condition1 and condition2:
            return True

    return False


def lic14(numpoints, x, y, a_pts, b_pts, radius1, radius2):
    """
    LIC 14: There exists at least one set of three data points separated by
    exactly A_PTS and B_PTS consecutive intervening points that cannot be
    contained within or on a circle of radius RADIUS1. In addition, there
    exists at least one set of three data points separated by exactly A_PTS
    and B_PTS consecutive intervening points that can be contained in or on
    a circle of radius RADIUS2. Both parts must be true.
    """
    if numpoints < 5:
        return False

    condition1 = False
    condition2 = False

    for i in range(numpoints - a_pts - b_pts - 2):
        j = i + a_pts + 1
        k = j + b_pts + 1
        if k < numpoints:
            radius = smallest_enclosing_circle_radius(x[i], y[i], x[j], y[j], x[k], y[k])
            if realcompare(radius, radius1) == "GT":
                condition1 = True
            if realcompare(radius, radius2) == "LT" or realcompare(radius, radius2) == "EQ":
                condition2 = True
            if condition1 and condition2:
                return True

    return False


def lic15(numpoints, x, y, e_pts, f_pts, area1, area2):
    """
    LIC 15: There exists at least one set of three data points separated by
    exactly E_PTS and F_PTS consecutive intervening points that are the vertices
    of a triangle with area greater than AREA1. In addition, there exist three
    data points separated by exactly E_PTS and F_PTS consecutive intervening
    points that are the vertices of a triangle with area less than AREA2.
    Both parts must be true.
    """
    if numpoints < 5:
        return False

    condition1 = False
    condition2 = False

    for i in range(numpoints - e_pts - f_pts - 2):
        j = i + e_pts + 1
        k = j + f_pts + 1
        if k < numpoints:
            area = triangle_area(x[i], y[i], x[j], y[j], x[k], y[k])
            if realcompare(area, area1) == "GT":
                condition1 = True
            if realcompare(area, area2) == "LT":
                condition2 = True
            if condition1 and condition2:
                return True

    return False


def compute_cmv(numpoints, x, y, parameters):
    """
    Compute the Conditions Met Vector (CMV) for all 15 LICs.
    Returns a list of 15 boolean values.
    """
    cmv = [False] * 15

    cmv[0] = lic1(numpoints, x, y, parameters['LENGTH1'])
    cmv[1] = lic2(numpoints, x, y, parameters['RADIUS1'])
    cmv[2] = lic3(numpoints, x, y, parameters['EPSILON'])
    cmv[3] = lic4(numpoints, x, y, parameters['AREA1'])
    cmv[4] = lic5(numpoints, x, y, parameters['Q_PTS'], parameters['QUADS'])
    cmv[5] = lic6(numpoints, x, y)
    cmv[6] = lic7(numpoints, x, y, parameters['N_PTS'], parameters['DIST'])
    cmv[7] = lic8(numpoints, x, y, parameters['K_PTS'], parameters['LENGTH1'])
    cmv[8] = lic9(numpoints, x, y, parameters['A_PTS'], parameters['B_PTS'], parameters['RADIUS1'])
    cmv[9] = lic10(numpoints, x, y, parameters['C_PTS'], parameters['D_PTS'], parameters['EPSILON'])
    cmv[10] = lic11(numpoints, x, y, parameters['E_PTS'], parameters['F_PTS'], parameters['AREA1'])
    cmv[11] = lic12(numpoints, x, y, parameters['G_PTS'])
    cmv[12] = lic13(numpoints, x, y, parameters['K_PTS'], parameters['LENGTH1'], parameters['LENGTH2'])
    cmv[13] = lic14(numpoints, x, y, parameters['A_PTS'], parameters['B_PTS'], parameters['RADIUS1'], parameters['RADIUS2'])
    cmv[14] = lic15(numpoints, x, y, parameters['E_PTS'], parameters['F_PTS'], parameters['AREA1'], parameters['AREA2'])

    return cmv


def compute_pum(cmv, lcm, pum_diag):
    """
    Compute the Preliminary Unlocking Matrix (PUM) from CMV and LCM.
    Returns a 15x15 matrix of boolean values.
    """
    pum = [[False] * 15 for _ in range(15)]

    # Set diagonal elements from input
    for i in range(15):
        pum[i][i] = pum_diag[i]

    # Compute off-diagonal elements
    for i in range(15):
        for j in range(15):
            if i != j:
                connector = lcm[i][j]
                if connector == "NOTUSED":
                    pum[i][j] = True
                elif connector == "ANDD":
                    pum[i][j] = cmv[i] and cmv[j]
                elif connector == "ORR":
                    pum[i][j] = cmv[i] or cmv[j]

    return pum


def compute_fuv(pum):
    """
    Compute the Final Unlocking Vector (FUV) from PUM.
    FUV[i] is True if PUM[i][i] is False OR all elements in PUM row i are True.
    Returns a list of 15 boolean values.
    """
    fuv = [False] * 15

    for i in range(15):
        if not pum[i][i]:
            fuv[i] = True
        else:
            # Check if all elements in row i are True
            fuv[i] = all(pum[i][j] for j in range(15))

    return fuv


def compute_launch(fuv):
    """
    Compute the final launch decision from FUV.
    LAUNCH is True if all elements of FUV are True.
    """
    return all(fuv)


def decide(numpoints, x, y, parameters, lcm, pum_diag):
    """
    Main DECIDE function that computes CMV, PUM, FUV, and LAUNCH decision.

    Args:
        numpoints: Number of data points (2-100)
        x: List of x-coordinates
        y: List of y-coordinates
        parameters: Dict of parameters for LICs
        lcm: 15x15 Logical Connector Matrix
        pum_diag: List of 15 boolean values for PUM diagonal

    Returns:
        Tuple of (cmv, pum, fuv, launch)
    """
    cmv = compute_cmv(numpoints, x, y, parameters)
    pum = compute_pum(cmv, lcm, pum_diag)
    fuv = compute_fuv(pum)
    launch = compute_launch(fuv)

    return cmv, pum, fuv, launch


def main():
    """
    Main function that reads JSON from stdin and writes JSON to stdout.
    """
    # Read input from stdin
    input_data = json.load(sys.stdin)

    # Extract input parameters
    numpoints = input_data['numpoints']
    x = input_data['x']
    y = input_data['y']
    parameters = input_data['parameters']
    lcm = input_data['lcm']
    pum_diag = input_data['pum_diag']

    # Run DECIDE
    cmv, pum, fuv, launch = decide(numpoints, x, y, parameters, lcm, pum_diag)

    # Create output
    output = {
        'cmv': cmv,
        'pum': pum,
        'fuv': fuv,
        'launch': launch
    }

    # Write output to stdout
    json.dump(output, sys.stdout)
    sys.stdout.write('\
')


if __name__ == '__main__':
    main()
