"""Reintento async de empresas que fallaron en el enriquecimiento."""

import asyncio
import pandas as pd
from loguru import logger
from src.enrichment.haiku_client import (
    CAMPOS_HAIKU, BATCH_SIZE, ASYNC_CONCURRENCY,
    load_async_client, async_enrich_empresa, merge_enrichment,
    _count_non_null_fields, _preparar_columnas,
)
from src.utils.io import leer_csv, guardar_csv
from pathlib import Path

INPUT_FILE = Path("data/processed/step4_enriquecido.csv")
OUTPUT_FILE = INPUT_FILE  # sobreescribe

# Campos exclusivos de Haiku (no vienen de Gemini)
HAIKU_EXCLUSIVE = [
    "pct_exportacion", "inversion_id", "mercado_b2b_b2c",
    "posicion_mercado", "producto_propio", "usa_ia", "ia_detalle",
    "stack_nivel", "stack_detalle", "equipo_tech_estimacion",
    "roles_tech_detectados",
]


async def main():
    df = leer_csv(INPUT_FILE)
    _preparar_columnas(df)

    # Identificar filas sin datos Haiku
    mask = df[HAIKU_EXCLUSIVE].isna().all(axis=1)
    failed_indices = df[mask].index.tolist()
    logger.info(f"Empresas a reintentar: {len(failed_indices)}")

    if not failed_indices:
        logger.info("No hay empresas pendientes")
        return

    client = load_async_client()
    sem = asyncio.Semaphore(ASYNC_CONCURRENCY)

    total_ok = 0
    total_error = 0
    total_campos = 0

    # Preparar lista de (idx, row_dict)
    pendientes = [(idx, df.loc[idx].to_dict()) for idx in failed_indices]

    total_batches = (len(pendientes) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_start in range(0, len(pendientes), BATCH_SIZE):
        batch = pendientes[batch_start:batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        logger.info(f"Batch {batch_num}/{total_batches} ({len(batch)} empresas)")

        async def _single(idx, row):
            nombre = row.get("Nombre", f"idx_{idx}")
            result = await async_enrich_empresa(client, row, sem)
            return (idx, nombre, result)

        tasks = [_single(idx, row) for idx, row in batch]
        results = await asyncio.gather(*tasks)

        for idx, nombre, enriched in results:
            if enriched is not None:
                campos_ok = _count_non_null_fields(enriched)
                total_campos += campos_ok
                logger.info(f"  {nombre}: OK ({campos_ok}/{len(CAMPOS_HAIKU)} campos)")
                df.loc[idx] = merge_enrichment(df.loc[idx], enriched)
                total_ok += 1
            else:
                logger.warning(f"  {nombre}: ERROR")
                total_error += 1

    await client.close()

    guardar_csv(df, OUTPUT_FILE)

    logger.info("─" * 40)
    logger.info("RESUMEN Reintento:")
    logger.info(f"  Total reintentadas:   {len(failed_indices):>5}")
    logger.info(f"  Exitosas:             {total_ok:>5}")
    logger.info(f"  Con error:            {total_error:>5}")
    logger.info(f"  Campos obtenidos:     {total_campos:>5}")
    if total_ok > 0:
        logger.info(f"  Media campos/empresa: {total_campos / total_ok:.1f}")


if __name__ == "__main__":
    asyncio.run(main())
