# Guide

This page is mechanics: the traps in matplotlib and in this package, and the incantation for each. For
the other half — what makes a figure worth submitting, and how much of that the tool can carry — see
[figure design](figure-design.md).

## Panels of different sizes

[`jf.mosaic`][journalfig.mosaic] sketches the layout as text: one character per grid cell, repeated where a
panel should span, `.` where it should stay empty. `width_ratios` and `height_ratios` then set how large the
columns and rows are relative to each other, so panels need not be multiples of one cell.

```python
fig, panels = jf.mosaic(
    "nature", "AAB\n"      # a big map on the left, spanning two rows and two columns,
              "AAC\n"      # two small panels stacked beside it,
              "DDD",       # and a wide strip underneath
    width="double", ratio=0.72,
    width_ratios=[1, 1, 1.15], height_ratios=[1, 1, 0.85],
)
panels["A"].imshow(density)
panels["D"].plot(r, gr)
jf.panel_labels(panels)    # a, b, c, d in reading order — pass labels=list(panels) for A, B, C, D
```

`panels` maps each name to its axes, in the order the names first appear reading left to right, top to
bottom, which is the order [`jf.panel_labels`][journalfig.panel_labels] letters them.

### Colour bars in a mosaic

Put the panel that carries a colour bar in the **outermost** column, not an interior one. In the sketch
above, `A` is interior — column 1 of 3 — and the wide strip `D` spans the whole grid. Constrained layout
then reserves the bar's width in column 1's colour-bar margin, and `match_submerged_margins`, which equalises
the gutters a spanning panel crosses so its columns line up, adds that reserved width into the ordinary
margin as well. The bar is counted twice and ends up floating roughly midway between its own panel and the
next one — a gap of about 0.10 of the figure width instead of 0.02. Mirroring the sketch to `"ABB\nCBB\nDDD"`
puts the map in the last column, whose margin no spanning panel submerges, and the bar sits against it:

```python
fig, panels = jf.mosaic(
    "nature", "ABB\n"      # small panel, then a big map spanning two rows and two columns,
              "CBB\n"      # the second small panel beneath the first,
              "DDD",       # and a wide strip underneath
    width="double", ratio=0.72,
    width_ratios=[1.15, 1, 1], height_ratios=[1, 1, 0.85],
)
mesh = panels["B"].imshow(density)
fig.colorbar(mesh, ax=panels["B"], pad=0.02)
```

This is a matplotlib layout behaviour, not a `journalfig` one — it applies to any
`constrained_layout` figure, and `jf.check` has nothing to say about it because no publisher states a rule
about colour-bar gaps. `demo.py` uses this arrangement for the same reason.

For layouts easier to express as slices than as a sketch,
[`jf.gridspec`][journalfig.gridspec] hands back the figure and an empty grid:

```python
fig, gs = jf.gridspec("aps", 3, 3, width="double", ratio=0.8, height_ratios=[1, 1, 0.6])
main = fig.add_subplot(gs[:2, :2])
side = fig.add_subplot(gs[:2, 2])
strip = fig.add_subplot(gs[2, :])
```

Both size and pin the figure exactly like `jf.subplots`, so `jf.save` and `jf.check` behave the same. For a
plain grid with unequal columns there is no need for either — `jf.subplots` forwards `width_ratios` /
`height_ratios` straight to matplotlib:

```python
fig, axs = jf.subplots("elsevier", 1, 2, width="double", width_ratios=[3, 1])
```

!!! warning "Two things bite in multi-panel figures"
    **Height still defaults to the golden ratio of the width**, which is far too short once there is more
    than one row — pass `ratio=` or `height_mm=` deliberately. And **a colour bar in an interior column
    lands in the wrong place**, for the reason in [Colour bars in a mosaic](#colour-bars-in-a-mosaic)
    above; `fraction` does not fix it, because `aspect` sets the bar's width regardless.

## Using it in a notebook

Put this once at the top, next to `%matplotlib inline`:

```python
%config InlineBackend.print_figure_kwargs = {"bbox_inches": None}
```

Jupyter crops every inline preview with `bbox_inches="tight"`. That defeats the exact column widths this
package exists to guarantee, and because the themes sit the axes close to the canvas edge, the crop slices
through the top and right spines — they preview at 40% and 20% of their true weight, so the frame looks
lopsided even though the figure is correct. Saved files were never affected: `jf.save()` forces
`bbox_inches=None`.

## Six things worth knowing

**Nature caps text at 7 pt; APS requires ≥ 2 mm lettering, which forces 9 pt.** These are irreconcilable,
which is exactly why there is a theme per publisher rather than one. The APS size is not a guess — Times New Roman
digits measure 1.94 mm at 8 pt (fails) and 2.18 mm at 9 pt (passes), measured with `TextPath`.

**A missing font is substituted silently, and that is the easiest way to submit a non-compliant figure.**
Ask for Arial on a machine that has no Arial and matplotlib draws DejaVu Sans instead — the figure looks
fine, and nothing in matplotlib treats it as an error. This bites when you develop on a laptop that has the
font and render on a cluster that does not. [`jf.check()`][journalfig.check] reports it as a `font`
violation, and [`jf.fonts()`][journalfig.fonts] shows what each face resolved to:

```pycon
>>> jf.use("nature"); jf.fonts()["text"]
FontStatus(requested=('Arial', 'Helvetica', ...), resolved='Arial', path='...', status='exact')
```

`status` is `exact` for a face the publisher names, `substitute` for a metrically compatible stand-in
(Liberation Sans, Nimbus Sans, Arimo for Arial; STIXGeneral, Nimbus Roman, Liberation Serif for Times), and
`fallback` for anything else. Substitutes pass `jf.check()` — they were cut to the same widths, so the
layout is identical. On a bare Linux box, `apt install fonts-liberation` is usually the whole fix; the APS
theme already lands on matplotlib's bundled STIXGeneral without any install.

**matplotlib shrinks maths sub/superscripts to 0.7×.** A 7 pt Elsevier label renders `$x_a$` at 4.9 pt
against a hard 6 pt floor. Use `jf.use("elsevier", base_size=9)` for maths-heavy figures. Nature's case is
*unsatisfiable* — 7 pt is their maximum, yet any subscript then falls below their 5 pt minimum.
`jf.check()` reports the real rendered size so the decision is yours rather than silent.

**`savefig.bbox="tight"` breaks column widths.** It crops a requested 89 mm figure to 87.9 mm
(252.3 → 249.2 pt). The themes use `constrained_layout` with `savefig.bbox="standard"`, and `jf.save()`
forces `bbox_inches=None`, so what you ask for is what lands in the file.

**Interactive backends round a new figure to whole device pixels.** On the default macOS backend,
`plt.subplots(figsize=jf.figsize("nature", "double"))` yields 182.88 mm rather than 183.0 mm, because the
canvas snaps 7.2047 in × 150 dpi = 1080.7 px down to 1080 px. `jf.subplots()` / `jf.figure()` re-apply the
size with `forward=False` to skip that round-trip, and `jf.save()` re-asserts it before writing. This is
invisible under `Agg`, so it will not show up in a headless test — it only bites in real use.

**In LaTeX, include theme figures at their natural size.** `\includegraphics[width=\linewidth]{...}`
rescales them and destroys the font sizing: `elsarticle` in `preprint` mode has a 137 mm `\textwidth`, so a
190 mm double-column figure is scaled by 0.72 and its compliant 7 pt labels land at ~5 pt. Size the figure
with `jf.figsize`/`jf.subplots` and then use a bare `\includegraphics{fig.pdf}`.

## Output formats

Every theme writes PDF, SVG and PNG — the file you submit, one to edit, one to show:

```python
jf.save(fig, "fig1")                                # fig1.pdf, fig1.svg, fig1.png
jf.save(fig, "fig1", formats=["tiff"])              # Elsevier TIFF, LZW-compressed
jf.save(fig, "fig1", formats=["pdf", "eps"])        # APS colour-online-only figure
```

The draft warning fires once per call, and only when nothing written can be submitted — a PNG beside a PDF
is silent, a PNG alone is not:

```pycon
>>> jf.save(fig, "fig1", formats=["png", "svg"])      # Nature
JournalFigWarning: none of PNG, SVG can be submitted to Nature Portfolio as final artwork;
it takes PDF - treat these as drafts
```

No theme writes EPS by default: the PostScript backend cannot express transparency, so any artist with
`alpha < 1` is flattened to opaque and the EPS stops matching the PDF of the same figure. APS still accepts
it, so `formats=["pdf", "eps"]` is there when a colour-online-only figure needs it.

SVG is written with live, editable text (`svg.fonttype: none`) rather than glyph outlines, which is what
makes it worth having — but it therefore renders correctly only on a machine with the theme's typeface
installed. `jf.fonts()` reports what that will be. Convert to whatever the publisher wants from there.

## Keeping vector files sane

`imshow` embeds a bitmap, so it is never the problem. `pcolormesh` and dense scatters are: one vector
path per cell or point, which on a 400x400 mesh means a PDF holding 160,000 paths — slow to open,
large enough for a submission system to refuse, and prone to hairline seams where antialiasing leaves
gaps between neighbouring quads.

`rasterized=True` converts that one artist to a bitmap at `savefig.dpi` while the axes, ticks and
labels stay live vector text. Measured on that mesh: **3.7 MB → 108 kB**.

```python
ax.pcolormesh(x, y, z, rasterized=True)
ax.scatter(a, b, rasterized=True)
```

[`jf.check()`][journalfig.check] reports an un-rasterized artist past
`jf.VECTOR_ELEMENT_LIMIT` (50,000 elements):

```
[vector] a QuadMesh holds 160,000 elements and is not rasterized; the vector file
  will be very large — pass rasterized=True to that call so only it becomes a
  bitmap, leaving axes and text as text
```

!!! note "The one rule that is not a publisher's"
    Every other check comes from a publisher document. This one is the package's own judgement about
    what makes a file impractical, so its threshold sits well past what an ordinary plot produces.

## Labelling lines without a legend

A legend costs space and makes the reader look up a colour before they can read the plot. At 89 mm
that lookup is the most expensive thing on the page. [`jf.label_lines()`][journalfig.label_lines] puts
each name beside its own line:

```python
ax.margins(x=0.22)        # the labels sit outside the axes, so leave room
jf.label_lines(ax)
```

Each label takes its line's colour, so in greyscale the association survives only because the themes'
property cycle varies linestyle too.

## Handing an SVG to someone else

SVG is written with live, editable text, which is the reason to want one — but it then renders
correctly only where the theme's typeface is installed. For a file leaving your machine:

```python
jf.save(fig, "fig1", formats=["svg"], svg_text="path")
```

That outlines the glyphs, so the file renders identically anywhere and converts safely, at the cost of
the text no longer being text. The setting is scoped to that write and does not leak into later figures.

## Logging

[`jf.save()`][journalfig.save] reports the size it wrote through the `journalfig` logger at INFO level, so
it stays quiet inside a pipeline. To see it:

```python
import logging
logging.basicConfig(format="%(message)s")
logging.getLogger("journalfig").setLevel(logging.INFO)
# Elsevier: 90.0 x 55.6 mm -> fig_structure_factor.pdf, fig_structure_factor.svg, fig_structure_factor.png
```

Raise that one logger rather than calling `logging.basicConfig(level="INFO")`, which also switches on
`fontTools` — it logs a dozen subsetting lines every time a PDF is written.

## Silencing compliance warnings

[`jf.check()`][journalfig.check] warns by default, and `jf.save()` calls it. Every warning the package
raises uses [`JournalFigWarning`][journalfig.JournalFigWarning], so they can be filtered without silencing
anything else:

```python
import warnings
warnings.filterwarnings("ignore", category=jf.JournalFigWarning)
```

Passing `validate=False` to `jf.save()`, or `warn=False` to `jf.check()`, turns the check off entirely
rather than hiding its output.

## Checking figures from the command line

Everything above assumes you are writing the figure. You are not always: a co-author's script, a figure
from an older paper, or one drawn by a different library still has to clear the same requirements. The
CLI runs [`jf.check()`][journalfig.check] against whatever a Python file or callable produces, so no
part of this depends on having adopted the themes.

```console
$ journalfig check figures.py --journal aps
figure 1  (162.6 x 121.9 mm)
  [width] figure is 162.6 mm wide; American Physical Society (PRB/PRL) uses double 178 mm, onehalf 135 mm, single 86 mm
  [line] a line is 0.30 pt, below the 0.50 pt minimum
  [marker] marker diameter is 0.35 mm, below the 1.0 mm minimum
figure 2  (85.7 x 53.0 mm)  OK

2 figure(s), 3 violations
```

The target is either a path to a script — every figure it leaves open is checked, which is what an
ordinary plotting script produces without being written to return anything — or `module:function`, which
imports and calls it. `--journal` defaults to the theme `jf.use()` last applied, so a script that sets its
own theme needs no flag. `journalfig journals` lists the keys.

Exit codes make it usable as a build step: `0` when every figure complies, `1` when any violation was
found, and `2` when the target could not be loaded at all — a missing file or a script that raised is not
the same answer as "your figures are fine".

```yaml
- run: journalfig check paper/figures.py --journal nature
```

`python -m journalfig check ...` is equivalent, and works from a checkout before the console script has
been installed.

!!! note "This does not read PDFs"
    A matplotlib `Figure` cannot be reconstructed from a saved PDF, so checking one is a different and
    much narrower question — page geometry and embedded fonts, not line weights or marker diameters. The
    CLI runs the real checks by re-running the code that draws the figures, and does not pretend a file
    on disk can be inspected the same way.
