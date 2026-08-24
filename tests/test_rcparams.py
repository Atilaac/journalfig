"""Frozen snapshot of the rcParams each theme resolves to.

The themes are about to be refactored so that ``SPECS`` drives the stylesheets rather than duplicating
them. That refactor is only safe if it changes nothing a figure can see, and the image baselines cannot
prove it here: they compare pixels only on FreeType 2.6.1, and skip on any other build. This file is the
substitute instrument. It records the fully resolved value of every rcParam the stylesheets set, so a
refactor that alters one is a test failure naming the key rather than a silent change in every figure.

Regenerate deliberately, never to make a failure go away::

    PYTHONPATH=src python tests/test_rcparams.py

Author: Achraf Atila (achraf.atila@bam.de)
"""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import matplotlib.style as mplstyle
import pytest
from cycler import Cycler

import journalfig as jf

REFERENCE_PATH = Path(__file__).parent / "rcparams_reference.json"


def _normalise(value: Any) -> Any:
    """Reduce an rcParam value to something JSON can hold and compare exactly."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Cycler):
        return {key: [_normalise(v) for v in values] for key, values in sorted(value.by_key().items())}
    if isinstance(value, (list, tuple)):
        return [_normalise(item) for item in value]
    return repr(value)


def _resolved(journal: str, keys: list[str]) -> dict[str, Any]:
    """Apply a theme and read back the resolved value of each key."""
    saved = plt.rcParams.copy()
    try:
        jf.use(journal)
        return {key: _normalise(plt.rcParams[key]) for key in keys}
    finally:
        plt.rcParams.update(saved)


def _style_keys() -> list[str]:
    """Every rcParam any theme sets, which is exactly what the themes are responsible for."""
    keys: set[str] = set()
    for journal in jf.JOURNALS:
        keys |= set(mplstyle.library[journal])
    return sorted(keys)


@pytest.mark.parametrize("journal", jf.JOURNALS)
def test_resolved_rcparams_match_reference(journal):
    reference = json.loads(REFERENCE_PATH.read_text())
    assert journal in reference, f"no reference for {journal!r}; regenerate tests/rcparams_reference.json"

    expected = reference[journal]
    actual = _resolved(journal, sorted(expected))
    drifted = {key: (expected[key], actual[key]) for key in expected if expected[key] != actual[key]}
    assert not drifted, "\n".join(f"{key}: reference {was!r} -> now {now!r}" for key, (was, now) in drifted.items())


def test_reference_covers_every_key_the_themes_set():
    """A theme that starts setting a new rcParam must be re-snapshotted, or the guard has a hole."""
    reference = json.loads(REFERENCE_PATH.read_text())
    for journal in jf.JOURNALS:
        missing = set(_style_keys()) - set(reference.get(journal, {}))
        assert not missing, f"{journal} sets un-snapshotted rcParams: {sorted(missing)}"


if __name__ == "__main__":
    keys = _style_keys()
    snapshot = {journal: _resolved(journal, keys) for journal in jf.JOURNALS}
    REFERENCE_PATH.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n")
    print(f"wrote {REFERENCE_PATH} — {len(jf.JOURNALS)} themes x {len(keys)} rcParams")
