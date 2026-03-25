# Instrucciones paso a paso: Proyecto Ecosistema Gipuzkoa v2

## Lo que necesitas antes de empezar

- VS Code abierto
- Claude Code instalado (extensión o terminal)
- Python 3.11+ instalado
- Los archivos del proyecto anterior (el ZIP que me pasaste + los CSVs originales)

---

## PASO 1: Preparar la estructura de carpetas

Crea una carpeta nueva para el proyecto. Puedes hacerlo desde la terminal:

```bash
mkdir ecosistema-gipuzkoa
cd ecosistema-gipuzkoa
```

## PASO 2: Colocar los archivos del esqueleto

Descomprime el ZIP `ecosistema-gipuzkoa-project-v2.zip` dentro de esa carpeta.
Debería quedarte esta estructura:

```
ecosistema-gipuzkoa/
├── CLAUDE.md                    ← LO REEMPLAZARÁS en el paso 3
├── cli.py
├── pyproject.toml
├── .gitignore
├── config/
│   └── settings.yaml
├── data/
│   └── {raw,processed,output}/  ← Carpeta vacía, la poblarás en paso 4
├── notebooks/
├── src/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── empresa.py
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── step1_recuperar.py      ← Stubs, Claude Code los implementará
│   │   ├── step2_mapping_sectorial.py
│   │   ├── step3_deduplicar.py
│   │   ├── step4_validar_datos.py
│   │   ├── step5_taxonomia.py
│   │   └── step6_scoring.py
│   ├── enrichment/
│   │   ├── __init__.py
│   │   ├── gemini_client.py        ← SE BORRARÁ, reemplazado por haiku_client.py
│   │   └── claude_client.py        ← SE RENOMBRARÁ a sonnet_client.py
│   └── utils/
│       ├── __init__.py
│       ├── cleaning.py
│       └── io.py
└── tests/
    ├── __init__.py
    └── fixtures/
```

## PASO 3: Reemplazar CLAUDE.md

Coge el archivo `CLAUDE.md` que te acabo de generar (el actualizado con todo Claude,
sin TIBURÓN, con CEO e inversores_capital_privado) y reemplaza el que hay en la raíz:

```bash
# Borra el viejo
rm CLAUDE.md
# Copia el nuevo (ajusta la ruta según dónde lo hayas descargado)
cp ~/Downloads/CLAUDE.md .
```

## PASO 4: Colocar los datos en data/raw/

Necesitas poner estos archivos dentro de `data/raw/`. Los tres primeros vienen de tu
proyecto anterior (el que analizamos en la conversación). Los otros los acabamos de generar.

```
data/raw/
├── euskadi_navarra_dollar.csv                  ← Tu dataset enriquecido con Gemini (2.237 empresas)
├── ranking_guipuzcoa_con_sectores.csv          ← El ranking original pre-filtrado (7.935 empresas)
├── empresas_adicionales_investigacion.csv      ← Las 108 empresas que acabo de extraer del PDF
├── campeonas_ocultas_euskadi.xlsx              ← El Excel de Orkestra (38 campeonas)
├── mapping_sectorial_cnae.xlsx                 ← El mapping CNAE → 45 sectores
└── taxonomia_empresarial_euskadi.docx          ← Tu documento de taxonomía (referencia)
```

**¿De dónde saco cada archivo?**
- `euskadi_navarra_dollar.csv` → Está en tu proyecto anterior, la carpeta donde corría el pipeline v1
- `ranking_guipuzcoa_con_sectores.csv` → También en tu proyecto anterior (es el output del paso de scraping, ANTES del filtrado sectorial)
- `empresas_adicionales_investigacion.csv` → Te lo acabo de dar para descargar
- `campeonas_ocultas_euskadi.xlsx` → Lo subiste al chat
- `mapping_sectorial_cnae.xlsx` → Lo subiste al chat
- `taxonomia_empresarial_euskadi.docx` → Lo subiste al chat

## PASO 5: Crear el .env

```bash
# Dentro de config/
echo "ANTHROPIC_API_KEY=tu-clave-aquí" > config/.env
```

La API key la sacas de https://console.anthropic.com/. Necesitarás cargar créditos
(con $50-100 tienes de sobra para todo el proyecto).

**IMPORTANTE**: Asegúrate de que `.env` está en el `.gitignore` (ya lo está).

## PASO 6: Instalar dependencias

```bash
pip install -e ".[enrichment,dev]"
```

Esto instala pandas, pydantic, typer, anthropic, openpyxl, loguru, etc.

## PASO 7: Verificar que todo está en su sitio

Ejecuta esto para comprobar:

```bash
python -c "
from pathlib import Path
archivos = {
    'CLAUDE.md': 'Especificación del proyecto',
    'data/raw/euskadi_navarra_dollar.csv': 'Dataset Gemini (2.237 empresas)',
    'data/raw/ranking_guipuzcoa_con_sectores.csv': 'Ranking original (7.935)',
    'data/raw/empresas_adicionales_investigacion.csv': '108 empresas investigación',
    'data/raw/campeonas_ocultas_euskadi.xlsx': 'Campeonas ocultas Orkestra',
    'data/raw/mapping_sectorial_cnae.xlsx': 'Mapping CNAE → sectores',
    'config/.env': 'API key Anthropic',
    'src/models/empresa.py': 'Modelo Pydantic',
    'cli.py': 'CLI principal',
}
ok = True
for path, desc in archivos.items():
    existe = Path(path).exists()
    estado = '✓' if existe else '✗ FALTA'
    print(f'  {estado}  {path:<55} ({desc})')
    if not existe: ok = False
print()
print('¡Todo listo!' if ok else 'Faltan archivos. Revisa arriba.')
"
```

## PASO 8: Abrir Claude Code y darle el prompt

Una vez que todo está en su sitio, abre Claude Code en la terminal (o en la extensión
de VS Code) dentro de la carpeta del proyecto.

**Copia y pega el siguiente prompt:**

---

### PROMPT PARA CLAUDE CODE (copia desde aquí)

```
Lee el archivo CLAUDE.md completo — es la especificación del proyecto. Luego implementa
los Steps 1, 2, 3 y 4 del pipeline. Son pasos deterministas (puro pandas, sin IA).

IMPORTANTE antes de implementar:
1. Renombra src/enrichment/gemini_client.py → src/enrichment/haiku_client.py
2. Renombra src/enrichment/claude_client.py → src/enrichment/sonnet_client.py
3. Actualiza los imports en src/enrichment/__init__.py
4. Añade el campo `ceo_actual` al modelo Pydantic en src/models/empresa.py
5. Renombra `private_equity_firmas` → `inversores_capital_privado` en:
   - src/models/empresa.py (en DatosGemini)
   - config/settings.yaml (si aparece)
6. Elimina las referencias a VeredictoFinal (TIBURÓN/PYME/DESCARTAR) y
   ConclusionViabilidad del modelo Pydantic. El Step 6 será "scoring de encaje
   con perfil", no clasificación TIBURÓN.

Luego implementa los 4 steps:

STEP 1 (step1_recuperar.py):
- Lee las 3 fuentes de data/raw/ según describe CLAUDE.md
- El CSV principal usa sep=';' y encoding='utf-8-sig'
- Para el ranking original, el campo de ventas puede ser numérico o texto
  ("corporativa", "grande", "mediana"). Recupera las que tengan ventas >2M€
  O categoría "grande"/"corporativa", siempre que no estén ya en las 2.237
- Para las 108 empresas adicionales, haz fuzzy matching por nombre (thefuzz)
  contra las existentes para evitar duplicados. Umbral: 85
- Marca fuente_entrada y necesita_enriquecimiento
- Guarda en data/processed/step1_dataset_consolidado.csv
- Imprime resumen: cuántas de cada fuente, cuántas nuevas, cuántas duplicadas

STEP 2 (step2_mapping_sectorial.py):
- Lee mapping_sectorial_cnae.xlsx (columnas: 'Sector Amigable', 'CNAE 2 dig.',
  'CNAE 3 dig.')
- Extrae 2-3 primeros dígitos del CNAE de cada empresa
- Match a 3 dígitos tiene prioridad sobre 2 dígitos
- Si no hay CNAE (empresas de investigación), usa sector_investigacion como
  valor temporal en sector_amigable
- Guarda en data/processed/step2_con_sectores.csv
- Imprime distribución de los 10 sectores con más empresas

STEP 3 (step3_deduplicar.py):
- Lee grupos_conocidos de config/settings.yaml
- Busca en el nombre de cada empresa si contiene la raíz del grupo
- También usa propiedad_accionistas para detectar relaciones
- Asigna grupo_empresarial y rol_en_grupo
- NO borra filas — mantiene cada entidad separada
- Guarda en data/processed/step3_con_grupos.csv
- Imprime los grupos detectados con sus miembros

STEP 4 (step4_validar_datos.py):
- Detecta ventas placeholder (50000000, 25000000, 1900000 exactos)
  → ventas_confianza = "baja"
- Ventas que no son placeholder → ventas_confianza = "alta"
- Parsea numero_empleados (string) usando parsear_empleados() de utils/cleaning.py
- Cruza con empresas_adicionales_investigacion.csv para enriquecer datos:
  si una empresa aparece allí con ventas_ref o empleados_ref, usar esos valores
  como ventas_reales/empleados_numero y marcar confianza "media"
- Detecta anomalías: empleados >5000 en empresa sin ventas altas, patentes
  >20 en empresa de servicios, etc.
- Genera data/processed/step4_validado.csv + data/processed/informe_calidad.json
- El informe debe incluir: total empresas, % con ventas reales, % con empleados,
  % que necesitan enriquecimiento, anomalías detectadas

PARA TODOS LOS STEPS:
- Usa loguru para logging
- Usa las funciones de src/utils/io.py para leer/escribir CSVs
- Cada step tiene una función ejecutar() que es el punto de entrada
- Conecta los steps al CLI en cli.py (descomenta los imports y llama a ejecutar())
- Si un CSV intermedio no existe, el step debe dar error claro diciendo qué falta
- Escribe al menos 2-3 tests en tests/ para verificar funciones clave
```

### FIN DEL PROMPT

---

## PASO 9: Revisar lo que Claude Code ha hecho

Cuando Claude Code termine, ejecuta:

```bash
# Verifica que los steps corren
python cli.py step1-recuperar
python cli.py step2-mapping
python cli.py step3-grupos
python cli.py step4-validar

# Revisa el informe de calidad
cat data/processed/informe_calidad.json | python -m json.tool

# Mira cuántas empresas hay
python -c "
import pandas as pd
df = pd.read_csv('data/processed/step4_validado.csv', sep=';', encoding='utf-8-sig')
print(f'Total empresas: {len(df)}')
print(f'Con ventas reales: {(df.get(\"ventas_confianza\",\"\")==\"alta\").sum()}')
print(f'Necesitan enriquecimiento: {df.get(\"necesita_enriquecimiento\",False).sum()}')
"
```

## PASO 10: Vuelve a este chat con los resultados

Tráeme:
1. El output de los 4 steps (lo que imprime en terminal)
2. El contenido de `informe_calidad.json`
3. Cualquier error que haya dado

Yo lo reviso y diseñamos juntos el enriquecimiento con Haiku (Step 5 prep) y
la clasificación taxonómica con Sonnet (Step 5).

---

## Resumen visual del flujo

```
TÚ (ahora)                    CLAUDE CODE                   ESTE CHAT (después)
─────────────                  ───────────                   ──────────────────
1. Crear carpeta               
2. Descomprimir ZIP            
3. Reemplazar CLAUDE.md        
4. Poner datos en data/raw/    
5. Crear .env                  
6. pip install                 
7. Verificar archivos          
8. Copiar prompt ──────────→   9. Implementa Steps 1-4
                               10. Ejecutar steps ──────→   11. Revisar resultados
                                                             12. Diseñar Steps 5-6
```
