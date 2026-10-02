"""La lógica de decisión de audio_loopback.py, con números sintéticos. Corre en la laptop.

Existe por una falla concreta: con la señal cruzada, el script imprimió "SIN SENAL"
mientras los niveles mostraban −2.3 dBFS en el otro canal. **La medición estaba bien y la
conclusión mal**, que es el peor caso — un número correcto con una historia falsa
encima. Estos casos son los que un banco no puede reproducir a pedido.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
pytest.importorskip("numpy", reason="audio_loopback importa numpy")
from audio_loopback import veredicto  # noqa: E402
from audio_hat_constants import LOOPBACK_CROSSED, LOOPBACK_NO_SIGNAL  # noqa: E402


# (canal, dB en L, dB en R, fragmento que tiene que aparecer, ¿es problema?)
CASOS = [
    # el caso real medido: mando por L y aparece en R a -2.3 dBFS
    ("L", -71.9, -2.3, LOOPBACK_CROSSED, True),
    ("R", -2.3, -82.0, LOOPBACK_CROSSED, True),
    # el mismo cruce con niveles sanos, sin aviso de clip
    ("L", -88.9, -10.6, LOOPBACK_CROSSED, True),
    # lo que se espera de un loopback bien cableado
    ("L", -10.5, -88.0, "ok", False),
    ("R", -88.0, -10.5, "ok", False),
    # nada conectado, o el DAC sin rutear: los dos canales en el piso
    ("L", -84.2, -84.5, LOOPBACK_NO_SIGNAL + " on either channel", True),
    # llega a los dos por igual: canales sumados en algún lado
    ("L", -12.0, -13.0, "mezclados", True),
    # el canal correcto pero rozando el fondo de escala
    ("L", -1.0, -80.0, "clip", True),
]


@pytest.mark.parametrize("canal,izq,der,fragmento,es_problema", CASOS,
                         ids=[f"{c}-{i}-{d}" for c, i, d, _, _ in CASOS])
def test_el_veredicto_dice_lo_que_muestran_los_numeros(canal, izq, der, fragmento, es_problema):
    texto, problemas = veredicto(canal, izq, der)
    assert fragmento in texto, f"con L={izq} R={der} dijo {texto!r}"
    assert bool(problemas) == es_problema, f"con L={izq} R={der}: problemas={problemas}"


def test_una_senal_fuerte_nunca_se_reporta_como_ausente():
    """La regresión exacta. Cualquier canal por encima del piso significa que hay señal:
    lo que falte será mapeo, no ausencia."""
    for canal in ("L", "R"):
        for izq, der in [(-2.3, -80.0), (-80.0, -2.3), (-10.0, -70.0), (-70.0, -10.0)]:
            texto, _ = veredicto(canal, izq, der)
            assert LOOPBACK_NO_SIGNAL not in texto, (
                f"{canal} con L={izq} R={der} tiene señal de sobra y dijo {texto!r}")


def test_el_cruce_se_nombra_en_las_dos_direcciones():
    """Mandar por L y recibir en R, y al revés, tienen que decir a dónde fue."""
    t_l, _ = veredicto("L", -80.0, -10.0)
    t_r, _ = veredicto("R", -10.0, -80.0)
    assert "out on L, in on R" in t_l
    assert "out on R, in on L" in t_r
