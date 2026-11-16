# ALTERGEA · Earth analogues for the Moon and Mars

*[Leer en español](#español)*

ALTERGEA team · NASA Space Apps 2026, Piura (Peru).
App: [app.py](app.py) (Streamlit). Our own measurement: [tools/sentinel_migration.py](tools/sentinel_migration.py).

## The challenge

Find places and processes on Earth that can serve as analogues to prepare permanent lunar bases and Mars exploration
sites, using open NASA data, explaining what makes the analogy strong, where it breaks down and how it helps.

## Our answer

1. **A similarity scoring system** that compares 14 sites around the world (6 in Peru) against reference conditions for
   Mars and the Moon, using NASA data: NASA POWER climate (precipitation, daily temperature range, albedo, 10 m wind)
   and SRTM/ASTER topography. Weights and thresholds are explicit and adjustable in the app.
2. **One proposed analogue, characterized in detail:** the **Médano Blanco dune field (Sechura, Piura)** against the
   **Bagnold Dunes of Gale crater**, studied in situ by the Curiosity rover (2015–2017). The app shows both sides in
   twin maps: Sentinel-2, Esri and MODIS (NASA GIBS) on Earth; CTX and HiRISE mosaics and the 1 m HiRISE DEM from
   NASA Mars Trek on Mars.
3. **Our own measurement of dune migration** from Sentinel-2 imagery (2018–2026) taken from Microsoft Planetary
   Computer, compared with the MINAM figure (Google Earth, 2006–2022) and with Bagnold migration measured with HiRISE.

## Médano Blanco ↔ Bagnold

| | Médano Blanco (Sechura) | Bagnold / Namib dune (Gale) |
|---|---|---|
| Dune type | Active barchan, ~16.4 ha (MINAM 2022) | Active barchans and linear dunes (Bridges et al. 2018) |
| Measured migration | Dune body < 1 m/yr, 0.9 ± 0.1 in the current run (Sentinel-2 2018–2026 via Planetary Computer, ALTERGEA); lee side 4–6 m/yr according to MINAM (Google Earth 2006–2022) | ~0.4 m/Earth-year (Silvestro et al. 2013, HiRISE); ripples up to 1.7 m/yr |
| Composition | Light quartz sand, INGEMMET unit Q-eo "Aeolian deposit" | Dark basaltic sand with olivine (ChemCam, APXS) |
| Position | −5.554, −80.757 (UTM 17M 526906 E / 9386090 S) | Namib: −4.680, 137.367 (rover, sol 1192) |
| Topography | Copernicus DEM GLO-30 via Planetary Computer (slope and roughness at 30 m); SRTM 30 m | HiRISE 1 m DTM (Gale_DEM_SMG_1m); MOLA at 463 m is too coarse |

**What makes the analogy strong.** The same shape and the same process: active barchans shaped by a persistent wind,
loose sand that traps wheels, slip faces and metre-scale ripples. On both bodies the migration is measured, not
assumed.

**Where it breaks down.** Composition (quartz versus basalt and olivine), atmosphere (1 bar versus 6 mbar: on Mars
sand moves rarely and roughly ten times more slowly), gravity and the absence of vegetation. Gale is a rover science
site, not a permanent base site. Médano Blanco is a protected tourist site: MINAM considers it vulnerable to intensive
use, so any training field must be coordinated with the community and the municipality.

**How it helps.** A test bed for rover mobility and recovery from sand traps (the failure mode that ended Spirit's
mission in 2009), route planning between dunes, change-detection methods for dust and bedforms, and calibration of
orbital measurements against ground truth, 50 km from Piura with documented access and infrastructure.

## Data used

| Source | Use |
|---|---|
| NASA POWER | Climatological data per site: `PRECTOTCORR`, `T2M_RANGE`, `ALLSKY_SRF_ALB`, `WS10M`, `WS10M_MAX` |
| Copernicus DEM GLO-30 (ESA) via **Microsoft Planetary Computer** | Elevation, mean slope at 30 m and roughness (detrended surface deviation) over a ~3 km window. This is the slope the model uses, at a resolution the Mars side (HiRISE DTM resampled to 30 m) can match |
| SRTM (NASA/NGA), ASTER GDEM (NASA/METI) | Elevation and regional slope (5×5 point window at 1 km), via OpenTopoData; fallback and source for user-added sites in the static web version |
| Copernicus Sentinel-2 L2A via **Planetary Computer** (Earth Search on AWS as fallback) | 2017–2026 series at 10 m to measure dune migration |
| NASA Mars Trek (WMTS) | Viking MDIM 2.1, MOLA 463 m, Gale CTX mosaic, Curiosity HiRISE mosaic, 1 m HiRISE DEM |
| NASA GIBS / Worldview | MODIS Terra, VIIRS NOAA-21 and VIIRS SNPP true-colour layers on the Earth maps, with a date control (web version) |
| NASA Earthdata (CMR API, Earthdata Search) | Live query of the collections and granules (MODIS MOD09GA, Harmonized Landsat HLSL30 and Sentinel-2 HLSS30) that cover each site, with links to Earthdata Search and Worldview (web version) |
| NASA PDS Geosciences Node, Mars Exploration Program | Orbital Data Explorer queried live for HiRISE DTMs and images around the MSL, MER (Spirit, Opportunity) and Mars 2020 sites, shown in the Mars twin tab (web version) |
| INGEMMET GEOCATMIN | Integrated 1:100k geology and geomorphology (WMS and point query) |
| MINAM / SINIA (2022) | Diagnosis and microzoning of the Médano Blanco dune: type, area, migration, restrictions |

## Sentinel-2 measurement: method and result

**Method.** From scenes with less than 4 % cloud since 2017, up to 45 spread over time are selected, and those with
clouds or shadows (SCL mask) inside a ~2 km window are discarded. A crop of the blue, green and red bands at 10 m is
read. In the reference scene (2019-03-31) the dune is delineated with an Otsu threshold and morphological opening, and
that silhouette (dilated by 30 m) is the template. In each later scene the template is located by *masked* normalized
cross-correlation, meaning only the dune's pixels count, so the surrounding dry forest, tracks and fixed sand do not
anchor the correlation. The peak is refined to sub-pixel precision and the speed is the slope of the linear fit of
displacement against time.

**Result (42 Planetary Computer scenes, 2018-01-30 to 2026-08-21).** The dune body moves
**0.9 ± 0.1 m/yr** toward the west-northwest, with a scatter of 1.8 m around the fit. An earlier run with the Earth
Search catalogue (43 scenes, reference 2019-03-31) gave 0.3 ± 0.1 m/yr: the figure depends on the reference scene and on
which scenes pass the cloud filter, so the honest value is **less than 1 m/yr**. At Sentinel-2 resolution the barchan is
essentially stationary, far below the 4–6 m/yr that the MINAM diagnosis attributes to the lee side from Google Earth
(2006–2022). The two figures do not measure the same thing: MINAM's describes the edge of the slip face and the arms,
where sandboarding and tubular traffic are concentrated, and the georeferencing of historical Google Earth images can
also shift by several metres between dates. Our measurement follows the full shape of the dune, which barely changes
position between 2019 and 2026. This agrees with MINAM's own observation that the dune is surrounded by dry forest that
slows the wind and the sand. In terms of the analogue, Médano Blanco resembles Bagnold more than the 6 m/yr figure
suggested: both fields are active at the scale of ripples and slip faces, but their bodies migrate less than 1 m/yr.

Limitations: 10 m per pixel limits detection to cumulative displacements of ~2 m; the brightness-based silhouette
varies with soil moisture and season (which is why the area fluctuates between 10 and 21 ha), although masked
correlation is robust to this; an analysis with PlanetScope (3 m) or drone orthophotos would resolve the motion of the
lee side.

## Use of AI

Claude (Anthropic) was used as a programming assistant to write and debug code. The idea, the choice of sites, the
model design and the interpretation are the team's.

## References

- MINAM / SINIA. *Diagnóstico y microzonificación del ámbito de uso turístico de la duna Médano Blanco, Sechura, Piura* (2022).
  https://sinia.minam.gob.pe/documentos/diagnostico-microzonificacion-ambito-uso-turistico-duna-medano
- Bridges, N. T. et al. (2018). The MSL Bagnold Dunes Campaign, Phase I. *JGR Planets*. doi:10.1002/2017JE005401
- Silvestro, S. et al. (2013). Pervasive aeolian activity along rover Curiosity's traverse in Gale Crater. *Geology* 41, 483–486.
- Baker, M. M. et al. (2018). The Bagnold Dunes in southern summer. *GRL*. doi:10.1029/2018GL079040
- NASA POWER https://power.larc.nasa.gov · NASA Mars Trek https://trek.nasa.gov/mars · NASA GIBS https://gibs.earthdata.nasa.gov
- NASA Earthdata Search https://search.earthdata.nasa.gov/search?q=sechura&lat=-5.940280099950111&long=-80.54643451544943&overlays=bordersRoads%2Ccoastlines%2CplaceLabels&zoom=10.81509069402037
- NASA Worldview https://worldview.earthdata.nasa.gov/index.html?v=-504.22662231419474,-190.8513647590744,359.77337768580526,219.7736352409256&t=2026-09-07-T01%3A58%3A13Z
- NASA PDS Geosciences Node, Mars Exploration Program https://pds-geosciences.wustl.edu/missions/mep/index.htm
- Microsoft Planetary Computer (Copernicus DEM GLO-30, Sentinel-2 L2A) https://planetarycomputer.microsoft.com
- Earth Search STAC (Element 84) https://earth-search.aws.element84.com/v1 · INGEMMET https://geocatmin.ingemmet.gob.pe

---

# Español

*[Read in English](#altergea--earth-analogues-for-the-moon-and-mars)*

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
3. **Una medición propia de la migración de la duna** con imágenes Sentinel-2 (2018–2026) tomadas de Microsoft
   Planetary Computer, comparada con la cifra del MINAM (Google Earth, 2006–2022) y con la migración de Bagnold medida
   con HiRISE.

## Médano Blanco ↔ Bagnold

| | Médano Blanco (Sechura) | Bagnold / duna Namib (Gale) |
|---|---|---|
| Tipo de duna | Barján activo, ~16,4 ha (MINAM 2022) | Barjanes y dunas lineales activas (Bridges et al. 2018) |
| Migración medida | Cuerpo de la duna < 1 m/año, 0,9 ± 0,1 en la corrida actual (Sentinel-2 2018–2026 vía Planetary Computer, ALTERGEA); sotavento 4–6 m/año según MINAM (Google Earth 2006–2022) | ~0,4 m/año terrestre (Silvestro et al. 2013, HiRISE); ondulaciones hasta 1,7 m/año |
| Composición | Arena cuarzosa clara, unidad INGEMMET Q-eo "Depósito eólico" | Arena basáltica oscura con olivino (ChemCam, APXS) |
| Posición | −5,554, −80,757 (UTM 17M 526906 E / 9386090 S) | Namib: −4,680, 137,367 (rover, sol 1192) |
| Topografía | Copernicus DEM GLO-30 vía Planetary Computer (pendiente y rugosidad a 30 m); SRTM 30 m | DTM HiRISE 1 m (Gale_DEM_SMG_1m); MOLA 463 m es demasiado grueso |

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
| Copernicus DEM GLO-30 (ESA) vía **Microsoft Planetary Computer** | Altitud, pendiente media a 30 m y rugosidad (desviación de la superficie sin tendencia) en una ventana de ~3 km. Es la pendiente que usa el modelo, a la resolución que el lado marciano (DTM HiRISE remuestreado a 30 m) puede igualar |
| SRTM (NASA/NGA), ASTER GDEM (NASA/METI) | Altitud y pendiente regional (ventana de 5×5 puntos a 1 km), vía OpenTopoData; respaldo y fuente para sitios añadidos por el usuario en la web estática |
| Copernicus Sentinel-2 L2A vía **Planetary Computer** (Earth Search en AWS como respaldo) | Serie 2017–2026 a 10 m para medir la migración de la duna |
| NASA Mars Trek (WMTS) | Viking MDIM 2.1, MOLA 463 m, mosaico CTX de Gale, mosaico HiRISE de Curiosity, DEM HiRISE 1 m |
| NASA GIBS / Worldview | Capas en color verdadero MODIS Terra, VIIRS NOAA-21 y VIIRS SNPP en los mapas terrestres, con selector de fecha (versión web) |
| NASA Earthdata (API CMR, Earthdata Search) | Consulta en vivo de las colecciones y granules (MODIS MOD09GA, Harmonized Landsat HLSL30 y Sentinel-2 HLSS30) que cubren cada sitio, con enlaces a Earthdata Search y Worldview (versión web) |
| NASA PDS Geosciences Node, Mars Exploration Program | Orbital Data Explorer consultado en vivo para DTM e imágenes HiRISE alrededor de los sitios de MSL, MER (Spirit, Opportunity) y Mars 2020, en la pestaña del gemelo marciano (versión web) |
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

**Resultado (42 escenas de Planetary Computer, 2018-01-30 a 2026-08-21).** El cuerpo de la duna se desplaza
**0,9 ± 0,1 m/año** hacia el oeste-noroeste, con una dispersión de 1,8 m alrededor del ajuste. Una corrida anterior con
el catálogo Earth Search (43 escenas, referencia 2019-03-31) dio 0,3 ± 0,1 m/año: la cifra depende de la escena de
referencia y de qué escenas pasan el filtro de nubes, así que el valor honesto es **menos de 1 m/año**. A la resolución
de Sentinel-2 el barján es esencialmente estacionario, muy por debajo de los 4–6 m/año que el diagnóstico del MINAM
atribuye al sotavento a partir de Google Earth (2006–2022). Las dos cifras no miden lo mismo: la del MINAM describe el borde de la cara de
deslizamiento y los brazos, donde se concentra el sandboarding y el paso de tubulares, y además la georreferenciación
de las imágenes históricas de Google Earth puede desplazarse varios metros entre fechas. Nuestra medida sigue la forma
completa de la duna, que entre 2019 y 2026 apenas cambia de sitio. Esto encaja con la propia observación del MINAM
de que la duna está rodeada de bosque seco que frena el viento y la arena. En términos del análogo, Médano Blanco se
parece más a Bagnold de lo que sugería la cifra de 6 m/año: ambos campos son activos a escala de ondulaciones y caras
de deslizamiento, pero sus cuerpos migran menos de 1 m/año.

Limitaciones: 10 m por píxel limita la detección a desplazamientos de ~2 m acumulados; la silueta por brillo varía con
la humedad del suelo y la estación (por eso el área oscila entre 10 y 21 ha), aunque la correlación enmascarada es
robusta a ello; un análisis con PlanetScope (3 m) o con ortofotos de dron resolvería el movimiento del sotavento.

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
- NASA Earthdata Search https://search.earthdata.nasa.gov/search?q=sechura&lat=-5.940280099950111&long=-80.54643451544943&overlays=bordersRoads%2Ccoastlines%2CplaceLabels&zoom=10.81509069402037
- NASA Worldview https://worldview.earthdata.nasa.gov/index.html?v=-504.22662231419474,-190.8513647590744,359.77337768580526,219.7736352409256&t=2026-09-07-T01%3A58%3A13Z
- NASA PDS Geosciences Node, Mars Exploration Program https://pds-geosciences.wustl.edu/missions/mep/index.htm
- Microsoft Planetary Computer (Copernicus DEM GLO-30, Sentinel-2 L2A) https://planetarycomputer.microsoft.com
- Earth Search STAC (Element 84) https://earth-search.aws.element84.com/v1 · INGEMMET https://geocatmin.ingemmet.gob.pe
