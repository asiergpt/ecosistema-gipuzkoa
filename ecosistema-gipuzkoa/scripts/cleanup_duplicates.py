"""
Removes duplicate/subsidiary rows and applies data corrections.
Reads the consolidated CSV (output of consolidate_groups.py) and cleanup_rules.json.

Usage: python scripts/cleanup_duplicates.py --provincia gipuzkoa
"""

import argparse
import csv
import json
import shutil
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provincia", default="gipuzkoa")
    args = parser.parse_args()

    rules_path = PROJECT_ROOT / "data" / "raw" / "cleanup_rules.json"
    input_csv = PROJECT_ROOT / "data" / "processed" / "resultado_guipuzcoa_consolidado.csv"
    output_csv = PROJECT_ROOT / "data" / "processed" / "resultado_guipuzcoa_limpio.csv"
    log_csv = PROJECT_ROOT / "data" / "processed" / "cleanup_log.csv"
    frontend_csv = PROJECT_ROOT / "frontend" / "public" / "data.csv"

    # Fallback to non-consolidated if it doesn't exist
    if not input_csv.exists():
        input_csv = PROJECT_ROOT / "data" / "processed" / "resultado_guipuzcoa.csv"
        print(f"WARNING: consolidated CSV not found, using {input_csv.name}")

    with open(rules_path, encoding="utf-8") as f:
        rules = json.load(f)

    with open(input_csv, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    initial_count = len(rows)
    print(f"Loaded {initial_count} rows from {input_csv.name}")

    # Build name index
    name_set = {r.get("Nombre", "") for r in rows}

    log_entries = []
    timestamp = datetime.now().isoformat()

    # ─── Step 1: Apply group eliminations ───

    to_remove = set()
    renames = {}

    for group in rules.get("grupos_consolidar", []):
        nombre_final = group["nombre_final"]
        mantener = group.get("mantener")
        renombrar_a = group.get("renombrar_a")
        eliminar = group.get("eliminar", [])

        for name in eliminar:
            if name in name_set:
                to_remove.add(name)
                log_entries.append({
                    "accion": "ELIMINAR",
                    "empresa": name,
                    "grupo": nombre_final,
                    "razon": group.get("razon", ""),
                    "timestamp": timestamp,
                })
            else:
                log_entries.append({
                    "accion": "WARNING_NOT_FOUND",
                    "empresa": name,
                    "grupo": nombre_final,
                    "razon": f"Empresa no encontrada en dataset",
                    "timestamp": timestamp,
                })

        if renombrar_a and mantener:
            renames[mantener] = renombrar_a

    # Remove rows
    rows = [r for r in rows if r.get("Nombre", "") not in to_remove]
    removed_count = initial_count - len(rows)

    # Apply renames
    renamed_count = 0
    for r in rows:
        name = r.get("Nombre", "")
        if name in renames:
            r["Nombre"] = renames[name]
            log_entries.append({
                "accion": "RENOMBRAR",
                "empresa": f"{name} -> {renames[name]}",
                "grupo": "",
                "razon": "Renombrar según reglas",
                "timestamp": timestamp,
            })
            renamed_count += 1

    # ─── Step 2: Apply data corrections ───

    corrected_count = 0
    for correction in rules.get("correcciones_datos", []):
        empresa_name = correction["empresa"]
        renombrar_a = correction.get("renombrar_a")
        campos = correction.get("campos", {})

        # Find row (exact match first, then partial)
        target = None
        for r in rows:
            if r.get("Nombre", "") == empresa_name:
                target = r
                break
        if target is None:
            for r in rows:
                if empresa_name.lower() in r.get("Nombre", "").lower():
                    target = r
                    break

        if target is None:
            log_entries.append({
                "accion": "WARNING_NOT_FOUND",
                "empresa": empresa_name,
                "grupo": "",
                "razon": f"Corrección no aplicada — empresa no encontrada",
                "timestamp": timestamp,
            })
            continue

        # Apply field corrections
        for field, value in campos.items():
            old = target.get(field, "")
            target[field] = str(value)
            log_entries.append({
                "accion": "CORREGIR",
                "empresa": target.get("Nombre", ""),
                "grupo": field,
                "razon": f"{old} -> {value} ({correction.get('razon', '')})",
                "timestamp": timestamp,
            })

        # Apply rename
        if renombrar_a:
            old_name = target.get("Nombre", "")
            target["Nombre"] = renombrar_a
            log_entries.append({
                "accion": "RENOMBRAR",
                "empresa": f"{old_name} -> {renombrar_a}",
                "grupo": "",
                "razon": correction.get("razon", ""),
                "timestamp": timestamp,
            })

        corrected_count += 1

    # ─── Save results ───

    with open(output_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)

    log_fields = ["accion", "empresa", "grupo", "razon", "timestamp"]
    with open(log_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=log_fields, delimiter=";")
        writer.writeheader()
        writer.writerows(log_entries)

    # Copy to frontend
    shutil.copy2(output_csv, frontend_csv)

    # Summary
    final_count = len(rows)
    warnings = sum(1 for e in log_entries if e["accion"] == "WARNING_NOT_FOUND")

    print(f"\n{'='*60}")
    print(f"RESUMEN CLEANUP")
    print(f"{'='*60}")
    print(f"  Empresas antes:     {initial_count}")
    print(f"  Eliminadas:         {removed_count}")
    print(f"  Renombradas:        {renamed_count}")
    print(f"  Correcciones datos: {corrected_count}")
    print(f"  Warnings:           {warnings}")
    print(f"  Empresas despues:   {final_count}")
    print(f"  Output:             {output_csv.name}")
    print(f"  Log:                {log_csv.name}")
    print(f"  Frontend:           {frontend_csv.name}")

    # Show warnings
    if warnings > 0:
        print(f"\n  Empresas no encontradas:")
        for e in log_entries:
            if e["accion"] == "WARNING_NOT_FOUND":
                print(f"    - {e['empresa']} ({e['grupo']})")


if __name__ == "__main__":
    main()
