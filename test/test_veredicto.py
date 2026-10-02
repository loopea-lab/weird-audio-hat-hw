"""audio_loopback.py's verdict logic on synthetic levels. Runs on the laptop."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
pytest.importorskip("numpy", reason="audio_loopback importa numpy")
from audio_loopback import veredicto  # noqa: E402
from audio_hat_constants import LOOPBACK_CROSSED, LOOPBACK_NO_SIGNAL  # noqa: E402


# (channel, dB on L, dB on R, text that must appear, is it a problem?)
CASOS = [
    # measured case: sent on L, shows up on R at -2.3 dBFS
    ("L", -71.9, -2.3, LOOPBACK_CROSSED, True),
    ("R", -2.3, -82.0, LOOPBACK_CROSSED, True),
    # the same crossing at sane levels, no clipping warning
    ("L", -88.9, -10.6, LOOPBACK_CROSSED, True),
    # a correctly wired loopback
    ("L", -10.5, -88.0, "ok", False),
    ("R", -88.0, -10.5, "ok", False),
    # nothing connected, or the DAC unrouted: both channels at the floor
    ("L", -84.2, -84.5, LOOPBACK_NO_SIGNAL + " on either channel", True),
    # equal on both: channels summed somewhere
    ("L", -12.0, -13.0, "mixed", True),
    # right channel, but near full scale
    ("L", -1.0, -80.0, "clip", True),
]


@pytest.mark.parametrize("canal,izq,der,fragmento,es_problema", CASOS,
                         ids=[f"{c}-{i}-{d}" for c, i, d, _, _ in CASOS])
def test_el_veredicto_dice_lo_que_muestran_los_numeros(canal, izq, der, fragmento, es_problema):
    texto, problemas = veredicto(canal, izq, der)
    assert fragmento in texto, f"with L={izq} R={der} it said {texto!r}"
    assert bool(problemas) == es_problema, f"with L={izq} R={der}: problems={problemas}"


def test_una_senal_fuerte_nunca_se_reporta_como_ausente():
    """Any channel above the floor means there is signal; what is wrong is mapping, not absence."""
    for canal in ("L", "R"):
        for izq, der in [(-2.3, -80.0), (-80.0, -2.3), (-10.0, -70.0), (-70.0, -10.0)]:
            texto, _ = veredicto(canal, izq, der)
            assert LOOPBACK_NO_SIGNAL not in texto, (
                f"{canal} with L={izq} R={der} has plenty of signal and said {texto!r}")


def test_el_cruce_se_nombra_en_las_dos_direcciones():
    """Both directions of a crossing must say where the signal went."""
    t_l, _ = veredicto("L", -80.0, -10.0)
    t_r, _ = veredicto("R", -10.0, -80.0)
    assert "out on L, in on R" in t_l
    assert "out on R, in on L" in t_r
