#!/usr/bin/env bash
# Audio HAT (WM8960) — automated bring-up checks.
# Runs on the Pi, after installing weird-audio-hat-driver and rebooting.
#
#   ./audio-bringup.sh            # every check, 5 s loopback
#   ./audio-bringup.sh -t 10      # 10 s loopback

set -u
HERE="$(cd "$(dirname "$0")" && pwd)"

# Constants come from the generated module.
k() {
  python3 -c "import sys; sys.path.insert(0, '$HERE'); import audio_hat_constants as c; print(eval(sys.argv[1], vars(c)))" "$1" \
    || { echo "could not read '$1' from audio_hat_constants.py (is it next to this script?)" >&2; exit 1; }
}
FMT=$(k SAMPLE_FORMAT)
RATE=$(k SAMPLE_RATE_HZ)
NCH=$(k CHANNELS)
I2C_ADDR=$(k "format(I2C_ADDR, 'x')")
CARD_NAME=$(k ALSA_CARD_NAME)
BOARD=$(k BOARD_NAME)
REV=$(k BOARD_REV)

LOOP_SECONDS=5
while getopts "t:h" opt; do
  case "$opt" in
    t) LOOP_SECONDS="$OPTARG" ;;
    h) echo "usage: $0 [-t loopback_seconds]"; exit 0 ;;
    *) exit 1 ;;
  esac
done

pass() { echo "  [OK]   $1"; }
fail() { echo "  [FAIL] $1"; FAILED=1; }
FAILED=0

echo "=== $BOARD $REV — bring-up ==="
echo "    revision as printed on the board; if yours says otherwise, this script is not for it"

# 1. I2C: the codec answers at 0x1A
echo "--- I2C (codec @ 0x$I2C_ADDR) ---"
if ! command -v i2cdetect >/dev/null; then
  echo "  i2cdetect not installed: sudo apt install i2c-tools"
elif i2cdetect -y 1 2>/dev/null | grep -qiE "(^| )$I2C_ADDR( |\$)"; then
  pass "codec found at 0x$I2C_ADDR (i2c-1)"
else
  fail "codec NOT found at 0x$I2C_ADDR. Check I2C is enabled, U1 soldering, the +3.3VA rail."
  i2cdetect -y 1 2>/dev/null || true
fi

# 2. ALSA enumeration
echo "--- ALSA (driver wm8960-soundcard) ---"
if aplay -l 2>/dev/null | grep -qi "$CARD_NAME"; then
  CARD=$(aplay -l 2>/dev/null | grep -i "$CARD_NAME" | head -1 | sed -E 's/^card ([0-9]+):.*/\1/')
  pass "playback enumerated (card $CARD)"
else
  fail "$CARD_NAME missing from 'aplay -l'. Install the driver and reboot."
  CARD=1
fi
if arecord -l 2>/dev/null | grep -qi "$CARD_NAME"; then
  pass "capture enumerated"
else
  fail "$CARD_NAME missing from 'arecord -l'."
fi

# 3. Capture-to-playback loopback
echo "--- Loopback ${LOOP_SECONDS}s (feed a signal into J5 = line in L, or J1 = line in R) ---"
if aplay -l 2>/dev/null | grep -qi "$CARD_NAME"; then
  echo "  arecord -f $FMT -D hw:${CARD} | aplay -D hw:${CARD}  (${LOOP_SECONDS}s)"
  timeout "${LOOP_SECONDS}" sh -c "arecord -f $FMT -r $RATE -c $NCH -D hw:${CARD} 2>/dev/null \
                                   | aplay -f $FMT -r $RATE -c $NCH -D hw:${CARD} 2>/dev/null"
  echo "  (did you hear it on line out / headphones?)"
else
  echo "  (skipped: no wm8960 card)"
fi

# 4. Capture to a file for inspection
echo "--- Capture to /tmp/wm8960_test.wav (5s) ---"
if aplay -l 2>/dev/null | grep -qi "$CARD_NAME"; then
  arecord -D "hw:${CARD},0" -f "$FMT" -r "$RATE" -c "$NCH" -d 5 /tmp/wm8960_test.wav 2>/dev/null \
    && pass "recorded /tmp/wm8960_test.wav (play with: aplay -D hw:${CARD},0 /tmp/wm8960_test.wav)" \
    || fail "arecord failed"
fi

echo "=== done: $([ "$FAILED" -eq 0 ] && echo 'all automated checks OK' || echo 'failures above') ==="
exit "$FAILED"
