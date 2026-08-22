#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rastreador del sismo del 10 de agosto de 2026.

Busca sobre TODO el universo de contratación de Cali y el Valle — sin filtro de
categoría — los contratos y las modificaciones que aluden al evento. La palabra
"sismo" casi no aparece en los objetos contractuales: la contratación lo nombra
como "los hechos acaecidos el 10 de agosto" o "la emergencia ocurrida", así que
se busca por varias frases y también por el mecanismo jurídico (urgencia
manifiesta, calamidad pública).

Salida: datos/sismo.json
"""
import json, os, re, sys, time, unicodedata, urllib.parse, urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://www.datos.gov.co"
NITS = ("890399011", "8903990113", "890399029", "8903990291", "8903990295")
CALI = ("890399011", "8903990113")
UA = {"User-Agent": "rastreador-sismo-cali-valle/1.0"}
EVENTO = "2026-08-10"
DESDE = "2026-08-01T00:00:00"

def cl(s):
    return re.sub(r"\s+", " ", (s or "")).strip()

def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0

def pedir(url, intentos=4, espera=6, tiempo=280):
    ultimo = None
    for i in range(intentos):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=tiempo) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:            # noqa: BLE001
            ultimo = e
            print(f"    reintento {i+1}/{intentos}: {e}", file=sys.stderr)
            time.sleep(espera * (i + 1))
    raise ultimo

def v3(q):
    return pedir(f"{API}/api/v3/views/jbjy-vk9h/query.json?" + urllib.parse.urlencode({"query": q}))

def soda(ds, where, sel=None, lim=50000, **kw):
    p = {"$where": where, "$limit": lim}
    if sel:
        p["$select"] = sel
    return pedir(f"{API}/resource/{ds}.json?" + urllib.parse.urlencode(p), **kw)

# frases con que la contratación nombra el evento (sin tildes: el LIKE no las normaliza)
FRASES = ["ACAECID", "10 DE AGOSTO DE 2026", "EMERGENCIA OCURRIDA", "SISMO", "TERREMOTO", "TEMBLOR"]
MECANISMO = ["URGENCIA MANIFIESTA", "CALAMIDAD P"]
NITS_SQL = ",".join(f"'{n}'" for n in NITS)
COLS = ("`id_contrato`,`referencia_del_contrato`,`nit_entidad`,`nombre_entidad`,`objeto_del_contrato`,"
        "`valor_del_contrato`,`fecha_de_firma`,`fecha_de_inicio_del_contrato`,`fecha_de_fin_del_contrato`,"
        "`proveedor_adjudicado`,`tipodocproveedor`,`codigo_de_categoria_principal`,`modalidad_de_contratacion`,"
        "`justificacion_modalidad_de`,`tipo_de_contrato`,`urlproceso`")

def url_de(r):
    u = r.get("urlproceso")
    return u.get("url") if isinstance(u, dict) else u

def ficha(r, motivo, evidencia):
    return {"id": r["id_contrato"], "ref": cl(r.get("referencia_del_contrato")),
            "ciu": "Cali" if r.get("nit_entidad") in CALI else "Valle",
            "ent": cl(r.get("nombre_entidad")), "prov": cl(r.get("proveedor_adjudicado")),
            "td": cl(r.get("tipodocproveedor")), "v": int(num(r.get("valor_del_contrato"))),
            "ff": (r.get("fecha_de_firma") or "")[:10],
            "fi": (r.get("fecha_de_inicio_del_contrato") or "")[:10],
            "fn": (r.get("fecha_de_fin_del_contrato") or "")[:10],
            "mod": cl(r.get("modalidad_de_contratacion")), "just": cl(r.get("justificacion_modalidad_de")),
            "tc": cl(r.get("tipo_de_contrato")), "un": cl(r.get("codigo_de_categoria_principal")),
            "obj": cl(r.get("objeto_del_contrato"))[:900], "url": url_de(r),
            "motivo": motivo, "evidencia": evidencia}

def buscar_contratos():
    """Contratos cuyo texto alude al evento, o suscritos por urgencia/calamidad."""
    campos = ["objeto_del_contrato", "descripcion_del_proceso", "justificacion_modalidad_de"]
    cond = " OR ".join(f"upper(`{c}`) like '%{f}%'" for f in FRASES + MECANISMO for c in campos)
    q = (f"SELECT {COLS} WHERE `nit_entidad` IN ({NITS_SQL}) "
         f"AND `fecha_de_firma` >= '2026-01-01T00:00:00'::floating_timestamp AND ({cond}) "
         f"ORDER BY `fecha_de_firma` DESC LIMIT 1000")
    filas = v3(q)
    out = []
    for r in filas:
        txt = " ".join([(r.get("objeto_del_contrato") or ""), (r.get("justificacion_modalidad_de") or "")]).upper()
        explicito = any(f in txt for f in FRASES)
        posterior = (r.get("fecha_de_firma") or "")[:10] >= EVENTO
        if explicito and posterior:
            out.append(ficha(r, "respuesta", "El objeto alude expresamente a los hechos del 10 de agosto"))
        elif posterior and any(m in txt for m in MECANISMO):
            out.append(ficha(r, "mecanismo", "Suscrito por urgencia manifiesta o calamidad pública tras el evento"))
        elif explicito:
            out.append(ficha(r, "previo", "Menciona sismo o calamidad, pero se firmó antes del 10 de agosto"))
    return out

def buscar_modificaciones():
    """Modificaciones cuya justificación alude al evento (búsqueda nacional, luego filtrada)."""
    sel = ("id_contrato,identificador_modificacion,numero_version,estado_modificacion,fecha_de_aprobacion,"
           "valor_modificacion,dias_extendidos,proposito_modificacion")
    # sobre el dataset nacional sólo se buscan las frases que responden rápido;
    # las tres son suficientes: los textos que invocan el sismo contienen alguna.
    mejor = {}
    for f in ["SISMO", "TERREMOTO", "EMERGENCIA OCURRIDA", "10 DE AGOSTO DE 2026"]:
        w = f"upper(proposito_modificacion) like '%{f}%' AND fecha_de_aprobacion >= '{DESDE}'"
        try:
            for x in soda("u8cx-r425", w, sel, 5000, intentos=2, espera=4, tiempo=100):
                k = x.get("identificador_modificacion")
                if not k:
                    continue
                if k not in mejor or num(x.get("numero_version")) > num(mejor[k].get("numero_version")):
                    mejor[k] = x
        except Exception as e:            # noqa: BLE001
            print(f"    '{f}' falló: {e}", file=sys.stderr)
        time.sleep(1)
    print(f"    {len(mejor)} modificaciones candidatas en todo el país")
    ids = sorted({m["id_contrato"] for m in mejor.values()})
    nuestros = {}
    for i in range(0, len(ids), 70):
        lote = ",".join(f"'{x}'" for x in ids[i:i + 70])
        try:
            for r in v3(f"SELECT {COLS} WHERE `id_contrato` IN ({lote}) LIMIT 200"):
                if r.get("nit_entidad") in NITS:
                    nuestros[r["id_contrato"]] = r
        except Exception as e:            # noqa: BLE001
            print(f"    lote falló: {e}", file=sys.stderr)
        time.sleep(0.4)
    out = []
    for cid, r in nuestros.items():
        ms = [m for m in mejor.values() if m["id_contrato"] == cid]
        ms.sort(key=lambda x: (x.get("fecha_de_aprobacion") or ""))
        d = ficha(r, "afectado", "Una modificación posterior invoca el sismo")
        d["mods"] = [{"e": cl(m.get("estado_modificacion")),
                      "f": (m.get("fecha_de_aprobacion") or "")[:10],
                      "d": int(num(m.get("dias_extendidos"))),
                      "vr": int(num(m.get("valor_modificacion"))),
                      "p": cl(m.get("proposito_modificacion"))[:900]} for m in ms]
        out.append(d)
    return out

def contexto():
    """Ritmo de contratación alrededor del evento, para dimensionar la respuesta."""
    q = (f"SELECT date_trunc_ymd(`fecha_de_firma`) AS dia, count(*) AS n, sum(`valor_del_contrato`) AS val "
         f"WHERE `nit_entidad` IN ({NITS_SQL}) AND `fecha_de_firma` >= '2026-07-20T00:00:00'::floating_timestamp "
         f"GROUP BY dia ORDER BY dia")
    return [{"dia": x["dia"][:10], "n": int(num(x["n"])), "val": int(num(x.get("val")))} for x in v3(q)]

def main():
    print("buscando contratos que aluden al evento…")
    contratos = buscar_contratos()
    print(f"  {len(contratos)} contratos")
    print("buscando modificaciones…")
    afectados = buscar_modificaciones()
    print(f"  {len(afectados)} contratos afectados")
    print("midiendo el ritmo de contratación…")
    dias = contexto()
    maxfirma = max((d["dia"] for d in dias), default="")

    ids_c = {c["id"] for c in contratos}
    afectados = [a for a in afectados if a["id"] not in ids_c]
    resp = [c for c in contratos if c["motivo"] in ("respuesta", "mecanismo")]

    salida = {
        "generado": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "evento": EVENTO,
        "cobertura_hasta": maxfirma,
        "resumen": {
            "respuesta": len(resp),
            "valor_respuesta": sum(c["v"] for c in resp),
            "afectados": len(afectados),
            "valor_afectados": sum(a["v"] for a in afectados),
        },
        "contratos": sorted(contratos, key=lambda x: -x["v"]),
        "afectados": sorted(afectados, key=lambda x: -x["v"]),
        "dias": dias,
    }
    p = os.path.join(RAIZ, "datos", "sismo.json")
    json.dump(salida, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("listo:", salida["resumen"], "| cobertura hasta", maxfirma)

if __name__ == "__main__":
    main()
