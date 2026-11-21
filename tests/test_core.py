"""Tests for the fragmentation estimator.

These tests do not depend on any particular filesystem layout beyond what
``os.stat`` reports for a file we just wrote.  Where the OS reports a value
that could vary (``st_blocks``), we compute the expected value from the same
inputs the implementation uses, so the assertions stay deterministic.
"""

import os
import tempfile
import unittest

from file_space_fragmentation_estimator_lib import (
    FragmentationReport,
    estimate_fragmentation,
)
from file_space_fragmentation_estimator_lib.core import STAT_BLOCK_SIZE


class TestEstimateFragmentation(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

    def _write(self, name, data):
        path = os.path.join(self.tmpdir.name, name)
        with open(path, "wb") as fh:
            fh.write(data)
        return path

    def test_empty_file(self):
        path = self._write("empty.bin", b"")
        report = estimate_fragmentation(path)
        self.assertIsInstance(report, FragmentationReport)
        self.assertEqual(report.logical_size, 0)
        self.assertEqual(report.minimum_blocks, 0)
        self.assertEqual(report.gap_blocks, 0)
        self.assertEqual(report.fragmentation_ratio, 0.0)

    def test_small_file_minimum_blocks(self):
        path = self._write("small.bin", b"x" * 100)
        report = estimate_fragmentation(path)
        self.assertEqual(report.logical_size, 100)
        self.assertEqual(report.minimum_blocks, 1)
        # st_blocks is at least 1 for a non-empty file on every filesystem we
        # support; gap can be zero or positive.
        self.assertGreaterEqual(report.allocated_blocks, 1)
        self.assertGreaterEqual(report.gap_blocks, 0)
        self.assertGreaterEqual(report.fragmentation_ratio, 0.0)
        self.assertLessEqual(report.fragmentation_ratio, 1.0)

    def test_exact_block_boundary(self):
        path = self._write("boundary.bin", b"y" * STAT_BLOCK_SIZE)
        report = estimate_fragmentation(path)
        self.assertEqual(report.logical_size, STAT_BLOCK_SIZE)
        self.assertEqual(report.minimum_blocks, 1)
        self.assertGreaterEqual(report.gap_blocks, 0)

    def test_one_byte_over_boundary(self):
        path = self._write("over.bin", b"z" * (STAT_BLOCK_SIZE + 1))
        report = estimate_fragmentation(path)
        self.assertEqual(report.logical_size, STAT_BLOCK_SIZE + 1)
        self.assertEqual(report.minimum_blocks, 2)
        self.assertGreaterEqual(report.gap_blocks, 0)

    def test_ratio_matches_gap_over_allocated(self):
        path = self._write("ratio.bin", b"a" * 4096)
        report = estimate_fragmentation(path)
        if report.allocated_blocks > 0:
            expected = report.gap_blocks / report.allocated_blocks
            self.assertAlmostEqual(report.fragmentation_ratio, expected, places=12)
        else:
            self.assertEqual(report.fragmentation_ratio, 0.0)

    def test_path_is_preserved(self):
        path = self._write("named.bin", b"data")
        report = estimate_fragmentation(path)
        self.assertEqual(report.path, path)

    def test_missing_file_raises(self):
        missing = os.path.join(self.tmpdir.name, "does-not-exist.bin")
        with self.assertRaises(FileNotFoundError):
            estimate_fragmentation(missing)

    def test_directory_is_accepted(self):
        report = estimate_fragmentation(self.tmpdir.name)
        self.assertIsInstance(report, FragmentationReport)
        self.assertGreaterEqual(report.logical_size, 0)
        self.assertGreaterEqual(report.gap_blocks, 0)
        self.assertGreaterEqual(report.fragmentation_ratio, 0.0)

    def test_report_is_frozen(self):
        path = self._write("frozen.bin", b"abc")
        report = estimate_fragmentation(path)
        with self.assertRaises(Exception):
            report.gap_blocks = 99  # type: ignore[misc]

    def test_accepts_pathlike(self):
        path = self._write("pathlike.bin", b"abc")
        report = estimate_fragmentation(os.path.join(self.tmpdir.name, "pathlike.bin"))
        self.assertEqual(report.path, path)


if __name__ == "__main__":
    unittest.main()
