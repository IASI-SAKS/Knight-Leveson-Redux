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

def get_dist(p1, p2):
    """Calculates Euclidean distance between two points."""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def get_area(p1, p2, p3):
    """Calculates the area of a triangle formed by three points."""
    return 0.5 * abs(p1[0]*(p2[1] - p3[1]) + p2[0]*(p3[1] - p1[1]) + p3[0]*(p1[1] - p2[1]))

def get_angle(p1, p2, p3):
    """Calculates the angle formed by three points with p2 as the vertex."""
    v1 = (p1[0] - p2[0], p1[1] - p2[1])
    v2 = (p3[0] - p2[0], p3[1] - p2[1])
    
    mag1 = math.sqrt(v1[0]**2 + v1[1]**2)
    mag2 = math.sqrt(v2[0]**2 + v2[1]**2)
    
    if realcompare(mag1, 0.0) == "EQ" or realcompare(mag2, 0.0) == "EQ":
        return None
    
    dot = v1[0]*v2[0] + v1[1]*v2[1]
    cos_theta = dot / (mag1 * mag2)
    # Clamp for numerical stability
    if cos_theta > 1.0: cos_theta = 1.0
    if cos_theta < -1.0: cos_theta = -1.0
    
    return math.acos(cos_theta)

def in_circle(p1, p2, p3, radius):
    """Checks if three points can be contained within or on a circle of a given radius."""
    a = get_dist(p1, p2)
    b = get_dist(p2, p3)
    c = get_dist(p3, p1)
    
    a2, b2, c2 = a*a, b*b, c*c
    
    # Smallest Enclosing Circle for 3 points:
    # If the triangle is obtuse or right, the smallest circle has the longest side as diameter.
    if (realcompare(a2 + b2, c2) != "GT" or 
        realcompare(b2 + c2, a2) != "GT" or 
        realcompare(c2 + a2, b2) != "GT"):
        r = max(a, b, c) / 2.0
    else:
        # If the triangle is acute, the smallest circle is the circumcircle.
        area = get_area(p1, p2, p3)
        if realcompare(area, 0.0) == "EQ":
            r = max(a, b, c) / 2.0
        else:
            r = (a * b * c) / (4.0 * area)
            
    return realcompare(r, radius) != "GT"

def get_quadrant(p):
    """Determines the quadrant of a point based on the specification's priority rules."""
    x, y = p
    if x >= 0 and y >= 0:
        return 1
    if x < 0 and y >= 0:
        return 2
    if x <= 0 and y < 0:
        return 3
    return 4

def decide(numpoints, x, y, parameters, lcm, pum_diag):
    """
    Core Launch Interceptor Program logic.
    Evaluates 15 LICs, computes CMV, PUM, FUV, and the final LAUNCH decision.
    """
    points = list(zip(x, y))
    cmv = [False] * 15
    
    # LIC 1: Consecutive points distance > LENGTH1
    for i in range(numpoints - 1):
        if realcompare(get_dist(points[i], points[i+1]), parameters['LENGTH1']) == "GT":
            cmv[0] = True
            break
            
    # LIC 2: 3 consecutive points cannot be in circle radius RADIUS1
    for i in range(numpoints - 2):
        if not in_circle(points[i], points[i+1], points[i+2], parameters['RADIUS1']):
            cmv[1] = True
            break
            
    # LIC 3: Angle at consecutive points vertex
    for i in range(numpoints - 2):
        angle = get_angle(points[i], points[i+1], points[i+2])
        if angle is not None:
            if (realcompare(angle, PI - parameters['EPSILON']) == "LT" or 
                realcompare(angle, PI + parameters['EPSILON']) == "GT"):
                cmv[2] = True
                break
                
    # LIC 4: Triangle area > AREA1
    for i in range(numpoints - 2):
        if realcompare(get_area(points[i], points[i+1], points[i+2]), parameters['AREA1']) == "GT":
            cmv[3] = True
            break
            
    # LIC 5: Q_PTS consecutive points in > QUADS quadrants
    for i in range(numpoints - parameters['Q_PTS'] + 1):
        quads = set()
        for j in range(parameters['Q_PTS']):
            quads.add(get_quadrant(points[i+j]))
        if len(quads) > parameters['QUADS']:
            cmv[4] = True
            break
            
    # LIC 6: X[i+1] - X[i] < 0
    for i in range(numpoints - 1):
        if realcompare(points[i+1][0] - points[i][0], 0.0) == "LT":
            cmv[5] = True
            break
            
    # LIC 7: N_PTS points, distance to line (first and last) > DIST
    if numpoints >= 3:
        for i in range(numpoints - parameters['N_PTS'] + 1):
            p_start = points[i]
            p_end = points[i + parameters['N_PTS'] - 1]
            for j in range(1, parameters['N_PTS'] - 1):
                p = points[i+j]
                if realcompare(p_start[0], p_end[0]) == "EQ" and realcompare(p_start[1], p_end[1]) == "EQ":
                    dist = get_dist(p, p_start)
                else:
                    x0, y0 = p
                    x1, y1 = p_start
                    x2, y2 = p_end
                    num = abs((y2-y1)*x0 - (x2-x1)*y0 + x2*y1 - y2*x1)
                    den = math.sqrt((y2-y1)**2 + (x2-x1)**2)
                    dist = num / den
                if realcompare(dist, parameters['DIST']) == "GT":
                    cmv[6] = True
                    break
            if cmv[6]: break

    # LIC 8: 2 points separated by K_PTS distance > LENGTH1
    if numpoints >= 3:
        for i in range(numpoints - parameters['K_PTS'] - 1):
            if realcompare(get_dist(points[i], points[i + parameters['K_PTS'] + 1]), parameters['LENGTH1']) == "GT":
                cmv[7] = True
                break
                
    # LIC 9: 3 points separated by A_PTS, B_PTS cannot be in circle radius RADIUS1
    if numpoints >= 5:
        for i in range(numpoints - parameters['A_PTS'] - parameters['B_PTS'] - 2):
            p1 = points[i]
            p2 = points[i + parameters['A_PTS'] + 1]
            p3 = points[i + parameters['A_PTS'] + parameters['B_PTS'] + 2]
            if not in_circle(p1, p2, p3, parameters['RADIUS1']):
                cmv[8] = True
                break
                
    # LIC 10: 3 points separated by C_PTS, D_PTS form angle
    if numpoints >= 5:
        for i in range(numpoints - parameters['C_PTS'] - parameters['D_PTS'] - 2):
            p1 = points[i]
            p2 = points[i + parameters['C_PTS'] + 1]
            p3 = points[i + parameters['C_PTS'] + parameters['D_PTS'] + 2]
            angle = get_angle(p1, p2, p3)
            if angle is not None:
                if (realcompare(angle, PI - parameters['EPSILON']) == "LT" or 
                    realcompare(angle, PI + parameters['EPSILON']) == "GT"):
                    cmv[9] = True
                    break
                    
    # LIC 11: 3 points separated by E_PTS, F_PTS area > AREA1
    if numpoints >= 5:
        for i in range(numpoints - parameters['E_PTS'] - parameters['F_PTS'] - 2):
            p1 = points[i]
            p2 = points[i + parameters['E_PTS'] + 1]
            p3 = points[i + parameters['E_PTS'] + parameters['F_PTS'] + 2]
            if realcompare(get_area(p1, p2, p3), parameters['AREA1']) == "GT":
                cmv[10] = True
                break
                
    # LIC 12: 2 points separated by G_PTS, X[j] - X[i] < 0
    if numpoints >= 3:
        for i in range(numpoints - parameters['G_PTS'] - 1):
            if realcompare(points[i + parameters['G_PTS'] + 1][0] - points[i][0], 0.0) == "LT":
                cmv[11] = True
                break
                
    # LIC 13: 2 points separated by K_PTS, dist > LENGTH1 and dist < LENGTH2
    if numpoints >= 3:
        cond1 = False
        cond2 = False
        for i in range(numpoints - parameters['K_PTS'] - 1):
            dist = get_dist(points[i], points[i + parameters['K_PTS'] + 1])
            if realcompare(dist, parameters['LENGTH1']) == "GT":
                cond1 = True
            if realcompare(dist, parameters['LENGTH2']) == "LT":
                cond2 = True
        if cond1 and cond2:
            cmv[12] = True
            
    # LIC 14: 3 points separated by A_PTS, B_PTS, circle radius RADIUS1 and RADIUS2
    if numpoints >= 5:
        cond1 = False
        cond2 = False
        for i in range(numpoints - parameters['A_PTS'] - parameters['B_PTS'] - 2):
            p1 = points[i]
            p2 = points[i + parameters['A_PTS'] + 1]
            p3 = points[i + parameters['A_PTS'] + parameters['B_PTS'] + 2]
            if not in_circle(p1, p2, p3, parameters['RADIUS1']):
                cond1 = True
            if in_circle(p1, p2, p3, parameters['RADIUS2']):
                cond2 = True
        if cond1 and cond2:
            cmv[13] = True
            
    # LIC 15: 3 points separated by E_PTS, F_PTS, area > AREA1 and area < AREA2
    if numpoints >= 5:
        cond1 = False
        cond2 = False
        for i in range(numpoints - parameters['E_PTS'] - parameters['F_PTS'] - 2):
            p1 = points[i]
            p2 = points[i + parameters['E_PTS'] + 1]
            p3 = points[i + parameters['E_PTS'] + parameters['F_PTS'] + 2]
            area = get_area(p1, p2, p3)
            if realcompare(area, parameters['AREA1']) == "GT":
                cond1 = True
            if realcompare(area, parameters['AREA2']) == "LT":
                cond2 = True
        if cond1 and cond2:
            cmv[14] = True

    # PUM calculation
    pum = [[True] * 15 for _ in range(15)]
    for i in range(15):
        for j in range(15):
            if i == j:
                pum[i][j] = pum_diag[i]
            else:
                conn = lcm[i][j]
                if conn == "NOTUSED":
                    pum[i][j] = True
                elif conn == "ANDD":
                    pum[i][j] = cmv[i] and cmv[j]
                elif conn == "ORR":
                    pum[i][j] = cmv[i] or cmv[j]
                    
    # FUV calculation
    fuv = [False] * 15
    for i in range(15):
        if not pum[i][i]:
            fuv[i] = True
        else:
            all_true = True
            for j in range(15):
                if not pum[i][j]:
                    all_true = False
                    break
            fuv[i] = all_true
            
    # Final LAUNCH decision
    launch = all(fuv)
    
    return cmv, pum, fuv, launch

if __name__ == "__main__":
    try:
        data = sys.stdin.read()
        if not data:
            sys.exit(0)
        input_data = json.loads(data)
        
        numpoints = input_data['numpoints']
        x = input_data['x']
        y = input_data['y']
        parameters = input_data['parameters']
        lcm = input_data['lcm']
        pum_diag = input_data['pum_diag']
        
        cmv, pum, fuv, launch = decide(numpoints, x, y, parameters, lcm, pum_diag)
        
        output_data = {
            "cmv": cmv,
            "pum": pum,
            "fuv": fuv,
            "launch": launch
        }
        print(json.dumps(output_data))
    except (EOFError, json.JSONDecodeError):
        pass
