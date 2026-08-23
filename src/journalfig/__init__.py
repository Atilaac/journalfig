"""Publication-ready matplotlib themes for twelve scientific publishers.

Each theme encodes the figure requirements the publisher actually documents -- column widths, font
sizes, panel label conventions, minimum line weights, and accepted file formats -- so a figure can be
retargeted from one journal to another by changing a single string.

Example:
    >>> import matplotlib.pyplot as plt
    >>> import journalfig as jf
    >>> jf.use("elsevier")
    >>> fig, ax = plt.subplots(figsize=jf.figsize("elsevier", "single"))
    >>> _ = ax.plot([1, 2, 3], [1, 4, 9], label=r"$S(q)$")

Author: Achraf Atila (achraf.atila@bam.de)
"""

from ._core import (
    GOLDEN,
    VECTOR_ELEMENT_LIMIT,
    FontStatus,
    JournalFigWarning,
    Violation,
    active,
    check,
    context,
    figsize,
    figure,
    fonts,
    gridspec,
    label_lines,
    mosaic,
    panel_labels,
    register,
    save,
    style_file,
    subplots,
    use,
)
from ._specs import (
    COLOR_CYCLE,
    COLORS,
    JOURNALS,
    LINESTYLE_CYCLE,
    MARKER_CYCLE,
    SOURCES,
    SPECS,
    JournalSpec,
    Source,
    ThemeStyle,
    get_spec,
    mm_to_inch,
    resolve,
    source,
)

__version__ = "0.1.0"

__all__ = [
    "COLORS",
    "COLOR_CYCLE",
    "GOLDEN",
    "VECTOR_ELEMENT_LIMIT",
    "JOURNALS",
    "LINESTYLE_CYCLE",
    "MARKER_CYCLE",
    "SOURCES",
    "SPECS",
    "FontStatus",
    "JournalSpec",
    "JournalFigWarning",
    "Source",
    "ThemeStyle",
    "Violation",
    "active",
    "check",
    "context",
    "figsize",
    "figure",
    "fonts",
    "get_spec",
    "gridspec",
    "label_lines",
    "mm_to_inch",
    "mosaic",
    "panel_labels",
    "register",
    "resolve",
    "save",
    "source",
    "style_file",
    "subplots",
    "use",
]

register()
