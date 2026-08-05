#!/usr/bin/env bash
# Audio HAT (WM8960) — checks automatizables de bring-up.
# Corre EN el Raspberry Pi, despues de instalar el driver (weird-audio-hat-driver) y rebootear.
# Los pasos de multimetro / osciloscopio son manuales: estan en el manual del modulo.
#
# Uso:
#   ./audio-bringup.sh            # corre todos los checks (loopback 5s)
#   ./audio-bringup.sh -t 10      # loopback de 10s

set -u
HERE="$(cd "$(dirname "$0")" && pwd)"

# Las constantes salen de constants.yaml via el modulo generado: este script no las repite.
k() {
  python3 -c "import sys; sys.path.insert(0, '$HERE'); import audio_hat_constants as c; print(eval(sys.argv[1], vars(c)))" "$1" \
    || { echo "no se pudo leer '$1' de audio_hat_constants.py (¿esta al lado de este script?)" >&2; exit 1; }
}
FMT=$(k SAMPLE_FORMAT)
RATE=$(k SAMPLE_RATE_HZ)
NCH=$(k CHANNELS)
I2C_ADDR=$(k "format(I2C_ADDR, 'x')")
CARD_NAME=$(k ALSA_CARD_NAME)

LOOP_SECONDS=5
while getopts "t:h" opt; do
  case "$opt" in
    t) LOOP_SECONDS="$OPTARG" ;;
    h) echo "uso: $0 [-t segundos_loopback]"; exit 0 ;;
    *) exit 1 ;;
  esac
done

pass() { echo "  [OK]   $1"; }
fail() { echo "  [FALLA] $1"; FAILED=1; }
FAILED=0

echo "=== Audio HAT (WM8960) bring-up ==="

# 1. I2C: el codec debe aparecer en 0x1A
echo "--- I2C (codec @ 0x$I2C_ADDR) ---"
if ! command -v i2cdetect >/dev/null; then
  echo "  i2cdetect no instalado: sudo apt install i2c-tools"
elif i2cdetect -y 1 2>/dev/null | grep -qiE "(^| )$I2C_ADDR( |\$)"; then
  pass "codec detectado en 0x$I2C_ADDR (i2c-1)"
else
  fail "codec NO detectado en 0x$I2C_ADDR. Revisar I2C habilitado, soldadura U1, riel +3.3VA."
  i2cdetect -y 1 2>/dev/null || true
fi

# 2. Enumeracion ALSA: la card la nombra constants.yaml
echo "--- ALSA (driver wm8960-soundcard) ---"
if aplay -l 2>/dev/null | grep -qi "$CARD_NAME"; then
  CARD=$(aplay -l 2>/dev/null | grep -i "$CARD_NAME" | head -1 | sed -E 's/^card ([0-9]+):.*/\1/')
  pass "playback enumerado (card $CARD)"
else
  fail "$CARD_NAME no aparece en 'aplay -l'. Instalar driver y rebootear."
  CARD=1
fi
if arecord -l 2>/dev/null | grep -qi "$CARD_NAME"; then
  pass "capture enumerado"
else
  fail "$CARD_NAME no aparece en 'arecord -l'."
fi

# 3. Loopback capture->playback
echo "--- Loopback ${LOOP_SECONDS}s (inyectar senal en J5 = line in L, o J1 = line in R) ---"
if aplay -l 2>/dev/null | grep -qi "$CARD_NAME"; then
  echo "  arecord -f $FMT -D hw:${CARD} | aplay -D hw:${CARD}  (${LOOP_SECONDS}s)"
  timeout "${LOOP_SECONDS}" sh -c "arecord -f $FMT -r $RATE -c $NCH -D hw:${CARD} 2>/dev/null \
                                   | aplay -f $FMT -r $RATE -c $NCH -D hw:${CARD} 2>/dev/null"
  echo "  (escuchaste el loopback en line-out/headphone? marcar en el checklist)"
else
  echo "  (saltado: sin card wm8960)"
fi

# 4. Captura a archivo para inspeccion
echo "--- Captura a /tmp/wm8960_test.wav (5s) ---"
if aplay -l 2>/dev/null | grep -qi "$CARD_NAME"; then
  arecord -D "hw:${CARD},0" -f "$FMT" -r "$RATE" -c "$NCH" -d 5 /tmp/wm8960_test.wav 2>/dev/null \
    && pass "grabado /tmp/wm8960_test.wav (reproducir con: aplay -D hw:${CARD},0 /tmp/wm8960_test.wav)" \
    || fail "arecord fallo"
fi

echo "=== fin: $([ "$FAILED" -eq 0 ] && echo 'todos los checks automaticos OK' || echo 'hubo fallas, revisar arriba') ==="
echo "Pasos manuales (multimetro/scope): ver el manual del modulo."
exit "$FAILED"
