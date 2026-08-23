"""Image-comparison tests: catch a theme change that alters what a figure looks like.

The rest of the suite asserts numbers -- widths, font sizes, violation kinds. None of it notices an
edit to a ``.mplstyle`` that moves tick direction, legend spacing, or spine weight, because every
assertion still holds while the rendered figure changes. These tests close that gap by rendering a
figure per theme and comparing it against a committed baseline.

Typography is deliberately normalised to matplotlib's own DejaVu faces before rendering. A baseline
made on a machine with Arial installed would never match a CI runner without it, and pinning the
whole matrix to one font situation is not possible. What is left under test is everything else the
theme controls -- sizes, spines, ticks, colours, line weights, layout, panel labels -- which is where
a silent regression would actually live. Which typeface a machine resolves to is covered separately
and thoroughly by the ``fonts()`` and ``check()`` tests in ``test_journalfig.py``.

Choosing the face is not enough to make a baseline portable, though: **the FreeType version rasterises
it**. matplotlib's PyPI wheels bundle FreeType 2.6.1 -- pinned precisely so image baselines reproduce --
while a conda-forge build links whatever the channel ships (2.14.1 at the time of writing). The same
figure under the two differs by an RMS of 2 to 16 against a tolerance of 2, worst on single-column
figures, where at 89 mm and 100 dpi the image is only ~350 px wide and glyphs are a large share of it.
So the baselines here are rendered with the wheel, and any environment on a different FreeType skips
the comparison rather than reporting a failure it cannot fix. The CI job asserts the version, so the
skip cannot quietly disable the check where it counts.

Given the same FreeType, platform barely matters: the RMS values this file produced on macOS matched
those from the Linux CI runner to full double precision on six of seven cases, and to 5e-5 on the
seventh.

Baselines live in ``tests/baseline/`` and are compared only when pytest runs with ``--mpl``; without
it these still execute, so they catch exceptions everywhere, but assert nothing about pixels.
Regenerate after an intentional change from a wheel-installed environment, matching the version CI
pins::

    python -m venv /tmp/mplbaseline
    /tmp/mplbaseline/bin/pip install -e ".[test]" matplotlib==3.10.9
    /tmp/mplbaseline/bin/python -m pytest --mpl-generate-path=tests/baseline tests/test_visual.py

Author: Achraf Atila (achraf.atila@bam.de)
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib import ft2font

import journalfig as jf

#: Small enough to keep baselines in the tens of kB; the themes render at 600 dpi by default.
SAVEFIG = {"dpi": 100, "bbox_inches": None}

#: The version bundled in matplotlib's wheels, and the one the baselines were rendered with.
BASELINE_FREETYPE = "2.6.1"


@pytest.fixture(autouse=True)
def _deterministic_typography():
    """Render with matplotlib's bundled faces so the baseline is machine-independent."""
    yield
    plt.close("all")


@pytest.fixture(autouse=True)
def _skip_comparison_on_another_freetype(request):
    """Compare pixels only against the FreeType the baselines were rendered with.

    A different build rasterises the same glyphs differently, which reports as a failure the
    contributor cannot act on. Skipping is safe because the CI job asserts the version first.
    """
    if request.config.getoption("--mpl", default=False) and ft2font.__freetype_version__ != BASELINE_FREETYPE:
        pytest.skip(
            f"baselines were rendered with FreeType {BASELINE_FREETYPE}; this environment has "
            f"{ft2font.__freetype_version__}. Install matplotlib from a PyPI wheel to compare."
        )


def _normalise_fonts() -> None:
    plt.rcParams["font.family"] = "DejaVu Sans"
    plt.rcParams["mathtext.fontset"] = "dejavusans"
    plt.rcParams["mathtext.rm"] = "DejaVu Sans"
    plt.rcParams["mathtext.it"] = "DejaVu Sans:italic"
    plt.rcParams["mathtext.bf"] = "DejaVu Sans:bold"


def _curves() -> tuple[np.ndarray, list[np.ndarray]]:
    """Analytic, seed-free data, so the baseline depends only on the theme."""
    q = np.linspace(0.5, 12.0, 400)
    curves = [
        1 + 1.6 * np.exp(-(((q - 2.1) / w) ** 2)) + 0.4 * np.exp(-(((q - 5.2) / (w * 1.4)) ** 2))
        for w in (0.8, 1.2, 1.8)
    ]
    return q, curves


@pytest.mark.parametrize("journal", jf.JOURNALS)
@pytest.mark.mpl_image_compare(savefig_kwargs=SAVEFIG, style="default")
def test_single_column_figure(journal):
    """The prop cycle, tick marks, minor ticks, legend, and mathtext labels together."""
    jf.use(journal)
    _normalise_fonts()
    fig, ax = jf.subplots(journal, width="single")

    q, curves = _curves()
    for width, sq in zip((0.8, 1.2, 1.8), curves, strict=True):
        ax.plot(q, sq, label=f"{width:.1f} GPa")
    ax.set_xlabel(r"$q$ (Å$^{-1}$)")
    ax.set_ylabel(r"$S(q)$")
    ax.legend(title="Pressure")
    return fig


@pytest.mark.parametrize("journal", jf.JOURNALS)
@pytest.mark.mpl_image_compare(savefig_kwargs=SAVEFIG, style="default")
def test_panel_labels_and_shared_axes(journal):
    """Panel-label placement and format, which differ per publisher."""
    jf.use(journal)
    _normalise_fonts()
    fig, axs = jf.subplots(journal, 1, 2, width="double", ratio=0.38)

    q, curves = _curves()
    axs[0].plot(q, curves[0])
    axs[0].fill_between(q, curves[0] - 0.15, curves[0] + 0.15, alpha=0.25, linewidth=0)
    axs[0].set_xlabel(r"$q$ (Å$^{-1}$)")
    axs[0].set_ylabel(r"$S(q)$")

    pressure = np.array([0.0, 3.0, 6.0, 10.0, 15.0, 20.0, 30.0])
    axs[1].errorbar(pressure, 1.6 - 0.03 * pressure, yerr=0.05, marker="o")
    axs[1].set_xlabel(r"$P$ (GPa)")
    axs[1].set_ylabel(r"$R'_{\mathrm{Li-Li}}$")

    jf.panel_labels(axs, journal=journal)
    return fig


@pytest.mark.mpl_image_compare(savefig_kwargs=SAVEFIG, style="default")
def test_mosaic_layout():
    """Unequal panels: the ratios and the spanning behaviour that mosaic() exists for."""
    jf.use("nature")
    _normalise_fonts()
    fig, panels = jf.mosaic(
        "nature",
        "AAB\nAAC\nDDD",
        width="double",
        ratio=0.72,
        width_ratios=[1.0, 1.0, 1.15],
        height_ratios=[1.0, 1.0, 0.85],
    )

    grid = np.linspace(-3, 3, 60)
    density = np.exp(-((grid[:, None] ** 2 + grid[None, :] ** 2) / 3.0))
    panels["A"].imshow(density, extent=(0, 30, 0, 30), origin="lower")
    q, curves = _curves()
    panels["B"].plot(q, curves[0])
    panels["C"].plot(q, curves[2])
    panels["D"].plot(q, curves[1])
    for name in "ABCD":
        panels[name].set_xlabel(r"$x$")
    jf.panel_labels(panels, journal="nature")
    return fig


@pytest.mark.parametrize("journal", jf.JOURNALS)
@pytest.mark.mpl_image_compare(savefig_kwargs=SAVEFIG, style="default")
def test_dense_curve_path_fidelity(journal):
    """Guards ``path.simplify_threshold``, which the other cases cannot see.

    Every other figure here plots a few hundred points on a smooth curve, where matplotlib's vertex
    simplification has nothing to discard. This one plots a dense noisy trace, where the default
    threshold of 0.111 drops enough detail to move 11% of the pixels -- so a revert of that setting
    fails here rather than shipping silently.

    It does not guard ``axes.unicode_minus``, despite spanning zero: with ``use_mathtext`` on, a
    hyphen and a true minus render to identical pixels. The rcParam is asserted directly in
    ``test_journalfig.py`` instead.
    """
    jf.use(journal)
    _normalise_fonts()
    fig, ax = jf.subplots(journal, width="single")

    x = np.linspace(-6.0, 6.0, 4000)
    ax.plot(x, np.sin(x) + 0.35 * np.sin(37.0 * x))
    ax.plot(x, np.cos(x) - 1.5)
    ax.set_xlabel("x (a.u.)")
    ax.set_ylabel("y (a.u.)")
    return fig
