"""Emit the per-journal half of ``docs/specifications.md`` from ``SPECS``.

The specifications page restated every width, font size and accepted format by hand, which made it a
third copy of numbers that already live in ``_specs.py`` and in the generated stylesheets. At three
journals that was merely redundant; at fifteen it is a page that quietly stops matching the package.

Only the part above the hand-written sentinel is generated. The prose below it -- what the package
chooses for itself, and why -- is reasoning no generator can produce, and is preserved verbatim.

Regenerate after any spec change::

    python -m journalfig._docsgen

Author: Achraf Atila (achraf.atila@bam.de)
"""

from __future__ import annotations

from pathlib import Path

from ._specs import ALIASES, SOURCES, SPECS, JournalSpec

_DOCS_PAGE = Path(__file__).resolve().parents[2] / "docs" / "specifications.md"

#: Everything from this line down is hand-written and is copied through untouched.
SENTINEL = "<!-- HAND-WRITTEN BELOW THIS LINE."

_INTRO = """# Specifications

Every number in the themes is read from a publisher document. The pages below record which document, which
edition, and the date the numbers were last checked against it — a specification is only as trustworthy as
that date, because publishers revise their artwork guidelines without notice.

If you find a value that no longer matches what the publisher states, please
[open a specification correction](https://github.com/Atilaac/journalfig/issues/new?template=spec_correction.yml).
"""


def _formats(names: tuple[str, ...]) -> str:
    """Upper-case format names, folding the jpg/jpeg pair that means one thing to a reader."""
    seen: list[str] = []
    for name in names:
        label = "JPEG" if name.lower() in {"jpg", "jpeg"} else name.upper()
        if label not in seen:
            seen.append(label)
    return ", ".join(seen)


def _raster(spec: JournalSpec) -> str:
    """How the raster resolution reads, including the case of a publisher that states none."""
    if spec.raster_dpi is None:
        return "raster at the theme default; no minimum stated"
    return f"raster at {spec.raster_dpi} dpi"


def _faces(spec: JournalSpec) -> str:
    """The typefaces a publisher asks for, or a plain statement that it asks for none.

    AIP and Wiley name no typeface at all; joining an empty tuple left a dangling comma and trailing
    whitespace, which the pre-commit hook then stripped out from under the generator.
    """
    return ", ".join(spec.font_families) if spec.font_families else "no typeface stated"


def _section(key: str) -> str:
    """One journal's entry, in the layout the page has always used."""
    spec = SPECS[key]
    widths = ", ".join(f"{name} {value:.1f} mm" for name, value in sorted(spec.widths_mm.items()))
    aliases = ", ".join(sorted(name for name, target in ALIASES.items() if target == key))
    lines = [
        f"### {spec.name} (`{key}`)",
        "",
        f"- **Widths**: {widths}",
        f"- **Base font**: {spec.font_sizes['base']:g} pt, {_faces(spec)}",
        f"- **Panel labels**: `{spec.panel_label_fmt.format('a')}` at {spec.panel_label_pt:g} pt",
        f"- **`save()` writes**: {_formats(spec.formats)} ({_raster(spec)})",
        f"- **Accepted as final artwork**: {_formats(spec.submission_formats)}",
    ]
    source = SOURCES.get(key)
    if source is not None:
        edition = f", {source.version}" if source.version else ""
        lines.append(f"- **Source**: [{source.title}]({source.url}){edition} — retrieved {source.retrieved}")
    lines.append(f"- **Aliases**: {aliases}")
    return "\n".join(lines)


def specifications_text(tail: str) -> str:
    """Build the whole page: generated sections, then the hand-written tail unchanged.

    Args:
        tail: Everything from :data:`SENTINEL` onward, copied through verbatim.

    Returns:
        The full markdown page, ending in a newline.

    Example:
        >>> page = specifications_text("<!-- HAND-WRITTEN BELOW THIS LINE. -->\\n")
        >>> "### Nature Portfolio (`nature`)" in page
        True
    """
    blocks = [_INTRO.rstrip("\n")] + [_section(key) for key in SPECS]
    return "\n\n".join(blocks) + "\n\n" + tail


def read_tail(path: Path | None = None) -> str:
    """Return the hand-written part of the page, starting at the sentinel.

    Args:
        path: The page to read. Defaults to ``docs/specifications.md``.

    Returns:
        The tail, sentinel line included.

    Raises:
        ValueError: If the sentinel is missing, which would mean regenerating silently discards prose.

    Example:
        >>> import tempfile
        >>> with tempfile.TemporaryDirectory() as d:
        ...     page = Path(d) / "specifications.md"
        ...     _ = page.write_text(f"# Specifications\\n\\n{SENTINEL} -->\\n\\n## Choices\\n", encoding="utf-8")
        ...     read_tail(page).startswith(SENTINEL)
        True
    """
    text = (path or _DOCS_PAGE).read_text(encoding="utf-8")
    index = text.find(SENTINEL)
    if index < 0:
        raise ValueError(f"no {SENTINEL!r} marker; refusing to regenerate over hand-written prose")
    return text[index:]


def write_specifications(path: Path | None = None) -> Path:
    """Regenerate the page in place, preserving everything below the sentinel.

    Args:
        path: The page to rewrite. Defaults to ``docs/specifications.md``.

    Returns:
        The path written.

    Example:
        >>> import tempfile
        >>> with tempfile.TemporaryDirectory() as d:
        ...     page = Path(d) / "specifications.md"
        ...     _ = page.write_text(f"{SENTINEL} -->\\n\\n## Choices the package makes\\n", encoding="utf-8")
        ...     written = write_specifications(page)
        ...     "### Nature Portfolio" in written.read_text(encoding="utf-8")
        True
    """
    target = path or _DOCS_PAGE
    target.write_text(specifications_text(read_tail(target)), encoding="utf-8")
    return target


if __name__ == "__main__":
    print(f"wrote {write_specifications()}")
