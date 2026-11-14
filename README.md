# ALTERGEA · Análogos terrestres para la Luna y Marte

Equipo ALTERGEA · NASA Space Apps 2026, Piura (Perú).
App: [app.py](app.py) (Streamlit). Medición propia: [tools/sentinel_migration.py](tools/sentinel_migration.py).

## El reto

Buscar en la Tierra lugares y procesos que sirvan como análogos para preparar bases lunares permanentes y sitios de
exploración en Marte, usando datos abiertos de la NASA, explicando qué hace sólida la analogía, dónde falla y cómo ayuda.

## Nuestra respuesta

1. **Un sistema de puntuación de similitud** que compara 14 sitios del mundo (6 en Perú) con las condiciones de
   referencia de Marte y la Luna, a partir de datos de la NASA: clima de NASA POWER (precipitación, rango térmico
   diario, albedo, viento a 10 m) y topografía SRTM/ASTER. Pesos y umbrales son explícitos y ajustables en la app.
2. **Un análogo propuesto y caracterizado en detalle:** el campo dunar de **Médano Blanco (Sechura, Piura)** frente a
   las **dunas Bagnold del cráter Gale**, estudiadas in situ por el rover Curiosity (2015–2017). La app muestra ambos
   lados en mapas gemelos: Sentinel-2, Esri y MODIS (NASA GIBS) en la Tierra; mosaicos CTX y HiRISE y el DEM HiRISE de
   1 m de NASA Mars Trek en Marte.
3. **Una medición propia de la migración de la duna** con imágenes Sentinel-2 (2017–2026), comparada con la cifra del
   MINAM (Google Earth, 2006–2022) y con la migración de Bagnold medida con HiRISE.

## Médano Blanco ↔ Bagnold

| | Médano Blanco (Sechura) | Bagnold / duna Namib (Gale) |
|---|---|---|
| Tipo de duna | Barján activo, ~16,4 ha (MINAM 2022) | Barjanes y dunas lineales activas (Bridges et al. 2018) |
| Migración medida | Cuerpo de la duna 0,3 ± 0,1 m/año (Sentinel-2 2019–2026, ALTERGEA); sotavento 4–6 m/año según MINAM (Google Earth 2006–2022) | ~0,4 m/año terrestre (Silvestro et al. 2013, HiRISE); ondulaciones hasta 1,7 m/año |
| Composición | Arena cuarzosa clara, unidad INGEMMET Q-eo "Depósito eólico" | Arena basáltica oscura con olivino (ChemCam, APXS) |
| Posición | −5,554, −80,757 (UTM 17M 526906 E / 9386090 S) | Namib: −4,680, 137,367 (rover, sol 1192) |
| Topografía | SRTM / Copernicus 30 m | DTM HiRISE 1 m (Gale_DEM_SMG_1m); MOLA 463 m es demasiado grueso |

**Qué hace sólida la analogía.** La misma forma y el mismo proceso: barjanes activos modelados por un viento
persistente, arena suelta que atrapa ruedas, caras de deslizamiento y ondulaciones métricas. En los dos cuerpos la
migración está medida, no supuesta.

**Dónde falla.** La composición (cuarzo frente a basalto y olivino), la atmósfera (1 bar frente a 6 mbar: en Marte la
arena se mueve rara vez y unas diez veces más despacio), la gravedad y la ausencia de vegetación. Gale es un sitio de
ciencia con rover, no de base permanente. Médano Blanco es un sitio turístico protegido: el MINAM lo considera
vulnerable al uso intensivo, así que cualquier campo de entrenamiento debe coordinarse con la comunidad y el municipio.

**Cómo ayuda.** Campo de pruebas de movilidad de rovers y de recuperación en trampas de arena (el modo de fallo de
Spirit en 2009), planificación de rutas entre dunas, métodos de detección de cambios en polvo y bedforms, y calibración
de medidas orbitales contra verdad de terreno, a 50 km de Piura y con acceso e infraestructura documentados.

## Datos usados

| Fuente | Uso |
|---|---|
| NASA POWER | Clima climatológico por sitio: `PRECTOTCORR`, `T2M_RANGE`, `ALLSKY_SRF_ALB`, `WS10M`, `WS10M_MAX` |
| SRTM (NASA/NGA), ASTER GDEM (NASA/METI) | Altitud y pendiente media (ventana de 5×5 puntos a 1 km), vía OpenTopoData |
| NASA Mars Trek (WMTS) | Viking MDIM 2.1, MOLA 463 m, mosaico CTX de Gale, mosaico HiRISE de Curiosity, DEM HiRISE 1 m |
| NASA GIBS / Worldview | MODIS Terra color verdadero como capa base terrestre |
| Copernicus Sentinel-2 L2A (Earth Search, AWS) | Serie 2017–2026 a 10 m para medir la migración de la duna |
| INGEMMET GEOCATMIN | Geología integrada 1:100k y geomorfología (WMS y consulta puntual) |
| MINAM / SINIA (2022) | Diagnóstico y microzonificación de la duna Médano Blanco: tipo, área, migración, restricciones |

## Medición Sentinel-2: método y resultado

**Método.** De las escenas con menos de 4 % de nubes desde 2017 se toman hasta 45 repartidas en el tiempo y se descartan
las que tienen nubes o sombras (máscara SCL) dentro de una ventana de ~2 km. Se lee un recorte de las bandas azul, verde
y roja a 10 m. En la escena de referencia (2019-03-31) se delimita la duna con un umbral de Otsu y apertura morfológica,
y esa silueta (dilatada 30 m) es la plantilla. En cada escena posterior se busca la plantilla por correlación cruzada
normalizada *enmascarada*, es decir, solo cuentan los píxeles de la duna, para que el bosque seco, las pistas y la arena
fija de alrededor no anclen la correlación. El pico se refina a subpíxel y la velocidad es la pendiente del ajuste
lineal del desplazamiento frente al tiempo.

**Resultado (43 escenas, 2019-03-31 a 2026-08-21).** El cuerpo de la duna se desplaza **0,3 ± 0,1 m/año** hacia el
oeste-suroeste, con una dispersión de 1,9 m alrededor del ajuste: a la resolución de Sentinel-2 el barján es
esencialmente estacionario, muy por debajo de los 4–6 m/año que el diagnóstico del MINAM atribuye al sotavento a partir
de Google Earth (2006–2022). Las dos cifras no miden lo mismo: la del MINAM describe el borde de la cara de
deslizamiento y los brazos, donde se concentra el sandboarding y el paso de tubulares, y además la georreferenciación
de las imágenes históricas de Google Earth puede desplazarse varios metros entre fechas. Nuestra medida sigue la forma
completa de la duna, que entre 2019 y 2026 apenas cambia de sitio. Esto encaja con la propia observación del MINAM
de que la duna está rodeada de bosque seco que frena el viento y la arena. En términos del análogo, Médano Blanco se
parece más a Bagnold de lo que sugería la cifra de 6 m/año: ambos campos son activos a escala de ondulaciones y caras
de deslizamiento, pero sus cuerpos migran menos de 1 m/año.

Limitaciones: 10 m por píxel limita la detección a desplazamientos de ~2 m acumulados; la silueta por brillo varía con
la humedad del suelo y la estación (por eso el área oscila entre 10 y 21 ha), aunque la correlación enmascarada es
robusta a ello; un análisis con PlanetScope (3 m) o con ortofotos de dron resolvería el movimiento del sotavento.

## Dos versiones de la app

| | Streamlit ([app.py](app.py)) | Web estática ([web/](web/)) |
|---|---|---|
| Para | Trabajo local y Streamlit Community Cloud | Vercel, Netlify, GitHub Pages o cualquier hosting estático |
| Datos de sitios | Descargados en vivo de NASA POWER y OpenTopoData | Precalculados en `web/data/sites.json` con `tools/export_sites.py`; los sitios que añade el usuario sí se consultan en vivo desde el navegador |
| Modelo | Python | JavaScript, mismas fórmulas y pesos |
| Mapas de Marte, GIBS, INGEMMET | Sí | Sí, directo desde el navegador (INGEMMET por JSONP) |
| Fundido Tierra/Marte | Sí, en el servidor | Sí, en `<canvas>` |

### Desplegar la web en Vercel

El repo ya incluye [vercel.json](vercel.json), que publica la carpeta `web/` tal cual, sin build.

1. En [vercel.com/new](https://vercel.com/new) importa el repositorio `TheGuillers/nasa-analogos`.
2. Deja el *Framework Preset* en "Other"; Vercel lee `vercel.json` y usa `web` como directorio de salida. Pulsa **Deploy**.
3. Cada push a `main` redespliega. Si cambian los datos, vuelve a ejecutar `tools/export_sites.py` antes del push.

Para probarla en local:

```bash
.venv/Scripts/python.exe -m http.server 8080 --directory web
```

## Cómo ejecutar la versión Streamlit

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe -m streamlit run app.py
```

Regenerar los datos de la web estática (unos 70 s, consulta NASA POWER y OpenTopoData):

```bash
.venv/Scripts/python.exe tools/export_sites.py
```

La medición Sentinel-2 (opcional, necesita `rasterio` y `scipy`):

```bash
.venv/Scripts/python.exe tools/sentinel_migration.py
```

## Uso de IA

Claude (Anthropic) se usó como asistente de programación para escribir y depurar el código. La idea, la selección
de sitios, el diseño del modelo y la interpretación son del equipo.

## Referencias

- MINAM / SINIA. *Diagnóstico y microzonificación del ámbito de uso turístico de la duna Médano Blanco, Sechura, Piura* (2022).
  https://sinia.minam.gob.pe/documentos/diagnostico-microzonificacion-ambito-uso-turistico-duna-medano
- Bridges, N. T. et al. (2018). The MSL Bagnold Dunes Campaign, Phase I. *JGR Planets*. doi:10.1002/2017JE005401
- Silvestro, S. et al. (2013). Pervasive aeolian activity along rover Curiosity's traverse in Gale Crater. *Geology* 41, 483–486.
- Baker, M. M. et al. (2018). The Bagnold Dunes in southern summer. *GRL*. doi:10.1029/2018GL079040
- NASA POWER https://power.larc.nasa.gov · NASA Mars Trek https://trek.nasa.gov/mars · NASA GIBS https://gibs.earthdata.nasa.gov
- Earth Search STAC (Element 84) https://earth-search.aws.element84.com/v1 · INGEMMET https://geocatmin.ingemmet.gob.pe
