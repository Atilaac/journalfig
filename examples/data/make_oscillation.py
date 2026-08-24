"""Regenerate the synthetic data set used by ``examples/06_reading_and_fitting.ipynb``.

The data is not a measurement of anything. It is a sinusoid with Gaussian noise, written out so the
notebook has a real file to read rather than an array conjured in the cell above the plot. Every
parameter and the seed are recorded in the file's own header, so the numbers are reproducible.

Run from the repository root::

    python examples/data/make_oscillation.py

Author: Achraf Atila (achraf.atila@bam.de)
"""

from __future__ import annotations

import pathlib

import numpy as np

SEED = 20260805
AMPLITUDE = 2.5
FREQUENCY = 0.35
PHASE = 0.8
OFFSET = 0.4
SIGMA = 0.35
N_POINTS = 60
X_MAX = 12.0

OUT = pathlib.Path(__file__).parent / "oscillation.dat"


def main() -> None:
    """Write the data set, with its provenance in the header."""
    rng = np.random.default_rng(SEED)
    x = np.linspace(0.0, X_MAX, N_POINTS)
    clean = AMPLITUDE * np.sin(2 * np.pi * FREQUENCY * x + PHASE) + OFFSET
    y = clean + rng.normal(0.0, SIGMA, x.size)
    y_err = np.full_like(y, SIGMA)

    header = (
        "Synthetic demonstration data for the journalfig example notebooks.\n"
        "Not a measurement of anything: a sinusoid plus Gaussian noise.\n"
        "\n"
        "model  : y = A * sin(2*pi*f*x + phi) + c, noise ~ Normal(0, sigma)\n"
        f"params : A={AMPLITUDE}  f={FREQUENCY}  phi={PHASE}  c={OFFSET}  sigma={SIGMA}\n"
        f"seed   : numpy.random.default_rng({SEED})\n"
        f"source : examples/data/{OUT.name} written by examples/data/{pathlib.Path(__file__).name}\n"
        "\n"
        "columns below, whitespace separated: x (a.u.), y (a.u.), y_err (a.u.)"
    )
    # Whitespace separated, which np.loadtxt reads with no delimiter argument at all.
    np.savetxt(OUT, np.column_stack([x, y, y_err]), fmt="%12.6f", header=header + "\n x  y  y_err")

    # savetxt prefixes every header line with "# ", so a blank one is left holding a trailing space.
    # The repository's trailing-whitespace hook would strip it and the committed file would then no
    # longer be what this script writes -- which is the one property the file is here to have.
    lines = OUT.read_text(encoding="utf-8").splitlines()
    OUT.write_text("\n".join(line.rstrip() for line in lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.1f} kB, {N_POINTS} rows)")


if __name__ == "__main__":
    main()
