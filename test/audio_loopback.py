#!/usr/bin/env python3
"""Audio HAT — measures an output-to-input loopback. Runs on the Pi.

Plays a tone on ONE channel at a time and records both: does signal pass, is L really L,
and how much leaks into the other channel. Levels in dBFS.

  python3 audio_loopback.py            # 1 kHz
  python3 audio_loopback.py -f 300     # another frequency

Not for quality figures: the WM8960's full-duplex loopback has its own ~5.7 dB dip around
1.6 kHz that is not the board.
"""

import argparse
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audio_hat_constants import (IN_CONTROLS, ALSA_CARD_NAME, BOARD_NAME, BOARD_REV, CHANNELS,  # noqa: E402
                                 CROSSTALK_MARGIN_DB, FLOOR_DB, LOOPBACK_CROSSED,
                                 LOOPBACK_NO_SIGNAL, LOOPBACK_SEPARATION, NEAR_CLIP_DB,
                                 SAMPLE_FORMAT, SAMPLE_RATE_HZ, TONE_AMPLITUDE, TONE_HZ)

TONE_SECONDS = 3.0
RECORD_SECONDS = 4.0
WINDOW = (0.7, 2.7)     # steady part, past the stream start

DTYPE = {"S32_LE": "<i4", "S16_LE": "<i2"}[SAMPLE_FORMAT]
SCALE = float(2 ** (8 * np.dtype(DTYPE).itemsize - 1))


def tone(channel, hz):
    n = int(SAMPLE_RATE_HZ * TONE_SECONDS)
    t = np.arange(n) / SAMPLE_RATE_HZ
    s = (TONE_AMPLITUDE * np.sin(2 * np.pi * hz * t) * (SCALE - 1)).astype(DTYPE)
    z = np.zeros(n, dtype=DTYPE)
    return np.column_stack([s, z] if channel == "L" else [z, s]).tobytes()


def db(x):
    return float("-inf") if x <= 0 else 20 * np.log10(x)


def run_once(channel, hz, card):
    raw_path = "/tmp/lb_tono_%s.raw" % channel
    rec_path = "/tmp/lb_rec_%s.raw" % channel
    with open(raw_path, "wb") as f:
        f.write(tone(channel, hz))
    if os.path.exists(rec_path):
        os.remove(rec_path)          # never read a previous run's capture

    common = ["-f", SAMPLE_FORMAT, "-r", str(SAMPLE_RATE_HZ), "-c", str(CHANNELS), "-t", "raw"]
    rec = subprocess.Popen(["arecord", "-D", card, *common, "-d", str(int(RECORD_SECONDS)), rec_path],
                           stderr=subprocess.DEVNULL)
    subprocess.run(["aplay", "-D", card, *common, raw_path], stderr=subprocess.DEVNULL)
    rec.wait()

    d = np.fromfile(rec_path, dtype=DTYPE)
    if d.size < SAMPLE_RATE_HZ * CHANNELS:
        return None
    d = d.reshape(-1, CHANNELS).astype(float) / SCALE
    a = d[int(SAMPLE_RATE_HZ * WINDOW[0]):int(SAMPLE_RATE_HZ * WINDOW[1])]
    return [float(np.sqrt((a[:, i] ** 2).mean())) for i in range(CHANNELS)]


def verdict(channel, left, right):
    """What two dBFS levels mean, as (text, [problems]). Pure, so it is tested without hardware."""
    expected, other = (left, right) if channel == "L" else (right, left)
    other_name = "R" if channel == "L" else "L"
    ps = []

    if max(expected, other) < FLOOR_DB:
        v = "%s on either channel" % LOOPBACK_NO_SIGNAL
        ps.append("%s: no signal arrives (max %.1f dBFS). Check the DAC is routed and the "
                  "inputs are not muted." % (channel, max(expected, other)))
    elif other > expected + CROSSTALK_MARGIN_DB:
        v = "%s: out on %s, in on %s" % (LOOPBACK_CROSSED, channel, other_name)
        ps.append("%s: the signal shows up on %s, %.1f dB above %s"
                  % (channel, other_name, other - expected, channel))
    elif expected < FLOOR_DB:
        v = "%s on %s" % (LOOPBACK_NO_SIGNAL, channel)
        ps.append("%s: no signal arrives (%.1f dBFS)" % (channel, expected))
    elif other > expected - CROSSTALK_MARGIN_DB:
        v = "channels mixed (separation %.1f dB)" % (expected - other)
        ps.append("%s: only %.1f dB of separation" % (channel, expected - other))
    else:
        v = "ok, %s %.1f dB" % (LOOPBACK_SEPARATION, expected - other)

    if max(expected, other) > NEAR_CLIP_DB:
        v += "  ⚠ near clipping"
        ps.append("%s: the input is at %.1f dBFS, nearly clipping: lower "
                  "'%s' or the amplitude" % (channel, max(expected, other), IN_CONTROLS[channel]))
    return v, ps


def _header():
    print("=== %s %s ===" % (BOARD_NAME, BOARD_REV))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-f", "--freq", type=float, default=float(TONE_HZ))
    p.add_argument("-D", "--device", default="hw:%s" % ALSA_CARD_NAME)
    a = p.parse_args()

    _header()
    print("%g Hz tone at %.0f%% of full scale, %s @ %d Hz"
          % (a.freq, TONE_AMPLITUDE * 100, SAMPLE_FORMAT, SAMPLE_RATE_HZ))
    print()
    print("  %-10s %10s %10s   %s" % ("sent", "RMS L", "RMS R", "verdict"))

    problems = []
    for channel in ("L", "R"):
        r = run_once(channel, a.freq, a.device)
        if r is None:
            print("  %-10s  empty or short capture" % (channel + " only"))
            problems.append("%s: nothing was recorded" % channel)
            continue
        left, right = db(r[0]), db(r[1])
        v, ps = verdict(channel, left, right)
        problems += ps
        print("  %-10s %9.1f %9.1f   %s" % (channel + " only", left, right, v))

    print()
    if problems:
        print("PROBLEMS:")
        for x in problems:
            print("  - " + x)
        return 1
    print("The round trip works and the channels are not crossed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
