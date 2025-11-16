"""Metamodel to OWL conversion utilities."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("metamodel2owl")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"

__all__ = ["__version__"]
