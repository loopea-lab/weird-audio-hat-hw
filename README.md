# Weird Audio HAT R1.1

A WM8960 sound card for the Raspberry Pi: stereo line in and out, headphone amp, mono out and
a microphone input with bias. It shows up as a normal ALSA sound card.

![Weird Audio HAT](WM_RB-HAT.png)

## Specifications

| | |
|---|---|
| Codec | WM8960, stereo, 24-bit |
| Sample rates | 44.1 kHz family (master clock 11.2896 MHz) |
| Sample formats | `S16_LE`, `S24_LE`, `S32_LE` |
| Control | I2C, address `0x1A` |
| Frequency response | ±0.5 dB, 100 Hz – 8 kHz † |
| Output THD (DAC) | 0.003 % at 1 kHz † |
| Crosstalk between inputs | −67 to −92 dB across the band † |
| MICBIAS | ~3 V (0.9 × AVDD) † |
| Inputs | single-ended, line level |
| Outputs | stereo line / headphone, mono |

† measured on fabricated boards.

## Requirements

**Raspberry Pi Zero 2W on 32-bit Raspberry Pi OS** (tested). Pi 1, Zero, 2 and 3 on a 32-bit OS
should work but are untested. **Not supported:** Pi 4, Pi 5, or any 64-bit OS — the codec has no
oscillator, and the helper that clocks it from the Pi's GPCLK0 only knows the 32-bit register
addresses of the older chips.

48 kHz needs a different clock and a device-tree change.

## Connectors

Names as printed on the board. The schematic designator is in the last column.

| On the board | Type | Carries | Schematic |
|---|---|---|---|
| **IN L** | 3.5 mm jack | Line in L (tip) | J5 |
| **IN R** | 3.5 mm jack | Line in R (tip), or an electret mic with **MIC-R BIAS** on | J1 |
| **OUT L/R** | 3.5 mm stereo jack | Line / headphone out — tip L, ring R \* | J4 |
| **OUT MONO** | 3.5 mm jack | Mono out (tip) — the sum of L and R | J2 |
| **MIC-R BIAS** | slide switch | Puts MICBIAS on **IN R** | SW1 |
| 4-pin header, left edge | 1×4 header | Line in from a panel — 1 GND · 2 R · 3 GND · 4 L | J6 |
| 4-pin header, right edge | 1×4 header | Line out to a panel — 1 GND · 2 R · 3 GND · 4 L | J7 |
| 40-pin header | 2×20 Pi header | I2C (3, 5) · I2S (12, 35, 38, 40) · GPCLK0 (7) · 3.3 V / 5 V. Free GPIOs (BCM): 5–17 and 22–27, including SPI0 and the UART; 0 and 1 are left for a HAT ID EEPROM | J3 |

Left and right edges as seen from the top, with the jacks facing you.

\* R1.1: L and R are swapped; the driver's `DAC L/R Swap` control corrects it.

## Using it

Install the driver: [weird-audio-hat-driver](https://github.com/loopea-lab/weird-audio-hat-driver).
It covers recording, playback, routing and gain.

- **Inputs are single-ended** (LINPUT3 / RINPUT3). The codec's differential mode is not wired.
- **Headphone out** is AC-coupled; it drives 32 Ω headphones or a line input.
- **IN R is line or microphone, chosen by the MIC-R BIAS switch:** off = line input; on = electret
  mic input, biased at ~3 V through 1 kΩ. The driver keeps `MIC Bias` on, so the switch is the only
  thing to set. Don't plug a line source into IN R with the switch on: it loads the source and puts
  3 V DC on it.

## Troubleshooting

**No sound card in `aplay -l`.** Not on a Pi 5? Driver installed? Do not add
`dtoverlay=wm8960-soundcard` to `config.txt` — the driver's service loads it. `i2cdetect -y 1`
should show `1a`.

**Recording fails or is silent.** Use `S32_LE` (or `S16_LE` / `S24_LE`); `S24_3LE` fails and
looks like dead hardware. If the format is right, the input path is muted — see the driver README.

## Combine it with

- [Weird Piano HAT](https://github.com/loopea-lab/weird-piano-hat) — keys and pots, an
  instrument with Pure Data.
- [Weird MCP Inputs](https://github.com/loopea-lab/weird-mcp-inputs) + Control Board + panel —
  a Eurorack module. The two 4-pin headers carry audio to the panel; the stacking header passes the MCP's
  signals through, so use a good one.

## License

CC BY-SA 4.0 — see [`LICENSE`](LICENSE). Datasheets in `datasheets/` are copyright of their manufacturers.

Copyright © 2024–2026 Weird Electronics / Loopea Lab.
