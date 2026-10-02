#!/usr/bin/env python3
"""Audio HAT — finds which side an L/R crossing is on. Runs on the Pi.

When `audio_loopback.py` reports crossed channels, this says where. It mutes one physical
input at a time while always playing on the same channel: if the signal enters on the other
input, the crossing is before the ADC (DAC, cables, patch); if it enters on the right input
but is captured on the other channel, it is in the capture.

  python3 lr_bisect.py            # play on ALSA-L
  python3 lr_bisect.py -c R       # play on ALSA-R

Restores the mixer when done.
"""

import argparse
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audio_hat_constants import (BOARD_NAME, BOARD_REV, CHANNELS,  # noqa: E402
                                 SAMPLE_FORMAT, SAMPLE_RATE_HZ)

SR = SAMPLE_RATE_HZ
SCALE = float(2 ** 31)
AMPLITUDE = 0.30
DUR = 2.5
COMMON = ["-f", SAMPLE_FORMAT, "-r", str(SR), "-c", str(CHANNELS), "-t", "raw"]


def amix(control, value):
    subprocess.run(["amixer", "-c1", "-q", "sset", control, value], check=False)


def read_mixer(control):
    r = subprocess.run(["amixer", "-c1", "sget", control], capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if "%]" in line:
            return line.split("[")[1].split("]")[0]
    return "100%"


def tone(channel, hz):
    n = int(SR * DUR)
    t = np.arange(n) / SR
    s = (AMPLITUDE * np.sin(2 * np.pi * hz * t) * (SCALE - 1)).astype("<i4")
    z = np.zeros(n, dtype="<i4")
    return np.column_stack([s, z] if channel == "L" else [z, s]).tobytes()


def db(x):
    return float("-inf") if x <= 0 else 20 * np.log10(x)


def run_once(channel, hz, card):
    with open("/tmp/lrb_tono.raw", "wb") as f:
        f.write(tone(channel, hz))
    if os.path.exists("/tmp/lrb_rec.raw"):
        os.remove("/tmp/lrb_rec.raw")     # never read a previous capture
    rec = subprocess.Popen(["arecord", "-D", card, *COMMON, "-d", "3", "/tmp/lrb_rec.raw"],
                           stderr=subprocess.DEVNULL)
    subprocess.run(["aplay", "-D", card, *COMMON, "/tmp/lrb_tono.raw"], stderr=subprocess.DEVNULL)
    rec.wait()
    d = np.fromfile("/tmp/lrb_rec.raw", dtype="<i4")
    if d.size < SR:
        return None
    d = d.reshape(-1, CHANNELS).astype(float) / SCALE
    a = d[int(SR * 0.6):int(SR * 2.1)]
    return [db(float(np.sqrt((a[:, i] ** 2).mean()))) for i in range(CHANNELS)]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-c", "--channel", choices=("L", "R"), default="L")
    p.add_argument("-f", "--freq", type=float, default=1000.0)
    p.add_argument("-D", "--device", default="hw:1,0")
    p.add_argument("--floor", type=float, default=-60.0, help="dBFS below which there is no signal")
    a = p.parse_args()

    print("=== %s %s ===" % (BOARD_NAME, BOARD_REV))
    print("playing on ALSA-%s at %g Hz\n" % (a.channel, a.freq))

    previous = {c: read_mixer(c) for c in ("Left Input Line", "Right Input Line")}
    entered_on = None
    try:
        print("  %-30s %9s %9s" % ("configuration", "ALSA L", "ALSA R"))
        for side, l, r in [("L", "100%", "0%"), ("R", "0%", "100%")]:
            amix("Left Input Line", l)
            amix("Right Input Line", r)
            levels = run_once(a.channel, a.freq, a.device)
            if levels is None:
                print("  empty or short capture")
                return 1
            print("  only input %s live %-15s %9.1f %9.1f"
                  % (side, "", levels[0], levels[1]))
            if max(levels) > a.floor:
                entered_on = (side, levels)
    finally:
        for c, v in previous.items():
            amix(c, v)

    print()
    if entered_on is None:
        print("No signal on either input. Crossing is not the problem: check the DAC is")
        print("routed ('Out Mixer DAC' on) and the cable is in.")
        return 1

    side, levels = entered_on
    captured = "L" if levels[0] > levels[1] else "R"
    print("The signal entered on physical input %s and was captured on ALSA-%s." % (side, captured))
    if side == captured == a.channel:
        print("All straight: no crossing.")
        return 0
    if side != captured:
        print("The ADC maps input %s to ALSA-%s: the crossing is in the CAPTURE." % (side, captured))
    else:
        print("Played on ALSA-%s, came out of physical output %s: the crossing is BEFORE the"
              % (a.channel, side))
        print("ADC — DAC, cables or patch. The board netlists are verified straight, so")
        print("start with the patch and the 4-way cables.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
