"""Render one example figure in every bundled theme, for visual comparison.

Run with ``python demo.py``; output lands in ``gallery/``.

Author: Achraf Atila (achraf.atila@bam.de)
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

import journalfig as jf

GALLERY = Path(__file__).parent / "gallery"


def build(journal: str) -> plt.Figure:
    """Draw a four-panel example figure using the given theme.

    Panels exercise the parts of a style that usually need hand-tuning: a multi-curve line plot, a
    scatter with error bars, a filled band, and a heatmap with a colour bar.

    Args:
        journal: Theme key or journal alias.

    Returns:
        The finished figure, sized to the journal's double-column width.
    """
    rng = np.random.default_rng(0)
    fig, axs = jf.subplots(journal, 2, 2, width="double", ratio=0.62)

    q = np.linspace(0.5, 12.0, 600)
    for width in (0.8, 1.2, 1.8):
        sq = 1 + np.exp(-(((q - 2.1) / width) ** 2)) * 1.6 + 0.4 * np.exp(-(((q - 5.2) / (width * 1.4)) ** 2))
        axs[0, 0].plot(q, sq, label=f"{width:.1f} GPa")
    axs[0, 0].set_xlabel(r"$q$ (Å$^{-1}$)")
    axs[0, 0].set_ylabel(r"$S(q)$")
    axs[0, 0].legend(title="Pressure")

    pressure = np.array([0, 3, 6, 10, 15, 20, 30])
    ratio = 1.6 - 0.03 * pressure + rng.normal(0, 0.02, pressure.size)
    error = np.full_like(ratio, 0.05)
    axs[0, 1].errorbar(pressure, ratio, yerr=error, marker="o", capsize=plt.rcParams["errorbar.capsize"])
    axs[0, 1].axhline(1.0, color=jf.COLORS["black"], linestyle=":", linewidth=0.8)
    axs[0, 1].set_xlabel(r"$P$ (GPa)")
    axs[0, 1].set_ylabel(r"$R'_{\mathrm{Li-Li}}$")

    r = np.linspace(0, 8, 400)
    gr = np.exp(-(((r - 2.6) / 0.35) ** 2)) * 3.2 + np.exp(-(((r - 4.9) / 0.7) ** 2)) * 1.1
    axs[1, 0].plot(r, gr, color=jf.COLORS["blue"])
    axs[1, 0].fill_between(r, gr - 0.15, gr + 0.15, color=jf.COLORS["blue"], alpha=0.25, linewidth=0)
    axs[1, 0].set_xlabel(r"$r$ (Å)")
    axs[1, 0].set_ylabel(r"$g(r)$")

    grid = np.exp(-((np.linspace(-3, 3, 80)[:, None] ** 2 + np.linspace(-3, 3, 80)[None, :] ** 2) / 4))
    mesh = axs[1, 1].imshow(grid, extent=(0, 30, 0, 30), aspect="auto")
    bar = fig.colorbar(mesh, ax=axs[1, 1])
    bar.set_label(r"$\rho$ (Å$^{-3}$)")
    axs[1, 1].set_xlabel(r"$x$ (Å)")
    axs[1, 1].set_ylabel(r"$y$ (Å)")

    jf.panel_labels(axs, journal=journal)
    return fig


def build_mosaic(journal: str) -> plt.Figure:
    """Draw an example figure whose panels differ in size.

    A large map panel carries the result, two small panels beside it carry the supporting curves,
    and a wide strip underneath carries a shared abscissa -- the arrangement a four-panel figure
    usually wants once the panels stop being interchangeable.

    The map sits in the *last* column on purpose; see the comment on its colour bar.

    Args:
        journal: Theme key or journal alias.

    Returns:
        The finished figure, sized to the journal's double-column width.
    """
    rng = np.random.default_rng(1)
    fig, panels = jf.mosaic(
        journal,
        "ABB\nCBB\nDDD",
        width="double",
        ratio=0.72,
        width_ratios=[1.15, 1.0, 1.0],
        height_ratios=[1.0, 1.0, 0.85],
    )

    q = np.linspace(0.5, 12.0, 600)
    for pressure in (0.8, 1.8):
        sq = 1 + 1.6 * np.exp(-(((q - 2.1) / pressure) ** 2)) + 0.4 * np.exp(-(((q - 5.2) / (pressure * 1.4)) ** 2))
        panels["A"].plot(q, sq, label=f"{pressure:.1f} GPa")
    panels["A"].set_xlabel(r"$q$ (Å$^{-1}$)")
    panels["A"].set_ylabel(r"$S(q)$")
    panels["A"].legend()

    x = np.linspace(-3, 3, 160)
    density = np.exp(-((x[:, None] ** 2 + x[None, :] ** 2) / 3.0)) + 0.15 * rng.normal(size=(160, 160))
    mesh = panels["B"].imshow(density, extent=(0, 30, 0, 30), origin="lower", aspect="auto")
    # The map is in the last column because constrained layout mis-places a colour bar that lands in
    # an *interior* column of a grid some other panel spans -- here the wide strip D. matplotlib
    # reserves the bar's width in that column's `rightcb` margin, then `match_submerged_margins`
    # copies `right + rightcb` into `right` so the gutters of the spanning panel line up, counting the
    # bar a second time. The bar then floats roughly midway between its map and the next panel, by a
    # figure width of 0.10 rather than 0.02. An outer column has no submerged margin, so it is exact.
    bar = fig.colorbar(mesh, ax=panels["B"], pad=0.02)
    bar.set_label(r"$\rho$ (Å$^{-3}$)")
    panels["B"].set_xlabel(r"$x$ (Å)")
    panels["B"].set_ylabel(r"$y$ (Å)")

    pressure = np.array([0, 3, 6, 10, 15, 20, 30])
    coordination = 4.0 - 0.02 * pressure + rng.normal(0, 0.03, pressure.size)
    panels["C"].errorbar(pressure, coordination, yerr=0.06, marker="o", capsize=plt.rcParams["errorbar.capsize"])
    panels["C"].set_xlabel(r"$P$ (GPa)")
    panels["C"].set_ylabel(r"$N_{\mathrm{O}}$")

    r = np.linspace(0, 8, 400)
    gr = 3.2 * np.exp(-(((r - 2.6) / 0.35) ** 2)) + 1.1 * np.exp(-(((r - 4.9) / 0.7) ** 2))
    panels["D"].plot(r, gr, color=jf.COLORS["blue"])
    panels["D"].fill_between(r, gr - 0.15, gr + 0.15, color=jf.COLORS["blue"], alpha=0.25, linewidth=0)
    panels["D"].set_xlabel(r"$r$ (Å)")
    panels["D"].set_ylabel(r"$g(r)$")

    jf.panel_labels(panels, journal=journal)
    return fig


def main() -> None:
    """Render and save both example figures in every bundled theme."""
    GALLERY.mkdir(exist_ok=True)
    for journal in jf.JOURNALS:
        jf.use(journal)
        for name, make in (("", build), ("_mosaic", build_mosaic)):
            fig = make(journal)
            jf.save(fig, GALLERY / f"{journal}{name}", formats=["pdf", "png"], validate=True)
            plt.close(fig)


if __name__ == "__main__":
    main()
