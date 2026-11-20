"""File Space Fragmentation Estimator.

Estimates filesystem fragmentation by analysing the gaps between the logical
block extents reported by ``os.stat``.  The public surface is deliberately
small: one dataclass and one function.
"""

from .core import FragmentationReport, estimate_fragmentation

__all__ = ["FragmentationReport", "estimate_fragmentation"]
