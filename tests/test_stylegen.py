"""The committed overlays must be what the generator produces.

``styles/<key>.mplstyle`` is generated from ``SPECS``; nothing stops someone editing the generated file
by hand, or changing a spec and forgetting to regenerate. Either way the stylesheet starts saying
something ``check()`` will then flag, which is the exact failure this whole layer exists to prevent.

Author: Achraf Atila (achraf.atila@bam.de)
"""

from __future__ import annotations

from dataclasses import replace

import matplotlib.pyplot as plt
import pytest

import journalfig as jf
from journalfig._core import _BASE_STYLE, _STYLE_DIR
from journalfig._stylegen import overlay_text


@pytest.fixture(autouse=True)
def _clean_rcparams():
    """Restore matplotlib's global state after every test."""
    saved = plt.rcParams.copy()
    yield
    plt.rcParams.update(saved)
    plt.close("all")


@pytest.mark.parametrize("journal", jf.JOURNALS)
def test_committed_overlay_matches_the_generator(journal):
    committed = (_STYLE_DIR / f"{journal}.mplstyle").read_text(encoding="utf-8")
    assert committed == overlay_text(journal), (
        f"{journal}.mplstyle is stale or hand-edited; run `python -m journalfig._stylegen`"
    )


@pytest.mark.parametrize("journal", jf.JOURNALS)
def test_overlay_cites_its_source(journal):
    """The provenance header is generated, so it cannot drift from SOURCES."""
    text = overlay_text(journal)
    source = jf.source(journal)
    assert source.url in text
    assert source.retrieved in text


@pytest.mark.parametrize("journal", jf.JOURNALS)
def test_overlay_carries_only_what_differs(journal):
    """Anything identical across every theme belongs in the base, not repeated in each overlay."""
    overlays = {
        j: jf._core.rc_params_from_file(_STYLE_DIR / f"{j}.mplstyle", use_default_template=False) for j in jf.JOURNALS
    }
    for key in overlays[journal]:
        present_everywhere = all(key in overlays[j] for j in jf.JOURNALS)
        identical = len({repr(overlays[j].get(key)) for j in jf.JOURNALS}) == 1
        assert not (present_everywhere and identical), f"{key} is the same in every theme; move it to _base.mplstyle"


def test_base_is_not_registered_as_a_theme():
    """_base.mplstyle is a fragment. Offering it to matplotlib as a style would be nonsense."""
    assert _BASE_STYLE.exists()
    assert "_base" not in plt.style.available


def test_base_supplies_what_the_overlays_omit():
    """A theme is base + overlay; neither half is a complete style on its own."""
    overlay = jf._core.rc_params_from_file(_STYLE_DIR / "nature.mplstyle", use_default_template=False)
    assert "axes.prop_cycle" not in overlay  # lives in the base
    jf.use("nature")
    assert len(plt.rcParams["axes.prop_cycle"]) == 8


# The two branches below exist for journals not yet added, so nothing in SPECS reaches them today.
# They are the first paths a new publisher will hit, which is exactly why they are tested now.


def test_a_floor_above_the_shared_default_overrides_it(monkeypatch):
    """Elsevier states 1000 dpi for line art; a theme built on that must not silently render at 600."""
    steep = replace(jf.SPECS["elsevier"], name="Steep Press", raster_dpi=1000)
    monkeypatch.setitem(jf.SPECS, "steep", steep)
    text = overlay_text("steep")
    assert "savefig.dpi" in text
    assert "1000" in text


def test_a_journal_stating_no_marker_floor_gets_a_plain_comment(monkeypatch):
    """Most publishers state no data-point minimum, so the comment must not invent one."""
    loose = replace(jf.SPECS["aps"], name="Loose Press", min_marker_mm=None)
    monkeypatch.setitem(jf.SPECS, "loose", loose)
    text = overlay_text("loose")
    assert "mm printed." in text
    assert "data-point rule" not in text


def test_generation_survives_a_missing_source(monkeypatch):
    """A spec with no SOURCES entry is a bug the conformance test catches -- but not by crashing here."""
    monkeypatch.setitem(jf.SPECS, "orphan", jf.SPECS["nature"])
    assert "font.size" in overlay_text("orphan")
