"""Helpers available inside every code cell and lab.

    from qlab_helpers import SEED, rng, show, record, table

- SEED   : the seed shown in the UI (default 1234). Use it everywhere.
- rng    : numpy Generator seeded with SEED.
- show   : display a plotly figure in the app.
- record : save a named output (number, list, dict) into the run record (JSON export).
- table  : display a pandas DataFrame in the app.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

SEED = int(os.environ.get("QLAB_SEED", "1234"))
rng = np.random.default_rng(SEED)
_OUT = Path(os.environ.get("QLAB_OUT", ".qlab_out"))
_OUT.mkdir(parents=True, exist_ok=True)
_counter = {"fig": 0, "tab": 0}


def _jsonable(v):
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    if isinstance(v, np.ndarray):
        return v.tolist()
    if isinstance(v, complex):
        return [v.real, v.imag]
    if isinstance(v, dict):
        return {str(k): _jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    return v


def show(fig) -> None:
    _counter["fig"] += 1
    (_OUT / f"fig_{_counter['fig']:03d}.json").write_text(fig.to_json())


def table(df, name: str | None = None) -> None:
    _counter["tab"] += 1
    (_OUT / f"tab_{_counter['tab']:03d}.json").write_text(
        json.dumps({"name": name, "data": df.to_json(orient="split")})
    )


def record(name: str, value) -> None:
    path = _OUT / "record.json"
    data = json.loads(path.read_text()) if path.exists() else {}
    data[name] = _jsonable(value)
    path.write_text(json.dumps(data, indent=2))
