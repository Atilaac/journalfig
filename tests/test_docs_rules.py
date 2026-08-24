"""The figure-design page must not claim a check that ``check()`` does not perform.

``docs/figure-design.md`` is hand-written prose -- no generator could produce it -- but its summary table
makes falsifiable claims about the code: that a rule is *checked*, and which ``Violation.kind`` reports
it. Nothing else ties the two together, so the page could keep advertising a rule after it was renamed or
removed, or stay silent about one that was added. That is worse than an ordinary stale document, because
the page's whole argument is that it distinguishes what the tool verifies from what it does not.

Author: Achraf Atila (achraf.atila@bam.de)
"""

from __future__ import annotations

import re
from pathlib import Path

from journalfig import _core

_PAGE = Path(__file__).resolve().parents[1] / "docs" / "figure-design.md"

#: The three states a rule may be in. Only ``checked`` may name a kind.
_CHECKED = "checked"
_STATES = (_CHECKED, "not checkable", "not yet")

#: Number words the closing section uses, so its counts can be compared against the table.
_NUMBERS = {
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "twenty-five": 25,
}


def _emitted_kinds() -> set[str]:
    """Every ``Violation.kind`` ``check()`` can report, read from the source.

    Reading the source rather than running ``check()`` is deliberate: a kind that only fires for a
    publisher no theme currently uses would never appear in a live run, and the page should still be
    allowed to document it.
    """
    source = Path(_core.__file__).read_text(encoding="utf-8")
    return set(re.findall(r'Violation\(\s*"([a-z_]+)"', source))


def _rows() -> list[tuple[int, str, str]]:
    """Parse the summary table into ``(number, rule, tag)`` triples."""
    text = _PAGE.read_text(encoding="utf-8")
    rows = re.findall(r"^\|\s*(\d+)\s*\|([^|]+)\|([^|]+)\|\s*$", text, flags=re.MULTILINE)
    return [(int(number), rule.strip(), tag.strip()) for number, rule, tag in rows]


def _claimed_kinds(tag: str) -> set[str]:
    """The ``Violation.kind`` names a tag cell claims, if any."""
    return set(re.findall(r"`([a-z_]+)`", tag))


def test_the_table_parses():
    """Without this, a reformatted table would make every other test here pass on zero rows."""
    assert len(_rows()) >= 20, "the summary table format changed; the regex in _rows() no longer matches"


def test_every_tag_is_one_of_the_three_states():
    """A fourth state would be skipped by the two tests below rather than failing them."""
    for number, rule, tag in _rows():
        assert tag.startswith(_STATES), f"rule {number} ({rule}) has an unrecognised tag: {tag!r}"


def test_kinds_the_page_claims_are_kinds_check_can_report():
    """The page saying `width` must mean `check()` can emit a `width` violation."""
    emitted = _emitted_kinds()
    for number, rule, tag in _rows():
        if not tag.startswith(_CHECKED):
            assert not _claimed_kinds(tag), f"rule {number} ({rule}) is not checked but names a kind: {tag!r}"
            continue
        claimed = _claimed_kinds(tag)
        assert claimed, f"rule {number} ({rule}) is marked checked but names no Violation kind"
        unknown = claimed - emitted
        assert not unknown, f"rule {number} ({rule}) claims {sorted(unknown)}, which check() never reports"


def test_every_kind_check_reports_appears_on_the_page():
    """Adding a rule to check() without documenting it leaves the page understating the tool."""
    claimed = {kind for _, _, tag in _rows() if tag.startswith(_CHECKED) for kind in _claimed_kinds(tag)}
    missing = _emitted_kinds() - claimed
    assert not missing, f"check() reports {sorted(missing)}, which the figure-design table never mentions"


def test_the_closing_counts_match_the_table():
    """The closing section counts the states in words, and the roadmap predicts those counts will move.

    Implementing a *not yet* rule is the whole point of listing them, and it changes two numbers written
    out in prose several hundred lines away from the table they describe.
    """
    text = _PAGE.read_text(encoding="utf-8")
    tallies = {state: sum(1 for _, _, tag in _rows() if tag.startswith(state)) for state in _STATES}

    def word(pattern: str) -> int:
        """The number word a sentence in the page states, as an integer."""
        match = re.search(pattern, text)
        assert match, f"the closing section no longer matches {pattern!r}; update the page or this test"
        return _NUMBERS[match.group(1).lower()]

    unfixable = r"(\w+) of the [\w-]+ rules above are marked \*\*not checkable\*\*"
    total = r"\w+ of the ([\w-]+) rules above are marked \*\*not checkable\*\*"
    pending = r"\*\*not yet\*\* rules are different: (\w+) of them"

    assert word(total) == len(_rows()), f"the closing section says {word(total)} rules; the table has {len(_rows())}"
    for pattern, state in ((unfixable, "not checkable"), (pending, "not yet")):
        assert word(pattern) == tallies[state], (
            f"the closing section says {word(pattern)} rules are '{state}'; the table has {tallies[state]}"
        )
