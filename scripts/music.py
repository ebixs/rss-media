"""Make an original 15 s music bed for a reel, entirely in code (no samples, no
copyright questions). Warm pad chords, a soft plucked arpeggio, a light beat,
a riser into the end card and a final soft hit.

    python scripts/music.py out.wav [--seconds 15] [--seed 7] [--end 11.5]

`--end` is when the end card starts: the riser builds into it and the beat
drops out there, so the music follows the picture. Output: 44.1 kHz stereo WAV.
"""
from __future__ import annotations

import argparse
import wave

import numpy as np

SR = 44100

# Chord progressions as semitone offsets from the key's root (I–V–vi–IV family).
PROGRESSIONS = [
    [[0, 4, 7, 11], [7, 11, 14, 17], [9, 12, 16, 19], [5, 9, 12, 16]],   # Imaj7 V vi IV
    [[9, 12, 16, 19], [5, 9, 12, 16], [0, 4, 7, 11], [7, 11, 14, 17]],   # vi IV I V
    [[0, 4, 7, 14], [5, 9, 12, 16], [9, 12, 16, 19], [7, 11, 14, 17]],   # I IV vi V
]
KEYS = [57, 60, 62, 55]  # A3, C4, D4, G3 (MIDI)


def hz(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def env(n: int, a: float, d: float, s: float, r: float) -> np.ndarray:
    a_n, d_n, r_n = int(a * SR), int(d * SR), int(r * SR)
    s_n = max(0, n - a_n - d_n - r_n)
    e = np.concatenate([np.linspace(0, 1, a_n, False), np.linspace(1, s, d_n, False),
                        np.full(s_n, s), np.linspace(s, 0, r_n)])
    return np.pad(e, (0, max(0, n - len(e))))[:n]


def lowpass(x: np.ndarray, cutoff: float) -> np.ndarray:
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):  # one-pole; fine for 15 s
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def pad(freq: float, n: int, rng) -> np.ndarray:
    t = np.arange(n) / SR
    out = np.zeros(n)
    for det in (-0.12, 0.0, 0.11):
        f = freq * 2 ** (det / 12)
        ph = rng.random() * 2 * np.pi
        out += 2 * ((f * t + ph / (2 * np.pi)) % 1) - 1          # saw
    out += 0.6 * np.sin(2 * np.pi * freq / 2 * t)                # warm sub
    return out / 3.6


def pluck(freq: float, n: int) -> np.ndarray:
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * 2 * freq * t) + 0.12 * np.sin(2 * np.pi * 3 * freq * t)
    return tone * np.exp(-t * 7.5)


def kick(n: int) -> np.ndarray:
    t = np.arange(n) / SR
    f = 48 + 90 * np.exp(-t * 32)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)


def hat(n: int, rng) -> np.ndarray:
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    noise = noise - lowpass(noise, 6000)
    return noise * np.exp(-t * 60)


def reverb(x: np.ndarray, rng, mix: float = 0.28) -> np.ndarray:
    out = x.copy()
    for delay, gain in ((0.031, 0.5), (0.047, 0.42), (0.071, 0.35), (0.113, 0.27), (0.163, 0.2), (0.241, 0.14)):
        d = int(delay * SR)
        out[d:] += gain * mix * x[:-d]
    return out


def make(seconds: float = 15.0, seed: int = 7, end_at: float = 11.5) -> np.ndarray:
    rng = np.random.default_rng(seed)
    bpm = float(rng.choice([88, 92, 96, 100]))
    beat = 60 / bpm
    root = int(rng.choice(KEYS))
    prog = PROGRESSIONS[int(rng.integers(len(PROGRESSIONS)))]
    n = int(seconds * SR)
    L, R = np.zeros(n), np.zeros(n)

    bar = 4 * beat
    chords = int(np.ceil(seconds / bar)) + 1
    for c in range(chords):
        start = int(c * bar * SR)
        if start >= n:
            break
        chord = prog[c % len(prog)]
        seg = min(int(bar * SR * 1.15), n - start)
        e = env(seg, 0.35, 0.4, 0.75, 0.6)
        p = sum(pad(hz(root + iv - 12), seg, rng) for iv in chord[:3]) * e
        p = lowpass(p, 1400 + 500 * (c % 2))
        L[start:start + seg] += 0.30 * p
        R[start:start + seg] += 0.30 * np.roll(p, 220)
        # arpeggio, eighth notes, from bar 2 until the end card
        for k in range(8):
            t0 = c * bar + k * beat / 2
            if t0 < bar * 0.9 or t0 >= end_at:
                continue
            note = root + chord[(k * 3) % len(chord)] + (12 if k % 4 == 3 else 0)
            s = int(t0 * SR)
            m = min(int(0.6 * SR), n - s)
            if m <= 0:
                continue
            pl = pluck(hz(note), m) * (0.9 if k % 2 == 0 else 0.6)
            pan = 0.35 + 0.3 * ((k % 4) / 3)
            L[s:s + m] += 0.16 * pl * (1 - pan)
            R[s:s + m] += 0.16 * pl * pan

    # beat: from bar 2, drops out at the end card
    t = bar
    i = 0
    while t < min(end_at - 0.05, seconds):
        s = int(t * SR)
        m = min(int(0.5 * SR), n - s)
        if i % 2 == 0:
            k = kick(m) * 0.55
            L[s:s + m] += k
            R[s:s + m] += k
        h = hat(min(int(0.12 * SR), n - s), rng) * 0.10
        o = int(beat / 2 * SR)
        if s + o + len(h) < n:
            L[s + o:s + o + len(h)] += h * 0.8
            R[s + o:s + o + len(h)] += h
        t += beat
        i += 1

    # riser into the end card + final soft hit
    rs, re_ = int(max(0, end_at - 1.6) * SR), int(end_at * SR)
    if re_ <= n:
        m = re_ - rs
        noise = rng.standard_normal(m)
        noise = noise - lowpass(noise, 1200)
        ramp = np.linspace(0, 1, m) ** 2.2
        L[rs:re_] += 0.12 * noise * ramp
        R[rs:re_] += 0.12 * np.roll(noise, 300) * ramp
        m = min(int(3.5 * SR), n - re_)
        if m > 0:
            hit = sum(pad(hz(root + iv), m, rng) for iv in prog[0]) * env(m, 0.01, 0.6, 0.5, 2.5)
            hit = lowpass(hit, 2200) * 0.28 + kick(m) * 0.5
            L[re_:re_ + m] += hit
            R[re_:re_ + m] += hit

    L, R = reverb(L, rng), reverb(R, rng)
    fade = int(0.8 * SR)
    for ch in (L, R):
        ch[:int(0.05 * SR)] *= np.linspace(0, 1, int(0.05 * SR))
        ch[-fade:] *= np.linspace(1, 0, fade)
    st = np.stack([L, R], axis=1)
    st = np.tanh(st * 1.2)                       # gentle limiter
    return st / max(1e-9, np.abs(st).max()) * 0.85


def save(path: str, audio: np.ndarray) -> None:
    pcm = (audio * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--seconds", type=float, default=15.0)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--end", type=float, default=11.5)
    a = ap.parse_args()
    save(a.out, make(a.seconds, a.seed, a.end))
    print(a.out)
