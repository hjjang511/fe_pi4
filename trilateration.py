import numpy as np

def rssi_to_distance(rssi, tx_power=-59, n=2.0):
    if rssi == 0:
        return -1
    return 10 ** ((tx_power - rssi) / (10 * n))

def trilaterate(p1, d1, p2, d2, p3, d3):
    P1, P2, P3 = np.array(p1), np.array(p2), np.array(p3)

    ex = (P2 - P1) / np.linalg.norm(P2 - P1)
    i = np.dot(ex, P3 - P1)
    ey = (P3 - P1 - i * ex)
    ey = ey / np.linalg.norm(ey)
    d = np.linalg.norm(P2 - P1)
    j = np.dot(ey, P3 - P1)

    x = (d1**2 - d2**2 + d**2) / (2 * d)
    y = (d1**2 - d3**2 + i**2 + j**2 - 2 * i * x) / (2 * j)

    trilat_pos = P1 + x * ex + y * ey
    return trilat_pos[0], trilat_pos[1]
