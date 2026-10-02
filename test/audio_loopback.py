#!/usr/bin/env python3
"""Audio HAT — mide un loopback de salida a entrada. Corre en el Pi.

Manda un tono por UN canal a la vez y graba los dos. Responde tres cosas que no se
pueden ver escuchando: si pasa senal, si L es L y R es R, y cuanta se filtra al otro
canal.

  python3 audio_loopback.py            # 1 kHz, el mapeo de canales
  python3 audio_loopback.py -f 300     # otra frecuencia

NO sirve para cifras de calidad. El loopback full-duplex del WM8960 tiene un artefacto
propio — un pozo de ~5.7 dB alrededor de 1.6 kHz — que no es un defecto de la placa. La
planitud publicada se mide record-only, con fuente externa.

Los niveles se informan en dBFS: 0 dBFS es fondo de escala.
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

AMPLITUD = 0.30          # lejos del clip, para que el resultado no sea recorte
DUR_TONO = 3.0
DUR_GRABA = 4.0
VENTANA = (0.7, 2.7)     # tramo estable, sin el arranque del stream
PISO_UTIL_DB = -60.0     # por debajo de esto no hay senal, hay ruido

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
        os.remove(grabado)          # nunca leer una captura de una corrida anterior

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
    """Decide que significan dos niveles en dBFS. Pura a proposito: es la parte que
    puede estar mal aunque la medicion este bien, y asi se testea sin hardware.

    Devuelve (texto, [problemas])."""
    esperado, otro = (izq, der) if canal == "L" else (der, izq)
    nombre_otro = "R" if canal == "L" else "L"
    ps = []

    if max(esperado, otro) < PISO_UTIL_DB:
        v = "%s on either channel" % LOOPBACK_NO_SIGNAL
        ps.append("%s: no llega senal (max %.1f dBFS). Revisar que el DAC este ruteado y "
                  "las entradas no esten mudas." % (canal, max(esperado, otro)))
    elif otro > esperado + 20:
        # el caso que este script existe para encontrar
        v = "%s: out on %s, in on %s" % (LOOPBACK_CROSSED, canal, nombre_otro)
        ps.append("%s: la senal aparece en %s, %.1f dB por encima de %s"
                  % (canal, nombre_otro, otro - esperado, canal))
    elif esperado < PISO_UTIL_DB:
        v = "%s on %s" % (LOOPBACK_NO_SIGNAL, canal)
        ps.append("%s: no llega senal (%.1f dBFS)" % (canal, esperado))
    elif otro > esperado - 20:
        v = "canales mezclados (separacion %.1f dB)" % (esperado - otro)
        ps.append("%s: separacion de solo %.1f dB" % (canal, esperado - otro))
    else:
        v = "ok, %s %.1f dB" % (LOOPBACK_SEPARATION, esperado - otro)

    if max(esperado, otro) > -3.0:
        v += "  ⚠ cerca del clip"
        ps.append("%s: el nivel de entrada esta a %.1f dBFS, casi recortando: bajar "
                  "'Input Line' o la amplitud" % (canal, max(esperado, otro)))
    return v, ps


def _cabecera():
    """Toda salida de test dice contra que hardware corrio. La revision sale de
    constants.yaml, que la toma de la serigrafia: no se escribe a mano en ningun lado."""
    print("=== %s %s ===" % (BOARD_NAME, BOARD_REV))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-f", "--freq", type=float, default=1000.0)
    p.add_argument("-D", "--device", default="hw:1,0")
    a = p.parse_args()

    _cabecera()
    print("tono de %g Hz a %.0f%% de fondo de escala, %s @ %d Hz"
          % (a.freq, AMPLITUD * 100, SAMPLE_FORMAT, SAMPLE_RATE_HZ))
    print()
    print("  %-10s %10s %10s   %s" % ("envio", "RMS L", "RMS R", "veredicto"))

    problemas = []
    for canal in ("L", "R"):
        r = corrida(canal, a.freq, a.device)
        if r is None:
            print("  %-10s  captura vacia o corta" % (canal + " sola"))
            problemas.append("%s: no se grabo nada" % canal)
            continue
        izq, der = db(r[0]), db(r[1])
        v, ps = veredicto(canal, izq, der)
        problemas += ps
        print("  %-10s %9.1f %9.1f   %s" % (canal + " sola", izq, der, v))

    print()
    if problemas:
        print("PROBLEMAS:")
        for x in problemas:
            print("  - " + x)
        return 1
    print("El camino de ida y vuelta funciona y los canales no estan cruzados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
