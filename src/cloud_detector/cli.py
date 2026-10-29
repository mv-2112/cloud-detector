import typer
import json
import csv
import io
import yaml
from typing import Optional
from enum import Enum
from rich.console import Console
from rich.table import Table
from cloud_detector.core import detect_all

class OutputFormat(str, Enum):
    table = "table"
    json = "json"
    yaml = "yaml"
    csv = "csv"
    tsv = "tsv"

app = typer.Typer(
    help="Cloud Infrastructure and Container Runtime Detection CLI Tool.",
    no_args_is_help=False
)
console = Console()

def generate_flat_rows(data: dict, include_runtime: bool) -> list:
    """Helper to convert the nested core library payload into flat rows for CSV/TSV."""
    rows = [
        {
            "Layer": "Infrastructure",
            "Identified As": data["infrastructure"],
            "Definitively Not": "|".join(data["exclusions"]["infrastructure"])
        }
    ]
    if include_runtime and "runtime" in data:
        rows.append({
            "Layer": "Container Runtime",
            "Identified As": data["runtime"],
            "Definitively Not": "|".join(data["exclusions"].get("runtime", []))
        })
    return rows

@app.command(name="detect")
def detect_cmd(
    include_runtime: bool = typer.Option(
        False, "--include-runtime", "-r", 
        help="Include container runtime detection flags."
    ),
    output_format: OutputFormat = typer.Option(
        OutputFormat.table, "--output", "-o", 
        help="The output format configuration."
    ),
    output_file: Optional[str] = typer.Option(
        None, "--file", "-f", 
        help="Optional file path to save the generated output stream."
    )
):
    """
    Probes system variables, file maps, and the local link-local IMDS configuration to return deployment specifics.
    """
    data = detect_all()
    
    # Filter runtime if not explicitly requested
    if not include_runtime:
        data.pop("runtime", None)
        if "runtime" in data.get("exclusions", {}):
            data["exclusions"].pop("runtime", None)

    output_str = ""
    
    # 1. Handle Structural Output Conversions
    if output_format == OutputFormat.json:
        output_str = json.dumps(data, indent=2)
        
    elif output_format == OutputFormat.yaml:
        output_str = yaml.dump(data, default_flow_style=False, sort_keys=False)
        
    elif output_format in (OutputFormat.csv, OutputFormat.tsv):
        fieldnames = ["Layer", "Identified As", "Definitively Not"]
        flat_rows = generate_flat_rows(data, include_runtime)
        
        # Use StringIO to generate standard tabular formatting strings natively
        string_buffer = io.StringIO()
        delimiter = "\t" if output_format == OutputFormat.tsv else ","
        
        writer = csv.DictWriter(string_buffer, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()
        for row in flat_rows:
            writer.writerow(row)
            
        output_str = string_buffer.getvalue()
        string_buffer.close()
    
    elif output_format == OutputFormat.table:
        with console.capture() as capture:
            table = Table(title="[bold cyan]Environment Detection Matrix[/bold cyan]")
            table.add_column("Layer", style="magenta", no_wrap=True)
            table.add_column("Identified As", style="green")
            table.add_column("Definitively Not", style="red")

            table.add_row(
                "Infrastructure", 
                data["infrastructure"], 
                ", ".join(data["exclusions"]["infrastructure"])
            )

            if include_runtime:
                table.add_row(
                    "Container Runtime", 
                    data["runtime"], 
                    ", ".join(data["exclusions"]["runtime"])
                )
            console.print(table)
        output_str = capture.get()

    # 2. Output Handling
    if output_file:
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(output_str)
            import sys
            print(f"[+] Output successfully saved to file: {output_file}", file=sys.stderr)
        except Exception as e:
            typer.echo(f"[-] Error writing file output: {e}", err=True)
            raise typer.Exit(code=1)
    else:
        typer.echo(output_str)

if __name__ == "__main__":
    app()

