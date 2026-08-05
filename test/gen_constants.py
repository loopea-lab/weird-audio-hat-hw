#!/usr/bin/env python3
"""Genera constants.py a partir de constants.yaml. Corre en la LAPTOP.

El YAML es la unica fuente autorada. constants.py se genera porque la Pi no trae
PyYAML y los scripts de bring-up tienen que correr en una SD recien flasheada.

  python3 gen_constants.py --write    regenera constants.py
  python3 gen_constants.py --check    falla si constants.py quedo desactualizado

Este archivo es identico en los tres repos de placa a proposito: un test cruzado
verifica que no divergieron.
"""

import argparse
import os
import pprint
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
YAML = os.path.join(os.path.dirname(HERE), "constants.yaml")
OUT = os.path.join(HERE, "constants.py")

BANNER = "# GENERADO por test/gen_constants.py desde constants.yaml -- NO EDITAR A MANO."


WIDTH = 96


def comment(text):
    """Envuelve una nota larga en lineas de comentario."""
    return textwrap.wrap(text, width=WIDTH, initial_indent="# ", subsequent_indent="# ",
                         break_long_words=False, break_on_hyphens=False)


def assignment(name, value, fmt=None):
    """`NOMBRE = valor`, partido con pprint si no entra en una linea."""
    if fmt == "hex" and isinstance(value, int):
        return ["%s = %#x" % (name, value)]
    one = "%s = %r" % (name, value)
    if len(one) <= WIDTH:
        return [one]
    body = pprint.pformat(value, width=WIDTH - 4, sort_dicts=False)
    return ["%s = (" % name] + ["    " + ln for ln in body.splitlines()] + [")"]


def load():
    try:
        import yaml
    except ImportError:
        sys.exit("Falta PyYAML: pip install pyyaml  (solo hace falta para regenerar)")
    with open(YAML) as f:
        return yaml.safe_load(f)


def render(doc):
    lines = [
        BANNER,
        "# Para cambiar un valor: editar constants.yaml y correr",
        "#   python3 test/gen_constants.py --write",
        '"""%s"""' % doc.get("_module_doc", "Constantes de la placa."),
        "",
    ]
    for group, entries in doc.items():
        if group.startswith("_"):
            continue
        lines.append("# --- %s ---" % group)
        for name, e in entries.items():
            note = " ".join(e.get("note", "").split())
            unit = (" " + e["unit"]) if e.get("unit") else ""
            head = "(%s)%s%s" % (e.get("source", "?"), unit, (" " + note) if note else "")
            body = assignment(name, e["value"], e.get("format"))
            trailing = "%s  # %s" % (body[0], head)
            if len(body) == 1 and len(trailing) <= WIDTH:
                lines.append(trailing)
            else:
                lines.extend(comment(head))   # nota larga o valor partido: el comentario va arriba
                lines.extend(body)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--write", action="store_true", help="regenera constants.py")
    p.add_argument("--check", action="store_true", help="falla si esta desactualizado")
    a = p.parse_args()
    if not (a.write or a.check):
        p.error("elegir --write o --check")

    want = render(load())
    have = open(OUT).read() if os.path.exists(OUT) else None

    if a.check:
        if have != want:
            print("constants.py esta desactualizado respecto de constants.yaml.",
                  file=sys.stderr)
            print("Regenerar con: python3 test/gen_constants.py --write", file=sys.stderr)
            return 1
        print("constants.py en sync con constants.yaml")
        return 0

    if have == want:
        print("constants.py ya estaba en sync")
        return 0
    with open(OUT, "w") as f:
        f.write(want)
    print("constants.py regenerado (%d lineas)" % want.count("\n"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
