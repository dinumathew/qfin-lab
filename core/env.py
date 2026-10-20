"""Library versions and the pinned specification."""
from __future__ import annotations

import platform
import sys
from importlib import metadata

PINNED = {
    "qiskit": "2.6.*",
    "qiskit-aer": "0.17.*",
    "qiskit-ibm-runtime": "any",
    "numpy": "any",
    "scipy": "any",
    "pandas": "any",
    "plotly": "any",
    "liboqs-python": "optional",
    "cryptography": "any",
    "sslyze": "optional",
    "pytest": "any",
    "streamlit": "any",
    "anthropic": "optional",
}


def _v(pkg: str) -> str | None:
    try:
        return metadata.version(pkg)
    except metadata.PackageNotFoundError:
        return None


def versions() -> dict:
    out = {"python": sys.version.split()[0], "platform": platform.platform()}
    for pkg in PINNED:
        out[pkg] = _v(pkg)
    return out


def pin_ok(pkg: str, installed: str | None) -> bool | None:
    spec = PINNED.get(pkg)
    if installed is None:
        return None if spec == "optional" else False
    if spec in ("any", "optional"):
        return True
    prefix = spec.rstrip("*").rstrip(".")
    return installed == prefix or installed.startswith(prefix + ".")
