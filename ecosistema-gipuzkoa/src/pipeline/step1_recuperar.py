"""
Pipeline: Step 1 — Recuperar empresas eliminadas y consolidar fuentes.

Consolida 3 fuentes:
1. euskadi_navarra_dollar.csv (2.237 empresas guipuzcoanas enriquecidas con Gemini)
2. ranking_guipuzcoa_con_sectores.csv (7.935 empresas pre-filtrado)
3. empresas_adicionales_investigacion.csv (108 empresas de investigación)
"""

from pathlib import Path

import pandas as pd
import yaml
from loguru import logger
from thefuzz import fuzz

from src.utils.cleaning import limpiar_nombre_legal, normalizar_texto
from src.utils.io import guardar_csv, leer_csv

# Rutas
DATA_RAW = Path("data/raw")
DATA_PROCESSED = Path("data/processed")
CONFIG = Path("config/settings.yaml")


def _cargar_config() -> dict:
    """Carga configuración del proyecto."""
    with open(CONFIG, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _parsear_ventas_texto(ventas_str: str) -> tuple[float | None, str | None]:
    """Convierte el campo Ventas del ranking a número y texto original.

    Retorna (valor_numerico, texto_categoria).
    - "1.861.621.350" → (1861621350.0, None)
    - "corporativa" → (None, "corporativa")
    """
    if pd.isna(ventas_str):
        return None, None

    ventas_str = str(ventas_str).strip().lower()

    # Categorías textuales
    categorias = {"corporativa", "grande", "mediana", "pequeña", "pequeã±a"}
    if ventas_str in categorias:
        return None, ventas_str

    # Intentar parsear como número (formato español: puntos como separador de miles)
    try:
        valor = float(ventas_str.replace(".", "").replace(",", "."))
        return valor, None
    except ValueError:
        return None, ventas_str


def _cargar_base_gemini() -> pd.DataFrame:
    """Carga las 2.237 empresas guipuzcoanas ya enriquecidas."""
    df = leer_csv(DATA_RAW / "euskadi_navarra_dollar.csv")

    # Filtrar solo guipúzcoa
    df["provincia_norm"] = df["provincia"].str.lower().str.strip()
    df = df[df["provincia_norm"].str.contains("guip", na=False)].copy()
    df.drop(columns=["provincia_norm"], inplace=True)

    logger.info(f"Base Gemini (guipúzcoa): {len(df)} empresas")
    return df


def _recuperar_del_ranking(df_base: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Recupera empresas del ranking original que cumplen criterios.

    Criterios: ventas >2M€ O categoría 'grande'/'corporativa',
    siempre que no estén ya en df_base.
    """
    df_ranking = leer_csv(DATA_RAW / "ranking_guipuzcoa_con_sectores.csv")
    umbral = config["pipeline"]["umbral_ventas_minimo"]
    categorias = set(config["pipeline"]["categorias_recuperar"])

    # Nombres ya existentes (normalizados) para comparar
    nombres_base = set(df_base["Nombre"].apply(normalizar_texto))

    recuperadas = []
    for _, row in df_ranking.iterrows():
        valor, texto = _parsear_ventas_texto(row["Ventas"])

        cumple_ventas = valor is not None and valor > umbral
        cumple_categoria = texto is not None and texto in categorias

        if not (cumple_ventas or cumple_categoria):
            continue

        # Verificar que no esté ya en la base
        nombre_norm = normalizar_texto(str(row["Nombre"]))
        if nombre_norm in nombres_base:
            continue

        recuperadas.append(row)

    df_recup = pd.DataFrame(recuperadas)
    logger.info(f"Recuperadas del ranking: {len(df_recup)} empresas nuevas")
    return df_recup


def _cargar_empresas_adicionales(df_existentes: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Carga las 108 empresas de investigación, filtrando duplicados por fuzzy matching.

    Retorna (df_nuevas, num_duplicadas).
    """
    df_adicionales = leer_csv(DATA_RAW / "empresas_adicionales_investigacion.csv")

    # Nombres existentes para fuzzy matching
    nombres_existentes = [normalizar_texto(str(n)) for n in df_existentes["Nombre"]]

    nuevas = []
    duplicadas = 0
    for _, row in df_adicionales.iterrows():
        nombre_norm = normalizar_texto(str(row["nombre"]))
        nombre_limpio = limpiar_nombre_legal(str(row["nombre"]))

        # Fuzzy match contra existentes
        es_duplicada = False
        for nombre_exist in nombres_existentes:
            nombre_exist_limpio = limpiar_nombre_legal(nombre_exist)
            score = fuzz.token_sort_ratio(nombre_limpio, nombre_exist_limpio)
            if score >= 85:
                logger.debug(f"Duplicada: '{row['nombre']}' ~ '{nombre_exist}' (score={score})")
                es_duplicada = True
                break

        if es_duplicada:
            duplicadas += 1
        else:
            nuevas.append(row)

    df_nuevas = pd.DataFrame(nuevas)
    logger.info(f"Empresas adicionales: {len(df_nuevas)} nuevas, {duplicadas} duplicadas descartadas")
    return df_nuevas, duplicadas


def _consolidar(
    df_base: pd.DataFrame,
    df_ranking: pd.DataFrame,
    df_adicionales: pd.DataFrame,
) -> pd.DataFrame:
    """Consolida las 3 fuentes en un único DataFrame."""

    # Marcar fuente de entrada
    df_base = df_base.copy()
    df_base["fuente_entrada"] = "eleconomista"
    df_base["necesita_enriquecimiento"] = False

    # Ranking recuperadas: adaptar columnas al formato base
    if len(df_ranking) > 0:
        df_ranking = df_ranking.copy()
        df_ranking["fuente_entrada"] = "eleconomista"
        df_ranking["necesita_enriquecimiento"] = True
        # Parsear ventas numéricas para el campo ventas_estimado
        ventas_parsed = df_ranking["Ventas"].apply(_parsear_ventas_texto)
        df_ranking["ventas_estimado"] = ventas_parsed.apply(lambda x: x[0])

    # Adicionales: adaptar columnas
    if len(df_adicionales) > 0:
        df_adicionales = df_adicionales.copy()
        # Renombrar 'nombre' → 'Nombre' para consistencia
        df_adicionales = df_adicionales.rename(columns={"nombre": "Nombre"})
        # Ya tienen fuente_entrada y necesita_enriquecimiento del CSV

    # Concatenar con outer join para conservar todas las columnas
    dfs = [df_base]
    if len(df_ranking) > 0:
        dfs.append(df_ranking)
    if len(df_adicionales) > 0:
        dfs.append(df_adicionales)

    df_consolidado = pd.concat(dfs, ignore_index=True, sort=False)

    # Asegurar que provincia tiene valor por defecto
    df_consolidado["provincia"] = df_consolidado["provincia"].fillna("guipúzcoa")

    return df_consolidado


def ejecutar() -> pd.DataFrame:
    """Punto de entrada del paso 1: Recuperar y consolidar."""
    logger.info("=" * 60)
    logger.info("STEP 1: Recuperar empresas y consolidar fuentes")
    logger.info("=" * 60)

    config = _cargar_config()

    # 1. Cargar base Gemini (guipúzcoa)
    df_base = _cargar_base_gemini()

    # 2. Recuperar del ranking original
    df_ranking = _recuperar_del_ranking(df_base, config)

    # 3. Cargar empresas adicionales (fuzzy dedup contra base + ranking)
    df_combinado_para_dedup = df_base.copy()
    if len(df_ranking) > 0:
        df_combinado_para_dedup = pd.concat(
            [df_combinado_para_dedup, df_ranking.rename(columns={})],
            ignore_index=True,
            sort=False,
        )
    df_adicionales, num_duplicadas = _cargar_empresas_adicionales(df_combinado_para_dedup)

    # 4. Consolidar
    df_final = _consolidar(df_base, df_ranking, df_adicionales)

    # 5. Guardar
    output_path = DATA_PROCESSED / "step1_dataset_consolidado.csv"
    guardar_csv(df_final, output_path)

    # Resumen
    n_base = len(df_base)
    n_ranking = len(df_ranking)
    n_adicionales = len(df_adicionales)
    logger.info("─" * 40)
    logger.info("RESUMEN Step 1:")
    logger.info(f"  Base Gemini (guipúzcoa):    {n_base:>5}")
    logger.info(f"  Recuperadas del ranking:    {n_ranking:>5}")
    logger.info(f"  Adicionales investigación:  {n_adicionales:>5}")
    logger.info(f"  Duplicadas descartadas:     {num_duplicadas:>5}")
    logger.info(f"  TOTAL CONSOLIDADO:          {len(df_final):>5}")
    logger.info(f"  Necesitan enriquecimiento:  {df_final['necesita_enriquecimiento'].sum():>5}")
    logger.info(f"  Guardado en: {output_path}")

    return df_final
