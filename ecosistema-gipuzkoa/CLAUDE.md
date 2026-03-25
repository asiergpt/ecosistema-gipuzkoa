# CLAUDE.md — Ecosistema Empresarial Guipuzcoano

## Contexto del proyecto

Estudio de inteligencia empresarial del ecosistema guipuzcoano para identificar empresas target.
El autor (Asier) es un directivo internacional ex-P&G (top 1% global, +$200M impacto en
transformación digital, 8 años Madrid-Ginebra, equipos +30 personas, Europa/EEUU/APAC).
ADE + Ingeniería Informática en Deusto. Busca identificar qué empresas del tejido vasco
encajan con su perfil: las que necesitan transformar organizaciones resistentes al cambio en
referentes digitales, monetizar tecnología en euros reales, y hablar todos los idiomas del
negocio (de la sala de servidores al comité de dirección).

## Estado actual (actualizado 23 marzo 2026)

Dataset consolidado de **2.842 empresas guipuzcoanas** en `data/processed/step5_con_taxonomia_v2.csv`.
Frontend React + Tailwind operativo en `frontend/` con Dashboard, Explorar y filtros avanzados.

### Lo que está HECHO
1. **Pipeline steps 1-5 completados**: consolidación, mapping sectorial, grupos, validación, taxonomía.
2. **Enriquecimiento con Haiku**: 2.842 empresas enriquecidas con web search (CEO, ventas, empleados,
   accionistas, inversores, stack tech, IA, exportación, posición mercado, producto propio).
3. **Geolocalización**: 616 de 643 empresas sin municipio geolocalizadas con Haiku web search.
   19 marcadas como "Fuera de Gipuzkoa". 6 "Sin determinar". Coste: $21.75.
4. **Comarcas**: 7 comarcas de Gipuzkoa asignadas via Sonnet. Municipios normalizados (104→87 únicos).
5. **Sectores**: Consolidados de 122→41 sectores amigables (nicho→principal via Sonnet).
6. **Dimensión 3 reclasificada** con criterios objetivos (ver abajo).
7. **Diccionarios de entidades**: inversores, tecnologías, aplicaciones IA generados con Sonnet.
8. **Frontend**: Dashboard + Explorar + filtros completos operativos.

### Lo que está PENDIENTE
- Constructor de gráficos dinámicos (vista 3)
- Comparador de empresas y "Mis Targets"
- Sistema multi-agente para Bizkaia/Álava/Navarra
- Step 6: Scoring de encaje con perfil de Asier
- Revisión manual de campeonas (campeonas_clasificacion.xlsx)

## Modelo de clasificación: 3 dimensiones

El modelo clasifica cada empresa en 3 dimensiones independientes que se cruzan.

### Dimensión 1: Mercado de cotización
Un atributo único por empresa.
- **IBEX 35** — 35 empresas más líquidas del mercado continuo español.
- **Mercado Continuo** — Cotiza en el SIBE fuera del IBEX 35. Ej: CAF, Vidrala.
- **BME Growth** — Mercado para pymes en expansión.
- **BME Scaleup** — Antesala de BME Growth, startups con ingresos.
- **No cotiza** — La inmensa mayoría del tejido empresarial.

### Dimensión 2: Tipología de propiedad y gobernanza
Categoría mutuamente excluyente. Se asigna la primera que encaje (regla de prelación):
1. **Filial de multinacional extranjera** — Control >50% por matriz con sede fuera de España.
2. **Filial de grupo español no vasco** — Control por matriz española con sede fuera de Euskadi.
3. **Cooperativa Mondragón** — Integrada en la Corporación MONDRAGON.
4. **Cooperativa independiente — Gran grupo** — No Mondragón, >50M€ o >250 empleados.
5. **Cooperativa independiente — Pyme / Sociedad Laboral** — Cooperativas pequeñas y SAL/SLL.
6. **Participada por PE / capital riesgo / family office** — PE/VC con ≥20% o en consejo.
7. **Empresa familiar — Gran grupo** — Familia controla, >50M€ o >250 empleados, sin PE ≥20%.
8. **Empresa familiar — Pyme** — Familia controla, bajo umbral, sin PE ≥20%.
9. **Propiedad participativa de trabajadores** — Trabajadores >15% capital, no cooperativa ni SAL.
10. **Empresa pública o participada por sector público** — Control/participación instituciones públicas.
11. **Otros** — Fundaciones, asociaciones, joint ventures, o propiedad no determinable.

Aclaraciones específicas:
- Orona y ULMA salieron de Mondragón en dic 2022 → "Cooperativa independiente — Gran grupo".
- Irizar y Ampo salieron en 2008 → "Cooperativa independiente — Gran grupo".
- CAF: Cartera Social ~26% (trabajadores) + Kutxabank ~14% → "Propiedad participativa".
- SAL/SLL: se clasifican en categoría 5 (cooperativa independiente pyme).
- Stellum Capital: gestora PE vasca (Fundación Artizarra). Participadas ≥20% → categoría 6.

### Dimensión 3: Rol en el ecosistema (RECLASIFICADA — criterios objetivos)

Decisión 23 marzo 2026: se abandonan las categorías subjetivas (famosa/tractora) basadas en
juicio de IA. Se aplican criterios 100% objetivos verificables con los datos del CSV.

**3 categorías mutuamente excluyentes, aplicadas en este orden de prelación:**

1. **Campeona visible** — Empresa vasca (NO filial multinacional ni filial grupo español) +
   producto propio (campo `producto_propio` empieza por "Sí") + cualquiera de:
   - Cotiza en bolsa (`mercado_cotizacion` ≠ "No cotiza")
   - >= 250 empleados (`empleados_numero` >= 250)
   - >= 100M€ ventas reales (`ventas_reales` >= 100.000.000)
   Resultado actual: **95 empresas**. Ejemplos: CAF, Orona, Irizar, ULMA, Kutxabank, Salto Systems.

2. **Campeona oculta** (criterios Orkestra INML) — Empresa vasca + B2B
   (`mercado_b2b_b2c` empieza por "B2B" o "Mixto") + producto propio + exporta >= 50%
   (`pct_exportacion` >= 50) + NO es campeona visible.
   Resultado actual: **238 empresas**. Ejemplos: Alcorta Forging, Etxe-Tar, Fundiciones del Estanda.

3. **Resto del tejido empresarial** — Todas las demás (incluye filiales multinacionales, pymes
   sin exportación, distribuidoras, servicios sin producto propio).
   Resultado actual: **2.509 empresas**.

**Relación entre Dimensión 2 y 3**: No son redundantes. La Dim 2 clasifica la estructura de
propiedad (quién manda). La Dim 3 clasifica el rol económico (qué papel juega en el ecosistema).
Una cooperativa pequeña puede ser campeona oculta o simplemente una pyme más.

**Script de reclasificación**: criterios aplicados directamente con Python en
`src/utils/consolidate_sectors_comarcas.py` — no requiere IA.

## Comarcas de Gipuzkoa

7 comarcas asignadas a cada empresa via el campo `comarca`:
- **Donostialdea** (1.168): Donostia-San Sebastián, Hernani, Astigarraga, Andoain, Lasarte-Oria,
  Usurbil, Urnieta, Villabona, Aduna, Orio, Zizurkil, Alkiza, Irura, Ikaztegieta
- **Bidasoa** (563): Irun, Hondarribia, Oiartzun, Lezo, Pasaia, Errenteria
- **Urola-Costa** (299): Azpeitia, Azkoitia, Zarautz, Zumaia, Getaria, Zestoa, Aia, Errezil
- **Bajo Deba** (251): Eibar, Elgoibar, Deba, Mutriku, Soraluze, Mendaro, Elgeta
- **Goierri** (206): Beasain, Ordizia, Lazkao, Zumarraga, Legazpi, Urretxu, Segura, Idiazabal
- **Tolosaldea** (192): Tolosa, Ibarra, Anoeta, Asteasu, Alegia, Belauntza, Legorreta
- **Alto Deba** (187): Arrasate/Mondragón, Bergara, Oñati, Eskoriatza, Aretxabaleta, Antzuola
- Fuera de Gipuzkoa (19), Sin determinar (6)

Mapping generado por Sonnet en `data/processed/comarca_mapping.json`.
Correcciones manuales aplicadas: Errenteria→Bidasoa (no Donostialdea), Irura→Tolosaldea,
Anoeta→Tolosaldea, Elgeta→Bajo Deba, Soraluze→Bajo Deba.

## Diccionarios de entidades

Generados con Sonnet, guardados en `frontend/public/entity_dicts.json`.
Se usan para poblar los filtros del frontend. NO se llama a Sonnet en runtime.

### Inversores y accionistas (filtro unificado)
Estructura con subcategorías:
- **Fondos PE/VC vascos** (12): Stellum (=Easo Ventures+Fundación Artizarra), Talde, Seed Gipuzkoa,
  Diana Capital, Espiga Capital, Inveready, ORZA, Clave Capital, Moira...
- **Fondos PE/VC nacionales** (20): Portobello, Magnum, Alantra, Corp. Financiera Alba (+Artá Capital),
  Sherpa, Peninsula, ProA, Suma, Adara, Columbus...
- **Fondos PE/VC internacionales** (45): KKR, Cinven, PAI Partners, Apollo, Carlyle, Bain, Macquarie,
  Ontario Teachers, Meridiam, Charterhouse, CapVest...
- **Family offices** (14): Onchena, Mirai, Landon, Azora, Sofina, Florac, Xeito, VVG, Mellby Gård...
- **Bancos y cajas** (6): Kutxabank (=Indar Kartera+Kutxa Fundazioa+BBK+Fundación BBK+Vital+Inzu),
  Laboral Kutxa, BBVA, Sabadell, Caja Rural Navarra, Santander
- **Institucionales** (6): Gobierno Vasco (=IVF+Finkatuz+SPRI+Ekarpen+Ezten),
  Estado Español (=CDTI+SETT+SEPI+COFIDES), Diputación, BEI, Gob. Navarra, UE
- **Aceleradoras** (9): BIC Gipuzkoa, Wayra, eCapital, Lanzadera, BerriUp, MassChallenge...

Agrupaciones paraguas clave:
- Ecosistema Kutxabank: Kutxabank + Indar Kartera + Kutxa Fundazioa + BBK + Vital + Inzu
- Stellum: Stellum Capital + Easo Ventures + Fundación Artizarra + Stellum Food&Tech
- Corp. Financiera Alba: Alba + Artá Capital + Grupo March

### Tecnologías (46 en 8 categorías)
Cloud (AWS, Azure, Google Cloud), ERP (SAP, Odoo, Microsoft Dynamics, Solmicro, IFS),
Lenguajes (Python, Java, JavaScript, C#/.NET, C++, PHP), DevOps (Docker, Kubernetes, Jenkins),
BI (Tableau, Power BI, Google Analytics, IBM Cognos), BD (PostgreSQL, SQL Server, Oracle, DynamoDB),
Industrial (Siemens, SCADA, PLC, CNC, CAD/CAM, MES, ANSYS, Fanuc, Heidenhain, Beckhoff),
Otros (Salesforce, React, WordPress, TensorFlow, OpenCV, BIM, Office 365)

### Aplicaciones IA (20)
Computer Vision, Mantenimiento Predictivo, Machine Learning, Analítica Predictiva, Deep Learning,
NLP, Chatbot, Digital Twin, IoT Industrial, Big Data Analytics, RPA, Automatización de Procesos,
Reconocimiento Facial, Optimización de Rutas, Control de Calidad Automatizado, IA Generativa,
OCR, Detección de Fraude, Sistemas de Recomendación, Análisis de Comportamiento

Script de generación: `src/utils/generate_entity_dicts.py` (llama a Sonnet, genera JSON estático).

## Frontend (React + Tailwind + Vite)

En `frontend/`. Usa `npm run dev` para arrancar (puerto 5173/5174).

### Vista 1 — Dashboard
- KPIs: total empresas, campeonas visibles, ocultas, con IA, stack avanzado
- 5 gráficos fijos de barras horizontales apiladas (Recharts):
  1. Rol ecosistema × tipología propiedad
  2. Rol ecosistema × sector amigable (top 10)
  3. Empresas por comarca × rol ecosistema
  4. Tecnología (IA, stack, equipo tech) × rol ecosistema — cruces independientes
  5. Posición competitiva × rol ecosistema
- Colores: visible=#5DCAA5, oculta=#AFA9EC, resto=#D3D1C7
- Todos los gráficos se actualizan con filtros activos

### Vista 2 — Explorar
- Panel lateral izquierdo con filtros organizados en secciones colapsables:
  - Taxonomía: rol ecosistema, tipología propiedad, cotización (multi-select)
  - Inversores y propiedad: inversores/accionistas clave (agrupado por categoría), grupo empresarial
  - Sector y mercado: sector amigable, B2B/B2C, posición mercado, producto propio
  - Tecnología: usa IA, aplicaciones IA, stack nivel, tecnologías (agrupadas), equipo tech
  - Tamaño: empleados (0-7K), ventas (0-2000M€), patentes (0-50), % exportación, año constitución
  - Ubicación: comarca, municipio
  - Búsqueda libre: nombre, CEO, CTO, actividad, roles tech
- Tabla central sorteable: Nombre, Sector, Rol, Propiedad, IA, Stack, Empleados, Ventas, Patentes
- Click en fila abre ficha detallada a la derecha con 30 campos organizados en secciones
- Filtros compartidos entre Dashboard y Explorar (estado global en DataProvider)

### Vista 3 — Constructor (pendiente)
- Generador dinámico de gráficos con dropdowns para ejes, desglose, tipo

### Campos mostrados en fichas
Solo estos 30 campos (sin campos antiguos de Gemini):
Nombre, NIF, sector_amigable, poblacion, comarca, ano_constitucion, web_oficial, actividad_resumen,
ceo_actual, cto_actual, empleados_numero, ventas_reales, patentes, propiedad_accionistas,
inversores_capital_privado, usa_ia, ia_detalle, stack_nivel, stack_detalle,
equipo_tech_estimacion, roles_tech_detectados, pct_exportacion, inversion_id,
mercado_b2b_b2c, posicion_mercado, producto_propio, mercado_cotizacion, tipologia_propiedad,
rol_ecosistema, grupo_empresarial, rol_en_grupo

Campos OCULTOS (NO mostrar): score_viabilidad, veredicto_final, conclusion_sueldo_80k,
justificacion_viabilidad, plataforma_cloud, usa_inteligencia_artificial, perfil_txt,
solvencia_txt, puntos_solv, tamano_ing, complejidad_txt, confianza, criterio,
taxonomia_razonamiento, rol_ecosistema_razonamiento, taxonomia_confianza,
rol_ecosistema_confianza, es_campeona_oculta, Ranking, Ventas, CNAE_Original, SECTOR_NOMBRE,
ventas_estimado, numero_empleados, fuente_entrada, necesita_enriquecimiento,
sector_investigacion, municipio, fuente_detalle, ventas_ref, empleados_ref, descripcion,
ventas_confianza, empleados_fuente, ventas_fuente, private_equity_firmas,
financiacion_publica_detalle

## Arquitectura del proyecto

```
ecosistema-gipuzkoa/
├── CLAUDE.md                          # Este archivo
├── pyproject.toml                     # Dependencias
├── config/
│   ├── settings.yaml                  # Configuración general
│   └── .env                           # API keys (NUNCA commitear)
├── data/
│   ├── raw/                           # Datos de entrada (NO modificar)
│   │   ├── euskadi_navarra_dollar.csv
│   │   ├── ranking_guipuzcoa_con_sectores.csv
│   │   ├── empresas_adicionales_investigacion.csv
│   │   ├── campeonas_ocultas_euskadi.xlsx
│   │   ├── mapping_sectorial_cnae.xlsx
│   │   └── taxonomia_empresarial_euskadi.docx
│   ├── processed/
│   │   ├── step5_con_taxonomia.csv     # Dataset original (bloqueado)
│   │   ├── step5_con_taxonomia_v2.csv  # Dataset actual (fuente de verdad)
│   │   └── comarca_mapping.json        # Mapping municipio→comarca (Sonnet)
│   └── output/
├── src/
│   ├── models/
│   │   └── empresa.py                 # Modelo Pydantic
│   ├── pipeline/
│   │   ├── step1_recuperar.py ... step6_scoring.py
│   ├── enrichment/
│   │   ├── haiku_client.py            # Haiku 4.5 + web search
│   │   └── sonnet_client.py           # Sonnet 4.6
│   └── utils/
│       ├── generate_entity_dicts.py   # Genera diccionarios con Sonnet
│       ├── geolocate_empresas.py      # Geolocaliza con Haiku web search
│       ├── consolidate_sectors_comarcas.py  # Consolida sectores + comarcas
│       ├── fix_municipios.py          # Normaliza municipios post-Haiku
│       ├── cleaning.py
│       └── io.py
├── frontend/
│   ├── public/
│   │   ├── data.csv                   # Copia del CSV para el frontend
│   │   └── entity_dicts.json          # Diccionarios de entidades (Sonnet)
│   ├── src/
│   │   ├── App.jsx                    # Router + DataProvider
│   │   ├── constants.js               # Colores, formateadores, roles
│   │   ├── hooks/useData.jsx          # Estado global: datos, filtros, entidades
│   │   ├── utils/entityExtractor.js   # Matching de entidades vs texto libre
│   │   ├── components/
│   │   │   ├── FilterPanel.jsx        # Panel de filtros completo
│   │   │   ├── KpiCard.jsx
│   │   │   └── StackedBarChart.jsx
│   │   └── pages/
│   │       ├── Dashboard.jsx
│   │       ├── Explorar.jsx
│   │       └── Constructor.jsx        # Placeholder
│   └── package.json
├── tests/
└── cli.py
```

## Convenciones de código

- Python 3.11+, Pydantic v2, Typer, pandas, loguru
- CSV: sep=';', encoding='utf-8-sig'
- Frontend: React 19, Tailwind CSS, Recharts, PapaParse, react-router-dom, Vite
- API key en .env: `ANTHROPIC_API_KEY`
- Modelos: Haiku 4.5 (`claude-haiku-4-5-20251001`) para datos factuales + web search,
  Sonnet 4.6 (`claude-sonnet-4-20250514`) para clasificación y análisis
- CSV numéricos usan formato Python float (punto decimal): `210822000.0` = 210M€.
  NO confundir con separador de miles. Usar `parseFloat()` directo, NO eliminar puntos.

## Fuentes de datos

### Principales
- **ElEconomista ranking**: 7.935 empresas de Gipuzkoa con CNAE, ventas (mayormente placeholders).
- **Dataset Gemini**: 2.237 empresas enriquecidas (actividad, web, empleados, accionariado, PE, tech).
- **Investigación PDF**: 108 empresas adicionales con sector, municipio, descripción, datos referencia.

### Referencia
- **Orkestra INML**: 38 campeonas ocultas de Euskadi (19 en Gipuzkoa).
- **Mapping sectorial**: 277 CNAEs → 41 sectores amigables (consolidado desde 45 original + 81 nicho).
- **Taxonomía propiedad**: Documento con 11 categorías y reglas de prelación.

### Contexto del ecosistema
- Valle del Deba (Elgoibar-Eibar-Bergara): cluster máquina-herramienta más denso de Europa.
- Mondragón Corporation: mayor grupo cooperativo del mundo, sede en Arrasate/Gipuzkoa.
- Parque Tecnológico Miramón: 206 empresas. BIC Gipuzkoa: 500+ empresas promovidas.
- Eje logístico Irún: frontera francesa, comercio transfronterizo.
- Stellum Capital + Easo Ventures: ecosistema PE/VC local (mismo grupo: Fundación Artizarra).
- Programa Gipuzkoa Digitala: €700K para M&A y crecimiento empresarial.

## Notas importantes

- NUNCA commitear credenciales (.env, API keys). Usar python-dotenv.
- Los datos de `data/raw/` son inmutables.
- `step5_con_taxonomia_v2.csv` es la fuente de verdad actual (step5 original puede estar bloqueado).
- El campo `provincia` en el CSV usa "guipúzcoa" con tilde y minúscula.
- NIFs españoles: [ABCDEFGHJPQRSUVW][0-9]{8}. Cooperativas empiezan por F.
- Orkestra usa INML (International Niche Market Leaders) para campeonas ocultas.
- Las cooperativas que salieron de Mondragón siguen siendo cooperativas, solo cambia la categoría.
- Macquarie y Meridiam son fondos privados internacionales, NO institucionales públicos.
- Errenteria pertenece a la comarca de Bidasoa, NO a Donostialdea.

## Costes de API acumulados (sesión 23 marzo 2026)

- Geolocalización Haiku (643 empresas, 1.130 búsquedas web): **$21.75**
- Diccionarios de entidades Sonnet (4 llamadas): ~$3
- Consolidación sectores + comarcas Sonnet (3 llamadas): ~$2
- Agrupación inversores Sonnet (1 llamada): ~$1
- Total sesión: **~$28**
