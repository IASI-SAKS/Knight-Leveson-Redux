
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

def dist_sq(p1, p2):
    return (p1[0] - p2[0])**2 + (p1[1] - p2[1])**2

def dist(p1, p2):
    return math.sqrt(dist_sq(p1, p2))

def lic1(points, parameters):
    length1 = parameters['LENGTH1']
    for i in range(len(points) - 1):
        if realcompare(dist(points[i], points[i+1]), length1) == "GT":
            return True
    return False

def lic2(points, parameters):
    radius1 = parameters['RADIUS1']
    if len(points) < 3:
        return False
    for i in range(len(points) - 2):
        p1, p2, p3 = points[i], points[i+1], points[i+2]
        
        d12 = dist(p1, p2)
        d13 = dist(p1, p3)
        d23 = dist(p2, p3)

        if realcompare(d12, 2 * radius1) == "GT" or \\
           realcompare(d13, 2 * radius1) == "GT" or \\
           realcompare(d23, 2 * radius1) == "GT":
            return True
        
        # Check if circumradius > radius1
        # Avoid colinear points
        # Using twice the area formula: area = |x1(y2 \u2212 y3) + x2(y3 \u2212 y1) + x3(y1 \u2212 y2)|
        twice_area = abs(p1[0] * (p2[1] - p3[1]) + p2[0] * (p3[1] - p1[1]) + p3[0] * (p1[1] - p2[1]))
        if realcompare(twice_area, 0) == "EQ":
            continue
        
        circum_diameter = (d12 * d13 * d23) / twice_area
        
        if realcompare(circum_diameter/2, radius1) == "GT":
            return True
    return False

def lic3(points, parameters):
    epsilon = parameters['EPSILON']
    if len(points) < 3:
        return False
    for i in range(len(points) - 2):
        p1, p2, p3 = points[i], points[i+1], points[i+2]

        if p1 == p2 or p3 == p2:
            continue
        
        v1 = (p1[0] - p2[0], p1[1] - p2[1])
        v2 = (p3[0] - p2[0], p3[1] - p2[1])

        dot_product = v1[0] * v2[0] + v1[1] * v2[1]
        mag_v1 = math.sqrt(v1[0]**2 + v1[1]**2)
        mag_v2 = math.sqrt(v2[0]**2 + v2[1]**2)

        angle = math.acos(dot_product / (mag_v1 * mag_v2))

        if realcompare(angle, PI - epsilon) == "LT" or realcompare(angle, PI + epsilon) == "GT":
            return True
    return False

def lic4(points, parameters):
    area1 = parameters['AREA1']
    if len(points) < 3:
        return False
    for i in range(len(points) - 2):
        p1, p2, p3 = points[i], points[i+1], points[i+2]
        area = 0.5 * abs(p1[0]*(p2[1]-p3[1]) + p2[0]*(p3[1]-p1[1]) + p3[0]*(p1[1]-p2[1]))
        if realcompare(area, area1) == "GT":
            return True
    return False

def get_quadrant(point):
    x, y = point
    if x >= 0 and y >= 0: return 1
    if x < 0 and y >= 0: return 2
    if x < 0 and y < 0: return 3
    if x >= 0 and y < 0: return 4
    return 1 # Should not be reached based on spec

def lic5(points, parameters):
    q_pts = parameters['Q_PTS']
    quads = parameters['QUADS']
    numpoints = len(points)
    if numpoints < q_pts:
        return False
        
    for i in range(numpoints - q_pts + 1):
        quadrant_set = set()
        for j in range(q_pts):
            quadrant_set.add(get_quadrant(points[i+j]))
        if len(quadrant_set) > quads:
            return True
    return False
    
def lic6(points, parameters):
    for i in range(len(points) - 1):
        if realcompare(points[i+1][0], points[i][0]) == "LT":
            return True
    return False

def lic7(points, parameters):
    n_pts = parameters['N_PTS']
    dist_param = parameters['DIST']
    numpoints = len(points)

    if numpoints < 3 or numpoints < n_pts:
        return False

    for i in range(numpoints - n_pts + 1):
        p_start = points[i]
        p_end = points[i + n_pts - 1]

        for j in range(i + 1, i + n_pts - 1):
            p_check = points[j]
            if p_start == p_end:
                d = dist(p_start, p_check)
            else:
                numerator = abs((p_end[1] - p_start[1]) * p_check[0] - (p_end[0] - p_start[0]) * p_check[1] + p_end[0] * p_start[1] - p_end[1] * p_start[0])
                denominator = dist(p_start, p_end)
                d = numerator / denominator
            
            if realcompare(d, dist_param) == "GT":
                return True
    return False

def lic8(points, parameters):
    k_pts = parameters['K_PTS']
    length1 = parameters['LENGTH1']
    numpoints = len(points)

    if numpoints < 3 or not (1 <= k_pts <= numpoints - 2):
        return False
        
    for i in range(numpoints - k_pts - 1):
        if realcompare(dist(points[i], points[i+k_pts+1]), length1) == "GT":
            return True
    return False

def lic9(points, parameters):
    a_pts = parameters['A_PTS']
    b_pts = parameters['B_PTS']
    radius1 = parameters['RADIUS1']
    numpoints = len(points)

    if numpoints < 5 or not (a_pts >= 1 and b_pts >= 1 and a_pts + b_pts <= numpoints - 3):
        return False

    for i in range(numpoints - a_pts - b_pts - 2):
        p1 = points[i]
        p2 = points[i + a_pts + 1]
        p3 = points[i + a_pts + b_pts + 2]

        d12 = dist(p1, p2)
        d13 = dist(p1, p3)
        d23 = dist(p2, p3)

        if realcompare(d12, 2 * radius1) == "GT" or \\
           realcompare(d13, 2 * radius1) == "GT" or \\
           realcompare(d23, 2 * radius1) == "GT":
            return True
            
        twice_area = abs(p1[0] * (p2[1] - p3[1]) + p2[0] * (p3[1] - p1[1]) + p3[0] * (p1[1] - p2[1]))
        if realcompare(twice_area, 0) == "EQ":
            continue

        circum_diameter = (d12 * d13 * d23) / twice_area
        if realcompare(circum_diameter/2, radius1) == "GT":
            return True

    return False

def lic10(points, parameters):
    c_pts = parameters['C_PTS']
    d_pts = parameters['D_PTS']
    epsilon = parameters['EPSILON']
    numpoints = len(points)

    if numpoints < 5 or not (c_pts >= 1 and d_pts >= 1 and c_pts + d_pts <= numpoints - 3):
        return False

    for i in range(numpoints - c_pts - d_pts - 2):
        p1 = points[i]
        p2 = points[i + c_pts + 1]
        p3 = points[i + c_pts + d_pts + 2]

        if p1 == p2 or p3 == p2:
            continue

        v1 = (p1[0] - p2[0], p1[1] - p2[1])
        v2 = (p3[0] - p2[0], p3[1] - p2[1])

        dot_product = v1[0] * v2[0] + v1[1] * v2[1]
        mag_v1 = math.sqrt(v1[0]**2 + v1[1]**2)
        mag_v2 = math.sqrt(v2[0]**2 + v2[1]**2)

        angle = math.acos(dot_product / (mag_v1 * mag_v2))

        if realcompare(angle, PI - epsilon) == "LT" or realcompare(angle, PI + epsilon) == "GT":
            return True
            
    return False

def lic11(points, parameters):
    e_pts = parameters['E_PTS']
    f_pts = parameters['F_PTS']
    area1 = parameters['AREA1']
    numpoints = len(points)

    if numpoints < 5 or not (e_pts >= 1 and f_pts >= 1 and e_pts + f_pts <= numpoints - 3):
        return False

    for i in range(numpoints - e_pts - f_pts - 2):
        p1 = points[i]
        p2 = points[i + e_pts + 1]
        p3 = points[i + e_pts + f_pts + 2]

        area = 0.5 * abs(p1[0]*(p2[1]-p3[1]) + p2[0]*(p3[1]-p1[1]) + p3[0]*(p1[1]-p2[1]))
        if realcompare(area, area1) == "GT":
            return True
    return False

def lic12(points, parameters):
    g_pts = parameters['G_PTS']
    numpoints = len(points)

    if numpoints < 3 or not (1 <= g_pts <= numpoints - 2):
        return False

    for i in range(numpoints - g_pts - 1):
        j = i + g_pts + 1
        if realcompare(points[j][0], points[i][0]) == "LT":
            return True
    return False

def lic13(points, parameters):
    k_pts = parameters['K_PTS']
    length1 = parameters['LENGTH1']
    length2 = parameters['LENGTH2']
    numpoints = len(points)

    if numpoints < 3:
        return False

    cond1_met = False
    cond2_met = False
    for i in range(numpoints - k_pts - 1):
        d = dist(points[i], points[i+k_pts+1])
        if realcompare(d, length1) == "GT":
            cond1_met = True
        if realcompare(d, length2) == "LT":
            cond2_met = True
    
    return cond1_met and cond2_met

def lic14(points, parameters):
    a_pts = parameters['A_PTS']
    b_pts = parameters['B_PTS']
    radius1 = parameters['RADIUS1']
    radius2 = parameters['RADIUS2']
    numpoints = len(points)

    if numpoints < 5:
        return False

    cond1_met = False
    cond2_met = False
    for i in range(numpoints - a_pts - b_pts - 2):
        p1 = points[i]
        p2 = points[i + a_pts + 1]
        p3 = points[i + a_pts + b_pts + 2]

        d12 = dist(p1, p2)
        d13 = dist(p1, p3)
        d23 = dist(p2, p3)

        cannot_be_contained = False
        if realcompare(d12, 2 * radius1) == "GT" or \\
           realcompare(d13, 2 * radius1) == "GT" or \\
           realcompare(d23, 2 * radius1) == "GT":
            cannot_be_contained = True
        else:
            twice_area = abs(p1[0] * (p2[1] - p3[1]) + p2[0] * (p3[1] - p1[1]) + p3[0] * (p1[1] - p2[1]))
            if realcompare(twice_area, 0) != "EQ":
                circum_diameter = (d12 * d13 * d23) / twice_area
                if realcompare(circum_diameter/2, radius1) == "GT":
                    cannot_be_contained = True
        
        if cannot_be_contained:
            cond1_met = True

        can_be_contained = False
        
        twice_area = abs(p1[0] * (p2[1] - p3[1]) + p2[0] * (p3[1] - p1[1]) + p3[0] * (p1[1] - p2[1]))
        if realcompare(twice_area, 0) == "EQ": # Collinear
            max_dist = max(d12, d13, d23)
            if realcompare(max_dist, 2 * radius2) != "GT":
                can_be_contained = True
        else: # Not collinear
            if realcompare(d12, 2 * radius2) != "GT" and \\
               realcompare(d13, 2 * radius2) != "GT" and \\
               realcompare(d23, 2 * radius2) != "GT":
                circum_diameter = (d12 * d13 * d23) / twice_area
                if realcompare(circum_diameter/2, radius2) != "GT":
                    can_be_contained = True
        
        if can_be_contained:
            cond2_met = True
    
    return cond1_met and cond2_met

def lic15(points, parameters):
    e_pts = parameters['E_PTS']
    f_pts = parameters['F_PTS']
    area1 = parameters['AREA1']
    area2 = parameters['AREA2']
    numpoints = len(points)
    
    if numpoints < 5:
        return False

    cond1_met = False
    cond2_met = False
    for i in range(numpoints - e_pts - f_pts - 2):
        p1 = points[i]
        p2 = points[i + e_pts + 1]
        p3 = points[i + e_pts + f_pts + 2]
        
        area = 0.5 * abs(p1[0]*(p2[1]-p3[1]) + p2[0]*(p3[1]-p1[1]) + p3[0]*(p1[1]-p2[1]))

        if realcompare(area, area1) == "GT":
            cond1_met = True
        if realcompare(area, area2) == "LT":
            cond2_met = True
            
    return cond1_met and cond2_met


def decide(numpoints, x, y, parameters, lcm, pum_diag):
    points = list(zip(x,y))

    cmv = [
        lic1(points, parameters),
        lic2(points, parameters),
        lic3(points, parameters),
        lic4(points, parameters),
        lic5(points, parameters),
        lic6(points, parameters),
        lic7(points, parameters),
        lic8(points, parameters),
        lic9(points, parameters),
        lic10(points, parameters),
        lic11(points, parameters),
        lic12(points, parameters),
        lic13(points, parameters),
        lic14(points, parameters),
        lic15(points, parameters),
    ]

    pum = [[False for _ in range(15)] for _ in range(15)]
    for i in range(15):
        for j in range(i, 15):
            if i == j:
                pum[i][j] = pum_diag[i]
                continue
            
            op = lcm[i][j]
            result = False
            if op == "NOTUSED":
                result = True
            elif op == "ANDD":
                result = cmv[i] and cmv[j]
            elif op == "ORR":
                result = cmv[i] or cmv[j]
            
            pum[i][j] = result
            pum[j][i] = result

    fuv = [False for _ in range(15)]
    for i in range(15):
        if not pum[i][i]:
            fuv[i] = True
        else:
            if all(pum[i]):
                fuv[i] = True

    launch = all(fuv)

    return cmv, pum, fuv, launch

if __name__ == "__main__":
    input_data = json.load(sys.stdin)
    
    cmv, pum, fuv, launch = decide(
        input_data['numpoints'],
        input_data['x'],
        input_data['y'],
        input_data['parameters'],
        input_data['lcm'],
        input_data['pum_diag']
    )

    output = {
        "cmv": cmv,
        "pum": pum,
        "fuv": fuv,
        "launch": launch
    }
    
    json.dump(output, sys.stdout)
