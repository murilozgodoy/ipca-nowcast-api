"""`macro` CLI. Subcommands are wired up incrementally per phase."""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

import typer

from ipca_nowcast import __version__
from ipca_nowcast.config import get_settings
from ipca_nowcast.db.session import session_scope
from ipca_nowcast.ingestion.registry import load_registry
from ipca_nowcast.ingestion.service import IngestionService
from ipca_nowcast.logging import configure_logging, get_logger

app = typer.Typer(
    name="macro",
    help="Painel Macro Brasil — nowcasting, ingestion and evaluation CLI.",
    no_args_is_help=True,
)
db_app = typer.Typer(help="Database management.", no_args_is_help=True)
app.add_typer(db_app, name="db")

# Wire pipeline subcommands (nowcast, backtest).
from ipca_nowcast.cli import pipeline as _pipeline  # noqa: E402

_pipeline.register(app)


@app.command()
def version() -> None:
    """Print the package version."""
    typer.echo(__version__)


@db_app.command("upgrade")
def db_upgrade(revision: str = "head") -> None:
    """Run `alembic upgrade <revision>` (default: head)."""
    configure_logging(get_settings().log_level)
    cmd = [sys.executable, "-m", "alembic", "upgrade", revision]
    typer.echo(" ".join(cmd))
    result = subprocess.run(cmd, check=False)
    raise typer.Exit(result.returncode)


@app.command()
def ingest(
    series: str | None = typer.Option(None, help="Fetch a single series by external_id."),
    all_series: bool = typer.Option(False, "--all", help="Fetch every series in the registry."),
    focus: bool = typer.Option(False, "--focus", help="Also fetch Focus expectations."),
    use_cache: bool = typer.Option(True, help="Cache raw downloads under data/raw/."),
) -> None:
    """Fetch series from the public APIs and upsert them into the database."""
    configure_logging(get_settings().log_level)
    logger = get_logger(__name__)
    if not series and not all_series and not focus:
        raise typer.BadParameter("Pass --all, --series <id>, or --focus.")
    with session_scope() as session:
        svc = IngestionService(session)
        if all_series:
            outcomes = svc.ingest_all(use_cache=use_cache)
            logger.info("ingest_all_done", count=len(outcomes))
            for o in outcomes:
                typer.echo(
                    f"{o.series_code}: upserted={o.rows_upserted} n={o.report.n_points} "
                    f"gaps={o.report.gaps} dups={o.report.duplicates}"
                )
        elif series:
            spec = next((s for s in svc.registry if s.external_id == series), None)
            if spec is None:
                raise typer.BadParameter(f"Series {series} not in registry.")
            outcome = svc.ingest_series(spec, use_cache=use_cache)
            typer.echo(f"{outcome.series_code}: upserted={outcome.rows_upserted}")
        if focus:
            n = svc.ingest_focus(use_cache=use_cache)
            typer.echo(f"focus: upserted={n}")


@app.command()
def seed(
    fixtures: bool = typer.Option(False, "--fixtures", help="Load tests/fixtures/*.json."),
    fixtures_dir: Path = typer.Option(
        Path("tests/fixtures"),
        help="Fixtures directory (defaults to tests/fixtures).",
    ),
) -> None:
    """Populate the database from offline fixtures (no internet required)."""
    configure_logging(get_settings().log_level)
    if not fixtures:
        raise typer.BadParameter("Pass --fixtures to confirm offline seed.")
    if not fixtures_dir.exists():
        raise typer.BadParameter(f"Fixtures dir not found: {fixtures_dir}")
    with session_scope() as session:
        svc = IngestionService(session)
        counts = svc.seed_from_fixtures(fixtures_dir)
    typer.echo(json.dumps(counts, indent=2, default=str))


@app.command("series-list")
def series_list() -> None:
    """List registered series from `config/series.yaml`."""
    for spec in load_registry():
        marker = "*" if spec.is_target else " "
        typer.echo(
            f"{marker} {spec.code:12s} {spec.source:10s} lag={spec.publication_lag_days:>3}d  "
            f"{spec.frequency:<8s} {spec.name}"
        )


# Hook to let typer resolve the entry point gracefully if invoked without args.
def _entry() -> None:
    try:
        app()
    except SystemExit as exc:
        if exc.code is None:
            raise
        raise


if __name__ == "__main__":
    _entry()


# Silence unused imports used only via the Typer registry.
_ = dt
