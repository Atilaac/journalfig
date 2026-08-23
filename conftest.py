"""Pytest configuration: render headlessly so tests and doctests never open a window.

Author: Achraf Atila (achraf.atila@bam.de)
"""

import matplotlib

matplotlib.use("Agg")
