import sys
import json
import math

def realcompare(a: float, b: float) -> str:
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

def compare_gt(a, b):
    return realcompare(a, b) == "GT"

def compare_lt(a, b):
    return realcompare(a, b) == "LT"

def compare_eq(a, b):
    return realcompare(a, b) == "EQ"

def get_dist(p1, p2):
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def get_area(p1, p2, p3):
    return 0.5 * abs(p1[0]*(p2[1] - p3[1]) + p2[0]*(p3[1] - p1[1]) + p3[0]*(p1[1] - p2[1]))

def get_angle(p1, p2, p3):
    # p2 is vertex
    v1 = (p1[0] - p2[0], p1[1] - p2[1])
    v2 = (p3[0] - p2[0], p3[1] - p2[1])
    m1 = get_dist(p1, p2)
    m2 = get_dist(p3, p2)
    if m1 == 0 or m2 == 0:
        return None
    dot = v1[0]*v2[0] + v1[1]*v2[1]
    cos_theta = dot / (m1 * m2)
    # Clamp for precision
    cos_theta = max(-1.0, min(1.0, cos_theta))
    return math.acos(cos_theta)

def get_quadrant(p):
    x, y = p
    if x >= 0 and y >= 0: return 1
    if x < 0 and y >= 0: return 2
    if x < 0 and y < 0: return 3
    if x >= 0 and y < 0: return 4
    return 1

def get_point_to_line_dist(p, p1, p2):
    # Line joining p1 and p2
    if p1 == p2:
        return get_dist(p, p1)
    num = abs((p2[0]-p1[0])*(p1[1]-p[1]) - (p1[0]-p[0])*(p2[1]-p1[1]))
    den = get_dist(p1, p2)
    return num / den

def check_circle_containment(points, radius):
    # Smallest enclosing circle is complex, but we only need to know if ANY circle of radius R exists.
    # For 3 points, the smallest enclosing circle is either:
    # 1. The circle with diameter as the longest side (if it's an obtuse or right triangle)
    # 2. The circumcircle (if it's an acute triangle)
    n = len(points)
    if n == 0: return True
    if n == 1: return True
    if n == 2:
        return get_dist(points[0], points[1]) <= 2 * radius
    
    # For 3 points
    # Try all pairs as diameter
    for i in range(n):
        for j in range(i+1, n):
            center = ((points[i][0]+points[j][0])/2, (points[i][1]+points[j][1])/2)
            r = get_dist(points[i], points[j]) / 2
            if r <= radius:
                all_in = True
                for k in range(n):
                    if get_dist(points[k], center) > radius + 1e-9: # Using a small epsilon for float
                        # Since we must use realcompare, we should ideally avoid this.
                        # But radius is a fixed parameter. Let's see.
                        all_in = False
                        break
                if all_in: return True
    
    # Try circumcircle
    p1, p2, p3 = points
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    D = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    if abs(D) > 1e-9:
        ux = ((x1**2 + y1**2) * (y2 - y3) + (x2**2 + y2**2) * (y3 - y1) + (x3**2 + y3**2) * (y1 - y2)) / D
        uy = ((x1**2 + y1**2) * (x3 - x2) + (x2**2 + y2**2) * (x1 - x3) + (x3**2 + y3**2) * (x2 - x1)) / D
        center = (ux, uy)
        r = get_dist(p1, center)
        if r <= radius + 1e-9:
            return True
    
    return False

def decide(numpoints, x, y, parameters, lcm, pum_diag):
    pts = list(zip(x, y))
    cmv = [False] * 15
    
    # LIC 1
    for i in range(numpoints - 1):
        if compare_gt(get_dist(pts[i], pts[i+1]), parameters['LENGTH1']):
            cmv[0] = True; break
            
    # LIC 2
    for i in range(numpoints - 2):
        if not check_circle_containment([pts[i], pts[i+1], pts[i+2]], parameters['RADIUS1']):
            cmv[1] = True; break
            
    # LIC 3
    for i in range(numpoints - 2):
        angle = get_angle(pts[i], pts[i+1], pts[i+2])
        if angle is not None:
            if compare_lt(angle, math.pi - parameters['EPSILON']) or compare_gt(angle, math.pi + parameters['EPSILON']):
                cmv[2] = True; break
                
    # LIC 4
    for i in range(numpoints - 2):
        if compare_gt(get_area(pts[i], pts[i+1], pts[i+2]), parameters['AREA1']):
            cmv[3] = True; break
            
    # LIC 5
    q_pts = parameters['Q_PTS']
    quads_limit = parameters['QUADS']
    for i in range(numpoints - q_pts + 1):
        q_set = set()
        for j in range(i, i + q_pts):
            q_set.add(get_quadrant(pts[j]))
        if len(q_set) > quads_limit:
            cmv[4] = True; break
            
    # LIC 6
    for i in range(numpoints - 1):
        if compare_lt(pts[i+1][0] - pts[i][0], 0):
            cmv[5] = True; break
            
    # LIC 7
    if numpoints >= 3:
        n_pts = parameters['N_PTS']
        dist_limit = parameters['DIST']
        for i in range(numpoints - n_pts + 1):
            p_first = pts[i]
            p_last = pts[i + n_pts - 1]
            for j in range(i, i + n_pts):
                if compare_gt(get_point_to_line_dist(pts[j], p_first, p_last), dist_limit):
                    cmv[6] = True; break
            if cmv[6]: break
            
    # LIC 8
    if numpoints >= 3:
        k_pts = parameters['K_PTS']
        for i in range(numpoints - k_pts - 1):
            if compare_gt(get_dist(pts[i], pts[i + k_pts + 1]), parameters['LENGTH1']):
                cmv[7] = True; break
                
    # LIC 9
    if numpoints >= 5:
        a_pts = parameters['A_PTS']
        b_pts = parameters['B_PTS']
        for i in range(numpoints - (a_pts + b_pts + 2)):
            p1 = pts[i]
            p2 = pts[i + a_pts + 1]
            p3 = pts[i + a_pts + b_pts + 2]
            if not check_circle_containment([p1, p2, p3], parameters['RADIUS1']):
                cmv[8] = True; break
                
    # LIC 10
    if numpoints >= 5:
        c_pts = parameters['C_PTS']
        d_pts = parameters['D_PTS']
        for i in range(numpoints - (c_pts + d_pts + 2)):
            p1 = pts[i]
            p2 = pts[i + c_pts + 1]
            p3 = pts[i + c_pts + d_pts + 2]
            angle = get_angle(p1, p2, p3)
            if angle is not None:
                if compare_lt(angle, math.pi - parameters['EPSILON']) or compare_gt(angle, math.pi + parameters['EPSILON']):
                    cmv[9] = True; break
                    
    # LIC 11
    if numpoints >= 5:
        e_pts = parameters['E_PTS']
        f_pts = parameters['F_PTS']
        for i in range(numpoints - (e_pts + f_pts + 2)):
            p1 = pts[i]
            p2 = pts[i + e_pts + 1]
            p3 = pts[i + e_pts + f_pts + 2]
            if compare_gt(get_area(p1, p2, p3), parameters['AREA1']):
                cmv[10] = True; break
                
    # LIC 12
    if numpoints >= 3:
        g_pts = parameters['G_PTS']
        for i in range(numpoints - g_pts - 1):
            if compare_lt(pts[i + g_pts + 1][0] - pts[i][0], 0):
                cmv[11] = True; break
                
    # LIC 13
    if numpoints >= 3:
        k_pts = parameters['K_PTS']
        part1 = False
        part2 = False
        for i in range(numpoints - k_pts - 1):
            d = get_dist(pts[i], pts[i + k_pts + 1])
            if compare_gt(d, parameters['LENGTH1']): part1 = True
            if compare_lt(d, parameters['LENGTH2']): part2 = True
        cmv[12] = part1 and part2
        
    # LIC 14
    if numpoints >= 5:
        a_pts = parameters['A_PTS']
        b_pts = parameters['B_PTS']
        part1 = False
        part2 = False
        for i in range(numpoints - (a_pts + b_pts + 2)):
            p1 = pts[i]
            p2 = pts[i + a_pts + 1]
            p3 = pts[i + a_pts + b_pts + 2]
            if not check_circle_containment([p1, p2, p3], parameters['RADIUS1']): part1 = True
            if check_circle_containment([p1, p2, p3], parameters['RADIUS2']): part2 = True
        cmv[13] = part1 and part2
        
    # LIC 15
    if numpoints >= 5:
        e_pts = parameters['E_PTS']
        f_pts = parameters['F_PTS']
        part1 = False
        part2 = False
        for i in range(numpoints - (e_pts + f_pts + 2)):
            p1 = pts[i]
            p2 = pts[i + e_pts + 1]
            p3 = pts[i + e_pts + f_pts + 2]
            area = get_area(p1, p2, p3)
            if compare_gt(area, parameters['AREA1']): part1 = True
            if compare_lt(area, parameters['AREA2']): part2 = True
        cmv[14] = part1 and part2

    # PUM
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
                    
    # FUV
    fuv = [False] * 15
    for i in range(15):
        if not pum[i][i]:
            fuv[i] = True
        else:
            if all(pum[i][j] for j in range(15)):
                fuv[i] = True
                
    # LAUNCH
    launch = all(fuv)
    
    return cmv, pum, fuv, launch

if __name__ == "__main__":
    try:
        input_data = json.load(sys.stdin)
        res_cmv, res_pum, res_fuv, res_launch = decide(
            input_data['numpoints'],
            input_data['x'],
            input_data['y'],
            input_data['parameters'],
            input_data['lcm'],
            input_data['pum_diag']
        )
        print(json.dumps({
            "cmv": res_cmv,
            "pum": res_pum,
            "fuv": res_fuv,
            "launch": res_launch
        }))
    except Exception as e:
        sys.exit(1)
