# file_space_fragmentation_estimator_lib

Estimates filesystem fragmentation for a single path by comparing the blocks
the OS says are allocated (``os.stat().st_blocks``) with the minimum number of
512-byte blocks the logical size requires.

```python
from file_space_fragmentation_estimator_lib import estimate_fragmentation

report = estimate_fragmentation(__file__)
print(report.logical_size)          # bytes
print(report.allocated_blocks)      # st_blocks
print(report.minimum_blocks)        # ceil(logical_size / 512)
print(report.gap_blocks)            # allocated - minimum, clamped at zero
print(report.fragmentation_ratio)   # gap / allocated, in [0.0, 1.0]
```

## Why this exists

``os.stat`` is the only fragmentation signal available without root and
without filesystem-specific ioctls.  It is coarse: it tells you how many
blocks are allocated, not where they are.  A file that is logically
contiguous but stored with a trailing partial block looks identical to one
that is scattered.  The library therefore reports an *upper bound* on
fragmentation.  That trade-off is deliberate: a conservative estimate that
never under-reports is more useful for capacity planning than a precise one
that requires privileges.

## The awkward edge

Sparse files break the arithmetic.  On tmpfs and some other filesystems a
sparse file can report fewer ``st_blocks`` than ``ceil(st_size / 512)``.  The
implementation clamps ``gap_blocks`` to zero rather than reporting a negative
gap, and the ratio stays in ``[0.0, 1.0]``.  This means a sparse file is
reported as non-fragmented, which is the honest answer for the signal we
have.
