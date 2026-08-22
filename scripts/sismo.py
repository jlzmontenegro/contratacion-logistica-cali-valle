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

# Consultas que no se pudieron completar. Si queda alguna, la busqueda esta incompleta
# y el resultado no se puede publicar: un fallo de red se veria igual que "no hay nada".
FALLOS = []


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

def organismos():
    """Nombre completo de cada organismo; el mismo mapa que usa el tablero."""
    p = os.path.join(RAIZ, "datos", "organismos.json")
    try:
        m = json.load(open(p, encoding="utf-8"))
    except Exception as e:                # noqa: BLE001
        print(f"  aviso: no se pudo leer organismos.json ({e}); se usaran los nombres crudos")
        return {}
    m.pop("_nota", None)
    return m


ORG = {}


def notas_verificadas():
    """Lectura humana de los documentos firmados, cuando el texto de SECOP no basta."""
    p = os.path.join(RAIZ, "datos", "sismo_notas.json")
    if not os.path.exists(p):
        return {}
    try:
        n = json.load(open(p, encoding="utf-8"))
    except Exception as e:                # noqa: BLE001
        print(f"  aviso: no se pudo leer sismo_notas.json ({e})")
        return {}
    n.pop("_nota", None)
    return n


def aplicar_notas(datos, notas=None):
    """Sustituye el resumen automatico de una modificacion por la lectura del documento.

    Idempotente: la llaman sismo.py al escribir el JSON y construir_sismo.py al armar la
    pagina, para que la nota valga aunque sismo.json venga de una corrida anterior.
    """
    notas = notas_verificadas() if notas is None else notas
    if not notas:
        return datos
    puestas = 0
    for c in list(datos.get("contratos", [])) + list(datos.get("afectados", [])):
        por_fecha = notas.get(c.get("id"))
        if not por_fecha:
            continue
        for m in c.get("mods", []):
            n = por_fecha.get(m.get("f"))
            if not n:
                continue
            for campo in ("titulo", "puntos", "implica", "fuente", "discrepancia"):
                if n.get(campo):
                    m[campo] = n[campo]
            m["verificada"] = True
            puestas += 1
    if puestas:
        print(f"  {puestas} modificacion(es) con lectura del documento firmado")
    return datos


def ficha(r, motivo, evidencia):
    entf = cl(r.get("nombre_entidad"))
    return {"id": r["id_contrato"], "ref": cl(r.get("referencia_del_contrato")),
            "ciu": "Cali" if r.get("nit_entidad") in CALI else "Valle",
            "ent": entf, "entl": ORG.get(entf, entf), "prov": cl(r.get("proveedor_adjudicado")),
            "td": cl(r.get("tipodocproveedor")), "v": int(num(r.get("valor_del_contrato"))),
            "ff": (r.get("fecha_de_firma") or "")[:10],
            "fi": (r.get("fecha_de_inicio_del_contrato") or "")[:10],
            "fn": (r.get("fecha_de_fin_del_contrato") or "")[:10],
            "mod": cl(r.get("modalidad_de_contratacion")), "just": cl(r.get("justificacion_modalidad_de")),
            "tc": cl(r.get("tipo_de_contrato")), "un": cl(r.get("codigo_de_categoria_principal")),
            "obj": cl(r.get("objeto_del_contrato")), "url": url_de(r),
            "motivo": motivo, "evidencia": evidencia}

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
         "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

def dia_es(iso):
    """2026-08-16 -> 16 de agosto de 2026"""
    if not iso or len(iso) < 10:
        return ""
    a, m, d = iso[:4], iso[5:7], iso[8:10]
    try:
        return f"{int(d)} de {MESES[int(m) - 1]} de {a}"
    except (ValueError, IndexError):
        return iso

def pesos(n):
    return "$" + f"{int(n):,}".replace(",", ".")

def finalidad(texto):
    """Extrae el proposito declarado: lo que sigue a 'con el fin de', 'para', etc."""
    m = re.search(r"(?:con el fin de|a fin de|con el prop[oó]sito de|con el objeto de)\s+(.{15,300}?)(?:\.|$)",
                  texto, re.I)
    if m:
        t = cl(m.group(1))
        return t[0].lower() + t[1:] if t else ""
    return ""

def resumir_mod(m, valor_contrato):
    """Devuelve {tipo, titulo, puntos[]} describiendo en qué consistió la modificación."""
    t = cl(m.get("proposito_modificacion"))
    b = t.lower()
    dias = int(num(m.get("dias_extendidos")))
    vmod = int(num(m.get("valor_modificacion")))
    fin = (m.get("fecha_fin_contrato") or "")[:10]
    delta = vmod - int(valor_contrato or 0)

    suspende = bool(re.search(r"suspend|suspensi[oó]n", b))
    prorroga = bool(re.search(r"prorrog|ampl[ií]a\w* el plazo|plazo de ejecuci[oó]n hasta", b))
    alcance = bool(re.search(r"alcance del objeto|cl[aá]usula segunda|modifica.{0,25}objeto", b))
    adiciona = bool(re.search(r"adicion|mayor valor", b))
    cede = bool(re.search(r"cesi[oó]n del contrato|cede el contrato", b))

    if suspende:
        tipo, titulo = "Suspensión", "Se suspende la ejecución"
    elif prorroga and adiciona:
        tipo, titulo = "Adición y prórroga", "Se amplía el plazo y el valor"
    elif prorroga:
        tipo, titulo = "Prórroga", "Se amplía el plazo"
    elif adiciona:
        tipo, titulo = "Adición", "Se amplía el valor"
    elif alcance:
        tipo, titulo = "Cambio de alcance", "Se modifica el alcance del objeto"
    elif cede:
        tipo, titulo = "Cesión", "Cambia el contratista"
    else:
        tipo, titulo = "Otra", "Se modifica el contrato"

    puntos = []
    # plazo
    hasta = re.search(r"hasta el (\d{1,2}) de (\w+) de (\d{4})", t, re.I)
    if dias > 0:
        verbo = "Se suspende por" if suspende else "Se añaden"
        cola = " de plazo" if not suspende else ""
        puntos.append(f"{verbo} {dias} días{cola}")
    if hasta:
        puntos.append(("La ejecución se reanuda el " if suspende else "El plazo va hasta el ")
                      + f"{int(hasta.group(1))} de {hasta.group(2).lower()} de {hasta.group(3)}")
    elif fin and dias > 0:
        puntos.append(("Nueva fecha de fin: " if not suspende else "Queda suspendido desde el ") + dia_es(fin))
    elif fin and dias == 0:
        puntos.append("El plazo no cambia: sigue hasta el " + dia_es(fin))
    # valor
    if delta > 0:
        pct = f" ({delta / (vmod - delta) * 100:.1f} % sobre el valor previo)" if vmod - delta > 0 else ""
        puntos.append(f"Se adicionan {pesos(delta)}{pct}")
    elif vmod:
        puntos.append(f"El valor no cambia: sigue en {pesos(vmod)}")
    # finalidad declarada
    f = finalidad(t)
    if f:
        puntos.append("Finalidad declarada: " + f)
    # alcance sin detalle
    if tipo == "Cambio de alcance" and not f:
        puntos.append("El texto publicado no dice qué cambió del alcance; el detalle está en el documento del otrosí")
    if dias == 0 and delta == 0 and tipo != "Cambio de alcance":
        puntos.append("No cambian ni el plazo ni el valor registrados")
    return {"tipo": tipo, "titulo": titulo, "puntos": puntos}


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
           "valor_modificacion,dias_extendidos,proposito_modificacion,fecha_inicio_contrato,fecha_fin_contrato")
    # sobre el dataset nacional sólo se buscan las frases que responden rápido;
    # las tres son suficientes: los textos que invocan el sismo contienen alguna.
    mejor = {}
    for f in ["SISMO", "TERREMOTO", "EMERGENCIA OCURRIDA", "10 DE AGOSTO DE 2026"]:
        w = f"upper(proposito_modificacion) like '%{f}%' AND fecha_de_aprobacion >= '{DESDE}'"
        try:
            for x in soda("u8cx-r425", w, sel, 5000, intentos=2, espera=8, tiempo=200):
                k = x.get("identificador_modificacion")
                if not k:
                    continue
                if k not in mejor or num(x.get("numero_version")) > num(mejor[k].get("numero_version")):
                    mejor[k] = x
        except Exception as e:            # noqa: BLE001
            print(f"    '{f}' falló: {e}", file=sys.stderr)
            FALLOS.append(f"frase '{f}': {e}")
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
            FALLOS.append(f"lote de contratos {i//70 + 1}: {e}")
        time.sleep(0.4)
    out = []
    for cid, r in nuestros.items():
        ms = [m for m in mejor.values() if m["id_contrato"] == cid]
        ms.sort(key=lambda x: (x.get("fecha_de_aprobacion") or ""))
        d = ficha(r, "afectado", "Una modificación posterior invoca el sismo")
        d["mods"] = []
        for m in ms:
            res = resumir_mod(m, r.get("valor_del_contrato"))
            d["mods"].append({"e": cl(m.get("estado_modificacion")),
                              "f": (m.get("fecha_de_aprobacion") or "")[:10],
                              "d": int(num(m.get("dias_extendidos"))),
                              "vr": int(num(m.get("valor_modificacion"))),
                              "fin": (m.get("fecha_fin_contrato") or "")[:10],
                              "tipo": res["tipo"], "titulo": res["titulo"], "puntos": res["puntos"],
                              "p": cl(m.get("proposito_modificacion"))})
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
    global ORG
    ORG = organismos()
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
    if FALLOS:
        print("\nNO SE ESCRIBE datos/sismo.json: la búsqueda quedó incompleta.", file=sys.stderr)
        for f in FALLOS:
            print(f"  · {f}", file=sys.stderr)
        print("Publicar este resultado diría que el sismo no alteró contratos, cuando lo que pasó\n"
              "es que la consulta no respondió. Se conserva el archivo anterior; reintenta el\n"
              "workflow cuando la API de datos.gov.co esté respondiendo.", file=sys.stderr)
        return 1

    aplicar_notas(salida)
    p = os.path.join(RAIZ, "datos", "sismo.json")
    json.dump(salida, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("listo:", salida["resumen"], "| cobertura hasta", maxfirma)
    return 0

if __name__ == "__main__":
    sys.exit(main() or 0)
