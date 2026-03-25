"""
CLI del proyecto Ecosistema Gipuzkoa.

Uso:
    python cli.py run --provincia gipuzkoa
    python cli.py step1-recuperar
    python cli.py quality-report
    python cli.py export-revision
"""

import typer
from rich.console import Console

app = typer.Typer(
    name="ecosistema-gipuzkoa",
    help="Pipeline de inteligencia empresarial del ecosistema guipuzcoano.",
)
console = Console()


@app.command()
def run(
    provincia: str = typer.Option("gipuzkoa", help="Provincia a procesar."),
    skip_enrich: bool = typer.Option(False, help="Saltar enriquecimiento con IA."),
):
    """Ejecuta el pipeline completo (pasos 1-6)."""
    console.print(f"\n[bold]Pipeline completo para {provincia}[/bold]\n")

    from src.pipeline.step1_recuperar import ejecutar as step1
    from src.pipeline.step2_mapping_sectorial import ejecutar as step2
    from src.pipeline.step3_deduplicar import ejecutar as step3
    from src.pipeline.step4_validar_datos import ejecutar as step4

    step1()
    step2()
    step3()
    step4()

    console.print("\n[green]Steps 1-4 completados.[/green]")
    console.print("[yellow]Steps 5-6 (taxonomía y scoring) pendientes de implementar.[/yellow]")


@app.command()
def step1_recuperar():
    """Paso 1: Recuperar empresas eliminadas del ranking original."""
    console.print("\n[bold]Paso 1: Recuperar empresas[/bold]\n")
    from src.pipeline.step1_recuperar import ejecutar
    ejecutar()


@app.command()
def step2_mapping():
    """Paso 2: Aplicar mapping CNAE → Sector Amigable."""
    console.print("\n[bold]Paso 2: Mapping sectorial[/bold]\n")
    from src.pipeline.step2_mapping_sectorial import ejecutar
    ejecutar()


@app.command()
def step3_grupos():
    """Paso 3: Detectar y marcar grupos empresariales."""
    console.print("\n[bold]Paso 3: Grupos empresariales[/bold]\n")
    from src.pipeline.step3_deduplicar import ejecutar
    ejecutar()


@app.command()
def step4_validar():
    """Paso 4: Validar datos y detectar inconsistencias."""
    console.print("\n[bold]Paso 4: Validación de datos[/bold]\n")
    from src.pipeline.step4_validar_datos import ejecutar
    ejecutar()


@app.command()
def enrich(
    bloque: int = typer.Option(None, "--bloque", "-b", help="Bloque: 1 (nuevas), 2 (top 200), 3 (resto). Todos usan enriquecimiento completo."),
    max_empresas: int = typer.Option(None, "--max-empresas", "-n", help="Máximo de empresas a procesar (para testing)."),
    all_bloques: bool = typer.Option(False, "--all", help="Procesar bloques 1→2→3 en orden."),
):
    """Enriquecer empresas con Haiku 4.5 + Web Search (22 campos, todos los bloques)."""
    console.print("\n[bold]Enriquecimiento: Haiku 4.5 + Web Search[/bold]\n")
    from src.enrichment.haiku_client import ejecutar

    bloque_final = None if all_bloques else bloque
    if bloque_final is None and not all_bloques:
        bloque_final = 1  # Default: bloque 1

    ejecutar(bloque=bloque_final, max_empresas=max_empresas)


@app.command()
def classify(
    dimension: int = typer.Option(None, "--dimension", "-d", help="Dimensión: 1 (cotización), 2 (propiedad), 3 (rol ecosistema)."),
    max_empresas: int = typer.Option(None, "--max-empresas", "-n", help="Máximo de empresas a clasificar (para testing)."),
    all_dims: bool = typer.Option(False, "--all", help="Clasificar las 3 dimensiones (1→2→3)."),
):
    """Clasificar empresas por taxonomía (3 dimensiones con Sonnet)."""
    console.print("\n[bold]Clasificación taxonómica (Sonnet 4.6)[/bold]\n")
    from src.pipeline.step5_taxonomia import ejecutar

    dim = None if all_dims else dimension
    ejecutar(dimension=dim, max_empresas=max_empresas)


@app.command()
def step5_taxonomia():
    """Paso 5: Clasificar por taxonomía (alias de classify --all)."""
    console.print("\n[bold]Paso 5: Taxonomía[/bold]\n")
    from src.pipeline.step5_taxonomia import ejecutar
    ejecutar()


@app.command()
def step6_scoring():
    """Paso 6: Recalcular scoring con datos limpios."""
    console.print("\n[bold]Paso 6: Scoring[/bold]\n")
    console.print("[yellow]Pendiente de implementar.[/yellow]")


@app.command()
def quality_report():
    """Genera informe de calidad del dataset."""
    console.print("\n[bold]Informe de calidad[/bold]\n")
    console.print("[yellow]Pendiente de implementar.[/yellow]")


@app.command()
def export_revision():
    """Exporta empresas con taxonomía dudosa para revisión manual."""
    console.print("\n[bold]Exportar para revisión[/bold]\n")
    from src.pipeline.step5_taxonomia import exportar_revision
    from src.utils.io import leer_csv
    from pathlib import Path

    csv = Path("data/processed/step5_con_taxonomia.csv")
    if not csv.exists():
        console.print("[red]No se encontró step5_con_taxonomia.csv. Ejecuta primero classify.[/red]")
        return
    df = leer_csv(csv)
    exportar_revision(df)


if __name__ == "__main__":
    app()
