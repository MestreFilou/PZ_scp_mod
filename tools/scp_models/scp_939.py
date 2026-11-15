"""SCP-939: skinless red predator, hunched, eyeless long-jawed head, dorsal spines, clawed paws."""
import sys
import numpy as np
from core import *
import build, weights

J = build.joint
SH, EL, WR = J('Bip01_L_UpperArm'), J('Bip01_L_Forearm'), J('Bip01_L_Hand')
ARM_DIR = (WR - EL) / np.linalg.norm(WR - EL)
WRIST = EL + ARM_DIR * 0.22
HAND_DIR = np.array([0.95, -0.30, 0.0])
PALM = WRIST + HAND_DIR * 0.04
HIP, KNEE, ANK = J('Bip01_L_Thigh'), J('Bip01_L_Calf'), J('Bip01_L_Foot')
SKULL = V(0, 0.865, 0.10)
HINGE = V(0, 0.842, 0.09)
JAW_OPEN = -24


def jaw_space(p):
    return rot(p, HINGE, 'x', JAW_OPEN)


def teeth(p):
    """Distance to the fangs (upper row fixed, lower row in the open jaw)."""
    q = mirror(p)
    d = np.full(len(p), 9.0)
    for i, f in enumerate(np.linspace(0.155, 0.305, 6)):
        x = 0.040 - 0.016 * (f - 0.155) / 0.15
        ln = 0.034 if i % 2 == 0 else 0.024
        d = np.minimum(d, cone(q, V(x, 0.846, f), V(x, 0.846 - ln, f + 0.004), 0.0085, 0.0025))
    qj = mirror(jaw_space(p))
    for i, f in enumerate(np.linspace(0.165, 0.29, 5)):
        x = 0.036 - 0.014 * (f - 0.165) / 0.125
        ln = 0.030 if i % 2 == 1 else 0.022
        d = np.minimum(d, cone(qj, V(x, 0.832, f), V(x, 0.832 + ln, f + 0.003), 0.008, 0.0025))
    return d


def spines(p):
    d = np.full(len(p), 9.0)
    for y, back, ln in [(0.56, 0.085, 0.045), (0.63, 0.105, 0.06), (0.70, 0.115, 0.07), (0.77, 0.105, 0.065), (0.83, 0.075, 0.05)]:
        a = V(0, y, -back + 0.02)
        d = np.minimum(d, cone(p, a, a + np.array([0, 0.35, 1.0]) * ln, 0.017, 0.003))
    return d


def claws(q):
    d = np.full(len(q), 9.0)
    for zz, ln in [(-0.03, 0.075), (-0.01, 0.09), (0.012, 0.085), (0.032, 0.065)]:
        b0 = PALM + HAND_DIR * 0.03 + [0, 0, zz]
        b1 = b0 + (HAND_DIR + [0, -0.25, zz * 4]) * ln * 0.55
        b2 = b1 + (HAND_DIR + [0, -0.9, zz * 2]) * ln * 0.5
        d = np.minimum(d, chain(q, [b0, b1, b2], [0.013, 0.011, 0.003]))
    for xx, ln in [(-0.022, 0.05), (0.0, 0.06), (0.022, 0.05)]:                  # toes
        t0 = ANK + [xx, -0.045, -0.105]
        d = np.minimum(d, chain(q, [t0, t0 + [xx * 0.6, 0.0, -ln * 0.6], t0 + [xx * 0.8, -0.018, -ln]], [0.013, 0.011, 0.003]))
    return d


def shape(p, detail=True):
    q = mirror(p)
    # hind legs: heavy thighs, lean shanks, broad clawed feet
    l = chain(q, [HIP + [0.005, -0.01, 0], KNEE, ANK + [0, -0.02, 0]], [0.062, 0.040, 0.024])
    l = smin(l, ellipsoid(q, HIP + [0.02, -0.09, -0.02], (0.05, 0.085, 0.06)), 0.03)       # thigh muscle
    l = smin(l, ellipsoid(q, KNEE + [0, -0.07, 0.022], (0.03, 0.06, 0.035)), 0.02)          # calf muscle
    l = smin(l, ellipsoid(q, ANK + [0.0, -0.04, -0.055], (0.04, 0.024, 0.075)), 0.025)
    # body: narrow hips, deep chest pushed forward, humped back
    d = ellipsoid(p, V(0, 0.515, -0.01), (0.092, 0.06, 0.07))
    d = smin(d, cone(p, V(0, 0.53, -0.01), V(0, 0.63, 0.01), 0.062, 0.085), 0.04)
    d = smin(d, ellipsoid(p, V(0, 0.70, 0.035), (0.128, 0.115, 0.105)), 0.04)
    d = smin(d, ellipsoid(p, V(0, 0.73, -0.055), (0.10, 0.10, 0.07)), 0.04)                 # hump
    d = smin(d, ellipsoid(q, V(0.105, 0.775, -0.01), (0.055, 0.045, 0.055)), 0.03)          # shoulders
    d = smin(d, l, 0.03)
    # neck and head carried low and forward
    d = smin(d, cone(p, V(0, 0.775, 0.02), SKULL + V(0, -0.005, -0.03), 0.07, 0.058), 0.03)
    h = ellipsoid(p, SKULL, (0.064, 0.056, 0.075))
    h = smin(h, ellipsoid(p, V(0, 0.872, 0.215), (0.050, 0.030, 0.118)), 0.03)              # upper jaw
    h = smin(h, ellipsoid(q, V(0.03, 0.905, 0.10), (0.022, 0.016, 0.06)), 0.02)             # brow ridges, no eyes
    pj = jaw_space(p)
    jw = ellipsoid(pj, V(0, 0.818, 0.20), (0.043, 0.020, 0.112))
    jw = smin(jw, ellipsoid(mirror(pj), V(0.04, 0.84, 0.10), (0.022, 0.03, 0.035)), 0.02)   # jaw muscles
    h = smin(h, jw, 0.012)
    d = smin(d, h, 0.02)
    d = np.minimum(d, teeth(p))
    # arms: thick, stretched forearms, paws
    a = chain(q, [SH, EL, WRIST], [0.043, 0.031, 0.024])
    a = smin(a, ellipsoid(rot(q, (SH + EL) / 2, 'z', 6), (SH + EL) / 2 + [0, 0.012, 0], (0.06, 0.036, 0.036)), 0.02)
    a = smin(a, ellipsoid(rot(q, EL + ARM_DIR * 0.07, 'z', 8), EL + ARM_DIR * 0.07, (0.07, 0.032, 0.032)), 0.02)
    a = smin(a, ellipsoid(rot(q, PALM, 'z', -17), PALM, (0.045, 0.02, 0.042)), 0.015)
    d = smin(d, a, 0.025)
    d = smin(d, claws(q), 0.006)
    d = smin(d, spines(p), 0.012)
    if detail:
        # muscle bundles
        d = d + 0.004 * (fbm(p * np.array([3.0, 1.0, 3.0]), 22, 3, 5) - 0.5) + 0.002 * (fbm(p, 80, 2, 7) - 0.5)
    return d


def color(P, N, ao):
    q = mirror(P)
    fib = fbm(P * np.array([3.5, 0.8, 3.5]), 40, 3, 5)
    red = mix(rgb('6e100e'), rgb('b3261d'), fbm(P, 12, 3, 1) * 0.6 + 0.4 * fib)
    red = mix(red, rgb('d0564a'), 0.5 * sstep(0.62, 0.8, fib))                              # sinew highlights
    red = mix(red, rgb('3d0808'), 0.7 * sstep(0.42, 0.25, fib))                             # grooves between bundles
    back = sstep(-0.01, 0.07, P[:, 2]) * sstep(0.45, 0.6, P[:, 1])
    red = mix(red, rgb('4a0c0c'), 0.55 * back)                                              # darker back
    belly = sstep(0.0, -0.08, P[:, 2]) * sstep(0.75, 0.6, P[:, 1]) * sstep(0.45, 0.55, P[:, 1]) * sstep(0.09, 0.04, np.abs(P[:, 0]))
    red = mix(red, rgb('c9837a'), 0.45 * belly)
    bone = mix(rgb('d8cfb4'), rgb('8f8672'), fbm(P, 60, 2, 3))
    col = mix(red, bone, sstep(0.004, -0.001, teeth(P)))
    col = mix(col, mix(rgb('2a2522'), rgb('8a7f6c'), sstep(0.0, 0.05, claws_tip(q))), sstep(0.006, 0.0, claws(q)) * claw_zone(q))
    sp = spines(P)
    col = mix(col, mix(rgb('3a2f2a'), rgb('9c917b'), sstep(0.02, 0.07, P[:, 2] - 0.06 + 0.0 * sp)), sstep(0.003, -0.002, sp) * sstep(0.075, 0.10, P[:, 2] + 0.25 * np.abs(P[:, 1] - 0.70)))
    # inside of the mouth
    pj = jaw_space(P)
    inside = (-P[:, 2] > 0.11) & (np.abs(P[:, 0]) < 0.036) & (N[:, 1] < -0.2) & (P[:, 1] > 0.83) & (P[:, 1] < 0.87)
    inside |= (-pj[:, 2] > 0.11) & (np.abs(pj[:, 0]) < 0.034) & (rotn(N)[:, 1] > 0.3) & (pj[:, 1] > 0.80) & (pj[:, 1] < 0.85)
    col = np.where((inside & (teeth(P) > 0.004))[:, None], mix(rgb('2a0505'), rgb('5c1414'), fbm(P, 50, 2, 4)), col)
    light = (0.40 + 0.60 * ao) * (0.84 + 0.16 * N[:, 1])
    return col * light[:, None]


def rotn(N):
    return rot(N, np.zeros(3), 'x', JAW_OPEN)


def claws_tip(q):
    """0 at the base of a claw, growing towards the tip (rough)."""
    hand = np.linalg.norm(q - (PALM + HAND_DIR * 0.03), axis=1) - 0.03
    foot = np.linalg.norm(q - (ANK + [0, -0.045, -0.105]), axis=1) - 0.02
    return np.minimum(hand, foot)


def claw_zone(q):
    return sstep(0.0, 0.02, claws_tip(q))


def weight_fn(v):
    u = weights.unstretch_arms(v, WRIST[0])
    seg = weights.segments()
    seg['Bip01_Head'] = (J('Bip01_Head') + [0, 0.03, -0.03], SKULL + V(0, 0, 0.12), 2.2)
    W = weights.humanoid(u, 6.0, seg, scale={'Bip01_Spine1': 1.15})
    ax = np.abs(v[:, 0])
    W = weights.drop(W, ax > EL[0] + 0.04, ['Spine', 'Pelvis', 'Thigh', 'Neck', 'Head'])
    W = weights.keep_only(W, (-v[:, 2] > 0.085) & (v[:, 1] > 0.78), ['Head'])
    W = weights.keep_only(W, (v[:, 2] > 0.085) & (v[:, 1] > 0.5), ['Spine', 'Pelvis', 'Neck'])   # dorsal spines
    return W


LO, HI = (-0.66, -0.01, -0.36), (0.66, 1.0, 0.22)
if __name__ == '__main__':
    if 'clay' in sys.argv:
        build.quick('scp_939', shape, LO, HI, 0.005)
    else:
        m = build.make('scp_939', shape, LO, HI, 4200, color, weight_fn, 'SCP_939_Model', voxel=0.003)
        build.preview('scp_939', m, height=1.35)
        build.preview_pose('scp_939', m, height=1.35)
