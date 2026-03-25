"""
Pipeline: Step 4 — Validar datos y detectar inconsistencias.

- Detecta ventas placeholder (50M/25M/1.9M exactos)
- Parsea numero_empleados (string → int)
- Cruza con empresas_adicionales_investigacion.csv para enriquecer
- Detecta anomalías
- Genera informe de calidad JSON
"""

import json
from pathlib import Path

import pandas as pd
import yaml
from loguru import logger

from src.utils.cleaning import normalizar_texto, parsear_empleados
from src.utils.io import guardar_csv, leer_csv

DATA_RAW = Path("data/raw")
DATA_PROCESSED = Path("data/processed")
CONFIG = Path("config/settings.yaml")
INPUT_FILE = DATA_PROCESSED / "step3_con_grupos.csv"
OUTPUT_FILE = DATA_PROCESSED / "step4_validado.csv"
INFORME_FILE = DATA_PROCESSED / "informe_calidad.json"


def _cargar_placeholders() -> list[float]:
    """Carga valores placeholder de ventas desde config."""
    with open(CONFIG, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return [float(v) for v in config["pipeline"]["placeholders_ventas"]]


def _clasificar_ventas(df: pd.DataFrame, placeholders: list[float]) -> pd.DataFrame:
    """Clasifica la confianza de las ventas."""
    df = df.copy()

    col_ventas = "ventas_estimado" if "ventas_estimado" in df.columns else None
    if col_ventas is None:
        df["ventas_confianza"] = "baja"
        return df

    df["ventas_confianza"] = "baja"  # Default

    for idx, row in df.iterrows():
        valor = row.get(col_ventas)
        if pd.isna(valor):
            continue

        try:
            valor_num = float(valor)
        except (ValueError, TypeError):
            continue

        if valor_num in placeholders:
            df.at[idx, "ventas_confianza"] = "baja"
        elif valor_num > 0:
            df.at[idx, "ventas_confianza"] = "alta"

    return df


def _parsear_campo_empleados(df: pd.DataFrame) -> pd.DataFrame:
    """Parsea el campo numero_empleados (texto) a empleados_numero (int) + empleados_fuente."""
    df = df.copy()
    df["empleados_numero"] = None
    df["empleados_fuente"] = None

    col_empleados = "numero_empleados" if "numero_empleados" in df.columns else None
    if col_empleados is None:
        return df

    for idx, row in df.iterrows():
        texto = row.get(col_empleados)
        if pd.isna(texto):
            continue

        numero, fuente = parsear_empleados(str(texto))
        if numero is not None:
            df.at[idx, "empleados_numero"] = numero
        if fuente is not None:
            df.at[idx, "empleados_fuente"] = fuente

    # Convertir a Int64 (nullable integer)
    df["empleados_numero"] = pd.to_numeric(df["empleados_numero"], errors="coerce").astype("Int64")

    return df


def _cruzar_con_investigacion(df: pd.DataFrame) -> pd.DataFrame:
    """Enriquece datos cruzando con empresas_adicionales_investigacion.csv."""
    ruta_adicionales = DATA_RAW / "empresas_adicionales_investigacion.csv"
    if not ruta_adicionales.exists():
        logger.warning("No se encontró empresas_adicionales_investigacion.csv, saltando cruce")
        return df

    df_ref = leer_csv(ruta_adicionales)
    df = df.copy()

    # Crear lookup por nombre normalizado
    ref_lookup: dict[str, dict] = {}
    for _, row in df_ref.iterrows():
        nombre_norm = normalizar_texto(str(row["nombre"]))
        ref_lookup[nombre_norm] = {
            "ventas_ref": row.get("ventas_ref"),
            "empleados_ref": row.get("empleados_ref"),
        }

    actualizados = 0
    for idx, row in df.iterrows():
        nombre_norm = normalizar_texto(str(row["Nombre"]))
        ref = ref_lookup.get(nombre_norm)
        if ref is None:
            continue

        # Ventas de referencia
        if pd.notna(ref.get("ventas_ref")) and float(ref["ventas_ref"]) > 0:
            ventas_ref = float(ref["ventas_ref"])
            # Solo usar si no tiene ventas reales o las actuales son placeholder
            if df.at[idx, "ventas_confianza"] == "baja" or pd.isna(row.get("ventas_estimado")):
                df.at[idx, "ventas_estimado"] = ventas_ref
                df.at[idx, "ventas_confianza"] = "media"

        # Empleados de referencia
        if pd.notna(ref.get("empleados_ref")) and float(ref["empleados_ref"]) > 0:
            empl_ref = int(float(ref["empleados_ref"]))
            if pd.isna(row.get("empleados_numero")) or row.get("empleados_numero") == 0:
                df.at[idx, "empleados_numero"] = empl_ref
                df.at[idx, "empleados_fuente"] = "investigacion_adicional"

        actualizados += 1

    logger.info(f"Cruce con investigación: {actualizados} empresas encontradas en referencia")
    return df


def _detectar_anomalias(df: pd.DataFrame) -> list[dict]:
    """Detecta anomalías en los datos."""
    anomalias = []

    for idx, row in df.iterrows():
        nombre = str(row.get("Nombre", f"fila_{idx}"))
        empleados = row.get("empleados_numero")
        ventas = row.get("ventas_estimado")
        sector = str(row.get("SECTOR_NOMBRE", "")).lower()
        patentes = row.get("patentes", 0)

        # Empleados >5000 sin ventas altas
        if pd.notna(empleados) and int(empleados) > 5000:
            if pd.isna(ventas) or (pd.notna(ventas) and float(ventas) < 50_000_000):
                anomalias.append({
                    "empresa": nombre,
                    "tipo": "empleados_sin_ventas",
                    "detalle": f"Empleados={empleados} pero ventas={ventas}",
                })

        # Patentes >20 en empresa de servicios
        if pd.notna(patentes) and int(patentes) > 20:
            servicios_keywords = ["servicio", "consultor", "asesor", "limpiez", "seguridad"]
            if any(kw in sector for kw in servicios_keywords):
                anomalias.append({
                    "empresa": nombre,
                    "tipo": "patentes_en_servicios",
                    "detalle": f"Patentes={patentes} en sector '{sector}'",
                })

        # Ventas muy altas (>1B) → verificar que no sea error
        if pd.notna(ventas) and float(ventas) > 1_000_000_000:
            anomalias.append({
                "empresa": nombre,
                "tipo": "ventas_muy_altas",
                "detalle": f"Ventas={float(ventas):,.0f}€ — verificar",
            })

    return anomalias


def _generar_informe(df: pd.DataFrame, anomalias: list[dict]) -> dict:
    """Genera el informe de calidad."""
    total = len(df)

    ventas_reales = (df["ventas_confianza"] == "alta").sum() if "ventas_confianza" in df.columns else 0
    ventas_media = (df["ventas_confianza"] == "media").sum() if "ventas_confianza" in df.columns else 0
    ventas_baja = (df["ventas_confianza"] == "baja").sum() if "ventas_confianza" in df.columns else 0

    con_empleados = df["empleados_numero"].notna().sum() if "empleados_numero" in df.columns else 0

    necesitan_enriq = df["necesita_enriquecimiento"].sum() if "necesita_enriquecimiento" in df.columns else 0

    informe = {
        "total_empresas": total,
        "ventas": {
            "confianza_alta": int(ventas_reales),
            "confianza_media": int(ventas_media),
            "confianza_baja": int(ventas_baja),
            "pct_con_ventas_reales": round((ventas_reales + ventas_media) / total * 100, 1) if total > 0 else 0,
        },
        "empleados": {
            "con_dato": int(con_empleados),
            "sin_dato": int(total - con_empleados),
            "pct_con_empleados": round(con_empleados / total * 100, 1) if total > 0 else 0,
        },
        "enriquecimiento": {
            "necesitan_enriquecimiento": int(necesitan_enriq),
            "pct_necesitan": round(necesitan_enriq / total * 100, 1) if total > 0 else 0,
        },
        "anomalias": {
            "total": len(anomalias),
            "por_tipo": {},
            "detalle": anomalias[:50],
        },
    }

    for a in anomalias:
        tipo = a["tipo"]
        informe["anomalias"]["por_tipo"][tipo] = informe["anomalias"]["por_tipo"].get(tipo, 0) + 1

    return informe


def ejecutar() -> pd.DataFrame:
    """Punto de entrada del paso 4: Validar datos."""
    logger.info("=" * 60)
    logger.info("STEP 4: Validar datos y detectar inconsistencias")
    logger.info("=" * 60)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"No se encontró {INPUT_FILE}. Ejecuta primero step3_grupos."
        )

    df = leer_csv(INPUT_FILE)
    placeholders = _cargar_placeholders()

    # 1. Clasificar confianza de ventas
    df = _clasificar_ventas(df, placeholders)
    logger.info(f"Ventas clasificadas: {(df['ventas_confianza'] == 'alta').sum()} alta, "
                f"{(df['ventas_confianza'] == 'baja').sum()} baja")

    # 2. Parsear empleados
    df = _parsear_campo_empleados(df)
    logger.info(f"Empleados parseados: {df['empleados_numero'].notna().sum()} con dato")

    # 3. Cruzar con investigación
    df = _cruzar_con_investigacion(df)

    # 4. Detectar anomalías
    anomalias = _detectar_anomalias(df)
    logger.info(f"Anomalías detectadas: {len(anomalias)}")

    # 5. Generar informe
    informe = _generar_informe(df, anomalias)
    INFORME_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(INFORME_FILE, "w", encoding="utf-8") as f:
        json.dump(informe, f, ensure_ascii=False, indent=2)
    logger.info(f"Informe de calidad guardado en: {INFORME_FILE}")

    # 6. Guardar dataset validado
    guardar_csv(df, OUTPUT_FILE)

    # Resumen
    logger.info("─" * 40)
    logger.info("RESUMEN Step 4:")
    logger.info(f"  Total empresas:             {informe['total_empresas']:>5}")
    logger.info(f"  Ventas confianza alta:      {informe['ventas']['confianza_alta']:>5} "
                f"({informe['ventas']['pct_con_ventas_reales']:.1f}% reales)")
    logger.info(f"  Ventas confianza baja:      {informe['ventas']['confianza_baja']:>5}")
    logger.info(f"  Con dato de empleados:      {informe['empleados']['con_dato']:>5} "
                f"({informe['empleados']['pct_con_empleados']:.1f}%)")
    logger.info(f"  Necesitan enriquecimiento:  {informe['enriquecimiento']['necesitan_enriquecimiento']:>5}")
    logger.info(f"  Anomalías detectadas:       {informe['anomalias']['total']:>5}")
    for tipo, count in informe["anomalias"]["por_tipo"].items():
        logger.info(f"    - {tipo}: {count}")
    logger.info(f"  Guardado en: {OUTPUT_FILE}")

    return df
