"""Funciones de lectura/escritura de archivos."""

import pandas as pd
from pathlib import Path
from loguru import logger

DEFAULT_SEP = ";"
DEFAULT_ENCODING = "utf-8-sig"


def leer_csv(ruta: str | Path, **kwargs) -> pd.DataFrame:
    """Lee CSV con configuración estándar del proyecto."""
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró: {ruta}")

    defaults = {"sep": DEFAULT_SEP, "encoding": DEFAULT_ENCODING}
    defaults.update(kwargs)

    df = pd.read_csv(ruta, **defaults)
    logger.info(f"Leído {ruta.name}: {len(df)} filas, {len(df.columns)} columnas")
    return df


def guardar_csv(df: pd.DataFrame, ruta: str | Path, **kwargs) -> None:
    """Guarda CSV con configuración estándar del proyecto."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)

    defaults = {"sep": DEFAULT_SEP, "encoding": DEFAULT_ENCODING, "index": False}
    defaults.update(kwargs)

    df.to_csv(ruta, **defaults)
    logger.info(f"Guardado {ruta.name}: {len(df)} filas")


def leer_excel(ruta: str | Path, **kwargs) -> pd.DataFrame:
    """Lee Excel."""
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró: {ruta}")

    df = pd.read_excel(ruta, **kwargs)
    logger.info(f"Leído {ruta.name}: {len(df)} filas, {len(df.columns)} columnas")
    return df
