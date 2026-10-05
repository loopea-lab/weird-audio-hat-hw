#!/usr/bin/env python3
"""Live input level meters, for testing a mic by talking into it. Runs on the Pi.

audio_loopback.py records four seconds to a file and then analyses it, which is why it feels
unresponsive as a meter: it is a capture, not a meter. This streams arecord and prints one
reading per period, so the lag is the period (23 ms at 1024 frames) and not the recording.

    ./input_levels.py                 # both channels, 1024-frame periods
    ./input_levels.py --period 256    # ~6 ms, twitchier
    ./input_levels.py --seconds 10    # stop by itself, for a scripted run

Silence and a dead capture look identical on a meter, so they are told apart here: no frames
at all is an abort with arecord's own words, never -inf dBFS.
"""
import argparse
import os
import signal
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import numpy as np
except ImportError:
    sys.exit("needs numpy: sudo apt install python3-numpy")

from audio_hat_constants import (ALSA_CARD_NAME, BOARD_NAME, BOARD_REV, CHANNELS,  # noqa: E402
                                 JACKS, SAMPLE_FORMAT, SAMPLE_RATE_HZ)
from audio_hat_constants import CLIP_DB, FLOOR_DB, QUIET_DB  # noqa: E402,F401
from audio_loopback import DTYPE, SCALE, db  # noqa: E402

BAR_WIDTH = 32
BAR_TOP_DB = 0.0
BAR_BOTTOM_DB = -72.0   # a bit under the floor, so the floor is visible as a mark


def bar(level_db):
    """A bar from BAR_BOTTOM_DB to BAR_TOP_DB, with the noise floor marked."""
    span = BAR_TOP_DB - BAR_BOTTOM_DB
    filled = 0 if level_db <= BAR_BOTTOM_DB else \
        min(BAR_WIDTH, int(round((level_db - BAR_BOTTOM_DB) / span * BAR_WIDTH)))
    floor_at = int(round((FLOOR_DB - BAR_BOTTOM_DB) / span * BAR_WIDTH))
    cells = []
    for i in range(BAR_WIDTH):
        if i < filled:
            cells.append("#")
        elif i == floor_at:
            cells.append(":")
        else:
            cells.append(" ")
    return "".join(cells)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("-D", "--device", default="hw:%s" % ALSA_CARD_NAME)
    p.add_argument("--period", type=int, default=1024, help="frames per reading")
    p.add_argument("--seconds", type=float, default=0.0, help="0 = until Ctrl-C")
    a = p.parse_args()

    frame_bytes = np.dtype(DTYPE).itemsize * CHANNELS
    chunk = a.period * frame_bytes
    cmd = ["arecord", "-D", a.device, "-f", SAMPLE_FORMAT, "-r", str(SAMPLE_RATE_HZ),
           "-c", str(CHANNELS), "-t", "raw", "--period-size", str(a.period), "-q", "-"]

    print("=== %s %s ===" % (BOARD_NAME, BOARD_REV))
    print("%s  %d Hz %s %dch  ·  %d-frame periods (%.1f ms)"
          % (a.device, SAMPLE_RATE_HZ, SAMPLE_FORMAT, CHANNELS, a.period,
             a.period / SAMPLE_RATE_HZ * 1000.0))
    # A mic on IN R shows on R: watching L instead reads exactly like a dead mic.
    jack = {d["channel"]: d["label"] for d in JACKS.values() if d["dir"] == "in"}
    print("floor %.0f dBFS is the ':' mark · a mic on %s shows on R, line in on %s shows on L\n"
          % (FLOOR_DB, jack["R"], jack["L"]))

    try:
        rec = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        sys.exit("arecord is not installed: sudo apt install alsa-utils")

    peak = [-float("inf")] * CHANNELS
    clipped = [0] * CHANNELS
    frames = readings = 0
    t0 = time.monotonic()
    try:
        while True:
            if a.seconds and time.monotonic() - t0 >= a.seconds:
                break
            raw = rec.stdout.read(chunk)
            if not raw or len(raw) < frame_bytes:
                break
            buf = np.frombuffer(raw[:len(raw) // frame_bytes * frame_bytes],
                                dtype=DTYPE).reshape(-1, CHANNELS) / SCALE
            frames += buf.shape[0]
            readings += 1
            cells = []
            for ch in range(CHANNELS):
                x = buf[:, ch]
                rms, pk = db(float(np.sqrt(np.mean(x * x)))), db(float(np.max(np.abs(x))))
                peak[ch] = max(peak[ch], pk)
                if pk >= CLIP_DB:
                    clipped[ch] += 1
                cells.append("%s %6.1f |%s|" % ("LR"[ch] if ch < 2 else str(ch), rms, bar(rms)))
            sys.stdout.write("\r" + "  ".join(cells))
            sys.stdout.flush()
    except KeyboardInterrupt:
        pass
    finally:
        rec.send_signal(signal.SIGINT)
        err = (rec.stderr.read() or b"").decode(errors="replace").strip()
        rec.wait()
    print()

    # No frames is not silence. Without this the meter sits at -inf and reads as a quiet mic.
    if frames == 0:
        sys.exit("no audio arrived from %s — arecord said: %s"
                 % (a.device, err or "(nothing)"))

    print("%d reading(s), %.1f s of audio" % (readings, frames / SAMPLE_RATE_HZ))
    for ch in range(CHANNELS):
        name = "LR"[ch] if ch < 2 else str(ch)
        if peak[ch] < FLOOR_DB:
            print("  %s peak %6.1f dBFS — under the %.0f dBFS floor: nothing on this channel"
                  % (name, peak[ch], FLOOR_DB))
        else:
            tail = " · %d period(s) clipping" % clipped[ch] if clipped[ch] else ""
            print("  %s peak %6.1f dBFS%s" % (name, peak[ch], tail))
    if err:
        print("arecord: %s" % err)
    return 0


if __name__ == "__main__":
    sys.exit(main())
