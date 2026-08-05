"""Invariantes de las constantes de esta placa. Corre en la laptop: `pytest test/`.

constants.yaml es la unica fuente autorada. El modulo de constantes se genera desde el YAML y
los scripts lo importan en vez de repetir valores. Estos tests verifican esa cadena.

Este archivo es identico en los tres repos de placa a proposito: cada repo tiene que
poder clonarse y verificarse solo. Un test cruzado, en la doc interna, confirma que las
copias no driftearon.
"""

import ast
import re
import subprocess
import sys
from pathlib import Path

import pytest

TEST = Path(__file__).resolve().parent
REPO = TEST.parent
YAML = REPO / "constants.yaml"

FUENTES_VALIDAS = {"netlist", "cobre", "bom", "datasheet", "design_target", "derived"}


def cargar():
    yaml = pytest.importorskip("yaml", reason="hace falta PyYAML para leer constants.yaml")
    return yaml.safe_load(YAML.read_text())


def nombre_modulo():
    """El modulo generado se llama por placa: copiar el de otra placa tiene que fallar
    al importar, no dar valores de otra cosa en silencio."""
    n = cargar().get("_module_name")
    assert n, "constants.yaml no declara _module_name"
    return n


def entradas():
    out = {}
    for grupo, es in cargar().items():
        if not grupo.startswith("_"):
            out.update(es)
    return out


def test_el_yaml_existe_y_tiene_constantes():
    """Guarda sobre el descubrimiento: sin esto todo lo de abajo pasaria de vacio."""
    assert YAML.exists(), f"falta {YAML.name}"
    assert len(entradas()) >= 3, "el YAML no declara casi nada — ¿cambio el formato?"


def test_lo_generado_esta_en_sync_con_el_yaml():
    r = subprocess.run([sys.executable, str(TEST / "gen_constants.py"), "--check"],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_lo_generado_avisa_que_no_se_edita_a_mano():
    generado = TEST / (nombre_modulo() + ".py")
    assert generado.exists(), f"falta {generado.name}"
    assert "NO EDITAR A MANO" in generado.read_text().splitlines()[0]


def test_el_modulo_generado_lleva_el_nombre_de_la_placa():
    """Un modulo llamado a secas es un nombre que cualquier placa puede tener. Copiar el
    equivocado a la Pi daba valores de otra placa sin que nada avisara."""
    n = nombre_modulo()
    assert n != "constants", "el modulo no puede llamarse 'constants' a secas"
    assert (TEST / (n + ".py")).exists()


def test_toda_constante_dice_de_donde_sale():
    """Un valor sin `source` es un numero que nadie puede rastrear."""
    malas = []
    for nombre, e in entradas().items():
        src = e.get("source")
        if src is None:
            malas.append(f"{nombre}: sin `source`")
        elif src not in FUENTES_VALIDAS:
            malas.append(f"{nombre}: `source: {src}` no esta en {sorted(FUENTES_VALIDAS)}")
    assert not malas, "\n".join(malas)


def test_ninguna_constante_es_una_medicion():
    """Las cifras medidas son por-tanda y por-placa; no describen el diseno."""
    malas = [n for n, e in entradas().items() if e.get("source") == "medido"]
    assert not malas, "constantes marcadas como medidas: " + ", ".join(malas)


def test_todo_lo_generado_es_importable():
    import importlib
    sys.path.insert(0, str(TEST))
    try:
        importlib.import_module(nombre_modulo())
    finally:
        sys.path.pop(0)


def scripts():
    return [p for p in sorted(TEST.glob("*.py"))
            if p.name not in {nombre_modulo() + ".py", "gen_constants.py"}
            and not p.name.startswith("test_")]


@pytest.mark.parametrize("s", scripts(), ids=lambda p: p.name)
def test_ningun_script_repite_un_valor_que_ya_esta_autorado(s):
    """La excepcion permitida es la que se declara: un script que no puede importar
    (porque se pipea por stdin) tiene que decirlo en su cabecera, y entonces un test
    cruzado se encarga de atarlo."""
    txt = s.read_text(errors="replace")
    cabeza = "\n".join(txt.splitlines()[:14])
    if "no hay ningun archivo al lado" in cabeza or "se pipea por stdin" in cabeza:
        pytest.skip(f"{s.name} declara que no puede importar")

    # valores escalares autorados que un script no deberia volver a escribir
    autorados = {n: e["value"] for n, e in entradas().items()
                 if isinstance(e["value"], (int, float)) and not isinstance(e["value"], bool)
                 and abs(e["value"]) >= 1000}
    repetidos = []
    cuerpo = "\n".join(ln for ln in txt.splitlines() if not ln.lstrip().startswith("#"))
    for nombre, val in autorados.items():
        literal = str(int(val)) if float(val).is_integer() else str(val)
        if re.search(rf'(?<![\w.]){re.escape(literal)}(?![\w.])', cuerpo) and nombre not in cuerpo:
            repetidos.append(f"{s.name} escribe {literal} en vez de importar {nombre}")
    assert not repetidos, "\n".join(repetidos)


@pytest.mark.parametrize("s", scripts(), ids=lambda p: p.name)
def test_todo_script_es_sintacticamente_valido(s):
    ast.parse(s.read_text(errors="replace"), filename=str(s))
