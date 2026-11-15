"""SCP-173: squat concrete statue with a crudely painted face. Rigid on the pelvis bone."""
import numpy as np
from core import *
import build

HEAD = V(0, 0.845, 0.035)


def shape(p, detail=True):
    p = p.copy()
    p[:, 0] -= 0.035 * (p[:, 1] - 0.5) * (p[:, 1] > 0.5)          # leans to one side
    q = mirror(p)
    # legs: thick columns that end in blunt stumps
    d = chain(q, [V(0.072, 0.40), V(0.08, 0.20, 0.01), V(0.082, 0.06, 0.0)], [0.080, 0.064, 0.060], 0.02)
    d = smin(d, ellipsoid(q, V(0.082, 0.035, 0.03), (0.064, 0.04, 0.088)), 0.025)
    # torso: heavy, pot-bellied, hunched back
    t = ellipsoid(p, V(0, 0.53, 0.0), (0.145, 0.185, 0.118))
    t = smin(t, ellipsoid(p, V(0, 0.46, 0.04), (0.132, 0.115, 0.115)), 0.04)
    t = smin(t, ellipsoid(p, V(0, 0.65, -0.02), (0.150, 0.075, 0.095)), 0.05)
    t = smin(t, ellipsoid(p, V(0, 0.61, -0.065), (0.12, 0.11, 0.08)), 0.05)
    d = smin(d, t, 0.035)
    # stubby arms pressed against the body, reaching a little forward
    a = chain(q, [V(0.155, 0.66, -0.01), V(0.185, 0.53, 0.03), V(0.172, 0.41, 0.09)], [0.052, 0.046, 0.043], 0.02)
    d = smin(d, a, 0.04)
    # neck and oversized, tilted head
    d = smin(d, cone(p, V(0, 0.68, 0.0), V(0, 0.77, 0.02), 0.07, 0.062), 0.03)
    ph = rot(rot(p, V(0, 0.76, 0), 'z', 7), V(0, 0.76, 0), 'x', -6)
    qh = mirror(ph)
    h = ellipsoid(ph, HEAD + V(0, 0.03, -0.01), (0.118, 0.132, 0.125))
    h = smin(h, ellipsoid(ph, HEAD + V(0, -0.06, 0.03), (0.082, 0.07, 0.088)), 0.05)
    d = smin(d, h, 0.02)
    if detail:
        d = smax(d, -ellipsoid(qh, HEAD + V(0.048, 0.02, 0.118), (0.024, 0.02, 0.02)), 0.012)
        d = smax(d, -ellipsoid(ph, HEAD + V(0, -0.066, 0.112), (0.022, 0.02, 0.02)), 0.01)
        d = d + 0.007 * (fbm(p, 20, 3, 3) - 0.5) + 0.0035 * (fbm(p, 70, 2, 9) - 0.5)
        d = d + 0.004 * cracks(p, 0.10)
    return d


def cracks(p, w):
    f1, f2 = worley(p, 8, 4)
    return sstep(w, 0.0, f2 - f1) * sstep(0.45, 0.6, fbm(p, 6, 2, 17))


def face_xy(P):
    p = P.copy()
    p[:, 0] -= 0.035 * (p[:, 1] - 0.5) * (p[:, 1] > 0.5)
    ph = rot(rot(p, V(0, 0.76, 0), 'z', 7), V(0, 0.76, 0), 'x', -6)
    L = ph - HEAD
    return L[:, 0], L[:, 1], -L[:, 2]


def color(P, N, ao):
    base = mix(rgb('857a66'), rgb('b0a38c'), fbm(P, 9, 4, 1))
    base = mix(base, rgb('6f6a5f'), 0.6 * sstep(0.55, 0.8, fbm(P, 45, 3, 5)))      # darker patches
    pits = sstep(0.72, 0.8, vnoise(P, 260, 7))
    base = mix(base, rgb('4f4b44'), 0.7 * pits)
    base = mix(base, rgb('3d3a35'), 0.85 * cracks(P, 0.035))
    # water stains running down, dirt at the base
    streak = fbm(P * np.array([1, 0.12, 1]), 60, 3, 11)
    base = mix(base, rgb('5d5548'), 0.45 * sstep(0.5, 0.75, streak) * sstep(-0.3, 0.6, N[:, 1] * 0 + 0.5))
    base = mix(base, rgb('4a4338'), 0.7 * sstep(0.22, 0.0, P[:, 1]) * (0.5 + 0.5 * fbm(P, 30, 2, 2)))
    # dried blood / rust-red spray on the body
    red = sstep(0.60, 0.72, fbm(P, 7, 3, 21)) * sstep(0.74, 0.60, P[:, 1])
    drip = sstep(0.55, 0.8, fbm(P * np.array([1, 0.08, 1]), 80, 2, 31)) * sstep(0.45, 0.65, fbm(P, 5, 2, 23)) * sstep(0.74, 0.6, P[:, 1])
    base = mix(base, rgb('5e1f17'), 0.8 * np.maximum(red * (0.6 + 0.4 * vnoise(P, 120, 3)), drip))
    # hands and forearms soaked dark red
    hand = sstep(0.50, 0.40, P[:, 1]) * sstep(0.12, 0.15, np.abs(P[:, 0])) * (P[:, 1] > 0.33)
    base = mix(base, rgb('4d1611'), 0.75 * hand * (0.6 + 0.4 * fbm(P, 60, 2, 8)))

    # ---- painted face (front of the head)
    x, y, fwd = face_xy(P)
    front = sstep(0.02, 0.06, fwd) * (P[:, 1] > 0.74)
    wob = 0.012 * (fbm(P, 40, 2, 41) - 0.5)
    rough = 0.75 + 0.25 * vnoise(P, 200, 43)                                      # paint worn off in the pores
    # pale wash over the face
    face = sstep(1.0, 0.82, np.sqrt((x / 0.108) ** 2 + ((y + 0.0) / 0.125) ** 2) + wob * 6)
    base = mix(base, rgb('cfc6b2'), 0.75 * face * front * rough)
    ax = np.abs(x)
    # red blotches through the eyes, dripping down
    r = np.sqrt(((ax - 0.048) / 0.036) ** 2 + ((y - 0.022) / 0.044) ** 2) + wob * 9
    blot = sstep(1.0, 0.75, r)
    dr = sstep(0.02, 0.008, np.abs(ax - 0.05 + wob * 0.8)) * sstep(-0.10 - 0.04 * vnoise(P * np.array([1, 0, 1]), 90, 5), -0.02, y) * (y < 0.02)
    base = mix(base, rgb('8c1a12'), 0.92 * np.maximum(blot, dr) * front * rough)
    # green smear on the brow and around the mouth
    g = sstep(1.0, 0.7, np.sqrt((x / 0.040) ** 2 + ((y + 0.066) / 0.038) ** 2) + wob * 8)
    g2 = sstep(1.0, 0.6, np.sqrt(((x - 0.01) / 0.06) ** 2 + ((y - 0.085) / 0.02) ** 2) + wob * 10)
    base = mix(base, rgb('3f6b3a'), 0.85 * np.maximum(g, 0.8 * g2) * front * rough)
    # black eyes and mouth
    eye = sstep(1.0, 0.75, np.sqrt(((ax - 0.048) / 0.016) ** 2 + ((y - 0.02) / 0.012) ** 2))
    mouth = sstep(1.0, 0.8, np.sqrt((x / 0.019) ** 2 + ((y + 0.066) / 0.015) ** 2))
    base = mix(base, rgb('0c0b0a'), np.maximum(eye, mouth) * front)

    light = (0.50 + 0.50 * ao) * (0.86 + 0.14 * N[:, 1])
    return base * light[:, None]


def weights(v):
    W = np.zeros((len(v), len(build.BONES)))
    W[:, build.BONES.index('Bip01_Pelvis')] = 1
    return W


if __name__ == '__main__':
    m = build.make('scp_173', shape, (-0.30, -0.02, -0.22), (0.30, 1.06, 0.20), 2200, color, weights, 'SCP_173_Model')
    build.preview('scp_173', m)
