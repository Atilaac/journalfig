# Contributing to journalfig

Thanks for considering a contribution. The package has one unusual constraint that shapes everything
below: **every number in it must be traceable to a publisher document.** A pull request that changes a
width, a font size, or a minimum without citing where the value comes from cannot be merged, however
sensible the value looks.

## Setup

```bash
git clone https://github.com/Atilaac/journalfig
cd journalfig
uv pip install -e ".[dev]"     # or: pip install -e ".[dev]"
pre-commit install
```

## Checks

```bash
pytest -q                                   # tests/ plus every docstring Example: block
coverage run -m pytest -q && coverage report # coverage (see the note below -- not pytest-cov)
pytest tests/test_journalfig.py -x -k mosaic  # one test
ruff check src/ tests/ demo.py
ruff format --check --diff src/ tests/ demo.py
pytest --mpl tests/test_visual.py           # image comparison against tests/baseline/
mkdocs serve                                # live docs preview
pytest --nbval-lax examples/                # execute every example notebook
python demo.py                              # regenerate gallery/
```

CI runs the suite on Linux, macOS, and Windows across Python 3.12-3.14, **with no journal typeface
installed**. Tests must therefore never depend on Arial or Times being present on the machine: use the
`BUNDLED_FONTS` path and the `_force_font` helper in `tests/test_journalfig.py` to simulate a specific
font situation.

## What a change needs

**A publisher citation, for anything numeric.** Add or update the entry in `SOURCES`
(`src/journalfig/_specs.py`), including the `retrieved` date, and mention the document section in a
comment beside the value. If a number cannot be read directly from a publisher document and has to be
derived, say so in the comment and mark it `DERIVED`, as the APS 1.5- and 2-column widths are.

**Both halves of a size change.** Widths and font sizes live twice: in `SPECS` and in the matching
`src/journalfig/styles/*.mplstyle`. `check()` validates figures against `SPECS`, so if the two drift the
theme starts flagging its own output. Change both in the same commit.

**An executed example.** Every public function carries a Google docstring with an `Example:` block, and
`pytest` runs those blocks as doctests (`--doctest-modules`). A new function without one is untested by
the project's own convention.

**A `_pin_size` call, if it creates a figure.** Interactive backends round a new figure to whole device
pixels, which silently destroys the exact column width the package exists to guarantee. Every factory
(`figure`, `subplots`, `mosaic`, `gridspec`) records its requested size through `_pin_size`; a new one
must too. This is invisible under the `Agg` backend used in tests, so no test will catch its absence.

**A pull request title a user can read.** There is no `CHANGELOG.md`; the draft GitHub Release is the
changelog, and it is assembled from merged pull request titles. Write the title as the changelog line it
will become — what changed for someone using the package, not what was done to the code. Add
`skip-changelog` to keep a pull request out of the notes entirely.

## Changing what a figure looks like

`tests/test_visual.py` renders a figure per theme and compares it against a committed baseline in
`tests/baseline/`. It exists because the rest of the suite cannot see this class of change: flipping
`xtick.direction` from `in` to `out` in a `.mplstyle` leaves all 76 other tests passing while every figure
the theme produces changes. Typography is normalised to matplotlib's bundled DejaVu faces first, so the
baselines match on a machine with Arial and on a bare CI runner alike; which typeface actually gets
resolved is covered by the `fonts()` and `check()` tests instead.

**The comparison runs only on FreeType 2.6.1**, the version matplotlib's PyPI wheels bundle and the one
the baselines were rendered with. A conda-forge matplotlib links a newer FreeType, which rasterises the
same glyphs differently — enough to miss the tolerance by an RMS of 2 to 16 on a single-column figure,
where the image is only ~350 px wide and glyphs are much of it. On any other build the tests skip the
pixel comparison instead of failing; the CI job asserts the version first, so the skip cannot hide a
regression there. Platform does not matter once FreeType matches: the same baselines produce identical
RMS values on macOS and on the Linux runner.

If you change a theme deliberately, regenerate the baselines in the same commit and say so in the message,
so a reviewer can see the pixels moved on purpose. Do it from a wheel-installed environment:

```bash
python -m venv /tmp/mplbaseline
/tmp/mplbaseline/bin/pip install -e ".[test]" matplotlib==3.10.9
/tmp/mplbaseline/bin/python -m pytest --mpl-generate-path=tests/baseline tests/test_visual.py
```

Not every theme rcParam is visible to these tests: `axes.unicode_minus` renders pixel-identical while
`use_mathtext` is on, so it is asserted directly in `test_journalfig.py` instead. When you change a
theme setting, check which of the two guards it before assuming it is covered.

Baselines are matplotlib-version sensitive, so CI pins `matplotlib==3.10.9` exactly for this job rather
than a `3.10.*` range — a patch release that changes antialiasing would otherwise fail the job at a
moment unrelated to any change. Bump the pin and regenerate the baselines in one commit. Without `--mpl`
these tests still run and still catch exceptions — they just compare nothing.

## Types and the dependency floor

The package ships `py.typed`, which tells downstream type checkers to trust its annotations, so keep every
public function annotated. **No type checker runs in CI**, which makes that a promise on the author rather
than a verified one: a wrong annotation will reach a release, and the person who finds it will be a user
running their own checker. Run one locally if you change a signature. The one `# type: ignore` in the
codebase is on `plt.subplot_mosaic`, where a union argument cannot be matched against matplotlib's
overload set; it carries a comment saying so.

`pyproject.toml` claims `matplotlib>=3.8` and `python>=3.12`, and a `minimum-versions` CI job installs
exactly that so the floor is tested rather than asserted. If you use a matplotlib feature newer than 3.8,
that job is what will tell you. The two floors are more coupled than they look: matplotlib 3.8 is the
last series that has cp312 wheels, since it never supported 3.13, so raising the Python floor past 3.12
would force the matplotlib floor up with it.

## Two notes on the test setup

`pyproject.toml` turns `JournalFigWarning` into an error during tests, so a test that trips a compliance
warning it did not ask for fails. Tests that mean to raise one must wrap it in `pytest.warns`.

Collect coverage with `coverage run -m pytest`, **not** `pytest --cov`. Naming the warning category in the
ini file makes pytest import `journalfig` while parsing the config, which happens before pytest-cov starts
measuring; every module-level statement then counts as uncovered and the total reads 69% instead of 96%.

## Adding a journal

Three edits to `src/journalfig/_specs.py` — a `JournalSpec` in `SPECS`, a `Source` in `SOURCES`, and the
journal's aliases in `ALIASES` — then run the two generators:

```bash
python -m journalfig._stylegen    # writes src/journalfig/styles/<key>.mplstyle
python -m journalfig._docsgen     # rewrites the generated half of docs/specifications.md
```

Do not hand-write the stylesheet. It is generated from `SPECS`, and `tests/test_stylegen.py` fails if the
committed file and the generator disagree; `tests/test_docsgen.py` does the same for the specifications
page. `register()` globs the style directory and `JOURNALS` follows `SPECS`, so everything parametrised
over `jf.JOURNALS` picks the new key up automatically.

Two things the generators cannot reach: the theme count in the one-line description, which appears in
`pyproject.toml`, `mkdocs.yml`, `CITATION.cff`, `README.md` and the `_specs.py` and `__init__.py` module
docstrings; and `tests/rcparams_reference.json`, which needs regenerating with
`python tests/test_rcparams.py` so the new theme's resolved rcParams are snapshotted.

**No test can tell you whether the numbers are right.** The suite verifies an entry is complete and
self-consistent, never that it matches the publisher's document. That stays a human review against the
cited source, which is why the `Source` and its `retrieved` date are mandatory.

## Versioning

The project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html) with one adaptation that
matters more here than the specification text does: **the public surface is the rendered figure, not only
the function signatures.** A user depends on `jf.subplots("nature", width="single")` producing an 89 mm
figure with 7 pt labels exactly as much as on it returning `(fig, ax)`. A number moving is therefore an
interface change, even though no signature moved and every test still passes.

The package is on 0.x, where SemVer leaves MAJOR without meaning. Until 1.0 the mapping is: anything that
would be MAJOR becomes a MINOR bump (0.1.0 → 0.2.0), and anything that would be MINOR or PATCH becomes a
PATCH bump (0.2.0 → 0.2.1). The table gives both, so it does not need rewriting at 1.0.

| Change | After 1.0 | Now (0.x) | Label |
| --- | --- | --- | --- |
| Remove or rename a public function, parameter, theme key, or alias | MAJOR | MINOR | `breaking` |
| Change a default that moves every figure and cannot be argued back | MAJOR | MINOR | `breaking` |
| Raise the Python or matplotlib floor | MAJOR | MINOR | `breaking` |
| Tighten the `vector` rule so a figure that passed `check()` now fails | MAJOR | MINOR | `breaking` |
| **A publisher-stated number moves** — width, font size, minimum, dpi floor, accepted format | MINOR | MINOR | `specification` |
| Add a journal, an alias, a function, a parameter, or a `check()` rule traceable to a publisher document | MINOR | PATCH | `journal`, `feature` |
| Fix a bug without moving a number | PATCH | PATCH | `bug` |
| Docs, comments, tests, CI, packaging, or a `retrieved` date refreshed on numbers that did not change | PATCH | PATCH | `documentation`, `maintenance` |

`.github/release-drafter.yml` encodes this table, so the labels on the merged pull requests resolve the
next version by themselves; the draft release shows the number it arrived at.

### A specification change is never a patch

It is the one rule worth stating on its own, because it reads backwards. Correcting a width that
`journalfig` had *wrong* feels like a bug fix, and SemVer would call it a patch. It is a MINOR bump here
regardless of cause, for two reasons:

- Every figure a user renders with that theme changes size or type, silently, on a `pip install -U`.
- `check()` validates against the spec, so a figure that passed can start failing — and a paper repository
  running `journalfig check` in CI goes red for a reason that has nothing to do with anything it changed.

`~=0.2.0` has to be enough to hold a figure still. That only works if a moved number is never hidden in
the patch digit. Name the journal and the old → new value in the pull request title, and cite the
publisher document in the diff as always.

The reverse also holds: refreshing a `retrieved` date after checking a document that turned out unchanged
is a patch. Nothing moved.

## Releasing

Maintainers only. There is no `CHANGELOG.md` — [Release
Drafter](https://github.com/release-drafter/release-drafter) keeps a draft GitHub Release up to date as
pull requests merge, and that draft is the changelog.

1. Open the draft release and read it. It is assembled from pull request titles, so fix anything that
   reads as an implementation note rather than a user-facing change, and check the version it resolved to
   against the table above.
2. Set `__version__` in `src/journalfig/__init__.py` to that number. It is the single source of truth;
   `pyproject.toml` reads it through `[tool.hatch.version]`. Commit that alone.
3. Tag and push:

   ```bash
   git tag -a v0.2.0 -m "v0.2.0"
   git push origin v0.2.0
   ```

4. Publish the draft release against the new tag.

`publish.yml` verifies the tag matches `__version__`, builds, and uploads to PyPI through Trusted
Publishing. No API token is stored in the repository.

**`__version__` never moves in an ordinary pull request.** It is bumped once, in the release commit.
Bumping it per-change would conflict on every parallel branch, and the tag check in `publish.yml` means a
half-bumped `main` fails the release rather than shipping the wrong number.

`packaging/journalfigs/` carries its own hard-coded version and is released separately. Bump it only when
the alias package itself changes — not when `journalfig.__version__` moves.
