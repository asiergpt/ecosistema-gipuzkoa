"""
Genera diccionarios de entidades limpios usando Claude Sonnet 4.6.
Lee step5_con_taxonomia.csv, extrae valores únicos, hace llamadas a Sonnet,
y guarda el resultado en frontend/public/entity_dicts.json.

Uso: python src/utils/generate_entity_dicts.py
"""

import csv
import json
import re
from pathlib import Path

import anthropic

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CSV_PATH = PROJECT_ROOT / "data" / "processed" / "step5_con_taxonomia.csv"
OUTPUT_PATH = PROJECT_ROOT / "frontend" / "public" / "entity_dicts.json"
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
    raise ValueError("ANTHROPIC_API_KEY no encontrada en config/.env")


def read_unique_values(field: str, min_len: int = 5) -> list[str]:
    values = set()
    noise = {"", "no", "null", "sin datos", "no hay datos", "sin evidencia",
             "no especificado", "no identificado", "no aplica", "sí", "básico", "avanzado"}
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            v = row.get(field, "").strip()
            if v and len(v) >= min_len and v.lower() not in noise:
                values.add(v)
    return sorted(values)


def call_sonnet(client, system, prompt, label):
    print(f"\n{'='*60}")
    print(f"Llamando a Sonnet para: {label}")
    print(f"Longitud del prompt: {len(prompt):,} chars")

    response = client.messages.create(
        model=MODEL,
        max_tokens=8192,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text
    print(f"Tokens: input={response.usage.input_tokens}, output={response.usage.output_tokens}")

    json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            print(f"ERROR: No JSON in response for {label}")
            print(text[:500])
            return {}

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"ERROR parsing JSON for {label}: {e}")
        print(json_str[:500])
        return {}


def main():
    api_key = load_api_key()
    client = anthropic.Anthropic(api_key=api_key)

    system = (
        "Eres un experto en el ecosistema inversor vasco y español. "
        "Responde SOLO con JSON válido, sin texto adicional fuera del JSON."
    )

    results = {}

    # ─── 1. INVERSORES + ACCIONISTAS (unified) ───

    inv_values = read_unique_values("inversores_capital_privado")
    acc_values = read_unique_values("propiedad_accionistas", min_len=15)

    # Combine both fields, truncate accionistas if needed
    inv_text = "\n".join(inv_values)
    acc_text = "\n".join(acc_values)
    if len(acc_text) > 80_000:
        acc_text = acc_text[:80_000] + "\n[... truncado ...]"

    print(f"\ninversores_capital_privado: {len(inv_values)} vals ({len(inv_text):,} chars)")
    print(f"propiedad_accionistas: {len(acc_values)} vals ({len(acc_text):,} chars)")

    inv_prompt = f"""Eres un experto en el ecosistema inversor vasco y español. Analiza estos textos que describen inversores y accionistas de 2.842 empresas guipuzcoanas.

Tu tarea es crear un diccionario LIMPIO y PRECISO para una herramienta de business intelligence. El usuario es un directivo que quiere saber QUIÉN INVIERTE EN GIPUZKOA para poder contactarlos.

CATEGORÍAS (mutuamente excluyentes — cada entidad en UNA sola):

A) Fondos PE/VC: fondos de private equity y venture capital que toman participaciones. Incluye fondos internacionales con inversiones en Gipuzkoa.
   Subcategorías: vascos/locales vs nacionales vs internacionales.

B) Family offices: patrimonios familiares que invierten. Ejemplos vascos: Stellum/Fundación Artizarra, Onchena (Careaga/Ybarra), Mirai (Jainaga), Landon (Gallardo). No confundir con fondos PE.

C) Bancos y cajas: entidades financieras con participaciones empresariales.

D) Institucionales públicos: SOLO entidades públicas (Gobierno Vasco, SPRI, CDTI, IVF/Finkatuz, Diputación, SEPI, COFIDES, BEI, Ekarpen). Macquarie y Meridiam NO son institucionales — son fondos privados internacionales.

E) Aceleradoras/incubadoras: BIC Gipuzkoa, Wayra, eCapital, Lanzadera, BerriUp.

REGLAS DE AGRUPACIÓN:
- Ecosistema Kutxabank: Kutxabank + Indar Kartera + Kutxa Fundazioa + BBK/Fundación BBK + Vital Fundazioa + Inzu Group → UN solo grupo paraguas "Kutxabank"
- Stellum: Stellum Capital + Easo Ventures + Stellum Food&Tech + Fundación Artizarra → UN solo grupo "Stellum"
- Corp. Financiera Alba + Artá Capital → UN solo grupo "Corporación Financiera Alba"
- Gobierno Vasco + IVF + Finkatuz + SPRI + Ekarpen + Ente Vasco de la Energía → UN solo grupo "Gobierno Vasco"
- CDTI + SETT + SEPI + COFIDES → UN solo grupo "Estado Español"

ELIMINAR:
- Empresas industriales que solo aparecen como matrices de sus filiales (CAF, Emmi, CIE Automotive, Atlas Copco, Siemens, ArcelorMittal, Bureau Veritas, Danfoss, DHL, ASSA ABLOY, Dana, Citizen, Connect Group, etc.) — NO son inversores, son multinacionales con plantas en Gipuzkoa
- Cooperativas que son accionistas de sí mismas (Mondragón, ULMA, Fagor, Danobatgroup)
- Holdings empresariales que solo son matrices de sus filiales (Grupo CAF, Grupo Calcinor)
- Personas físicas sueltas (nombres propios sin family office identificado)
- Contextos negativos (salida, abandonó, histórica, desinvertido, no concretada, anteriormente)
- Frases genéricas (empresa familiar, no identificados, estructura cooperativa, trabajadores)
- Entidades con menos de 2 apariciones SALVO fondos PE/VC conocidos activos en Euskadi

NORMALIZAR:
- Title Case para todos los nombres propios
- Siglas en MAYÚSCULAS (BBVA, KKR, CDTI, BEI)

Devuelve SOLO JSON con esta estructura exacta:
{{
  "fondos_pe_vc": {{
    "vascos": {{"nombre_paraguas": ["alias1", "alias2", ...]}},
    "nacionales": {{"nombre_paraguas": ["alias1", ...]}},
    "internacionales": {{"nombre_paraguas": ["alias1", ...]}}
  }},
  "family_offices": {{"nombre_paraguas": ["alias1", ...]}},
  "bancos_cajas": {{"nombre_grupo": ["subentidad1", "subentidad2", ...]}},
  "institucionales_publicos": {{"nombre_paraguas": ["alias1", ...]}},
  "aceleradoras": {{"nombre": ["alias1", ...]}}
}}

=== CAMPO inversores_capital_privado ({len(inv_values)} textos) ===
{inv_text}

=== CAMPO propiedad_accionistas (muestra de {len(acc_values)} textos) ===
{acc_text}"""

    results["inversores_accionistas"] = call_sonnet(client, system, inv_prompt, "inversores+accionistas")

    # ─── 2. STACK TECNOLÓGICO ───

    stack_values = read_unique_values("stack_detalle")
    stack_text = "\n".join(stack_values)
    if len(stack_text) > 100_000:
        stack_text = stack_text[:100_000] + "\n[... truncado ...]"

    print(f"\nstack_detalle: {len(stack_values)} vals ({len(stack_text):,} chars)")

    stack_prompt = f"""Extrae las tecnologías concretas (con nombre propio) mencionadas en el stack tecnológico de empresas guipuzcoanas. Normaliza nombres y agrupa por categoría.

Solo tecnologías que aparezcan en al menos 2 empresas. ~30-60 tecnologías agrupadas.

INCLUIR: tecnologías concretas (SAP, AWS, Docker, Python, PostgreSQL, Siemens NX, SCADA...)
NO INCLUIR: conceptos genéricos (digitalización, Industria 4.0, innovación), certificaciones (ISO 9001), hardware (GPS, RFID)
Agrupa aliases: Amazon Web Services = AWS → "AWS"

Usa capitalización estándar de cada tecnología (AWS, SAP, Python, Docker, PostgreSQL, JavaScript, .NET, Power BI).
Usa Title Case para categorías.

Devuelve SOLO JSON:
{{
  "Cloud": {{"tecnologia": ["alias1", ...], ...}},
  "ERP": {{"tecnologia": ["alias1", ...], ...}},
  "Lenguajes": {{"tecnologia": ["alias1", ...], ...}},
  "DevOps": {{"tecnologia": ["alias1", ...], ...}},
  "BI / Data": {{"tecnologia": ["alias1", ...], ...}},
  "Bases de datos": {{"tecnologia": ["alias1", ...], ...}},
  "Industrial": {{"tecnologia": ["alias1", ...], ...}},
  "Otros": {{"tecnologia": ["alias1", ...], ...}}
}}

TEXTOS:
{stack_text}"""

    results["tecnologias"] = call_sonnet(client, system, stack_prompt, "stack_detalle")

    # ─── 3. APLICACIONES DE IA ───

    ia_values = read_unique_values("ia_detalle")
    print(f"\nia_detalle: {len(ia_values)} vals")

    ia_prompt = f"""Extrae las aplicaciones de IA concretas que usan las empresas guipuzcoanas. Normaliza y agrupa sinónimos.

Solo aplicaciones que aparezcan en al menos 2 empresas. ~15-25 aplicaciones.

INCLUIR: aplicaciones concretas (mantenimiento predictivo, computer vision, NLP, chatbot, gemelo digital, RPA, etc.)
NO INCLUIR: frases genéricas ("usa IA", "invierte en tecnología")
Agrupa sinónimos: "visión artificial" = "computer vision" = "visión por máquina" → "Computer vision"
Fusionar: "CV para control de calidad" con "Computer vision" (misma técnica, aplicación específica)

Usa Title Case para nombres de aplicaciones.

Devuelve SOLO JSON:
{{
  "Aplicacion Normalizada": ["alias1", "alias2", ...]
}}

TEXTOS:
{chr(10).join(ia_values)}"""

    results["aplicaciones_ia"] = call_sonnet(client, system, ia_prompt, "ia_detalle")

    # ─── Guardar resultado ───

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"Guardado en: {OUTPUT_PATH}")
    print(f"Tamaño: {OUTPUT_PATH.stat().st_size:,} bytes")

    # Summary
    def count_entities(d, depth=0):
        if isinstance(d, list):
            return 0  # aliases
        if isinstance(d, dict):
            total = 0
            for v in d.values():
                if isinstance(v, list):
                    total += 1  # this is an entity
                elif isinstance(v, dict):
                    total += count_entities(v, depth + 1)
            return total
        return 0

    for key, data in results.items():
        print(f"  {key}: {count_entities(data)} entidades")


if __name__ == "__main__":
    main()
