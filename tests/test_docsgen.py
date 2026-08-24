"""The committed specifications page must be what the generator produces.

``docs/specifications.md`` restated every width, font size and accepted format by hand. It was accurate,
but nothing kept it that way: a spec change left the published page quietly describing the previous
release. The per-journal half is generated now, and this is what fails the build when it goes stale.

Author: Achraf Atila (achraf.atila@bam.de)
"""

from __future__ import annotations

import pytest

import journalfig as jf
from journalfig._docsgen import _DOCS_PAGE, SENTINEL, read_tail, specifications_text


def test_committed_page_matches_the_generator():
    committed = _DOCS_PAGE.read_text(encoding="utf-8")
    assert committed == specifications_text(read_tail()), (
        "docs/specifications.md is stale; run `python -m journalfig._docsgen`"
    )


@pytest.mark.parametrize("journal", jf.JOURNALS)
def test_every_journal_appears_with_its_numbers(journal):
    page = _DOCS_PAGE.read_text(encoding="utf-8")
    spec = jf.get_spec(journal)
    assert f"### {spec.name} (`{journal}`)" in page
    assert f"{spec.widths_mm['single']:.1f} mm" in page
    if spec.raster_dpi is None:
        assert "no minimum stated" in page
    else:
        assert f"raster at {spec.raster_dpi} dpi" in page


@pytest.mark.parametrize("journal", jf.JOURNALS)
def test_every_journal_cites_its_source(journal):
    page = _DOCS_PAGE.read_text(encoding="utf-8")
    source = jf.source(journal)
    assert source.url in page
    assert source.retrieved in page


def test_hand_written_prose_survives_regeneration():
    """The tail is reasoning no generator can produce; regenerating must never eat it."""
    tail = read_tail()
    assert tail.startswith(SENTINEL)
    assert "Choices the package makes" in tail
    assert tail in specifications_text(tail)


def test_regenerating_without_the_sentinel_refuses(tmp_path):
    """Without the marker the generator cannot tell prose from output, so it must not guess."""
    page = tmp_path / "specifications.md"
    page.write_text("# Specifications\n\nno marker here\n", encoding="utf-8")
    with pytest.raises(ValueError, match="refusing to regenerate"):
        read_tail(page)


def test_jpg_and_jpeg_are_not_listed_twice():
    """Elsevier's submission formats carry both spellings; a reader wants one."""
    page = _DOCS_PAGE.read_text(encoding="utf-8")
    accepted = next(line for line in page.splitlines() if line.startswith("- **Accepted") and "JPEG" in line)
    assert accepted.count("JPEG") == 1
    assert "JPG" not in accepted
