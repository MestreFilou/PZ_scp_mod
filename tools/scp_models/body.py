"""Parametric human-like body that follows the joints of the bind pose (T-pose)."""
import numpy as np
from core import *
import build

J = build.joint
SH, EL, WR, FI = J('Bip01_L_UpperArm'), J('Bip01_L_Forearm'), J('Bip01_L_Hand'), J('Bip01_L_Finger1')
HIP, KNEE, ANK = J('Bip01_L_Thigh'), J('Bip01_L_Calf'), J('Bip01_L_Foot')
HAND_DIR = (FI - WR) / np.linalg.norm(FI - WR)


def hand(q, wrist=WR, direction=HAND_DIR, size=1.0, claw=0.0):
    """Palm, four fingers and a thumb. claw > 0 lengthens and sharpens the fingers."""
    palm = wrist + direction * 0.035 * size
    d = ellipsoid(rot(q, palm, 'z', -19), palm, (0.04 * size, 0.013 * size, 0.03 * size))
    for zz, ln in [(-0.024, 0.052), (-0.008, 0.062), (0.008, 0.058), (0.024, 0.045)]:
        ln = ln * size * (1 + claw)
        b0 = palm + direction * 0.03 * size + [0, 0, zz * size]
        b1 = b0 + (direction + [0, -0.15, zz * 3]) * ln * 0.55
        b2 = b1 + (direction + [0, -0.6, zz * 2]) * ln * 0.45
        d = smin(d, chain(q, [b0, b1, b2], [0.009 * size, 0.008 * size, 0.0065 * size * (1 - 0.6 * min(claw, 1))]), 0.006)
    t0 = palm + [-0.012 * size, 0, -0.026 * size]
    d = smin(d, chain(q, [t0, t0 + np.array([0.02, -0.008, -0.03]) * size, t0 + np.array([0.045, -0.02, -0.042]) * size * (1 + 0.5 * claw)],
                      [0.011 * size, 0.009 * size, 0.0065 * size]), 0.006)
    return d


def humanoid(p, limb=1.0, torso=1.0, belly=0.0, head_fwd=0.0, head_size=1.0, hand_size=1.0, claw=0.0, hunch=0.0, foot=1.0):
    q = mirror(p)
    # legs
    l = chain(q, [HIP + [0.005, -0.02, 0], KNEE, ANK + [0, -0.02, 0]], [0.066 * limb, 0.043 * limb, 0.028 * limb])
    l = smin(l, ellipsoid(q, KNEE + [0, -0.075, 0.02], (0.036 * limb, 0.07, 0.04 * limb)), 0.02)
    l = smin(l, ellipsoid(q, ANK + [0.002, -0.042, -0.05], (0.036 * foot, 0.024, 0.085 * foot)), 0.02)
    # trunk
    d = ellipsoid(p, V(0, 0.515, -0.012), (0.105 * torso, 0.065, 0.075 * torso))
    d = smin(d, cone(p, V(0, 0.54, -0.01), V(0, 0.64, 0.0), 0.078 * torso, 0.088 * torso), 0.04)
    d = smin(d, ellipsoid(p, V(0, 0.70, 0.0 - 0.3 * hunch), (0.118 * torso, 0.10, 0.075 * torso)), 0.04)
    if belly:
        d = smin(d, ellipsoid(p, V(0, 0.585, 0.03 + belly * 0.3), (0.085, 0.07, 0.06 + belly)), 0.04)
    if hunch:
        d = smin(d, ellipsoid(p, V(0, 0.745, -hunch), (0.09 * torso, 0.075, 0.06)), 0.04)
    d = smin(d, ellipsoid(q, SH + [-0.002, 0.0, -0.005], (0.048 * limb, 0.042 * limb, 0.045 * limb)), 0.03)
    d = smin(d, l, 0.03)
    # neck, head
    hc = V(0, 0.90, 0.02 + head_fwd)
    d = smin(d, cone(p, V(0, 0.775, -0.02), hc + V(0, -0.05, -0.03), 0.042 * limb, 0.038 * limb), 0.03)
    h = ellipsoid(p, hc + V(0, 0.012, -0.012), np.array([0.066, 0.078, 0.08]) * head_size)
    h = smin(h, ellipsoid(p, hc + V(0, -0.05 * head_size, 0.025 * head_size), np.array([0.05, 0.045, 0.055]) * head_size), 0.03)
    d = smin(d, h, 0.015)
    # arms
    a = chain(q, [SH, EL, WR], [0.040 * limb, 0.031 * limb, 0.023 * limb])
    a = smin(a, hand(q, size=hand_size, claw=claw), 0.012)
    d = smin(d, a, 0.025)
    return d, hc
