"""Tests for the journal themes.

Author: Achraf Atila (achraf.atila@bam.de)
"""

from __future__ import annotations

import re
import shutil
import warnings
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pytest
from PIL import Image

import journalfig as jf

MM_PER_INCH = 25.4
PT_PER_INCH = 72.0

#: Fonts matplotlib ships with, so these tests do not depend on what the machine has installed.
BUNDLED_FONTS = Path(matplotlib.get_data_path()) / "fonts" / "ttf"


def _force_font(monkeypatch, filename):
    """Resolve every lookup to one bundled file, as on a machine missing the theme's typeface."""
    path = str(BUNDLED_FONTS / filename)
    monkeypatch.setattr(jf._core, "findfont", lambda *args, **kwargs: path)
    return path


@pytest.fixture(autouse=True)
def _clean_rcparams():
    """Restore matplotlib's global state after every test."""
    saved = plt.rcParams.copy()
    yield
    plt.rcParams.update(saved)
    plt.close("all")


@pytest.mark.parametrize("journal", jf.JOURNALS)
def test_style_loads(journal):
    jf.use(journal)
    assert jf.active() == journal
    assert plt.rcParams["pdf.fonttype"] == 42
    assert plt.rcParams["savefig.bbox"] is None  # matplotlib stores "standard" as None
    assert plt.rcParams["figure.constrained_layout.use"] is True
    assert len(plt.rcParams["axes.prop_cycle"]) == 8


@pytest.mark.parametrize("journal", jf.JOURNALS)
def test_registered_in_matplotlib_library(journal):
    assert journal in plt.style.available
    plt.style.use(journal)


def test_aliases_resolve():
    assert jf.resolve("PRB") == "aps"
    assert jf.resolve("Acta Materialia") == "elsevier"
    assert jf.resolve("Nature Communications") == "nature"
    assert jf.resolve("Science") == "science"
    assert jf.resolve("Chemistry of Materials") == "acs"
    with pytest.raises(KeyError):
        jf.resolve("Journal of Irreproducible Results")


@pytest.mark.parametrize(
    ("journal", "width", "expected_mm"),
    [
        ("nature", "single", 89.0),
        ("nature", "onehalf", 120.0),
        ("nature", "onehalf_wide", 136.0),
        ("nature", "double", 183.0),
        ("aps", "single", 3.375 * MM_PER_INCH),
        ("aps", "double", 7.0 * MM_PER_INCH),
        ("elsevier", "single", 90.0),
        ("elsevier", "onehalf", 140.0),
        ("elsevier", "double", 190.0),
    ],
)
def test_figsize_widths_are_exact(journal, width, expected_mm):
    width_in, _ = jf.figsize(journal, width)
    assert width_in * MM_PER_INCH == pytest.approx(expected_mm, abs=1e-6)


def test_figsize_ratio_and_explicit_height():
    width_in, height_in = jf.figsize("aps", "double", ratio=0.4)
    assert (width_in, height_in) == pytest.approx((7.0, 2.8))
    _, height_in = jf.figsize("elsevier", "single", height_mm=50.0)
    assert height_in * MM_PER_INCH == pytest.approx(50.0)


def test_figsize_accepts_explicit_mm():
    width_in, _ = jf.figsize("nature", 75.0)
    assert width_in * MM_PER_INCH == pytest.approx(75.0)


def test_figsize_clamps_to_max_height():
    with pytest.warns(UserWarning, match="exceeds"):
        _, height_in = jf.figsize("nature", "double", ratio=3.0)
    assert height_in * MM_PER_INCH == pytest.approx(247.0)


def test_figsize_warns_below_minimum_width():
    with pytest.warns(UserWarning, match="minimum"):
        jf.figsize("elsevier", 20.0)


def test_figsize_rejects_unknown_layout():
    with pytest.raises(KeyError, match="onehalf_wide"):
        jf.figsize("aps", "onehalf_wide")


def test_base_size_scales_every_font_key():
    jf.use("elsevier", base_size=9)
    assert plt.rcParams["font.size"] == pytest.approx(9.0)
    assert plt.rcParams["xtick.labelsize"] == pytest.approx(9.0)
    assert plt.rcParams["legend.fontsize"] == pytest.approx(9.0)


def test_context_restores_previous_state():
    plt.rcParams["font.size"] = 11.0
    jf.use("nature")
    with jf.context("aps"):
        assert plt.rcParams["font.size"] == pytest.approx(9.0)
        assert jf.active() == "aps"
    assert jf.active() == "nature"
    assert plt.rcParams["font.size"] == pytest.approx(7.0)


@pytest.mark.parametrize("journal", jf.JOURNALS)
def test_mosaic_pins_the_exact_width_and_names_panels_in_reading_order(journal):
    jf.use(journal)
    fig, panels = jf.mosaic(journal, "AAB\nCCB", width="double", ratio=0.7)
    assert list(panels) == ["A", "B", "C"]
    expected_mm = jf.get_spec(journal).widths_mm["double"]
    assert fig.get_size_inches()[0] * MM_PER_INCH == pytest.approx(expected_mm, abs=1e-6)


def test_mosaic_panels_span_the_cells_they_repeat_over():
    """A spans two columns and B two rows, so the drawn panels differ in size."""
    jf.use("nature")
    fig, panels = jf.mosaic("nature", "AAB\nCCB", width="double", ratio=0.7)
    fig.canvas.draw()
    wide, tall = panels["A"].get_position(), panels["B"].get_position()
    assert wide.width > tall.width
    assert tall.height > wide.height


def test_mosaic_applies_width_and_height_ratios():
    jf.use("elsevier")
    fig, panels = jf.mosaic("elsevier", "AB\nCD", width="double", ratio=0.7, width_ratios=[2, 1], height_ratios=[1, 3])
    grid = panels["A"].get_gridspec()
    assert list(grid.get_width_ratios()) == [2, 1]
    assert list(grid.get_height_ratios()) == [1, 3]

    fig.canvas.draw()
    assert panels["A"].get_position().width == pytest.approx(2 * panels["B"].get_position().width, rel=0.02)
    assert panels["C"].get_position().height == pytest.approx(3 * panels["A"].get_position().height, rel=0.02)


def test_mosaic_leaves_a_dot_cell_empty():
    jf.use("aps")
    fig, panels = jf.mosaic("aps", "AB\n.B", width="single")
    assert sorted(panels) == ["A", "B"]
    assert len(fig.get_axes()) == 2


def test_gridspec_places_spanning_panels():
    jf.use("aps")
    fig, grid = jf.gridspec("aps", 2, 3, width="double", ratio=0.6, width_ratios=[1, 1, 2])
    assert grid.get_geometry() == (2, 3)
    wide = fig.add_subplot(grid[0, :2])
    tall = fig.add_subplot(grid[:, 2])
    fig.canvas.draw()
    assert tall.get_position().height > wide.get_position().height
    assert fig.get_size_inches()[0] == pytest.approx(7.0, abs=1e-6)


def test_gridspec_pins_the_size_through_save(tmp_path):
    jf.use("nature")
    fig, grid = jf.gridspec("nature", 2, 2, width="double", ratio=0.7)
    fig.add_subplot(grid[0, :]).plot([1, 2, 3], [1, 4, 9])
    fig.set_size_inches(7.2, 4.4, forward=False)  # simulate a GUI backend snapping the figure
    (written,) = jf.save(fig, tmp_path / "fig", formats=["pdf"], validate=False)

    box = re.search(rb"/MediaBox\s*\[([^\]]*)\]", written.read_bytes())
    x0, _, x1, _ = (float(v) for v in box.group(1).split())
    assert x1 - x0 == pytest.approx(183.0 / MM_PER_INCH * PT_PER_INCH, abs=0.01)


def test_subplots_forwards_gridspec_ratios():
    jf.use("nature")
    fig, axs = jf.subplots("nature", 1, 2, width="double", width_ratios=[3, 1])
    fig.canvas.draw()
    assert axs[0].get_position().width == pytest.approx(3 * axs[1].get_position().width, rel=0.05)


def test_panel_labels_accept_a_mosaic_mapping():
    jf.use("aps")
    fig, panels = jf.mosaic("aps", "AAB\nCCB", width="double", ratio=0.7)
    assert [t.get_text() for t in jf.panel_labels(panels)] == ["(a)", "(b)", "(c)"]
    assert [t.get_text() for t in jf.panel_labels(panels, labels=list(panels))] == ["A", "B", "C"]


def test_panel_labels_use_journal_format():
    jf.use("nature")
    fig, axs = plt.subplots(1, 3)
    assert [t.get_text() for t in jf.panel_labels(axs)] == ["a", "b", "c"]

    jf.use("aps")
    fig, axs = plt.subplots(1, 2)
    labels = jf.panel_labels(axs)
    assert [t.get_text() for t in labels] == ["(a)", "(b)"]
    assert all(t.get_gid() == jf._core.PANEL_LABEL_GID for t in labels)
    assert labels[0].get_fontsize() == pytest.approx(9.0)


def test_panel_labels_accept_single_axes_and_custom_labels():
    jf.use("elsevier")
    fig, ax = plt.subplots()
    assert [t.get_text() for t in jf.panel_labels(ax)] == ["(a)"]
    fig, axs = plt.subplots(1, 2)
    assert [t.get_text() for t in jf.panel_labels(axs, labels=["i", "ii"])] == ["i", "ii"]


def test_saved_pdf_width_matches_requested_width(tmp_path):
    """Regression test: savefig.bbox='tight' would silently shrink the column width."""
    jf.use("nature")
    width_in, height_in = jf.figsize("nature", "single")
    fig, ax = plt.subplots(figsize=(width_in, height_in))
    ax.plot([1, 2, 3], [1, 4, 9])
    ax.set_xlabel(r"$q$ (Å$^{-1}$)")
    ax.set_ylabel(r"$S(q)$")

    (written,) = jf.save(fig, tmp_path / "fig", formats=["pdf"], validate=False)
    box = re.search(rb"/MediaBox\s*\[([^\]]*)\]", written.read_bytes())
    assert box is not None
    x0, y0, x1, y1 = (float(v) for v in box.group(1).split())
    assert x1 - x0 == pytest.approx(width_in * PT_PER_INCH, abs=0.5)
    assert y1 - y0 == pytest.approx(height_in * PT_PER_INCH, abs=0.5)


@pytest.mark.parametrize("journal", jf.JOURNALS)
def test_subplots_and_figure_pin_the_exact_width(journal):
    """Interactive backends round a new figure to whole device pixels; the factories undo that."""
    jf.use(journal)
    expected_mm = jf.get_spec(journal).widths_mm["double"]

    fig, _ = jf.subplots(journal, 2, 2, width="double")
    assert fig.get_size_inches()[0] * MM_PER_INCH == pytest.approx(expected_mm, abs=1e-6)

    fig = jf.figure(journal, "double")
    assert fig.get_size_inches()[0] * MM_PER_INCH == pytest.approx(expected_mm, abs=1e-6)


def test_save_reasserts_the_pinned_size_after_backend_rounding(tmp_path):
    jf.use("nature")
    width_in, height_in = jf.figsize("nature", "double")
    fig, ax = jf.subplots("nature", width="double")
    ax.plot([1, 2, 3], [1, 4, 9])

    fig.set_size_inches(7.2, 4.4, forward=False)  # simulate a GUI backend snapping the figure
    (written,) = jf.save(fig, tmp_path / "fig", formats=["pdf"], validate=False)

    box = re.search(rb"/MediaBox\s*\[([^\]]*)\]", written.read_bytes())
    x0, _, x1, _ = (float(v) for v in box.group(1).split())
    assert x1 - x0 == pytest.approx(width_in * PT_PER_INCH, abs=0.01)
    assert fig.get_size_inches()[1] == pytest.approx(height_in)


def test_check_flags_undersized_aps_lettering():
    """Regression test for the APS 2 mm rule: 8 pt Times fails, 9 pt passes."""
    jf.use("aps")
    fig, ax = plt.subplots(figsize=jf.figsize("aps", "single"))
    ax.plot([1, 2, 3], [1, 4, 9])
    ax.set_xlabel("q", fontsize=8)
    kinds = [v.kind for v in jf.check(fig, warn=False)]
    assert "lettering" in kinds


def test_check_passes_a_compliant_figure():
    jf.use("aps")
    fig, ax = plt.subplots(figsize=jf.figsize("aps", "single"))
    ax.plot([1, 2, 3], [1, 4, 9])
    ax.set_xlabel("q (arb. units)")
    ax.set_ylabel("S")
    assert jf.check(fig, warn=False) == []


def test_check_flags_shrunk_math_subscripts():
    jf.use("elsevier")
    fig, ax = plt.subplots(figsize=jf.figsize("elsevier", "single"))
    ax.set_xlabel(r"$x_{a}$")
    violations = [v for v in jf.check(fig, warn=False) if v.kind == "subscript"]
    assert violations
    assert "4.90 pt" in violations[0].message


def test_check_exempts_nature_panel_labels_from_the_7pt_cap():
    jf.use("nature")
    fig, ax = plt.subplots(figsize=jf.figsize("nature", "single"))
    jf.panel_labels(ax)
    assert [v for v in jf.check(fig, warn=False) if v.kind == "text"] == []


def test_check_flags_wrong_figure_width():
    jf.use("nature")
    fig, ax = plt.subplots(figsize=(5.0, 3.0))
    assert any(v.kind == "width" for v in jf.check(fig, warn=False))


def test_check_flags_thin_lines_and_small_markers():
    jf.use("aps")
    fig, ax = plt.subplots(figsize=jf.figsize("aps", "single"))
    ax.plot([1, 2, 3], [1, 4, 9], linewidth=0.2, marker="o", markersize=1.0)
    kinds = {v.kind for v in jf.check(fig, warn=False)}
    assert {"line", "marker"} <= kinds


def test_check_ignores_artists_with_no_data():
    """A line with no vertices draws nothing, so its marker size cannot be a violation.

    Axes.boxplot creates a flier artist per box whether or not any point lies beyond the whiskers, so
    without this every empty one reported an undersized marker of its own.
    """
    jf.use("aps")
    fig, ax = jf.subplots("aps", width="single")
    ax.plot([], [], marker="o", markersize=0.5, linewidth=0.1)
    assert jf.check(fig, warn=False) == []

    samples = [[1.0, 2.0, 3.0, 4.0, 5.0], [1.0, 2.0, 3.0, 4.0, 200.0]]
    fig, ax = jf.subplots("aps", width="single")
    ax.boxplot(samples, flierprops={"marker": ".", "markersize": 1.0})  # 0.35 mm, below the 1.0 mm floor
    markers = [v for v in jf.check(fig, warn=False) if v.kind == "marker"]
    assert len(markers) == 1, "one violation for the one box that actually has a flier"


def test_check_flags_undersized_scatter_markers():
    """Axes.scatter makes a PathCollection, not a Line2D, and sizes it in points squared."""
    jf.use("aps")
    fig, ax = jf.subplots("aps", width="single")
    ax.scatter([1, 2, 3], [1, 2, 3], s=0.5)  # 0.7 pt across = 0.25 mm
    markers = [v for v in jf.check(fig, warn=False) if v.kind == "marker"]
    assert markers
    assert "0.25 mm" in markers[0].message


def test_check_passes_default_scatter():
    jf.use("aps")
    fig, ax = jf.subplots("aps", width="single")
    ax.scatter([1, 2, 3], [1, 2, 3])  # inherits lines.markersize = 4 pt -> 1.41 mm
    ax.set_xlabel("x (arb. units)")
    ax.set_ylabel("y (arb. units)")
    assert jf.check(fig, warn=False) == []


def test_check_ignores_collections_without_sizes():
    """fill_between makes a PolyCollection, which has no marker size to check."""
    jf.use("aps")
    fig, ax = jf.subplots("aps", width="single")
    x = [0.0, 0.5, 1.0]
    ax.fill_between(x, [0.0, 0.4, 0.9], [0.1, 0.6, 1.1])
    ax.set_xlabel("x (arb. units)")
    ax.set_ylabel("y (arb. units)")
    assert jf.check(fig, warn=False) == []


def test_fonts_reports_the_stack_the_theme_asks_for():
    jf.use("nature")
    status = jf.fonts()["text"]
    assert status.requested[0] == "Arial"
    assert "DejaVu Sans" in status.requested  # the stack ends in a bundled face so it degrades


def test_fonts_flags_a_silent_fallback(monkeypatch):
    """A machine with neither Arial nor Helvetica draws DejaVu, and nothing else says so."""
    jf.use("nature")
    _force_font(monkeypatch, "DejaVuSans.ttf")
    status = jf.fonts()["text"]
    assert (status.resolved, status.status) == ("DejaVu Sans", "fallback")

    fig, _ = jf.subplots("nature", width="single")
    violations = [v for v in jf.check(fig, warn=False) if v.kind == "font"]
    assert violations
    assert "DejaVu Sans" in violations[0].message
    assert "Arial" in violations[0].message


def test_fonts_accepts_a_metric_compatible_substitute(monkeypatch):
    """STIXGeneral ships with matplotlib and was cut to Times metrics, so APS still complies."""
    jf.use("aps")
    _force_font(monkeypatch, "STIXGeneral.ttf")
    assert jf.fonts()["text"].status == "substitute"

    fig, _ = jf.subplots("aps", width="single")
    assert [v for v in jf.check(fig, warn=False) if v.kind == "font"] == []


def test_fonts_covers_custom_mathtext_faces():
    jf.use("elsevier")  # mathtext.fontset: custom, every face pinned to Arial by name
    assert "mathtext.rm" in jf.fonts()
    jf.use("aps")  # mathtext.fontset: stix, bundled with matplotlib
    assert set(jf.fonts()) == {"text"}


def test_fonts_defers_to_latex_under_usetex():
    jf.use("aps")
    plt.rcParams["text.usetex"] = True
    assert jf.fonts() == {}


def test_fonts_reads_the_figure_rather_than_the_caller():
    """The point of fig=: a figure journalfig did not draw carries its own faces, not the caller's."""
    jf.use("nature")  # Arial
    fig, ax = plt.subplots()
    ax.set_xlabel("q", fontname="STIXGeneral")

    assert jf.fonts(journal="nature")["text"].requested[0] == "Arial"
    requested = {status.requested[0] for status in jf.fonts(journal="nature", fig=fig).values()}
    assert "STIXGeneral" in requested


def test_check_sees_a_per_artist_font_the_rcparams_hide():
    """A label given a face by hand is exactly what reading rcParams cannot catch."""
    jf.use("nature")
    fig, ax = jf.subplots("nature", width="single")
    ax.set_xlabel("q", fontname="DejaVu Serif")  # not an Arial substitute
    assert [v for v in jf.check(fig, warn=False) if v.kind == "font"]


def test_check_on_a_figure_from_another_toolchain():
    """No use() call, no journalfig-made figure: check() still answers for the named journal."""
    plt.rcParams["font.family"] = "DejaVu Sans"
    fig, ax = plt.subplots(figsize=jf.figsize("nature", "single"))
    ax.plot([0, 1], [0, 1])
    kinds = {v.kind for v in jf.check(fig, journal="nature", warn=False)}
    assert "font" in kinds  # DejaVu is neither an Arial nor a listed substitute
    assert "width" not in kinds  # but the geometry is right


def test_fonts_on_a_figure_with_no_text_at_all():
    """A bare figure has no Text artists, so there is nothing to report and nothing to flag."""
    jf.use("nature")
    fig = plt.figure(figsize=jf.figsize("nature", "single"))
    assert jf.fonts(fig=fig) == {}
    assert [v for v in jf.check(fig, warn=False) if v.kind == "font"] == []


def test_check_warns_by_default():
    jf.use("nature")
    fig, ax = plt.subplots(figsize=(5.0, 3.0))
    with pytest.warns(UserWarning, match="requirements not met"):
        jf.check(fig)


def test_check_without_active_theme_raises():
    jf._core._ACTIVE = None
    fig, _ = plt.subplots()
    with pytest.raises(RuntimeError, match="no active theme"):
        jf.check(fig, warn=False)


@pytest.mark.parametrize("journal", jf.JOURNALS)
def test_save_writes_pdf_svg_and_png_for_every_journal(tmp_path, journal):
    """One figure is usually wanted in all three: to submit, to edit, and to show."""
    jf.use(journal)
    fig, ax = plt.subplots(figsize=jf.figsize(journal, "single"))
    ax.plot([1, 2, 3], [1, 4, 9])
    with warnings.catch_warnings():
        # PLOS takes only TIFF and EPS, so its default write is legitimately all drafts. This test is
        # about which files appear, not about whether they can be submitted.
        warnings.simplefilter("ignore", jf.JournalFigWarning)
        written = jf.save(fig, tmp_path / "fig", validate=False)
    assert [p.suffix for p in written] == [".pdf", ".svg", ".png"]
    assert all(p.exists() and p.stat().st_size > 0 for p in written)
    # svg.fonttype "none" keeps text live and editable rather than converting glyphs to outlines.
    assert "<text" in (tmp_path / "fig.svg").read_text()


@pytest.mark.parametrize(
    ("journal", "fmt"),
    [("elsevier", "tiff"), ("aps", "eps"), ("nature", "pdf")],
)
def test_other_formats_stay_available_on_request(tmp_path, journal, fmt):
    """The default set is a convenience, not a restriction."""
    jf.use(journal)
    fig, ax = plt.subplots(figsize=jf.figsize(journal, "single"))
    ax.plot([1, 2, 3], [1, 4, 9])
    (written,) = jf.save(fig, tmp_path / "fig", formats=[fmt], validate=False)
    assert written.suffix == f".{fmt}"
    assert written.stat().st_size > 0


def test_save_compresses_tiff_losslessly(tmp_path):
    """An uncompressed 500 dpi Elsevier TIFF is several MB; LZW keeps the pixels and drops the bulk."""
    jf.use("elsevier")
    fig, ax = jf.subplots("elsevier", width="single")
    ax.plot([1, 2, 3], [1, 4, 9])

    (packed,) = jf.save(fig, tmp_path / "packed", formats=["tiff"], validate=False)
    (raw,) = jf.save(fig, tmp_path / "raw", formats=["tiff"], validate=False, pil_kwargs={})

    assert packed.stat().st_size < raw.stat().st_size / 5
    with Image.open(packed) as small, Image.open(raw) as large:
        assert small.info["compression"] == "tiff_lzw"
        assert small.size == large.size
        assert small.tobytes() == large.tobytes()  # lossless: identical pixels


def test_save_strips_an_existing_extension(tmp_path):
    jf.use("nature")
    fig, _ = plt.subplots(figsize=jf.figsize("nature", "single"))
    (written,) = jf.save(fig, tmp_path / "fig.png", formats=["pdf"], validate=False)
    assert written.name == "fig.pdf"


@pytest.mark.parametrize("journal", jf.JOURNALS)
def test_save_warns_when_nothing_written_is_submittable(tmp_path, journal):
    """Writing only formats a publisher rejects must say so. Which formats those are is per-journal:
    Nature takes neither PNG nor SVG, while IOP and Wiley take PNG and Science takes SVG."""
    spec = jf.get_spec(journal)
    rejected = [fmt for fmt in ("png", "svg") if fmt not in spec.submission_formats]
    if not rejected:
        pytest.skip(f"{spec.name} accepts both PNG and SVG as final artwork")
    jf.use(journal)
    fig, _ = plt.subplots(figsize=jf.figsize(journal, "single"))
    with pytest.warns(jf.JournalFigWarning, match="can be submitted"):
        jf.save(fig, tmp_path / "fig", formats=rejected, validate=False)


def _dpi_warnings(tmp_path, journal, name, **kwargs):
    """Save and return only the dpi-floor messages.

    A raster write to a journal that takes no raster artwork also raises the unrelated draft warning,
    so these tests select the message they are about rather than asserting nothing else was said.
    """
    fig, _ = plt.subplots(figsize=jf.figsize(journal, "single"))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        jf.save(fig, tmp_path / name, validate=False, **kwargs)
    plt.close(fig)
    return [str(w.message) for w in caught if "dpi is below the" in str(w.message)]


@pytest.mark.parametrize("journal", jf.JOURNALS)
def test_save_warns_below_the_raster_dpi_floor(tmp_path, journal):
    """A publisher states a minimum resolution; writing under it must not be silent."""
    spec = jf.get_spec(journal)
    if spec.raster_dpi is None:
        pytest.skip(f"{spec.name} states no resolution floor to fall below")
    jf.use(journal)
    (message,) = _dpi_warnings(tmp_path, journal, "low", formats=["png"], dpi=spec.raster_dpi - 1)
    assert f"minimum of {spec.raster_dpi} dpi" in message


@pytest.mark.parametrize("journal", jf.JOURNALS)
def test_save_accepts_a_raster_dpi_above_the_floor(tmp_path, journal):
    """Exceeding the minimum is compliant, so a generous dpi must not be flagged."""
    spec = jf.get_spec(journal)
    if spec.raster_dpi is None:
        pytest.skip(f"{spec.name} states no resolution floor to exceed")
    jf.use(journal)
    assert _dpi_warnings(tmp_path, journal, "high", formats=["png"], dpi=spec.raster_dpi * 2) == []


@pytest.mark.parametrize("journal", jf.JOURNALS)
def test_save_ignores_dpi_for_vector_only_writes(tmp_path, journal):
    """A vector file has no resolution, so a low dpi beside one is meaningless, not non-compliant."""
    jf.use(journal)
    assert _dpi_warnings(tmp_path, journal, "vector", formats=["pdf"], dpi=1) == []


@pytest.mark.parametrize("journal", jf.JOURNALS)
def test_every_submittable_format_saves_without_a_draft_warning(tmp_path, journal):
    """Regression: Elsevier accepts EPS, and warning that it does not made the format unusable there."""
    spec = jf.get_spec(journal)
    jf.use(journal)
    for fmt in spec.submission_formats:
        fig, _ = plt.subplots(figsize=jf.figsize(journal, "single"))
        with warnings.catch_warnings():
            warnings.simplefilter("error", jf.JournalFigWarning)
            (written,) = jf.save(fig, tmp_path / f"{journal}_{fmt}", formats=[fmt], validate=False)
        assert written.stat().st_size > 0
        plt.close(fig)


@pytest.mark.parametrize("journal", jf.JOURNALS)
def test_the_default_write_is_flagged_only_where_nothing_default_is_accepted(tmp_path, journal):
    """A companion beside a submittable file is silent. PLOS is the one theme where nothing in the
    default set qualifies -- it takes TIFF or EPS only -- and there the warning is correct."""
    spec = jf.get_spec(journal)
    submittable = [fmt for fmt in spec.formats if fmt in spec.submission_formats]
    jf.use(journal)
    fig, _ = plt.subplots(figsize=jf.figsize(journal, "single"))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        written = jf.save(fig, tmp_path / "fig", validate=False)
    drafts = [w for w in caught if "treat these as drafts" in str(w.message)]
    assert bool(drafts) is not bool(submittable)
    assert [p.suffix for p in written] == [".pdf", ".svg", ".png"]


def test_theme_uses_a_true_minus_sign():
    """Asserted on the rcParam, because no rendered figure can see it.

    With ``axes.formatter.use_mathtext`` on -- which every theme sets -- mathtext already typesets a
    hyphen as a proper minus, so the two settings are pixel-identical and the image-comparison tests
    cannot guard this. It matters only where a user turns mathtext off.
    """
    for journal in jf.JOURNALS:
        jf.use(journal)
        assert plt.rcParams["axes.unicode_minus"] is True


def test_theme_renders_every_vertex():
    """matplotlib drops vertices below path.simplify_threshold, altering dense curves in the file."""
    for journal in jf.JOURNALS:
        jf.use(journal)
        assert plt.rcParams["path.simplify_threshold"] == 0.0


def test_label_lines_uses_each_line_label_and_colour():
    jf.use("elsevier")
    fig, ax = jf.subplots("elsevier")
    (first,) = ax.plot([1, 2, 3], [1, 4, 9], label="Series A")
    (second,) = ax.plot([1, 2, 3], [2, 5, 10], label="Series B")

    texts = jf.label_lines(ax)
    assert [t.get_text() for t in texts] == ["Series A", "Series B"]
    assert texts[0].get_color() == first.get_color()
    assert texts[1].get_color() == second.get_color()


def test_label_lines_skips_unlabelled_lines_and_accepts_overrides():
    jf.use("aps")
    fig, ax = jf.subplots("aps")
    ax.plot([1, 2], [1, 2])  # no label -> matplotlib names it "_child0"
    ax.plot([1, 2], [2, 3], label="Series A")

    assert [t.get_text() for t in jf.label_lines(ax)] == ["Series A"]
    assert [t.get_text() for t in jf.label_lines(ax, labels=["Renamed"])] == ["Renamed"]


def test_label_lines_anchors_to_the_last_finite_point():
    """A trailing NaN is a gap, not a position; anchoring there would put the label nowhere."""
    jf.use("nature")
    fig, ax = jf.subplots("nature")
    ax.plot([1.0, 2.0, 3.0], [1.0, 4.0, float("nan")], label="Series A")

    (text,) = jf.label_lines(ax)
    assert text.xy == (2.0, 4.0)


def test_label_lines_handles_a_date_axis():
    """Dates are not convertible to float; treating that as non-finite would discard every point."""
    import datetime as dt

    jf.use("elsevier")
    fig, ax = jf.subplots("elsevier")
    days = [dt.date(2026, 1, day) for day in (1, 2, 3)]
    ax.plot(days, [1.0, 2.0, 3.0], label="Series A")

    (text,) = jf.label_lines(ax)
    assert text.get_text() == "Series A"


def test_check_flags_an_unrasterized_heavy_artist(monkeypatch):
    jf.use("nature")
    fig, ax = jf.subplots("nature")
    monkeypatch.setattr(jf._core, "VECTOR_ELEMENT_LIMIT", 100)
    ax.scatter(range(500), range(500))

    violations = [v for v in jf.check(fig, warn=False) if v.kind == "vector"]
    assert violations
    assert "rasterized=True" in violations[0].message


def test_check_accepts_a_rasterized_heavy_artist(monkeypatch):
    jf.use("nature")
    fig, ax = jf.subplots("nature")
    monkeypatch.setattr(jf._core, "VECTOR_ELEMENT_LIMIT", 100)
    ax.scatter(range(500), range(500), rasterized=True)

    assert [v for v in jf.check(fig, warn=False) if v.kind == "vector"] == []


def test_check_ignores_an_ordinary_plot():
    """The limit must sit well past what a normal figure produces, or it is noise."""
    jf.use("aps")
    fig, ax = jf.subplots("aps")
    ax.plot(range(2000), range(2000))
    ax.scatter(range(1000), range(1000))

    assert [v for v in jf.check(fig, warn=False) if v.kind == "vector"] == []


@pytest.mark.parametrize(("mode", "expect_text"), [("none", True), ("path", False)])
def test_save_svg_text_mode(tmp_path, mode, expect_text):
    """Live text is editable but needs the font; outlined paths render identically anywhere."""
    jf.use("elsevier")
    fig, ax = jf.subplots("elsevier")
    ax.set_xlabel("Label")

    with warnings.catch_warnings():
        # SVG alone is not submittable anywhere, which save() rightly says; not what this test is about.
        warnings.simplefilter("ignore", jf.JournalFigWarning)
        (written,) = jf.save(fig, tmp_path / f"fig_{mode}", formats=["svg"], validate=False, svg_text=mode)
    assert ("<text" in written.read_text()) is expect_text


def test_save_svg_text_does_not_leak_into_later_figures(tmp_path):
    jf.use("elsevier")
    fig, ax = jf.subplots("elsevier")
    ax.set_xlabel("Label")
    before = plt.rcParams["svg.fonttype"]

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", jf.JournalFigWarning)
        jf.save(fig, tmp_path / "fig", formats=["svg"], validate=False, svg_text="path")
    assert plt.rcParams["svg.fonttype"] == before


@pytest.mark.skipif(shutil.which("latex") is None, reason="requires a LaTeX installation")
@pytest.mark.parametrize("journal", jf.JOURNALS)
def test_usetex_renders(tmp_path, journal):
    jf.use(journal, usetex=True)
    assert plt.rcParams["text.usetex"] is True
    fig, ax = plt.subplots(figsize=jf.figsize(journal, "single"))
    ax.plot([1, 2, 3], [1, 4, 9])
    ax.set_xlabel(r"$q$ (\AA$^{-1}$)")
    ax.set_ylabel(r"$S(q)$")
    with warnings.catch_warnings():
        # ACS and PLOS do not take PDF as final artwork; this test is about LaTeX rendering, not that.
        warnings.simplefilter("ignore", jf.JournalFigWarning)
        (written,) = jf.save(fig, tmp_path / "fig", formats=["pdf"], validate=False)
    assert written.stat().st_size > 0
