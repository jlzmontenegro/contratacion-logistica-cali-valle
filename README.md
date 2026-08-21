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

## Regeneración automática

Una GitHub Action (`.github/workflows/actualizar.yml`) corre los lunes a las 5:00 a. m. de Colombia
y ejecuta `scripts/actualizar.py`, que reconsulta la API, vuelve a clasificar, reaplica los
veredictos de `datos/veredictos.json` y reescribe el tablero, los CSV y los indicadores de la
portada. Sólo hace commit si algo cambió. También se puede lanzar a mano desde la pestaña Actions.

El script usa únicamente la biblioteca estándar de Python, así que no hay dependencias que instalar.

### Archivos que sostienen la revisión manual

- `datos/veredictos.json` — un registro por `id_contrato` con el veredicto, el motivo, y la adición
  verificada en el expediente cuando la hay. **Este es el archivo a editar si quieres corregir una
  clasificación**; sobrevive a todas las actualizaciones.
- `datos/dependencias.json` — nombres cortos de las 44 dependencias.
- `plantillas/tablero.tpl.html` — el tablero sin datos; el script le inyecta la instantánea.

## Contenido

- `index.html` — portada
- `tablero/` — tablero interactivo, con actualización en vivo
- `informe/` — informe metodológico y hallazgos
- `datos/` — los dos CSV, los veredictos y el mapa de dependencias
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
