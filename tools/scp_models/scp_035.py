"""SCP-035: white porcelain comedy mask weeping black fluid. Rigid, on the head bone."""
import sys
import numpy as np
from core import *
import build

HC = V(0, 0.895, -0.01)
R = np.array([0.080, 0.100, 0.097])


def fxy(p):
    L = p - HC
    return L[:, 0], L[:, 1], -L[:, 2]


def eye(x, y):
    """Laughing crescent eyes: 1 inside."""
    ax = np.abs(x) - 0.031
    yy = y - 0.022 - 0.012 * np.cos(np.clip(ax / 0.02, -1, 1) * np.pi / 2) + 0.012
    return sstep(1.0, 0.8, np.sqrt((ax / 0.02) ** 2 + (yy / 0.0075) ** 2))


def mouth(x, y):
    """Wide grin, corners turned up."""
    yy = y + 0.05 - 0.035 * (x / 0.045) ** 2
    up = sstep(1.0, 0.85, np.sqrt((x / 0.047) ** 2 + (yy / 0.0085) ** 2))
    low = sstep(1.0, 0.85, np.sqrt((x / 0.036) ** 2 + ((y + 0.056) / 0.016) ** 2)) * (yy < 0.004)
    return np.maximum(up, low)


def drips(x, y, P):
    w = 0.0035 + 0.0015 * vnoise(P * np.array([1, 0, 1]), 150, 3)
    d = np.zeros(len(x))
    for cx, top, ln in [(-0.036, 0.014, 0.075), (-0.027, 0.012, 0.05), (0.03, 0.013, 0.085), (0.039, 0.014, 0.04),
                        (-0.02, -0.062, 0.035), (0.004, -0.07, 0.03), (0.024, -0.064, 0.045), (-0.043, -0.03, 0.05), (0.044, -0.03, 0.035)]:
        d = np.maximum(d, sstep(w, w * 0.5, np.abs(x - cx)) * (y < top) * sstep(top - ln - 0.004, top - ln + 0.004, y))
        d = np.maximum(d, sstep(0.0058, 0.004, np.sqrt((x - cx) ** 2 + (y - top + ln) ** 2)))      # bead at the end
    return d


def shape(p, detail=True):
    q = mirror(p)
    x, y, fwd = fxy(p)
    d = ellipsoid(p, HC, R)
    d = smin(d, ellipsoid(q, HC + V(0.034, -0.012, 0.07), (0.022, 0.02, 0.02)), 0.02)               # cheeks
    d = smin(d, ellipsoid(q, HC + V(0.031, 0.04, 0.072), (0.026, 0.008, 0.016)), 0.012)             # brows
    d = smin(d, cone(p, HC + V(0, 0.022, 0.09), HC + V(0, -0.018, 0.103), 0.008, 0.012), 0.01)      # nose
    d = smax(d, -ellipsoid(p, HC + V(0, 0, -0.006), R - 0.009), 0.003)                              # hollow shell
    d = smax(d, 0.022 - fwd + 0.25 * np.abs(y), 0.006)                                              # front part only
    if detail:
        d = d + 0.005 * np.maximum(eye(x, y), mouth(x, y)) * (fwd > 0.04)
        d = d - 0.0025 * drips(x, y, p) * (fwd > 0.04)
    return d


def color(P, N, ao):
    x, y, fwd = fxy(P)
    por = mix(rgb('d9d6cc'), rgb('f3f1ea'), fbm(P, 30, 3, 1))
    f1, f2 = worley(P, 45, 4)
    por = mix(por, rgb('8c8a82'), 0.5 * sstep(0.035, 0.0, f2 - f1) * sstep(0.5, 0.7, fbm(P, 12, 2, 6)))   # crazing
    por = mix(por, rgb('b9b4a4'), 0.5 * (1 - ao))
    outer = (fwd > 0.03) & (ellipsoid(P, HC + V(0, 0, -0.006), R - 0.009) > 0.004)
    black = mix(rgb('050506'), rgb('1a1a1f'), sstep(0.3, 0.9, N[:, 1]) * 0.6)
    k = np.maximum(np.maximum(eye(x, y), mouth(x, y)), drips(x, y, P)) * outer
    col = mix(por, black, k)
    col = np.where(outer[:, None], col, rgb('2a2826') * np.ones((len(P), 3)))                       # inside of the shell
    light = (0.5 + 0.5 * ao) * (0.82 + 0.18 * N[:, 1])
    return col * np.where(outer, light, 0.8)[:, None]


LO, HI = (-0.1, 0.78, -0.13), (0.1, 1.01, 0.0)
if __name__ == '__main__':
    VIEWS = [('front', 0, 5), ('iso', 40, 20), ('side', 90, 5)]
    if 'clay' in sys.argv:
        build.quick('scp_035_mask', shape, LO, HI, 0.002, height=0.32, center=(0, 0, 0.9), views=VIEWS)
    else:
        m = build.make('scp_035_mask', shape, LO, HI, 900, color, None, 'SCP_035_Model', voxel=0.0015, res=256, static='Bip01_Head')
        import render
        render.VIEWS = VIEWS
        build.preview('scp_035_mask', m, height=0.32, center=(0, 0, 0.9))
