import json
import subprocess
from pathlib import Path

from assertpy import assert_that

from asgi_monitor.logging.uvicorn import build_uvicorn_log_config


def test_generate_log_config_file(tmpdir: Path) -> None:
    # Arrange
    path = str(tmpdir) + "/log_config.json"
    expected = build_uvicorn_log_config(json_format=True, include_trace=True)

    # Act
    result = subprocess.run(
        [
            "asgi-monitor",
            "uvicorn-log-config",
            "--path",
            path,
            "--json-format",
            "--include-trace",
        ],
        check=True,
        capture_output=True,
    )

    # Assert
    with Path(path).open("r") as f:
        log_config = json.load(f)

    assert_that(log_config).is_equal_to(expected)
    assert_that(result.stdout.decode()).contains(f"Successfully wrote log config in {path}")


def test_generate_log_config_file_not_json(tmpdir: Path) -> None:
    # Arrange
    path = str(tmpdir) + "/log_config.ini"

    # Act
    result = subprocess.run(
        [
            "asgi-monitor",
            "uvicorn-log-config",
            "--path",
            path,
            "--json-format",
            "--include-trace",
        ],
        capture_output=True,
        check=False,
    )

    # Assert
    assert_that(result.stderr.decode()).contains("Error: Invalid value: Support only JSON format")
