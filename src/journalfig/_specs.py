"""Published figure specifications for Nature, APS, and Elsevier journals.

Every number here is traceable to a publisher document; see ``SOURCES``. Values that had to be derived
rather than read off a spec sheet are marked ``DERIVED`` in the comment next to them.

Author: Achraf Atila (achraf.atila@bam.de)
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Default height-to-width ratio (inverse golden ratio). Lives here rather than in _core so the
#: stylesheet generator can derive a default figure size without importing matplotlib.
GOLDEN = 0.6180339887498949

MM_PER_INCH = 25.4
PT_PER_INCH = 72.0
PT_PER_MM = PT_PER_INCH / MM_PER_INCH

#: matplotlib shrinks nested math (sub/superscripts) by this factor; see ``matplotlib._mathtext.SHRINK_FACTOR``.
MATHTEXT_SHRINK = 0.7

#: Okabe-Ito colourblind-safe qualitative palette.
COLORS = {
    "blue": "#0072B2",
    "vermillion": "#D55E00",
    "green": "#009E73",
    "purple": "#CC79A7",
    "orange": "#E69F00",
    "sky": "#56B4E9",
    "yellow": "#F0E442",
    "black": "#000000",
}

#: Written for every journal by default: PDF to submit, SVG to edit, PNG for talks and previews.
#: Anything else the matplotlib backend supports can be requested through ``journalfig.save(formats=...)``.
DEFAULT_FORMATS = ("pdf", "svg", "png")

COLOR_CYCLE = list(COLORS.values())
LINESTYLE_CYCLE = ["-", "--", "-.", ":"]
MARKER_CYCLE = ["o", "s", "^", "D"]


@dataclass(frozen=True)
class Source:
    """The publisher document a theme's numbers were read from.

    Publishers revise their artwork guidelines, so a specification is only as trustworthy as the date
    it was last checked against the source. ``retrieved`` records that date.

    Attributes:
        url: Where the document was obtained.
        title: The document's own title.
        version: The document's stated edition or date, or ``None`` if it carries neither.
        retrieved: ISO date on which the numbers in :data:`SPECS` were last checked against it.
    """

    url: str
    title: str
    version: str | None
    retrieved: str

    def __str__(self) -> str:
        edition = f", {self.version}" if self.version else ""
        return f"{self.title}{edition} (retrieved {self.retrieved})"


SOURCES: dict[str, Source] = {
    "nature": Source(
        url="https://www.nature.com/documents/nature-final-artwork.pdf",
        title="Nature Portfolio, Guide to Preparing Final Artwork",
        version=None,
        retrieved="2026-07-28",
    ),
    "aps": Source(
        url="https://res.cloudinary.com/apsphysics/image/upload/v1715884920/aps-journals-style-guide_tnoyln.pdf",
        title="APS Journals Style Guide for Authors",
        version="November 2024",
        retrieved="2026-07-28",
    ),
    "elsevier": Source(
        url="https://www.elsevier.com/about/policies-and-standards/author/artwork-and-media-instructions/artwork-sizing",
        title="Elsevier, Artwork sizing",
        version=None,
        retrieved="2026-07-28",
    ),
    # Added 2026-08-24. Every entry is the publisher's own author-guidelines document.
    "iop": Source(
        url="https://publishingsupport.iopscience.iop.org/questions/figures-journal-articles/",
        title="IOP Publishing, Figures for journal articles",
        version=None,
        retrieved="2026-08-24",
    ),
    "aip": Source(
        url="https://publishing.aip.org/resources/researchers/author-instructions/",
        title="AIP Publishing, Author Instructions",
        version=None,
        retrieved="2026-08-24",
    ),
    "acs": Source(
        url="https://researcher-resources.acs.org/publish/author_guidelines?coden=accacs",
        title="ACS Publications, Author Guidelines (ACS Catalysis)",
        version=None,
        retrieved="2026-08-24",
    ),
    "rsc": Source(
        url="https://www.rsc.org/publishing/publish-with-us/publish-a-journal-article/chemical-science",
        title="Royal Society of Chemistry, Author guidelines for Chemical Science",
        version=None,
        retrieved="2026-08-24",
    ),
    "ieee": Source(
        url="https://conferences.ieeeauthorcenter.ieee.org/write-your-paper/improve-your-graphics/",
        title="IEEE Author Center, Improve Your Graphics",
        version=None,
        retrieved="2026-08-24",
    ),
    "plos": Source(
        url="https://journals.plos.org/plosone/s/figures",
        title="PLOS, Figures",
        version=None,
        retrieved="2026-08-24",
    ),
    "wiley": Source(
        url="https://authors.wiley.com/asset/photos/electronic_artwork_guidelines.pdf",
        title="Wiley, Guidelines for the Preparation of Figures",
        version="1 September 2016",
        retrieved="2026-08-24",
    ),
    "pnas": Source(
        url="https://www.pnas.org/pb-assets/authors/digitalart-1675347574760.pdf",
        title="PNAS, Digital Art Guidelines",
        version="16 February 2022",
        retrieved="2026-08-24",
    ),
    "science": Source(
        url="https://www.science.org/cms/asset/67f37ac8-4d02-4625-8a05-230568cb8323/author_prep_guide_2025.pdf",
        title="Science (AAAS), Guide to Preparing Figures",
        version="2025",
        retrieved="2026-08-24",
    ),
}


def mm_to_inch(value_mm: float) -> float:
    """Convert millimetres to inches.

    Args:
        value_mm: Length in millimetres.

    Returns:
        The same length in inches.

    Example:
        >>> round(mm_to_inch(89.0), 4)
        3.5039
    """
    return value_mm / MM_PER_INCH


def pt_to_mm(value_pt: float) -> float:
    """Convert typographic points to millimetres.

    Args:
        value_pt: Length in points (1/72 inch).

    Returns:
        The same length in millimetres.

    Example:
        >>> round(pt_to_mm(72.0), 1)
        25.4
    """
    return value_pt / PT_PER_MM


@dataclass(frozen=True)
class ThemeStyle:
    """How a theme draws, as opposed to what its publisher requires.

    Nothing in this class is quoted from an author guide. No publisher states a tick length, a marker
    diameter, or a legend handle length; these are journalfig's own choices about what looks right at
    the sizes the publisher *does* state, and they are kept out of :class:`JournalSpec` so that
    "every number is traceable to a publisher document" stays literally true of that class.
    :func:`journalfig.check` validates against :class:`JournalSpec` only, never against this.

    Values are in points unless the name says otherwise. The defaults are the Nature theme's, which is
    the most conservative of the three; a theme built for a larger base font wants larger ticks.

    Attributes:
        axes_linewidth: Weight of the axes frame, and of patch and hatch edges with it.
        grid_linewidth: Weight of grid lines, and of minor tick marks with them.
        tick_major_size: Length of major tick marks. Applied to both axes -- x and y are never
            given different tick geometry, and hand-writing them separately invited asymmetry.
        tick_minor_size: Length of minor tick marks, both axes.
        tick_major_width: Weight of major tick marks, both axes.
        tick_minor_width: Weight of minor tick marks, both axes.
        tick_pad: Gap between a tick mark and its label, both axes.
        marker_size: Default marker diameter for line plots.
        marker_edge_width: Default marker edge weight.
        errorbar_capsize: Half-width of an errorbar cap.
        legend_handlelength: Length of the sample line in a legend entry.
        title_weight: ``"bold"`` or ``"normal"`` for axes titles.
        title_location: ``"left"``, ``"center"`` or ``"right"`` for axes titles.
        mathtext_fontset: ``"custom"`` to pin maths to the theme's own face, or a matplotlib set
            such as ``"stix"`` where that face already matches the publisher's typeface.
        font_family_category: ``"sans-serif"`` or ``"serif"`` -- which matplotlib family the stack
            below is registered under.
        font_stack: The concrete fallback chain matplotlib searches, most preferred first, ending in
            a face matplotlib bundles so the theme degrades rather than fails. This is a third thing
            from ``JournalSpec.font_families`` (what the publisher asks for) and
            ``font_substitutes`` (what :func:`journalfig.check` accepts): Elsevier permits Times, for
            instance, yet the theme renders all-sans, and the stack lists only the substitutes worth
            actually trying.
    """

    axes_linewidth: float = 0.5
    grid_linewidth: float = 0.4
    tick_major_size: float = 2.5
    tick_minor_size: float = 1.5
    tick_major_width: float = 0.5
    tick_minor_width: float = 0.4
    tick_pad: float = 2.0
    marker_size: float = 3.0
    marker_edge_width: float = 0.6
    errorbar_capsize: float = 1.5
    legend_handlelength: float = 1.6
    title_weight: str = "bold"
    title_location: str = "left"
    mathtext_fontset: str = "custom"
    font_family_category: str = "sans-serif"
    font_stack: tuple[str, ...] = (
        # Arial leads: it exposes separate regular/italic/bold faces, whereas macOS Helvetica
        # collapses every variant into a single .ttc. Ends in DejaVu Sans, which matplotlib bundles,
        # so the theme degrades rather than fails off macOS.
        "Arial",
        "Helvetica",
        "Helvetica Neue",
        "Nimbus Sans",
        "Liberation Sans",
        "DejaVu Sans",
    )


@dataclass(frozen=True)
class JournalSpec:
    """Figure requirements for one publisher.

    Attributes:
        name: Human-readable publisher name.
        widths_mm: Allowed figure widths keyed by layout name.
        max_height_mm: Maximum figure height, or ``None`` if the publisher does not state one.
        min_width_mm: Minimum figure width, or ``None`` if unstated.
        text_min_pt: Smallest permitted size for normal text, or ``None`` if unstated.
        text_max_pt: Largest permitted size for normal text, or ``None`` if unstated.
        sub_min_pt: Smallest permitted size for sub/superscripts, or ``None`` if unstated.
        min_lettering_mm: Minimum printed glyph height, or ``None`` if unstated.
        min_marker_mm: Minimum printed data-point diameter, or ``None`` if unstated.
        min_linewidth_pt: Minimum printed line weight, or ``None`` if unstated.
        panel_label_fmt: Format string for panel labels, e.g. ``"{}"`` or ``"({})"``.
        panel_label_upper: Label panels ``A, B, C`` rather than ``a, b, c``. Science asks for
            uppercase; most publishers that state a convention at all ask for lowercase.
        panel_label_pt: Panel label font size.
        raster_dpi: The publisher's stated *minimum* resolution for raster artwork, and the resolution
            :func:`journalfig.save` writes at unless a higher one is asked for. Exceeding it is
            compliant -- the themes set ``savefig.dpi`` to 600 for that reason -- and only falling
            below it is a violation, which :func:`journalfig.save` warns about. ``None`` where the
            publisher states no resolution at all, as IOP does not: there is then no floor to enforce
            and :func:`journalfig.save` writes at the theme's own 600 dpi.
        formats: File formats :func:`journalfig.save` writes by default. The same three everywhere --
            PDF to submit, SVG to edit, PNG to drop into a talk -- since one figure is usually wanted
            in all three. Any other format the backend supports can be asked for explicitly.
        submission_formats: What the publisher accepts as *final artwork*, which is not the same
            question as what is useful to have on disk. Drives the draft warning in
            :func:`journalfig.save`, which fires only when nothing written is submittable: a PNG
            beside a PDF is silent, a PNG on its own is not.
        font_families: Typefaces the publisher asks for, most preferred first.
        font_substitutes: Metrically compatible stand-ins. Type designers cut these to the same
            widths, so a figure set in one is indistinguishable in layout from the real thing;
            :func:`journalfig.check` accepts them and :func:`journalfig.fonts` names them.
        tiff_compression: Pillow compression passed through when a TIFF is written, or ``None`` to
            write it uncompressed.
        style: Rendering choices for this theme. Deliberately a separate object: nothing in it comes
            from the publisher, and :func:`journalfig.check` never validates against it.
    """

    name: str
    widths_mm: dict[str, float]
    max_height_mm: float | None
    min_width_mm: float | None
    text_min_pt: float | None
    text_max_pt: float | None
    sub_min_pt: float | None
    min_lettering_mm: float | None
    min_marker_mm: float | None
    min_linewidth_pt: float | None
    panel_label_fmt: str
    panel_label_pt: float
    raster_dpi: int | None
    panel_label_upper: bool = False
    formats: tuple[str, ...] = DEFAULT_FORMATS
    submission_formats: tuple[str, ...] = ("pdf",)
    font_sizes: dict[str, float] = field(default_factory=dict)
    font_families: tuple[str, ...] = ()
    font_substitutes: tuple[str, ...] = ()
    # LZW is lossless, so the decoded pixels are identical to an uncompressed write and compliance
    # cannot change. Elsevier recommends TIFF but documents no compression scheme either way; this
    # is our choice, not theirs. Pass pil_kwargs={} to journalfig.save to turn it off.
    tiff_compression: str | None = "tiff_lzw"
    style: ThemeStyle = field(default_factory=ThemeStyle)
    #: Reasoning a generator cannot derive from the numbers -- why a size was chosen, or a trap the
    #: publisher's rules set. Emitted into the generated stylesheet header beneath the source citation.
    notes: tuple[str, ...] = ()


#: Furniture for a theme whose base text is 8-9 pt. The ThemeStyle defaults suit a 7 pt base; a larger
#: one carries slightly longer ticks and larger markers without looking heavy.
_MEDIUM = {
    "axes_linewidth": 0.6,
    "grid_linewidth": 0.5,
    "tick_major_size": 3.0,
    "tick_minor_size": 1.8,
    "tick_major_width": 0.6,
    "tick_minor_width": 0.5,
    "tick_pad": 2.5,
    "marker_size": 4.0,
    "marker_edge_width": 0.7,
    "errorbar_capsize": 2.0,
    "legend_handlelength": 1.8,
}

#: Serif rendering, for themes whose publisher sets its text in Times.
_SERIF = {
    "mathtext_fontset": "stix",
    "font_family_category": "serif",
    "font_stack": ("Times New Roman", "Times", "Nimbus Roman", "Liberation Serif", "STIXGeneral", "DejaVu Serif"),
}


SPECS: dict[str, JournalSpec] = {
    "nature": JournalSpec(
        name="Nature Portfolio",
        widths_mm={"single": 89.0, "onehalf": 120.0, "onehalf_wide": 136.0, "double": 183.0},
        max_height_mm=247.0,
        min_width_mm=None,
        text_min_pt=5.0,
        text_max_pt=7.0,
        sub_min_pt=5.0,  # Nature states one minimum for all text, so it binds subscripts too.
        min_lettering_mm=None,
        min_marker_mm=None,
        min_linewidth_pt=None,
        panel_label_fmt="{}",  # lowercase a, b, c -- no parentheses
        panel_label_pt=8.0,
        raster_dpi=300,
        submission_formats=("pdf",),  # Nature cannot accept JPEG/TIFF/PNG for final artwork.
        font_sizes={"base": 7.0, "label": 7.0, "tick": 6.0, "legend": 6.0, "title": 7.0},
        font_families=("Arial", "Helvetica", "Helvetica Neue"),
        font_substitutes=("Nimbus Sans", "Liberation Sans", "Arimo", "TeX Gyre Heros"),
        # The lightest of the three themes: Nature caps body text at 7 pt, so the furniture is drawn
        # finer to match. These are the ThemeStyle defaults.
        style=ThemeStyle(),
        notes=(
            "RGB colour space; supply editable vector artwork with live (non-outlined) text.",
            "Panel labels are 8 pt where body text caps at 7 pt, so check() exempts them by gid.",
        ),
    ),
    "aps": JournalSpec(
        name="American Physical Society (PRB/PRL)",
        # 8.5 cm / 3 3/8 in is published. The 1.5- and 2-column values are DERIVED from the standard
        # REVTeX two-column geometry (7.0 in text width, 0.25 in gutter); APS does not publish them.
        widths_mm={"single": 3.375 * MM_PER_INCH, "onehalf": 5.3125 * MM_PER_INCH, "double": 7.0 * MM_PER_INCH},
        max_height_mm=None,
        min_width_mm=None,
        text_min_pt=None,  # expressed as a printed height instead, see min_lettering_mm
        text_max_pt=None,
        sub_min_pt=None,
        min_lettering_mm=2.0,
        min_marker_mm=1.0,
        min_linewidth_pt=0.5,
        panel_label_fmt="({})",
        panel_label_pt=9.0,
        raster_dpi=600,
        # APS documents .ps/.eps for colour-online-only figures, so it counts as submittable and stays
        # available on request -- but it is never written by default, because the PostScript backend
        # cannot express transparency: any artist with alpha < 1 (a shaded error band, a filled
        # confidence region) is silently flattened to opaque, so the EPS and the PDF of the same
        # figure disagree. Ask for it deliberately, with formats=["pdf", "eps"], and check the result.
        submission_formats=("pdf", "eps"),
        font_sizes={"base": 9.0, "label": 9.0, "tick": 9.0, "legend": 9.0, "title": 9.0},
        font_families=("Times New Roman", "Times"),
        # STIXGeneral ships with matplotlib and was cut to Times metrics, so this theme still lands
        # on a compliant face on a machine with no Times installed.
        font_substitutes=("Nimbus Roman", "Liberation Serif", "Tinos", "TeX Gyre Termes", "STIXGeneral"),
        # Heavier throughout: a 9 pt serif base carries larger ticks and markers than Nature's 7 pt
        # sans. STIX rather than a custom set, since STIX is already metrically a Times.
        style=ThemeStyle(
            axes_linewidth=0.6,
            grid_linewidth=0.5,
            tick_major_size=3.0,
            tick_minor_size=1.8,
            tick_major_width=0.6,
            tick_minor_width=0.5,
            tick_pad=2.5,
            marker_size=4.0,
            marker_edge_width=0.7,
            errorbar_capsize=2.0,
            legend_handlelength=1.8,
            title_weight="normal",
            title_location="center",
            # STIX is metric-compatible with Times and covers the full maths range, so there is no
            # reason to pin the individual faces the way the sans themes must.
            mathtext_fontset="stix",
            font_family_category="serif",
            font_stack=(
                "Times New Roman",
                "Times",
                "Nimbus Roman",
                "Liberation Serif",
                "STIXGeneral",
                "DejaVu Serif",
            ),
        ),
        notes=(
            "9 pt is not cosmetic: Times New Roman digits measure 1.94 mm at 8 pt and 2.18 mm at\n"
            "9 pt, so 8 pt fails the 2 mm lettering rule.",
            "Axis units go in parentheses; subfigures are labelled (a), (b).",
        ),
    ),
    "elsevier": JournalSpec(
        name="Elsevier",
        widths_mm={"single": 90.0, "onehalf": 140.0, "double": 190.0},
        max_height_mm=None,
        min_width_mm=30.0,
        text_min_pt=7.0,
        text_max_pt=None,
        sub_min_pt=6.0,
        min_lettering_mm=None,
        min_marker_mm=None,
        min_linewidth_pt=None,
        panel_label_fmt="({})",
        panel_label_pt=8.0,
        raster_dpi=500,  # combination art
        # "EPS, PDF, TIFF or JPEG, or Microsoft Office files" -- Elsevier, Artwork formats checklist,
        # https://www.elsevier.com/about/policies-and-standards/author/artwork-and-media-instructions/
        # artwork-formats-checklist (retrieved 2026-08-05). EPS and PDF are named for vector artwork,
        # TIFF and JPEG for halftones and bitmaps. PNG is not on the list.
        submission_formats=("pdf", "eps", "tiff", "jpeg", "jpg"),
        font_sizes={"base": 7.0, "label": 7.0, "tick": 7.0, "legend": 7.0, "title": 7.0},
        # Elsevier names Arial, Courier, Times New Roman and Symbol, "or fonts that look similar".
        font_families=("Arial", "Times New Roman"),
        font_substitutes=("Helvetica", "Helvetica Neue", "Nimbus Sans", "Liberation Sans", "Arimo", "TeX Gyre Heros"),
        # Nature's 7 pt base but drawn a little heavier, since Elsevier figures are reproduced at a
        # wider single column (90 mm against 89 mm) and print on stock that takes more ink.
        style=ThemeStyle(
            axes_linewidth=0.6,
            grid_linewidth=0.5,
            tick_major_size=2.8,
            tick_minor_size=1.6,
            tick_major_width=0.6,
            tick_minor_width=0.5,
            marker_size=3.5,
            errorbar_capsize=1.8,
        ),
        notes=(
            'matplotlib renders maths sub/superscripts at 0.7x, so a 7 pt label puts "$x_a$" at\n'
            '4.9 pt, under the 6 pt floor. Use journalfig.use("elsevier", base_size=9) for\n'
            "maths-heavy figures, and journalfig.check(fig) to see the rendered sizes.",
        ),
    ),
    # ------------------------------------------------------------------------------------------------
    # Added 2026-08-24. Each entry below was read from the publisher's own author-guidelines document,
    # cited in SOURCES. Where a publisher states nothing, the field is None rather than a guess -- most
    # state widths and resolution and nothing else, which is why so many minima here are unset.
    # ------------------------------------------------------------------------------------------------
    "iop": JournalSpec(
        name="IOP Publishing",
        # "typically 8.5cm for a small/single-column figure and 15cm for a large/double-column figure"
        widths_mm={"single": 85.0, "double": 150.0},
        max_height_mm=None,
        min_width_mm=None,
        text_min_pt=8.0,  # "Aim for text sizes of 8 to 12 pt at the final figure size"
        text_max_pt=12.0,
        sub_min_pt=None,
        min_lettering_mm=None,
        min_marker_mm=None,
        min_linewidth_pt=None,
        panel_label_fmt="({})",  # "identified by a lower-case letter in parentheses"
        panel_label_pt=8.0,  # DEFAULT: IOP states no panel-label size; matched to its 8 pt text floor.
        raster_dpi=None,  # IOP states no resolution anywhere in its figures guidance.
        submission_formats=("pdf", "eps", "tiff", "png", "jpeg", "jpg"),
        font_sizes={"base": 8.0, "label": 8.0, "tick": 8.0, "legend": 8.0, "title": 8.0},
        # "Fonts used should be restricted to the standard font families (Times, Helvetica, Courier
        # or Symbol)." Courier and Symbol are for code and glyphs, not body text, so they are not
        # listed as body faces here.
        font_families=("Times", "Helvetica"),
        font_substitutes=("Nimbus Roman", "Liberation Serif", "Tinos", "TeX Gyre Termes", "STIXGeneral"),
        style=ThemeStyle(**_MEDIUM, title_weight="normal", title_location="center", **_SERIF),
        notes=("IOP states no resolution requirement, so save() writes at the theme's own 600 dpi.",),
    ),
    "aip": JournalSpec(
        name="AIP Publishing",
        # "The maximum published width for a one-column figure is 3.37 inches (8.5 cm). The maximum
        # width for a two-column figure is 6.69 inches (17 cm)." The two readings of each disagree
        # slightly; the smaller is taken, since both are stated as maxima.
        widths_mm={"single": 85.0, "double": 169.9},
        max_height_mm=209.6,  # "The maximum depth of figures should be 8 1/4 in. (21.1 cm)."
        min_width_mm=None,
        text_min_pt=8.0,  # "Legends or labels within figures should be a minimum of 8-point type size"
        text_max_pt=None,
        sub_min_pt=None,
        # AIP glosses 8 pt as "2.8 mm high", but that is the type size expressed in mm, not the printed
        # glyph height min_lettering_mm measures. Recording it there would demand roughly 11.5 pt text.
        min_lettering_mm=None,
        min_marker_mm=None,
        min_linewidth_pt=0.5,  # "A minimum of 0.5-point width for lines."
        panel_label_fmt="({})",  # "Identify all figure parts with (a), (b), etc."
        panel_label_pt=8.0,  # DEFAULT: no stated size; matched to the 8 pt text floor.
        raster_dpi=600,  # line art and combinations 600 dpi; halftones 264; colour online 300.
        submission_formats=("pdf", "eps", "ps", "tiff", "png", "jpeg", "jpg", "svg"),
        font_sizes={"base": 9.0, "label": 9.0, "tick": 9.0, "legend": 9.0, "title": 9.0},
        # AIP requires only that fonts be embedded, naming no typeface. An empty tuple means check()
        # reports the face as "unrestricted" rather than inventing a requirement to fail.
        font_families=(),
        font_substitutes=(),
        style=ThemeStyle(**_MEDIUM, title_weight="normal", title_location="center", **_SERIF),
        notes=("AIP names no required typeface; check() reports fonts as unrestricted here.",),
    ),
    "acs": JournalSpec(
        name="ACS Publications",
        # "Single-column graphics can be sized up to 240 points wide (3.33 in.)" and "double-column
        # graphics must be sized between 300 and 504 points (4.167 in. and 7 in.)".
        widths_mm={"single": 84.7, "double": 177.8},
        max_height_mm=232.8,  # "The maximum depth for all graphics is 660 points (9.167 in.)"
        # The 300 pt lower bound applies to double-column graphics only, not to every figure, so it is
        # deliberately not recorded as a figure-wide minimum.
        min_width_mm=None,
        text_min_pt=4.5,  # "Lettering should be no smaller than 4.5 points in the final published format"
        text_max_pt=None,
        sub_min_pt=None,
        min_lettering_mm=None,
        min_marker_mm=None,
        min_linewidth_pt=None,
        panel_label_fmt="({})",  # DEFAULT: ACS states no panel-label convention.
        panel_label_pt=8.0,
        raster_dpi=300,  # colour art 300 dpi; grayscale 600; black-and-white line art 1200.
        # "Image files should be submitted as TIF, JPG, PNG, or EPS files (not PDF or PPT)" -- PDF is
        # explicitly excluded, which is why it is absent here despite being the package default write.
        submission_formats=("eps", "tiff", "png", "jpeg", "jpg"),
        font_sizes={"base": 8.0, "label": 8.0, "tick": 8.0, "legend": 8.0, "title": 8.0},
        font_families=("Helvetica", "Arial"),
        font_substitutes=("Nimbus Sans", "Liberation Sans", "Arimo", "TeX Gyre Heros"),
        style=ThemeStyle(**_MEDIUM),
        notes=(
            "ACS accepts lettering down to 4.5 pt, far below what the other themes allow. check()\n"
            "enforces what the document says, so it will pass text most readers cannot read.",
            "Black-and-white line art wants 1200 dpi; the 300 dpi floor here is ACS's colour-art\n"
            "figure, which is what save() writes as a PNG companion.",
        ),
    ),
    "rsc": JournalSpec(
        name="Royal Society of Chemistry",
        # "Images should fit within either single column (8.3 cm) or double column (17.1 cm) width"
        widths_mm={"single": 83.0, "double": 171.0},
        max_height_mm=233.0,  # "must be no longer than 23.3 cm"
        min_width_mm=None,
        text_min_pt=None,
        text_max_pt=None,
        sub_min_pt=None,
        min_lettering_mm=None,
        min_marker_mm=None,
        min_linewidth_pt=0.5,  # "Bond width = 0.016 cm or 0.5 pt"
        panel_label_fmt="({})",  # DEFAULT: RSC states no panel-label convention.
        panel_label_pt=8.0,
        raster_dpi=600,  # "a resolution of 600 dpi or greater"
        submission_formats=("tiff", "eps", "pdf"),
        font_sizes={"base": 7.0, "label": 7.0, "tick": 7.0, "legend": 7.0, "title": 7.0},
        font_families=("Arial", "Helvetica"),  # "Captions/atom labels = Arial/Helvetica, 7 pt"
        font_substitutes=("Nimbus Sans", "Liberation Sans", "Arimo", "TeX Gyre Heros"),
        style=ThemeStyle(),
    ),
    "ieee": JournalSpec(
        name="IEEE",
        # "one column width (3.5 inches / 21 picas wide) or two column width (7.16 inches / 43 picas)"
        widths_mm={"single": 88.9, "double": 181.9},
        max_height_mm=None,
        min_width_mm=None,
        text_min_pt=None,  # "Type should appear approximately 9-10 point" is guidance, not a floor.
        text_max_pt=None,
        sub_min_pt=None,
        min_lettering_mm=None,
        min_marker_mm=None,
        min_linewidth_pt=None,
        panel_label_fmt="({})",  # DEFAULT: not stated in the graphics guidance.
        panel_label_pt=9.0,
        raster_dpi=None,  # Not stated in the graphics guidance this spec was read from.
        submission_formats=("ps", "eps", "pdf", "png", "tiff"),
        font_sizes={"base": 9.0, "label": 9.0, "tick": 9.0, "legend": 9.0, "title": 9.0},
        font_families=("Helvetica", "Times New Roman", "Arial", "Cambria", "Symbol"),
        font_substitutes=("Nimbus Sans", "Liberation Sans", "Arimo", "TeX Gyre Heros"),
        style=ThemeStyle(**_MEDIUM),
    ),
    "plos": JournalSpec(
        name="PLOS",
        # "Width: 789 - 2250 pixels (at 300 dpi)" -- DERIVED: 789/300 in = 66.8 mm, 2250/300 in = 190.5 mm.
        # PLOS has no column grid, so "single" is its minimum width and "double" its maximum.
        widths_mm={"single": 66.8, "double": 190.5},
        max_height_mm=222.3,  # DERIVED from "Height maximum: 2625 pixels (at 300 dpi)".
        min_width_mm=66.8,
        text_min_pt=8.0,  # "Arial, Times, or Symbol font only in 8-12 point."
        text_max_pt=12.0,
        sub_min_pt=None,
        min_lettering_mm=None,
        min_marker_mm=None,
        min_linewidth_pt=0.57,  # DERIVED from "the width of all lines to 0.2 mm".
        panel_label_fmt="({})",  # "a lettered panel label: for example, (A) or (a)"
        panel_label_pt=8.0,
        raster_dpi=300,  # "a resolution no greater than 300-600 dpi" -- 300 is the usable floor.
        submission_formats=("tiff", "eps"),  # "TIFF or EPS only."
        font_sizes={"base": 8.0, "label": 8.0, "tick": 8.0, "legend": 8.0, "title": 8.0},
        font_families=("Arial", "Times"),
        font_substitutes=("Nimbus Sans", "Liberation Sans", "Arimo", "TeX Gyre Heros"),
        style=ThemeStyle(**_MEDIUM),
        notes=(
            "PLOS states a resolution ceiling as well as a floor -- 300 to 600 dpi, and no more.\n"
            "JournalSpec models floors only, so the upper bound is not enforced.",
        ),
    ),
    "wiley": JournalSpec(
        name="Wiley",
        # "Small: 80 mm canvas size" / "Large: 180 mm canvas size"
        widths_mm={"single": 80.0, "double": 180.0},
        max_height_mm=None,
        min_width_mm=None,
        text_min_pt=None,
        text_max_pt=None,
        sub_min_pt=None,
        min_lettering_mm=None,
        min_marker_mm=None,
        min_linewidth_pt=None,
        panel_label_fmt="({})",  # DEFAULT: Wiley states no panel-label convention.
        panel_label_pt=8.0,
        raster_dpi=300,  # "Were figures created between 80 and 180 mm width? 300 to 600 DPI?"
        submission_formats=("eps", "pdf", "tiff", "png"),
        font_sizes={"base": 8.0, "label": 8.0, "tick": 8.0, "legend": 8.0, "title": 8.0},
        font_families=(),  # Wiley's artwork guidelines name no typeface at all.
        font_substitutes=(),
        style=ThemeStyle(**_MEDIUM),
        notes=("Wiley's artwork guide states widths, formats and resolution, and nothing about type.",),
    ),
    "pnas": JournalSpec(
        name="PNAS",
        # "1 column wide (20.5 picas / 3.42" / 8.7 cm), 1.5 columns wide (27 picas / 4.5" / 11.4 cm),
        # 2 columns wide (42.125 picas / 7" / 17.8 cm)". The three readings of each agree to well
        # within check()'s 0.5 mm tolerance; the centimetre figure is used.
        widths_mm={"single": 87.0, "onehalf": 114.0, "double": 178.0},
        max_height_mm=225.0,  # "Recommended max height: 54 picas / 9" / 22.5 cm."
        min_width_mm=None,
        text_min_pt=6.0,  # "Confirm that text size is at least 6 points after reduction."
        text_max_pt=None,
        sub_min_pt=None,
        min_lettering_mm=None,
        min_marker_mm=None,
        min_linewidth_pt=0.25,  # "graph lines at least 0.25 points wide"
        panel_label_fmt="({})",  # DEFAULT: PNAS's prose states no convention.
        panel_label_pt=8.0,
        raster_dpi=600,  # combination halftones 600-900 ppi; line art 1000-1200; halftones 300.
        submission_formats=("tiff", "eps", "pdf"),  # "TIFF, EPS, or PDF file formats are preferred."
        font_sizes={"base": 8.0, "label": 8.0, "tick": 8.0, "legend": 8.0, "title": 8.0},
        font_families=("Arial", "Helvetica", "Times"),
        font_substitutes=("Nimbus Sans", "Liberation Sans", "Arimo", "TeX Gyre Heros"),
        style=ThemeStyle(**_MEDIUM),
        notes=(
            "PNAS asks for LZW compression on TIFFs and never JPEG compression, which is what this\n"
            "package writes by default. Colour must be supplied as RGB.",
        ),
    ),
    "science": JournalSpec(
        name="Science (AAAS)",
        # "1 column = 21p3 picas (9 cm, or 3.6 in.)" and "2 column = 43p4 picas (18.3 cm, or 7.25 in.)"
        widths_mm={"single": 90.0, "double": 183.0},
        max_height_mm=None,
        min_width_mm=None,
        text_min_pt=6.0,  # "Labels are 6 to 9 points"
        text_max_pt=9.0,
        sub_min_pt=None,
        min_lettering_mm=None,
        min_marker_mm=None,
        min_linewidth_pt=0.28,  # "At final print size, minimum line weight is 0.28 pt (~0.10 mm)"
        panel_label_fmt="{}",  # "Panel parts are 10-point Bold - A B C D"
        panel_label_pt=10.0,
        panel_label_upper=True,
        raster_dpi=300,  # "a resolution of 300 to 500 dots per inch (dpi) at final print size"
        submission_formats=("pdf", "eps", "svg"),
        font_sizes={"base": 8.0, "label": 8.0, "tick": 7.0, "legend": 7.0, "title": 8.0},
        # "all text should be in a sans serif typeface, preferably Arial, or Helvetica"
        font_families=("Arial", "Helvetica"),
        font_substitutes=("Nimbus Sans", "Liberation Sans", "Arimo", "TeX Gyre Heros"),
        style=ThemeStyle(),
        notes=(
            "Panel labels are 10 pt where body text caps at 9 pt; check() exempts them by gid.",
            "Science asks authors to avoid red/green combinations and to carry meaning with shape\nas well as colour.",
        ),
    ),
}

#: Journal keys accepted by the public API.
JOURNALS = tuple(SPECS)

#: Aliases so common journal names resolve to a theme.
ALIASES = {
    "nature": "nature",
    "npj": "nature",
    "nature communications": "nature",
    "aps": "aps",
    "prb": "aps",
    "prl": "aps",
    "physical review b": "aps",
    "physical review letters": "aps",
    "elsevier": "elsevier",
    "acta": "elsevier",
    "acta materialia": "elsevier",
    "jncs": "elsevier",
    "journal of non-crystalline solids": "elsevier",
    "iop": "iop",
    "iop publishing": "iop",
    "journal of physics": "iop",
    "j. phys. condens. matter": "iop",
    "modelling simul. mater. sci. eng.": "iop",
    "aip": "aip",
    "applied physics letters": "aip",
    "apl": "aip",
    "journal of chemical physics": "aip",
    "jcp": "aip",
    "acs": "acs",
    "chemistry of materials": "acs",
    "chem. mater.": "acs",
    "journal of physical chemistry": "acs",
    "rsc": "rsc",
    "royal society of chemistry": "rsc",
    "chemical science": "rsc",
    "journal of materials chemistry": "rsc",
    "ieee": "ieee",
    "plos": "plos",
    "plos one": "plos",
    "wiley": "wiley",
    "advanced materials": "wiley",
    "journal of the american ceramic society": "wiley",
    "jacers": "wiley",
    "pnas": "pnas",
    "proceedings of the national academy of sciences": "pnas",
    "science": "science",
    "aaas": "science",
    "science advances": "science",
}


def resolve(journal: str) -> str:
    """Resolve a journal name or alias to a theme key.

    Args:
        journal: Theme key or a known journal alias, case-insensitive.

    Returns:
        One of ``"nature"``, ``"aps"``, ``"elsevier"``.

    Raises:
        KeyError: If the name is not a known theme or alias.

    Example:
        >>> resolve("Acta Materialia")
        'elsevier'
        >>> resolve("PRB")
        'aps'
    """
    key = ALIASES.get(journal.strip().lower())
    if key is None:
        raise KeyError(f"unknown journal {journal!r}; expected one of {JOURNALS} or an alias in {sorted(ALIASES)}")
    return key


def get_spec(journal: str) -> JournalSpec:
    """Look up the :class:`JournalSpec` for a journal name or alias.

    Args:
        journal: Theme key or a known journal alias.

    Returns:
        The matching specification.

    Example:
        >>> get_spec("nature").widths_mm["single"]
        89.0
    """
    return SPECS[resolve(journal)]


def source(journal: str) -> Source:
    """Look up the publisher document a theme's numbers came from.

    Args:
        journal: Theme key or a known journal alias.

    Returns:
        The document, including the date its numbers were last checked.

    Example:
        >>> print(source("PRB"))
        APS Journals Style Guide for Authors, November 2024 (retrieved 2026-07-28)
    """
    return SOURCES[resolve(journal)]
