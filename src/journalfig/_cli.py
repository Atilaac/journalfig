"""Command line entry point: check figures against a publisher's requirements.

``check()`` is the part of this package no stylesheet collection offers, and until now it was reachable
only from Python, by someone who had already adopted the themes. This exposes it to a shell and to CI,
so a paper repository can fail its build on a figure that would be bounced at submission -- whatever
drew the figure.

Nothing here parses a saved file. A matplotlib ``Figure`` cannot be reconstructed from a PDF, so
"checking a PDF" is a different and much narrower question (page geometry, embedded fonts) that this
does not pretend to answer. The target is Python that builds figures.

Author: Achraf Atila (achraf.atila@bam.de)
"""

from __future__ import annotations

import argparse
import importlib
import runpy
import sys
import warnings
from collections.abc import Iterable, Sequence
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # noqa: E402  -- before pyplot, so no target can open a window

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from ._core import JournalFigWarning, Violation, check  # noqa: E402
from ._specs import (  # noqa: E402
    JOURNALS,
    MM_PER_INCH,  # noqa: E402
    SPECS,
)

#: Returned when the target could not be loaded at all, as distinct from loading and failing the check.
EXIT_ERROR = 2


def _as_figures(value: object) -> list[Figure]:
    """Pull every figure out of whatever a target handed back.

    Accepts a figure, the ``(fig, ax)`` pair ``plt.subplots`` returns, or any iterable mixing the two.

    Args:
        value: The return value of a called target.

    Returns:
        The figures found, in order, without duplicates.

    Example:
        >>> fig = plt.figure()
        >>> len(_as_figures((fig, "axes-go-here")))
        1
        >>> plt.close(fig)
    """
    found: list[Figure] = []
    stack = [value]
    while stack:
        item = stack.pop(0)
        if isinstance(item, Figure):
            if item not in found:
                found.append(item)
        elif isinstance(item, (list, tuple)):
            stack = list(item) + stack
    return found


def load_figures(target: str) -> list[Figure]:
    """Run a target and collect the figures it produced.

    Two forms. A path to a Python file is executed, and every figure left open afterwards is
    collected -- which is what a plotting script produces without being written to return anything.
    A ``module:callable`` string imports the module and calls the attribute, collecting whatever it
    returns as well as anything it left open.

    Args:
        target: A path to a ``.py`` file, or ``"package.module:function"``.

    Returns:
        The figures found, in creation order.

    Raises:
        SystemExit: If the target cannot be imported, found, or called.

    Example:
        >>> import tempfile
        >>> script = "import matplotlib.pyplot as plt\\nplt.figure()\\n"
        >>> with tempfile.TemporaryDirectory() as d:
        ...     path = Path(d) / "make.py"
        ...     _ = path.write_text(script, encoding="utf-8")
        ...     len(load_figures(str(path)))
        1
        >>> plt.close("all")
    """
    plt.close("all")
    returned: object = None
    with warnings.catch_warnings():
        # The target may itself call save() or check(); we are about to report properly, so its own
        # compliance warnings would only duplicate what the table below says.
        warnings.simplefilter("ignore", JournalFigWarning)
        try:
            if ":" in target and not target.endswith(".py"):
                module_name, _, attribute = target.partition(":")
                module = importlib.import_module(module_name)
                returned = getattr(module, attribute)()
            else:
                path = Path(target)
                if not path.is_file():
                    raise SystemExit(f"journalfig: no such file: {target}")
                runpy.run_path(str(path), run_name="__journalfig__")
        except SystemExit:
            raise
        except (ImportError, AttributeError) as exc:
            raise SystemExit(f"journalfig: could not load {target!r}: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 -- the target is arbitrary user code
            raise SystemExit(f"journalfig: {target!r} raised {type(exc).__name__}: {exc}") from exc

    open_figures = [plt.figure(num) for num in plt.get_fignums()]
    collected = _as_figures(returned)
    return collected + [fig for fig in open_figures if fig not in collected]


def _describe(fig: Figure, index: int) -> str:
    """One heading line naming a figure and its size in millimetres."""
    width_mm, height_mm = (value * MM_PER_INCH for value in fig.get_size_inches())
    label = fig.get_label() or f"figure {index}"
    return f"{label}  ({width_mm:.1f} x {height_mm:.1f} mm)"


def report(figures: Iterable[Figure], journal: str | None) -> tuple[str, int]:
    """Render the violation table for a set of figures.

    Args:
        figures: The figures to check.
        journal: Theme key or alias, or ``None`` to use the active theme.

    Returns:
        ``(text, violation_count)``.

    Example:
        >>> fig = plt.figure(figsize=(3.503937, 2.165552))
        >>> text, count = report([fig], "nature")
        >>> count
        0
        >>> plt.close(fig)
    """
    lines: list[str] = []
    total = 0
    for index, fig in enumerate(figures, start=1):
        violations: list[Violation] = check(fig, journal=journal, warn=False)
        total += len(violations)
        if violations:
            lines.append(f"{_describe(fig, index)}")
            lines += [f"  [{v.kind}] {v.message}" for v in violations]
        else:
            lines.append(f"{_describe(fig, index)}  OK")
    return "\n".join(lines), total


def _build_parser() -> argparse.ArgumentParser:
    """The argument parser, split out so the tests can exercise it without running anything."""
    parser = argparse.ArgumentParser(
        prog="journalfig",
        description="Check matplotlib figures against a publisher's stated figure requirements.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    checker = sub.add_parser("check", help="check the figures a script or callable produces")
    checker.add_argument("target", help="path to a .py file, or package.module:function")
    checker.add_argument(
        "-j",
        "--journal",
        help=f"theme key or journal alias (default: the active theme). One of: {', '.join(JOURNALS)}",
    )

    sub.add_parser("journals", help="list the themes this build knows about")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line interface.

    Args:
        argv: Arguments to parse. Defaults to ``sys.argv[1:]``.

    Returns:
        ``0`` when every figure complies, ``1`` when any violation was found, and
        :data:`EXIT_ERROR` when the target could not be loaded.
    """
    args = _build_parser().parse_args(argv)

    if args.command == "journals":
        for key in sorted(SPECS):
            print(f"{key:<12} {SPECS[key].name}")
        return 0

    try:
        figures = load_figures(args.target)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return EXIT_ERROR

    if not figures:
        print(f"journalfig: {args.target} produced no figures", file=sys.stderr)
        return EXIT_ERROR

    try:
        text, total = report(figures, args.journal)
    except (RuntimeError, KeyError) as exc:
        # str(KeyError) wraps its message in quotes; the message is already a sentence.
        message = exc.args[0] if isinstance(exc, KeyError) and exc.args else exc
        print(f"journalfig: {message}", file=sys.stderr)
        return EXIT_ERROR

    print(text)
    noun = "violation" if total == 1 else "violations"
    print(f"\n{len(figures)} figure(s), {total} {noun}")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
