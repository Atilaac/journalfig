"""Allow ``python -m journalfig`` alongside the installed ``journalfig`` console script.

The console script only exists after an install picks up ``[project.scripts]``; this always works from
a checkout, which is the difference between the CLI being usable and being usable after a reinstall.

Author: Achraf Atila (achraf.atila@bam.de)
"""

from __future__ import annotations

import sys

from ._cli import main

if __name__ == "__main__":
    sys.exit(main())
