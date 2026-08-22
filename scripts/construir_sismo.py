#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Construye sismo/index.html inyectando datos/sismo.json en plantillas/sismo.tpl.html.

Se ejecuta después de scripts/sismo.py. Sólo biblioteca estándar.
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sismo import aplicar_notas   # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NAV = ('<nav class="sitenav"><a href="../index.html">← Inicio</a>'
       '<span>Contratación logística · Cali y Valle 2026</span></nav>\n'
       '<style>.sitenav{display:flex;gap:16px;align-items:center;justify-content:space-between;flex-wrap:wrap;'
       'padding:10px clamp(14px,2.5vw,32px);font:500 12.5px/1.4 "IBM Plex Mono",ui-monospace,monospace;'
       'background:var(--surface-2,#EDF1F0);border-bottom:1px solid var(--hair,#DCE3E1);color:var(--muted,#5A6A68)}'
       '.sitenav a{color:var(--accent,#0E5C58);text-decoration:none;font-weight:600}'
       '.sitenav a:hover{text-decoration:underline}</style>')


def main():
    p_datos = os.path.join(RAIZ, "datos", "sismo.json")
    p_tpl = os.path.join(RAIZ, "plantillas", "sismo.tpl.html")
    if not os.path.isfile(p_datos):
        print("no existe datos/sismo.json; corre antes scripts/sismo.py", file=sys.stderr)
        return 1

    datos = aplicar_notas(json.load(open(p_datos, encoding="utf-8")))
    tpl = open(p_tpl, encoding="utf-8").read()
    for marca in ("__SISMO__", "__ORG__"):
        if marca not in tpl:
            print(f"la plantilla no tiene el marcador {marca}", file=sys.stderr)
            return 1

    # el mismo mapa de nombres completos que usa el tablero, para que la pagina
    # del sismo nombre los organismos igual que el resto del sitio
    org = {}
    p_org = os.path.join(RAIZ, "datos", "organismos.json")
    try:
        org = json.load(open(p_org, encoding="utf-8"))
        org.pop("_nota", None)
    except Exception as e:                # noqa: BLE001
        print(f"aviso: no se pudo leer organismos.json ({e}); se usaran los nombres crudos",
              file=sys.stderr)

    crudo = json.dumps(datos, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    cuerpo = (tpl.replace("__SISMO__", crudo)
                 .replace("__ORG__", json.dumps(org, ensure_ascii=False, separators=(",", ":"))
                                         .replace("<", "\\u003c")))

    i = cuerpo.index("</style>") + len("</style>")
    cab, cpo = cuerpo[:i], cuerpo[i:]
    if "<meta charset" not in cab:
        cab = '<meta charset="utf-8">\n' + cab

    doc = ('<!doctype html>\n<html lang="es">\n<head>\n' + cab +
           "\n</head>\n<body>\n" + NAV + "\n" + cpo + "\n</body>\n</html>\n")

    destino = os.path.join(RAIZ, "sismo")
    os.makedirs(destino, exist_ok=True)
    salida = os.path.join(destino, "index.html")
    open(salida, "w", encoding="utf-8").write(doc)

    r = datos.get("resumen", {})
    print(f"sismo/index.html escrito ({round(len(doc)/1024)} KB) · "
          f"{r.get('respuesta', 0)} de respuesta, {r.get('afectados', 0)} afectados · "
          f"cobertura hasta {datos.get('cobertura_hasta', '?')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
