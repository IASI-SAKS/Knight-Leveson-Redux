import math
import sys
import json

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
    return math.sqrt((x1-x2)**2 + (y1-y2)**2)

def min_enclosing_circle_radius(x1, y1, x2, y2, x3, y3):
    d12 = distance(x1, y1, x2, y2)
    d23 = distance(x2, y2, x3, y3)
    d13 = distance(x1, y1, x3, y3)
    sides = sorted([d12, d23, d13])
    a, b, c = sides[0], sides[1], sides[2]
    if realcompare(c**2, a**2 + b**2) != "LT":
        return c / 2.0
    area = abs((x1*(y2-y3) + x2*(y3-y1) + x3*(y1-y2)) / 2.0)
    if realcompare(area, 0.0) == "EQ":
        return c / 2.0
    return (a * b * c) / (4.0 * area)

def check_angle(x1, y1, vx, vy, x2, y2, epsilon):
    if (realcompare(x1, vx) == "EQ" and realcompare(y1, vy) == "EQ") or \\
       (realcompare(x2, vx) == "EQ" and realcompare(y2, vy) == "EQ"):
        return False
    a1 = math.atan2(y1 - vy, x1 - vx)
    a2 = math.atan2(y2 - vy, x2 - vx)
    ang = a2 - a1
    while ang < 0:
        ang += 2 * math.pi
    while ang >= 2 * math.pi:
        ang -= 2 * math.pi
    
    pi = 3.1415926535
    if realcompare(ang, pi - epsilon) == "LT" or realcompare(ang, pi + epsilon) == "GT":
        return True
    return False

def get_quadrant(x, y):
    if x >= 0 and y >= 0: return 1
    if x < 0 and y >= 0: return 2
    if x <= 0 and y < 0: return 3
    if x > 0 and y < 0: return 4
    return 1

def decide(numpoints, x, y, parameters, lcm, pum_diag):
    cmv = [False] * 15
    
    # LIC 0 (Condition 1 in spec)
    length1 = parameters["LENGTH1"]
    for i in range(numpoints - 1):
        if realcompare(distance(x[i], y[i], x[i+1], y[i+1]), length1) == "GT":
            cmv[0] = True
            break
            
    # LIC 1
    radius1 = parameters["RADIUS1"]
    for i in range(numpoints - 2):
        if realcompare(min_enclosing_circle_radius(x[i], y[i], x[i+1], y[i+1], x[i+2], y[i+2]), radius1) == "GT":
            cmv[1] = True
            break
            
    # LIC 2
    epsilon = parameters["EPSILON"]
    for i in range(numpoints - 2):
        if check_angle(x[i], y[i], x[i+1], y[i+1], x[i+2], y[i+2], epsilon):
            cmv[2] = True
            break
            
    # LIC 3
    area1 = parameters["AREA1"]
    for i in range(numpoints - 2):
        p1x, p1y = x[i], y[i]
        p2x, p2y = x[i+1], y[i+1]
        p3x, p3y = x[i+2], y[i+2]
        area = abs((p1x*(p2y-p3y) + p2x*(p3y-p1y) + p3x*(p1y-p2y)) / 2.0)
        if realcompare(area, area1) == "GT":
            cmv[3] = True
            break
            
    # LIC 4
    q_pts = parameters["Q_PTS"]
    quads = parameters["QUADS"]
    if 2 <= q_pts <= numpoints:
        for i in range(numpoints - q_pts + 1):
            q_set = set()
            for j in range(i, i + q_pts):
                q_set.add(get_quadrant(x[j], y[j]))
            if len(q_set) > quads:
                cmv[4] = True
                break

    # LIC 5
    for i in range(numpoints - 1):
        if realcompare(x[i+1], x[i]) == "LT":
            cmv[5] = True
            break
            
    # LIC 6
    n_pts = parameters["N_PTS"]
    dist_param = parameters["DIST"]
    if numpoints >= 3 and 3 <= n_pts <= numpoints:
        for i in range(numpoints - n_pts + 1):
            x1, y1 = x[i], y[i]
            x2, y2 = x[i + n_pts - 1], y[i + n_pts - 1]
            is_ident = (realcompare(x1, x2) == "EQ" and realcompare(y1, y2) == "EQ")
            for j in range(i + 1, i + n_pts - 1):
                px, py = x[j], y[j]
                if is_ident:
                    d = distance(px, py, x1, y1)
                else:
                    num = abs((y2 - y1)*px - (x2 - x1)*py + x2*y1 - y2*x1)
                    den = distance(x1, y1, x2, y2)
                    d = num / den
                if realcompare(d, dist_param) == "GT":
                    cmv[6] = True
                    break
            if cmv[6]:
                break

    # LIC 7
    k_pts = parameters["K_PTS"]
    if numpoints >= 3 and 1 <= k_pts <= numpoints - 2:
        for i in range(numpoints - k_pts - 1):
            if realcompare(distance(x[i], y[i], x[i + k_pts + 1], y[i + k_pts + 1]), length1) == "GT":
                cmv[7] = True
                break
                
    # LIC 8
    a_pts = parameters["A_PTS"]
    b_pts = parameters["B_PTS"]
    if numpoints >= 5 and 1 <= a_pts and 1 <= b_pts and a_pts + b_pts <= numpoints - 3:
        for i in range(numpoints - a_pts - b_pts - 2):
            p1x, p1y = x[i], y[i]
            p2x, p2y = x[i + a_pts + 1], y[i + a_pts + 1]
            p3x, p3y = x[i + a_pts + b_pts + 2], y[i + a_pts + b_pts + 2]
            r = min_enclosing_circle_radius(p1x, p1y, p2x, p2y, p3x, p3y)
            if realcompare(r, radius1) == "GT":
                cmv[8] = True
                break
                
    # LIC 9
    c_pts = parameters["C_PTS"]
    d_pts = parameters["D_PTS"]
    if numpoints >= 5 and 1 <= c_pts and 1 <= d_pts and c_pts + d_pts <= numpoints - 3:
        for i in range(numpoints - c_pts - d_pts - 2):
            if check_angle(x[i], y[i], x[i + c_pts + 1], y[i + c_pts + 1], x[i + c_pts + d_pts + 2], y[i + c_pts + d_pts + 2], epsilon):
                cmv[9] = True
                break
                
    # LIC 10
    e_pts = parameters["E_PTS"]
    f_pts = parameters["F_PTS"]
    if numpoints >= 5 and 1 <= e_pts and 1 <= f_pts and e_pts + f_pts <= numpoints - 3:
        for i in range(numpoints - e_pts - f_pts - 2):
            p1x, p1y = x[i], y[i]
            p2x, p2y = x[i + e_pts + 1], y[i + e_pts + 1]
            p3x, p3y = x[i + e_pts + f_pts + 2], y[i + e_pts + f_pts + 2]
            area = abs((p1x*(p2y-p3y) + p2x*(p3y-p1y) + p3x*(p1y-p2y)) / 2.0)
            if realcompare(area, area1) == "GT":
                cmv[10] = True
                break
                
    # LIC 11
    g_pts = parameters["G_PTS"]
    if numpoints >= 3 and 1 <= g_pts <= numpoints - 2:
        for i in range(numpoints - g_pts - 1):
            if realcompare(x[i + g_pts + 1], x[i]) == "LT":
                cmv[11] = True
                break
                
    # LIC 12
    length2 = parameters["LENGTH2"]
    if numpoints >= 3 and 1 <= k_pts <= numpoints - 2:
        c1, c2 = False, False
        for i in range(numpoints - k_pts - 1):
            d = distance(x[i], y[i], x[i + k_pts + 1], y[i + k_pts + 1])
            if realcompare(d, length1) == "GT": c1 = True
            if realcompare(d, length2) == "LT": c2 = True
        cmv[12] = c1 and c2
        
    # LIC 13
    radius2 = parameters["RADIUS2"]
    if numpoints >= 5 and 1 <= a_pts and 1 <= b_pts and a_pts + b_pts <= numpoints - 3:
        c1, c2 = False, False
        for i in range(numpoints - a_pts - b_pts - 2):
            p1x, p1y = x[i], y[i]
            p2x, p2y = x[i + a_pts + 1], y[i + a_pts + 1]
            p3x, p3y = x[i + a_pts + b_pts + 2], y[i + a_pts + b_pts + 2]
            r = min_enclosing_circle_radius(p1x, p1y, p2x, p2y, p3x, p3y)
            if realcompare(r, radius1) == "GT": c1 = True
            if realcompare(r, radius2) != "GT": c2 = True
        cmv[13] = c1 and c2
        
    # LIC 14
    area2 = parameters["AREA2"]
    if numpoints >= 5 and 1 <= e_pts and 1 <= f_pts and e_pts + f_pts <= numpoints - 3:
        c1, c2 = False, False
        for i in range(numpoints - e_pts - f_pts - 2):
            p1x, p1y = x[i], y[i]
            p2x, p2y = x[i + e_pts + 1], y[i + e_pts + 1]
            p3x, p3y = x[i + e_pts + f_pts + 2], y[i + e_pts + f_pts + 2]
            area = abs((p1x*(p2y-p3y) + p2x*(p3y-p1y) + p3x*(p1y-p2y)) / 2.0)
            if realcompare(area, area1) == "GT": c1 = True
            if realcompare(area, area2) == "LT": c2 = True
        cmv[14] = c1 and c2

    # PUM
    pum = [[False]*15 for _ in range(15)]
    for i in range(15):
        for j in range(15):
            if i == j:
                pum[i][j] = pum_diag[i]
            elif lcm[i][j] == "NOTUSED":
                pum[i][j] = True
            elif lcm[i][j] == "ANDD":
                pum[i][j] = cmv[i] and cmv[j]
            elif lcm[i][j] == "ORR":
                pum[i][j] = cmv[i] or cmv[j]
                
    # FUV
    fuv = [False] * 15
    for i in range(15):
        if not pum_diag[i]:
            fuv[i] = True
        else:
            fuv[i] = all(pum[i])
            
    # LAUNCH
    launch = all(fuv)

    return {
        "cmv": cmv,
        "pum": pum,
        "fuv": fuv,
        "launch": launch
    }

if __name__ == "__main__":
    input_str = sys.stdin.read()
    if input_str.strip():
        data = json.loads(input_str)
        result = decide(
            data["numpoints"],
            data["x"],
            data["y"],
            data["parameters"],
            data["lcm"],
            data["pum_diag"]
        )
        print(json.dumps(result))
