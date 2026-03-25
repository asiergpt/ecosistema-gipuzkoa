"""Cliente Haiku 4.5 + Web Search para recopilación de datos factuales.

Usa la server-side tool web_search_20250305 para buscar información
actualizada sobre empresas guipuzcoanas. Enriquecimiento completo (22 campos)
para todas las empresas, organizadas en 3 bloques por orden de prioridad.

Modo async para todos los bloques: 10 llamadas en paralelo con
asyncio.Semaphore, batches de 50 empresas (checkpoint cada batch).
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

from src.utils.io import guardar_csv, leer_csv

# ═══════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════

MODEL = "claude-haiku-4-5-20251001"
MAX_SEARCH_USES = 5
MAX_TOKENS = 4096
TEMPERATURE = 0.1
MAX_RETRIES = 3
DELAY_ENTRE_REQUESTS = 1  # segundos entre llamadas (sync)
CHECKPOINT_CADA = 10  # guardar progreso cada N empresas (sync legacy)
ASYNC_CONCURRENCY = 10  # llamadas en paralelo (async)
BATCH_SIZE = 50  # empresas por batch (checkpoint cada batch)

DATA_PROCESSED = Path("data/processed")
INPUT_FILE = DATA_PROCESSED / "step4_validado.csv"
OUTPUT_FILE = DATA_PROCESSED / "step4_enriquecido.csv"
CHECKPOINT_FILE = DATA_PROCESSED / "enrich_checkpoint.csv"
CHECKPOINT_NAMES_FILE = DATA_PROCESSED / "enrich_checkpoint_nombres.txt"

USER_LOCATION = {
    "type": "approximate",
    "city": "Donostia",
    "region": "Gipuzkoa",
    "country": "ES",
    "timezone": "Europe/Madrid",
}

# Campos que Haiku devuelve y que se mapean al DataFrame
CAMPOS_HAIKU = [
    "ceo_actual", "cto_actual", "empleados_numero", "empleados_fuente",
    "ventas_reales", "ventas_fuente", "web_oficial", "ano_constitucion",
    "actividad_resumen", "propiedad_accionistas", "inversores_capital_privado",
    "usa_ia", "ia_detalle", "stack_nivel", "stack_detalle",
    "equipo_tech_estimacion", "roles_tech_detectados",
    # Campos Orkestra (Dimensión 3)
    "pct_exportacion", "inversion_id", "mercado_b2b_b2c",
    "posicion_mercado", "producto_propio",
]

SYSTEM_PROMPT = """Eres un investigador empresarial especializado en el ecosistema vasco.
Tu tarea es buscar en la web información actualizada sobre empresas de Gipuzkoa (País Vasco, España).

<instrucciones>
1. Busca información sobre la empresa indicada usando fuentes fiables en la web.
2. Prioriza fuentes oficiales: web corporativa, eInforma, Empresite, registros mercantiles, LinkedIn.
3. Para empleados: busca el dato de la ENTIDAD LOCAL en Gipuzkoa, NO del grupo global.
   Ejemplo: CAF tiene ~16.000 empleados en el grupo pero ~2.500 en la sede de Beasain.
4. Para inversores: incluye fondos de PE, VC, capital riesgo Y family offices.
   Family offices vascos relevantes: Stellum Capital (Fundación Artizarra), Talde.
5. Para equipo tech: busca ofertas de empleo tech activas y evidencia de equipo IT en la web.
6. Si no encuentras un dato con confianza suficiente, devuelve null en ese campo.
   Es preferible devolver null a inventar un dato. Basa todas tus respuestas exclusivamente
   en información encontrada en los resultados de búsqueda web.
7. Para IA: busca evidencia concreta de uso de inteligencia artificial. Fuentes: web corporativa
   (sección tecnología/innovación/I+D), ofertas de empleo tech, SPRI, BAIC (Basque AI Center),
   artículos LinkedIn de directivos, prensa vasca (El Diario Vasco, Noticias de Gipuzkoa,
   Crónica Vasca), premios innovación (Cámara Gipuzkoa, ADEGI, Innobasque), clusters (AFM,
   ACICAE, GAIA, HEGAN), proyectos europeos (Horizon, CDTI). Busca: machine learning, deep
   learning, computer vision, NLP, RPA, analítica avanzada, mantenimiento predictivo, digital
   twin, IoT industrial, Industria 4.0. Indica PARA QUÉ lo usan.
8. Para stack tecnológico: busca en ofertas de empleo tech (mejor fuente), partnerships
   tecnológicos (Microsoft/AWS/SAP Partner), eventos tech (Basque Industry 4.0), perfiles
   LinkedIn de empleados tech. Básico = ERP (SAP, Oracle, Dynamics), CRM (Salesforce, HubSpot),
   Office 365. Avanzado = cloud nativo, big data, data engineering, microservicios, DevOps,
   BI avanzado, desarrollo propio.
9. Para ventas_reales, devuelve siempre el valor en euros (sin puntos ni comas). Ejemplo: 370000000.
</instrucciones>

<formato_output>
Responde ÚNICAMENTE con un objeto JSON válido. Sin markdown, sin texto adicional, sin backticks.
El JSON debe tener exactamente estos campos:

{
  "ceo_actual": "Nombre del CEO/Director General/Gerente o null",
  "cto_actual": "Nombre del CTO/Director Tecnología/Responsable IT o null",
  "empleados_numero": número_entero_o_null,
  "empleados_fuente": "fuente del dato o null",
  "ventas_reales": número_en_euros_o_null,
  "ventas_fuente": "fuente del dato o null",
  "web_oficial": "URL o null",
  "ano_constitucion": "año o null",
  "actividad_resumen": "descripción breve de la actividad principal o null",
  "propiedad_accionistas": "accionistas principales con porcentaje y tipo o null",
  "inversores_capital_privado": "PE/VC/family offices con porcentaje o null",
  "usa_ia": "Sí|No|null",
  "ia_detalle": "Descripción de para qué usa IA con casos concretos o null",
  "stack_nivel": "Avanzado|Básico|null",
  "stack_detalle": "Descripción del stack tecnológico completo o null",
  "equipo_tech_estimacion": "grande (>20)|medio (5-20)|mínimo (<5)|sin evidencia",
  "roles_tech_detectados": "roles tech encontrados en ofertas/web o null",
  "pct_exportacion": "% aproximado de ventas exportadas fuera de España o null",
  "inversion_id": "Evidencia de I+D: % sobre ventas, centro I+D propio, proyectos o null",
  "mercado_b2b_b2c": "B2B|B2C|Mixto|null",
  "posicion_mercado": "líder mundial|líder europeo|referente nacional|regional|local|null",
  "producto_propio": "Sí, [descripción producto flagship] | No (subcontratista/servicios) | null"
}
</formato_output>

<example>
Para la empresa "Salto Systems" de Oiartzun, Gipuzkoa, una respuesta correcta sería:
{
  "ceo_actual": "Marc Gómez",
  "cto_actual": null,
  "empleados_numero": 1200,
  "empleados_fuente": "web corporativa saltosystems.com",
  "ventas_reales": 370000000,
  "ventas_fuente": "prensa sectorial 2024",
  "web_oficial": "https://www.saltosystems.com",
  "ano_constitucion": "2001",
  "actividad_resumen": "Líder mundial en control de acceso electrónico y cerraduras inteligentes",
  "propiedad_accionistas": "Familia Eguizábal (mayoritario, empresa familiar)",
  "inversores_capital_privado": null,
  "usa_ia": "Sí",
  "ia_detalle": "IA para reconocimiento biométrico en control de acceso (computer vision), analítica predictiva de patrones de uso, NLP en asistente virtual de soporte técnico",
  "stack_nivel": "Avanzado",
  "stack_detalle": "Cloud: AWS (EC2, S3, Lambda, IoT Core). ERP: SAP. Dev: Java, Python, React Native (app móvil). BD: PostgreSQL, DynamoDB. DevOps: Jenkins, Docker, Kubernetes. BI: Tableau",
  "equipo_tech_estimacion": "grande (>20)",
  "roles_tech_detectados": "Software Engineer, Cloud Engineer, Product Manager — múltiples ofertas en LinkedIn",
  "pct_exportacion": "85",
  "inversion_id": "Centro I+D propio en Oiartzun, ~6% sobre ventas, proyectos Horizon Europe",
  "mercado_b2b_b2c": "B2B",
  "posicion_mercado": "líder mundial",
  "producto_propio": "Sí, cerraduras electrónicas y plataforma de control de acceso SALTO KS"
}
</example>"""

# Mapeo de campos Haiku → columnas del DataFrame
FIELD_MAPPING = {campo: campo for campo in CAMPOS_HAIKU}

TOOLS = [{
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": MAX_SEARCH_USES,
    "user_location": USER_LOCATION,
}]


# ═══════════════════════════════════════════════════════════════
# FUNCIONES COMUNES
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
    """Devuelve cadena vacía si el valor es NaN/None, si no str."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    s = str(valor).strip()
    return "" if s.lower() == "nan" else s


def build_user_prompt(row: dict) -> str:
    """Construye el prompt para Haiku — siempre pide los 22 campos.

    Si la empresa ya tiene datos previos (Gemini), los incluye como
    contexto para que Haiku los verifique, corrija y complete.
    """
    nombre = row.get("Nombre") or row.get("nombre", "Desconocida")
    sector = _limpiar_nan(row.get("sector_amigable"))
    municipio = _limpiar_nan(row.get("poblacion") or row.get("municipio")) or "Gipuzkoa"
    actividad = _limpiar_nan(row.get("actividad_resumen"))
    empleados = _limpiar_nan(row.get("numero_empleados"))
    ventas = _limpiar_nan(row.get("ventas_estimado"))
    propiedad = _limpiar_nan(row.get("propiedad_accionistas"))
    web = _limpiar_nan(row.get("web_oficial"))
    ceo = _limpiar_nan(row.get("ceo_actual"))
    pe = _limpiar_nan(row.get("inversores_capital_privado"))

    base = f"Busca información actualizada sobre la empresa '{nombre}'"
    base += f" ubicada en {municipio}, Gipuzkoa (País Vasco, España)."

    if sector:
        base += f" Sector: {sector}."
    if actividad:
        base += f" Actividad conocida: {actividad}."

    datos_previos = []
    if empleados:
        datos_previos.append(f"Empleados registrados: {empleados} — verifica si es entidad local o grupo global.")
    if ventas:
        datos_previos.append(f"Ventas registradas: {ventas}€ — verifica y actualiza si encuentras cifra más reciente.")
    if propiedad:
        datos_previos.append(f"Accionariado registrado: {propiedad} — verifica y completa.")
    if ceo:
        datos_previos.append(f"CEO registrado: {ceo} — verifica si sigue en el cargo.")
    if web:
        datos_previos.append(f"Web registrada: {web}")
    if pe:
        datos_previos.append(f"Inversores registrados: {pe} — verifica y completa.")

    if datos_previos:
        base += "\n\nDatos previos a verificar y completar:"
        for d in datos_previos:
            base += f"\n- {d}"

    base += "\n\nNecesito TODOS los 22 campos del JSON. Busca exhaustivamente en la web."
    base += "\nBusca también datos de competitividad internacional: % exportación, inversión en I+D, si es B2B o B2C, posición en su mercado, y si tiene producto propio."

    return base


def parse_response(response) -> dict | None:
    """Extrae JSON de la respuesta de Haiku.

    Maneja múltiples formatos posibles: JSON puro, JSON dentro de
    markdown, JSON mezclado con texto.
    """
    text_blocks = [b.text for b in response.content if hasattr(b, "text")]
    full_text = "\n".join(text_blocks)

    if not full_text.strip():
        return None

    # Intento 1: parsear directamente
    try:
        return json.loads(full_text.strip())
    except json.JSONDecodeError:
        pass

    # Intento 2: buscar JSON dentro de markdown ```json ... ```
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", full_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Intento 3: buscar cualquier objeto JSON en el texto
    match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", full_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    logger.warning(f"No se pudo parsear JSON de la respuesta: {full_text[:200]}...")
    return None


def _check_web_search_errors(response) -> str | None:
    """Verifica si hay errores en los resultados de web search."""
    for block in response.content:
        if hasattr(block, "type") and block.type == "web_search_tool_result":
            content = block.content
            if hasattr(content, "type") and content.type == "web_search_tool_result_error":
                return content.error_code
    return None


def _count_non_null_fields(data: dict) -> int:
    """Cuenta campos no-null en el resultado."""
    return sum(1 for v in data.values() if v is not None)


def merge_enrichment(row: pd.Series, enriched: dict) -> pd.Series:
    """Mergea datos nuevos de Haiku al row existente.

    REGLA: si Haiku devuelve un valor no-null, sobreescribe.
    Si null, mantiene el existente.
    """
    row = row.copy()

    for haiku_field, col in FIELD_MAPPING.items():
        value = enriched.get(haiku_field)
        if value is not None:
            if not isinstance(value, str):
                value = str(value)
            row[col] = value

    if enriched.get("ventas_reales") is not None:
        row["ventas_confianza"] = "media"

    return row


# ═══════════════════════════════════════════════════════════════
# MODO SYNC (Bloque 1)
# ═══════════════════════════════════════════════════════════════


def enrich_empresa(client: anthropic.Anthropic, row: dict) -> dict | None:
    """Llamada sync a Haiku con web search para una empresa."""
    prompt = build_user_prompt(row)

    for attempt in range(MAX_RETRIES):
        try:
            messages = [{"role": "user", "content": prompt}]

            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )

            while response.stop_reason == "pause_turn":
                logger.debug("pause_turn detectado, reenviando...")
                messages.append({"role": "assistant", "content": response.content})
                response = client.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    temperature=TEMPERATURE,
                    system=SYSTEM_PROMPT,
                    tools=TOOLS,
                    messages=messages,
                )

            ws_error = _check_web_search_errors(response)
            if ws_error in ("too_many_requests", "unavailable"):
                wait = 2 ** (attempt + 1)
                logger.warning(f"Web search error '{ws_error}', reintentando en {wait}s...")
                time.sleep(wait)
                continue

            result = parse_response(response)
            if result is not None:
                return result

            logger.warning("Respuesta sin JSON válido, reintentando...")
            time.sleep(2)

        except anthropic.RateLimitError:
            wait = 2 ** (attempt + 1)
            logger.warning(f"Rate limit (429), reintentando en {wait}s...")
            time.sleep(wait)
        except anthropic.InternalServerError:
            wait = 2 ** (attempt + 1)
            logger.warning(f"Server error (500), reintentando en {wait}s...")
            time.sleep(wait)
        except anthropic.APIStatusError as e:
            if e.status_code == 529:
                wait = 2 ** (attempt + 1)
                logger.warning(f"Overloaded (529), reintentando en {wait}s...")
                time.sleep(wait)
            else:
                logger.error(f"API error inesperado: {e}")
                return None

    logger.error(f"Agotados {MAX_RETRIES} reintentos para '{row.get('Nombre', '?')}'")
    return None


# ═══════════════════════════════════════════════════════════════
# MODO ASYNC (Bloques 2 y 3)
# ═══════════════════════════════════════════════════════════════


async def async_enrich_empresa(
    client: anthropic.AsyncAnthropic,
    row: dict,
    semaphore: asyncio.Semaphore,
) -> dict | None:
    """Llamada async a Haiku con web search para una empresa.

    Usa semáforo para limitar concurrencia. Retry con backoff exponencial.
    """
    prompt = build_user_prompt(row)

    async with semaphore:
        for attempt in range(MAX_RETRIES):
            try:
                messages = [{"role": "user", "content": prompt}]

                response = await client.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    temperature=TEMPERATURE,
                    system=SYSTEM_PROMPT,
                    tools=TOOLS,
                    messages=messages,
                )

                while response.stop_reason == "pause_turn":
                    logger.debug("pause_turn detectado, reenviando...")
                    messages.append({"role": "assistant", "content": response.content})
                    response = await client.messages.create(
                        model=MODEL,
                        max_tokens=MAX_TOKENS,
                        temperature=TEMPERATURE,
                        system=SYSTEM_PROMPT,
                        tools=TOOLS,
                        messages=messages,
                    )

                ws_error = _check_web_search_errors(response)
                if ws_error in ("too_many_requests", "unavailable"):
                    wait = 2 ** (attempt + 1)
                    logger.warning(f"Web search error '{ws_error}', reintentando en {wait}s...")
                    await asyncio.sleep(wait)
                    continue

                result = parse_response(response)
                if result is not None:
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
                    return None

    logger.error(f"Agotados {MAX_RETRIES} reintentos para '{row.get('Nombre', '?')}'")
    return None


async def _procesar_batch_async(
    client: anthropic.AsyncAnthropic,
    batch: list[tuple[int, dict]],
    semaphore: asyncio.Semaphore,
) -> list[tuple[int, str, dict | None]]:
    """Procesa un batch de empresas en paralelo.

    Args:
        batch: lista de (idx_df, row_dict)

    Returns:
        lista de (idx_df, nombre, enriched_dict_o_None)
    """
    async def _single(idx: int, row: dict):
        nombre = row.get("Nombre", f"idx_{idx}")
        result = await async_enrich_empresa(client, row, semaphore)
        return (idx, nombre, result)

    tasks = [_single(idx, row) for idx, row in batch]
    return await asyncio.gather(*tasks)


# ═══════════════════════════════════════════════════════════════
# BLOQUES Y EJECUCIÓN
# ═══════════════════════════════════════════════════════════════


def _preparar_bloques(df: pd.DataFrame) -> dict[int, pd.DataFrame]:
    """Divide el DataFrame en 3 bloques por orden de prioridad.

    Todos los bloques reciben enriquecimiento completo (22 campos).
    Los bloques solo determinan el ORDEN de ejecución.

    Bloque 1: necesita_enriquecimiento == True (~605 empresas nuevas)
    Bloque 2: top 200 por ventas_estimado de las restantes
    Bloque 3: resto de empresas
    """
    bloques = {}

    mask1 = df["necesita_enriquecimiento"] == True  # noqa: E712
    bloques[1] = df[mask1].copy()

    df_resto = df[~mask1].copy()
    df_resto["_ventas_num"] = pd.to_numeric(
        df_resto["ventas_estimado"], errors="coerce"
    )
    top200 = df_resto.nlargest(200, "_ventas_num")
    bloques[2] = top200.drop(columns=["_ventas_num"])

    indices_usados = set(bloques[1].index) | set(bloques[2].index)
    bloques[3] = df[~df.index.isin(indices_usados)].copy()

    return bloques


def _cargar_checkpoint(df: pd.DataFrame) -> set[str]:
    """Carga checkpoint: nombres procesados y restaura datos al DataFrame."""
    procesadas: set[str] = set()

    if CHECKPOINT_NAMES_FILE.exists():
        procesadas = set(
            CHECKPOINT_NAMES_FILE.read_text(encoding="utf-8").strip().splitlines()
        )
        logger.info(f"Checkpoint cargado: {len(procesadas)} empresas ya procesadas")

    if CHECKPOINT_FILE.exists() and procesadas:
        df_checkpoint = leer_csv(CHECKPOINT_FILE)
        for col in CAMPOS_HAIKU:
            if col in df_checkpoint.columns:
                mask = df_checkpoint["Nombre"].isin(procesadas)
                for idx in df_checkpoint[mask].index:
                    if idx in df.index:
                        val = df_checkpoint.at[idx, col]
                        if pd.notna(val):
                            df.at[idx, col] = val
        logger.info(f"Datos de checkpoint restaurados para {len(procesadas)} empresas")

    return procesadas


def _guardar_checkpoint(df: pd.DataFrame, procesadas: set[str]):
    """Guarda checkpoint: DataFrame completo + lista de nombres."""
    guardar_csv(df, CHECKPOINT_FILE)
    CHECKPOINT_NAMES_FILE.write_text("\n".join(procesadas), encoding="utf-8")


def _limpiar_checkpoint():
    """Elimina ficheros de checkpoint."""
    for f in (CHECKPOINT_FILE, CHECKPOINT_NAMES_FILE):
        if f.exists():
            f.unlink()
    logger.info("Checkpoint eliminado (proceso completado)")


def _preparar_columnas(df: pd.DataFrame):
    """Asegura que las columnas Haiku existen y son object dtype."""
    for col in CAMPOS_HAIKU:
        if col not in df.columns:
            df[col] = None
        df[col] = df[col].astype(object)


def _ejecutar_sync(
    df: pd.DataFrame,
    df_bloque: pd.DataFrame,
    bloque_num: int,
    procesadas: set[str],
    max_empresas: int | None,
    total_procesadas: int,
) -> tuple[int, int, int, int]:
    """Ejecuta enriquecimiento secuencial (sync).

    Returns:
        (total_procesadas, total_ok, total_error, total_campos)
    """
    client = load_client()
    total_ok = 0
    total_error = 0
    total_campos = 0
    empresas_bloque = 0

    for idx, row in df_bloque.iterrows():
        nombre = str(row.get("Nombre", f"idx_{idx}"))

        if nombre in procesadas:
            continue
        if max_empresas and total_procesadas >= max_empresas:
            logger.info(f"Límite de {max_empresas} empresas alcanzado")
            break

        empresas_bloque += 1
        logger.info(f"Bloque {bloque_num}: {empresas_bloque}/{len(df_bloque)} — {nombre}")

        enriched = enrich_empresa(client, row.to_dict())

        if enriched is not None:
            campos_ok = _count_non_null_fields(enriched)
            total_campos += campos_ok
            logger.info(f"  OK ({campos_ok}/{len(CAMPOS_HAIKU)} campos)")
            df.loc[idx] = merge_enrichment(df.loc[idx], enriched)
            total_ok += 1
        else:
            logger.warning(f"  ERROR — sin datos para {nombre}")
            total_error += 1

        procesadas.add(nombre)
        total_procesadas += 1

        if total_procesadas % CHECKPOINT_CADA == 0:
            _guardar_checkpoint(df, procesadas)
            logger.debug(f"Checkpoint guardado ({len(procesadas)} procesadas)")

        time.sleep(DELAY_ENTRE_REQUESTS)

    return total_procesadas, total_ok, total_error, total_campos


def _ejecutar_async(
    df: pd.DataFrame,
    df_bloque: pd.DataFrame,
    bloque_num: int,
    procesadas: set[str],
    max_empresas: int | None,
    total_procesadas: int,
) -> tuple[int, int, int, int]:
    """Ejecuta enriquecimiento en paralelo (async, 10 concurrentes).

    Procesa en batches de ASYNC_CONCURRENCY. Cada batch se lanza en
    paralelo con asyncio.gather, se recogen resultados, se mergean
    y se guarda checkpoint.

    Returns:
        (total_procesadas, total_ok, total_error, total_campos)
    """

    async def _run():
        client = load_async_client()
        semaphore = asyncio.Semaphore(ASYNC_CONCURRENCY)

        nonlocal total_procesadas
        total_ok = 0
        total_error = 0
        total_campos = 0

        # Filtrar empresas pendientes
        pendientes = []
        for idx, row in df_bloque.iterrows():
            nombre = str(row.get("Nombre", f"idx_{idx}"))
            if nombre not in procesadas:
                pendientes.append((idx, row.to_dict()))

        if max_empresas:
            restantes = max_empresas - total_procesadas
            pendientes = pendientes[:restantes]

        logger.info(f"Bloque {bloque_num} async: {len(pendientes)} empresas pendientes (batches de {BATCH_SIZE}, {ASYNC_CONCURRENCY} en paralelo)")

        # Procesar en batches de BATCH_SIZE, con ASYNC_CONCURRENCY concurrentes
        for batch_start in range(0, len(pendientes), BATCH_SIZE):
            batch = pendientes[batch_start:batch_start + BATCH_SIZE]
            batch_num = batch_start // BATCH_SIZE + 1
            total_batches = (len(pendientes) + BATCH_SIZE - 1) // BATCH_SIZE

            nombres_batch = [r.get("Nombre", "?") for _, r in batch]
            logger.info(f"  Batch {batch_num}/{total_batches} ({len(batch)} empresas)")

            results = await _procesar_batch_async(client, batch, semaphore)

            for idx, nombre, enriched in results:
                if enriched is not None:
                    campos_ok = _count_non_null_fields(enriched)
                    total_campos += campos_ok
                    logger.info(f"    {nombre}: OK ({campos_ok}/{len(CAMPOS_HAIKU)} campos)")
                    df.loc[idx] = merge_enrichment(df.loc[idx], enriched)
                    total_ok += 1
                else:
                    logger.warning(f"    {nombre}: ERROR — sin datos")
                    total_error += 1

                procesadas.add(nombre)
                total_procesadas += 1

            # Checkpoint después de cada batch
            _guardar_checkpoint(df, procesadas)
            logger.debug(f"Checkpoint guardado ({len(procesadas)} procesadas)")

        await client.close()
        return total_procesadas, total_ok, total_error, total_campos

    return asyncio.run(_run())


def ejecutar(
    bloque: int | None = None,
    max_empresas: int | None = None,
) -> pd.DataFrame:
    """Punto de entrada principal del enriquecimiento con Haiku.

    Todos los bloques usan modo async (10 en paralelo, batches de 50).

    Args:
        bloque: 1, 2, 3 o None para todos (en orden 1→2→3).
        max_empresas: limitar el número de empresas a procesar (para testing).
    """
    logger.info("=" * 60)
    logger.info("ENRIQUECIMIENTO: Haiku 4.5 + Web Search")
    logger.info("=" * 60)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"No se encontró {INPUT_FILE}. Ejecuta primero step4_validar."
        )

    df = leer_csv(INPUT_FILE)
    bloques = _preparar_bloques(df)

    logger.info("Bloques preparados (todos enriquecimiento completo, 22 campos):")
    logger.info(f"  Bloque 1 (nuevas):     {len(bloques[1]):>5} empresas")
    logger.info(f"  Bloque 2 (top 200):    {len(bloques[2]):>5} empresas")
    logger.info(f"  Bloque 3 (resto):      {len(bloques[3]):>5} empresas")

    if bloque is not None:
        bloques_a_procesar = [bloque]
    else:
        bloques_a_procesar = [1, 2, 3]

    procesadas = _cargar_checkpoint(df)
    _preparar_columnas(df)

    total_procesadas = 0
    total_ok = 0
    total_error = 0
    total_campos = 0

    for bloque_num in bloques_a_procesar:
        df_bloque = bloques[bloque_num]

        logger.info(f"\n{'─' * 40}")

        # Todos los bloques usan async con semaphore
        logger.info(f"Procesando Bloque {bloque_num} (async x{ASYNC_CONCURRENCY}, batch {BATCH_SIZE}): {len(df_bloque)} empresas")
        tp, tok, terr, tc = _ejecutar_async(
            df, df_bloque, bloque_num, procesadas, max_empresas, total_procesadas
        )

        total_procesadas = tp
        total_ok += tok
        total_error += terr
        total_campos += tc

        if max_empresas and total_procesadas >= max_empresas:
            break

    # Guardar resultado final
    guardar_csv(df, OUTPUT_FILE)

    # Limpiar checkpoint si se completó todo
    if bloque is None and max_empresas is None:
        _limpiar_checkpoint()

    # Resumen
    logger.info("─" * 40)
    logger.info("RESUMEN Enriquecimiento:")
    logger.info(f"  Total procesadas:     {total_procesadas:>5}")
    logger.info(f"  Exitosas:             {total_ok:>5}")
    logger.info(f"  Con error:            {total_error:>5}")
    logger.info(f"  Campos obtenidos:     {total_campos:>5}")
    if total_ok > 0:
        logger.info(f"  Media campos/empresa: {total_campos / total_ok:.1f}")
    logger.info(f"  Guardado en: {OUTPUT_FILE}")

    return df
