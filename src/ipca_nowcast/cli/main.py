"""`macro` CLI. Subcommands are wired up incrementally per phase."""

from __future__ import annotations

import typer

from ipca_nowcast import __version__

app = typer.Typer(
    name="macro",
    help="Painel Macro Brasil — nowcasting, ingestion and evaluation CLI.",
    no_args_is_help=True,
)


@app.command()
def version() -> None:
    """Print the package version."""
    typer.echo(__version__)


if __name__ == "__main__":
    app()
