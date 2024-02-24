import sys

__all__ = ("test_python_version",)


def test_python_version() -> None:
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    assert version in ("3.10", "3.11", "3.12")
