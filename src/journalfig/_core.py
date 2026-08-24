"""Theme application, figure sizing, compliance checking, and export.

Author: Achraf Atila (achraf.atila@bam.de)
"""

from __future__ import annotations

import logging
import warnings
from collections.abc import Hashable, Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from math import isfinite, sqrt
from pathlib import Path
from string import ascii_lowercase
from typing import TYPE_CHECKING, Any, cast
from weakref import WeakKeyDictionary

import matplotlib.pyplot as plt
from matplotlib import rc_params_from_file
from matplotlib import style as mplstyle
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties, findfont
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D
from matplotlib.text import Text
from matplotlib.textpath import TextPath

if TYPE_CHECKING:
    from matplotlib.typing import HashableList

from ._specs import (
    GOLDEN,
    MATHTEXT_SHRINK,
    MM_PER_INCH,
    PT_PER_MM,
    JournalSpec,
    get_spec,
    mm_to_inch,
    resolve,
)

#: Reports what was written and at what size, at INFO level. Silent unless the application configures
#: logging; ``logging.getLogger("journalfig").setLevel("INFO")`` surfaces it without also switching on
#: ``fontTools``, which logs a dozen subsetting lines per PDF.
_LOG = logging.getLogger(__name__)


class JournalFigWarning(UserWarning):
    """Warning raised for a figure that departs from a publisher's requirements.

    A dedicated class so these can be filtered without silencing every other ``UserWarning``:
    ``warnings.filterwarnings("ignore", category=journalfig.JournalFigWarning)``.
    """


#: Element count above which an un-rasterized artist makes a vector file impractically large. Well past
#: what an ordinary plot produces: a 200x200 mesh is 40,000 cells, a busy scatter a few thousand points.
VECTOR_ELEMENT_LIMIT = 50_000

#: gid stamped on panel labels so :func:`check` can exempt them from the body-text limits.
PANEL_LABEL_GID = "journalfig-panel-label"

#: Formats that carry a resolution, and so can fall below a publisher's dpi floor. A vector format has
#: no pixels to count, which is why an explicit dpi is meaningless rather than non-compliant for one.
_RASTER_FORMATS = frozenset({"png", "tif", "tiff", "jpg", "jpeg"})

_STYLE_DIR = Path(__file__).parent / "styles"

#: Settings every theme shares, applied beneath each journal's generated overlay. Hand-written.
_BASE_STYLE = _STYLE_DIR / "_base.mplstyle"

_ACTIVE: str | None = None

#: Exact requested sizes, so :func:`save` can undo backend pixel rounding. Keyed weakly so
#: closing a figure releases it.
_PINNED: WeakKeyDictionary[Figure, tuple[float, float]] = WeakKeyDictionary()

_FONT_SIZE_KEYS = (
    "font.size",
    "axes.labelsize",
    "axes.titlesize",
    "xtick.labelsize",
    "ytick.labelsize",
    "legend.fontsize",
    "legend.title_fontsize",
    "figure.titlesize",
)

#: LaTeX preamble per font category, not per journal. There were only ever two -- a sans theme wants
#: helvet with sansmath so maths matches the labels, a serif theme wants mathptmx for Times maths -- and
#: keying them by journal meant a new theme raised KeyError the first time anyone passed usetex=True.
_USETEX_BY_CATEGORY = {
    "sans-serif": r"\usepackage[T1]{fontenc}"
    r"\usepackage{helvet}"
    r"\renewcommand{\familydefault}{\sfdefault}"
    r"\usepackage{amsmath}\usepackage{amssymb}"
    r"\usepackage{sansmath}\sansmath",
    "serif": r"\usepackage[T1]{fontenc}\usepackage{mathptmx}\usepackage{amsmath}\usepackage{amssymb}",
}


def _usetex_preamble(spec: JournalSpec) -> str:
    """The LaTeX preamble a theme needs, chosen by whether it sets sans or serif."""
    return _USETEX_BY_CATEGORY[spec.style.font_family_category]


def style_file(journal: str) -> Path:
    """Return the path to a theme's ``.mplstyle`` file.

    Args:
        journal: Theme key or journal alias.

    Returns:
        Path to the style file shipped with the package.

    Example:
        >>> style_file("prb").name
        'aps.mplstyle'
    """
    return _STYLE_DIR / f"{resolve(journal)}.mplstyle"


def register() -> None:
    """Add the bundled themes to matplotlib's in-process style library.

    Makes ``plt.style.use("nature")`` work without going through :func:`use`. This only touches the
    running interpreter; nothing is written to ``~/.matplotlib/stylelib``.

    Example:
        >>> register()
        >>> "nature" in plt.style.available
        True
    """
    base = rc_params_from_file(_BASE_STYLE, use_default_template=False)
    for path in sorted(_STYLE_DIR.glob("*.mplstyle")):
        # A leading underscore marks a fragment, not a theme: _base.mplstyle is applied beneath every
        # overlay rather than offered to matplotlib as a style of its own.
        if path.name.startswith("_"):
            continue
        # RcParams.copy() rather than dict(base): matplotlib's style library holds RcParams, and a plain
        # dict works only because nothing downcasts it.
        merged = base.copy()
        merged.update(rc_params_from_file(path, use_default_template=False))
        mplstyle.library[path.stem] = merged
    mplstyle.available[:] = sorted(mplstyle.library)


def active() -> str | None:
    """Return the theme key applied by the most recent :func:`use` call.

    Returns:
        The active theme key, or ``None`` if no theme has been applied.

    Example:
        >>> use("nature")
        >>> active()
        'nature'
    """
    return _ACTIVE


def _scale_fonts(factor: float) -> None:
    for key in _FONT_SIZE_KEYS:
        try:
            plt.rcParams[key] = float(plt.rcParams[key]) * factor
        except (TypeError, ValueError):
            continue


def use(journal: str, *, usetex: bool = False, base_size: float | None = None) -> None:
    """Apply a journal theme to the global matplotlib state.

    Args:
        journal: Theme key (``"nature"``, ``"aps"``, ``"elsevier"``) or a journal alias
            such as ``"Acta Materialia"`` or ``"PRB"``.
        usetex: Render text with the system LaTeX installation instead of mathtext. Slower, and
            requires ``latex`` plus ``dvipng`` on ``PATH``. The APS preamble uses ``mathptmx`` for
            Times maths, which needs matplotlib >= 3.10 on TeX installations whose ``pdftex.map``
            carries no Type 1 entry for it; on 3.8 and 3.9 the same setup raises ``LookupError`` at
            save time. Nature and Elsevier are unaffected.
        base_size: Override the theme's base font size in points; every other font size is scaled
            by the same factor. Useful for maths-heavy Elsevier figures, where the publisher's
            6 pt sub/superscript floor needs a base of at least 8.6 pt.

    Example:
        >>> use("elsevier", base_size=9)
        >>> plt.rcParams["font.size"]
        9.0
    """
    global _ACTIVE
    key = resolve(journal)
    spec = get_spec(key)
    # Base first, then the journal's overlay on top: the overlay carries only what differs.
    plt.style.use([str(_BASE_STYLE), str(style_file(key))])

    if base_size is not None:
        _scale_fonts(float(base_size) / spec.font_sizes["base"])

    if usetex:
        plt.rcParams["text.usetex"] = True
        plt.rcParams["text.latex.preamble"] = _usetex_preamble(spec)

    _ACTIVE = key


@contextmanager
def context(journal: str, **kwargs: Any) -> Iterator[None]:
    """Apply a theme temporarily, restoring the previous rcParams on exit.

    Args:
        journal: Theme key or journal alias.
        **kwargs: Forwarded to :func:`use`.

    Yields:
        ``None``, with the theme active for the duration of the block.

    Example:
        >>> plt.rcParams["font.size"] = 11.0
        >>> with context("nature"):
        ...     pass
        >>> plt.rcParams["font.size"]
        11.0
    """
    global _ACTIVE
    saved = plt.rcParams.copy()
    saved_active = _ACTIVE
    try:
        use(journal, **kwargs)
        yield
    finally:
        plt.rcParams.update(saved)
        _ACTIVE = saved_active


def figsize(
    journal: str,
    width: str | float = "single",
    *,
    ratio: float = GOLDEN,
    height_mm: float | None = None,
) -> tuple[float, float]:
    """Return an exact figure size in inches for a journal column width.

    Args:
        journal: Theme key or journal alias.
        width: A layout name from the journal's spec (``"single"``, ``"onehalf"``, ``"double"``,
            and for Nature also ``"onehalf_wide"``), or an explicit width in millimetres.
        ratio: Height divided by width. Defaults to the inverse golden ratio.
        height_mm: Explicit height in millimetres, overriding ``ratio``.

    Returns:
        ``(width_inches, height_inches)``.

    Raises:
        KeyError: If ``width`` names a layout the journal does not define.

    Example:
        >>> tuple(round(v, 4) for v in figsize("nature", "single"))
        (3.5039, 2.1656)
        >>> tuple(round(v, 4) for v in figsize("aps", "double", ratio=0.4))
        (7.0, 2.8)
    """
    spec = get_spec(journal)
    if isinstance(width, str):
        if width not in spec.widths_mm:
            raise KeyError(f"{spec.name} has no width {width!r}; available: {sorted(spec.widths_mm)}")
        width_mm = spec.widths_mm[width]
    else:
        width_mm = float(width)

    if spec.min_width_mm is not None and width_mm < spec.min_width_mm:
        warnings.warn(
            f"{width_mm:.1f} mm is below the {spec.name} minimum of {spec.min_width_mm:.0f} mm",
            category=JournalFigWarning,
            stacklevel=2,
        )

    h_mm = height_mm if height_mm is not None else width_mm * ratio
    if spec.max_height_mm is not None and h_mm > spec.max_height_mm:
        warnings.warn(
            f"height {h_mm:.1f} mm exceeds the {spec.name} maximum of {spec.max_height_mm:.0f} mm; clamping",
            category=JournalFigWarning,
            stacklevel=2,
        )
        h_mm = spec.max_height_mm

    return mm_to_inch(width_mm), mm_to_inch(h_mm)


def _pin_size(fig: Figure, size: tuple[float, float]) -> None:
    """Force an exact figure size and remember it.

    Interactive backends (``macosx``, Qt, Tk) round a figure to whole device pixels when it is
    created, which turns a 183.0 mm Nature figure into 182.88 mm. Re-applying the size with
    ``forward=False`` skips the canvas round-trip and restores the requested value exactly.
    """
    fig.set_size_inches(*size, forward=False)
    _PINNED[fig] = size


def figure(
    journal: str,
    width: str | float = "single",
    *,
    ratio: float = GOLDEN,
    height_mm: float | None = None,
    **kwargs: Any,
) -> Figure:
    """Create a figure at an exact journal column width.

    Prefer this over ``plt.figure(figsize=figsize(...))``: it survives the pixel rounding that
    interactive backends apply, and it records the requested size so :func:`save` can re-assert it.

    Args:
        journal: Theme key or journal alias.
        width: Layout name or an explicit width in millimetres.
        ratio: Height divided by width.
        height_mm: Explicit height in millimetres, overriding ``ratio``.
        **kwargs: Forwarded to ``plt.figure``.

    Returns:
        The new figure, sized exactly.

    Example:
        >>> use("nature")
        >>> round(float(figure("nature", "double").get_size_inches()[0]) * 25.4, 4)
        183.0
    """
    size = figsize(journal, width, ratio=ratio, height_mm=height_mm)
    fig = plt.figure(figsize=size, **kwargs)
    _pin_size(fig, size)
    return fig


def subplots(
    journal: str,
    nrows: int = 1,
    ncols: int = 1,
    *,
    width: str | float = "single",
    ratio: float = GOLDEN,
    height_mm: float | None = None,
    **kwargs: Any,
) -> tuple[Figure, Any]:
    """Create a figure and axes grid at an exact journal column width.

    Args:
        journal: Theme key or journal alias.
        nrows: Number of subplot rows.
        ncols: Number of subplot columns.
        width: Layout name or an explicit width in millimetres.
        ratio: Height divided by width.
        height_mm: Explicit height in millimetres, overriding ``ratio``.
        **kwargs: Forwarded to ``plt.subplots``.

    Returns:
        ``(figure, axes)``, exactly as ``plt.subplots`` returns them.

    Example:
        >>> use("elsevier")
        >>> fig, axs = subplots("elsevier", 2, 2, width="double")
        >>> round(float(fig.get_size_inches()[0]) * 25.4, 4)
        190.0
    """
    size = figsize(journal, width, ratio=ratio, height_mm=height_mm)
    fig, axes = plt.subplots(nrows, ncols, figsize=size, **kwargs)
    _pin_size(fig, size)
    return fig, axes


def _merge_ratios(
    kwargs: dict[str, Any],
    width_ratios: Sequence[float] | None,
    height_ratios: Sequence[float] | None,
) -> dict[str, object]:
    """Fold explicit row/column ratios into a ``gridspec_kw`` mapping."""
    merged: dict[str, Any] = dict(kwargs.pop("gridspec_kw", None) or {})
    if width_ratios is not None:
        merged["width_ratios"] = list(width_ratios)
    if height_ratios is not None:
        merged["height_ratios"] = list(height_ratios)
    return merged


def mosaic(
    journal: str,
    layout: str | HashableList[Hashable],
    *,
    width: str | float = "single",
    ratio: float = GOLDEN,
    height_mm: float | None = None,
    width_ratios: Sequence[float] | None = None,
    height_ratios: Sequence[float] | None = None,
    **kwargs: Any,
) -> tuple[Figure, dict[str, Axes]]:
    """Create panels of unequal size from an ASCII sketch of the layout.

    Each cell of the sketch names the panel that occupies it; repeating a name over neighbouring
    cells makes that panel span them, and ``"."`` leaves a cell empty. ``width_ratios`` and
    ``height_ratios`` then set how large the underlying grid's columns and rows are relative to each
    other, so panels need not be multiples of one cell size.

    Args:
        journal: Theme key or journal alias.
        layout: Panel layout, either a multi-line string with one character per cell or nested lists
            of panel names (use lists for names longer than one character).
        width: Layout name or an explicit width in millimetres.
        ratio: Height divided by width. Layouts of more than one row usually need a value well above
            the default inverse golden ratio.
        height_mm: Explicit height in millimetres, overriding ``ratio``.
        width_ratios: Relative widths of the grid columns; one entry per column.
        height_ratios: Relative heights of the grid rows; one entry per row.
        **kwargs: Forwarded to ``plt.subplot_mosaic``, e.g. ``sharex`` or ``per_subplot_kw``.

    Returns:
        ``(figure, panels)``, where ``panels`` maps each name in the sketch to its axes, in the
        order the names first appear when reading the sketch left to right, top to bottom.

    Example:
        >>> use("nature")
        >>> fig, panels = mosaic("nature", "AAB\\nCCB", width="double", width_ratios=[1, 1, 1.4])
        >>> list(panels)
        ['A', 'B', 'C']
        >>> round(float(fig.get_size_inches()[0]) * 25.4, 4)
        183.0
    """
    size = figsize(journal, width, ratio=ratio, height_mm=height_mm)
    gridspec_kw = _merge_ratios(kwargs, width_ratios, height_ratios)
    # mypy cannot match a union against subplot_mosaic's overload set: it has one overload for str and
    # one for the nested-list form, and no overload accepting either. Both members are individually
    # valid, which is what the annotation documents.
    fig, panels = plt.subplot_mosaic(
        layout,  # type: ignore[arg-type]
        figsize=size,
        gridspec_kw=gridspec_kw or None,
        **kwargs,
    )
    _pin_size(fig, size)
    return fig, panels


def gridspec(
    journal: str,
    nrows: int = 1,
    ncols: int = 1,
    *,
    width: str | float = "single",
    ratio: float = GOLDEN,
    height_mm: float | None = None,
    width_ratios: Sequence[float] | None = None,
    height_ratios: Sequence[float] | None = None,
    **kwargs: Any,
) -> tuple[Figure, GridSpec]:
    """Create a figure and an empty grid to place spanning panels on by hand.

    Use this when a layout is easier to express as slices than as a sketch -- a panel spanning
    columns 0 and 1 of row 0 is ``fig.add_subplot(gs[0, :2])``. For anything that fits in a sketch,
    :func:`mosaic` is shorter. Both size the figure identically.

    Args:
        journal: Theme key or journal alias.
        nrows: Number of grid rows.
        ncols: Number of grid columns.
        width: Layout name or an explicit width in millimetres.
        ratio: Height divided by width.
        height_mm: Explicit height in millimetres, overriding ``ratio``.
        width_ratios: Relative widths of the grid columns; one entry per column.
        height_ratios: Relative heights of the grid rows; one entry per row.
        **kwargs: Forwarded to ``Figure.add_gridspec``.

    Returns:
        ``(figure, gridspec)``. The grid holds no axes until you add them.

    Example:
        >>> use("aps")
        >>> fig, gs = gridspec("aps", 2, 3, width="double", height_ratios=[1, 1.5])
        >>> wide = fig.add_subplot(gs[0, :2])
        >>> tall = fig.add_subplot(gs[:, 2])
        >>> gs.get_geometry()
        (2, 3)
    """
    size = figsize(journal, width, ratio=ratio, height_mm=height_mm)
    fig = plt.figure(figsize=size)
    grid = fig.add_gridspec(
        nrows,
        ncols,
        width_ratios=list(width_ratios) if width_ratios is not None else None,
        height_ratios=list(height_ratios) if height_ratios is not None else None,
        **kwargs,
    )
    _pin_size(fig, size)
    return fig, grid


def panel_labels(
    axes: Iterable[Axes] | Axes,
    *,
    journal: str | None = None,
    fmt: str | None = None,
    labels: Iterable[str] | None = None,
    dx: float = -16.0,
    dy: float = 3.0,
    weight: str = "bold",
    size: float | None = None,
    **kwargs: Any,
) -> list[Text]:
    """Add journal-styled panel labels to a set of axes.

    Nature wants bare lowercase letters (``a``, ``b``); APS and Elsevier want parentheses
    (``(a)``, ``(b)``). The label is offset in points from each axes' top-left corner, so it stays
    put regardless of figure size.

    Args:
        axes: A single axes or an iterable of them, in reading order. Accepts the array returned
            by ``plt.subplots`` and the name-to-axes mapping returned by :func:`mosaic`, which is
            already in reading order; pass ``labels=list(panels)`` to letter a mosaic by its own
            names instead.
        journal: Theme key or alias. Defaults to the active theme.
        fmt: Format string applied to each letter, overriding the journal default.
        labels: Explicit label strings, overriding the generated letters.
        dx: Horizontal offset in points from the axes' left edge.
        dy: Vertical offset in points from the axes' top edge.
        weight: Font weight.
        size: Font size in points. Defaults to the journal's panel label size.
        **kwargs: Forwarded to ``Axes.annotate``.

    Returns:
        The created text artists, in the order the axes were given.

    Example:
        >>> use("aps")
        >>> fig, axs = plt.subplots(1, 2)
        >>> tuple(t.get_text() for t in panel_labels(axs))
        ('(a)', '(b)')
    """
    spec = _spec_for(journal)
    axes_list = [axes] if isinstance(axes, Axes) else [ax for ax in _flatten(axes)]
    template = fmt if fmt is not None else spec.panel_label_fmt
    letters = ascii_lowercase[: len(axes_list)]
    if spec.panel_label_upper:
        letters = letters.upper()
    texts = list(labels) if labels is not None else [template.format(c) for c in letters]

    artists: list[Text] = []
    for ax, label in zip(axes_list, texts, strict=False):
        artist = ax.annotate(
            label,
            xy=(0.0, 1.0),
            xycoords="axes fraction",
            xytext=(dx, dy),
            textcoords="offset points",
            fontsize=size if size is not None else spec.panel_label_pt,
            fontweight=weight,
            va="bottom",
            ha="left",
            annotation_clip=False,
            **kwargs,
        )
        artist.set_gid(PANEL_LABEL_GID)
        artists.append(artist)
    return artists


def label_lines(
    ax: Axes,
    *,
    labels: Iterable[str] | None = None,
    offset: float = 3.0,
    **kwargs: Any,
) -> list[Text]:
    """Label each line at its right-hand end instead of in a legend.

    A legend costs space and makes the reader look up a colour before they can read the plot. At a
    single-column width that lookup is the most expensive thing on the page, and putting the name
    beside the line removes it. The label takes the line's own colour, so the association survives a
    greyscale print only if the linestyles differ too -- which the themes' property cycle ensures.

    Labels are drawn outside the axes and are not clipped, so leave room for them: ``ax.margins(x=0.2)``
    before calling, or set an explicit upper x-limit.

    Args:
        ax: The axes whose lines should be labelled.
        labels: Explicit label strings, overriding each line's own label. Must match the number of
            labelled lines.
        offset: Horizontal gap in points between the end of the line and its label.
        **kwargs: Forwarded to ``Axes.annotate``.

    Returns:
        The created text artists, in the order the lines were drawn.

    Example:
        >>> use("elsevier")
        >>> fig, ax = subplots("elsevier")
        >>> _ = ax.plot([1, 2, 3], [1, 4, 9], label="Series A")
        >>> _ = ax.plot([1, 2, 3], [2, 5, 10], label="Series B")
        >>> tuple(t.get_text() for t in label_lines(ax))
        ('Series A', 'Series B')
    """
    lines = [line for line in ax.lines if not str(line.get_label()).startswith("_")]
    texts = list(labels) if labels is not None else [str(line.get_label()) for line in lines]

    artists: list[Text] = []
    for line, text in zip(lines, texts, strict=False):
        xdata: Any = line.get_xdata()
        ydata: Any = line.get_ydata()
        finite = [(x, y) for x, y in zip(xdata, ydata, strict=False) if _is_finite(x) and _is_finite(y)]
        if not finite:
            continue
        x_end, y_end = finite[-1]
        artists.append(
            ax.annotate(
                text,
                xy=cast("tuple[float, float]", (x_end, y_end)),
                xytext=(offset, 0.0),
                textcoords="offset points",
                color=line.get_color(),
                va="center",
                ha="left",
                annotation_clip=False,
                **kwargs,
            )
        )
    return artists


def _is_finite(value: Any) -> bool:
    """True unless the value is a numeric NaN or infinity.

    Anything that is not a number -- a date, a category label -- cannot be NaN, so it counts as finite.
    Returning False for those would discard every point on a date axis.
    """
    try:
        return bool(isfinite(float(value)))
    except (TypeError, ValueError):
        return True


@dataclass(frozen=True)
class Violation:
    """A single departure from a publisher's figure requirements.

    Attributes:
        kind: Short category, e.g. ``"text"``, ``"line"``, ``"width"``.
        message: Human-readable description including the measured and required values.
    """

    kind: str
    message: str

    def __str__(self) -> str:
        return f"[{self.kind}] {self.message}"


def _flatten(obj: Axes | Mapping[Any, Any] | Iterable[Any]) -> Iterator[Axes]:
    if isinstance(obj, Axes):
        yield obj
        return
    # A mosaic maps names to axes; iterating it plainly would yield the names, and a one-character
    # name is its own iterator, so this would recurse forever.
    for item in obj.values() if isinstance(obj, Mapping) else obj:
        yield from _flatten(item)


def _spec_for(journal: str | None) -> JournalSpec:
    key = journal if journal is not None else _ACTIVE
    if key is None:
        raise RuntimeError(
            "no journal given and no active theme. Name one -- check(fig, journal='nature'), "
            "fonts(journal='nature') -- which is how to inspect a figure this process did not draw, "
            "or call journalfig.use(...) first to set a default."
        )
    return get_spec(key)


def _glyph_height_mm(prop: FontProperties) -> float:
    """Height of the digit ``0`` in millimetres, as it will be printed."""
    return TextPath((0, 0), "0", prop=prop).get_extents().height / PT_PER_MM


def _has_shrinking_math(s: str) -> bool:
    return "$" in s and ("_" in s or "^" in s)


@dataclass(frozen=True)
class FontStatus:
    """What a requested typeface actually resolved to on this machine.

    Attributes:
        requested: The families asked for, in the order matplotlib searches them.
        resolved: The family that will really be drawn.
        path: The font file backing ``resolved``.
        status: ``"exact"`` for a face the publisher names, ``"substitute"`` for a metrically
            compatible stand-in, ``"unrestricted"`` where the publisher names no typeface at all,
            and ``"fallback"`` for a face that misses a stated requirement.
    """

    requested: tuple[str, ...]
    resolved: str
    path: str
    status: str

    def __str__(self) -> str:
        return f"{self.resolved} [{self.status}] <- {', '.join(self.requested)}"


def _expand_families(families: str | Iterable[str]) -> tuple[str, ...]:
    """Expand an rcParam font family into the concrete list matplotlib will search."""
    names = [families] if isinstance(families, str) else list(families)
    expanded: list[str] = []
    for name in names:
        if name in ("sans-serif", "serif", "monospace", "cursive", "fantasy"):
            expanded.extend(plt.rcParams[f"font.{name}"])
        else:
            expanded.append(str(name))
    return tuple(expanded)


def _resolve_family(families: tuple[str, ...], spec: JournalSpec) -> FontStatus:
    path = findfont(FontProperties(family=list(families)))
    resolved = FontProperties(fname=path).get_name()
    folded = resolved.casefold()
    if any(folded == name.casefold() for name in spec.font_families):
        status = "exact"
    elif any(folded == name.casefold() for name in spec.font_substitutes):
        status = "substitute"
    elif not spec.font_families:
        # A publisher that names no typeface cannot be disobeyed on typeface. AIP and Wiley state
        # none, and calling every face a fallback there would flag every figure for a rule that does
        # not exist.
        status = "unrestricted"
    else:
        status = "fallback"
    return FontStatus(families, resolved, path, status)


def _figure_families(fig: Figure) -> tuple[tuple[str, ...], ...]:
    """Distinct font families the figure's own text asks for, in the order they are first seen."""
    seen: list[tuple[str, ...]] = []
    for text in fig.findobj(Text):
        # Deliberately not filtered on text content. A tick label is an empty Text until the figure is
        # drawn, but it already carries the family it was constructed with, and that is the family it
        # will render in -- skipping empties would make check() blind to fonts on any undrawn figure.
        if not text.get_visible():
            continue
        families = _expand_families(text.get_fontproperties().get_family())
        if families and families not in seen:
            seen.append(families)
    return tuple(seen)


def fonts(journal: str | None = None, fig: Figure | None = None) -> dict[str, FontStatus]:
    """Report the typefaces this machine will really draw with.

    matplotlib substitutes silently when a requested family is missing. A theme asking for Arial or
    Times renders in DejaVu on a machine that has neither -- it still looks fine on screen, and the
    figure breaks the publisher's font requirement. Run this before trusting a figure produced
    somewhere other than where the theme was tested, an HPC node especially.

    Args:
        journal: Theme key or alias. Defaults to the active theme.
        fig: Read the families from this figure's own text artists instead of from the global
            rcParams. Pass it for any figure this process did not just draw under the theme --
            without it the answer describes the caller's settings, not the figure. Note that an
            artist which inherited the generic name ``"sans-serif"`` is still expanded through the
            current rcParams, because the artist does not record what that name meant elsewhere; an
            artist given a concrete face is read exactly, which is the case rcParams cannot see.

    Returns:
        One :class:`FontStatus` per role. Reading the rcParams gives ``"text"`` for body text plus an
        entry per custom mathtext face; reading a figure gives ``"text"`` for the first family found
        and ``"text[<family>]"`` for any further ones. Empty when ``text.usetex`` is on, since LaTeX
        chooses the fonts then, and empty for a figure carrying no visible text.

    Example:
        >>> use("nature")
        >>> fonts()["text"].requested[0]
        'Arial'
        >>> fig, ax = subplots("nature")
        >>> _ = ax.set_xlabel("q")
        >>> fonts(fig=fig)["text"].requested[0]
        'Arial'
    """
    spec = _spec_for(journal)
    if plt.rcParams["text.usetex"]:
        return {}

    if fig is not None:
        return {
            ("text" if index == 0 else f"text[{families[0]}]"): _resolve_family(families, spec)
            for index, families in enumerate(_figure_families(fig))
        }

    report = {"text": _resolve_family(_expand_families(plt.rcParams["font.family"]), spec)}
    if plt.rcParams["mathtext.fontset"] == "custom":
        for key in ("mathtext.rm", "mathtext.it", "mathtext.bf", "mathtext.sf"):
            # "Arial:italic" names a face within the Arial family; only the family is looked up.
            family = str(plt.rcParams[key]).split(":")[0]
            report[key] = _resolve_family(_expand_families(family), spec)
    return report


def _element_count(artist: Any) -> int:
    """Cheap size proxy for an artist, without materialising its paths.

    ``QuadMesh.get_paths()`` builds every quad on demand, so asking a large mesh how many paths it has
    is itself the expensive operation this rule exists to warn about. The underlying array knows.
    """
    array = getattr(artist, "get_array", lambda: None)()
    if array is not None:
        return _length(array)
    if isinstance(artist, Line2D):
        return _length(artist.get_xdata())
    offsets = getattr(artist, "get_offsets", lambda: None)()
    if offsets is not None:
        return _length(offsets)
    return 0


def _length(obj: Any) -> int:
    """Number of elements, preferring an array's ``size`` over materialising it."""
    size = getattr(obj, "size", None)
    if isinstance(size, int):
        return size
    try:
        return len(obj)
    except TypeError:
        return 0


def _vector_heavy_artists(fig: Figure) -> Iterator[Any]:
    """Artists large enough to bloat a vector file, and not rasterized."""
    for ax in fig.get_axes():
        for artist in [*ax.collections, *ax.lines]:
            # AxesImage (imshow) is already a bitmap in the output, so it is never the problem here.
            if artist.get_visible() and not artist.get_rasterized():
                if _element_count(artist) > VECTOR_ELEMENT_LIMIT:
                    yield artist


def check(fig: Figure, *, journal: str | None = None, warn: bool = True) -> list[Violation]:
    """Check a figure against a publisher's stated figure requirements.

    Inspects text sizes (including the 0.7x shrink matplotlib applies to maths sub/superscripts),
    printed glyph height, line weights, marker diameters, the figure's own dimensions, and which
    typeface the machine will actually draw with. A metrically compatible substitute passes; a
    silent fall back to something else does not. See :func:`fonts` for the full picture.

    Args:
        fig: The figure to inspect.
        journal: Theme key or alias. Defaults to the active theme.
        warn: Emit a ``UserWarning`` summarising the violations found.

    Returns:
        Every violation found, in discovery order. Empty means the figure complies with the
        machine-checkable parts of the spec.

    Example:
        >>> use("aps")
        >>> fig, ax = subplots("aps")
        >>> _ = ax.set_xlabel("q", fontsize=4)
        >>> sorted({v.kind for v in check(fig, warn=False)})
        ['lettering']
    """
    spec = _spec_for(journal)
    found: list[Violation] = []

    width_in, height_in = _PINNED.get(fig, tuple(fig.get_size_inches()))
    width_mm = width_in * MM_PER_INCH
    if not any(abs(width_mm - allowed) <= 0.5 for allowed in spec.widths_mm.values()):
        allowed_str = ", ".join(f"{name} {value:.0f} mm" for name, value in sorted(spec.widths_mm.items()))
        found.append(Violation("width", f"figure is {width_mm:.1f} mm wide; {spec.name} uses {allowed_str}"))
    if spec.max_height_mm is not None and height_in * MM_PER_INCH > spec.max_height_mm + 0.5:
        found.append(
            Violation(
                "height",
                f"figure is {height_in * MM_PER_INCH:.1f} mm tall; {spec.name} allows {spec.max_height_mm:.0f} mm",
            )
        )

    for role, status in fonts(journal=journal, fig=fig).items():
        if status.status == "fallback":
            # A figure drawn elsewhere often asks for the face it already got, so "asks for X but
            # resolves to X" is the common case rather than the odd one. Say what happened instead.
            if status.requested[0] == status.resolved:
                rendered = f"{role} renders in {status.resolved}"
            else:
                rendered = f"{role} asks for {status.requested[0]} but resolves to {status.resolved}"
            found.append(
                Violation(
                    "font",
                    f"{rendered}; {spec.name} requires {', '.join(spec.font_families)} — install one "
                    f"of those, or a metric substitute ({', '.join(spec.font_substitutes)})",
                )
            )

    for text in fig.findobj(Text):
        content = text.get_text()
        if not content.strip() or not text.get_visible():
            continue
        is_panel_label = text.get_gid() == PANEL_LABEL_GID
        size = float(text.get_fontsize())

        if spec.text_min_pt is not None and size < spec.text_min_pt:
            found.append(
                Violation("text", f"{content!r} is {size:.1f} pt, below the {spec.text_min_pt:.0f} pt minimum")
            )
        if spec.text_max_pt is not None and not is_panel_label and size > spec.text_max_pt:
            found.append(
                Violation("text", f"{content!r} is {size:.1f} pt, above the {spec.text_max_pt:.0f} pt maximum")
            )

        if spec.sub_min_pt is not None and _has_shrinking_math(content):
            effective = size * MATHTEXT_SHRINK
            if effective < spec.sub_min_pt:
                found.append(
                    Violation(
                        "subscript",
                        f"{content!r} renders sub/superscripts at {effective:.2f} pt "
                        f"({size:.1f} pt x {MATHTEXT_SHRINK}), below the {spec.sub_min_pt:.0f} pt floor",
                    )
                )

        if spec.min_lettering_mm is not None:
            height_mm = _glyph_height_mm(text.get_fontproperties())
            if height_mm < spec.min_lettering_mm:
                found.append(
                    Violation(
                        "lettering",
                        f"{content!r} at {size:.1f} pt prints {height_mm:.2f} mm tall, "
                        f"below the {spec.min_lettering_mm:.1f} mm minimum",
                    )
                )

    if spec.min_linewidth_pt is not None:
        edge_width = float(plt.rcParams["axes.linewidth"])
        for ax in fig.get_axes():
            for spine in ax.spines.values():
                edge_width = min(edge_width, spine.get_linewidth())
        if edge_width < spec.min_linewidth_pt:
            found.append(
                Violation(
                    "line",
                    f"axes frame is {edge_width:.2f} pt, below the {spec.min_linewidth_pt:.2f} pt minimum",
                )
            )

    # Only data lines: fig.findobj(Line2D) would also pick up tick marks, whose "markersize"
    # is the tick length and would report as an undersized data point.
    for line in (line for ax in fig.get_axes() for line in ax.lines):
        xdata: Any = line.get_xdata()
        if not line.get_visible() or len(xdata) == 0:
            # An empty line draws nothing, so nothing about it can be too small. Axes.boxplot creates a
            # flier artist per box whether or not any point lies beyond the whiskers, and without this a
            # five-box plot reports five undersized-marker violations for the three that have fliers.
            continue
        if spec.min_linewidth_pt is not None and line.get_linestyle() not in ("None", "none", "", " "):
            width = line.get_linewidth()
            if 0 < width < spec.min_linewidth_pt:
                found.append(
                    Violation("line", f"a line is {width:.2f} pt, below the {spec.min_linewidth_pt:.2f} pt minimum")
                )
        if spec.min_marker_mm is not None and line.get_marker() not in ("None", "none", "", " ", None):
            diameter_mm = line.get_markersize() / PT_PER_MM
            if diameter_mm < spec.min_marker_mm:
                found.append(
                    Violation(
                        "marker",
                        f"marker diameter is {diameter_mm:.2f} mm, below the {spec.min_marker_mm:.1f} mm minimum",
                    )
                )

    # Axes.scatter produces a PathCollection rather than a Line2D, and sizes it in points squared.
    if spec.min_marker_mm is not None:
        for collection in (c for ax in fig.get_axes() for c in ax.collections):
            if not collection.get_visible() or not hasattr(collection, "get_sizes"):
                continue
            sizes = collection.get_sizes()
            if len(sizes) == 0:
                continue
            diameter_mm = sqrt(float(min(sizes))) / PT_PER_MM
            if diameter_mm < spec.min_marker_mm:
                found.append(
                    Violation(
                        "marker",
                        f"scatter marker is {diameter_mm:.2f} mm across (s={min(sizes):.3g} pt²), "
                        f"below the {spec.min_marker_mm:.1f} mm minimum",
                    )
                )

    # The one rule here that no publisher document states. A figure whose vector artists hold hundreds
    # of thousands of paths produces a PDF that is slow to open and large enough for a submission system
    # to reject, and rasterizing that one artist fixes it without touching the vector text or axes.
    for artist in _vector_heavy_artists(fig):
        found.append(
            Violation(
                "vector",
                f"a {type(artist).__name__} holds {_element_count(artist):,} elements and is not "
                f"rasterized; the vector file will be very large — pass rasterized=True to that call "
                f"so only it becomes a bitmap, leaving axes and text as text",
            )
        )

    if warn and found:
        summary = "\n  ".join(str(v) for v in found)
        warnings.warn(
            f"{spec.name} figure requirements not met:\n  {summary}",
            category=JournalFigWarning,
            stacklevel=2,
        )
    return found


def save(
    fig: Figure,
    path: str | Path,
    *,
    journal: str | None = None,
    formats: Iterable[str] | None = None,
    dpi: int | None = None,
    validate: bool = True,
    pil_kwargs: dict[str, Any] | None = None,
    svg_text: str | None = None,
) -> list[Path]:
    """Save a figure in the formats the target publisher accepts.

    Writes with ``bbox_inches=None`` so the declared column width survives into the file; a tight
    bounding box would crop it by around one percent. TIFFs are LZW-compressed by default, which is
    lossless: an Elsevier single-column figure lands at a few hundred kB rather than 7.5 MB.

    The size actually written is reported through the ``journalfig`` logger at INFO level, so it stays
    out of the way in a pipeline. Raise that one logger to see it --
    ``logging.getLogger("journalfig").setLevel("INFO")`` -- rather than the root logger, which also
    switches on ``fontTools`` and its dozen subsetting lines per PDF.

    Every journal writes PDF, SVG and PNG by default: the file you submit, one to edit in Inkscape or
    Illustrator, and one for a talk or a preview. Pass ``formats=`` for anything else the backend
    supports -- TIFF for Elsevier, EPS for an APS colour-online-only figure -- and convert from the
    SVG for whatever else a publisher asks for.

    SVG keeps live, editable text (``svg.fonttype: none``), which means it renders correctly only
    where the theme's typeface is installed; :func:`fonts` reports what that will be. The draft
    warning fires once per call, and only when *nothing* written is a format the publisher takes as
    final artwork -- so a PNG beside a PDF is silent, and a PNG on its own is not.

    Args:
        fig: The figure to write.
        path: Output path. Any extension is replaced by each requested format.
        journal: Theme key or alias. Defaults to the active theme.
        formats: File formats to write, overriding the journal defaults.
        dpi: Resolution for raster formats. Defaults to the journal's requirement.
        validate: Run :func:`check` first and warn about any violations.
        pil_kwargs: Passed to Pillow for raster formats, replacing the journal's TIFF compression.
            Pass ``{}`` to write an uncompressed TIFF.
        svg_text: How text is stored in an SVG. ``"none"`` (the theme default) keeps it live and
            editable, which is the reason to want an SVG at all -- but it then renders correctly only
            where the theme's typeface is installed. ``"path"`` converts glyphs to outlines, so the
            file renders identically anywhere and converts safely on any machine, at the cost of the
            text no longer being text. Applies to the SVG only; other formats are unaffected.

    Returns:
        The paths written, in the order requested.

    Example:
        >>> import tempfile
        >>> use("elsevier")
        >>> fig, ax = subplots("elsevier")
        >>> with tempfile.TemporaryDirectory() as d:
        ...     # validate=False keeps this example independent of whether the machine running it has
        ...     # Arial installed; leave it on in real use, where that is exactly what you want to know.
        ...     tuple(p.suffix for p in save(fig, Path(d) / "fig1", formats=["pdf"], validate=False))
        ('.pdf',)
    """
    spec = _spec_for(journal)
    pinned = _PINNED.get(fig)
    if pinned is not None:
        fig.set_size_inches(*pinned, forward=False)
    if validate:
        check(fig, journal=journal)

    chosen = tuple(formats) if formats is not None else spec.formats
    stem = Path(path)
    if stem.suffix.lstrip(".").lower() in {"pdf", "eps", "ps", "png", "tif", "tiff", "svg", "jpg", "jpeg"}:
        stem = stem.with_suffix("")

    # The warning belongs to the write as a whole, not to each file: a PNG or SVG companion beside a
    # submittable PDF is a working copy, not a compliance problem, and warning per format would make
    # asking for one permanently noisy. What matters is whether anything written can be submitted.
    if not any(fmt.lower() in spec.submission_formats for fmt in chosen):
        warnings.warn(
            f"none of {', '.join(f.upper() for f in chosen)} can be submitted to {spec.name} as final "
            f"artwork; it takes {', '.join(f.upper() for f in spec.submission_formats)} — treat these "
            f"as drafts",
            category=JournalFigWarning,
            stacklevel=2,
        )

    # spec.raster_dpi is a floor, not a target: a publisher states the resolution below which artwork is
    # rejected, so writing above it is fine and only falling short is a problem. Vector formats carry no
    # resolution, so an explicit dpi is simply irrelevant to them and must not warn.
    resolution = dpi if dpi is not None else spec.raster_dpi
    rasters = tuple(fmt for fmt in chosen if fmt.lower() in _RASTER_FORMATS)
    if rasters and spec.raster_dpi is not None and resolution is not None and resolution < spec.raster_dpi:
        warnings.warn(
            f"{', '.join(f.upper() for f in rasters)} at {resolution} dpi is below the {spec.name} "
            f"minimum of {spec.raster_dpi} dpi",
            category=JournalFigWarning,
            stacklevel=2,
        )

    written: list[Path] = []
    for fmt in chosen:
        target = stem.with_suffix(f".{fmt}")
        extra: dict[str, Any] = {}
        if pil_kwargs is not None:
            extra["pil_kwargs"] = pil_kwargs
        elif fmt.lower() in {"tif", "tiff"} and spec.tiff_compression is not None:
            extra["pil_kwargs"] = {"compression": spec.tiff_compression}
        # Scoped to this write: svg.fonttype is a global rcParam, and a caller asking for outlined text
        # in one file should not silently get it in every figure drawn afterwards.
        overrides = {"svg.fonttype": svg_text} if svg_text is not None and fmt.lower() == "svg" else {}
        with plt.rc_context(overrides):
            # No stated floor and no explicit request leaves dpi to the theme's own savefig.dpi.
            written_dpi = dpi if dpi is not None else spec.raster_dpi
            if written_dpi is None:
                fig.savefig(target, format=fmt, bbox_inches=None, **extra)
            else:
                fig.savefig(target, format=fmt, dpi=written_dpi, bbox_inches=None, **extra)
        written.append(target)

    width_in, height_in = pinned if pinned is not None else tuple(fig.get_size_inches())
    _LOG.info(
        "%s: %.1f x %.1f mm -> %s",
        spec.name,
        width_in * MM_PER_INCH,
        height_in * MM_PER_INCH,
        ", ".join(p.name for p in written),
    )
    return written
