"""SCP-049: plague doctor. Skinned robe (cape, bell sleeves, gloves, boots) + rigid hood and beak mask."""
import sys
import numpy as np
from core import *
import build, weights, body

Z0 = 0.012                     # skirt axis (a little behind the body axis, like the vanilla robe)
HC = V(0, 0.90, 0.0)           # head centre


def skirt_r(y):
    t = np.clip((0.57 - y) / 0.54, 0, 1)
    return 0.100 + 0.068 * t, 0.082 + 0.058 * t


def folds(p):
    th = np.arctan2(p[:, 2] - Z0, p[:, 0])
    t = np.clip((0.57 - p[:, 1]) / 0.54, 0, 1)
    return t * np.sin(9 * th + 2.2 * np.sin(p[:, 1] * 9) + 0.8)


def belt(p):
    return sstep(0.016, 0.011, np.abs(p[:, 1] - 0.565))


def shape(p, detail=True):
    q = mirror(p)
    rx, rz = skirt_r(p[:, 1])
    sk = (np.sqrt((p[:, 0] / rx) ** 2 + ((p[:, 2] - Z0) / rz) ** 2) - 1) * np.minimum(rx, rz)
    sk = smax(sk, p[:, 1] - 0.60, 0.03)
    sk = smax(sk, 0.022 - p[:, 1], 0.004)
    d = sk
    d = smin(d, cone(p, V(0, 0.55, -0.008), V(0, 0.65, -0.004), 0.098, 0.105), 0.03)
    d = smin(d, ellipsoid(p, V(0, 0.705, -0.002), (0.128, 0.10, 0.088)), 0.03)
    cape = ellipsoid(p, V(0, 0.750, -0.006), (0.150, 0.058, 0.106))                        # shoulder cape
    cape = smax(cape, 0.728 - p[:, 1] - 0.03 * (np.abs(p[:, 0]) / 0.17) ** 2, 0.006)        # cut flat underneath
    d = smin(d, cape, 0.012)
    d = smin(d, cone(p, V(0, 0.775, -0.012), V(0, 0.825, -0.008), 0.062, 0.058), 0.01)      # high collar
    a = chain(q, [body.SH + [0.0, -0.004, 0], body.EL, body.WR + [0.004, 0, 0]], [0.043, 0.038, 0.053])   # bell sleeves
    d = smin(d, a, 0.02)
    d = smin(d, body.hand(q, size=1.08), 0.004)                                             # gloves
    d = np.minimum(d, ellipsoid(q, body.ANK + [0.0, -0.036, -0.062], (0.040, 0.030, 0.092)))  # boots under the hem
    d = np.minimum(d, box(p, V(0.085, 0.525, 0.092), (0.026, 0.028, 0.014), 0.006))          # belt pouch
    if detail:
        d = d + 0.011 * folds(p) * (p[:, 1] < 0.58)
        d = d - 0.005 * belt(p)
        d = d + 0.002 * (fbm(p, 50, 2, 3) - 0.5)
    return d


def color(P, N, ao):
    q = mirror(P)
    cloth = mix(rgb('17161a'), rgb('2e2c33'), fbm(P, 20, 3, 1))
    cloth = mix(cloth, rgb('3a3840'), 0.5 * sstep(0.6, 0.9, vnoise(P * np.array([1, 6, 1]), 160, 4)))      # weave
    cloth = mix(cloth, rgb('0d0c0f'), 0.6 * sstep(0.15, -0.5, folds(P)) * (P[:, 1] < 0.58))               # fold shadows
    cloth = mix(cloth, rgb('4b4337'), 0.65 * sstep(0.16, 0.02, P[:, 1]) * (0.5 + 0.5 * fbm(P, 30, 2, 6)))  # dusty hem
    cape = (P[:, 1] > 0.722) & (P[:, 1] < 0.80)
    cloth = np.where(cape[:, None], cloth * 1.25 + 0.012, cloth)
    edge = sstep(0.012, 0.004, np.abs(P[:, 1] - 0.733 + 0.03 * (np.abs(P[:, 0]) / 0.17) ** 2)) * (np.abs(P[:, 0]) > 0.0)
    cloth = mix(cloth, rgb('54493a'), 0.6 * edge * (P[:, 1] < 0.76))                                       # cape trim
    col = cloth
    leather = mix(rgb('3b2a1c'), rgb('5f452c'), fbm(P, 40, 3, 8))
    col = mix(col, leather, belt(P) * (np.abs(P[:, 0]) < 0.14))
    brass = mix(rgb('8a6a2c'), rgb('d1ab55'), sstep(-0.2, 0.8, N[:, 1]))
    front = -P[:, 2] > 0.03
    buckle = (np.abs(P[:, 0]) < 0.02) & (np.abs(P[:, 1] - 0.565) < 0.018) & front
    col = np.where(buckle[:, None], brass, col)
    col = np.where(((np.abs(P[:, 0]) < 0.011) & (np.abs(P[:, 1] - 0.565) < 0.009) & front)[:, None], leather * 0.6, col)
    pouch = box(P, V(0.085, 0.525, 0.092), (0.026, 0.028, 0.014), 0.006) < 0.004
    col = np.where(pouch[:, None], leather * (0.8 + 0.2 * (P[:, 1] > 0.535)[:, None]), col)
    by = np.abs(((P[:, 1] - 0.60) / 0.034) % 1.0 - 0.5) * 0.034                                           # buttons down the front
    button = (np.sqrt(P[:, 0] ** 2 + by ** 2) < 0.0075) & front & (P[:, 1] > 0.59) & (P[:, 1] < 0.725)
    col = np.where(button[:, None], brass, col)
    col = mix(col, rgb('0a0a0c'), 0.7 * sstep(0.004, 0.0015, np.abs(P[:, 0])) * front * (P[:, 1] > 0.05) * (P[:, 1] < 0.72))  # front seam
    glove = np.abs(P[:, 0]) > body.WR[0] + 0.012
    col = np.where(glove[:, None], mix(rgb('2a1d14'), rgb('4a3524'), fbm(P, 45, 3, 9)), col)
    cuff = sstep(0.012, 0.004, np.abs(np.abs(P[:, 0]) - body.WR[0] - 0.002))
    col = mix(col, rgb('54493a'), 0.6 * cuff)
    boot = (P[:, 1] < 0.075) & (ellipsoid(q, body.ANK + [0.0, -0.036, -0.062], (0.040, 0.030, 0.092)) < 0.004)
    col = np.where(boot[:, None], mix(rgb('100e0d'), rgb('2a2420'), fbm(P, 40, 2, 3)), col)
    col = np.where((P[:, 1] < 0.024)[:, None] & ~boot[:, None], rgb('050505'), col)                        # underside
    light = (0.42 + 0.58 * ao) * (0.80 + 0.20 * N[:, 1])
    return col * light[:, None]


def weight_fn(v):
    return weights.transfer(v, 'ref_robe_weights.npz')


# ------------------------------------------------------------------ hood and beak mask (rigid, head bone)
EYE = HC + V(0.031, 0.008, 0.088)
BEAK = [HC + V(0, -0.012, 0.075), HC + V(0, -0.040, 0.165), HC + V(0, -0.098, 0.232)]


def lens(q):
    return np.linalg.norm((q - EYE) * np.array([1, 1, 0.0]), axis=1)


def hood_d(p):
    hood = ellipsoid(p, HC + V(0, 0.008, -0.012), (0.090, 0.100, 0.102))
    hood = smin(hood, cone(p, V(0, 0.795, -0.012), V(0, 0.87, -0.012), 0.072, 0.086), 0.02)
    return smin(hood, ellipsoid(p, HC + V(0, 0.03, -0.085), (0.05, 0.06, 0.05)), 0.03)        # peak at the back


def face_d(p):
    q = mirror(p)
    face = ellipsoid(p, HC + V(0, -0.012, 0.052), (0.058, 0.074, 0.052))
    ps = p.copy(); ps[:, 0] *= 1.25                                                             # beak narrower than tall
    face = smin(face, chain(ps, BEAK, [0.040, 0.026, 0.006], 0.01), 0.018)
    rim = smax(sphere(q, EYE + V(0, 0, -0.012), 0.027), -(lens(q) - 0.0155), 0.003)             # goggle rims
    return smin(face, rim, 0.004)


def mask_shape(p, detail=True):
    d = np.minimum(hood_d(p), face_d(p))
    if detail:
        d = d + 0.0015 * (fbm(p, 60, 2, 3) - 0.5)
    return d


def mask_color(P, N, ao):
    q = mirror(P)
    fwd = -(P[:, 2] - HC[2])
    is_mask = face_d(P) < hood_d(P) + 0.001
    cloth = mix(rgb('17161a'), rgb('2e2c33'), fbm(P, 20, 3, 1))
    cloth = mix(cloth, rgb('3a3840'), 0.5 * sstep(0.6, 0.9, vnoise(P * np.array([1, 6, 1]), 160, 4)))
    bone = mix(rgb('b8ad94'), rgb('e2dac6'), fbm(P, 25, 3, 5))
    bone = mix(bone, rgb('7d6f58'), 0.55 * sstep(0.55, 0.8, fbm(P, 60, 3, 7)))                  # stains
    bone = mix(bone, rgb('6a5d49'), 0.5 * (1 - ao))
    ridge = sstep(0.0035, 0.0015, np.abs(P[:, 0])) * (fwd > 0.09) * (N[:, 1] > 0.2)
    stitch = ridge * (np.sin(fwd / 0.006 * np.pi) > 0.0)
    bone = mix(bone, rgb('2a2018'), 0.9 * stitch)                                               # stitched seam on the beak
    bone = mix(bone, rgb('2a2018'), 0.55 * sstep(0.004, 0.0015, np.abs(P[:, 1] - HC[1] + 0.012 + 0.6 * (fwd - 0.075))) * (fwd > 0.10) * (np.abs(N[:, 0]) > 0.5))
    col = np.where(is_mask[:, None], bone, cloth)
    r = lens(q)
    near = fwd > 0.06
    brass = mix(rgb('5e4a22'), rgb('b8944a'), sstep(-0.3, 0.8, N[:, 1]))
    col = np.where(((r < 0.028) & near & is_mask)[:, None], brass, col)
    glass = mix(rgb('120607'), rgb('5a1210'), sstep(0.016, 0.0, r))
    hl = sstep(0.006, 0.003, np.linalg.norm((q - EYE - V(0.005, 0.006, 0)) * np.array([1, 1, 0]), axis=1))
    glass = mix(glass, rgb('e8d8c8'), 0.8 * hl)
    col = np.where(((r < 0.0165) & near)[:, None], glass, col)
    strap = (np.abs(P[:, 1] - EYE[1]) < 0.007) & ~is_mask & (fwd > -0.03)
    col = np.where(strap[:, None], mix(rgb('3b2a1c'), rgb('5f452c'), fbm(P, 40, 3, 8)), col)
    light = (0.45 + 0.55 * ao) * (0.80 + 0.20 * N[:, 1])
    return col * light[:, None]


LO, HI = (-0.56, -0.01, -0.18), (0.56, 0.86, 0.18)
MLO, MHI = (-0.115, 0.77, -0.27), (0.115, 1.03, 0.17)
if __name__ == '__main__':
    if 'clay' in sys.argv:
        build.quick('scp_049', lambda p, d=True: np.minimum(shape(p, d), mask_shape(p, d)), (-0.56, -0.01, -0.27), (0.56, 1.03, 0.18), 0.005)
    else:
        robe = build.make('scp_049_robe', shape, LO, HI, 3400, color, weight_fn, 'SCP_049_Model', voxel=0.003)
        mask = build.make('scp_049_mask', mask_shape, MLO, MHI, 1300, mask_color, None, 'SCP_049_BeakMask', voxel=0.002, res=256, static='Bip01_Head')
        mask['W'] = 'Bip01_Head'
        build.preview('scp_049', [robe, mask])
        build.preview_pose('scp_049', [robe, mask])
