"""Sounds of the shock maul, synthesised here (no source recordings).

    python3 tools/make_weapon_sounds.py

Writes mono Ogg Vorbis files to media/sound/ (needs ffmpeg).
"""

import os
import subprocess
import tempfile
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "Contents/mods/SCPFoundation/42/media/sound")
SR = 44100


def t_axis(sec):
    return np.arange(int(sec * SR)) / SR


def lowpass(x, cut):
    a = np.exp(-2 * np.pi * cut / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def highpass(x, cut):
    return x - lowpass(x, cut)


def bandpass(x, lo, hi):
    return lowpass(highpass(x, lo), hi)


def env(t, attack, decay):
    return np.minimum(1, t / max(attack, 1e-4)) * np.exp(-np.maximum(0, t - attack) / decay)


def saw(f, t):
    ph = np.cumsum(np.broadcast_to(f, t.shape)) / SR
    return 2 * (ph % 1) - 1


def crackle(t, rng, density, length=0.004, start=0.0, end=None):
    """Random sharp sparks: short bursts of bright noise."""
    end = t[-1] if end is None else end
    x = np.zeros_like(t)
    n = int(density * (end - start))
    for _ in range(n):
        at = rng.uniform(start, end)
        i0 = int(at * SR)
        ln = int(rng.uniform(0.3, 1.5) * length * SR)
        if i0 + ln >= len(t):
            continue
        burst = rng.standard_normal(ln) * np.exp(-np.arange(ln) / (ln / 3)) * rng.uniform(0.3, 1.0)
        x[i0:i0 + ln] += burst
    return highpass(x, 1500)


def buzz(t, base=100, rng=None):
    """Mains-like electric hum, a bit dirty."""
    wob = 1 + 0.01 * np.sin(2 * np.pi * 7 * t)
    x = 0.6 * saw(base * wob, t) + 0.4 * np.sign(np.sin(2 * np.pi * base * 2 * t))
    return bandpass(x, 80, 4000)


def norm(x, peak=0.9):
    m = np.max(np.abs(x))
    return x * (peak / m) if m > 0 else x


def save(x, name):
    x = norm(x)
    fade = int(0.01 * SR)
    x[-fade:] *= np.linspace(1, 0, fade)
    pcm = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "a.wav")
        with wave.open(wav, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes(pcm.tobytes())
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-c:a", "libvorbis", "-q:a", "4",
                        os.path.join(OUT, name + ".ogg")], check=True)
    print(name, f"{len(x) / SR:.2f}s")


def hit(seed):
    rng = np.random.default_rng(seed)
    t = t_axis(0.95)
    # heavy blow: low thump + body noise
    thump = np.sin(2 * np.pi * (60 + 50 * np.exp(-t / 0.03)) * t) * env(t, 0.002, 0.12)
    body = lowpass(rng.standard_normal(len(t)), 900) * env(t, 0.001, 0.05)
    # discharge: loud snap, crackling arc and a buzz that dies out
    snap = highpass(rng.standard_normal(len(t)), 2000) * env(t, 0.0005, 0.015)
    arc = crackle(t, rng, 260, start=0.0, end=0.55) * np.exp(-t / 0.35)
    hum = buzz(t, 100 + 20 * rng.random()) * env(t, 0.01, 0.25)
    return 1.0 * thump + 0.5 * body + 0.7 * snap + 0.8 * arc + 0.35 * hum


def swing():
    rng = np.random.default_rng(3)
    t = t_axis(0.5)
    shape = np.sin(np.pi * np.clip(t / 0.42, 0, 1)) ** 2
    whoosh = bandpass(rng.standard_normal(len(t)), 250, 1800) * shape
    hum = buzz(t, 120) * shape * 0.5
    sparks = crackle(t, rng, 30, start=0.05, end=0.4) * shape
    return whoosh + hum + 0.4 * sparks


def charge():
    rng = np.random.default_rng(5)
    t = t_axis(1.3)
    f = 220 + 1500 * (t / t[-1]) ** 1.6
    whine = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(1, t / 0.2)
    whine += 0.3 * np.sin(2 * np.pi * np.cumsum(2 * f) / SR) * np.minimum(1, t / 0.2)
    ready = np.zeros_like(t)
    i0 = int(1.05 * SR)
    tt = t[i0:] - t[i0]
    ready[i0:] = np.sin(2 * np.pi * 1760 * tt) * np.exp(-tt / 0.08)
    hum = buzz(t, 100) * 0.25 * (t / t[-1])
    sparks = crackle(t, rng, 15, start=0.2, end=1.0) * 0.3
    return 0.5 * whine * (1 - 0.6 * (t > 1.05)) + 0.6 * ready + hum + sparks


def empty():
    rng = np.random.default_rng(9)
    t = t_axis(0.45)
    click = highpass(rng.standard_normal(len(t)), 3000) * env(t, 0.0005, 0.006)
    fizz = bandpass(rng.standard_normal(len(t)), 1500, 6000) * env(t, 0.01, 0.08) * 0.4
    drop = np.sin(2 * np.pi * np.cumsum(600 * np.exp(-t / 0.08) + 80) / SR) * env(t, 0.005, 0.1) * 0.5
    return click + fizz + drop


if __name__ == "__main__":
    for k in (1, 2, 3):
        save(hit(k), f"SCP_ShockMaul_Hit{k}")
    save(swing(), "SCP_ShockMaul_Swing")
    save(charge(), "SCP_ShockMaul_Charge")
    save(empty(), "SCP_ShockMaul_Empty")
