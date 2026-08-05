#!/usr/bin/env python3
"""Audio HAT — aisla de que lado esta un cruce L/R. Corre en el Pi.

Cuando `audio_loopback.py` dice CRUZADO, esto dice donde. Muteando UNA entrada fisica por
vez y mandando siempre por el mismo canal, se separa el camino de ida del de vuelta:

  entrada L viva, R muteada  → si llega, la senal entro por la entrada L
  entrada L muteada, R viva  → si llega, la senal entro por la entrada R

Si mandas por ALSA-L y la senal entra por la entrada R, el cruce esta **antes** del ADC:
en el DAC, en el cableado o en el patch. Si entra por la L pero se captura en ALSA-R, el
cruce esta en la captura.

  python3 lr_bisect.py            # manda por ALSA-L
  python3 lr_bisect.py -c R       # manda por ALSA-R

Deja el mixer como lo encontro.
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
ESCALA = float(2 ** 31)
AMPLITUD = 0.30
DUR = 2.5
COMUN = ["-f", SAMPLE_FORMAT, "-r", str(SR), "-c", str(CHANNELS), "-t", "raw"]


def amix(control, valor):
    subprocess.run(["amixer", "-c1", "-q", "sset", control, valor], check=False)


def leer_mixer(control):
    r = subprocess.run(["amixer", "-c1", "sget", control], capture_output=True, text=True)
    for linea in r.stdout.splitlines():
        if "%]" in linea:
            return linea.split("[")[1].split("]")[0]
    return "100%"


def tono(canal, hz):
    n = int(SR * DUR)
    t = np.arange(n) / SR
    s = (AMPLITUD * np.sin(2 * np.pi * hz * t) * (ESCALA - 1)).astype("<i4")
    z = np.zeros(n, dtype="<i4")
    return np.column_stack([s, z] if canal == "L" else [z, s]).tobytes()


def db(x):
    return float("-inf") if x <= 0 else 20 * np.log10(x)


def corrida(canal, hz, card):
    with open("/tmp/lrb_tono.raw", "wb") as f:
        f.write(tono(canal, hz))
    if os.path.exists("/tmp/lrb_rec.raw"):
        os.remove("/tmp/lrb_rec.raw")     # nunca leer una captura anterior
    rec = subprocess.Popen(["arecord", "-D", card, *COMUN, "-d", "3", "/tmp/lrb_rec.raw"],
                           stderr=subprocess.DEVNULL)
    subprocess.run(["aplay", "-D", card, *COMUN, "/tmp/lrb_tono.raw"], stderr=subprocess.DEVNULL)
    rec.wait()
    d = np.fromfile("/tmp/lrb_rec.raw", dtype="<i4")
    if d.size < SR:
        return None
    d = d.reshape(-1, CHANNELS).astype(float) / ESCALA
    a = d[int(SR * 0.6):int(SR * 2.1)]
    return [db(float(np.sqrt((a[:, i] ** 2).mean()))) for i in range(CHANNELS)]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-c", "--canal", choices=("L", "R"), default="L")
    p.add_argument("-f", "--freq", type=float, default=1000.0)
    p.add_argument("-D", "--device", default="hw:1,0")
    p.add_argument("--piso", type=float, default=-60.0, help="dBFS bajo el cual no hay senal")
    a = p.parse_args()

    print("=== %s %s ===" % (BOARD_NAME, BOARD_REV))
    print("mandando por ALSA-%s a %g Hz\n" % (a.canal, a.freq))

    previo = {c: leer_mixer(c) for c in ("Left Input Line", "Right Input Line")}
    entro_por = None
    try:
        print("  %-30s %9s %9s" % ("configuracion", "ALSA L", "ALSA R"))
        for entrada, l, r in [("L", "100%", "0%"), ("R", "0%", "100%")]:
            amix("Left Input Line", l)
            amix("Right Input Line", r)
            niveles = corrida(a.canal, a.freq, a.device)
            if niveles is None:
                print("  captura vacia o corta")
                return 1
            print("  solo la entrada %s viva %-11s %9.1f %9.1f"
                  % (entrada, "", niveles[0], niveles[1]))
            if max(niveles) > a.piso:
                entro_por = (entrada, niveles)
    finally:
        for c, v in previo.items():
            amix(c, v)

    print()
    if entro_por is None:
        print("No llego senal por ninguna entrada. El cruce no es el problema: revisar que")
        print("el DAC este ruteado ('Out Mixer DAC' on) y que haya cable.")
        return 1

    entrada, niveles = entro_por
    capturada = "L" if niveles[0] > niveles[1] else "R"
    print("La senal entro por la entrada fisica %s y se capturo en ALSA-%s." % (entrada, capturada))
    if entrada == capturada == a.canal:
        print("Todo derecho: no hay cruce.")
        return 0
    if entrada != capturada:
        print("El ADC mapea la entrada %s a ALSA-%s: el cruce esta en la CAPTURA." % (entrada, capturada))
    else:
        print("Mandaste por ALSA-%s y salio por la salida fisica %s: el cruce esta ANTES del"
              % (a.canal, entrada))
        print("ADC — DAC, cables o patch. El netlist de las placas ya se verifico derecho,")
        print("asi que empeza por el patch y los cables de 4 vias.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
