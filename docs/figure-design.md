# Figure design

A figure that passes `jf.check()` is *submittable*. That is a lower bar than *good*. The checker measures
what a publisher wrote down — widths, type sizes, line weights — and a publisher writes down almost
nothing about whether a figure communicates. This page covers the rest, and is honest about which half
belongs to the tool and which stays with you.

Every rule below carries three lines: what the principle is, what `journalfig` already does about it, and
what remains yours to decide.

!!! note "Where these come from"

    Rules 1–10 are the *Ten Simple Rules for Better Figures* — Rougier, Droettboom & Bourne,
    [PLOS Computational Biology 10(9): e1003833](https://doi.org/10.1371/journal.pcbi.1003833) (2014),
    released under a CC0 public domain dedication and reprinted as Chapter 6 of Rougier's
    *Scientific Visualization: Python + Matplotlib*. The wording here is ours; read the original, it is
    short and better than any summary.

    Rules 11–25 are this package's own, drawn from what actually gets figures bounced in production.
    They are **not** publisher requirements, and are labelled as such wherever they appear.

## Checklist at a glance

The `check()` column describes **`jf.check()` only**, in three states. **checked** names the
`Violation.kind` it reports. **not checkable** means no machine can judge it from a figure object.
**not yet** means it is checkable in principle and is not built — an honest roadmap, not a claim.
Resolution and file format are policed by [`jf.save()`](guide.md#output-formats) instead of `check()`,
which is why they read "not yet" here.

| # | Rule | `check()` |
|---|---|---|
| 1 | Know your audience | not checkable |
| 2 | Identify your message | not checkable |
| 3 | Adapt the figure to its medium | checked — `width`, `height` |
| 4 | Captions are not optional | not checkable |
| 5 | Do not trust the defaults | checked — `text`, `font` |
| 6 | Use colour effectively | not yet |
| 7 | Do not mislead the reader | not yet |
| 8 | Avoid chartjunk | not checkable |
| 9 | Message trumps beauty | not checkable |
| 10 | Get the right tool | not checkable |
| 11 | Size the figure; never rescale it afterwards | not yet |
| 12 | Resolution is a floor, not a target | not yet |
| 13 | Ship a format the publisher accepts | not yet |
| 14 | Keep the vector file small enough to open | checked — `vector` |
| 15 | Render every vertex you plotted | not checkable |
| 16 | Do not truncate a quantitative axis | not yet |
| 17 | Label every axis with its unit | not yet |
| 18 | Use a true minus, not a hyphen | not checkable |
| 19 | Ink has a minimum physical size | checked — `lettering`, `line`, `marker` |
| 20 | Maths renders smaller than you asked for | checked — `subscript` |
| 21 | Survive greyscale | not yet |
| 22 | Be colourblind-safe by construction | not yet |
| 23 | The figure must be regenerable from script and data | not checkable |
| 24 | Record the seed, the parameters, and the input paths | not checkable |
| 25 | Never hand-edit the exported file | not checkable |

---

# Part I — The ten simple rules

## 1. Know your audience

A figure for your own lab notebook, for a referee, for a lecture hall, and for a press release are four
different figures. The referee will read it for as long as it takes; the lecture hall gets fifteen
seconds and sees it from twelve metres away. Decide who is looking before you decide anything else.

**`journalfig` does** — encodes exactly one axis of this: which journal. `jf.use("nature")` is a
declaration that the audience is a Nature referee reading print.

**You must** — everything else. The package cannot tell a talk from a thesis.

## 2. Identify your message

A figure exists to say one thing that prose would say badly. Name that thing in a sentence before you
plot. If you cannot, the figure is not ready, and no amount of styling will rescue it.

**`journalfig` does** — nothing. This is the part no library reaches.

**You must** — all of it. If the sentence needs an "and", consider two figures.

## 3. Adapt the figure to its medium

The same data on a poster, a projector, and a journal column wants three different treatments. Print is
the strictest: the column width is fixed by the publisher, and anything that does not fit is scaled by
production — which shrinks your type below the legible minimum without telling you.

**`journalfig` does** — the print medium, thoroughly. Exact per-publisher column widths, maximum heights,
resolution floors by artwork type, and a format per purpose: PDF to submit, SVG to edit, PNG for a talk.
`jf.figsize`, `jf.subplots` and `jf.mosaic` all size to a real column.

**You must** — choose the width that suits the content, not the widest available. A single-column figure
that is legible beats a double-column one that is empty. For a talk, scale the whole theme with
`jf.use(journal, base_size=...)` rather than resizing the figure afterwards.

## 4. Captions are not optional

The caption carries what the figure cannot: what the reader is looking at, what the error bars mean, how
many samples, and where the exact numbers live. Write it as if answering the question you expect.

**`journalfig` does** — `jf.panel_labels()` letters the panels in the publisher's convention, so the
caption has stable handles to refer to.

**You must** — write it. A figure that needs no caption is usually a figure that is not saying much.

## 5. Do not trust the defaults

Every plotting library ships defaults tuned to be acceptable for everything, which makes them optimal for
nothing. Matplotlib's are recognisable at a glance, and a referee recognises them too.

**`journalfig` does** — this is the entire package. Each theme replaces the defaults with values read from
the publisher's own author guidelines, and `check()` reports where a figure still departs from them.

**You must** — notice the limit of that. The package's defaults are correct for *a publisher's
constraints*, not for *your message*. A theme cannot know that your third series is the important one.

## 6. Use colour effectively

Colour is a channel, not decoration. If a curve is blue for no reason, make it black. Reserve colour for
the element that carries the message, and match the colormap type to the data: sequential for a
quantity that runs low to high, diverging for deviation from a midpoint, qualitative for categories.
Rainbow and jet are neither perceptually uniform nor safe, and they hide detail exactly where dense
data needs it.

**`journalfig` does** — ships the Okabe–Ito colourblind-safe cycle
([see the palette](index.md#colours)), pairs it with a linestyle cycle so series stay distinct without
hue, and sets `image.cmap: viridis` so the default colormap is perceptually uniform rather than rainbow.

**You must** — pick the colormap that matches your data; the package cannot see your data. And if you
override the cycle, you have left the safe palette and nothing will warn you.

## 7. Do not mislead the reader

A scientific figure is bound to its data, and the binding is easy to loosen by accident. A truncated
y-axis makes noise look like a trend. Encoding a value as a circle's *radius* rather than its area
exaggerates the ratio. Pie charts and 3-D bars defeat quantitative comparison. None of these are lies,
and all of them mislead.

**`journalfig` does** — one concrete thing: `path.simplify_threshold: 0.0`, so matplotlib renders every
vertex. Its default of `0.111` silently discards points; on a dense noisy trace that moved 11% of the
pixels, which means the exported curve was not the curve that was plotted.

**You must** — the rest, and the rest is most of it. Start quantitative axes at zero unless you have a
reason, and say the reason. Matplotlib's `scatter(s=...)` is an area, which is the correct default — do
not "fix" it by passing a radius.

## 8. Avoid chartjunk

Every mark that carries no information competes with the marks that do. Grid lines nobody reads, a legend
box overlapping the data, a coloured background, three decimal places of false precision, a frame around
a frame.

**`journalfig` does** — starts you clean: grid off, legend frame off, white background, restrained tick
geometry. [`jf.label_lines()`](guide.md#labelling-lines-without-a-legend) names each curve at its end so
you can drop the legend box entirely, which is the standard remedy when a legend is fighting the data.

**You must** — resist adding things back. Turn the grid on only when a reader needs to *read values off*
the figure rather than see a shape.

## 9. Message trumps beauty

Know your field's conventions, because a reader who recognises the format spends their attention on your
result instead of your layout — and because a familiar format makes your own errors visible. When you
must invent, borrow structure from published work rather than from data-visualisation galleries, where
aesthetics outranks accuracy.

**`journalfig` does** — nothing directly, though the whole design refuses to compete on decorative
styling. There is deliberately no gallery of themes to pick by taste.

**You must** — prefer the readable figure over the striking one, every time.

## 10. Get the right tool

The tool that analyses your data does not have to be the tool that draws it, and forcing one to do both
usually costs more than exporting an intermediate file.

**`journalfig` does** — is one such tool, for one job: matplotlib figures aimed at a journal.

**You must** — recognise when it is the wrong one. Diagrams, schematics and network layouts are someone
else's job.

---

# Part II — Personal rules

Everything below is this package's judgement rather than a publisher's rule. They are the failures that
get a figure returned by production, or that quietly survive review and embarrass you later.

## Size & scaling integrity

### 11. Size the figure; never rescale it afterwards

A figure has exactly one correct physical size, and every downstream transform destroys it. LaTeX's
`\includegraphics[width=\linewidth]` rescales silently: a 190 mm double-column figure dropped into
`elsarticle`'s 137 mm preprint text block is scaled by 0.72, and its compliant 7 pt labels land at
about 5 pt. Cropping does the same in miniature — `bbox_inches="tight"` turns a requested 89 mm figure
into 87.9 mm.

**`journalfig` does** — pins the exact size at creation, re-asserts it at save time, and forces
`bbox_inches=None` so a tight crop cannot happen behind your back.
See [the six behaviours that bite](guide.md#six-things-worth-knowing).

**You must** — include it at natural size: a bare `\includegraphics{fig.pdf}`. If it does not fit, build
it narrower; do not scale it.

### 12. Resolution is a floor, not a target

Publishers state a *minimum*, and it varies by artwork type: typically 300 dpi for a colour halftone, 600
for greyscale or a combination image, and 1000–1200 for pure line art. Exceeding it is always fine.
Falling below it is a rejection, and for a raster format it is the one property you cannot fix afterwards.

**`journalfig` does** — sets `savefig.dpi: 600`. Each spec records the floor for the *combination* case —
a plot with text, rules and colour, which is what a matplotlib figure is — and 600 clears every one of
them, the highest being APS, AIP, RSC and PNAS at 600. `jf.save()` warns if you pass an explicit `dpi=`
below the publisher's minimum for a raster format.

**Note the case not covered.** The 1000–1200 dpi line-art figure applies to scanned pen-and-ink drawings,
not to a rendered plot, so it is not in the database. If you are submitting genuine line art, read the
publisher's own table rather than trusting the theme.

**You must** — prefer vector output where the publisher accepts it, which makes the question moot.

### 13. Ship a format the publisher accepts

Accepted-format lists are narrower and stranger than people expect. ACS excludes PDF for image files.
PLOS takes TIFF and EPS and nothing else. Taylor & Francis explicitly refuses PDF as "locked". Finding
this out at submission costs a day.

**`journalfig` does** — records `submission_formats` per publisher and warns from `jf.save()` when
*nothing* you wrote is submittable. See [output formats](guide.md#output-formats).

**You must** — check the specific journal, not just the publisher. And avoid EPS where you use
transparency: the PostScript backend flattens it, so the EPS and the PDF of one figure disagree.

### 14. Keep the vector file small enough to open

A PDF holding a few hundred thousand un-rasterized path elements is technically correct and practically
useless — slow to render, sometimes refused outright by submission systems.

**`journalfig` does** — `check()` reports a `vector` violation past `jf.VECTOR_ELEMENT_LIMIT` (50,000
elements). See [keeping vector files sane](guide.md#keeping-vector-files-sane).

**You must** — pass `rasterized=True` on the offending artist. Rasterize the dense layer, keep the text
and axes as vectors.

## Data fidelity

### 15. Render every vertex you plotted

A renderer that discards points to go faster has changed your data without saying so. This is the default
in matplotlib.

**`journalfig` does** — sets `path.simplify_threshold: 0.0` in every theme.

**You must** — accept the file-size cost, or rasterize deliberately (rule 14). A 20k-point line goes from
21 kB to 194 kB in PDF; discarding data is not the right way to save 170 kB.

### 16. Do not truncate a quantitative axis

Bars starting at 80 instead of 0 make a 3% difference look like a threefold one, and the effect survives
even when the axis is honestly labelled, because the bar lengths are what the eye reads.

**`journalfig` does** — nothing yet. This is the most valuable rule the checker does not implement.

**You must** — start bar and area axes at zero. Line plots may be truncated, because a line encodes
position rather than length, but say so in the caption when the range is unusual.

### 17. Label every axis with its unit

An axis without a unit is not a measurement. This is the single most common defect in submitted figures
and the easiest to fix.

**`journalfig` does** — nothing yet; the presence of an axis label is checkable, the correctness of its
unit is not.

**You must** — write quantity and unit on every axis, and on every colour bar.

### 18. Use a true minus, not a hyphen

`-5` set with an ASCII hyphen is a typographic error in a scientific figure. The characters differ in
width and vertical position.

**`journalfig` does** — sets `axes.unicode_minus: True` and `axes.formatter.use_mathtext: True`.

**You must** — nothing, unless you write tick labels by hand, in which case use `−` (U+2212).

## Accessibility

### 19. Ink has a minimum physical size

Publishers state minima in millimetres, not points, because what matters is the size on the printed page.
APS requires lettering of at least 2 mm — which forces 9 pt Times, since Times digits measure 1.94 mm at
8 pt and fail. Lines below about 0.3 pt disappear in print; data points below 1 mm are unreadable.

**`journalfig` does** — measures the rendered physical size and reports `lettering`, `line` and `marker`
violations against the publisher's stated minima.

**You must** — resist shrinking type to fit more in. If it does not fit at the minimum size, it is too
much for one figure.

### 20. Maths renders smaller than you asked for

Matplotlib sets sub- and superscripts at 0.7× the surrounding text. A 7 pt Elsevier label renders `$x_a$`
at 4.9 pt against a hard 6 pt floor — so a compliant base size produces a non-compliant subscript.

**`journalfig` does** — reports a `subscript` violation using the *rendered* size, not the nominal one.

**You must** — raise the base size for maths-heavy figures: `jf.use("elsevier", base_size=8.6)`. Nature's
case is unsatisfiable — 7 pt is their maximum and any subscript then falls below their 5 pt minimum — so
the checker tells you and the judgement is yours.

### 21. Survive greyscale

Many journals still print in black and white while publishing colour online; Taylor & Francis states this
outright. If two series are distinguished by hue alone, they merge in print.

**`journalfig` does** — pairs the colour cycle with a linestyle cycle, so the shipped default is already
distinguishable without hue.

**You must** — check it. Convert to greyscale and look. This is not yet a `check()` rule.

### 22. Be colourblind-safe by construction

Around 8% of men have some form of colour vision deficiency. Red-green pairs are the common failure, and
the rainbow colormap fails for everyone.

**`journalfig` does** — ships Okabe–Ito, which is designed for this, and a perceptually uniform default
colormap.

**You must** — verify anything you choose yourself. Simulating a deuteranopia transform is checkable in
principle and is not implemented.

## Reproducibility

### 23. The figure must be regenerable from script and data

A figure you cannot rebuild is a figure you cannot revise, and revision is guaranteed. The referee will
ask for one more series four months from now.

**`journalfig` does** — nothing directly, but `journalfig check` runs a plotting script in CI, which
only works if the figure is script-generated in the first place. See
[checking from the command line](guide.md#checking-figures-from-the-command-line).

**You must** — keep one script per figure, committed alongside the data.

### 24. Record the seed, the parameters, and the input paths

A stochastic figure without its seed is not reproducible even by you. The same applies to cutoffs,
normalisations and which file the numbers came from.

**`journalfig` does** — nothing; this is yours.

**You must** — write them into the script, and prefer a data file that records its own provenance in a
header.

### 25. Never hand-edit the exported file

Opening the PDF in Illustrator to nudge a label is the moment the figure stops being reproducible. The
edit is invisible, undocumented, and lost the next time the script runs.

**`journalfig` does** — provides the escape hatches that make hand-editing unnecessary: exact sizing,
`jf.mosaic` for irregular layouts, `jf.panel_labels`, `jf.label_lines`, and SVG output with live text when
someone else genuinely must edit it.

**You must** — push the change back into the script. If the tool cannot express it, that is worth knowing.

---

## What `check()` deliberately will not do

Eleven of the twenty-five rules above are marked **not checkable**, and that is not a gap to be closed.
Whether a figure has a message, whether its caption answers the right question, whether its conventions
match its field — these need a reader. A checker that scored them would be guessing, and a confident
wrong score is worse than silence.

The **not yet** rules are different: nine of them are mechanically decidable and simply are not built.
Truncated axes, missing units, greyscale collision and colourblind safety are all computable from a
figure object.

One caution if they are added. `check()` currently reports one rule that no publisher states — `vector` —
and it is
[labelled as the package's own judgement](specifications.md) everywhere it appears, because the value of
the spec database is that every other number traces to a document. Colour and axis rules would be the
same kind of claim, and would need the same label. A checker that mixes "Nature requires this" with
"we think this" without distinguishing them is no longer a compliance tool.
