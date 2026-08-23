"""Alias package: ``journalfigs`` is the same library as :mod:`journalfig`.

Published so the plural spelling resolves to the real package rather than being left for
someone else to claim. Importing it hands back the ``journalfig`` module itself, so
``journalfigs.use("nature")`` and ``journalfig.use("nature")`` are the same call on the
same module object -- there is no second copy of anything.

Author: Achraf Atila (achraf.atila@bam.de)
"""

import sys

import journalfig

sys.modules[__name__] = journalfig
