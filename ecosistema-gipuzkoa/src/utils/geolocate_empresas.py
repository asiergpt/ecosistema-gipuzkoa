"""
Geolocaliza empresas sin municipio o con municipio fuera de Gipuzkoa
usando Claude Haiku 4.5 con web search.

Usage: python src/utils/geolocate_empresas.py
"""

import asyncio
import csv
import json
import re
import shutil
import time
from collections import Counter
from pathlib import Path

import anthropic

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CSV_PATH = PROJECT_ROOT / "data" / "processed" / "step5_con_taxonomia_v2.csv"
OUTPUT_CSV = PROJECT_ROOT / "data" / "processed" / "step5_con_taxonomia_v2.csv"
FRONTEND_CSV = PROJECT_ROOT / "frontend" / "public" / "data.csv"
ENV_PATH = PROJECT_ROOT / "config" / ".env"
MODEL = "claude-haiku-4-5-20251001"
MAX_COST = 25.0  # USD
COST_PER_SEARCH = 0.01
COST_PER_INPUT_TOKEN = 0.80 / 1_000_000
COST_PER_OUTPUT_TOKEN = 4.00 / 1_000_000
CONCURRENCY = 10
BATCH_LOG_SIZE = 50

# Comarca mapping for newly found municipalities
COMARCA_MAP = {
    # Donostialdea
    "Donostia-San Sebastián": "Donostialdea", "Donostia": "Donostialdea",
    "Hernani": "Donostialdea", "Astigarraga": "Donostialdea",
    "Andoain": "Donostialdea", "Lasarte-Oria": "Donostialdea",
    "Usurbil": "Donostialdea", "Urnieta": "Donostialdea",
    "Villabona": "Donostialdea", "Aduna": "Donostialdea",
    "Orio": "Donostialdea", "Asteasu": "Donostialdea",
    "Zizurkil": "Donostialdea",
    # Bidasoa
    "Irun": "Bidasoa", "Hondarribia": "Bidasoa",
    "Oiartzun": "Bidasoa", "Lezo": "Bidasoa",
    "Pasaia": "Bidasoa", "Errenteria": "Bidasoa",
    # Tolosaldea
    "Tolosa": "Tolosaldea", "Ibarra": "Tolosaldea",
    "Anoeta": "Tolosaldea", "Alkiza": "Tolosaldea",
    "Belauntza": "Tolosaldea", "Legorreta": "Tolosaldea",
    "Alegia": "Tolosaldea", "Irura": "Tolosaldea",
    "Amezketa": "Tolosaldea", "Baliarrain": "Tolosaldea",
    "Lizartza": "Tolosaldea", "Altzo": "Tolosaldea",
    "Albiztur": "Tolosaldea", "Bidegoian": "Tolosaldea",
    "Hernialde": "Tolosaldea", "Gaztelu": "Tolosaldea",
    "Elduain": "Tolosaldea", "Berrobi": "Tolosaldea",
    "Berastegi": "Tolosaldea", "Ikaztegieta": "Tolosaldea",
    # Goierri
    "Beasain": "Goierri", "Ordizia": "Goierri",
    "Lazkao": "Goierri", "Zumarraga": "Goierri",
    "Legazpi": "Goierri", "Urretxu": "Goierri",
    "Segura": "Goierri", "Idiazabal": "Goierri",
    "Zegama": "Goierri", "Zerain": "Goierri",
    "Ataun": "Goierri", "Gabiria": "Goierri",
    "Mutiloa": "Goierri", "Olaberria": "Goierri",
    "Ormaiztegi": "Goierri", "Ezkio-Itsaso": "Goierri",
    # Alto Deba
    "Arrasate/Mondragón": "Alto Deba", "Arrasate": "Alto Deba",
    "Mondragón": "Alto Deba", "Bergara": "Alto Deba",
    "Oñati": "Alto Deba", "Eskoriatza": "Alto Deba",
    "Aretxabaleta": "Alto Deba", "Antzuola": "Alto Deba",
    "Leintz-Gatzaga": "Alto Deba",
    # Bajo Deba
    "Eibar": "Bajo Deba", "Elgoibar": "Bajo Deba",
    "Deba": "Bajo Deba", "Mutriku": "Bajo Deba",
    "Soraluze": "Bajo Deba", "Mendaro": "Bajo Deba",
    "Ermua": "Bajo Deba", "Mallabia": "Bajo Deba",
    "Elgeta": "Bajo Deba",
    # Urola-Costa
    "Azpeitia": "Urola-Costa", "Azkoitia": "Urola-Costa",
    "Zarautz": "Urola-Costa", "Zumaia": "Urola-Costa",
    "Getaria": "Urola-Costa", "Zestoa": "Urola-Costa",
    "Aizarnazabal": "Urola-Costa", "Aia": "Urola-Costa",
    "Errezil": "Urola-Costa", "Beizama": "Urola-Costa",
}


def load_api_key():
    with open(ENV_PATH, "rb") as f:
        raw = f.read()
    try:
        text = raw.decode("utf-16")
    except (UnicodeDecodeError, UnicodeError):
        text = raw.decode("utf-8-sig")
    for line in text.strip().split("\n"):
        line = line.strip()
        if line.startswith("ANTHROPIC_API_KEY"):
            return line.split("=", 1)[1].strip()
    raise ValueError("ANTHROPIC_API_KEY no encontrada")


def read_csv():
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        fieldnames = list(reader.fieldnames)
        rows = list(reader)
    return rows, fieldnames


def write_csv(rows, fieldnames):
    with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def normalize_municipio(raw: str) -> str:
    """Normalize Haiku's response to canonical municipality name."""
    raw = raw.strip().strip('"').strip("'").strip(".")
    # Common normalizations
    norm = {
        "Donostia/San Sebastián": "Donostia-San Sebastián",
        "Donostia / San Sebastián": "Donostia-San Sebastián",
        "Donostia-San Sebastian": "Donostia-San Sebastián",
        "San Sebastián": "Donostia-San Sebastián",
        "Donostia": "Donostia-San Sebastián",
        "Irún": "Irun",
        "Mondragón": "Arrasate/Mondragón",
        "Arrasate": "Arrasate/Mondragón",
        "Mondragon": "Arrasate/Mondragón",
        "Usúrbil": "Usurbil",
    }
    return norm.get(raw, raw)


def get_comarca(municipio: str) -> str:
    if not municipio:
        return ""
    return COMARCA_MAP.get(municipio, "")


# ─── Stats tracking ───

class Stats:
    def __init__(self):
        self.processed = 0
        self.geolocated = 0
        self.fuera = 0
        self.desconocido = 0
        self.errors = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_searches = 0
        self.start_time = time.time()

    @property
    def cost(self):
        return (
            self.total_searches * COST_PER_SEARCH
            + self.total_input_tokens * COST_PER_INPUT_TOKEN
            + self.total_output_tokens * COST_PER_OUTPUT_TOKEN
        )

    def log_batch(self):
        elapsed = time.time() - self.start_time
        rate = self.processed / elapsed if elapsed > 0 else 0
        print(
            f"  [{self.processed:4d} procesadas] "
            f"geo={self.geolocated} fuera={self.fuera} desc={self.desconocido} err={self.errors} | "
            f"searches={self.total_searches} cost=${self.cost:.2f} | "
            f"{rate:.1f} emp/s"
        )


# ─── Main geolocate function ───

async def geolocate_one(client, row, sem, stats):
    nombre = row.get("Nombre", "")
    nif = row.get("NIF", "")
    web = row.get("web_oficial", "")
    actividad = (row.get("actividad_resumen", "") or "")[:200]

    prompt = (
        f"¿En qué municipio de Gipuzkoa (País Vasco, España) tiene su sede, "
        f"planta o centro de actividad principal esta empresa?\n"
        f"Nombre: {nombre}\n"
        f"NIF: {nif}\n"
        f"Web: {web}\n"
        f"Actividad: {actividad}\n\n"
        f"Si la empresa NO tiene presencia en Gipuzkoa, responde 'FUERA'.\n"
        f"Si no encuentras información suficiente, responde 'DESCONOCIDO'.\n"
        f"Responde SOLO con el nombre del municipio, 'FUERA', o 'DESCONOCIDO'."
    )

    async with sem:
        try:
            resp = await asyncio.to_thread(
                client.messages.create,
                model=MODEL,
                max_tokens=16000,
                tools=[{
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "max_uses": 2,
                }],
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract text from response
            answer = ""
            for block in resp.content:
                if hasattr(block, "text"):
                    answer = block.text.strip()

            stats.total_input_tokens += resp.usage.input_tokens
            stats.total_output_tokens += resp.usage.output_tokens
            # Count web searches from server_tool_use blocks
            for block in resp.content:
                if getattr(block, "type", "") == "server_tool_use":
                    stats.total_searches += 1

            stats.processed += 1

            if not answer:
                stats.desconocido += 1
                return

            upper = answer.upper()
            if "FUERA" in upper:
                stats.fuera += 1
                row["comarca"] = "Fuera de Gipuzkoa"
                return

            if "DESCONOCIDO" in upper or "NO " in upper:
                stats.desconocido += 1
                return

            # Got a municipality name
            municipio = normalize_municipio(answer)
            row["poblacion"] = municipio
            comarca = get_comarca(municipio)
            if comarca:
                row["comarca"] = comarca
            else:
                # Unknown comarca - might be a valid Gipuzkoa municipality we don't have
                row["comarca"] = ""
            stats.geolocated += 1

        except Exception as e:
            stats.errors += 1
            stats.processed += 1
            print(f"  ERROR {nombre}: {e}")

        # Batch logging
        if stats.processed % BATCH_LOG_SIZE == 0:
            stats.log_batch()

        # Cost check
        if stats.cost > MAX_COST:
            raise RuntimeError(f"Cost limit exceeded: ${stats.cost:.2f} > ${MAX_COST}")


async def run_geolocate(client, targets, stats):
    sem = asyncio.Semaphore(CONCURRENCY)
    tasks = [geolocate_one(client, row, sem, stats) for row in targets]

    try:
        await asyncio.gather(*tasks)
    except RuntimeError as e:
        print(f"\n** {e}")
        print("Parando automaticamente.")


def main():
    api_key = load_api_key()
    client = anthropic.Anthropic(api_key=api_key)

    rows, fieldnames = read_csv()
    print(f"CSV loaded: {len(rows)} rows")

    # Identify targets
    targets = []
    for row in rows:
        pob = row.get("poblacion", "").strip()
        comarca = row.get("comarca", "").strip()
        if not pob or comarca == "Fuera de Gipuzkoa":
            targets.append(row)

    print(f"Targets to geolocate: {len(targets)}")
    print(f"  - Empty poblacion: {sum(1 for r in targets if not r.get('poblacion','').strip())}")
    print(f"  - Fuera de Gipuzkoa: {sum(1 for r in targets if r.get('comarca','') == 'Fuera de Gipuzkoa')}")
    print(f"  - Max cost limit: ${MAX_COST}")
    print(f"  - Concurrency: {CONCURRENCY}")
    print()

    stats = Stats()
    asyncio.run(run_geolocate(client, targets, stats))

    # Final stats
    stats.log_batch()
    print(f"\n{'='*60}")
    print(f"RESUMEN FINAL")
    print(f"{'='*60}")
    print(f"  Procesadas:     {stats.processed}")
    print(f"  Geolocalizadas: {stats.geolocated}")
    print(f"  Fuera Gipuzkoa: {stats.fuera}")
    print(f"  Desconocido:    {stats.desconocido}")
    print(f"  Errores:        {stats.errors}")
    print(f"  Búsquedas web:  {stats.total_searches}")
    print(f"  Input tokens:   {stats.total_input_tokens:,}")
    print(f"  Output tokens:  {stats.total_output_tokens:,}")
    print(f"  Coste total:    ${stats.cost:.2f}")
    print(f"  Tiempo:         {time.time() - stats.start_time:.0f}s")

    # Show comarca distribution after update
    comarca_counts = Counter(r.get("comarca", "") for r in rows)
    print(f"\nComarcas después de geolocalización:")
    for c, n in sorted(comarca_counts.items(), key=lambda x: -x[1]):
        label = c or "(vacío)"
        print(f"  {n:4d} | {label}")

    # Show new municipalities found
    new_munis = Counter()
    for r in targets:
        p = r.get("poblacion", "").strip()
        if p and r.get("comarca", "") != "Fuera de Gipuzkoa":
            new_munis[p] += 1
    if new_munis:
        print(f"\nNuevos municipios asignados:")
        for m, c in new_munis.most_common(20):
            print(f"  {c:3d} | {m} -> {get_comarca(m) or '?'}")

    # Save
    write_csv(rows, fieldnames)
    print(f"\nCSV guardado: {OUTPUT_CSV}")

    # Copy to frontend
    shutil.copy2(OUTPUT_CSV, FRONTEND_CSV)
    print(f"Copiado a: {FRONTEND_CSV}")


if __name__ == "__main__":
    main()
