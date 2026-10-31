#!/usr/bin/env python3
"""zyPlat CLI - Command line interface for zyPlat"""

import json
from pathlib import Path

import click
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from .client import ZyPlatClient

console = Console()
DEFAULT_INPUT_DIR = Path(__file__).parent.parent.parent / "input"


@click.group()
@click.option("--api-url", default="http://localhost:8000/api/v1", help="API base URL")
@click.pass_context
def cli(ctx, api_url: str):
    """zyPlat CLI - Manage taxonomies, domains, companies, and domain instances"""
    ctx.ensure_object(dict)
    ctx.obj["client"] = ZyPlatClient(api_url)


@cli.group()
def company():
    """Manage companies"""
    pass


@company.command("create")
@click.option("--file", "-f", type=click.Path(exists=True), help="JSON file with company data")
@click.option("--company-id", help="Company ID")
@click.option("--name", help="Company name")
@click.option(
    "--type",
    "company_type",
    type=click.Choice(["LENDER", "BORROWER", "PARTICIPANT"]),
    help="Company type",
)
@click.pass_context
def company_create(
    ctx,
    file: str | None,
    company_id: str | None,
    name: str | None,
    company_type: str | None,
):
    """Create a new company"""
    client = ctx.obj["client"]

    if file:
        with open(file) as f:
            data = json.load(f)
    elif company_id and name and company_type:
        data = {
            "company_id": company_id,
            "name": name,
            "company_type": company_type,
            "description": "",
        }
    else:
        raise click.UsageError("Either --file or (--company-id, --name, --type) must be provided")

    try:
        result = client.create_company(data)
        console.print(f"[green]✓[/green] Created company: {result['name']} (ID: {result['id']})")
        rprint(result)
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        raise click.Abort() from e


@company.command("list")
@click.pass_context
def company_list(ctx):
    """List all companies"""
    client = ctx.obj["client"]

    try:
        companies = client.list_companies()

        table = Table(title="Companies")
        table.add_column("ID", style="cyan")
        table.add_column("Company ID", style="magenta")
        table.add_column("Name", style="green")
        table.add_column("Type", style="yellow")

        for company in companies:
            table.add_row(
                str(company["id"])[:8],
                company["company_id"],
                company["name"],
                company["company_type"],
            )

        console.print(table)
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        raise click.Abort() from e


@cli.group()
def taxonomy():
    """Manage taxonomies"""
    pass


@taxonomy.command("create")
@click.option("--file", "-f", type=click.Path(exists=True), help="JSON file with taxonomy data")
@click.option(
    "--dir", "-d", type=click.Path(exists=True), help="Directory containing taxonomy files"
)
@click.pass_context
def taxonomy_create(ctx, file: str | None, dir: str | None):
    """Create taxonomy definition(s) from file or directory"""
    client = ctx.obj["client"]

    files: list[Path]
    if file:
        files = [Path(file)]
    elif dir:
        files = list(Path(dir).glob("*.json"))
    else:
        # Default to input/taxonomies
        files = list(DEFAULT_INPUT_DIR.glob("taxonomies/*.json"))

    for filepath in files:
        try:
            with open(filepath) as f:
                data = json.load(f)

            # Transform legacy format to new schema
            taxonomy_data = {
                "taxonomy_id": data.get("id", Path(filepath).stem),
                "version": data.get("version", "1.0.0"),
                "scope_type": "GLOBAL",
                "owner_company_id": None,
                "description": data.get("description", ""),
                "is_hierarchical": data.get("isHierarchical", False),
                "allowed_classifications": data.get("classifications", []),
                "is_published": True,
                "is_default": True,
            }

            result = client.create_taxonomy_definition(taxonomy_data)
            console.print(
                f"[green]✓[/green] Created taxonomy: {result['taxonomy_id']} (ID: {result['id']})"
            )

            # Create entities if present
            if "entities" in data:
                taxonomy_def_id = result["id"]
                for entity in data["entities"]:
                    entity_data = {
                        "taxonomy_definition_id": taxonomy_def_id,
                        "entity_id": entity["id"],
                        "value": entity["value"],
                        "display_name": entity.get("displayName", entity["value"]),
                        "description": entity.get("description", ""),
                        "explicit_classifications": entity.get("classifications", []),
                        "is_base_entity": entity.get("isBase", True),
                        "parent_entity_id": None,  # Simplified for now
                    }
                    client.create_taxonomy_entity(entity_data)
                console.print(f"  Created {len(data['entities'])} entities")

        except Exception as e:
            console.print(f"[red]✗[/red] Error processing {filepath}: {e}")


@taxonomy.command("list")
@click.pass_context
def taxonomy_list(ctx):
    """List all taxonomy definitions"""
    client = ctx.obj["client"]

    try:
        taxonomies = client.list_taxonomy_definitions()

        table = Table(title="Taxonomy Definitions")
        table.add_column("ID", style="cyan")
        table.add_column("Taxonomy ID", style="magenta")
        table.add_column("Version", style="yellow")
        table.add_column("Scope", style="green")
        table.add_column("Hierarchical", style="blue")

        for taxonomy in taxonomies:
            table.add_row(
                str(taxonomy["id"])[:8],
                taxonomy["taxonomy_id"],
                taxonomy["version"],
                taxonomy["scope_type"],
                "Yes" if taxonomy["is_hierarchical"] else "No",
            )

        console.print(table)
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        raise click.Abort() from e


@cli.group()
def domain():
    """Manage domains"""
    pass


@domain.command("create")
@click.option("--file", "-f", type=click.Path(exists=True), help="JSON file with domain data")
@click.option("--dir", "-d", type=click.Path(exists=True), help="Directory containing domain files")
@click.pass_context
def domain_create(ctx, file: str | None, dir: str | None):
    """Create domain definition(s) from file or directory"""
    client = ctx.obj["client"]

    files: list[Path]
    if file:
        files = [Path(file)]
    elif dir:
        files = list(Path(dir).glob("*.json"))
    else:
        # Default to input/domains
        files = list(DEFAULT_INPUT_DIR.glob("domains/*.json"))

    for filepath in files:
        try:
            with open(filepath) as f:
                data = json.load(f)

            # Transform legacy format to new schema
            domain_data = {
                "domain_id": data.get("id", Path(filepath).stem),
                "description": data.get("description", ""),
                "kind": "TIME_SERIES" if data.get("isTimeSeries", False) else "SCALAR",
                "scope_type": "GLOBAL",
                "owner_company_id": None,
            }

            result = client.create_domain_definition(domain_data)
            console.print(
                f"[green]✓[/green] Created domain: {result['domain_id']} (ID: {result['id']})"
            )

        except Exception as e:
            console.print(f"[red]✗[/red] Error processing {filepath}: {e}")


@domain.command("list")
@click.pass_context
def domain_list(ctx):
    """List all domain definitions"""
    client = ctx.obj["client"]

    try:
        domains = client.list_domain_definitions()

        table = Table(title="Domain Definitions")
        table.add_column("ID", style="cyan")
        table.add_column("Domain ID", style="magenta")
        table.add_column("Kind", style="yellow")
        table.add_column("Scope", style="green")

        for domain in domains:
            table.add_row(
                str(domain["id"])[:8], domain["domain_id"], domain["kind"], domain["scope_type"]
            )

        console.print(table)
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        raise click.Abort() from e


if __name__ == "__main__":
    cli(obj={})
