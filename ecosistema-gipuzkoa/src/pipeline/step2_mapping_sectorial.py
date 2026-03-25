"""
Pipeline: Step 2 — Mapping sectorial CNAE → Sector Amigable.

Cruza los códigos CNAE con mapping_sectorial_cnae.xlsx para asignar
uno de 45 sectores amigables a cada empresa. Match a 3 dígitos tiene
prioridad sobre match a 2 dígitos.
"""

from pathlib import Path

import pandas as pd
from loguru import logger

from src.utils.io import guardar_csv, leer_csv, leer_excel

DATA_RAW = Path("data/raw")
DATA_PROCESSED = Path("data/processed")
INPUT_FILE = DATA_PROCESSED / "step1_dataset_consolidado.csv"
OUTPUT_FILE = DATA_PROCESSED / "step2_con_sectores.csv"
MAPPING_FILE = DATA_RAW / "mapping_sectorial_cnae.xlsx"


def _cargar_mapping() -> tuple[dict[str, str], dict[str, str]]:
    """Carga el mapping CNAE → Sector Amigable.

    Retorna (mapping_3dig, mapping_2dig).
    """
    df = leer_excel(MAPPING_FILE)

    mapping_3dig: dict[str, str] = {}
    mapping_2dig: dict[str, str] = {}

    for _, row in df.iterrows():
        sector = str(row["Sector Amigable"]).strip()

        # Mapping a 3 dígitos
        cnae3 = row.get("CNAE 3 dig.")
        if pd.notna(cnae3):
            key = str(int(cnae3)).zfill(3)
            mapping_3dig[key] = sector

        # Mapping a 2 dígitos
        cnae2 = row.get("CNAE 2 dig.")
        if pd.notna(cnae2):
            key = str(int(cnae2)).zfill(2)
            mapping_2dig[key] = sector

    logger.info(f"Mapping cargado: {len(mapping_3dig)} CNAEs a 3 dígitos, {len(mapping_2dig)} a 2 dígitos")
    return mapping_3dig, mapping_2dig


def _extraer_cnae_digitos(cnae_raw: str) -> tuple[str | None, str | None]:
    """Extrae los primeros 2 y 3 dígitos de un código CNAE.

    Retorna (cnae_3dig, cnae_2dig).
    """
    if pd.isna(cnae_raw):
        return None, None

    cnae = str(cnae_raw).strip()

    # Limpiar: quedarnos solo con dígitos
    digitos = "".join(c for c in cnae if c.isdigit())
    if len(digitos) < 2:
        return None, None

    cnae_2 = digitos[:2].zfill(2)
    cnae_3 = digitos[:3].zfill(3) if len(digitos) >= 3 else None

    return cnae_3, cnae_2


def asignar_sector(cnae_raw, sector_investigacion, mapping_3dig, mapping_2dig) -> str:
    """Asigna sector amigable a una empresa según su CNAE.

    Prioridad: CNAE 3 dígitos > CNAE 2 dígitos > sector_investigacion > 'Sin clasificar'.
    """
    cnae_3, cnae_2 = _extraer_cnae_digitos(cnae_raw)

    # Intentar match a 3 dígitos
    if cnae_3 and cnae_3 in mapping_3dig:
        return mapping_3dig[cnae_3]

    # Intentar match a 2 dígitos
    if cnae_2 and cnae_2 in mapping_2dig:
        return mapping_2dig[cnae_2]

    # Usar sector de investigación como fallback
    if pd.notna(sector_investigacion) and str(sector_investigacion).strip():
        return str(sector_investigacion).strip()

    return "Sin clasificar"


def ejecutar() -> pd.DataFrame:
    """Punto de entrada del paso 2: Mapping sectorial."""
    logger.info("=" * 60)
    logger.info("STEP 2: Mapping sectorial CNAE → Sector Amigable")
    logger.info("=" * 60)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"No se encontró {INPUT_FILE}. Ejecuta primero step1_recuperar."
        )

    # Cargar datos
    df = leer_csv(INPUT_FILE)
    mapping_3dig, mapping_2dig = _cargar_mapping()

    # Determinar columna CNAE (puede venir como CNAE_Original o cnae_original)
    col_cnae = None
    for candidato in ["CNAE_Original", "cnae_original"]:
        if candidato in df.columns:
            col_cnae = candidato
            break

    # Columna sector_investigacion (solo para empresas adicionales)
    col_sector_inv = "sector_investigacion" if "sector_investigacion" in df.columns else None

    # Asignar sector amigable
    df["sector_amigable"] = df.apply(
        lambda row: asignar_sector(
            row.get(col_cnae) if col_cnae else None,
            row.get(col_sector_inv) if col_sector_inv else None,
            mapping_3dig,
            mapping_2dig,
        ),
        axis=1,
    )

    # Guardar
    guardar_csv(df, OUTPUT_FILE)

    # Estadísticas
    distribucion = df["sector_amigable"].value_counts()
    sin_clasificar = (df["sector_amigable"] == "Sin clasificar").sum()

    logger.info("─" * 40)
    logger.info("RESUMEN Step 2:")
    logger.info(f"  Total empresas:       {len(df):>5}")
    logger.info(f"  Con sector asignado:  {len(df) - sin_clasificar:>5}")
    logger.info(f"  Sin clasificar:       {sin_clasificar:>5}")
    logger.info(f"  Sectores únicos:      {df['sector_amigable'].nunique():>5}")
    logger.info("")
    logger.info("  Top 10 sectores:")
    for sector, count in distribucion.head(10).items():
        logger.info(f"    {count:>4}  {sector}")
    logger.info(f"  Guardado en: {OUTPUT_FILE}")

    return df
