"""Pipeline: step5_taxonomia — Clasificación en 3 dimensiones.

Dimensión 1 (Cotización): Determinista, sin IA.
Dimensión 2 (Propiedad): Sonnet batch de 15.
Dimensión 3 (Rol ecosistema): Sonnet batch de 15.

Orden obligatorio: Dim 1 → Dim 2 → Dim 3.
"""

from pathlib import Path

import pandas as pd
from loguru import logger

from src.utils.io import guardar_csv, leer_csv, leer_excel

DATA_PROCESSED = Path("data/processed")
DATA_RAW = Path("data/raw")
DATA_OUTPUT = Path("data/output")
INPUT_FILE = DATA_PROCESSED / "step4_enriquecido.csv"
OUTPUT_FILE = DATA_PROCESSED / "step5_con_taxonomia.csv"

# ═══════════════════════════════════════════════════════════════
# DIMENSIÓN 1: COTIZACIÓN (determinista)
# ═══════════════════════════════════════════════════════════════

COTIZADAS_POR_NIF = {
    "A20001020": ("CAF", "Mercado Continuo"),
}

COTIZADAS_POR_NOMBRE = {
    "CIE AUTOMOTIVE": "IBEX 35",
    "CAF": "Mercado Continuo",
    "VIDRALA": "Mercado Continuo",
    "TUBACEX": "Mercado Continuo",
    "IBERPAPEL": "Mercado Continuo",
}


def clasificar_cotizacion(row: dict) -> str:
    """Dimensión 1: mercado de cotización. Puro lookup."""
    nif = str(row.get("NIF", "")).strip()
    nombre = str(row.get("Nombre") or row.get("nombre", "")).upper()

    if nif in COTIZADAS_POR_NIF:
        return COTIZADAS_POR_NIF[nif][1]

    for clave, mercado in COTIZADAS_POR_NOMBRE.items():
        if clave in nombre:
            return mercado

    return "No cotiza"


# ═══════════════════════════════════════════════════════════════
# CAMPEONAS OCULTAS: cruce con Orkestra
# ═══════════════════════════════════════════════════════════════


def _cargar_campeonas_orkestra() -> set[str]:
    """Carga lista de campeonas ocultas confirmadas por Orkestra."""
    campeonas = set()
    xlsx = DATA_RAW / "campeonas_ocultas_euskadi.xlsx"
    if xlsx.exists():
        df = leer_excel(xlsx)
        # Buscar columna con nombre de empresa
        for col in df.columns:
            if "nombre" in col.lower() or "empresa" in col.lower():
                campeonas = {str(v).strip().upper() for v in df[col].dropna()}
                break
        if not campeonas and len(df.columns) > 0:
            # Usar primera columna por defecto
            campeonas = {str(v).strip().upper() for v in df.iloc[:, 0].dropna()}
        logger.info(f"Campeonas Orkestra cargadas: {len(campeonas)}")
    else:
        logger.warning(f"No se encontró {xlsx}")
    return campeonas


def marcar_campeonas_orkestra(df: pd.DataFrame):
    """Marca empresas confirmadas como campeonas ocultas por Orkestra."""
    campeonas = _cargar_campeonas_orkestra()
    if not campeonas:
        return

    if "es_campeona_oculta" not in df.columns:
        df["es_campeona_oculta"] = False

    count = 0
    for idx, row in df.iterrows():
        nombre = str(row.get("Nombre", "")).upper()
        for campeona in campeonas:
            if campeona in nombre or nombre in campeona:
                df.at[idx, "es_campeona_oculta"] = True
                count += 1
                break

    logger.info(f"Campeonas ocultas Orkestra marcadas: {count}")


# ═══════════════════════════════════════════════════════════════
# EXPORTAR REVISIÓN
# ═══════════════════════════════════════════════════════════════


def exportar_revision(df: pd.DataFrame):
    """Exporta empresas con confianza baja para revisión manual."""
    DATA_OUTPUT.mkdir(parents=True, exist_ok=True)

    mask_baja = (
        (df.get("taxonomia_confianza") == "baja") |
        (df.get("rol_ecosistema_confianza") == "baja")
    )

    if mask_baja.any():
        cols = [
            "Nombre", "NIF", "sector_amigable", "ventas_estimado", "ventas_reales",
            "empleados_numero", "propiedad_accionistas", "inversores_capital_privado",
            "mercado_cotizacion", "tipologia_propiedad", "taxonomia_confianza",
            "taxonomia_razonamiento", "rol_ecosistema", "rol_ecosistema_confianza",
            "rol_ecosistema_razonamiento",
        ]
        cols_exist = [c for c in cols if c in df.columns]
        df_revision = df[mask_baja][cols_exist].copy()

        out_path = DATA_OUTPUT / "revision_taxonomia.xlsx"
        df_revision.to_excel(out_path, index=False)
        logger.info(f"Exportadas {len(df_revision)} empresas para revisión → {out_path}")
    else:
        logger.info("No hay empresas con confianza baja para revisar")


# ═══════════════════════════════════════════════════════════════
# EJECUCIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════════


def ejecutar(
    dimension: int | None = None,
    max_empresas: int | None = None,
):
    """Punto de entrada del Step 5.

    Args:
        dimension: 1, 2, 3 o None para todas (1→2→3).
        max_empresas: límite para testing.
    """
    logger.info("=" * 60)
    logger.info("STEP 5: CLASIFICACIÓN TAXONÓMICA (3 dimensiones)")
    logger.info("=" * 60)

    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"No se encontró {INPUT_FILE}. Ejecuta primero enrich.")

    df = leer_csv(INPUT_FILE)

    # Asegurar columnas con dtype object
    for col in ["mercado_cotizacion", "tipologia_propiedad", "taxonomia_confianza",
                "taxonomia_razonamiento", "rol_ecosistema", "rol_ecosistema_confianza",
                "rol_ecosistema_razonamiento"]:
        if col not in df.columns:
            df[col] = pd.Series(dtype="object")
        df[col] = df[col].astype(object)
    if "es_campeona_oculta" not in df.columns:
        df["es_campeona_oculta"] = False

    dims = [dimension] if dimension else [1, 2, 3]

    # ─── Dimensión 1: Cotización (siempre, es instantánea) ───
    if 1 in dims or dimension is None:
        logger.info("\n─── Dimensión 1: Mercado de cotización (determinista) ───")
        for idx, row in df.iterrows():
            df.at[idx, "mercado_cotizacion"] = clasificar_cotizacion(row.to_dict())

        counts = df["mercado_cotizacion"].value_counts()
        for mercado, count in counts.items():
            logger.info(f"  {mercado}: {count}")

    # ─── Marcar campeonas Orkestra (para que Dim 3 lo use) ───
    if 3 in dims:
        marcar_campeonas_orkestra(df)

    # ─── Dimensiones 2 y 3: Sonnet ───
    sonnet_dims = [d for d in dims if d in (2, 3)]
    if sonnet_dims:
        # Guardar estado parcial con Dim 1 para que Sonnet lo lea
        guardar_csv(df, INPUT_FILE)

        from src.enrichment.sonnet_client import ejecutar as sonnet_ejecutar

        for dim in sonnet_dims:
            df = sonnet_ejecutar(
                dimension=dim,
                max_empresas=max_empresas,
            )
            # Guardar entre dimensiones para que la siguiente lea los resultados
            guardar_csv(df, INPUT_FILE)

    # ─── Exportar revisión ───
    exportar_revision(df)

    # ─── Guardar resultado final ───
    guardar_csv(df, OUTPUT_FILE)

    # ─── Resumen ───
    logger.info("\n" + "─" * 40)
    logger.info("RESUMEN Step 5:")
    logger.info(f"  Total empresas: {len(df)}")

    if "mercado_cotizacion" in df.columns:
        cotiza = (df["mercado_cotizacion"] != "No cotiza").sum()
        logger.info(f"  Cotizadas: {cotiza}")

    if "tipologia_propiedad" in df.columns:
        clasificadas_d2 = df["tipologia_propiedad"].notna().sum()
        logger.info(f"  Dim 2 clasificadas: {clasificadas_d2}")

    if "rol_ecosistema" in df.columns:
        clasificadas_d3 = df["rol_ecosistema"].notna().sum()
        logger.info(f"  Dim 3 clasificadas: {clasificadas_d3}")

    logger.info(f"  Guardado en: {OUTPUT_FILE}")

    return df
