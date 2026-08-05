# GENERADO por test/gen_constants.py desde constants.yaml -- NO EDITAR A MANO.
# Para cambiar un valor: editar constants.yaml y correr
#   python3 test/gen_constants.py --write
"""Constantes del Audio HAT (WM8960). Generado desde constants.yaml, no editar a mano."""

# --- codec ---
I2C_ADDR = 0x1a  # (netlist) WM8960 en i2c-1
# (design_target) nombre con el que enumera el driver; `aplay -l` lo tiene que mostrar
ALSA_CARD_NAME = 'wm8960soundcard'

# --- reloj ---
# (design_target) Hz SYSCLK directo de la familia 44.1 k, sin PLL. Lo genera minimal_clk desde
# userspace sobre GPCLK0. La placa NO tiene oscilador: se removio del layout.
MCLK_HZ = 11289600
MCLK_GPIO_BCM = 4  # (netlist) J3 pin 7 = BCM4 = GPCLK0 -> R26 -> U1 pin 11 (MCLK)
# (design_target) La Pi 5 NO sirve: minimal_clk pokea registros legacy del BCM283x que no
# existen detras del RP1, y sin oscilador onboard no hay MCLK.
PI_MODELOS_SOPORTADOS = ['Pi 1', 'Pi 2', 'Pi 3', 'Pi 4', 'Zero 2 W']

# --- captura ---
# (design_target) El formato correcto para arecord/aplay. Con S16_LE la captura parece rota y no
# lo esta: fue un diagnostico falso que costo tiempo. No usar `-f cd`.
SAMPLE_FORMAT = 'S32_LE'
# (derived) Hz Familia 44.1 k, que es la que permite MCLK_HZ. 48 kHz no esta disponible sin
# cambiar el reloj a 12.288 MHz y el device tree.
SAMPLE_RATE_HZ = 44100
CHANNELS = 2  # (netlist)

# --- jacks ---
# (netlist) Las entradas son single-ended: LINPUT1/2 y RINPUT1/2 quedaron sin conectar, asi que
# el modo diferencial es imposible en este hardware. J1 es el unico con MICBIAS, conmutado por
# SW1.
JACKS = (
    {'J5': {'dir': 'in', 'canal': 'L', 'pin': 'LINPUT3'},
     'J1': {'dir': 'in', 'canal': 'R', 'pin': 'RINPUT3'},
     'J4': {'dir': 'out', 'canal': 'LR', 'pin': 'HP_L/HP_R'},
     'J2': {'dir': 'out', 'canal': 'mono', 'pin': 'OUT3'}}
)
