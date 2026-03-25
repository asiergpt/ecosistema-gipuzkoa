"""
Consolidates group data before duplicate removal.
For each group, merges data from all member rows into the keeper row.
Uses deterministic rules for numeric fields and Sonnet for text synthesis.

Usage: python scripts/consolidate_groups.py --provincia gipuzkoa
"""

import argparse
import csv
import json
import re
import time
from datetime import datetime
from pathlib import Path

import anthropic

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL = "claude-sonnet-4-20250514"


def load_api_key():
    env_path = PROJECT_ROOT / "config" / ".env"
    with open(env_path, "rb") as f:
        raw = f.read()
    try:
        text = raw.decode("utf-16")
    except (UnicodeDecodeError, UnicodeError):
        text = raw.decode("utf-8-sig")
    for line in text.strip().split("\n"):
        line = line.strip()
        if line.startswith("ANTHROPIC_API_KEY"):
            return line.split("=", 1)[1].strip()
    raise ValueError("ANTHROPIC_API_KEY not found")


def parse_num(val):
    if not val:
        return None
    try:
        return float(str(val).strip())
    except ValueError:
        m = re.search(r"\d+\.?\d*", str(val))
        if m:
            try:
                return float(m.group())
            except ValueError:
                return None
        return None


# ─── Deterministic consolidation rules (Type A + B) ───

POSITION_ORDER = [
    "local", "regional", "B2C", "B2B", "referente nacional",
    "líder nacional", "líder europeo", "líder mundial",
]

ROL_ORDER = [
    "Resto del tejido empresarial", "Campeona oculta", "Campeona visible",
]

STACK_ORDER = ["", "sin evidencia", "Básico", "Avanzado"]

TECH_TEAM_ORDER = ["", "sin evidencia", "mínimo (<5)", "medio (5-20)", "grande (>20)"]

CONFIANZA_ORDER = ["", "baja", "media", "alta"]


def best_ordinal(rows, field, order):
    """Return the best value from an ordered list."""
    best_idx = -1
    for r in rows:
        val = r.get(field, "").strip()
        for i, o in enumerate(order):
            if o and val.startswith(o):
                best_idx = max(best_idx, i)
                break
    return order[best_idx] if best_idx >= 0 else ""


def consolidate_deterministic(keeper, all_rows):
    """Apply deterministic consolidation rules to the keeper row."""
    changes = []

    # empleados_numero: MAX
    vals = [parse_num(r.get("empleados_numero")) for r in all_rows]
    vals = [v for v in vals if v is not None]
    if vals:
        best = max(vals)
        old = keeper.get("empleados_numero", "")
        if parse_num(old) != best:
            keeper["empleados_numero"] = str(int(best))
            changes.append(("empleados_numero", old, str(int(best)), "MAX"))

    # ventas_reales: MAX (and track which row had it for ventas_confianza)
    best_ventas = None
    best_ventas_conf = ""
    for r in all_rows:
        v = parse_num(r.get("ventas_reales"))
        if v is not None and (best_ventas is None or v > best_ventas):
            best_ventas = v
            best_ventas_conf = r.get("ventas_confianza", "")
    if best_ventas is not None:
        old = keeper.get("ventas_reales", "")
        if parse_num(old) != best_ventas:
            keeper["ventas_reales"] = str(best_ventas)
            keeper["ventas_confianza"] = best_ventas_conf
            changes.append(("ventas_reales", old, str(best_ventas), "MAX"))

    # usa_ia: "Sí" if ANY
    if any(r.get("usa_ia", "").startswith("S") for r in all_rows):
        old = keeper.get("usa_ia", "")
        if not old.startswith("S"):
            keeper["usa_ia"] = "Sí"
            changes.append(("usa_ia", old, "Sí", "ANY_YES"))

    # patentes: SUM
    pat_vals = [parse_num(r.get("patentes")) for r in all_rows]
    pat_vals = [v for v in pat_vals if v is not None and v > 0]
    if pat_vals:
        total = sum(pat_vals)
        old = keeper.get("patentes", "")
        if parse_num(old) != total:
            keeper["patentes"] = str(int(total))
            changes.append(("patentes", old, str(int(total)), "SUM"))

    # pct_exportacion: MAX
    exp_vals = [parse_num(r.get("pct_exportacion")) for r in all_rows]
    exp_vals = [v for v in exp_vals if v is not None]
    if exp_vals:
        best = max(exp_vals)
        old = keeper.get("pct_exportacion", "")
        if parse_num(old) != best:
            keeper["pct_exportacion"] = str(int(best))
            changes.append(("pct_exportacion", old, str(int(best)), "MAX"))

    # Ordinal fields
    for field, order in [
        ("stack_nivel", STACK_ORDER),
        ("equipo_tech_estimacion", TECH_TEAM_ORDER),
        ("posicion_mercado", POSITION_ORDER),
        ("rol_ecosistema", ROL_ORDER),
        ("taxonomia_confianza", CONFIANZA_ORDER),
    ]:
        best = best_ordinal(all_rows, field, order)
        if best and best != keeper.get(field, ""):
            old = keeper.get(field, "")
            keeper[field] = best
            changes.append((field, old, best, "BEST_ORDINAL"))

    # mercado_cotizacion: any cotiza
    if any(r.get("mercado_cotizacion", "") != "No cotiza" and r.get("mercado_cotizacion", "")
           for r in all_rows):
        for r in all_rows:
            mc = r.get("mercado_cotizacion", "")
            if mc and mc != "No cotiza":
                old = keeper.get("mercado_cotizacion", "")
                if old != mc:
                    keeper["mercado_cotizacion"] = mc
                    changes.append(("mercado_cotizacion", old, mc, "ANY_COTIZA"))
                break

    return changes


# ─── Sonnet consolidation for text fields (Type C) ───

SONNET_FIELDS = [
    "sector_amigable", "tipologia_propiedad", "inversores_capital_privado",
    "ia_detalle", "stack_detalle", "roles_tech_detectados", "inversion_id",
    "producto_propio", "mercado_b2b_b2c", "ceo_actual",
    "taxonomia_razonamiento", "rol_ecosistema_razonamiento",
]


def call_sonnet_consolidate(client, group_name, all_rows, fieldnames):
    """Call Sonnet to synthesize text fields for a group."""
    # Build a summary of all rows
    row_summaries = []
    for r in all_rows:
        summary = {k: r.get(k, "") for k in SONNET_FIELDS + ["Nombre", "empleados_numero", "ventas_reales"]}
        # Only include non-empty fields
        summary = {k: v for k, v in summary.items() if v and v.strip()}
        if summary:
            row_summaries.append(summary)

    if not row_summaries:
        return {}

    prompt = f"""Eres un analista de datos empresariales. Te doy varias filas que representan
diferentes entidades legales del mismo grupo empresarial: "{group_name}".

Genera UNA fila consolidada con los mejores datos del grupo. No inventes datos — usa solo
lo que aparece en las filas. Si un campo no tiene datos útiles en ninguna fila, devuelve null.

Filas del grupo:
{json.dumps(row_summaries, ensure_ascii=False, indent=2)}

Genera JSON con estos campos:
- sector_amigable: sector principal de la actividad REAL del grupo (no "Finanzas y seguros" si es holding industrial)
- tipologia_propiedad: tipología que mejor describe al grupo
- inversores_capital_privado: merge de inversores sin duplicados (o null)
- ia_detalle: combinación de detalles IA de todas las filiales (o null)
- stack_detalle: combinación de stacks tecnológicos (o null)
- roles_tech_detectados: unión de roles tech (o null)
- inversion_id: combinación de evidencia I+D (o null)
- producto_propio: "Sí" o "No" con justificación breve
- mercado_b2b_b2c: "B2B", "B2C" o "Mixto"
- ceo_actual: CEO/director del grupo (no de una filial)
- taxonomia_razonamiento: razonamiento para la taxonomía de propiedad
- rol_ecosistema_razonamiento: razonamiento para el rol en el ecosistema

Responde SOLO con JSON."""

    for attempt in range(3):
        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=1500,
                temperature=0,
                system="Responde SOLO con JSON válido.",
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.content[0].text

            # Save raw response
            responses_dir = PROJECT_ROOT / "data" / "processed" / "sonnet_consolidation_responses"
            responses_dir.mkdir(parents=True, exist_ok=True)
            safe_name = re.sub(r'[^\w\-]', '_', group_name)[:50]
            (responses_dir / f"{safe_name}.json").write_text(text, encoding="utf-8")

            # Parse JSON
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if m:
                return json.loads(m.group())
            return {}
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** (attempt + 1))
                continue
            print(f"    ERROR Sonnet for {group_name}: {e}")
            return {}

    return {}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provincia", default="gipuzkoa")
    args = parser.parse_args()

    # Paths
    rules_path = PROJECT_ROOT / "data" / "raw" / "cleanup_rules.json"
    input_csv = PROJECT_ROOT / "data" / "processed" / "resultado_guipuzcoa.csv"
    output_csv = PROJECT_ROOT / "data" / "processed" / "resultado_guipuzcoa_consolidado.csv"
    log_csv = PROJECT_ROOT / "data" / "processed" / "consolidation_log.csv"

    # Load
    with open(rules_path, encoding="utf-8") as f:
        rules = json.load(f)

    with open(input_csv, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    print(f"Loaded {len(rows)} rows from {input_csv.name}")
    print(f"Rules: {len(rules['grupos_consolidar'])} groups")

    # Build name index
    name_idx = {}
    for i, r in enumerate(rows):
        name_idx[r.get("Nombre", "")] = i

    api_key = load_api_key()
    client = anthropic.Anthropic(api_key=api_key)

    log_entries = []
    groups_consolidated = 0
    sonnet_calls = 0

    for group in rules["grupos_consolidar"]:
        nombre_final = group["nombre_final"]
        mantener = group.get("mantener")
        eliminar = group.get("eliminar", [])

        if not eliminar:
            continue

        # Find keeper row
        keeper_idx = name_idx.get(mantener)
        if keeper_idx is None and mantener:
            print(f"  WARNING: '{mantener}' not found for group '{nombre_final}'")
            continue

        # Find all group rows (keeper + to-be-eliminated)
        all_names = ([mantener] if mantener else []) + eliminar
        all_rows = []
        for name in all_names:
            idx = name_idx.get(name)
            if idx is not None:
                all_rows.append(rows[idx])

        if len(all_rows) < 2:
            # Only 1 row found (or just eliminations without keeper) — skip consolidation
            continue

        keeper = rows[keeper_idx] if keeper_idx is not None else all_rows[0]
        print(f"  Consolidating: {nombre_final} ({len(all_rows)} rows)")

        # Type A+B: deterministic
        det_changes = consolidate_deterministic(keeper, all_rows)
        for field, old, new, rule in det_changes:
            log_entries.append({
                "grupo": nombre_final,
                "campo": field,
                "valor_antes": old[:100] if old else "",
                "valor_despues": new[:100] if new else "",
                "fuente": rule,
                "timestamp": datetime.now().isoformat(),
            })

        # Type C: Sonnet synthesis (only if group has 2+ rows with text data)
        has_text = any(
            any(r.get(f, "").strip() for f in SONNET_FIELDS)
            for r in all_rows
        )
        if has_text:
            sonnet_result = call_sonnet_consolidate(client, nombre_final, all_rows, fieldnames)
            sonnet_calls += 1

            for field, value in sonnet_result.items():
                if value and field in SONNET_FIELDS:
                    str_val = str(value) if value is not None else ""
                    old = keeper.get(field, "")
                    if str_val and str_val != "null" and str_val != old:
                        keeper[field] = str_val
                        log_entries.append({
                            "grupo": nombre_final,
                            "campo": field,
                            "valor_antes": old[:100] if old else "",
                            "valor_despues": str_val[:100],
                            "fuente": "SONNET",
                            "timestamp": datetime.now().isoformat(),
                        })

        groups_consolidated += 1

    # Save consolidated CSV
    with open(output_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)

    # Save log
    log_fields = ["grupo", "campo", "valor_antes", "valor_despues", "fuente", "timestamp"]
    with open(log_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=log_fields, delimiter=";")
        writer.writeheader()
        writer.writerows(log_entries)

    print(f"\nDone:")
    print(f"  Groups consolidated: {groups_consolidated}")
    print(f"  Sonnet calls: {sonnet_calls}")
    print(f"  Changes logged: {len(log_entries)}")
    print(f"  Output: {output_csv.name}")
    print(f"  Log: {log_csv.name}")


if __name__ == "__main__":
    main()
