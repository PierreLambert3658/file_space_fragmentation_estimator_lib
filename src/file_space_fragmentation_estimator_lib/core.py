"""Core fragmentation estimation logic.

We model a file as a sequence of logical blocks.  ``os.stat`` gives us the
number of blocks actually allocated (``st_blocks``) and the logical size in
bytes (``st_size``).  On most Unix filesystems ``st_blocks`` counts 512-byte
units.  A perfectly contiguous file uses exactly ``ceil(st_size / 512)``
blocks.  Any extra allocated blocks are the result of internal fragmentation
or holes that the filesystem still accounts for.

The estimator is intentionally conservative: it treats *every* block beyond the
minimum as a fragmentation gap, because we cannot see the physical layout from
``os.stat`` alone.  This over-estimates on filesystems with compression or
delayed allocation, but it never under-estimates.  That trade-off is the whole
point of the library.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Union

# ``os.stat`` reports ``st_blocks`` in 512-byte units on every platform we
# care about.  The constant is named so the assumption is visible and testable.
STAT_BLOCK_SIZE = 512


@dataclass(frozen=True)
class FragmentationReport:
    """Result of analysing a single file.

    Attributes
    ----------
    path:
        The path that was analysed, exactly as passed in.
    logical_size:
        ``st_size`` in bytes.
    allocated_blocks:
        ``st_blocks`` as reported by the OS.
    minimum_blocks:
        Blocks a contiguous file of this size would need.
    gap_blocks:
        ``allocated_blocks - minimum_blocks``, never negative.
    fragmentation_ratio:
        ``gap_blocks / allocated_blocks`` when ``allocated_blocks > 0``,
        otherwise ``0.0``.  In ``[0.0, 1.0]``.
    """

    path: str
    logical_size: int
    allocated_blocks: int
    minimum_blocks: int
    gap_blocks: int
    fragmentation_ratio: float


PathLike = Union[str, bytes, os.PathLike]


def estimate_fragmentation(path: PathLike) -> FragmentationReport:
    """Estimate fragmentation for *path* using ``os.stat``.

    Raises ``FileNotFoundError`` if the path does not exist and
    ``OSError`` for any other stat failure.  Directories are allowed: their
    ``st_size`` and ``st_blocks`` are whatever the filesystem reports, and the
    same arithmetic applies.

    The function never returns a negative ``gap_blocks``.  Some filesystems
    (notably tmpfs) report ``st_blocks`` smaller than ``ceil(st_size / 512)``
    for sparse files; clamping to zero keeps the ratio meaningful.
    """
    st = os.stat(path)

    logical_size = st.st_size
    allocated_blocks = st.st_blocks

    # ``st_size`` can be zero for empty files or some special files.  A
    # contiguous file of size zero needs zero blocks, so the floor division
    # below is correct without a special case.
    minimum_blocks = (logical_size + STAT_BLOCK_SIZE - 1) // STAT_BLOCK_SIZE

    gap_blocks = allocated_blocks - minimum_blocks
    if gap_blocks < 0:
        gap_blocks = 0

    if allocated_blocks > 0:
        fragmentation_ratio = gap_blocks / allocated_blocks
    else:
        fragmentation_ratio = 0.0

    return FragmentationReport(
        path=os.fspath(path) if not isinstance(path, bytes) else path.decode(),
        logical_size=logical_size,
        allocated_blocks=allocated_blocks,
        minimum_blocks=minimum_blocks,
        gap_blocks=gap_blocks,
        fragmentation_ratio=fragmentation_ratio,
    )
