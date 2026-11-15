"""SCP-106: rotting, corroded old man. Hunched, bald, sunken grinning face, skin eaten away."""
import sys
import numpy as np
from core import *
import build, weights, body


def base(p):
    return body.humanoid(p, limb=0.86, torso=0.9, belly=0.018, head_fwd=0.035, hunch=0.05, hand_size=1.12, claw=0.25)


def face(p):
    _, hc = body.humanoid(p[:1])
    L = p - hc
    return np.abs(L[:, 0]), L[:, 1], -L[:, 2], L[:, 0]


def pits(p):
    f1, f2 = worley(p, 34, 6)
    return sstep(0.38, 0.12, f1) * sstep(0.45, 0.62, fbm(p, 8, 2, 13))


def shape(p, detail=True):
    d, hc = base(p)
    q = mirror(p)
    if detail:
        d = smax(d, -ellipsoid(q, hc + V(0.027, 0.006, 0.07), (0.016, 0.012, 0.016)), 0.008)     # eye sockets
        d = smax(d, -ellipsoid(p, hc + V(0, -0.052, 0.078), (0.036, 0.008, 0.02)), 0.004)        # grin
        d = smax(d, -ellipsoid(p, hc + V(0, -0.02, 0.092), (0.008, 0.012, 0.012)), 0.005)        # rotted nose
        d = smin(d, ellipsoid(q, hc + V(0.066, -0.005, -0.005), (0.008, 0.02, 0.014)), 0.006)    # ears
        d = d + 0.0045 * (fbm(p, 26, 3, 3) - 0.5)                                                 # sagging, lumpy skin
        d = d + 0.006 * pits(p)                                                                   # corrosion holes
        drip = sstep(0.55, 0.8, fbm(p * np.array([1, 0.1, 1]), 55, 2, 21))
        d = d - 0.003 * drip                                                                      # running sludge
    return d


def color(P, N, ao):
    n = fbm(P, 16, 4, 1)
    col = mix(rgb('1c1714'), rgb('4a3b2e'), n)                                    # near-black brown skin
    col = mix(col, rgb('5d4a35'), 0.5 * sstep(0.55, 0.8, fbm(P, 40, 3, 5)))       # leathery lighter patches
    col = mix(col, rgb('2f3a2a'), 0.35 * sstep(0.55, 0.75, fbm(P, 9, 3, 15)))     # greenish rot
    pt = pits(P)
    col = mix(col, rgb('0a0807'), 0.9 * pt)                                       # corrosion holes
    col = mix(col, rgb('6b2a1c'), 0.5 * sstep(0.15, 0.5, pt) * sstep(0.9, 0.5, pt))   # raw rims
    drip = sstep(0.55, 0.8, fbm(P * np.array([1, 0.1, 1]), 55, 2, 21))
    col = mix(col, rgb('0b0a09'), 0.75 * drip)                                    # black sludge running down
    low = sstep(0.30, 0.0, P[:, 1])
    hands = sstep(body.WR[0] - 0.02, body.WR[0] + 0.05, np.abs(P[:, 0]))
    col = mix(col, rgb('080707'), 0.8 * np.maximum(low, hands) * (0.6 + 0.4 * fbm(P, 30, 2, 2)))
    # wet highlights
    gl = sstep(0.72, 0.85, fbm(P, 70, 2, 9)) * sstep(0.2, 0.7, N[:, 1])
    col = mix(col, rgb('8d8a80'), 0.35 * gl)
    # face
    x, y, fwd, sx = face(P)
    fr = fwd > 0.03
    eye = np.sqrt(((x - 0.027) / 0.016) ** 2 + ((y - 0.006) / 0.012) ** 2)
    col = mix(col, rgb('050404'), sstep(1.25, 0.8, eye) * fr)
    col = mix(col, rgb('d6d2c4'), sstep(0.35, 0.2, eye) * fr)                     # pale pinpoint eyes
    mouth = np.sqrt((sx / 0.038) ** 2 + ((y + 0.052 - 0.006 * (x / 0.038) ** 2) / 0.010) ** 2)
    col = mix(col, rgb('070505'), sstep(1.15, 0.9, mouth) * fr)
    teeth = sstep(0.95, 0.8, mouth) * (np.sin(sx / 0.0052 * np.pi) > -0.35) * (np.abs(y + 0.052 - 0.006 * (x / 0.038) ** 2) < 0.0065)
    col = mix(col, rgb('b9ad84'), 0.95 * teeth * fr)                              # yellow grin
    col = mix(col, rgb('050404'), sstep(1.0, 0.6, np.sqrt((sx / 0.008) ** 2 + ((y + 0.02) / 0.012) ** 2)) * fr)
    light = (0.45 + 0.55 * ao) * (0.82 + 0.18 * N[:, 1])
    return col * light[:, None]


def weight_fn(v):
    W = weights.humanoid(v, 6.0)
    W = weights.keep_only(W, v[:, 1] > 0.87, ['Head', 'Neck'])
    return W


LO, HI = (-0.56, -0.01, -0.17), (0.56, 1.0, 0.16)
if __name__ == '__main__':
    if 'clay' in sys.argv:
        build.quick('scp_106', shape, LO, HI, 0.005)
    else:
        m = build.make('scp_106', shape, LO, HI, 3600, color, weight_fn, 'SCP_106_Model', voxel=0.003)
        build.preview('scp_106', m)
        build.preview_pose('scp_106', m)
