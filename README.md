# Weird Audio HAT

Stereo audio HAT for Raspberry Pi based on the WM8960 codec. Part of the Weird modular system.

## What is this

A sound card for Raspberry Pi with:
- WM8960 stereo codec (24-bit, 48kHz)
- I2S digital audio + I2C control
- 4x 3.5mm TRS jacks (stereo line in, stereo line out, headphone out, mic in)
- 2x20 pin RPi HAT connector
- 24MHz crystal oscillator

## Physical Stack

```
┌─────────────────────────┐
│      Control Panel       │  ← ControlPanelBoard (weird-mcp-inputs)
├─────────────────────────┤
│      MCP Inputs HAT      │  ← McpInputBoard (weird-mcp-inputs)
├─────────────────────────┤
│      Audio HAT           │  ← This board
├─────────────────────────┤
│      Raspberry Pi        │  ← Pi Zero 2W
└─────────────────────────┘
```

## Branches

| Branch | Version | Description |
|--------|---------|-------------|
| `main` | v1.0 | Stable, THT components, 2-layer PCB |
| `dev` | v1.1 | SMD migration, 4-layer PCB for JLCPCB assembly |

## Layer Stack (dev)

| Layer | Purpose |
|-------|---------|
| F.Cu | SMD components + signal routing |
| In1.Cu | GND plane |
| In2.Cu | Power plane (+5V, +VREGIN) |
| B.Cu | Signal routing |

## Main Components

| Ref | Part | Package | Description | LCSC |
|-----|------|---------|-------------|------|
| U1 | WM8960 | QFN-32 | Stereo codec, I2S + I2C | C18752 |
| U4 | MCP1711T-33 | SOT-23-5 | 3.3V LDO regulator | C79527 |
| U3 | 74AHC1G14 | SOT-353 | Schmitt trigger inverter | — |
| Q1, Q2 | BC817 | SOT-23 | NPN transistor | C2137 |
| D1 | 1N4148W | SOD-123 | Signal diode | — |
| J1, J2, J4, J5 | AudioJack3 | 3.5mm TRS | Audio connectors | C18594 |
| J3 | 2x20 Header | 2.54mm | RPi HAT connector | — |
| FB1-FB3 | Ferrite Bead | 0805 | 220Ω-1kΩ @ 100MHz | C85835 |
| Y1 | 24MHz | XO32 | Crystal oscillator | — |
| CP1-CP4 | 220µF 16V | — | Bulk decoupling | — |

## Interfaces

**I2S (digital audio):**
- BCLK — Bit clock
- LRCLK — Left/Right word clock
- DACDAT — DAC data (Pi → codec)
- ADCDAT — ADC data (codec → Pi)

**I2C (control):**
- SCL — Clock
- SDA — Data
- Address: 0x1A

## Power

| Rail | Source | Purpose |
|------|--------|---------|
| +5V | RPi GPIO header | Main supply |
| +3.3V | MCP1711T-33 LDO | Digital logic |
| +3.3VA | Filtered from +3.3V | Analog supply (codec) |

Total current draw: ~70mA max.

## Audio Specs

- Line output: 1V RMS (0 dBV), load ≥ 1kΩ (≥ 10kΩ recommended)
- Headphone output: 32Ω load
- Output coupling: -3dB < 10Hz
- Mic bias: selectable via jumper JP1

## Datasheets

- [WM8960](https://datasheet.lcsc.com/lcsc/2304140030_Cirrus-Logic-WM8960CGEFL-RV_C18752.pdf) — Stereo codec (Cirrus Logic)
- [MCP1711](https://ww1.microchip.com/downloads/aemDocuments/documents/OTH/ProductDocuments/DataSheets/20005415D.pdf) — LDO 3.3V regulator (Microchip)
- [SN74AHC1G14](https://www.ti.com/lit/ds/symlink/sn74ahc1g14.pdf) — Single Schmitt-trigger inverter (TI)
- [BC817](https://assets.nexperia.com/documents/data-sheet/BC817_SER.pdf) — NPN transistor (Nexperia)
- [1N4148W](https://www.diodes.com/assets/Datasheets/BAV16W_1N4148W.pdf) — Fast switching diode (Diodes Inc)

## Current Status

Schematic design is advanced. PCB placement and routing are pending for the v1.1 SMD/4-layer revision.

## Known Issues (v1.0)

- Crosstalk at -60dB between input jacks J1 and J7 (fix: replace jacks or increase spacing)
- Ring/tip bridging with mono cables (fix: cut ring pin on input jacks)

## Project Structure

```
weird-audio-hat-hw/
├── WM_RB-HAT.kicad_sch      # Main schematic
├── WM_RB-HAT.kicad_pcb      # PCB layout
├── WM_RB-HAT.kicad_pro      # KiCad project file
├── datasheets/               # Component datasheets
├── libs/                     # Custom symbol libraries
├── libs.pretty/              # Custom footprint libraries
├── libs.3dshapes/            # 3D models
├── production/               # Manufacturing outputs
└── releases/v1.0/            # v1.0 release artifacts
```
