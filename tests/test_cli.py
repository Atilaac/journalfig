"""Tests for the command line interface.

Exit codes are the contract here, because the point of the CLI is a paper repository failing its build
on a figure that would be bounced at submission: 0 compliant, 1 violations found, 2 could not even look.

Author: Achraf Atila (achraf.atila@bam.de)
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pytest

import journalfig as jf
from journalfig._cli import EXIT_ERROR, _as_figures, load_figures, main

#: Fonts matplotlib ships, so nothing here depends on what the machine has installed.
BUNDLED_FONTS = Path(matplotlib.get_data_path()) / "fonts" / "ttf"

COMPLIANT = """
import journalfig as jf
jf.use("aps")
fig, ax = jf.subplots("aps", width="single")
ax.plot([0, 1], [0, 1])

def make():
    return jf.subplots("aps", width="double")
"""

SLOPPY = """
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(6.4, 4.8))
ax.plot([0, 1, 2], [1, 3, 2], lw=0.3, marker="o", ms=1.0)
ax.set_xlabel("q")
"""


@pytest.fixture(autouse=True)
def _clean_rcparams():
    """Restore matplotlib's global state after every test."""
    saved = plt.rcParams.copy()
    yield
    plt.rcParams.update(saved)
    plt.close("all")


@pytest.fixture(autouse=True)
def _bundled_serif(monkeypatch):
    """Resolve every font lookup to STIXGeneral, which matplotlib ships and APS accepts as a substitute.

    Without this, the exit-code assertions below pass on a developer's macOS (which has Times and Arial)
    and fail on CI, which installs no journal typeface on purpose. Exit code is the CLI's contract, so
    these tests have to be able to assert it without depending on the machine.
    """
    path = str(BUNDLED_FONTS / "STIXGeneral.ttf")
    monkeypatch.setattr(jf._core, "findfont", lambda *args, **kwargs: path)


@pytest.fixture
def script(tmp_path):
    """Write a plotting script and return its path."""

    def _write(body, name="figs.py"):
        path = tmp_path / name
        path.write_text(body, encoding="utf-8")
        return str(path)

    return _write


def test_compliant_figures_exit_zero(script, capsys):
    assert main(["check", script(COMPLIANT), "-j", "aps"]) == 0
    assert "0 violations" in capsys.readouterr().out


def test_violations_exit_one_and_are_listed(script, capsys):
    assert main(["check", script(SLOPPY), "-j", "aps"]) == 1
    out = capsys.readouterr().out
    assert "[width]" in out
    assert "[line]" in out
    assert "[marker]" in out


def test_the_journal_changes_the_verdict(script, capsys):
    """The same figure fits one publisher's column and not another's; that is the whole product."""
    path = script("import journalfig as jf\nfig, ax = jf.subplots('nature', width='single')\n")
    main(["check", path, "-j", "nature"])
    assert "[width]" not in capsys.readouterr().out
    main(["check", path, "-j", "elsevier"])  # 89 mm is Nature's column, Elsevier's is 90
    assert "[width]" in capsys.readouterr().out


def test_missing_file_is_an_error_not_a_failure(capsys):
    """Exit 2, not 1: nothing was checked, so reporting 'compliant' or 'violations' would both lie."""
    assert main(["check", "no_such_file.py", "-j", "nature"]) == EXIT_ERROR
    assert "no such file" in capsys.readouterr().err


def test_a_target_that_raises_reports_its_exception(script, capsys):
    assert main(["check", script("raise ValueError('boom')"), "-j", "nature"]) == EXIT_ERROR
    assert "ValueError: boom" in capsys.readouterr().err


def test_a_target_producing_no_figures_is_an_error(script, capsys):
    assert main(["check", script("x = 1"), "-j", "nature"]) == EXIT_ERROR
    assert "produced no figures" in capsys.readouterr().err


def test_unknown_journal_is_reported_without_key_error_quoting(script, capsys):
    assert main(["check", script(COMPLIANT), "-j", "nosuch"]) == EXIT_ERROR
    err = capsys.readouterr().err
    assert "unknown journal 'nosuch'" in err
    assert not err.startswith('journalfig: "')


def test_a_journal_alias_works(script, capsys):
    """ "PRB" has to reach the APS spec, or the alias table is decoration."""
    assert main(["check", script(COMPLIANT), "-j", "PRB"]) == 0
    assert "OK" in capsys.readouterr().out


def test_callable_target_form(script, monkeypatch, tmp_path, capsys):
    monkeypatch.syspath_prepend(str(tmp_path))
    script(COMPLIANT, name="mod_under_test.py")
    assert main(["check", "mod_under_test:make", "-j", "aps"]) == 0
    assert "OK" in capsys.readouterr().out


def test_bad_module_target_is_an_error(capsys):
    assert main(["check", "no.such.module:fn", "-j", "nature"]) == EXIT_ERROR
    assert "could not load" in capsys.readouterr().err


def test_journals_lists_every_theme(capsys):
    assert main(["journals"]) == 0
    out = capsys.readouterr().out
    for journal in jf.JOURNALS:
        assert journal in out


def test_target_compliance_warnings_do_not_leak(script, capsys):
    """The target may call save(); its warnings would duplicate the table we are about to print."""
    body = "import journalfig as jf\njf.use('aps')\nfig, _ = jf.subplots('aps')\n"
    body += "import tempfile, pathlib\n"
    body += "jf.save(fig, pathlib.Path(tempfile.mkdtemp()) / 'f', formats=['png'], validate=False)\n"
    assert main(["check", script(body), "-j", "aps"]) == 0
    assert "draft" not in capsys.readouterr().out


def test_as_figures_unwraps_the_subplots_pair():
    fig, ax = plt.subplots()
    assert _as_figures((fig, ax)) == [fig]
    assert _as_figures([[fig], fig]) == [fig]  # nested, and deduplicated
    assert _as_figures("not a figure") == []


def test_load_figures_closes_whatever_was_open_before(script):
    """A figure left over from an earlier check must not be reported against the next target."""
    stale = plt.figure()
    figures = load_figures(script("import matplotlib.pyplot as plt\nplt.figure()\n"))
    assert stale not in figures
    assert len(figures) == 1
