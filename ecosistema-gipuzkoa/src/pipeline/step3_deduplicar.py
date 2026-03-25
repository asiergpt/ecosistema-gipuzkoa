"""
Pipeline: Step 3 — Detectar y marcar grupos empresariales.

No borra filas: mantiene cada entidad jurídica separada pero marca
grupo_empresarial y rol_en_grupo.
"""

from pathlib import Path

import pandas as pd
import yaml
from loguru import logger

from src.utils.cleaning import normalizar_texto
from src.utils.io import guardar_csv, leer_csv

DATA_PROCESSED = Path("data/processed")
CONFIG = Path("config/settings.yaml")
INPUT_FILE = DATA_PROCESSED / "step2_con_sectores.csv"
OUTPUT_FILE = DATA_PROCESSED / "step3_con_grupos.csv"


def _cargar_grupos_conocidos() -> list[dict]:
    """Carga la lista de grupos conocidos de settings.yaml."""
    with open(CONFIG, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config["pipeline"]["grupos_conocidos"]


def _detectar_por_nombre(nombre: str, grupos: list[dict]) -> dict | None:
    """Detecta si el nombre de una empresa pertenece a un grupo conocido."""
    nombre_norm = normalizar_texto(str(nombre))
    for grupo in grupos:
        raiz = normalizar_texto(grupo["raiz"])
        if raiz in nombre_norm:
            return grupo
    return None


def _detectar_por_accionistas(accionistas: str, grupos: list[dict]) -> dict | None:
    """Detecta grupo analizando el campo propiedad_accionistas."""
    if pd.isna(accionistas) or not str(accionistas).strip():
        return None

    accionistas_norm = normalizar_texto(str(accionistas))
    for grupo in grupos:
        raiz = normalizar_texto(grupo["raiz"])
        if raiz in accionistas_norm:
            return grupo
    return None


def _determinar_rol(
    nombre_norm: str,
    raiz_grupo: str,
    nif: str | None,
    nif_matriz: str | None,
) -> str:
    """Determina el rol de la entidad en el grupo."""
    # Si tiene NIF de matriz configurado
    if nif_matriz and nif and str(nif).strip().upper() == nif_matriz.upper():
        return "matriz"

    # Si el nombre empieza por la raíz (probable matriz o entidad principal)
    nombre_limpio = nombre_norm.strip()
    if nombre_limpio.startswith(raiz_grupo) and len(nombre_limpio) < len(raiz_grupo) + 15:
        return "matriz"

    # Si el NIF empieza por F → cooperativa del grupo
    if nif and str(nif).strip().upper().startswith("F"):
        return "cooperativa_del_grupo"

    return "filial"


def ejecutar() -> pd.DataFrame:
    """Punto de entrada del paso 3: Detectar grupos empresariales."""
    logger.info("=" * 60)
    logger.info("STEP 3: Detectar y marcar grupos empresariales")
    logger.info("=" * 60)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"No se encontró {INPUT_FILE}. Ejecuta primero step2_mapping."
        )

    df = leer_csv(INPUT_FILE)
    grupos = _cargar_grupos_conocidos()

    # Inicializar columnas
    df["grupo_empresarial"] = None
    df["rol_en_grupo"] = "independiente"

    # Detectar columnas relevantes
    col_nombre = "Nombre"
    col_nif = "NIF" if "NIF" in df.columns else None
    col_accionistas = "propiedad_accionistas" if "propiedad_accionistas" in df.columns else None

    grupos_detectados: dict[str, list[str]] = {}

    for idx, row in df.iterrows():
        nombre = str(row[col_nombre])

        # Detectar por nombre
        grupo = _detectar_por_nombre(nombre, grupos)

        # Si no se detectó por nombre, intentar por accionistas
        if grupo is None and col_accionistas:
            grupo = _detectar_por_accionistas(row.get(col_accionistas), grupos)

        if grupo is None:
            continue

        nombre_grupo = grupo["nombre_grupo"]
        raiz = normalizar_texto(grupo["raiz"])
        nif = str(row[col_nif]).strip().upper() if col_nif and pd.notna(row.get(col_nif)) else None
        nif_matriz = grupo.get("nif_matriz")

        rol = _determinar_rol(normalizar_texto(nombre), raiz, nif, nif_matriz)

        df.at[idx, "grupo_empresarial"] = nombre_grupo
        df.at[idx, "rol_en_grupo"] = rol

        # Tracking para resumen
        if nombre_grupo not in grupos_detectados:
            grupos_detectados[nombre_grupo] = []
        grupos_detectados[nombre_grupo].append(f"{nombre} [{rol}]")

    # Guardar
    guardar_csv(df, OUTPUT_FILE)

    # Resumen
    n_en_grupo = (df["grupo_empresarial"].notna()).sum()
    logger.info("─" * 40)
    logger.info("RESUMEN Step 3:")
    logger.info(f"  Total empresas:         {len(df):>5}")
    logger.info(f"  En algún grupo:         {n_en_grupo:>5}")
    logger.info(f"  Independientes:         {len(df) - n_en_grupo:>5}")
    logger.info(f"  Grupos detectados:      {len(grupos_detectados):>5}")
    logger.info("")
    for nombre_grupo, miembros in sorted(grupos_detectados.items()):
        logger.info(f"  {nombre_grupo} ({len(miembros)} entidades):")
        for m in miembros:
            logger.info(f"    - {m}")
    logger.info(f"  Guardado en: {OUTPUT_FILE}")

    return df
