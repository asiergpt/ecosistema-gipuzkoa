# PROMPT PARA CLAUDE CODE — Step 5: Clasificación Taxonómica con Sonnet

Copia todo lo que está debajo de esta línea y pégalo en Claude Code:

---

Lee estos recursos ANTES de escribir código:

1. CLAUDE.md del proyecto — secciones "Modelo de clasificación: 3 dimensiones" y "Paso 5: Taxonomía"
2. El documento de taxonomía en data/raw/taxonomia_empresarial_euskadi.docx (referencia completa)
3. Best practices de prompting: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
4. Structured outputs: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
5. Increase output consistency: https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/increase-consistency
6. Batch processing: https://platform.claude.com/docs/en/build-with-claude/batch-processing

Implementa src/pipeline/step5_taxonomia.py y src/enrichment/sonnet_client.py. Conéctalos al CLI.

## Arquitectura del Step 5

El Step 5 clasifica cada empresa en 3 dimensiones independientes:
- Dimensión 1 (Cotización): DETERMINISTA, sin IA
- Dimensión 2 (Propiedad): Sonnet con batch de 15 empresas por llamada
- Dimensión 3 (Rol ecosistema): Sonnet con batch de 15 empresas por llamada

## Dimensión 1: Mercado de cotización (determinista)

Implementar en step5_taxonomia.py SIN llamar a la API. Es puro lookup:

```python
COTIZADAS_GIPUZKOA = {
    # NIF → (nombre, mercado)
    "A20001020": ("CAF", "Mercado Continuo"),
    # Añadir más si se conocen - por ahora la mayoría son "No cotiza"
}

# También buscar en el nombre por si no tenemos NIF
COTIZADAS_POR_NOMBRE = {
    "CIE AUTOMOTIVE": "IBEX 35",
    "CAF": "Mercado Continuo",
    "VIDRALA": "Mercado Continuo",
    "TUBACEX": "Mercado Continuo",
    "IBERPAPEL": "Mercado Continuo",
}

def clasificar_cotizacion(row: dict) -> str:
    """Dimensión 1: determinista."""
    nif = row.get("NIF", "")
    nombre = (row.get("Nombre") or row.get("nombre", "")).upper()
    
    if nif in COTIZADAS_GIPUZKOA:
        return COTIZADAS_GIPUZKOA[nif][1]
    
    for clave, mercado in COTIZADAS_POR_NOMBRE.items():
        if clave in nombre:
            return mercado
    
    return "No cotiza"
```

## Dimensión 2: Propiedad/Gobernanza (Sonnet batch)

### System prompt para Sonnet — Dimensión 2

Sigue todas las best practices de Anthropic Academy:
- Rol especializado con contexto del ecosistema vasco
- Regla de prelación como instrucciones secuenciales numeradas
- XML tags para estructura
- Ejemplos diversos que cubren edge cases
- Output JSON schema fijo
- Anti-alucinación: "Si no hay datos suficientes, asigna Otros con confianza baja"

```python
SYSTEM_PROMPT_DIM2 = """Eres un analista experto en estructura empresarial del País Vasco.
Tu tarea es clasificar empresas según su tipología de propiedad y gobernanza.

<regla_de_prelacion>
Asigna la PRIMERA categoría que encaje, recorriendo esta lista de arriba a abajo:

1. Filial de multinacional extranjera — Control >50% por matriz con sede FUERA de España.
2. Filial de grupo español no vasco — Control por matriz española con sede FUERA de Euskadi.
3. Cooperativa Mondragón — Cooperativa actualmente integrada en la Corporación MONDRAGON.
4. Cooperativa independiente — Gran grupo — Cooperativa NO Mondragón con >50M€ o >250 empleados.
5. Cooperativa independiente — Pyme / Sociedad Laboral — Cooperativa pequeña o SAL/SLL.
6. Participada por PE / capital riesgo / family office — Fondo PE/VC/family office con ≥20% o en consejo. Prevalece sobre "familiar".
7. Empresa familiar — Gran grupo — Familia controla, >50M€ o >250 empleados, sin PE ≥20%.
8. Empresa familiar — Pyme — Familia controla, bajo umbral, sin PE ≥20%.
9. Propiedad participativa de trabajadores — Trabajadores >15% capital, no cooperativa ni SAL.
10. Empresa pública o participada por sector público — Control por instituciones públicas.
11. Otros — Fundaciones, asociaciones, JVs, o propiedad no determinable.
</regla_de_prelacion>

<pistas_importantes>
- NIF que empieza por F = cooperativa (pero ¿Mondragón o independiente? Verificar)
- Cooperativas Mondragón conocidas: Fagor Arrasate, Fagor Ederlan, Copreci, Orkli, Goizper, Danobat, Soraluce, Fagor Automation, Mondragon Assembly, Cikautxo, Eika, Erreka, Embega, Laboral Kutxa, LKS Next, Bexen Medical, Domusa Teknik, RPK
- Cooperativas que SALIERON de Mondragón: Orona, ULMA (dic 2022), Irizar, Ampo (2008) → son "Cooperativa independiente — Gran grupo"
- Family offices vascos: Stellum Capital (Fundación Artizarra), Talde → si ≥20% → categoría 6
- CAF: Cartera Social ~26% (trabajadores) → categoría 9 "Propiedad participativa"
- Kutxabank como accionista minoritario NO define la categoría
- SAL/SLL = Sociedad Anónima/Limitada Laboral → categoría 5
</pistas_importantes>

<formato_output>
Para cada empresa, responde con un JSON object que tiene el nombre como clave:
{
  "NOMBRE EMPRESA": {
    "tipologia_propiedad": "categoría exacta del listado",
    "taxonomia_confianza": "alta|media|baja",
    "taxonomia_razonamiento": "explicación breve de por qué esta categoría"
  }
}

Confianza:
- alta: datos claros que determinan inequívocamente la categoría
- media: hay pistas razonables pero no certeza total
- baja: no hay datos suficientes, clasificación por defecto
</formato_output>

<examples>
Input: "ARCELORMITTAL OLABERRIA-BERGARA SL." — Propiedad: "ArcelorMittal (Luxemburgo, 100%)"
Output: {"tipologia_propiedad": "Filial de multinacional extranjera", "taxonomia_confianza": "alta", "taxonomia_razonamiento": "Controlada 100% por ArcelorMittal, multinacional con sede en Luxemburgo"}

Input: "FAGOR EDERLAN S.COOP." — NIF: F20... — Propiedad: "Cooperativa integrada en Mondragón"
Output: {"tipologia_propiedad": "Cooperativa Mondragón", "taxonomia_confianza": "alta", "taxonomia_razonamiento": "NIF F (cooperativa) + integrada en Corporación Mondragón"}

Input: "ORONA S.COOP." — NIF: F20... — Ventas: 1.100M€ — Propiedad: "Cooperativa, salió de Mondragón dic 2022"
Output: {"tipologia_propiedad": "Cooperativa independiente — Gran grupo", "taxonomia_confianza": "alta", "taxonomia_razonamiento": "Cooperativa que salió de Mondragón en 2022. >50M€ → Gran grupo"}

Input: "URKABE BENETAN" — Propiedad: "Stellum Food&Tech (31,5%)"
Output: {"tipologia_propiedad": "Participada por PE / capital riesgo / family office", "taxonomia_confianza": "alta", "taxonomia_razonamiento": "Stellum Capital (family office vasco) tiene 31,5% ≥20% → prevalece sobre familiar"}

Input: "CONSTRUCCIONES Y AUXILIAR DE FERROCARRILES, SA" — Propiedad: "Cartera Social ~26%, Kutxabank ~14%"
Output: {"tipologia_propiedad": "Empresa con propiedad participativa de trabajadores", "taxonomia_confianza": "alta", "taxonomia_razonamiento": "Cartera Social (sociedad instrumental de trabajadores) tiene ~26% >15% → categoría 9. Kutxabank minoritario no define"}

Input: "TALLER MECANICO AITOR SL" — Sin datos de propiedad — Ventas: 1.9M€ — 8 empleados
Output: {"tipologia_propiedad": "Empresa familiar — Pyme", "taxonomia_confianza": "baja", "taxonomia_razonamiento": "Sin datos de propiedad. Por defecto pyme vasca sin datos = empresa familiar pyme (lo más probable estadísticamente)"}
</examples>"""
```

## Dimensión 3: Rol en el ecosistema (Sonnet batch)

### System prompt para Sonnet — Dimensión 3

```python
SYSTEM_PROMPT_DIM3 = """Eres un analista experto en el ecosistema empresarial del País Vasco.
Tu tarea es clasificar empresas según su rol en el ecosistema de Gipuzkoa.

<categorias>
1. Campeona oculta (INML) — Empresa vasca líder en nicho de mercado internacional.
   Criterios Orkestra: top 1 Europa o top 3 mundial en su nicho, B2B, fabricante,
   exporta >50%, alta innovación (4%+ I+D), producto propio, propiedad vasca,
   >10 años, poco conocida fuera de su sector.
   NO todas las empresas industriales son campeonas ocultas — necesitan liderazgo mundial en nicho.

2. Campeona famosa — Empresa vasca grande y conocida. Referente por tamaño, marca o visibilidad.
   Propiedad vasca. No necesariamente líder en nicho pero relevante por escala (>200M€ o >1000 empleados).

3. Campeona tractora — Filial de multinacional extranjera o grupo español no vasco con presencia
   significativa en Gipuzkoa (>100 empleados o >50M€ locales). Tira del ecosistema.
   SIEMPRE es "Filial multinacional" o "Filial grupo español" en Dimensión 2.

4. Resto del tejido empresarial — No encaja en las anteriores.
   La mayoría de empresas caen aquí: pymes locales, comercio, servicios, construcción.
</categorias>

<campeonas_ocultas_confirmadas_orkestra>
Estas empresas están confirmadas como INML por Orkestra:
Salto Systems, Wavegarden, AMPO, Graphenea, Orbinox, Pasaban, Bellota/VNPI,
Alcorta Forging, Irizar Forge, Etxe-Tar, Danobat, Soraluce, Orkli, Goizper,
Copreci, Fagor Automation, Ikusi (Velatia), Ingeteam
</campeonas_ocultas_confirmadas_orkestra>

<campeonas_famosas_confirmadas>
CAF, Irizar, Orona, Grupo Uvesco, CIE Automotive, Velatia, Laboral Kutxa
</campeonas_famosas_confirmadas>

<formato_output>
Para cada empresa, responde con JSON:
{
  "NOMBRE EMPRESA": {
    "rol_ecosistema": "Campeona oculta|Campeona famosa|Campeona tractora|Resto del tejido empresarial",
    "rol_ecosistema_confianza": "alta|media|baja",
    "rol_ecosistema_razonamiento": "explicación breve"
  }
}
</formato_output>

<examples>
Input: "DANOBAT S.COOP." — Sector: Maquinaria — Cooperativa Mondragón — 1300 empleados — Patentes: 12
Output: {"rol_ecosistema": "Campeona oculta", "rol_ecosistema_confianza": "alta", "rol_ecosistema_razonamiento": "Confirmada INML Orkestra. Líder mundial rectificadoras. B2B, fabricante, cooperativa vasca, alta I+D (8-10%)"}

Input: "ORONA S.COOP." — Ascensores — Cooperativa independiente — 6486 empleados — 1100M€
Output: {"rol_ecosistema": "Campeona famosa", "rol_ecosistema_confianza": "alta", "rol_ecosistema_razonamiento": "5º fabricante europeo ascensores. >1000M€, >6000 empleados. Referente del ecosistema por escala y marca"}

Input: "ARCELORMITTAL OLABERRIA-BERGARA SL." — Siderurgia — Filial multinacional — ~750M€
Output: {"rol_ecosistema": "Campeona tractora", "rol_ecosistema_confianza": "alta", "rol_ecosistema_razonamiento": "Filial de ArcelorMittal (multinacional). 2 acerías en Gipuzkoa, gran empleador, tira del ecosistema siderúrgico local"}

Input: "BAR RESTAURANTE KAIXO SL" — Hostelería — 5 empleados — 0.5M€
Output: {"rol_ecosistema": "Resto del tejido empresarial", "rol_ecosistema_confianza": "alta", "rol_ecosistema_razonamiento": "Pyme de hostelería local, sin liderazgo de nicho ni escala relevante"}
</examples>"""
```

## User prompt para batches de 15 empresas

```python
def build_batch_prompt(empresas: list[dict], dimension: int) -> str:
    """Construye el prompt con 15 empresas para clasificación batch.
    
    Sigue 'Be clear and direct' y 'Long context: put data at top'.
    Los datos van primero, la instrucción al final.
    """
    lineas = ["<empresas_a_clasificar>"]
    
    for i, emp in enumerate(empresas, 1):
        nombre = emp.get("Nombre") or emp.get("nombre", "?")
        nif = emp.get("NIF", "")
        sector = emp.get("sector_amigable", "")
        ventas = emp.get("ventas_reales") or emp.get("ventas_estimado", "")
        empleados = emp.get("empleados_numero", "")
        propiedad = emp.get("propiedad_accionistas", "")
        inversores = emp.get("inversores_capital_privado", "")
        actividad = emp.get("actividad_resumen", "")
        patentes = emp.get("patentes", 0)
        grupo = emp.get("grupo_empresarial", "")
        es_campeona = emp.get("es_campeona_oculta", False)
        # Campos Orkestra para Dim 3
        exportacion = emp.get("pct_exportacion", "")
        id_inversion = emp.get("inversion_id", "")
        b2b_b2c = emp.get("mercado_b2b_b2c", "")
        posicion = emp.get("posicion_mercado", "")
        producto = emp.get("producto_propio", "")
        
        lineas.append(f"\n<empresa index=\"{i}\">")
        lineas.append(f"  Nombre: {nombre}")
        if nif: lineas.append(f"  NIF: {nif}")
        if sector: lineas.append(f"  Sector: {sector}")
        if ventas: lineas.append(f"  Ventas: {ventas}€")
        if empleados: lineas.append(f"  Empleados: {empleados}")
        if propiedad: lineas.append(f"  Accionariado: {propiedad}")
        if inversores: lineas.append(f"  Inversores capital privado: {inversores}")
        if actividad: lineas.append(f"  Actividad: {actividad}")
        if patentes: lineas.append(f"  Patentes: {patentes}")
        if grupo: lineas.append(f"  Grupo empresarial: {grupo}")
        if es_campeona: lineas.append(f"  Confirmada campeona oculta Orkestra: Sí")
        # Campos Orkestra (Dim 3)
        if exportacion: lineas.append(f"  % Exportación: {exportacion}")
        if id_inversion: lineas.append(f"  I+D: {id_inversion}")
        if b2b_b2c: lineas.append(f"  Mercado: {b2b_b2c}")
        if posicion: lineas.append(f"  Posición mercado: {posicion}")
        if producto: lineas.append(f"  Producto propio: {producto}")
        lineas.append("</empresa>")
    
    lineas.append("</empresas_a_clasificar>")
    
    if dimension == 2:
        lineas.append("\nClasifica cada empresa según su tipología de propiedad y gobernanza.")
        lineas.append(f"Aplica la regla de prelación. Responde con JSON para las {len(empresas)} empresas.")
    elif dimension == 3:
        lineas.append("\nClasifica cada empresa según su rol en el ecosistema de Gipuzkoa.")
        lineas.append(f"Usa los datos de exportación, I+D, mercado B2B/B2C y posición competitiva cuando estén disponibles.")
        lineas.append(f"Responde con JSON para las {len(empresas)} empresas.")
    
    return "\n".join(lineas)
```

## Estructura de sonnet_client.py

```
1. CONSTANTES: SYSTEM_PROMPT_DIM2, SYSTEM_PROMPT_DIM3, MODEL="claude-sonnet-4-6"
2. load_config() → anthropic.Anthropic() desde .env
3. build_batch_prompt(empresas, dimension) → prompt con 15 empresas
4. parse_batch_response(response, nombres) → dict[nombre → clasificación]
5. clasificar_batch(client, empresas, dimension) → clasificaciones
6. ejecutar(dimension, batch_size=15, max_empresas=None) → punto de entrada
```

## Estructura de step5_taxonomia.py

```
1. clasificar_cotizacion(row) → Dimensión 1 (determinista)
2. Pre-clasificar cooperativas por NIF (F → cooperativa) y por settings.yaml
3. Llamar a sonnet_client para Dimensión 2 en batches de 15
4. Llamar a sonnet_client para Dimensión 3 en batches de 15
5. Cruzar con campeonas_ocultas_euskadi.xlsx → marcar es_campeona_oculta
6. Modo semiautomático: confianza "baja" → exportar a data/output/revision_taxonomia.xlsx
7. Output: data/processed/step5_con_taxonomia.csv
```

## Checkpoint y resiliencia

- Guardar progreso después de cada batch de 15 empresas
- Si se interrumpe, retomar desde el último batch completado
- Rate limiting: time.sleep(2) entre batches (Sonnet es más caro)
- Retry con backoff: 3 reintentos para 429/500
- Logging: "Dim 2 batch 5/40 — 75 empresas clasificadas — 68 alta confianza"

## CLI

Conecta al cli.py:
- python cli.py classify --dimension 2
- python cli.py classify --dimension 3
- python cli.py classify --all (dim 1 + 2 + 3)
- python cli.py classify --max-empresas 30 (para testing, 2 batches)
- python cli.py export-revision (genera revision_taxonomia.xlsx con las de baja confianza)

## INSTRUCCIONES FINALES

1. Implementa todo el código
2. Haz prueba: python cli.py classify --dimension 2 --max-empresas 15 (1 solo batch)
3. Muéstrame los resultados del primer batch antes de lanzar el completo
4. Sonnet NO usa web search — trabaja solo con los datos que ya tenemos en el CSV
5. El batch de 15 empresas reduce el coste 15x respecto a 1 llamada por empresa
6. Para Dim 3, necesita el resultado de Dim 2 (propiedad influye en el rol)
   Ejecutar siempre en orden: Dim 1 → Dim 2 → Dim 3
