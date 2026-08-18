#!/usr/bin/env python3
"""Genera los archivos derivados de esta placa. Corre en la LAPTOP.

Dos salidas, las dos generadas y ninguna editable a mano:

  el modulo de constantes de la placa, en test/   desde constants.yaml
  CONNECTORS.md                                  desde el .kicad_pcb -- que net tiene cada pin de cada
                              conector, leido del COBRE. No existia en ningun lado y su
                              ausencia costo una tarde entera de diagnostico (O-28).

El YAML es la unica fuente autorada. El modulo se genera porque la Pi no trae
PyYAML y los scripts de bring-up tienen que correr en una SD recien flasheada.

  python3 gen_constants.py --write    regenera el modulo
  python3 gen_constants.py --check    falla si el modulo quedo desactualizado

Este archivo es identico en los tres repos de placa a proposito: un test cruzado
verifica que no divergieron.
"""

import argparse
import glob
import os
import re
import pprint
import subprocess
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
YAML = os.path.join(os.path.dirname(HERE), "constants.yaml")
def _salida():
    """El modulo se llama por placa a proposito: copiar el de otra placa a la Pi tiene
    que fallar al importar, no dar valores de otra cosa en silencio."""
    import yaml
    with open(YAML) as f:
        nombre = yaml.safe_load(f).get("_module_name")
    if not nombre:
        sys.exit("constants.yaml no declara _module_name")
    return os.path.join(HERE, nombre + ".py")

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


PCB_BANNER = ("<!-- GENERADO por test/gen_constants.py desde los .kicad_pcb. "
              "NO EDITAR A MANO. -->")

# KiCad escribe el net de un pad de dos formas segun la version: (net 12 "GND") y
# (net "GND"). Un patron que exija el numero devuelve vacio en el otro caso, en silencio.
_PAD = re.compile(r'\(pad "([^"]+)"(?:(?!\(pad ).)*?\(net (?:\d+ )?"([^"]*)"\)', re.S)


def _footprints(texto):
    inicios = [m.start() for m in re.finditer(r'\n\t\(footprint ', texto)] + [len(texto)]
    for i in range(len(inicios) - 1):
        yield texto[inicios[i]:inicios[i + 1]]


def conectores(pcb):
    """[(referencia, valor, {pin: net})] de los conectores de un .kicad_pcb."""
    texto = open(pcb, errors="replace").read()
    out = []
    for b in _footprints(texto):
        r = re.search(r'\(property "Reference" "(J[^"]*)"', b)
        if not r:
            continue
        pads = dict(_PAD.findall(b))
        if len(pads) < 2:
            continue
        v = re.search(r'\(property "Value" "([^"]*)"', b)
        out.append((r.group(1), v.group(1) if v else "", pads))
    return sorted(out, key=lambda x: (len(x[2]), x[0]))


def pcbs_versionados(raiz):
    """Los `.kicad_pcb` que git trackea, que son los que forman parte del diseño.

    Leer del disco traga lo que KiCad deja al lado: `.backups/`, `_autosave-*`, y lo que
    invente la próxima version. Una lista negra a mano nunca está completa — el autosave
    agregó 356 líneas y una placa inexistente a CONNECTORS.md. Con git, `.gitignore` es la
    única fuente de verdad y la clase entera desaparece.
    """
    r = subprocess.run(["git", "-C", raiz, "ls-files", "-z", "*.kicad_pcb"],
                       capture_output=True, text=True)
    assert r.returncode == 0, f"git ls-files falló en {raiz}: {r.stderr.strip()}"
    pcbs = sorted(os.path.join(raiz, p) for p in r.stdout.split("\0") if p)
    assert pcbs, f"git no trackea ningún .kicad_pcb en {raiz} — ¿es un repo?"
    return pcbs


def render_conectores(raiz):
    pcbs = pcbs_versionados(raiz)
    lineas = [PCB_BANNER, "",
              "# Conectores — qué net tiene cada pin",
              "",
              "Leído del **cobre**, que es lo que responde \"¿qué hay en la placa que tengo",
              "en la mano?\". Para saber qué *hace* cada conector, ver el manual.",
              ""]
    total = 0
    for pcb in pcbs:
        cs = conectores(pcb)
        if not cs:
            continue
        lineas += ["## `%s`" % os.path.basename(pcb), ""]
        for ref, val, pads in cs:
            lineas.append("### %s%s" % (ref, " — %s" % val if val else ""))
            lineas += ["", "| Pin | Net |", "|---|---|"]
            for pin in sorted(pads, key=lambda x: (len(x), x)):
                lineas.append("| %s | `%s` |" % (pin, pads[pin]))
            lineas.append("")
            total += 1
    if not total:
        raise SystemExit("no encontre ningun conector con nets en %s" % raiz)
    return "\n".join(lineas).rstrip() + "\n"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--write", action="store_true", help="regenera el modulo de constantes")
    p.add_argument("--check", action="store_true", help="falla si esta desactualizado")
    a = p.parse_args()
    if not (a.write or a.check):
        p.error("elegir --write o --check")

    raiz = os.path.dirname(HERE)
    out = _salida()
    conn_out = os.path.join(raiz, "CONNECTORS.md")
    want = render(load())
    want_conn = render_conectores(raiz)
    have = open(out).read() if os.path.exists(out) else None
    have_conn = open(conn_out).read() if os.path.exists(conn_out) else None

    if a.check:
        if have_conn != want_conn:
            print("CONNECTORS.md esta desactualizado respecto del .kicad_pcb.", file=sys.stderr)
            print("Regenerar con: python3 test/gen_constants.py --write", file=sys.stderr)
            return 1
        if have != want:
            print(os.path.basename(out) + " esta desactualizado respecto de constants.yaml.",
                  file=sys.stderr)
            print("Regenerar con: python3 test/gen_constants.py --write", file=sys.stderr)
            return 1
        print(os.path.basename(out) + " en sync con constants.yaml")
        return 0

    if have_conn != want_conn:
        with open(conn_out, "w") as f:
            f.write(want_conn)
        print("CONNECTORS.md regenerado (%d lineas)" % want_conn.count("\n"))
    if have == want:
        print(os.path.basename(out) + " ya estaba en sync")
        return 0
    with open(out, "w") as f:
        f.write(want)
    print("%s regenerado (%d lineas)" % (os.path.basename(out), want.count("\n")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
