"""Cliente Sonnet 4.6 para clasificación taxonómica (Dimensiones 2 y 3).

Procesa empresas en batches de 15 para reducir coste 15x.
No usa web search — trabaja solo con datos del CSV.
"""

import asyncio
import json
import re
import time
from pathlib import Path

import anthropic
import pandas as pd
from dotenv import load_dotenv
from loguru import logger

from src.utils.io import leer_csv, guardar_csv

# ═══════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 8192
TEMPERATURE = 0.0
MAX_RETRIES = 3
DELAY_ENTRE_BATCHES = 1  # segundos entre super-batches
BATCH_SIZE = 15  # empresas por llamada API
ASYNC_CONCURRENCY = 5  # batches en paralelo

DATA_PROCESSED = Path("data/processed")
INPUT_FILE = DATA_PROCESSED / "step4_enriquecido.csv"
OUTPUT_FILE = DATA_PROCESSED / "step5_con_taxonomia.csv"
CHECKPOINT_FILE = DATA_PROCESSED / "taxonomia_checkpoint.csv"
CHECKPOINT_NAMES_FILE = DATA_PROCESSED / "taxonomia_checkpoint_nombres.txt"

# ═══════════════════════════════════════════════════════════════
# SYSTEM PROMPTS
# ═══════════════════════════════════════════════════════════════

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
Responde ÚNICAMENTE con un JSON válido. Sin markdown, sin texto adicional, sin backticks.
El JSON debe ser un objeto donde cada clave es el nombre EXACTO de la empresa:
{
  "NOMBRE EMPRESA 1": {
    "tipologia_propiedad": "categoría exacta del listado",
    "taxonomia_confianza": "alta|media|baja",
    "taxonomia_razonamiento": "explicación breve de por qué esta categoría"
  },
  "NOMBRE EMPRESA 2": { ... }
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
Output: {"tipologia_propiedad": "Propiedad participativa de trabajadores", "taxonomia_confianza": "alta", "taxonomia_razonamiento": "Cartera Social (sociedad instrumental de trabajadores) tiene ~26% >15% → categoría 9. Kutxabank minoritario no define"}

Input: "TALLER MECANICO AITOR SL" — Sin datos de propiedad — Ventas: 1.9M€ — 8 empleados
Output: {"tipologia_propiedad": "Empresa familiar — Pyme", "taxonomia_confianza": "baja", "taxonomia_razonamiento": "Sin datos de propiedad. Por defecto pyme vasca sin datos = empresa familiar pyme (lo más probable estadísticamente)"}
</examples>"""


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
Responde ÚNICAMENTE con un JSON válido. Sin markdown, sin texto adicional, sin backticks.
El JSON debe ser un objeto donde cada clave es el nombre EXACTO de la empresa:
{
  "NOMBRE EMPRESA 1": {
    "rol_ecosistema": "Campeona oculta|Campeona famosa|Campeona tractora|Resto del tejido empresarial",
    "rol_ecosistema_confianza": "alta|media|baja",
    "rol_ecosistema_razonamiento": "explicación breve"
  },
  "NOMBRE EMPRESA 2": { ... }
}
</formato_output>

<examples>
Input: "DANOBAT S.COOP." — Sector: Maquinaria — Cooperativa Mondragón — 1300 empleados — Patentes: 12
Output: {"rol_ecosistema": "Campeona oculta", "rol_ecosistema_confianza": "alta", "rol_ecosistema_razonamiento": "Confirmada INML Orkestra. Líder mundial rectificadoras. B2B, fabricante, cooperativa vasca, alta I+D"}

Input: "ORONA S.COOP." — Ascensores — Cooperativa independiente — 6486 empleados — 1100M€
Output: {"rol_ecosistema": "Campeona famosa", "rol_ecosistema_confianza": "alta", "rol_ecosistema_razonamiento": "5º fabricante europeo ascensores. >1000M€, >6000 empleados. Referente del ecosistema por escala y marca"}

Input: "ARCELORMITTAL OLABERRIA-BERGARA SL." — Siderurgia — Filial multinacional — ~750M€
Output: {"rol_ecosistema": "Campeona tractora", "rol_ecosistema_confianza": "alta", "rol_ecosistema_razonamiento": "Filial de ArcelorMittal (multinacional). 2 acerías en Gipuzkoa, gran empleador, tira del ecosistema siderúrgico local"}

Input: "BAR RESTAURANTE KAIXO SL" — Hostelería — 5 empleados — 0.5M€
Output: {"rol_ecosistema": "Resto del tejido empresarial", "rol_ecosistema_confianza": "alta", "rol_ecosistema_razonamiento": "Pyme de hostelería local, sin liderazgo de nicho ni escala relevante"}
</examples>"""


# ═══════════════════════════════════════════════════════════════
# FUNCIONES
# ═══════════════════════════════════════════════════════════════


def _load_env():
    """Carga variables de entorno desde config/.env."""
    import os

    env_path = Path("config/.env")
    if env_path.exists():
        try:
            load_dotenv(env_path)
        except UnicodeDecodeError:
            content = env_path.read_text(encoding="utf-16")
            for line in content.strip().splitlines():
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, _, value = line.partition("=")
                    os.environ[key.strip()] = value.strip()
    else:
        load_dotenv()


def load_client() -> anthropic.Anthropic:
    """Carga la API key y retorna el cliente sync Anthropic."""
    _load_env()
    return anthropic.Anthropic()


def load_async_client() -> anthropic.AsyncAnthropic:
    """Carga la API key y retorna el cliente async Anthropic."""
    _load_env()
    return anthropic.AsyncAnthropic()


def _limpiar_nan(valor) -> str:
    """Devuelve cadena vacía si el valor es NaN/None."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    s = str(valor).strip()
    return "" if s.lower() == "nan" else s


def build_batch_prompt(empresas: list[dict], dimension: int) -> str:
    """Construye el prompt con hasta 15 empresas para clasificación batch."""
    lineas = ["<empresas_a_clasificar>"]

    for i, emp in enumerate(empresas, 1):
        nombre = emp.get("Nombre") or emp.get("nombre", "?")
        nif = _limpiar_nan(emp.get("NIF", ""))
        sector = _limpiar_nan(emp.get("sector_amigable", ""))
        ventas = _limpiar_nan(emp.get("ventas_reales")) or _limpiar_nan(emp.get("ventas_estimado", ""))
        empleados = _limpiar_nan(emp.get("empleados_numero", ""))
        propiedad = _limpiar_nan(emp.get("propiedad_accionistas", ""))
        inversores = _limpiar_nan(emp.get("inversores_capital_privado", ""))
        actividad = _limpiar_nan(emp.get("actividad_resumen", ""))
        patentes = _limpiar_nan(emp.get("patentes", ""))
        grupo = _limpiar_nan(emp.get("grupo_empresarial", ""))
        tipologia = _limpiar_nan(emp.get("tipologia_propiedad", ""))
        # Campos Orkestra para Dim 3
        exportacion = _limpiar_nan(emp.get("pct_exportacion", ""))
        id_inversion = _limpiar_nan(emp.get("inversion_id", ""))
        b2b_b2c = _limpiar_nan(emp.get("mercado_b2b_b2c", ""))
        posicion = _limpiar_nan(emp.get("posicion_mercado", ""))
        producto = _limpiar_nan(emp.get("producto_propio", ""))

        lineas.append(f"\n<empresa index=\"{i}\">")
        lineas.append(f"  Nombre: {nombre}")
        if nif:
            lineas.append(f"  NIF: {nif}")
        if sector:
            lineas.append(f"  Sector: {sector}")
        if ventas:
            lineas.append(f"  Ventas: {ventas}€")
        if empleados:
            lineas.append(f"  Empleados: {empleados}")
        if propiedad:
            lineas.append(f"  Accionariado: {propiedad}")
        if inversores:
            lineas.append(f"  Inversores capital privado: {inversores}")
        if actividad:
            lineas.append(f"  Actividad: {actividad}")
        if patentes and patentes != "0":
            lineas.append(f"  Patentes: {patentes}")
        if grupo:
            lineas.append(f"  Grupo empresarial: {grupo}")
        # Para Dim 3, incluir tipología de Dim 2 si ya está
        if dimension == 3 and tipologia:
            lineas.append(f"  Tipología propiedad (Dim 2): {tipologia}")
        # Campos Orkestra (Dim 3)
        if dimension == 3:
            if exportacion:
                lineas.append(f"  % Exportación: {exportacion}")
            if id_inversion:
                lineas.append(f"  I+D: {id_inversion}")
            if b2b_b2c:
                lineas.append(f"  Mercado: {b2b_b2c}")
            if posicion:
                lineas.append(f"  Posición mercado: {posicion}")
            if producto:
                lineas.append(f"  Producto propio: {producto}")
        lineas.append("</empresa>")

    lineas.append("</empresas_a_clasificar>")

    if dimension == 2:
        lineas.append("\nClasifica cada empresa según su tipología de propiedad y gobernanza.")
        lineas.append(f"Aplica la regla de prelación. Responde con JSON para las {len(empresas)} empresas.")
    elif dimension == 3:
        lineas.append("\nClasifica cada empresa según su rol en el ecosistema de Gipuzkoa.")
        lineas.append("Usa los datos de exportación, I+D, mercado B2B/B2C y posición competitiva cuando estén disponibles.")
        lineas.append(f"Responde con JSON para las {len(empresas)} empresas.")

    return "\n".join(lineas)


def parse_batch_response(response, nombres: list[str]) -> dict:
    """Extrae JSON de la respuesta de Sonnet.

    Retorna dict[nombre → clasificación].
    """
    text_blocks = [b.text for b in response.content if hasattr(b, "text")]
    full_text = "\n".join(text_blocks)

    if not full_text.strip():
        return {}

    # Intento 1: parsear directamente
    try:
        return json.loads(full_text.strip())
    except json.JSONDecodeError:
        pass

    # Intento 2: buscar JSON dentro de markdown
    match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", full_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Intento 3: buscar el objeto JSON más grande
    match = re.search(r"\{[\s\S]*\}", full_text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    logger.warning(f"No se pudo parsear JSON: {full_text[:300]}...")
    return {}


async def clasificar_batch_async(
    client: anthropic.AsyncAnthropic,
    empresas: list[dict],
    dimension: int,
    semaphore: asyncio.Semaphore,
) -> dict:
    """Clasifica un batch de 15 empresas con Sonnet (async).

    Args:
        empresas: lista de dicts con datos de empresas
        dimension: 2 (propiedad) o 3 (rol ecosistema)
        semaphore: limita concurrencia

    Returns:
        dict[nombre → clasificación]
    """
    system = SYSTEM_PROMPT_DIM2 if dimension == 2 else SYSTEM_PROMPT_DIM3
    prompt = build_batch_prompt(empresas, dimension)
    nombres = [e.get("Nombre") or e.get("nombre", "?") for e in empresas]

    async with semaphore:
        for attempt in range(MAX_RETRIES):
            try:
                response = await client.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    temperature=TEMPERATURE,
                    system=system,
                    messages=[{"role": "user", "content": prompt}],
                )

                result = parse_batch_response(response, nombres)
                if result:
                    return result

                logger.warning("Respuesta sin JSON válido, reintentando...")
                await asyncio.sleep(2)

            except anthropic.RateLimitError:
                wait = 2 ** (attempt + 1)
                logger.warning(f"Rate limit (429), reintentando en {wait}s...")
                await asyncio.sleep(wait)
            except anthropic.InternalServerError:
                wait = 2 ** (attempt + 1)
                logger.warning(f"Server error (500), reintentando en {wait}s...")
                await asyncio.sleep(wait)
            except anthropic.APIStatusError as e:
                if e.status_code == 529:
                    wait = 2 ** (attempt + 1)
                    logger.warning(f"Overloaded (529), reintentando en {wait}s...")
                    await asyncio.sleep(wait)
                else:
                    logger.error(f"API error inesperado: {e}")
                    return {}

    logger.error(f"Agotados {MAX_RETRIES} reintentos para batch de {len(empresas)} empresas")
    return {}


def _cargar_checkpoint(dimension: int) -> set[str]:
    """Carga nombres procesados del checkpoint."""
    names_file = Path(str(CHECKPOINT_NAMES_FILE).replace(".txt", f"_dim{dimension}.txt"))
    if names_file.exists():
        procesadas = set(names_file.read_text(encoding="utf-8").strip().splitlines())
        logger.info(f"Checkpoint Dim {dimension}: {len(procesadas)} empresas ya clasificadas")
        return procesadas
    return set()


def _guardar_checkpoint(df: pd.DataFrame, procesadas: set[str], dimension: int):
    """Guarda checkpoint."""
    guardar_csv(df, CHECKPOINT_FILE)
    names_file = Path(str(CHECKPOINT_NAMES_FILE).replace(".txt", f"_dim{dimension}.txt"))
    names_file.write_text("\n".join(procesadas), encoding="utf-8")


def _limpiar_checkpoint(dimension: int):
    """Elimina ficheros de checkpoint para una dimensión."""
    names_file = Path(str(CHECKPOINT_NAMES_FILE).replace(".txt", f"_dim{dimension}.txt"))
    for f in (CHECKPOINT_FILE, names_file):
        if f.exists():
            f.unlink()
    logger.info(f"Checkpoint Dim {dimension} eliminado")


def merge_clasificacion(df: pd.DataFrame, nombre: str, data: dict, dimension: int):
    """Mergea clasificación de Sonnet al DataFrame."""
    mask = df["Nombre"] == nombre
    if not mask.any():
        return

    idx = df[mask].index[0]

    if dimension == 2:
        tp = data.get("tipologia_propiedad", "")
        if tp:
            df.at[idx, "tipologia_propiedad"] = tp
        tc = data.get("taxonomia_confianza", "")
        if tc:
            df.at[idx, "taxonomia_confianza"] = tc
        tr = data.get("taxonomia_razonamiento", "")
        if tr:
            df.at[idx, "taxonomia_razonamiento"] = tr
    elif dimension == 3:
        re_ = data.get("rol_ecosistema", "")
        if re_:
            df.at[idx, "rol_ecosistema"] = re_
        rc = data.get("rol_ecosistema_confianza", "")
        if rc:
            df.at[idx, "rol_ecosistema_confianza"] = rc
        rr = data.get("rol_ecosistema_razonamiento", "")
        if rr:
            df.at[idx, "rol_ecosistema_razonamiento"] = rr


def ejecutar(
    dimension: int | None = None,
    batch_size: int = BATCH_SIZE,
    max_empresas: int | None = None,
) -> pd.DataFrame:
    """Punto de entrada: clasifica empresas con Sonnet (async x5).

    Args:
        dimension: 2, 3 o None para ambas (2→3).
        batch_size: empresas por batch API (default 15).
        max_empresas: límite para testing.
    """
    if not INPUT_FILE.exists():
        if CHECKPOINT_FILE.exists():
            df = leer_csv(CHECKPOINT_FILE)
        else:
            raise FileNotFoundError(f"No se encontró {INPUT_FILE}")
    else:
        df = leer_csv(INPUT_FILE)

    dims = [dimension] if dimension else [2, 3]

    # Asegurar columnas existen con dtype object
    for col in ["tipologia_propiedad", "taxonomia_confianza", "taxonomia_razonamiento",
                "mercado_cotizacion", "rol_ecosistema", "rol_ecosistema_confianza",
                "rol_ecosistema_razonamiento"]:
        if col not in df.columns:
            df[col] = pd.Series(dtype="object")
        df[col] = df[col].astype(object)

    for dim in dims:
        logger.info(f"\n{'═' * 60}")
        logger.info(f"CLASIFICACIÓN DIMENSIÓN {dim} (async x{ASYNC_CONCURRENCY})")
        logger.info(f"{'═' * 60}")

        procesadas = _cargar_checkpoint(dim)

        # Filtrar pendientes
        pendientes = []
        for idx, row in df.iterrows():
            nombre = str(row.get("Nombre", f"idx_{idx}"))
            if nombre not in procesadas:
                pendientes.append((idx, row.to_dict()))

        if max_empresas:
            pendientes = pendientes[:max_empresas]

        total = len(pendientes)
        total_api_batches = (total + batch_size - 1) // batch_size
        logger.info(f"Empresas pendientes: {total} ({total_api_batches} batches de {batch_size}, {ASYNC_CONCURRENCY} en paralelo)")

        # Dividir pendientes en batches de batch_size (15 empresas cada uno)
        api_batches = []
        for i in range(0, total, batch_size):
            api_batches.append(pendientes[i:i + batch_size])

        # Ejecutar async
        total_ok, total_alta, total_media, total_baja = _ejecutar_dim_async(
            df, api_batches, dim, procesadas, total_api_batches,
        )

        logger.info(f"  Dim {dim} completada: {total_ok} clasificadas")
        logger.info(f"    Alta: {total_alta} | Media: {total_media} | Baja: {total_baja}")

        _limpiar_checkpoint(dim)

    # Guardar resultado final
    guardar_csv(df, OUTPUT_FILE)
    logger.info(f"Guardado en {OUTPUT_FILE}")

    return df


def _ejecutar_dim_async(
    df: pd.DataFrame,
    api_batches: list[list],
    dim: int,
    procesadas: set[str],
    total_api_batches: int,
) -> tuple[int, int, int, int]:
    """Ejecuta clasificación async con Semaphore(5).

    Procesa en super-batches de ASYNC_CONCURRENCY batches API en paralelo.
    Checkpoint después de cada super-batch.
    """

    async def _run():
        client = load_async_client()
        semaphore = asyncio.Semaphore(ASYNC_CONCURRENCY)

        total_ok = 0
        total_alta = 0
        total_media = 0
        total_baja = 0

        # Procesar en super-batches de ASYNC_CONCURRENCY
        for sb_start in range(0, len(api_batches), ASYNC_CONCURRENCY):
            sb = api_batches[sb_start:sb_start + ASYNC_CONCURRENCY]
            sb_num = sb_start // ASYNC_CONCURRENCY + 1
            total_sb = (len(api_batches) + ASYNC_CONCURRENCY - 1) // ASYNC_CONCURRENCY

            batch_range_start = sb_start + 1
            batch_range_end = min(sb_start + len(sb), total_api_batches)
            logger.info(f"  Dim {dim} super-batch {sb_num}/{total_sb} (batches {batch_range_start}-{batch_range_end}/{total_api_batches})")

            # Lanzar ASYNC_CONCURRENCY batches en paralelo
            tasks = []
            for batch in sb:
                empresas_batch = [row for _, row in batch]
                tasks.append(clasificar_batch_async(client, empresas_batch, dim, semaphore))

            results = await asyncio.gather(*tasks)

            # Procesar resultados
            for batch, result in zip(sb, results):
                nombres_batch = [row.get("Nombre", "?") for _, row in batch]
                for nombre in nombres_batch:
                    if nombre in result:
                        merge_clasificacion(df, nombre, result[nombre], dim)
                        total_ok += 1

                        conf_key = "taxonomia_confianza" if dim == 2 else "rol_ecosistema_confianza"
                        conf = result[nombre].get(conf_key, "baja")
                        if conf == "alta":
                            total_alta += 1
                        elif conf == "media":
                            total_media += 1
                        else:
                            total_baja += 1
                    else:
                        logger.warning(f"    {nombre}: no encontrado en respuesta")

                    procesadas.add(nombre)

            # Checkpoint después de cada super-batch
            _guardar_checkpoint(df, procesadas, dim)

        await client.close()
        return total_ok, total_alta, total_media, total_baja

    return asyncio.run(_run())
