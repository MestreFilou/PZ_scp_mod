"""Skin weights from distances to the bones of the bind pose (checked against the weights the
previous models inherited from the vanilla body)."""
import numpy as np
import build

J = build.joint


def segments(who=None):
    who = who or build.BOB
    j = lambda b: J(b, who)
    S = {}
    S['Bip01_Pelvis'] = (j('Bip01_R_Thigh') + [0, -0.02, 0], j('Bip01_L_Thigh') + [0, -0.02, 0], 1.25)
    S['Bip01_Spine'] = (j('Bip01_Spine'), j('Bip01_Spine1'), 1.6)
    S['Bip01_Spine1'] = (j('Bip01_Spine1') + [0, 0.02, 0], j('Bip01_Neck') - [0, 0.03, 0], 1.7)
    S['Bip01_Neck'] = (j('Bip01_Neck'), j('Bip01_Head'), 0.7)
    S['Bip01_Head'] = (j('Bip01_Head') + [0, 0.03, -0.01], j('Bip01_Head') + [0, 0.11, -0.01], 1.5)
    for s in 'LR':
        p = f'Bip01_{s}_'
        S[p + 'Clavicle'] = (j(p + 'Clavicle') + [0.03 * (1 if s == 'L' else -1), 0, 0], j(p + 'UpperArm'), 0.8)
        S[p + 'UpperArm'] = (j(p + 'UpperArm'), j(p + 'Forearm'), 1.0)
        S[p + 'Forearm'] = (j(p + 'Forearm'), j(p + 'Hand'), 1.0)
        S[p + 'Hand'] = (j(p + 'Hand'), j(p + 'Finger1'), 0.8)
        d = j(p + 'Finger1') - j(p + 'Hand'); d /= np.linalg.norm(d)
        S[p + 'Finger1'] = (j(p + 'Finger1') + 0.01 * d, j(p + 'Finger1') + 0.07 * d, 0.6)
        S[p + 'Finger0'] = (j(p + 'Finger0') + [0, 0, -0.01], j(p + 'Finger0') + 0.03 * d + [0, 0, -0.04], 0.5)
        S[p + 'Thigh'] = (j(p + 'Thigh') + [0, -0.03, 0], j(p + 'Calf'), 1.0)
        S[p + 'Calf'] = (j(p + 'Calf'), j(p + 'Foot'), 1.0)
        S[p + 'Foot'] = (j(p + 'Foot') + [0, -0.03, 0], j(p + 'Foot') + [0, -0.05, -0.12], 0.9)
    return S


def seg_dist(v, a, b):
    ab = b - a
    t = np.clip(((v - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
    return np.linalg.norm(v - (a + t[:, None] * ab), axis=1), t


def humanoid(v, power=6.0, segs=None, scale=None, side_margin=0.012):
    """v in bind space. scale: optional dict bone -> extra thickness factor."""
    S = segs or segments()
    W = np.zeros((len(v), len(build.BONES)))
    for b, (a, c, r) in S.items():
        d, _ = seg_dist(v, a, c)
        r = r * (scale or {}).get(b, 1.0)
        w = (r / (d + 0.004)) ** power
        if '_L_' in b:
            w = w * (v[:, 0] > -side_margin)
        if '_R_' in b:
            w = w * (v[:, 0] < side_margin)
        W[:, build.BONES.index(b)] = w
    W /= W.sum(1, keepdims=True)
    return W


if __name__ == '__main__':
    import xlib, itertools
    for n in ('scp_106', 'scp_966', 'scp_096'):
        x = xlib.load(f'{build.MEDIA}/models_X/skinned/clothes/{n}.x')
        ref = np.zeros((len(x.verts), len(build.BONES)))
        for b, (i, w) in x.weights.items():
            ref[i, build.BONES.index(b)] = w
        for p in (3, 4, 6, 8):
            W = build.limit_weights(humanoid(x.verts, p))
            err = np.abs(W - ref).sum(1) / 2
            print(n, 'power', p, 'mean err %.3f  p90 %.3f' % (err.mean(), np.percentile(err, 90)))
        W = build.limit_weights(humanoid(x.verts, 4))
        e = np.abs(W - ref)
        print('  worst bones:', sorted([(round(e[:, i].mean(), 3), b) for i, b in enumerate(build.BONES)], reverse=True)[:6])


def unstretch_arms(v, long_wrist_x, hand_scale=0.7):
    """Models with stretched forearms: map the arm back to normal proportions before weighting."""
    EL, WR = J('Bip01_L_Forearm'), J('Bip01_L_Hand')
    u = v.copy()
    ax = np.abs(u[:, 0])
    fore = (ax > EL[0]) & (ax <= long_wrist_x)
    hand = ax > long_wrist_x
    nx = ax.copy()
    nx[fore] = EL[0] + (ax[fore] - EL[0]) * (WR[0] - EL[0]) / (long_wrist_x - EL[0])
    nx[hand] = WR[0] + (ax[hand] - long_wrist_x) * hand_scale
    u[:, 0] = np.sign(u[:, 0]) * nx
    return u


def keep_only(W, mask, names):
    """On the masked vertices keep only the bones whose name contains one of names."""
    for i, b in enumerate(build.BONES):
        if not any(n in b for n in names):
            W[mask, i] = 0
    return W / W.sum(1, keepdims=True)


def drop(W, mask, names):
    for i, b in enumerate(build.BONES):
        if any(n in b for n in names):
            W[mask, i] = 0
    return W / W.sum(1, keepdims=True)


def transfer(v, ref_file, k=4):
    """Copy weights from a reference mesh (nearest vertices, inverse-distance blend)."""
    import os
    from scipy.spatial import cKDTree
    r = np.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), ref_file))
    d, i = cKDTree(r['v']).query(v, k=k)
    w = 1.0 / (d + 0.003) ** 2
    W = (r['W'][i] * w[..., None]).sum(1)
    return W / W.sum(1, keepdims=True)
