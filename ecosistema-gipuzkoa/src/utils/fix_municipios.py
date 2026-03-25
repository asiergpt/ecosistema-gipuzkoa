"""Fix messy municipio names from Haiku responses and reassign comarcas."""

import csv
import re
import shutil
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CSV_PATH = PROJECT_ROOT / "data" / "processed" / "step5_con_taxonomia_v2.csv"
FRONTEND_CSV = PROJECT_ROOT / "frontend" / "public" / "data.csv"

# Canonical municipio names (key=lowercase variant, value=canonical)
MUNI_NORM = {}

# Build normalization map
_CANONICAL = [
    ("Donostia-San Sebastian", [
        "donostia-san sebastian", "donostia/san sebastian", "donostia",
        "san sebastian", "donostia-san sebastian", "zubieta",
        "san sebasti\u00e1n", "donostia-san sebasti\u00e1n", "donostia/san sebasti\u00e1n",
    ]),
    ("Irun", ["irun", "ir\u00fan"]),
    ("Arrasate/Mondragon", [
        "arrasate/mondragon", "arrasate-mondragon", "arrasate", "mondragon",
    ]),
    ("Elgoibar", ["elgoibar"]),
    ("Azpeitia", ["azpeitia"]),
    ("Errenteria", ["errenteria"]),
    ("Bergara", ["bergara"]),
    ("Astigarraga", ["astigarraga"]),
    ("Zestoa", ["zestoa"]),
    ("Lezo", ["lezo"]),
    ("Beasain", ["beasain"]),
    ("Zarautz", ["zarautz"]),
    ("Andoain", ["andoain"]),
    ("Hernani", ["hernani"]),
    ("Mendaro", ["mendaro"]),
    ("Oiartzun", ["oiartzun"]),
    ("Orio", ["orio"]),
    ("Urnieta", ["urnieta"]),
    ("Aduna", ["aduna"]),
    ("Lasarte-Oria", ["lasarte-oria"]),
    ("Zaldibia", ["zaldibia"]),
    ("Ikaztegieta", ["ikaztegieta"]),
    ("Tolosa", ["tolosa"]),
    ("Idiazabal", ["idiazabal"]),
    ("Arama", ["arama"]),
    ("Gabiria", ["gabiria"]),
    ("Leaburu", ["leaburu"]),
    ("Legazpi", ["legazpi", "legazpia"]),
    ("Soraluze", ["soraluze", "placencia de las armas"]),
    ("Deba", ["deba", "itziar"]),
    ("Zumaia", ["zumaia"]),
    ("Errezil", ["errezil"]),
    ("Azkoitia", ["azkoitia"]),
    ("Pasaia", ["pasaia"]),
    ("Hondarribia", ["hondarribia"]),
    ("Urretxu", ["urretxu"]),
    ("Ordizia", ["ordizia"]),
    ("Eibar", ["eibar"]),
    ("Onati", ["onati", "o\u00f1ati"]),
    ("Usurbil", ["usurbil"]),
]

for canonical, variants in _CANONICAL:
    MUNI_NORM[canonical.lower()] = canonical
    for v in variants:
        MUNI_NORM[v.lower()] = canonical

# Comarca mapping
COMARCA_MAP = {
    "Donostia-San Sebastian": "Donostialdea",
    "Hernani": "Donostialdea", "Astigarraga": "Donostialdea",
    "Andoain": "Donostialdea", "Lasarte-Oria": "Donostialdea",
    "Usurbil": "Donostialdea", "Urnieta": "Donostialdea",
    "Villabona": "Donostialdea", "Aduna": "Donostialdea",
    "Orio": "Donostialdea", "Asteasu": "Donostialdea",
    "Zizurkil": "Donostialdea",
    "Irun": "Bidasoa", "Hondarribia": "Bidasoa",
    "Oiartzun": "Bidasoa", "Lezo": "Bidasoa",
    "Pasaia": "Bidasoa", "Errenteria": "Bidasoa",
    "Tolosa": "Tolosaldea", "Ibarra": "Tolosaldea",
    "Anoeta": "Tolosaldea", "Alkiza": "Tolosaldea",
    "Belauntza": "Tolosaldea", "Legorreta": "Tolosaldea",
    "Alegia": "Tolosaldea", "Irura": "Tolosaldea",
    "Amezketa": "Tolosaldea", "Albiztur": "Tolosaldea",
    "Lizartza": "Tolosaldea", "Altzo": "Tolosaldea",
    "Bidegoian": "Tolosaldea", "Hernialde": "Tolosaldea",
    "Ikaztegieta": "Tolosaldea", "Berrobi": "Tolosaldea",
    "Berastegi": "Tolosaldea", "Leaburu": "Tolosaldea",
    "Beasain": "Goierri", "Ordizia": "Goierri",
    "Lazkao": "Goierri", "Zumarraga": "Goierri",
    "Legazpi": "Goierri", "Urretxu": "Goierri",
    "Segura": "Goierri", "Idiazabal": "Goierri",
    "Zegama": "Goierri", "Zerain": "Goierri",
    "Ataun": "Goierri", "Gabiria": "Goierri",
    "Olaberria": "Goierri", "Ormaiztegi": "Goierri",
    "Ezkio-Itsaso": "Goierri", "Zaldibia": "Goierri",
    "Arama": "Goierri", "Mutiloa": "Goierri",
    "Arrasate/Mondragon": "Alto Deba", "Bergara": "Alto Deba",
    "Onati": "Alto Deba", "Eskoriatza": "Alto Deba",
    "Aretxabaleta": "Alto Deba", "Antzuola": "Alto Deba",
    "Leintz-Gatzaga": "Alto Deba",
    "Eibar": "Bajo Deba", "Elgoibar": "Bajo Deba",
    "Deba": "Bajo Deba", "Mutriku": "Bajo Deba",
    "Soraluze": "Bajo Deba", "Mendaro": "Bajo Deba",
    "Ermua": "Bajo Deba", "Mallabia": "Bajo Deba",
    "Elgeta": "Bajo Deba",
    "Azpeitia": "Urola-Costa", "Azkoitia": "Urola-Costa",
    "Zarautz": "Urola-Costa", "Zumaia": "Urola-Costa",
    "Getaria": "Urola-Costa", "Zestoa": "Urola-Costa",
    "Aia": "Urola-Costa", "Errezil": "Urola-Costa",
    "Beizama": "Urola-Costa",
}


def extract_municipio(raw: str) -> str:
    """Extract clean municipio from Haiku's verbose response."""
    if not raw or not raw.strip():
        return ""

    txt = raw.strip()

    # Check for FUERA / DESCONOCIDO
    upper = txt.upper()
    if upper in ("FUERA", "DESCONOCIDO"):
        return txt

    # Try to find **Name** (bold markdown)
    bold_matches = re.findall(r"\*\*([^*]+)\*\*", txt)
    if bold_matches:
        candidate = bold_matches[-1].strip()
        norm = MUNI_NORM.get(candidate.lower())
        if norm:
            return norm

    # Try direct lookup (clean single-word response)
    simple = txt.rstrip(".").strip()
    norm = MUNI_NORM.get(simple.lower())
    if norm:
        return norm

    # Try last non-empty line
    lines = [l.strip() for l in txt.split("\n") if l.strip()]
    if lines:
        last = lines[-1].rstrip(".").strip()
        # Remove markdown bold
        last = re.sub(r"\*\*", "", last).strip()
        norm = MUNI_NORM.get(last.lower())
        if norm:
            return norm

    # Scan all text for known municipio names (longest match first)
    lower = txt.lower()
    for muni_lower, canonical in sorted(MUNI_NORM.items(), key=lambda x: -len(x[0])):
        if muni_lower in lower:
            return canonical

    return simple


def main():
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    print(f"Loaded {len(rows)} rows")

    # Fix municipios with empty comarca (messy Haiku responses)
    fixed_muni = 0
    for r in rows:
        p = r.get("poblacion", "").strip()
        c = r.get("comarca", "").strip()
        if p and not c:
            clean = extract_municipio(p)
            if clean and clean != p:
                r["poblacion"] = clean
                fixed_muni += 1

    print(f"Fixed {fixed_muni} messy municipio names")

    # Reassign all comarcas
    comarca_assigned = 0
    for r in rows:
        p = r.get("poblacion", "").strip()
        if p and p in COMARCA_MAP:
            r["comarca"] = COMARCA_MAP[p]
            comarca_assigned += 1
        elif p and not r.get("comarca", "").strip():
            # Try normalized lookup
            norm = MUNI_NORM.get(p.lower())
            if norm and norm in COMARCA_MAP:
                r["poblacion"] = norm
                r["comarca"] = COMARCA_MAP[norm]
                comarca_assigned += 1

    print(f"Comarcas assigned: {comarca_assigned}")

    # Remaining without comarca
    still_empty = Counter()
    for r in rows:
        p = r.get("poblacion", "").strip()
        c = r.get("comarca", "").strip()
        if p and not c:
            still_empty[p] += 1

    if still_empty:
        print(f"\nStill {sum(still_empty.values())} with municipio but no comarca:")
        for m, cnt in still_empty.most_common(30):
            print(f'  {cnt:3d} | "{m[:80]}"')

    # Final distribution
    comarca_counts = Counter(r.get("comarca", "") for r in rows)
    print(f"\nFinal comarca distribution:")
    for c, n in sorted(comarca_counts.items(), key=lambda x: -x[1]):
        label = c or "(vacio)"
        print(f"  {n:4d} | {label}")

    # Save
    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)

    shutil.copy2(CSV_PATH, FRONTEND_CSV)
    print(f"\nSaved and copied to frontend")


if __name__ == "__main__":
    main()
