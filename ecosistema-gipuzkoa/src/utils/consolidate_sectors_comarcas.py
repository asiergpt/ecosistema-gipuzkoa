"""
Consolidates sector_amigable (maps niche sectors to main 45) and adds comarca column.
Also normalizes municipio duplicates.

Usage: python src/utils/consolidate_sectors_comarcas.py
"""

import csv
import json
import re
from pathlib import Path
from collections import Counter

import anthropic

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CSV_PATH = PROJECT_ROOT / "data" / "processed" / "step5_con_taxonomia.csv"
OUTPUT_CSV = PROJECT_ROOT / "data" / "processed" / "step5_con_taxonomia_v2.csv"
ENV_PATH = PROJECT_ROOT / "config" / ".env"
MODEL = "claude-sonnet-4-20250514"


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


def call_sonnet(client, prompt, label):
    print(f"\n{'='*60}")
    print(f"Llamando a Sonnet: {label}")
    response = client.messages.create(
        model=MODEL,
        max_tokens=8192,
        system="Responde SOLO con JSON válido, sin texto adicional.",
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text
    print(f"Tokens: in={response.usage.input_tokens}, out={response.usage.output_tokens}")
    m = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if m:
        return json.loads(m.group(1))
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        return json.loads(m.group(0))
    print(f"ERROR: no JSON. Response: {text[:300]}")
    return {}


def read_csv():
    rows = []
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)
    return rows, fieldnames


def write_csv(rows, fieldnames):
    with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def main():
    api_key = load_api_key()
    client = anthropic.Anthropic(api_key=api_key)
    rows, fieldnames = read_csv()

    # ═══════════════════════════════════════════════════════════
    # 1. SECTOR AMIGABLE CONSOLIDATION
    # ═══════════════════════════════════════════════════════════

    sector_counts = Counter(r.get("sector_amigable", "") for r in rows)
    # Main sectors (>=5 empresas)
    main_sectors = sorted([s for s, c in sector_counts.items() if c >= 5 and s])
    # Niche sectors (1-4 empresas) that need mapping
    niche_sectors = sorted([s for s, c in sector_counts.items() if 0 < c < 5 and s])

    print(f"Main sectors (>= 5 empresas): {len(main_sectors)}")
    print(f"Niche sectors (< 5 empresas): {len(niche_sectors)}")

    sector_prompt = f"""Mapea cada uno de estos {len(niche_sectors)} sectores de nicho al sector principal más adecuado de la lista de sectores amigables.

SECTORES PRINCIPALES (destino del mapeo):
{chr(10).join(f'- {s}' for s in main_sectors)}

SECTORES DE NICHO A MAPEAR (origen):
{chr(10).join(f'- {s}' for s in niche_sectors)}

Reglas:
- Cada sector de nicho debe mapearse a EXACTAMENTE uno de los sectores principales
- Usa el sector principal más cercano temáticamente
- Si un nicho es claramente maquinaria industrial → "Maquinaria y equipo"
- Si es tecnología/software/IT → el sector tech más cercano de la lista principal
- Si es alimentación → "Industria alimentaria" o el más cercano
- Si no encaja en ninguno → "Otras industrias manufactureras" o "Servicios profesionales diversos"

Devuelve JSON: {{"sector_nicho": "sector_principal_destino", ...}}"""

    sector_mapping = call_sonnet(client, sector_prompt, "sector consolidation")

    # Apply sector mapping
    mapped_count = 0
    for row in rows:
        s = row.get("sector_amigable", "")
        if s in sector_mapping:
            row["sector_amigable"] = sector_mapping[s]
            mapped_count += 1

    print(f"Sectores mapeados: {mapped_count} filas")
    new_sector_counts = Counter(r.get("sector_amigable", "") for r in rows)
    print(f"Sectores únicos después: {len([s for s in new_sector_counts if s])}")

    # ═══════════════════════════════════════════════════════════
    # 2. NORMALIZE MUNICIPIOS
    # ═══════════════════════════════════════════════════════════

    MUNICIPIO_NORMALIZATION = {
        # Donostia variants
        "Donostia/San Sebastián": "Donostia-San Sebastián",
        "Donostia / San Sebastián": "Donostia-San Sebastián",
        "Donostia - San Sebastián": "Donostia-San Sebastián",
        "Donostia": "Donostia-San Sebastián",
        "San Sebastián": "Donostia-San Sebastián",
        "Donostia/San Sebastián, Gipuzkoa": "Donostia-San Sebastián",
        "Donostia-San Sebastián, Gipuzkoa": "Donostia-San Sebastián",
        "Donostia/San Sebastian": "Donostia-San Sebastián",
        # Irún
        "Irún": "Irun",
        "Irun, Gipuzkoa": "Irun",
        "Irún, Gipuzkoa": "Irun",
        "Irún (Gipuzkoa)": "Irun",
        # Arrasate
        "Arrasate/Mondragon": "Arrasate/Mondragón",
        "Arrasate-Mondragón": "Arrasate/Mondragón",
        "Arrasate": "Arrasate/Mondragón",
        "Arrasate o Mondragón": "Arrasate/Mondragón",
        "Arrasate o Mondragon": "Arrasate/Mondragón",
        "Mondragon": "Arrasate/Mondragón",
        # Usurbil
        "Usúrbil": "Usurbil",
        # Composite entries
        "Itziar-Deba": "Deba",
        "Itziar-Deba, Gipuzkoa": "Deba",
        "Aia-Orio": "Aia",
        "Aia-Orio, Gipuzkoa": "Aia",
    }

    # Also strip ", Gipuzkoa" suffix generically
    norm_count = 0
    for row in rows:
        p = row.get("poblacion", "").strip()
        if not p:
            continue
        # Check explicit mapping first
        if p in MUNICIPIO_NORMALIZATION:
            row["poblacion"] = MUNICIPIO_NORMALIZATION[p]
            norm_count += 1
        # Strip ", Gipuzkoa" suffix
        elif p.endswith(", Gipuzkoa"):
            row["poblacion"] = p.replace(", Gipuzkoa", "")
            norm_count += 1
        # Strip " (Gipuzkoa)" suffix
        elif p.endswith(" (Gipuzkoa)"):
            row["poblacion"] = p.replace(" (Gipuzkoa)", "")
            norm_count += 1

    print(f"\nMunicipios normalizados: {norm_count} filas")
    muni_counts = Counter(r.get("poblacion", "") for r in rows)
    unique_munis = sorted([m for m in muni_counts if m])
    print(f"Municipios únicos después: {len(unique_munis)}")

    # ═══════════════════════════════════════════════════════════
    # 3. MAP MUNICIPIOS TO COMARCAS
    # ═══════════════════════════════════════════════════════════

    comarca_prompt = f"""Mapea cada uno de estos {len(unique_munis)} municipios a su comarca de Gipuzkoa.

Las 7 comarcas de Gipuzkoa son:
- Donostialdea: Donostia-San Sebastián, Hernani, Astigarraga, Andoain, Lasarte-Oria, Usurbil, Urnieta, Villabona, Aduna, Orio, etc.
- Bidasoa: Irun, Hondarribia, Oiartzun, Lezo, Pasaia, Errenteria
- Tolosaldea: Tolosa, Ibarra, Anoeta, Asteasu, Zizurkil, Alkiza, Belauntza, Legorreta, etc.
- Goierri: Beasain, Ordizia, Lazkao, Zumarraga, Legazpi, Urretxu, Segura, Idiazabal, etc.
- Alto Deba: Arrasate/Mondragón, Bergara, Oñati, Eskoriatza, Aretxabaleta, Leintz-Gatzaga, Antzuola
- Bajo Deba: Eibar, Elgoibar, Deba, Mutriku, Soraluze, Mendaro, Ermua, Mallabia
- Urola-Costa: Azpeitia, Azkoitia, Zarautz, Zumaia, Getaria, Zestoa, Aizarnazabal

Si un municipio NO es de Gipuzkoa (ej: Bilbao, Madrid, Barcelona), mapéalo a "Fuera de Gipuzkoa".
Si no estás seguro, usa tu mejor juicio basado en la geografía vasca.

MUNICIPIOS:
{chr(10).join(unique_munis)}

Devuelve JSON: {{"municipio": "comarca", ...}}"""

    comarca_mapping = call_sonnet(client, comarca_prompt, "comarca mapping")

    # Add comarca column
    if "comarca" not in fieldnames:
        # Insert after poblacion
        idx = fieldnames.index("poblacion") + 1 if "poblacion" in fieldnames else len(fieldnames)
        fieldnames = list(fieldnames)
        fieldnames.insert(idx, "comarca")

    for row in rows:
        p = row.get("poblacion", "").strip()
        row["comarca"] = comarca_mapping.get(p, "")

    comarca_counts = Counter(r.get("comarca", "") for r in rows)
    print(f"\nComarcas asignadas:")
    for c, n in sorted(comarca_counts.items(), key=lambda x: -x[1]):
        if c:
            print(f"  {c}: {n}")

    # ═══════════════════════════════════════════════════════════
    # SAVE
    # ═══════════════════════════════════════════════════════════

    write_csv(rows, fieldnames)
    print(f"\nCSV guardado: {OUTPUT_CSV}")
    print(f"Filas: {len(rows)}")

    # Copy to frontend
    import shutil
    frontend_csv = PROJECT_ROOT / "frontend" / "public" / "data.csv"
    shutil.copy2(OUTPUT_CSV, frontend_csv)
    print(f"Copiado a: {frontend_csv}")


if __name__ == "__main__":
    main()
