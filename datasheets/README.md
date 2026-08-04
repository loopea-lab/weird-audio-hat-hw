# Datasheets — Audio HAT

Vendor datasheets for the parts fitted on the board. They ship with the repo so a spec
can be checked offline and a citation stays valid when a vendor URL moves.

Cite as `(datasheet <file> p.<n>)`.

| Part | Ref | File | Document |
|------|-----|------|----------|
| WM8960 — stereo codec | U1 | [`WM8960_datasheet.pdf`](WM8960_datasheet.pdf) | Cirrus Logic, Production Data Rev 4.1 |
| MCP1711T-33 — 3.3 V LDO | U4 | [`MCP1711.pdf`](MCP1711.pdf) | Microchip DS20005415D |
| SN74AHC1G14 — Schmitt inverter | U3 | [`SN74AHC1G14.pdf`](SN74AHC1G14.pdf) | TI |
| BC817 — NPN transistor | Q1 | [`BC817.pdf`](BC817.pdf) | Nexperia BC817 series |
| 1N4148W — signal diode | D1 | [`1N4148W.pdf`](1N4148W.pdf) | Diodes Inc DS30086 |
| SSSS213202 — SPDT slide switch (MICBIAS) | SW1 | [`SSSS213202.pdf`](SSSS213202.pdf) | Alps SSSS2 series |
| BFS17A — 3 GHz wideband NPN | Q2 | [`BFS17A.pdf`](BFS17A.pdf) | NXP · **DNP** |
| XO32 — 3.2×2.5 mm SMD oscillator | X1 | [`XO32.pdf`](XO32.pdf) | EuroQuartz · **DNP** |

## Notes

**U3 is a 74AHC1G14.** The schematic's Datasheet field points at the **LVC** part
(`sn74lvc1g14.pdf`). AHC and LVC differ in thresholds and speed — the file here is the
AHC one, which matches what is fitted.

**U3, X1, Y1 and Q2 are DNP.** The onboard oscillator was deliberately removed from the
layout: the symbols remain in the schematic but their footprints are not on the PCB.
The codec clocks from the Pi's GPCLK0 instead.

**Q2's schematic Datasheet field points at `BC818-D.pdf`**, which is a small-signal
NPN — not this 3 GHz wideband part. The file here is the right one.
