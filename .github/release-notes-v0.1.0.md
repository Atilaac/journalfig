# Release notes for v0.1.0

Seed for the first GitHub Release. Release Drafter assembles later releases from merged pull request
titles, but it has no pull request history to work from for this one -- everything below arrived in the
initial commit -- so this file carries it across. Paste it into the v0.1.0 release body and delete the
file; from v0.2.0 onward the draft release is the changelog and there is no file to maintain.

**Not yet reviewed against the current package.** These entries were written when journalfig shipped three
themes on Python 3.10-3.13. It now ships twelve and requires 3.12, and the two notes below about the
initial version and about dropping 3.10/3.11 contradict each other. Reconcile before publishing.

### Added

- `jf.label_lines()`, which names each curve at its end instead of in a legend box.
- `svg_text=` on `jf.save()`, choosing live editable text or outlined glyphs for an SVG.
- A `vector` rule in `jf.check()`: an un-rasterized artist past `VECTOR_ELEMENT_LIMIT` (50,000
  elements) makes a file large enough to be refused. It is the only rule in the checker not traceable
  to a publisher document, and it is labelled as such.
- Scientific colour maps (Crameri) in the heatmap notebook through an optional `examples` extra, with
  a fallback to matplotlib's built-ins when the package is absent.

- `JournalFigWarning`, the category every compliance warning is now raised under, so it can be silenced
  without suppressing unrelated `UserWarning`s.
- `journalfig.source(journal)` and the `Source` dataclass, recording the publisher document behind each
  theme along with the date its numbers were last checked against it.
- `py.typed`, so the annotations already in the source are visible to downstream type checkers.
- Continuous integration across Linux, macOS, and Windows on Python 3.10-3.13, with no journal typeface
  installed, plus lint, docs, packaging, and an end-to-end run of `demo.py`.
- MkDocs documentation site with an API reference generated from the docstrings.
- Image-comparison tests (`pytest --mpl`) with committed baselines, covering the one class of regression
  the rest of the suite is blind to: a theme edit that changes what every figure looks like while every
  numeric assertion still holds.
- A minimum-versions CI job installs matplotlib 3.8 on Python 3.10, so the declared floor is tested
  rather than assumed.
- Tests treat an unexpected `JournalFigWarning` as a failure, so a figure that quietly stops complying
  cannot pass CI.

- SVG and PNG are available for every journal alongside its submission formats, for editing and for
  talks; convert from there as needed.
- The single tour notebook is split into six focused, standalone notebooks: getting started, line plots,
  scatter plots, histograms, heatmaps, and multi-panel figures. All use synthetic data and generic axis
  labels. Every one is executed in CI (`pytest --nbval-lax examples/`), so they cannot go stale unnoticed.
- A seventh notebook reads a data file from `examples/data/`, fits a sinusoid to it with weighted
  `curve_fit`, and reports pulls, reduced chi-squared and a residual panel. The data file records its own
  model, parameters and seed, and `examples/data/make_oscillation.py` regenerates it byte-identically.
- An eighth notebook covers box plots: the five-number summary, the difference between matplotlib's
  default 1.5 x IQR whiskers and the literal minimum and maximum (`whis=(0, 100)`), colouring boxes the
  property cycle never reaches, flier size against the APS symbol minimum, jittered overlays that restore
  the sample size a box plot hides, notches, and horizontal layout across the matplotlib
  `vert`/`orientation` rename.

### Changed

- Themes render every vertex (`path.simplify_threshold: 0.0`). matplotlib's default of 0.111 silently
  drops points: on a dense noisy trace that moved 11% of pixels, so the exported curve was not the
  curve that was plotted. A 20k-point line grows from 21 kB to 194 kB in PDF; `rasterized=True` is the
  answer where that matters, not discarding data.
- Themes ask for a true minus (`axes.unicode_minus: True`). With `use_mathtext` on this is
  pixel-identical, since mathtext already typesets a hyphen as a minus; it matters only if that is
  turned off.

- `save()` reports the size written through the `journalfig` logger at INFO level rather than printing to
  stdout. Call `logging.getLogger("journalfig").setLevel("INFO")` to see it as before — a blanket
  `logging.basicConfig(level="INFO")` also switches on fontTools, which logs a dozen lines per PDF.
- `subplots()` and `mosaic()` carry precise type annotations (`tuple[Figure, Any]`,
  `str | list[list[Hashable]]`).
- Every theme writes PDF, SVG and PNG by default; TIFF, EPS and anything else the backend supports are
  available through `formats=`. `JournalSpec.formats` (what gets written) and the new
  `JournalSpec.submission_formats` (what the publisher accepts as final artwork) are now separate, which
  also replaces the `raster_rejected` flag and extends the draft warning to APS and Elsevier.
- Elsevier accepts EPS and JPEG as final artwork, per its artwork formats checklist; saving either no longer warns.
- EPS is no longer a default for any theme. It remains available on request, but the
  PostScript backend flattens transparency, so an EPS and the PDF of the same figure disagree wherever an
  artist has `alpha < 1`.
- The draft warning in `save()` fires once per call and only when nothing written is submittable, instead
  of once per raster file. Asking for a PNG or SVG beside a PDF is now silent.
- `SOURCES` maps each theme to a `Source` object instead of a bare URL string; use `.url` for the
  previous value.

### Fixed


- The image-comparison baselines are rendered against FreeType 2.6.1, the version matplotlib's PyPI
  wheels bundle, and the tests skip the pixel comparison on any other build instead of failing. They had
  been generated with a conda-forge matplotlib linking FreeType 2.14.1, which rasterises the same glyphs
  differently and missed the tolerance by an RMS of 2 to 16 on the CI runner. The CI job now asserts the
  FreeType version, so the skip cannot silently disable the check, and pins matplotlib exactly rather
  than to a `3.10.*` range.

- `check()` no longer reports a violation for an artist that draws nothing. `Axes.boxplot` creates a flier
  line per box whether or not any point lies beyond the whiskers, so a five-box plot with small fliers
  reported five undersized-marker violations when only three boxes had fliers to measure.

### Known issues

- `jf.use("aps", usetex=True)` needs matplotlib >= 3.10 on TeX installations without a Type 1 entry for
  `mathptmx`; 3.8 and 3.9 raise `LookupError` at save time. CI runners carry no LaTeX, so no job covers
  this — it was found by running the suite against the floor by hand.

### Removed

- **No type checker runs in CI.** mypy was set up during development and taken out again before release,
  so the `[tool.mypy]` configuration, the CI job and the dev dependency are all absent by choice.
  `py.typed` and the annotations still ship, which means downstream checkers read annotations that
  nothing here verifies — treat them as an author's promise, not a tested fact.
- **Python 3.10 and 3.11 support.** `requires-python` is now `>=3.12`; the CI matrix runs 3.12, 3.13 and
  3.14 across Linux, macOS and Windows. Nothing in the package required the change — it still imports and
  passes on 3.10 — so pin `journalfig<next` on an older interpreter if you need one. `matplotlib>=3.8`
  is unchanged and still tested, on 3.12: matplotlib 3.8 is the last series with cp312 wheels, so it is
  also the last that can satisfy both floors at once.

- `pypdf` from the development dependencies -- it was never imported; the PDF width test parses
  `/MediaBox` directly.

## Initial version

Initial version: Nature, APS, and Elsevier themes; exact column-width figure factories (`figure`,
`subplots`, `mosaic`, `gridspec`); `check()` compliance reporting; `fonts()` substitution reporting; and
`save()` writing each publisher's accepted formats.
