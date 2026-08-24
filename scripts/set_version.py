"""Write a version into every file that carries one.

The version has no single home. ``pyproject.toml`` reads it out of ``__init__.py`` via
``[tool.hatch.version]``, but ``CITATION.cff`` keeps its own copy for GitHub's citation panel, the
``journalfigs`` alias package keeps another, and the example notebooks bake it into stored output that
the documentation site renders verbatim -- mkdocs-jupyter is configured not to execute them.

``.github/workflows/version-bump.yml`` calls this during a release. It lives here rather than inline in
that workflow so the same code path can be run by hand, and so ``tests/test_version_consistency.py``
checks the result of something executable rather than of a shell snippet nobody can run locally.

    python scripts/set_version.py 0.4.0

Author: Achraf Atila (achraf.atila@bam.de)
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _replace(relative_path: str, pattern: str, replacement: str, *, expected: int | None = 1) -> int:
    """Substitute in one file, asserting how many times it matched.

    A silent no-op is the failure worth guarding against: it would produce a release pull request that
    changes nothing, tag a version the package does not report, and only surface in publish.yml long
    after the release notes are public. ``expected=None`` allows any count, for files that legitimately
    may not mention the version at all.
    """
    path = ROOT / relative_path
    text = path.read_text(encoding="utf-8")
    new, count = re.subn(pattern, replacement, text, flags=re.M)
    if expected is not None and count != expected:
        sys.exit(f"{relative_path}: {pattern!r} matched {count} times, expected {expected}")
    if new != text:
        path.write_text(new, encoding="utf-8")
    print(f"  {relative_path}: {count} substitution(s)")
    return count


def set_version(version: str, *, released: datetime.date | None = None) -> None:
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        sys.exit(f"refusing to write a version that is not X.Y.Z: {version!r}")
    released = released or datetime.date.today()

    print(f"Setting version {version}")
    _replace("src/journalfig/__init__.py", r'^__version__ = "[^"]+"', f'__version__ = "{version}"')
    _replace("CITATION.cff", r"^version: .+$", f"version: {version}")
    _replace("CITATION.cff", r"^date-released: .+$", f"date-released: {released}")
    _replace("packaging/journalfigs/pyproject.toml", r'^version = "[^"]+"', f'version = "{version}"')

    # Stored notebook output, not source. Rewriting the frozen string avoids re-executing the notebooks,
    # which would also rewrite every embedded figure PNG -- none of which reproduce byte-for-byte across
    # platforms, so the diff would be enormous and meaningless.
    for notebook in sorted((ROOT / "examples").glob("*.ipynb")):
        _replace(
            f"examples/{notebook.name}",
            r"journalfig \d+\.\d+\.\d+",
            f"journalfig {version}",
            expected=None,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="the version to write, as X.Y.Z")
    set_version(parser.parse_args().version)


if __name__ == "__main__":
    main()
