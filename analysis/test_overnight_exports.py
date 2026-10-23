"""Regression tests against the immutable overnight analysis export."""

import importlib.util
import unittest
from pathlib import Path


spec = importlib.util.spec_from_file_location(
    "plot_overnight_exports", Path(__file__).with_name("plot_overnight_exports.py")
)
overnight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(overnight)


class OvernightExportTests(unittest.TestCase):
    def test_strong_scaling_headlines(self):
        actual = {(r["node"], int(r["L"]), int(r["threads"])): r
                  for r in overnight.strong_rows()}
        for key, median, efficiency in (
            (("dine", 24, 32), 352.596, .510),
            (("dine", 32, 32), 350.573, .537),
            (("dine2", 24, 64), 768.923, .341),
            (("dine2", 32, 64), 695.397, .335),
        ):
            self.assertAlmostEqual(float(actual[key]["median"]), median, delta=.001)
            self.assertAlmostEqual(float(actual[key]["parallel_efficiency"]), efficiency, delta=.001)

    def test_matched_weak_scaling(self):
        actual = {(r["node"], int(r["small_L"])): r for r in overnight.weak_rows()}
        self.assertEqual(len(actual), 4)
        for node, retention in (("dine", .56360278), ("dine2", .321)):
            self.assertAlmostEqual(
                float(actual[(node, 24)]["per_thread_throughput_retention"]),
                retention, delta=.001,
            )

    def test_counters_and_axpy(self):
        actual = overnight.counter_rows()
        self.assertEqual(len(actual), 6)
        for node, threads in (("dine", 32), ("dine2", 64)):
            row = next(r for r in actual if r["node"] == node and int(r["threads"]) == threads)
            self.assertEqual(row["counter_mode"], "simultaneous")
            self.assertIn("whole-process", row["scope"])
        axpy = overnight.axpy_l64()
        self.assertAlmostEqual(axpy["dine"], 174.383, delta=.002)
        self.assertAlmostEqual(axpy["dine2"], 350.429, delta=.002)


if __name__ == "__main__":
    unittest.main()
