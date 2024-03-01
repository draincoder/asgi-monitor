import contextlib
import json
from collections.abc import Iterator, MutableMapping
from json import JSONDecodeError
from typing import Any

import pytest
import structlog
from _pytest.capture import CaptureFixture
from structlog.testing import LogCapture


@contextlib.contextmanager
def capture_full_logs() -> Iterator[list[MutableMapping[str, Any]]]:
    """Copy of structlog.testing.capture_logs() but without processors clearing."""
    cap = LogCapture()

    processors = structlog.get_config()["processors"]
    old_processors = processors.copy()
    try:
        # wrapper change dict tu tuple for logging
        with contextlib.suppress(ValueError):
            processors.remove(structlog.stdlib.ProcessorFormatter.wrap_for_formatter)

        processors.append(cap)
        structlog.configure(processors=processors)
        yield cap.entries
    finally:
        # remove LogCapture and restore original processors
        processors.clear()
        processors.extend(old_processors)
        structlog.configure(processors=processors)


def read_json_logs(capfd: CaptureFixture[str]) -> list[dict[Any, Any]] | Any:
    """
    STDOUT reader for JSON format
    """
    out, err = capfd.readouterr()
    assert err == "", f"stderror output:\n{err}"

    records = out.strip().split("\n")
    try:
        return [json.loads(record) for record in records]
    except JSONDecodeError as error:
        return pytest.fail(
            "Invalid json log format. Change log format or read as plaint text.\n" f"log record: `{error.doc}`",
        )


def read_console_logs(capfd: CaptureFixture[str]) -> list[str]:
    """
    STDOUT reader for console format
    """
    out, err = capfd.readouterr()
    assert err == "", f"stderror output:\n{err}"

    records: list[str] = out.strip().split("\n")
    return records
