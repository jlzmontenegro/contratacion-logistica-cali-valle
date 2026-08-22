#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regenera la instantánea del tablero desde la API de datos.gov.co.

Sólo usa la biblioteca estándar. Conserva los veredictos de la revisión manual
(datos/veredictos.json), que van asociados al id_contrato y no se recalculan.

Uso:  python scripts/actualizar.py
Salida: tablero/index.html, datos/01_contratos_logistica.csv, datos/02_modificaciones_detalle.csv
"""
import csv, json, os, re, sys, time, unicodedata, urllib.parse, urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://www.datos.gov.co"
NITS = ("890399011", "8903990113", "890399029", "8903990291", "8903990295")
CALI = ("890399011", "8903990113")
UA = {"User-Agent": "actualizador-contratacion-cali-valle/1.0 (+github actions)"}

# ---------------------------------------------------------------- utilidades
def cl(s):
    return re.sub(r"\s+", " ", (s or "")).strip()

def norm(s):
    s = unicodedata.normalize("NFD", (s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", s)

def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0

def pedir(url, intentos=4, espera=5):
    ultimo = None
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:            # noqa: BLE001
            ultimo = e
            print(f"    reintento {i+1}/{intentos}: {e}", file=sys.stderr)
            time.sleep(espera * (i + 1))
    raise ultimo

# ------------------------------------------------------- filtro y clasificación
FRAG = ["LOG","CATERING","ALIMENTA","REFRIGERIO","TIQUETE","MENSAJER","BODEGA","ALMACENAMIENTO","CUSTODIA",
        "TRANSPORTE","PASAJEROS","CAFETER","HOSPEDAJE","ALOJAMIENTO","EVENTO","FERIA","FESTIVAL","MERCADO",
        "BANQUETE","VIAJE","TURISTIC","MONTAJE","TARIMA","ESCENOGRAF","ARRIERIA","GRUA","CORREO",
        "CORRESPONDENCIA","COFFEE","MINUTA","RACION","CANJEABLE","PAE","JORNADA"]
FAMS = ["V1.9010","V1.90111","V1.90121","V1.80141","V1.81141","V1.90151","V1.78101","V1.78111","V1.78102","V1.9013"]
FAMCAT = {"V1.9010":"Alimentación y catering","V1.90111":"Transporte y viajes","V1.90121":"Transporte y viajes",
          "V1.80141":"Logística y eventos","V1.81141":"Logística y eventos","V1.90151":"Logística y eventos",
          "V1.78101":"Transporte y viajes","V1.78111":"Transporte y viajes","V1.78102":"Mensajería y correo",
          "V1.9013":"Logística y eventos"}
STRONG = {
 "Logística y eventos": r"(operador(a)?(es)? logistic|operacion logistic|servicio(s)? logistico(s)?|apoyo logistic|gestion logistic|logistica integral|prestacion de servicios logistic|servicios? tecnicos?[,;] logistic|logisticos?[,;] administrativos?|logistica para llevar a cabo|actividades operativas y logisticas|servicios logisticos y operativos|servicios? de apoyo a la gestion de logistica|adquirir servicios logisticos|montaje y desmontaje|tarima|escenograf|planeacion[,;] organizacion[,;] produccion|produccion[,;] promocion[,;] ejecucion|organizacion y ejecucion de una mision|eventos y jornadas de la secretaria)",
 "Alimentación y catering": r"(catering|complemento(s)? alimentari|suministro de alimentacion|servicio de alimentacion|alimentacion al personal|programa de alimentacion escolar|\bpae\b|racion(es)? alimentari|refrigerio|banquete|bonos? canjeables? de alimentacion|kits? de alimentos|kits? de mercado|minuta patron|logistica alimentaria)",
 "Transporte y viajes": r"(tiquete(s)? aere|agencia de viajes|servicio(s)? (especial(es)? )?de transporte|transporte (especial|terrestre|de pasajeros|de carga|escolar|de muestras|de insumos|de bienes|que permita)|prestar servicio de transporte|arrieria|vehiculos tipo grua|servicios turisticos|hospedaje|alojamiento)",
 "Mensajería y correo": r"(mensajeria (expresa|certificada|motorizada|de voz)|servicio(s)? de correo|distribucion de correspondencia|correo (electronico )?certificad)",
 "Almacenamiento y bodegaje": r"(bodegaje|almacenamiento y custodia|guarda y custodia|bodega para (el |la )?(almacenamiento|organizacion)|inmueble tipo bodega|uso de bodega(je)?|servicio de almacenamiento)",
 "Cafetería y suministros": r"(elementos de cafeteria|insumos de cafeteria|papeleria[^.]{0,40}cafeteria|cafeteria[^.]{0,40}(aseo|papeleria)|limpieza integral y cafeteria|servicio de cafeteria|coffee break)",
}
WEAK = r"(esfuerzos[^.]{0,80}logistic|humanos[^.]{0,40}logistic|logistic[oa]s? y financier|administrativos?[,;] operativos?[,;] logistic|apoyo a las actividades logistic|actividades logistic|soporte logistic|coordinacion logistic)"
EXC = r"(prestamo de uso|aprovechamiento economico|en calidad de comodato|entregar en comodato)"
TIPOS = [("Adición en valor", r"(adicion|adcion|mayor valor|cuotas al valor)"),
         ("Prórroga de plazo", r"(prorrog|amplia\w* el plazo|plazo de ejecucion hasta|extension del plazo)"),
         ("Aclaración o corrección", r"(aclara|corrige|correccion|subsanar|error de digitacion|otro si aclaratorio)"),
         ("Cesión", r"(cesion del contrato|cede el contrato)"),
         ("Suspensión", r"(suspension|se suspende)"),
         ("Liquidación o terminación", r"(liquidacion|terminacion anticipada)"),
         ("Ajuste presupuestal", r"(plan de pagos|informacion presupuestal|vigencias futuras)")]
CED = {"Cédula de Ciudadanía","Cédula de Extranjería","Tarjeta de Identidad","Pasaporte","Permiso por Protección Temporal"}

def tipo_de(t):
    n = norm(t)
    o = [k for k, rx in TIPOS if re.search(rx, n)]
    if o:
        return o
    return ["Sin descripción"] if n in ("no definido", "", "sin descripcion") else ["Otra"]

# ------------------------------------------------------------------ descargas
def traer_contratos():
    likes = " OR ".join(f"upper(`objeto_del_contrato`) like '%{f}%'" for f in FRAG)
    cats = " OR ".join(f"starts_with(`codigo_de_categoria_principal`,'{c}')" for c in FAMS)
    cols = ("`id_contrato`,`referencia_del_contrato`,`nit_entidad`,`nombre_entidad`,`objeto_del_contrato`,"
            "`codigo_de_categoria_principal`,`tipo_de_contrato`,`modalidad_de_contratacion`,`valor_del_contrato`,"
            "`valor_pagado`,`fecha_de_firma`,`fecha_de_inicio_del_contrato`,`fecha_de_fin_del_contrato`,"
            "`proveedor_adjudicado`,`tipodocproveedor`,`urlproceso`")
    nits = ",".join(f"'{n}'" for n in NITS)
    q = (f"SELECT {cols} WHERE `nit_entidad` IN ({nits}) "
         f"AND `fecha_de_firma` >= '2026-01-01T00:00:00'::floating_timestamp "
         f"AND ( {likes} OR {cats} ) ORDER BY `id_contrato` LIMIT 20000")
    return pedir(f"{API}/api/v3/views/jbjy-vk9h/query.json?" + urllib.parse.urlencode({"query": q}))

def traer_mods(ids):
    sel = ("id_contrato,identificador_modificacion,numero_version,estado_modificacion,fecha_de_aprobacion,"
           "valor_modificacion,dias_extendidos,proposito_modificacion")
    mejor = {}
    for i in range(0, len(ids), 70):
        lote = ids[i:i + 70]
        w = "id_contrato in(" + ",".join(f"'{x}'" for x in lote) + ")"
        url = f"{API}/resource/u8cx-r425.json?" + urllib.parse.urlencode({"$limit": 50000, "$select": sel, "$where": w})
        for x in pedir(url):
            k = x.get("identificador_modificacion")
            if not k:
                continue
            if k not in mejor or num(x.get("numero_version")) > num(mejor[k].get("numero_version")):
                mejor[k] = x
        time.sleep(0.4)
    por = {}
    for m in mejor.values():
        por.setdefault(m["id_contrato"], []).append({
            "t": tipo_de(m.get("proposito_modificacion")),
            "e": cl(m.get("estado_modificacion")),
            "f": (m.get("fecha_de_aprobacion") or "")[:10],
            "d": int(num(m.get("dias_extendidos"))),
            "vr": int(num(m.get("valor_modificacion"))),
            "p": cl(m.get("proposito_modificacion"))[:800]})
    for v in por.values():
        v.sort(key=lambda x: x["f"] or "")
    return por

# ------------------------------------------------------------------ armado
def clasificar(filas):
    salida = []
    for r in filas:
        t = norm(r.get("objeto_del_contrato"))
        if re.search(EXC, t):
            continue
        cod = r.get("codigo_de_categoria_principal") or ""
        cats = set()
        for k, rx in STRONG.items():
            if re.search(rx, t):
                cats.add(k)
        for p in FAMS:
            if cod.startswith(p):
                cats.add(FAMCAT[p])
        if not cats and re.search(WEAK, t):
            cats.add("Logística y eventos")
        if cats:
            salida.append((r, sorted(cats)))
    return salida

def construir(vivos, mods, veredictos, entmap, orgmap):
    out = []
    for r, cats in vivos:
        cid = r["id_contrato"]
        ms = mods.get(cid, [])
        u = r.get("urlproceso")
        u = u.get("url") if isinstance(u, dict) else u
        entf = cl(r.get("nombre_entidad"))
        d = {
            "id": cid, "ref": cl(r.get("referencia_del_contrato")),
            "ciu": "Cali" if r.get("nit_entidad") in CALI else "Valle",
            "ent": entmap.get(entf, entf[:44]), "entf": entf,
            "entl": orgmap.get(entf, entf),
            "prov": cl(r.get("proveedor_adjudicado")), "td": cl(r.get("tipodocproveedor")),
            "v": int(num(r.get("valor_del_contrato"))), "vp": int(num(r.get("valor_pagado"))),
            "ff": (r.get("fecha_de_firma") or "")[:10],
            "fi": (r.get("fecha_de_inicio_del_contrato") or "")[:10],
            "fn": (r.get("fecha_de_fin_del_contrato") or "")[:10],
            "mod": cl(r.get("modalidad_de_contratacion")), "tc": cl(r.get("tipo_de_contrato")),
            "un": cl(r.get("codigo_de_categoria_principal")),
            "obj": cl(r.get("objeto_del_contrato"))[:700], "url": u,
            "cats": cats, "g": "B" if cl(r.get("tipodocproveedor")) in CED else "A",
            "inc": 1, "rev": "Evidencia alta, no requirió revisión", "mot": "",
            "vi": None, "ad": None, "fad": "", "nuevo": False,
            "ms": ms, "dx": sum(m["d"] for m in ms if m["e"] == "Publicado"),
        }
        ver = veredictos.get(cid)
        if ver:
            d["rev"] = ver.get("revision_texto", d["rev"])
            if ver.get("motivo"):
                d["mot"] = ver["motivo"]
            if "incluido" in ver:
                d["inc"] = ver["incluido"]
            if ver.get("cats"):
                d["cats"] = ver["cats"]
            if ver.get("adicion") is not None:
                d["ad"] = ver["adicion"]
            if ver.get("valor_inicial") is not None:
                d["vi"] = ver["valor_inicial"]
            if ver.get("fuente_adicion"):
                d["fad"] = ver["fuente_adicion"]
        else:
            vs = [m["vr"] for m in ms if m["vr"] > 0]
            delta = (max(vs) - min(vs)) if vs else 0
            d["nuevo"] = True
            d["rev"] = "Sin revisar — apareció después del corte"
            d["mot"] = "Clasificado por el filtro automático; no ha pasado por revisión manual."
            if delta:
                d["ad"] = delta
                d["vi"] = d["v"] - delta
                d["fad"] = "Diferencia entre valores registrados en el dataset (piso, sin verificar en el expediente)"
        out.append(d)
    out.sort(key=lambda x: -x["v"])
    return out

# ------------------------------------------------------------------ escritura
def escribir_csv(regs):
    p1 = os.path.join(RAIZ, "datos", "01_contratos_logistica.csv")
    with open(p1, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["incluido","revision","motivo_revision","grupo","id_contrato","referencia","categorias",
                    "territorio","dependencia","entidad","proveedor","tipo_doc_prov","valor_inicial",
                    "adicion_cuantificada","pct_adicion_sobre_inicial","fuente_adicion","valor_contrato",
                    "valor_pagado","fecha_firma","fecha_inicio","fecha_fin","modalidad","tipo_contrato","unspsc",
                    "n_modif_registradas","n_modif_publicadas","dias_extendidos_total","objeto","url_proceso"])
        for d in regs:
            pct = f"{d['ad']/d['vi']*100:.1f}" if (d.get("ad") and d.get("vi")) else ""
            w.writerow(["SI" if d["inc"] else "NO", d["rev"], d["mot"], d["g"], d["id"], d["ref"],
                        "|".join(d["cats"]), d["ciu"], d["ent"], d["entf"], d["prov"], d["td"],
                        d.get("vi") or "", d.get("ad") or "", pct, d.get("fad") or "", d["v"], d["vp"],
                        d["ff"], d["fi"], d["fn"], d["mod"], d["tc"], d["un"], len(d["ms"]),
                        sum(1 for m in d["ms"] if m["e"] == "Publicado"), d["dx"], d["obj"], d["url"] or ""])
    p2 = os.path.join(RAIZ, "datos", "02_modificaciones_detalle.csv")
    with open(p2, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["incluido","id_contrato","referencia","dependencia","proveedor","categorias","valor_contrato",
                    "tipo_inferido","estado","fecha_aprobacion","valor_resultante","dias_extendidos","proposito_texto"])
        for d in regs:
            for m in d["ms"]:
                w.writerow(["SI" if d["inc"] else "NO", d["id"], d["ref"], d["ciu"] + " · " + d["ent"],
                            d["prov"], "|".join(d["cats"]), d["v"], "+".join(m["t"]), m["e"], m["f"],
                            m["vr"], m["d"], m["p"]])
    return p1, p2

def escribir_portada(regs):
    """Refresca los indicadores de la portada, entre los marcadores KPIS."""
    p = os.path.join(RAIZ, "index.html")
    if not os.path.isfile(p):
        return
    s = open(p, encoding="utf-8").read()
    inc = [d for d in regs if d["inc"]]
    conmod = sum(1 for d in inc if any(m["e"] == "Publicado" for m in d["ms"]))
    conad = sum(1 for d in inc if d.get("ad"))
    sumad = sum(d["ad"] for d in inc if d.get("ad"))

    def mil(n):
        return "$" + f"{round(n / 1000000):,}".replace(",", ".") + " M"

    filas = [
        ("hi", str(len(inc)), "contratos identificados"),
        ("", mil(sum(d["v"] for d in inc)), "valor contratado"),
        ("", str(conmod), "con modificación publicada"),
        ("warn", str(conad), "con adición en valor"),
        ("warn", mil(sumad), "sumaron esas adiciones"),
    ]
    cuerpo = "\n".join(
        f'  <div class="kpi {c}"><b>{n}</b><span>{l}</span></div>'.replace('kpi "', 'kpi"')
        for c, n, l in filas)
    bloque = "<!--KPIS-->\n<div class=\"kpis\">\n" + cuerpo + "\n</div>\n<!--/KPIS-->"
    nuevo, k = re.subn(r"<!--KPIS-->.*?<!--/KPIS-->", lambda _m: bloque, s, count=1, flags=re.S)
    if k and nuevo != s:
        open(p, "w", encoding="utf-8").write(nuevo)
        print("  portada actualizada")


def escribir_tablero(regs):
    tpl = open(os.path.join(RAIZ, "plantillas", "tablero.tpl.html"), encoding="utf-8").read()
    assert "__DATA__" in tpl, "la plantilla no tiene el marcador __DATA__"
    datos = json.dumps(regs, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    salida = os.path.join(RAIZ, "tablero", "index.html")
    cuerpo = tpl.replace("__DATA__", datos)
    i = cuerpo.index("</style>") + len("</style>")
    cab, cpo = cuerpo[:i], cuerpo[i:]
    nav = ('<nav class="sitenav"><a href="../index.html">← Inicio</a>'
           '<span>Contratación logística · Cali y Valle 2026</span></nav>\n'
           '<style>.sitenav{display:flex;gap:16px;align-items:center;justify-content:space-between;flex-wrap:wrap;'
           'padding:10px clamp(14px,2.5vw,32px);font:500 12.5px/1.4 "IBM Plex Mono",ui-monospace,monospace;'
           'background:var(--surface-2,#EDF1F0);border-bottom:1px solid var(--hair,#DCE3E1);color:var(--muted,#5A6A68)}'
           '.sitenav a{color:var(--accent,#0E5C58);text-decoration:none;font-weight:600}'
           '.sitenav a:hover{text-decoration:underline}</style>')
    if "<meta charset" not in cab:
        cab = '<meta charset="utf-8">\n' + cab
    doc = '<!doctype html>\n<html lang="es">\n<head>\n' + cab + "\n</head>\n<body>\n" + nav + "\n" + cpo + "\n</body>\n</html>\n"
    open(salida, "w", encoding="utf-8").write(doc)
    return salida

# ------------------------------------------------------------------ principal
def main():
    ver_path = os.path.join(RAIZ, "datos", "veredictos.json")
    veredictos = json.load(open(ver_path, encoding="utf-8"))
    entmap = json.load(open(os.path.join(RAIZ, "datos", "dependencias.json"), encoding="utf-8"))
    orgmap = json.load(open(os.path.join(RAIZ, "datos", "organismos.json"), encoding="utf-8"))
    orgmap.pop("_nota", None)
    print(f"veredictos cargados: {len(veredictos)}")

    print("descargando contratos…")
    filas = traer_contratos()
    print(f"  {len(filas)} filas del prefiltro")
    vivos = clasificar(filas)
    print(f"  {len(vivos)} clasificados")

    # rescate: contratos ya revisados que el prefiltro no alcanza (p. ej. si cambió el objeto)
    presentes = {r["id_contrato"] for r, _ in vivos}
    faltan = [i for i in veredictos if i not in presentes]
    if faltan:
        print(f"  rescatando {len(faltan)} contratos revisados que el prefiltro no trajo…")
        cols = ("`id_contrato`,`referencia_del_contrato`,`nit_entidad`,`nombre_entidad`,`objeto_del_contrato`,"
                "`codigo_de_categoria_principal`,`tipo_de_contrato`,`modalidad_de_contratacion`,`valor_del_contrato`,"
                "`valor_pagado`,`fecha_de_firma`,`fecha_de_inicio_del_contrato`,`fecha_de_fin_del_contrato`,"
                "`proveedor_adjudicado`,`tipodocproveedor`,`urlproceso`")
        for i in range(0, len(faltan), 70):
            lote = faltan[i:i + 70]
            ids = ",".join(f"'{x}'" for x in lote)
            q = f"SELECT {cols} WHERE `id_contrato` IN ({ids}) LIMIT 200"
            for r in pedir(f"{API}/api/v3/views/jbjy-vk9h/query.json?" + urllib.parse.urlencode({"query": q})):
                ver = veredictos.get(r["id_contrato"], {})
                vivos.append((r, ver.get("cats") or ["Logística y eventos"]))
            time.sleep(0.4)
        print(f"  {len(vivos)} tras el rescate")

    print("descargando modificaciones…")
    mods = traer_mods([r["id_contrato"] for r, _ in vivos])
    print(f"  {sum(len(v) for v in mods.values())} modificaciones en {len(mods)} contratos")

    regs = construir(vivos, mods, veredictos, entmap, orgmap)
    sin_nombre = sorted({d["entf"] for d in regs if d["entl"] == d["entf"]})
    if sin_nombre:
        print(f"  aviso: {len(sin_nombre)} entidad(es) sin nombre completo en datos/organismos.json")
        for e in sin_nombre:
            print(f"    · {e}")
    inc = [d for d in regs if d["inc"]]
    nuevos = [d for d in regs if d["nuevo"]]
    print(f"registros: {len(regs)} | incluidos: {len(inc)} | sin revisar: {len(nuevos)}")
    print(f"valor incluido: ${sum(d['v'] for d in inc):,}")

    escribir_tablero(regs)
    escribir_csv(regs)
    escribir_portada(regs)
    meta = {"generado": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "contratos": len(regs), "incluidos": len(inc), "sin_revisar": len(nuevos),
            "valor_incluido": sum(d["v"] for d in inc)}
    json.dump(meta, open(os.path.join(RAIZ, "datos", "instantanea.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("listo:", meta)

if __name__ == "__main__":
    main()
