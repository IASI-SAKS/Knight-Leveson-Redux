import json
import math
import sys

PI = 3.1415926535


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


def _dist(x1, y1, x2, y2):
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def _triangle_area(x1, y1, x2, y2, x3, y3):
    return 0.5 * abs(x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))


def _smallest_enclosing_circle_radius(x1, y1, x2, y2, x3, y3):
    d12 = _dist(x1, y1, x2, y2)
    d23 = _dist(x2, y2, x3, y3)
    d13 = _dist(x1, y1, x3, y3)
    max_d = max(d12, d23, d13)
    if max_d == 0:
        return 0.0
    area = _triangle_area(x1, y1, x2, y2, x3, y3)
    if area == 0:
        return max_d / 2.0
    circumradius = (d12 * d23 * d13) / (4.0 * area)
    sides = sorted([d12, d23, d13])
    a, b, c = sides[0], sides[1], sides[2]
    if a * a + b * b <= c * c:
        return c / 2.0
    else:
        return circumradius


def _compute_angle(x1, y1, x2, y2, x3, y3):
    dx1 = x1 - x2
    dy1 = y1 - y2
    dx3 = x3 - x2
    dy3 = y3 - y2
    len1 = math.sqrt(dx1 * dx1 + dy1 * dy1)
    len3 = math.sqrt(dx3 * dx3 + dy3 * dy3)
    if len1 == 0 or len3 == 0:
        return None
    cos_angle = (dx1 * dx3 + dy1 * dy3) / (len1 * len3)
    cos_angle = max(-1.0, min(1.0, cos_angle))
    return math.acos(cos_angle)


def _point_to_line_distance(px, py, x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    length = math.sqrt(dx * dx + dy * dy)
    if length == 0:
        return _dist(px, py, x1, y1)
    return abs(dx * (py - y1) - dy * (px - x1)) / length


def _quadrant(x, y):
    if y >= 0:
        if x >= 0:
            return 1
        else:
            return 2
    else:
        if x <= 0:
            return 3
        else:
            return 4


def decide(numpoints, x, y, parameters, lcm, pum_diag):
    LENGTH1 = parameters['LENGTH1']
    RADIUS1 = parameters['RADIUS1']
    EPSILON = parameters['EPSILON']
    AREA1 = parameters['AREA1']
    Q_PTS = parameters['Q_PTS']
    QUADS = parameters['QUADS']
    DIST_PARAM = parameters['DIST']
    N_PTS = parameters['N_PTS']
    K_PTS = parameters['K_PTS']
    A_PTS = parameters['A_PTS']
    B_PTS = parameters['B_PTS']
    C_PTS = parameters['C_PTS']
    D_PTS = parameters['D_PTS']
    E_PTS = parameters['E_PTS']
    F_PTS = parameters['F_PTS']
    G_PTS = parameters['G_PTS']
    LENGTH2 = parameters['LENGTH2']
    RADIUS2 = parameters['RADIUS2']
    AREA2 = parameters['AREA2']

    cmv = [False] * 15

    # LIC 1
    for i in range(numpoints - 1):
        d = _dist(x[i], y[i], x[i + 1], y[i + 1])
        if realcompare(d, LENGTH1) == 'GT':
            cmv[0] = True
            break

    # LIC 2
    for i in range(numpoints - 2):
        r = _smallest_enclosing_circle_radius(x[i], y[i], x[i + 1], y[i + 1], x[i + 2], y[i + 2])
        if realcompare(r, RADIUS1) == 'GT':
            cmv[1] = True
            break

    # LIC 3
    for i in range(numpoints - 2):
        angle = _compute_angle(x[i], y[i], x[i + 1], y[i + 1], x[i + 2], y[i + 2])
        if angle is not None:
            if realcompare(angle, PI - EPSILON) == 'LT' or realcompare(angle, PI + EPSILON) == 'GT':
                cmv[2] = True
                break

    # LIC 4
    for i in range(numpoints - 2):
        area = _triangle_area(x[i], y[i], x[i + 1], y[i + 1], x[i + 2], y[i + 2])
        if realcompare(area, AREA1) == 'GT':
            cmv[3] = True
            break

    # LIC 5
    for i in range(numpoints - Q_PTS + 1):
        quads = set()
        for j in range(i, i + Q_PTS):
            quads.add(_quadrant(x[j], y[j]))
        if len(quads) > QUADS:
            cmv[4] = True
            break

    # LIC 6
    for i in range(numpoints - 1):
        if realcompare(x[i + 1] - x[i], 0.0) == 'LT':
            cmv[5] = True
            break

    # LIC 7
    if numpoints >= 3:
        for i in range(numpoints - N_PTS + 1):
            first_x, first_y = x[i], y[i]
            last_x, last_y = x[i + N_PTS - 1], y[i + N_PTS - 1]
            found = False
            for j in range(i + 1, i + N_PTS - 1):
                d = _point_to_line_distance(x[j], y[j], first_x, first_y, last_x, last_y)
                if realcompare(d, DIST_PARAM) == 'GT':
                    found = True
                    break
            if found:
                cmv[6] = True
                break

    # LIC 8
    if numpoints >= 3:
        for i in range(numpoints - K_PTS - 1):
            j = i + K_PTS + 1
            d = _dist(x[i], y[i], x[j], y[j])
            if realcompare(d, LENGTH1) == 'GT':
                cmv[7] = True
                break

    # LIC 9
    if numpoints >= 5:
        for i in range(numpoints - A_PTS - B_PTS - 2):
            j = i + A_PTS + 1
            k = j + B_PTS + 1
            r = _smallest_enclosing_circle_radius(x[i], y[i], x[j], y[j], x[k], y[k])
            if realcompare(r, RADIUS1) == 'GT':
                cmv[8] = True
                break

    # LIC 10
    if numpoints >= 5:
        for i in range(numpoints - C_PTS - D_PTS - 2):
            j = i + C_PTS + 1
            k = j + D_PTS + 1
            angle = _compute_angle(x[i], y[i], x[j], y[j], x[k], y[k])
            if angle is not None:
                if realcompare(angle, PI - EPSILON) == 'LT' or realcompare(angle, PI + EPSILON) == 'GT':
                    cmv[9] = True
                    break

    # LIC 11
    if numpoints >= 5:
        for i in range(numpoints - E_PTS - F_PTS - 2):
            j = i + E_PTS + 1
            k = j + F_PTS + 1
            area = _triangle_area(x[i], y[i], x[j], y[j], x[k], y[k])
            if realcompare(area, AREA1) == 'GT':
                cmv[10] = True
                break

    # LIC 12
    if numpoints >= 3:
        for i in range(numpoints - G_PTS - 1):
            j = i + G_PTS + 1
            if realcompare(x[j] - x[i], 0.0) == 'LT':
                cmv[11] = True
                break

    # LIC 13
    if numpoints >= 3:
        part_a = False
        part_b = False
        for i in range(numpoints - K_PTS - 1):
            j = i + K_PTS + 1
            d = _dist(x[i], y[i], x[j], y[j])
            if realcompare(d, LENGTH1) == 'GT':
                part_a = True
            if realcompare(d, LENGTH2) == 'LT':
                part_b = True
        if part_a and part_b:
            cmv[12] = True

    # LIC 14
    if numpoints >= 5:
        part_a = False
        part_b = False
        for i in range(numpoints - A_PTS - B_PTS - 2):
            j = i + A_PTS + 1
            k = j + B_PTS + 1
            r = _smallest_enclosing_circle_radius(x[i], y[i], x[j], y[j], x[k], y[k])
            if realcompare(r, RADIUS1) == 'GT':
                part_a = True
            if realcompare(r, RADIUS2) != 'GT':
                part_b = True
        if part_a and part_b:
            cmv[13] = True

    # LIC 15
    if numpoints >= 5:
        part_a = False
        part_b = False
        for i in range(numpoints - E_PTS - F_PTS - 2):
            j = i + E_PTS + 1
            k = j + F_PTS + 1
            area = _triangle_area(x[i], y[i], x[j], y[j], x[k], y[k])
            if realcompare(area, AREA1) == 'GT':
                part_a = True
            if realcompare(area, AREA2) == 'LT':
                part_b = True
        if part_a and part_b:
            cmv[14] = True

    # PUM
    pum = [[False] * 15 for _ in range(15)]
    for i in range(15):
        for j in range(15):
            if i == j:
                pum[i][j] = pum_diag[i]
            else:
                connector = lcm[i][j]
                if connector == 'NOTUSED':
                    pum[i][j] = True
                elif connector == 'ANDD':
                    pum[i][j] = cmv[i] and cmv[j]
                elif connector == 'ORR':
                    pum[i][j] = cmv[i] or cmv[j]

    # FUV
    fuv = [False] * 15
    for i in range(15):
        if not pum[i][i]:
            fuv[i] = True
        else:
            fuv[i] = all(pum[i][j] for j in range(15))

    # LAUNCH
    launch = all(fuv)

    return cmv, pum, fuv, launch


def main():
    data = json.load(sys.stdin)
    numpoints = data['numpoints']
    x = data['x']
    y = data['y']
    parameters = data['parameters']
    lcm = data['lcm']
    pum_diag = data['pum_diag']

    cmv, pum, fuv, launch = decide(numpoints, x, y, parameters, lcm, pum_diag)

    result = {
        'cmv': cmv,
        'pum': pum,
        'fuv': fuv,
        'launch': launch
    }

    print(json.dumps(result))


if __name__ == '__main__':
    main()
