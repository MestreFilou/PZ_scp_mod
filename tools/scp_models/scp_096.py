"""SCP-096: tall, emaciated, very long arms, unhinged jaw. Full skeleton."""
import numpy as np
from core import *
import build, weights

J = build.joint
SH, EL, WR = J('Bip01_L_UpperArm'), J('Bip01_L_Forearm'), J('Bip01_L_Hand')
ARM_DIR = (WR - EL) / np.linalg.norm(WR - EL)
WRIST = EL + ARM_DIR * 0.27           # end of the stretched forearm (the real wrist joint is at 0.137)
HAND_DIR = np.array([0.94, -0.33, 0.0])
PALM = WRIST + HAND_DIR * 0.035
HIP, KNEE, ANK = J('Bip01_L_Thigh'), J('Bip01_L_Calf'), J('Bip01_L_Foot')
HEAD = V(0, 0.945, 0.035)
MOUTH = HEAD + V(0, -0.075, 0.05)


def ribs(p):
    """Groove pattern of the rib cage: 1 on a rib, 0 between ribs (masked to the chest)."""
    ax = np.abs(p[:, 0])
    ph = (p[:, 1] + 0.45 * ax - 0.25 * np.clip(ax - 0.05, 0, 1)) / 0.026 * 2 * np.pi
    m = sstep(0.585, 0.62, p[:, 1]) * sstep(0.765, 0.735, p[:, 1]) * sstep(0.008, 0.02, ax) * sstep(0.115, 0.095, ax)
    return (0.5 + 0.5 * np.sin(ph)), m


def shape(p, detail=True):
    q = mirror(p)
    # pelvis and sunken waist
    d = ellipsoid(p, V(0, 0.508, -0.005), (0.07, 0.04, 0.046))
    d = smin(d, ellipsoid(q, V(0.062, 0.525, 0.005), (0.026, 0.03, 0.036)), 0.02)       # hip bones
    d = smin(d, cone(p, V(0, 0.52, -0.012), V(0, 0.62, -0.01), 0.040, 0.046), 0.03)
    # rib cage, narrow shoulders
    d = smin(d, ellipsoid(p, V(0, 0.685, -0.005), (0.092, 0.105, 0.064)), 0.03)
    d = smin(d, cone(q, V(0.0, 0.775, -0.02), SH + [0.01, 0.005, 0], 0.024, 0.026), 0.02)  # collar bone to shoulder knob
    # neck craned forward, long skull
    d = smin(d, chain(p, [V(0, 0.775, -0.03), V(0, 0.85, -0.005), V(0, 0.90, 0.015)], [0.028, 0.022, 0.024]), 0.02)
    h = ellipsoid(p, HEAD + V(0, 0.012, -0.02), (0.058, 0.07, 0.076))
    h = smin(h, ellipsoid(q, HEAD + V(0.034, -0.02, 0.04), (0.022, 0.02, 0.026)), 0.02)   # cheek bones
    jaw = ellipsoid(p, HEAD + V(0, -0.09, 0.03), (0.04, 0.05, 0.045))                     # jaw dropped far down
    h = smin(h, jaw, 0.03)
    h = smax(h, -ellipsoid(p, MOUTH, (0.029, 0.052, 0.05)), 0.008)                         # gaping mouth
    h = smax(h, -ellipsoid(q, HEAD + V(0.025, 0.0, 0.06), (0.010, 0.008, 0.012)), 0.005)  # eye sockets
    d = smin(d, h, 0.012)
    # arms: thin, forearm stretched well past the real wrist
    a = chain(q, [SH, EL, WRIST], [0.024, 0.017, 0.013])
    a = smin(a, sphere(q, EL, 0.021), 0.01)
    a = smin(a, ellipsoid(rot(q, PALM, 'z', -19), PALM, (0.036, 0.011, 0.026)), 0.012)
    for k, (zz, ln, dy) in enumerate([(-0.026, 0.115, 0.0), (-0.009, 0.135, 0.004), (0.009, 0.128, 0.0), (0.026, 0.10, -0.006)]):
        b0 = PALM + HAND_DIR * 0.028 + [0, dy, zz]
        b1 = b0 + (HAND_DIR + [0, -0.12, zz * 5]) * ln * 0.55
        b2 = b1 + (HAND_DIR + [0, -0.55, zz * 3]) * ln * 0.45
        a = smin(a, chain(q, [b0, b1, b2], [0.0085, 0.0075, 0.005]), 0.006)
    t0 = PALM + [-0.005, 0, -0.026]
    a = smin(a, chain(q, [t0, t0 + [0.03, -0.012, -0.035], t0 + [0.065, -0.035, -0.045]], [0.009, 0.008, 0.005]), 0.006)
    d = smin(d, a, 0.015)
    # legs: bony, big knees, long feet
    l = chain(q, [HIP + [0, -0.01, 0], KNEE, ANK + [0, -0.03, 0]], [0.032, 0.022, 0.016])
    l = smin(l, sphere(q, KNEE + [0, 0, -0.008], 0.027), 0.012)
    l = smin(l, ellipsoid(q, ANK + [0.004, -0.043, -0.055], (0.028, 0.018, 0.078)), 0.02)
    d = smin(d, l, 0.02)
    if detail:
        r, m = ribs(p)
        d = d - 0.0045 * (r - 0.5) * m
        back = sstep(0.0, 0.03, p[:, 2]) * sstep(0.016, 0.004, np.abs(p[:, 0])) * sstep(0.50, 0.55, p[:, 1]) * sstep(0.80, 0.76, p[:, 1])
        d = d - 0.005 * back * (0.5 + 0.5 * np.sin(p[:, 1] / 0.022 * 2 * np.pi))          # vertebrae
        d = d + 0.002 * (fbm(p, 60, 2, 3) - 0.5)
    return d


def color(P, N, ao):
    skin = mix(rgb('cfc9c0'), rgb('e6e1d8'), fbm(P, 14, 4, 1))
    skin = mix(skin, rgb('a9a6ad'), 0.45 * sstep(0.5, 0.75, fbm(P, 30, 3, 5)))           # bluish mottling
    veins = sstep(0.05, 0.0, np.abs(fbm(P, 28, 3, 9) - 0.5))
    skin = mix(skin, rgb('8f93a6'), 0.13 * veins)
    r, m = ribs(P)
    skin = mix(skin, rgb('7d7873'), 0.55 * m * sstep(0.55, 0.1, r))                       # shadows between ribs
    back = sstep(0.0, 0.03, P[:, 2]) * sstep(0.02, 0.004, np.abs(P[:, 0])) * sstep(0.50, 0.55, P[:, 1]) * sstep(0.80, 0.76, P[:, 1])
    skin = mix(skin, rgb('8a847e'), 0.45 * back * sstep(0.6, 0.1, 0.5 + 0.5 * np.sin(P[:, 1] / 0.022 * 2 * np.pi)))
    # grime on feet, knees, hands
    q = mirror(P)
    skin = mix(skin, rgb('6e6459'), 0.55 * sstep(0.10, 0.0, P[:, 1]) * (0.5 + 0.5 * fbm(P, 50, 2, 2)))
    hand = sstep(WRIST[0] + 0.05, WRIST[0] + 0.15, q[:, 0])
    skin = mix(skin, rgb('8f8880'), 0.5 * sstep(WRIST[0] - 0.02, WRIST[0] + 0.05, q[:, 0]))
    skin = mix(skin, rgb('4a100e'), 0.8 * hand * sstep(0.3, 0.55, fbm(P, 45, 3, 12) + 0.4 * hand))   # blood on the hands
    # face
    L = P - HEAD
    x, y, fwd = np.abs(L[:, 0]), L[:, 1], -L[:, 2]
    inm = ellipsoid(P, MOUTH, (0.033, 0.056, 0.054))
    skin = mix(skin, rgb('6a1512'), 0.35 * sstep(0.012, 0.002, inm) * (P[:, 1] > 0.82) * (fwd > 0.0) * sstep(0.4, 0.6, fbm(P, 60, 2, 7) + 0.2))
    skin = mix(skin, rgb('1a0606'), sstep(0.004, -0.004, inm))                            # inside of the mouth
    teeth = sstep(0.0, -0.003, inm) * sstep(-0.012, -0.004, inm) * (fwd > 0.045) * (np.sin(L[:, 0] / 0.0075 * np.pi) > -0.2) * ((np.abs(y + 0.075) > 0.036))
    skin = mix(skin, rgb('d9d2b8'), 0.9 * teeth)
    eye = np.sqrt((x - 0.025) ** 2 + (y - 0.0) ** 2)
    skin = mix(skin, rgb('2b2326'), sstep(0.013, 0.008, eye) * (fwd > 0.03))
    skin = mix(skin, rgb('f4f1ea'), sstep(0.0055, 0.0035, eye) * (fwd > 0.03))             # blank white eyes
    light = (0.42 + 0.58 * ao) * (0.84 + 0.16 * N[:, 1])
    return skin * light[:, None]


def weight_fn(v):
    # undo the arm stretch so each part gets the weights of the bone it stands for
    u = v.copy()
    ax = np.abs(u[:, 0])
    long_end = WRIST[0]
    fore = (ax > EL[0]) & (ax <= long_end)
    hand = ax > long_end
    nx = ax.copy()
    nx[fore] = EL[0] + (ax[fore] - EL[0]) * (WR[0] - EL[0]) / (long_end - EL[0])
    nx[hand] = WR[0] + (ax[hand] - long_end) * 0.7
    u[:, 0] = np.sign(u[:, 0]) * nx
    seg = weights.segments()
    seg['Bip01_Head'] = (J('Bip01_Head') + [0, 0.05, -0.02], HEAD + [0, 0.03, 0], 2.0)
    seg['Bip01_Neck'] = (J('Bip01_Neck'), J('Bip01_Head') + [0, 0.03, -0.01], 0.8)
    W = weights.humanoid(u, 6.0, seg)
    arm = (ax > EL[0] + 0.04)
    for b in ('Spine', 'Spine1', 'Pelvis', 'L_Thigh', 'R_Thigh', 'Neck', 'Head'):
        W[arm, build.BONES.index('Bip01_' + b)] = 0
    hd = v[:, 1] > 0.86
    for b in build.BONES:
        if 'Head' not in b and 'Neck' not in b:
            W[hd, build.BONES.index(b)] = 0
    return W / W.sum(1, keepdims=True)


if __name__ == '__main__':
    m = build.make('scp_096', shape, (-0.70, -0.01, -0.16), (0.70, 1.05, 0.12), 3600, color, weight_fn, 'SCP_096_Model', voxel=0.003)
    build.preview('scp_096', m, height=1.45, center=(0, 0, 0.52))
    build.preview_pose('scp_096', m, height=1.45, center=(0, 0, 0.52))
