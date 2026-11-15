"""SCP-966: gaunt hairless stalker, long face with needle teeth, five long claws on each hand."""
import sys
import numpy as np
from core import *
import build, weights, body


def base(p):
    return body.humanoid(p, limb=0.72, torso=0.74, head_fwd=0.03, head_size=0.92, hand_size=1.15, claw=1.6, hunch=0.035, foot=0.95)


def ribs(p):
    ax = np.abs(p[:, 0])
    ph = (p[:, 1] + 0.4 * ax) / 0.027 * 2 * np.pi
    m = sstep(0.60, 0.63, p[:, 1]) * sstep(0.77, 0.74, p[:, 1]) * sstep(0.008, 0.02, ax) * sstep(0.10, 0.085, ax) * (p[:, 2] < 0.02)
    return 0.5 + 0.5 * np.sin(ph), m


def shape(p, detail=True):
    d, hc = base(p)
    q = mirror(p)
    d = smin(d, ellipsoid(p, hc + V(0, 0.045, -0.035), (0.052, 0.06, 0.07)), 0.03)                 # long skull
    d = smin(d, ellipsoid(p, hc + V(0, -0.06, 0.05), (0.03, 0.04, 0.045)), 0.02)                   # muzzle
    if detail:
        d = smax(d, -ellipsoid(q, hc + V(0.028, 0.004, 0.066), (0.019, 0.015, 0.016)), 0.008)      # big eye sockets
        d = smax(d, -ellipsoid(p, hc + V(0, -0.078, 0.085), (0.024, 0.012, 0.03)), 0.004)          # mouth
        r, m = ribs(p)
        d = d - 0.0035 * (r - 0.5) * m
        d = d + 0.003 * (fbm(p, 30, 3, 3) - 0.5)
    return d


def color(P, N, ao):
    q = mirror(P)
    _, hc = base(P[:1])
    skin = mix(rgb('6f7a6c'), rgb('a3ad9c'), fbm(P, 14, 4, 1))                     # grey with a green cast
    skin = mix(skin, rgb('4e5a52'), 0.55 * sstep(0.5, 0.75, fbm(P, 34, 3, 5)))
    skin = mix(skin, rgb('8e7f86'), 0.3 * sstep(0.6, 0.8, fbm(P, 8, 2, 11)))       # bruised patches
    r, m = ribs(P)
    skin = mix(skin, rgb('3d4640'), 0.5 * m * sstep(0.55, 0.1, r))
    # claws: dark, from the knuckles out
    reach = np.abs(P[:, 0]) - (body.WR[0] + 0.075)
    claw = sstep(0.0, 0.03, reach)
    skin = mix(skin, mix(rgb('2a2a26'), rgb('0f0f0e'), sstep(0.02, 0.1, reach)), claw)
    skin = mix(skin, rgb('3f423a'), 0.6 * sstep(0.09, 0.0, P[:, 1]))
    L = P - hc
    x, y, fwd, sx = np.abs(L[:, 0]), L[:, 1], -L[:, 2], L[:, 0]
    fr = fwd > 0.03
    eye = np.sqrt(((x - 0.028) / 0.019) ** 2 + ((y - 0.004) / 0.015) ** 2)
    skin = mix(skin, rgb('080a08'), sstep(1.15, 0.85, eye) * fr)
    skin = mix(skin, rgb('9fd08a'), 0.7 * sstep(0.45, 0.2, eye) * fr)              # faint green eye shine
    mouth = np.sqrt((sx / 0.026) ** 2 + ((y + 0.078) / 0.012) ** 2)
    skin = mix(skin, rgb('1a0808'), sstep(1.1, 0.9, mouth) * (fwd > 0.05))
    teeth = sstep(1.0, 0.85, mouth) * (np.abs(((sx / 0.0045) % 1.0) - 0.5) < 0.22) * (fwd > 0.05)
    skin = mix(skin, rgb('ddd8c0'), 0.9 * teeth)                                   # needle teeth
    light = (0.42 + 0.58 * ao) * (0.82 + 0.18 * N[:, 1])
    return skin * light[:, None]


def weight_fn(v):
    W = weights.humanoid(v, 6.0)
    return weights.keep_only(W, v[:, 1] > 0.87, ['Head', 'Neck'])


LO, HI = (-0.64, -0.01, -0.18), (0.64, 1.04, 0.16)
if __name__ == '__main__':
    if 'clay' in sys.argv:
        build.quick('scp_966', shape, LO, HI, 0.005)
    else:
        m = build.make('scp_966', shape, LO, HI, 3600, color, weight_fn, 'SCP_966_Model', voxel=0.003)
        build.preview('scp_966', m, height=1.3)
        build.preview_pose('scp_966', m, height=1.3)
