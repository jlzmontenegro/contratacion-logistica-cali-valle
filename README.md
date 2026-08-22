# Contratación de logística y catering — Cali y Valle del Cauca, 2026

Barrido de los 34.888 contratos firmados por el Distrito de Santiago de Cali y la Gobernación
del Valle del Cauca entre el 1 de enero y el 20 de agosto de 2026, para identificar los de
logística, catering y servicios conexos, y seguirles el rastro de modificaciones y adiciones.

**Sitio:** https://jlzmontenegro.github.io/contratacion-logistica-cali-valle/

## Resultados

| | |
|---|---|
| Contratos identificados | 191 |
| Valor contratado | $302.696 millones |
| Con modificación publicada | 66 |
| Con adición en valor | 33 |
| Suma de las adiciones | $9.431 millones |

## Actualización

El tablero consulta la API de datos.gov.co cada vez que se abre: refresca valores, fechas,
modificaciones y trae contratos nuevos que el filtro automático identifique. Primero pinta la
instantánea revisada (carga instantánea) y luego la reemplaza con los datos vivos.

Lo que no se recalcula solo es el trabajo humano: la revisión caso por caso de los 66 dudosos y
los montos de adición leídos en los expedientes. Esos veredictos van asociados al `id_contrato`,
así que sobreviven a la actualización. Los contratos que aparezcan después del corte se marcan
**«sin revisar»** y su adición es solo un piso calculado por diferencia entre registros.
Si la API falla, se muestra la instantánea y el indicador de estado lo advierte.

## Modificaciones desde el 10 de agosto

El tablero abre con un panel que lista las modificaciones y adiciones **aprobadas del 10 de
agosto de 2026 en adelante**, sobre los contratos incluidos en el análisis. Es la lista de lo
que se movió después del sismo sin ser respuesta al sismo: los contratos que ya rastrea
`sismo/` se excluyen, para no contar dos veces lo mismo.

El panel no obedece a los filtros de la tabla — es un corte fijo por fecha. Cada entrada trae
el organismo, el propósito publicado, el contratista y, si el contrato tiene adición verificada
en el expediente, su monto y su porcentaje sobre el valor inicial. Dos advertencias sobre eso:

- La adición mostrada es la **del contrato**, no la de esa modificación en particular. SECOP
  publica en `valor_modificacion` el valor total del contrato después del cambio, no el delta,
  así que no se puede atribuir un monto a cada otrosí por separado.
- Solo se listan las modificaciones en estado **Publicado**. Las que están en edición, aceptadas,
  canceladas o rechazadas se cuentan en la nota del panel pero no se detallan.

La lista de contratos del sismo se inyecta al generar el tablero desde `datos/sismo.json` y se
refresca al abrir la página, porque `scripts/sismo.py` corre después de `scripts/actualizar.py`.

## Rastreador del sismo del 10 de agosto de 2026

`scripts/sismo.py` busca sobre **toda** la contratación de las cinco entidades —sin filtro de
categoría— los contratos que responden al sismo y los que quedaron alterados por él. Se publica
en `sismo/`.

El detalle que hace falta conocer: **la palabra «sismo» no aparece ni una vez en los más de
35.000 objetos contractuales de 2026.** La contratación nombra el evento como «los hechos
acaecidos el 10 de agosto de 2026» o «la emergencia ocurrida». Sólo en el texto de las
*modificaciones* se lee directamente, y ahí consta que fue un sismo de magnitud 7,4. Por eso la
búsqueda combina varias frases con el mecanismo jurídico: urgencia manifiesta y calamidad pública.

Un contrato entra como **respuesta** si su objeto, la descripción del proceso o la justificación de
la modalidad aluden al evento, o si se suscribió por urgencia manifiesta o calamidad después del
10 de agosto. Entra como **afectado** si una modificación posterior invoca el sismo.

### Sobre la frescura de los datos

Ninguna consulta de este repositorio tiene tope superior de fecha: siempre piden **todo lo que
SECOP II tenga publicado en ese momento**. Lo que limita la cobertura es el rezago de publicación
de SECOP, no el código.

Para comprobarlo basta comparar: la fecha de firma más reciente en Cali y el Valle es la misma que
la más reciente en *toda* la contratación del país. Ese rezago ronda 1 o 2 días.

Por eso el rastreador distingue dos fechas que es fácil confundir:

| | |
|---|---|
| **Consultado** | cuándo se pidieron los datos — hoy, al abrir la página |
| **Cobertura** | fecha del contrato más reciente que SECOP ha publicado |

La página muestra ambas y calcula el rezago en días. Que la cobertura no llegue a hoy no significa
que la página esté desactualizada; significa que SECOP todavía no ha publicado lo de hoy.

Con todo, lo que se ve es un piso, no el total: la respuesta a una emergencia tarda semanas en
aparecer completa en SECOP.

## Regeneración automática

Una GitHub Action (`.github/workflows/actualizar.yml`) corre **cada 12 horas** (5:00 a. m. y 5:00 p. m. de Colombia)
y ejecuta `scripts/actualizar.py` y `scripts/sismo.py`, que reconsultan la API, vuelve a clasificar, reaplica los
veredictos de `datos/veredictos.json` y reescribe el tablero, los CSV y los indicadores de la
portada. Sólo hace commit si algo cambió. También se puede lanzar a mano desde la pestaña Actions.

> GitHub desactiva los workflows programados cuando un repositorio pasa 60 días sin actividad.
> Como este hace commit cada vez que los datos cambian, se mantiene activo solo; si algún día
> deja de correr, basta reactivarlo desde la pestaña Actions.

El script usa únicamente la biblioteca estándar de Python, así que no hay dependencias que instalar.

### Archivos que sostienen la revisión manual

- `datos/veredictos.json` — un registro por `id_contrato` con el veredicto, el motivo, y la adición
  verificada en el expediente cuando la hay. **Este es el archivo a editar si quieres corregir una
  clasificación**; sobrevive a todas las actualizaciones.
- `datos/dependencias.json` — nombres cortos de los 44 organismos, para los filtros y los CSV.
- `datos/organismos.json` — nombre completo de cada organismo: el mismo `nombre_entidad` de SECOP II
  con mayúsculas, tildes y territorio corregidos. Es lo que titula cada grupo del tablero, para que
  dos homónimos (Educación de Cali y Educación del Valle) no se confundan. Si SECOP publica una
  entidad que no esté en el mapa, el tablero la muestra con el nombre crudo y el script lo avisa.
- `plantillas/tablero.tpl.html` — el tablero sin datos; el script le inyecta la instantánea.

## Contenido

- `index.html` — portada
- `tablero/` — tablero interactivo, con actualización en vivo
- `sismo/` — rastreador del sismo del 10 de agosto
- `informe/` — informe metodológico y hallazgos
- `datos/` — los dos CSV, los veredictos y los mapas de nombres de organismos
- `scripts/` — el regenerador
- `plantillas/` — la plantilla del tablero

## Método, en corto

La palabra «catering» aparece una sola vez en los 34.888 contratos, así que la búsqueda por
palabras obvias no sirve. El léxico se construyó leyendo los 767 objetos contractuales distintos
de proveedores empresariales. El código UNSPSC se usó como segundo criterio, pero resultó poco
confiable: explica 17 de los 22 falsos positivos que se descartaron en la revisión manual.

Las adiciones no se pueden leer directamente del dataset porque `valor_del_contrato` ya viene con
ellas incorporadas y no se publica el valor inicial. Se cuantificaron una por una: 5 con el
documento del expediente (RPC de adición, CDP, ficha técnica del otrosí), 5 con el monto declarado
en el texto de la modificación, 19 por aritmética de cuotas del CPS, y 4 por diferencia entre
valores registrados.

## Fuentes

Todas de [datos.gov.co](https://www.datos.gov.co/), unidas por `id_contrato`:

- `jbjy-vk9h` — SECOP II, contratos electrónicos
- `u8cx-r425` — SECOP II, modificaciones a contratos
- `cb9c-h8sn` — SECOP II, adiciones
- `dmgg-8hin` — SECOP II, archivos de descarga (URL de los documentos del expediente)

Datos con corte al 20 de agosto de 2026.
