#!/usr/bin/env python3
"""Offline smoke tests. Run: python3 -m unittest discover -s analysis -p 'test_*.py'"""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import collect
import plots


class CollectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.results = self.root / "results"
        self.out = self.root / "data"

    def make_grid_run(self, job="123_8", threads=8):
        run = self.results / "dine" / "grid" / job
        run.mkdir(parents=True)
        (run / "meta.txt").write_text(
            f"git=abc123\nargs=T={threads} MAX_L=32 PERFCTR= NUMACTL=\n"
            "--- env\nGRID_CONFIG=cpu-avx2\nOMP_PROC_BIND=spread\n"
        )
        return run

    def test_grid_deduplicates_flops_and_results_sections(self):
        run = self.make_grid_run()
        by_l = [
            {"L": 24, "Precision": "FP32", "Gflops_dwf4": 123.0},
            {"L": 32, "Precision": "FP32", "Gflops_dwf4": 112.0},
        ]
        (run / "result.json").write_text(json.dumps({
            "flops": by_l,
            "results": by_l,
            "axpy": [{"L": 24, "GBps": 105.0, "GFlops": 9.0, "size_MB": 96}],
        }))
        with patch.object(collect, "RESULTS", self.results), patch.object(collect, "OUT", self.out):
            collect.grid()
        with (self.out / "grid.csv").open() as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 2)
        self.assertEqual({int(r["L"]) for r in rows}, {24, 32})
        self.assertTrue(all(r["precision"] == "FP32" for r in rows))
        self.assertTrue(all(r["threads"] == "8" for r in rows))
        self.assertEqual(rows[0]["config"], "cpu-avx2")
        self.assertEqual(rows[0]["bind"], "spread")
        with (self.out / "grid_axpy.csv").open() as f:
            self.assertEqual(len(list(csv.DictReader(f))), 1)

    def test_bad_meta_or_partial_json_does_not_crash_collection(self):
        run = self.make_grid_run()
        (run / "result.json").write_text("{incomplete")
        missing_meta = self.results / "dine2" / "grid" / "456_16"
        missing_meta.mkdir(parents=True)
        (missing_meta / "result.json").write_text("{}")
        with patch.object(collect, "RESULTS", self.results), patch.object(collect, "OUT", self.out):
            collect.grid()
        self.assertFalse((self.out / "grid.csv").exists())

    def test_empty_input_removes_stale_generated_csv(self):
        self.out.mkdir(parents=True)
        (self.out / "grid.csv").write_text("old,stale\n1,2\n")
        with patch.object(collect, "OUT", self.out):
            collect.write("grid.csv", [])
        self.assertFalse((self.out / "grid.csv").exists())


class PlotTests(unittest.TestCase):
    def test_matched_weak_scaling_uses_similar_sites_per_thread(self):
        import pandas as pd
        df = pd.DataFrame([
            {"L": 24, "threads": 8, "Gflops_dwf4": 80.0},
            {"L": 32, "threads": 24, "Gflops_dwf4": 230.0},
            {"L": 32, "threads": 32, "Gflops_dwf4": 300.0},
        ])
        pairs = plots.weak_pairs(df, "Gflops_dwf4")
        self.assertEqual(len(pairs), 1)
        t1, t2, ratio, mismatch = pairs[0]
        self.assertEqual((t1, t2), (8, 24))
        self.assertAlmostEqual(ratio, 230 / 24 / (80 / 8))
        self.assertLess(mismatch, 0.10)

    def test_grid_plots_include_strong_and_weak_scaling(self):
        import pandas as pd
        df = pd.DataFrame([
            {"node": "dine", "experiment": "grid", "precision": "FP32", "L": 24,
             "threads": 1, "Gflops_dwf4": 12.0},
            {"node": "dine", "experiment": "grid", "precision": "FP32", "L": 32,
             "threads": 1, "Gflops_dwf4": 10.0},
            {"node": "dine", "experiment": "grid", "precision": "FP32", "L": 24,
             "threads": 8, "Gflops_dwf4": 80.0},
            {"node": "dine", "experiment": "grid", "precision": "FP32", "L": 32,
             "threads": 24, "Gflops_dwf4": 230.0},
            # This unrelated tuning pass must not alter default plots.
            {"node": "dine", "experiment": "grid-tune", "precision": "FP32", "L": 24,
             "threads": 8, "Gflops_dwf4": 10000.0},
            # Nor may FP64 be combined with Grid's required FP32 measurements.
            {"node": "dine", "experiment": "grid", "precision": "FP64", "L": 24,
             "threads": 8, "Gflops_dwf4": 9000.0},
        ])
        with tempfile.TemporaryDirectory() as tmp, patch.object(plots, "FIGS", Path(tmp)):
            plots.grid_plots(df)
            for name in ("grid_scaling_dine", "grid_weak_scaling_dine", "grid_vs_L"):
                self.assertTrue((Path(tmp) / f"{name}.pdf").stat().st_size > 0)
                self.assertTrue((Path(tmp) / f"{name}.png").stat().st_size > 0)


if __name__ == "__main__":
    unittest.main()
