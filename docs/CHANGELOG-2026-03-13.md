# Audio HAT — Changelog 2026-03-13

## SSSS213202 slide switch agregado

- **Alps SSSS213202** SPDT slide switch vertical — LCSC C115375
- Descargado con easyeda2kicad: símbolo, footprint, 3D model (STEP + WRL)
- Libraries registradas en `sym-lib-table` y `fp-lib-table`
- Ubicación: `libs/SSSS213202.*`
- Propósito: reemplazar JP1 (solder jumper) para MICBIAS on/off
- MICBIAS: ~2.97V del WM8960 para polarización de micrófonos electret

## Verificación BOM Audio HAT

Stock verificado 2026-03-13:
- WM8960 (C18752): 193 unidades, ~$11 c/u — stock bajo, monitorear
- 2 resistores básicos OOS: C22775 (100Ω), C25803 (100kΩ) — tienen alternativas abundantes
- Resto del BOM OK

## Pendiente

- [ ] Cablear SSSS213202 en esquemático (reemplazar JP1)
- [ ] Rutear MIDI THRU en PCB (si se activa)
- [ ] Completar migración 0603 (19 componentes, ver AUDIO-HAT-v1.1-UPGRADE.md)
- [ ] R27 (0Ω jumper en DCVDD): evaluar si eliminar y conectar directo
