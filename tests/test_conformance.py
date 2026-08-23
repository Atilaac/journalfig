"""The guard that keeps SPECS and the stylesheets from disagreeing.

Widths, font sizes and raster resolution are stated twice: once in :mod:`journalfig._specs`, which is
what ``check()`` validates against, and once in the matching ``.mplstyle``, which is what actually
renders. Nothing tied the two together, so either could have been wrong without a single test failing --
``check()`` would have started flagging the theme's own output. These tests are that missing link.

They also assert that a journal added to ``SPECS`` is registered everywhere else it has to be. Two of
those places fail silently: a missing ``SOURCES`` entry surfaces only when a user calls ``source()``, and
a missing ``_USETEX_PREAMBLE`` entry only when a user calls ``use(..., usetex=True)``.

Author: Achraf Atila (achraf.atila@bam.de)
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import pytest

import journalfig as jf
from journalfig._core import _usetex_preamble
from journalfig._specs import GOLDEN, mm_to_inch

#: The stylesheets carry six decimal places, so agreement is only meaningful to that precision. Half a
#: unit in the last place is 5e-7, and floating point can land just outside that, so the tolerance is
#: 1e-6 inches -- 2.5e-5 mm, far below anything a publisher states or a printer can resolve.
ROUNDING = 1e-6

#: rcParam -> the ``JournalSpec.font_sizes`` key it must equal.
FONT_SIZE_KEYS = {
    "font.size": "base",
    "axes.labelsize": "label",
    "axes.titlesize": "title",
    "figure.titlesize": "title",
    "xtick.labelsize": "tick",
    "ytick.labelsize": "tick",
    "legend.fontsize": "legend",
    "legend.title_fontsize": "legend",
}


@pytest.fixture(autouse=True)
def _clean_rcparams():
    """Restore matplotlib's global state after every test."""
    saved = plt.rcParams.copy()
    yield
    plt.rcParams.update(saved)
    plt.close("all")


@pytest.mark.parametrize("journal", jf.JOURNALS)
def test_default_figsize_matches_the_spec_width(journal):
    jf.use(journal)
    spec = jf.get_spec(journal)
    assert plt.rcParams["figure.figsize"][0] == pytest.approx(mm_to_inch(spec.widths_mm["single"]), abs=ROUNDING)


@pytest.mark.parametrize("journal", jf.JOURNALS)
def test_default_figsize_uses_the_same_ratio_as_figsize(journal):
    """plt.subplots() and jf.subplots() must not disagree about the default aspect ratio."""
    jf.use(journal)
    width, height = plt.rcParams["figure.figsize"]
    assert height == pytest.approx(width * GOLDEN, abs=ROUNDING)


@pytest.mark.parametrize("journal", jf.JOURNALS)
@pytest.mark.parametrize("rcparam,size_key", sorted(FONT_SIZE_KEYS.items()))
def test_font_sizes_match_the_spec(journal, rcparam, size_key):
    jf.use(journal)
    expected = jf.get_spec(journal).font_sizes[size_key]
    assert plt.rcParams[rcparam] == pytest.approx(expected)


@pytest.mark.parametrize("journal", jf.JOURNALS)
def test_savefig_dpi_clears_the_spec_floor(journal):
    """Publishers state a *minimum* resolution, so exceeding it is compliant and only falling short is not."""
    floor = jf.get_spec(journal).raster_dpi
    if floor is None:
        pytest.skip(f"{journal} states no resolution requirement")
    jf.use(journal)
    assert plt.rcParams["savefig.dpi"] >= floor


#: rcParam -> the ``ThemeStyle`` attribute it must equal. Every entry is a rendering choice this
#: package makes; none is a publisher requirement, which is why they live outside JournalSpec.
STYLE_KEYS = {
    "axes.linewidth": "axes_linewidth",
    "patch.linewidth": "axes_linewidth",
    "hatch.linewidth": "axes_linewidth",
    "grid.linewidth": "grid_linewidth",
    "xtick.major.size": "tick_major_size",
    "ytick.major.size": "tick_major_size",
    "xtick.minor.size": "tick_minor_size",
    "ytick.minor.size": "tick_minor_size",
    "xtick.major.width": "tick_major_width",
    "ytick.major.width": "tick_major_width",
    "xtick.minor.width": "tick_minor_width",
    "ytick.minor.width": "tick_minor_width",
    "xtick.major.pad": "tick_pad",
    "ytick.major.pad": "tick_pad",
    "lines.markersize": "marker_size",
    "lines.markeredgewidth": "marker_edge_width",
    "errorbar.capsize": "errorbar_capsize",
    "legend.handlelength": "legend_handlelength",
    "axes.titleweight": "title_weight",
    "axes.titlelocation": "title_location",
    "mathtext.fontset": "mathtext_fontset",
}


@pytest.mark.parametrize("journal", jf.JOURNALS)
@pytest.mark.parametrize("rcparam,attribute", sorted(STYLE_KEYS.items()))
def test_style_values_match_the_theme_style(journal, rcparam, attribute):
    jf.use(journal)
    expected = getattr(jf.get_spec(journal).style, attribute)
    actual = plt.rcParams[rcparam]
    assert actual == (expected if isinstance(expected, str) else pytest.approx(expected))


@pytest.mark.parametrize("journal", jf.JOURNALS)
def test_tick_geometry_is_symmetric_between_axes(journal):
    """x and y are never given different tick geometry; ThemeStyle has one field per pair."""
    jf.use(journal)
    for suffix in ("major.size", "minor.size", "major.width", "minor.width", "major.pad"):
        assert plt.rcParams[f"xtick.{suffix}"] == pytest.approx(plt.rcParams[f"ytick.{suffix}"])


@pytest.mark.parametrize("journal", jf.JOURNALS)
def test_every_journal_has_a_source(journal):
    """Omitting a Source stays green until a user calls source() and gets a KeyError."""
    assert journal in jf.SOURCES
    assert jf.source(journal).retrieved


@pytest.mark.parametrize("journal", jf.JOURNALS)
def test_every_journal_has_a_usetex_preamble(journal):
    """Used to be a per-journal dict, where a new theme raised KeyError on use(..., usetex=True)."""
    preamble = _usetex_preamble(jf.get_spec(journal))
    assert preamble and r"\usepackage{amsmath}" in preamble


@pytest.mark.parametrize("journal", jf.JOURNALS)
def test_every_journal_resolves_from_its_own_key(journal):
    assert jf.resolve(journal) == journal
    assert jf.get_spec(journal) is jf.SPECS[journal]
