# journalfig

Publication-ready matplotlib themes for **Nature**, **APS** (PRB/PRL), and **Elsevier** (Acta Materialia,
JNCS). Import once, and retarget a figure to a different journal by changing one string.

Every number in the themes is traceable to a publisher document. Nothing is guessed; the two values that
had to be derived are marked as such, and [`journalfig.source`][journalfig.source] reports when each
document was last checked.

## Install

```bash
pip install journalfig
```

## Use

```python
import journalfig as jf

jf.use("elsevier")                                # or "nature", "aps", "PRB", "Acta Materialia"
fig, ax = jf.subplots("elsevier", width="single") # exact 90 mm, no figsize boilerplate
ax.plot(q, sq, label=r"$S(q)$")
ax.set_xlabel(r"$q$ (Å$^{-1}$)")                  # APS wants units in parentheses
ax.legend()
jf.save(fig, "fig_structure_factor")              # writes .pdf + .svg + .png
```

Use [`jf.subplots`][journalfig.subplots] and [`jf.figure`][journalfig.figure] rather than
`plt.subplots(figsize=...)`: they pin the exact size, which a plain `plt.subplots` loses to backend
pixel rounding.

## What each theme enforces

| | **Nature** | **APS** (PRB/PRL) | **Elsevier** |
|---|---|---|---|
| single | 89 mm | 3.375 in (8.5 cm) | 90 mm |
| 1.5 column | 120 / 136 mm | 5.3125 in *(derived)* | 140 mm |
| double | 183 mm | 7.0 in *(derived)* | 190 mm |
| max height | 247 mm | — | — |
| font | Arial / Helvetica | Times New Roman | Arial / Helvetica |
| base size | 7 pt | 9 pt | 7 pt |
| text limits | 5–7 pt | lettering ≥ 2 mm | 7 pt, sub ≥ 6 pt |
| panel labels | `a` 8 pt bold | `(a)` 9 pt bold | `(a)` 8 pt bold |
| lines / markers | — | ≥ 0.5 pt / ≥ 1 mm | — |
| `save()` writes | PDF + SVG + PNG | PDF + SVG + PNG | PDF + SVG + PNG |
| accepts as final artwork | PDF | PDF, EPS | PDF, EPS, TIFF, JPEG |
| raster dpi | 300 | 600 | 500 |

APS publishes only the single-column width; the 1.5- and 2-column values are derived from standard REVTeX
two-column geometry (7.0 in text width, 0.25 in gutter) and are the only inferred numbers in the package.

## Colours

Okabe–Ito, identical across all three themes so retargeting never changes colours. This follows APS's
explicit requirement to use accessible palettes and to distinguish curves by line style as well as hue, so
figures survive greyscale printing.

```
#0072B2 blue    #D55E00 vermillion   #009E73 green    #CC79A7 purple
#E69F00 orange  #56B4E9 sky          #F0E442 yellow   #000000 black
```

Available as `jf.COLORS` (name → hex) and `jf.COLOR_CYCLE`. The property cycle pairs colour with linestyle
only — markers are deliberately left out, since a marker in the cycle would decorate every point of a dense
curve. Use `jf.MARKER_CYCLE` when you want them.

## Where to go next

- The [guide](guide.md) covers multi-panel layouts, notebook setup, and the six behaviours that bite.
- The [specifications page](specifications.md) lists the publisher documents behind every number.
- The [API reference](api.md) is generated from the docstrings.
