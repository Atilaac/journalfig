# Release notes for v0.1.0

Seed for the first GitHub Release. Release Drafter assembles later releases from merged pull request
titles, but it has no pull request history to work from for this one -- everything below arrived in the
initial commit -- so this file carries it across. Paste it into the v0.1.0 release body and delete the
file; from v0.2.0 onward the draft release is the changelog and there is no file to maintain.

---

First release. Twelve matplotlib themes whose every number is read from a publisher's own author
guidelines, plus a checker that reports where a figure violates them. Retargeting a figure from one
journal to another is a one-string change.

## Themes

`nature`, `aps`, `elsevier`, `iop`, `aip`, `acs`, `rsc`, `ieee`, `plos`, `wiley`, `pnas`, `science`,
reachable by publisher key or by journal name -- `jf.use("PRB")`, `jf.use("Acta Materialia")`.

Every width, font size, minimum and accepted format cites the document it came from, with the date it was
last checked against it: `jf.source("aps")` returns that record, and `docs/specifications.md` prints all
twelve.

Six values are not quoted directly and are marked `DERIVED` beside the number. Four are unit conversions
of figures PLOS does publish -- two widths and a maximum height stated in pixels at 300 dpi, and a line
minimum stated in millimetres. The other two are the APS 1.5- and 2-column widths, the only genuinely
inferred numbers in the package: APS publishes neither, and both follow from standard REVTeX two-column
geometry.

Not every publisher states every rule, and the gaps are recorded as `None` rather than filled with a
plausible number. IOP and IEEE state no resolution; AIP and Wiley name no typeface, so `jf.fonts()`
reports `unrestricted` for them instead of calling every face a fallback.

## API

- Figure factories at exact column widths: `figure`, `subplots`, `mosaic`, `gridspec`. Each pins the
  requested size so an interactive backend cannot round it away, and `save()` re-asserts it before
  writing.
- `check(fig)` reports violations -- width, font size, line weight, marker size, typeface, resolution,
  submission format -- and works on any figure, including one built without journalfig.
- `fonts()` reports what each typeface actually resolved to on this machine.
- `save()` writes each publisher's formats, warns when nothing written is submittable, and reports the
  size it wrote through the `journalfig` logger at INFO level rather than printing. Call
  `logging.getLogger("journalfig").setLevel("INFO")` to see it; a blanket `logging.basicConfig` also
  switches on fontTools, which logs a dozen lines per PDF.
- `panel_labels()` letters panels in each publisher's convention, and `label_lines()` names each curve at
  its end instead of in a legend box.
- `svg_text=` on `save()` chooses live editable text or outlined glyphs for an SVG, scoped to that one
  write.
- `use(journal, base_size=...)` scales a whole theme, keeping the ratios between its font sizes.
- `context(journal)` applies a theme temporarily and restores what was there.
- `plt.style.use("nature")` works after a bare `import journalfig`.

## Command line

`journalfig check <target> [-j journal]` runs a `.py` file or a `module:function` and checks every figure
it produces; `journalfig journals` lists the themes. Exit codes are the contract, for use in a paper
repository's CI: **0** compliant, **1** violations found, **2** the target could not be loaded -- a
missing file must never read as "your figures are fine". `python -m journalfig` is equivalent.

It does not read PDFs. A matplotlib figure cannot be reconstructed from one, and the narrower set of
questions a PDF can answer is a different feature.

## Choices worth knowing about

- **Themes render every vertex** (`path.simplify_threshold: 0.0`). matplotlib's default of 0.111 silently
  drops points: on a dense noisy trace that moved 11% of pixels, so the exported curve was not the curve
  that was plotted. A 20k-point line grows from 21 kB to 194 kB in PDF; `rasterized=True` is the answer
  where that matters, not discarding data.
- **Themes ask for a true minus** (`axes.unicode_minus: True`). With `use_mathtext` on this is
  pixel-identical, since mathtext already typesets a hyphen as a minus; it matters only if that is turned
  off.
- **Resolution is a floor, not a target.** Publishers state a minimum -- Nature 300, Elsevier 300/500/1000
  by artwork type, APS 600 -- so the themes' `savefig.dpi: 600` clears all of them. Only falling below the
  stated number is a violation, and `save()` warns only when an explicit `dpi=` drops under it for a
  raster format.
- **What `save()` writes and what a publisher accepts are separate questions.** Every theme writes PDF,
  SVG and PNG by default -- one to submit, one to edit, one for a talk -- while `submission_formats`
  records what the publisher takes as final artwork and drives the draft warning. The warning fires once
  per `save()` call and only when *nothing* written is submittable, so a PNG beside a PDF is silent. ACS
  excludes PDF for image files and PLOS takes only TIFF and EPS, so their default writes are correctly
  called drafts.
- **EPS is never written by default**, though it is submittable for APS and Elsevier and remains available
  on request. The PostScript backend cannot express transparency, so any artist with `alpha < 1` is
  silently flattened and the EPS stops agreeing with the PDF of the same figure.
- **The `vector` rule is the package's own judgement, not a publisher's.** An un-rasterized artist past
  `VECTOR_ELEMENT_LIMIT` (50,000 elements) makes a file large enough to be refused. It is the only rule in
  the checker not traceable to a publisher document, and it is labelled as such wherever it appears.
- **`check()` ignores artists that draw nothing.** `Axes.boxplot` creates a flier line per box whether or
  not any point lies beyond the whiskers, which would otherwise report five undersized-marker violations
  on a five-box plot where only three boxes had fliers to measure.
- **Compliance warnings use `JournalFigWarning`**, so they can be silenced without suppressing unrelated
  `UserWarning`s.
- **The colour cycle is Okabe-Ito**, identical across every theme so retargeting never changes colours,
  paired with line-style and marker cycles so curves survive greyscale printing.

## Requirements

Python >= 3.12 and matplotlib >= 3.8. The two floors are more coupled than they look: matplotlib 3.8 is
the last series with cp312 wheels, since it never supported 3.13, so it is also the last that can satisfy
both at once. numpy is not a runtime dependency.

## How the numbers are kept honest

- CI runs the suite on Linux, macOS and Windows across Python 3.12, 3.13 and 3.14, **with no journal
  typeface installed** -- the situation a user on a cluster is in -- plus lint, packaging, a strict docs
  build, and an end-to-end run of `demo.py`.
- A `minimum-versions` job installs `matplotlib==3.8.*` with `numpy<2` on Python 3.12, so the declared
  floor is tested rather than asserted.
- Every `Example:` block in a docstring is executed as a doctest, so a public function without a runnable
  example is untested by the project's own convention.
- An unexpected `JournalFigWarning` fails the suite, so a figure that quietly stops complying cannot pass
  CI.
- Image-comparison tests (`pytest --mpl`) cover the one class of regression the rest of the suite is blind
  to: a theme edit that changes what every figure looks like while every numeric assertion still holds.
  Baselines are rendered against FreeType 2.6.1, the version matplotlib's PyPI wheels bundle; a build
  linking a different FreeType rasterises the same glyphs differently enough to miss the tolerance by an
  RMS of 2 to 16, so the comparison skips there rather than failing, and the CI job asserts the version
  first so the skip cannot silently disable it.
- The eight example notebooks are executed in CI (`pytest --nbval-lax examples/`), so they cannot go stale
  unnoticed. Six are a tour -- getting started, line plots, scatter plots, histograms, heatmaps,
  multi-panel figures -- all on synthetic data with generic axis labels. A seventh reads a data file from
  `examples/data/`, fits a sinusoid with weighted `curve_fit`, and reports pulls, reduced chi-squared and
  a residual panel; the data file records its own model, parameters and seed, and
  `examples/data/make_oscillation.py` regenerates it byte-identically. An eighth covers box plots: the
  five-number summary, matplotlib's 1.5 x IQR whiskers against the literal extremes (`whis=(0, 100)`),
  colouring boxes the property cycle never reaches, flier size against the APS symbol minimum, jittered
  overlays that restore the sample size a box plot hides, notches, and horizontal layout across the
  matplotlib `vert`/`orientation` rename.
- An MkDocs site carries a guide, the full specification tables, and an API reference generated from the
  docstrings.
- `mypy --strict` runs over `src/journalfig`, with no `ignore_missing_imports`. The package ships
  `py.typed`, and this is what makes that marker a verified claim rather than an author's promise.

**No test can tell you whether a number is right.** The suite verifies that an entry is complete and
self-consistent, never that it matches the publisher's document. That stays a human review against the
cited source, which is why every `Source` carries a retrieval date.

## Known limitations

- `jf.use("aps", usetex=True)` needs matplotlib >= 3.10 on TeX installations without a Type 1 entry for
  `mathptmx`; 3.8 and 3.9 raise `LookupError` at save time. CI runners carry no LaTeX, so no job covers
  this -- it was found by running the suite against the floor by hand.
- Elsevier's 6 pt sub/superscript floor and matplotlib's 0.7x mathtext shrink mean the theme's own 7 pt
  base fails `check()` the moment a subscript appears (7 x 0.7 = 4.9 pt). `jf.use("elsevier",
  base_size=8.6)` is the fix. Nature's equivalent case is genuinely unsatisfiable: 7 pt is their maximum,
  yet any subscript then falls below their 5 pt minimum. `check()` reports the real rendered size so the
  decision is yours rather than silent.
- A colour bar attached to a panel in an interior column of a grid that another panel spans is placed
  badly by matplotlib's constrained layout. Put that panel in an outer column; see the guide.

## Also released

`journalfigs`, a thin alias package reserving the plural spelling on PyPI. Importing it hands back the
`journalfig` module itself, so there is no second copy of anything. It carries its own version and is
released separately.
