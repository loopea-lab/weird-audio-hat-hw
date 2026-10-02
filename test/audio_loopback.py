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
from audio_hat_constants import (BOARD_NAME, BOARD_REV, CHANNELS, LOOPBACK_CROSSED,  # noqa: E402
                                 LOOPBACK_NO_SIGNAL, LOOPBACK_SEPARATION, SAMPLE_FORMAT,
                                 SAMPLE_RATE_HZ)

AMPLITUD = 0.30          # well below clipping
DUR_TONO = 3.0
DUR_GRABA = 4.0
VENTANA = (0.7, 2.7)     # steady part, past the stream start
PISO_UTIL_DB = -60.0     # below this there is only noise

DTYPE = {"S32_LE": "<i4", "S16_LE": "<i2"}[SAMPLE_FORMAT]
ESCALA = float(2 ** (8 * np.dtype(DTYPE).itemsize - 1))


def tono(canal, hz):
    n = int(SAMPLE_RATE_HZ * DUR_TONO)
    t = np.arange(n) / SAMPLE_RATE_HZ
    s = (AMPLITUD * np.sin(2 * np.pi * hz * t) * (ESCALA - 1)).astype(DTYPE)
    z = np.zeros(n, dtype=DTYPE)
    return np.column_stack([s, z] if canal == "L" else [z, s]).tobytes()


def db(x):
    return float("-inf") if x <= 0 else 20 * np.log10(x)


def corrida(canal, hz, card):
    crudo = "/tmp/lb_tono_%s.raw" % canal
    grabado = "/tmp/lb_rec_%s.raw" % canal
    with open(crudo, "wb") as f:
        f.write(tono(canal, hz))
    if os.path.exists(grabado):
        os.remove(grabado)          # never read a previous run's capture

    comun = ["-f", SAMPLE_FORMAT, "-r", str(SAMPLE_RATE_HZ), "-c", str(CHANNELS), "-t", "raw"]
    rec = subprocess.Popen(["arecord", "-D", card, *comun, "-d", str(int(DUR_GRABA)), grabado],
                           stderr=subprocess.DEVNULL)
    subprocess.run(["aplay", "-D", card, *comun, crudo], stderr=subprocess.DEVNULL)
    rec.wait()

    d = np.fromfile(grabado, dtype=DTYPE)
    if d.size < SAMPLE_RATE_HZ * CHANNELS:
        return None
    d = d.reshape(-1, CHANNELS).astype(float) / ESCALA
    a = d[int(SAMPLE_RATE_HZ * VENTANA[0]):int(SAMPLE_RATE_HZ * VENTANA[1])]
    return [float(np.sqrt((a[:, i] ** 2).mean())) for i in range(CHANNELS)]


def veredicto(canal, izq, der):
    """What two dBFS levels mean, as (text, [problems]). Pure, so it is tested without hardware."""
    esperado, otro = (izq, der) if canal == "L" else (der, izq)
    nombre_otro = "R" if canal == "L" else "L"
    ps = []

    if max(esperado, otro) < PISO_UTIL_DB:
        v = "%s on either channel" % LOOPBACK_NO_SIGNAL
        ps.append("%s: no signal arrives (max %.1f dBFS). Check the DAC is routed and the "
                  "inputs are not muted." % (canal, max(esperado, otro)))
    elif otro > esperado + 20:
        v = "%s: out on %s, in on %s" % (LOOPBACK_CROSSED, canal, nombre_otro)
        ps.append("%s: the signal shows up on %s, %.1f dB above %s"
                  % (canal, nombre_otro, otro - esperado, canal))
    elif esperado < PISO_UTIL_DB:
        v = "%s on %s" % (LOOPBACK_NO_SIGNAL, canal)
        ps.append("%s: no signal arrives (%.1f dBFS)" % (canal, esperado))
    elif otro > esperado - 20:
        v = "channels mixed (separation %.1f dB)" % (esperado - otro)
        ps.append("%s: only %.1f dB of separation" % (canal, esperado - otro))
    else:
        v = "ok, %s %.1f dB" % (LOOPBACK_SEPARATION, esperado - otro)

    if max(esperado, otro) > -3.0:
        v += "  ⚠ near clipping"
        ps.append("%s: the input is at %.1f dBFS, nearly clipping: lower "
                  "'Input Line' or the amplitude" % (canal, max(esperado, otro)))
    return v, ps


def _cabecera():
    print("=== %s %s ===" % (BOARD_NAME, BOARD_REV))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-f", "--freq", type=float, default=1000.0)
    p.add_argument("-D", "--device", default="hw:1,0")
    a = p.parse_args()

    _cabecera()
    print("%g Hz tone at %.0f%% of full scale, %s @ %d Hz"
          % (a.freq, AMPLITUD * 100, SAMPLE_FORMAT, SAMPLE_RATE_HZ))
    print()
    print("  %-10s %10s %10s   %s" % ("sent", "RMS L", "RMS R", "verdict"))

    problemas = []
    for canal in ("L", "R"):
        r = corrida(canal, a.freq, a.device)
        if r is None:
            print("  %-10s  empty or short capture" % (canal + " only"))
            problemas.append("%s: nothing was recorded" % canal)
            continue
        izq, der = db(r[0]), db(r[1])
        v, ps = veredicto(canal, izq, der)
        problemas += ps
        print("  %-10s %9.1f %9.1f   %s" % (canal + " only", izq, der, v))

    print()
    if problemas:
        print("PROBLEMS:")
        for x in problemas:
            print("  - " + x)
        return 1
    print("The round trip works and the channels are not crossed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
