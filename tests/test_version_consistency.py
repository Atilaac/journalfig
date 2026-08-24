"""Every file that writes the version must agree with ``journalfig.__version__``.

The version is not stored in one place. ``pyproject.toml`` reads it out of ``__init__.py``, but
``CITATION.cff`` carries its own copy, the ``journalfigs`` alias package carries another, and the eight
example notebooks bake it into their stored output -- which the documentation site renders verbatim,
because mkdocs-jupyter is configured not to execute them.

``.github/workflows/version-bump.yml`` rewrites all of them, so in normal operation they cannot drift.
This test is what makes that a verified claim rather than a promise: it fails when a release misses a
file, and, more usefully, when someone adds a *new* place the version is written and forgets to teach the
workflow about it. Both failures are otherwise silent -- the package still imports, the suite still
passes, and only a reader of the published docs or the citation panel ever notices.

Author: Achraf Atila (achraf.atila@bam.de)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import journalfig

_ROOT = Path(__file__).resolve().parents[1]
_NOTEBOOKS = sorted((_ROOT / "examples").glob("*.ipynb"))

#: Each entry is a file and the pattern whose first capture group must be the current version. Adding a
#: version to a new file means adding it here *and* to version-bump.yml; this list is the checklist.
_SITES: list[tuple[str, str]] = [
    ("src/journalfig/__init__.py", r'^__version__ = "([^"]+)"'),
    ("CITATION.cff", r"^version: (.+)$"),
    ("packaging/journalfigs/pyproject.toml", r'^version = "([^"]+)"'),
]


@pytest.mark.parametrize(("relative_path", "pattern"), _SITES, ids=[path for path, _ in _SITES])
def test_the_file_carries_the_current_version(relative_path: str, pattern: str) -> None:
    text = (_ROOT / relative_path).read_text(encoding="utf-8")
    found = re.search(pattern, text, flags=re.M)
    assert found is not None, f"{relative_path}: no version matched {pattern!r}"
    assert found.group(1).strip() == journalfig.__version__, (
        f"{relative_path} says {found.group(1).strip()!r}, journalfig.__version__ is {journalfig.__version__!r}"
    )


def test_there_are_notebooks_to_check() -> None:
    # A glob that silently matches nothing would make the test below vacuously pass.
    assert _NOTEBOOKS, "no notebooks found in examples/"


@pytest.mark.parametrize("notebook", _NOTEBOOKS, ids=lambda path: path.name)
def test_notebook_output_does_not_advertise_an_old_version(notebook: Path) -> None:
    # Read as JSON rather than as text: a version inside a *source* cell is a different problem from one
    # frozen into stored output, and only the latter is what the docs site publishes.
    cells = json.loads(notebook.read_text(encoding="utf-8"))["cells"]
    printed = [
        version
        for cell in cells
        for output in cell.get("outputs", [])
        for line in output.get("text", [])
        for version in re.findall(r"journalfig (\d+\.\d+\.\d+)", line)
    ]
    stale = sorted({version for version in printed if version != journalfig.__version__})
    assert not stale, (
        f"{notebook.name} has stored output naming journalfig {stale}, but the current version is "
        f"{journalfig.__version__}. Re-run version-bump.yml's rewrite, or re-execute the notebook."
    )
