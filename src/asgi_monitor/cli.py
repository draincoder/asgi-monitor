import json
import logging
from pathlib import Path
from typing import Any

import click

from asgi_monitor.logging.uvicorn import build_uvicorn_log_config

__all__ = ("uvicorn_log_config",)


TRACE_LOG_LEVEL = 5
LOG_LEVELS: dict[str, int] = {
    "critical": logging.CRITICAL,
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG,
    "trace": TRACE_LOG_LEVEL,
}
LEVEL_CHOICES = click.Choice(list(LOG_LEVELS.keys()))


def _save_json_config(path: str, log_config: dict[str, Any]) -> None:
    with Path(path).open("w") as f:
        json.dump(log_config, f, indent=4)


@click.group()
def main() -> None:
    pass


@click.command()
@click.option("--path", type=click.Path(dir_okay=False), help="Path to save config. Supported formats: .json")
@click.option("--level", type=LEVEL_CHOICES, default="info", help="Logging level")
@click.option("--json-format", is_flag=True, help="Render log as JSON")
@click.option("--include-trace", is_flag=True, help="Include tracing information")
def uvicorn_log_config(
    *,
    path: str,
    level: str,
    json_format: bool,
    include_trace: bool,
) -> None:
    """Write uvicorn config in file."""

    if not path.endswith(".json"):
        raise click.exceptions.BadParameter("Support only JSON format")

    log_config = build_uvicorn_log_config(level=LOG_LEVELS[level], json_format=json_format, include_trace=include_trace)
    _save_json_config(path, log_config)

    click.echo(f"Successfully wrote log config in {path}")


main.add_command(uvicorn_log_config)
