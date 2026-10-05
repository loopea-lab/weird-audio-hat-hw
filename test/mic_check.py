#!/usr/bin/env python3
"""Records a few seconds from the mic input and plays it straight back. Runs on the Pi.

The fastest way to know an electret works is to hear yourself. The level is measured as well,
because hearing nothing does not say WHICH half is dead: a mic that captured -8 dBFS and a
silent playback is an output problem, and that distinction is the whole point of printing the
number next to the sound.

    ./mic_check.py                  # 4 s, record then play
    ./mic_check.py --seconds 8
    ./mic_check.py --no-play        # measure only, for a headless run

Before running: SW1 ON puts MIC Bias on J1, and J1 is RINPUT3, so the mic lands on R.
"""
import argparse
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import numpy as np
except ImportError:
    sys.exit("needs numpy: sudo apt install python3-numpy")

from audio_hat_constants import (ALSA_CARD_NAME, BOARD_NAME, BOARD_REV, CHANNELS,  # noqa: E402
                                 JACKS, MICBIAS_V, SAMPLE_FORMAT, SAMPLE_RATE_HZ)
from audio_loopback import DTYPE, FLOOR_DB, SCALE, db  # noqa: E402

CLIP_DB = -0.5
QUIET_DB = -40.0        # above the floor but too low to call a working mic


def mic_jack():
    """The input jack on R, which is where MIC Bias and SW1 act."""
    return next((j for j, d in JACKS.items()
                 if d["dir"] == "in" and d["channel"] == "R"), "J1")


def out_jack():
    return next((j for j, d in JACKS.items() if d["channel"] == "LR"), "J4")


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("-D", "--device", default="hw:%s" % ALSA_CARD_NAME)
    p.add_argument("--seconds", type=float, default=4.0)
    p.add_argument("--no-play", action="store_true")
    a = p.parse_args()

    common = ["-D", a.device, "-f", SAMPLE_FORMAT, "-r", str(SAMPLE_RATE_HZ),
              "-c", str(CHANNELS), "-t", "raw", "-q"]
    mic, out = mic_jack(), out_jack()

    print("=== %s %s ===" % (BOARD_NAME, BOARD_REV))
    print("%s  %d Hz %s %dch" % (a.device, SAMPLE_RATE_HZ, SAMPLE_FORMAT, CHANNELS))
    print("mic on %s (SW1 ON feeds it ~%.2f V of MIC Bias) · it lands on R" % (mic, MICBIAS_V))
    print("playback on %s\n" % out)

    fd, path = tempfile.mkstemp(suffix=".raw")
    os.close(fd)
    try:
        print("recording %.0f s — talk now" % a.seconds)
        rec = subprocess.run(["arecord", *common, "-s", str(int(a.seconds * SAMPLE_RATE_HZ)), path],
                             capture_output=True, text=True)
        size = os.path.getsize(path)
        frame_bytes = np.dtype(DTYPE).itemsize * CHANNELS
        # An empty capture is not a quiet mic. Without this the verdict would be "nothing on R"
        # for a card that never opened.
        if size < frame_bytes:
            sys.exit("nothing was captured from %s — arecord said: %s"
                     % (a.device, (rec.stderr or "").strip() or "(nothing)"))

        buf = np.fromfile(path, dtype=DTYPE)
        buf = buf[:buf.size // CHANNELS * CHANNELS].reshape(-1, CHANNELS) / SCALE
        got_s = buf.shape[0] / SAMPLE_RATE_HZ
        if got_s < a.seconds * 0.5:
            print("  short capture: %.2f s of the %.0f s asked for" % (got_s, a.seconds))

        print("\n%.2f s captured" % got_s)
        verdict = {}
        for ch in range(CHANNELS):
            x = buf[:, ch]
            rms, pk = db(float(np.sqrt(np.mean(x * x)))), db(float(np.max(np.abs(x))))
            name = "LR"[ch] if ch < 2 else str(ch)
            tail = ""
            if pk >= CLIP_DB:
                tail = " — CLIPPING, turn the input gain down"
            elif pk < FLOOR_DB:
                tail = " — under the %.0f dBFS floor: nothing here" % FLOOR_DB
            elif pk < QUIET_DB:
                tail = " — above the floor but very low; check SW1 and the gain"
            print("  %s  rms %6.1f  peak %6.1f dBFS%s" % (name, rms, pk, tail))
            verdict[name] = pk

        if a.no_play:
            return 0 if verdict.get("R", -999) >= QUIET_DB else 1

        print("\nplaying it back on %s" % out)
        play = subprocess.run(["aplay", *common, path], capture_output=True, text=True)
        if play.returncode != 0:
            # The mic's own verdict stands: this failure is the output path, not the mic.
            print("  aplay failed (%s): the capture above is still valid — this is the output"
                  % ((play.stderr or "").strip() or "no message"))
            return 1

        r = verdict.get("R", -999)
        if r < FLOOR_DB:
            print("\nThe mic captured nothing on R. In order: SW1 ON, the plug fully seated in "
                  "%s, and MIC Bias in the mixer (check_mixer turns it on)." % mic)
            return 1
        if r < QUIET_DB:
            print("\nThe mic is alive but quiet (%.1f dBFS peak). Raise the input gain or move "
                  "closer before blaming the capsule." % r)
            return 1
        print("\nThe mic works: %.1f dBFS peak on R, and you just heard it." % r)
        return 0
    finally:
        os.unlink(path)


if __name__ == "__main__":
    sys.exit(main())
