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

    def test_likwid_excludes_bad_jobs_before_combining_reruns(self):
        jobs = [("dine", "sizes", "12200764"),
                ("dine2", "threads", "12203200"), ("dine2", "threads", "12203201"),
                ("dine2", "sizes", "12203202"), ("dine2", "sizes", "99900001"),
                ("dine2", "flops", "99900002")]
        for node, mode, job in jobs:
            run = self.results / node / f"likwid-{mode}" / job
            run.mkdir(parents=True)
            (run / "out.csv").write_text(
                "kernel,placement,threads,size,rep,MBps,MFlops\n"
                "triad_avx,all,64,1MB,1,1000,100\n"
            )
        with patch.object(collect, "RESULTS", self.results), patch.object(collect, "OUT", self.out):
            collect.likwid()
        with (self.out / "likwid.csv").open() as f:
            rows = list(csv.DictReader(f))
        self.assertEqual({r["job"] for r in rows}, {"99900001", "99900002"})

    def test_runlog_failure_excludes_grid_and_counter_outputs(self):
        run = self.make_grid_run()
        (run / "result.json").write_text(json.dumps({
            "flops": [{"L": 24, "Precision": "FP32", "Gflops_dwf4": 123.0}],
            "axpy": [{"L": 24, "GBps": 105.0}],
        }))
        (run / "perfctr-MEM.csv").write_text("Memory bandwidth [MBytes/s],1000\n")
        (self.results / "runlog.csv").write_text(
            "job,node,experiment,status,note\n"
            '123_8,dine,grid,warn,"perfctr failed, incomplete measurement"\n'
        )
        with patch.object(collect, "RESULTS", self.results), patch.object(collect, "OUT", self.out):
            collect.grid()
            collect.perfctr()
        self.assertFalse((self.out / "grid.csv").exists())
        self.assertFalse((self.out / "grid_axpy.csv").exists())
        self.assertFalse((self.out / "perfctr.csv").exists())

    def test_runlog_failure_keeps_ok_and_unlogged_likwid_runs(self):
        for job in ("100", "101", "102"):
            run = self.results / "dine2" / "likwid-bw" / job
            run.mkdir(parents=True)
            (run / "out.csv").write_text(
                "kernel,placement,threads,size,rep,MBps,MFlops\n"
                "triad_avx,compact,64,2GB,1,1000,100\n"
            )
        (self.results / "runlog.csv").write_text(
            "job,node,experiment,status,note\n"
            "100,dine2,likwid-bw,TIMEOUT,time limit\n"
            "101,dine2,likwid-bw,ok,complete\n"
        )
        with patch.object(collect, "RESULTS", self.results), patch.object(collect, "OUT", self.out):
            collect.likwid()
        with (self.out / "likwid.csv").open() as f:
            self.assertEqual({r["job"] for r in csv.DictReader(f)}, {"101", "102"})


class PlotTests(unittest.TestCase):
    def test_roofline_uses_fixed_flops_and_bw_instead_of_legacy_memory(self):
        import numpy as np
        import pandas as pd
        df = pd.DataFrame([
            dict(node="dine2", mode=mode, job=job, kernel=kernel, threads=64,
                 placement="compact", MBps=mbps, MFlops=mflops)
            for mode, job, kernel, mbps, mflops in [
                ("threads", "12203200", "peakflops_sp_avx_fma", 1e9, 1e9),
                ("threads", "12203201", "triad_avx", 1e9, 1e9),
                ("flops", "99900002", "peakflops_sp_avx512_fma", 1000, 100000),
                ("flops", "99900002", "peakflops_avx512_fma", 1000, 50000),
                ("bw", "99900003", "triad_avx", 80000, 1000),
            ]
        ])
        curves = {}

        def capture(fig, name):
            curves[name] = [(line.get_label(), line.get_xdata(), line.get_ydata())
                            for line in fig.axes[0].lines]
            plots.plt.close(fig)

        with tempfile.TemporaryDirectory() as tmp, patch.object(plots, "FIGS", Path(tmp)), \
                patch.object(plots, "save", side_effect=capture):
            plots.roofline(df, None)
        self.assertIn("roofline_dine2", curves)
        sp, dp = curves["roofline_dine2"]
        np.testing.assert_allclose(sp[2], np.minimum(100.0, 80.0 * sp[1]))
        np.testing.assert_allclose(dp[2], np.minimum(50.0, 80.0 * dp[1]))

    def test_missing_valid_likwid_data_removes_stale_figures(self):
        import pandas as pd
        empty = pd.DataFrame(columns=["node", "mode", "job", "kernel", "placement",
                                      "threads", "MBps", "MFlops"])
        with tempfile.TemporaryDirectory() as tmp, patch.object(plots, "FIGS", Path(tmp)):
            names = [f"{kind}_{node}" for node in ("dine", "dine2")
                     for kind in ("likwid_bw_threads", "likwid_flops_threads",
                                  "likwid_bw_sizes", "roofline")]
            for name in names:
                for ext in ("pdf", "png"):
                    (Path(tmp) / f"{name}.{ext}").write_bytes(b"stale")
            plots.likwid_plots(empty)
            plots.roofline(empty, None)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_legacy_flops_reuse_is_limited_to_validated_dine_compute_rows(self):
        import pandas as pd
        rows = [
            ("dine", "threads", "12200761", "peakflops_avx_fma", 32),
            ("dine", "threads", "12200761", "peakflops_sse", 32),
            ("dine", "threads", "12200761", "load_avx", 32),
            ("dine", "threads", "12200761", "peakflops_avx_fma", 3),
            ("dine2", "threads", "12203200", "peakflops_avx512_fma", 64),
            ("dine2", "flops", "99900002", "peakflops_avx512_fma", 64),
        ]
        df = pd.DataFrame([
            dict(node=node, mode=mode, job=job, kernel=kernel, threads=threads,
                 placement="compact", size="16kB", rep=1, MBps=1000.0, MFlops=100000.0)
            for node, mode, job, kernel, threads in rows
        ])
        with tempfile.TemporaryDirectory() as tmp, patch.object(plots, "FIGS", Path(tmp)), \
                patch.object(plots, "band", wraps=plots.band) as band, \
                patch.object(plots, "save", side_effect=lambda fig, name: plots.plt.close(fig)):
            plots.likwid_plots(df)
        used = pd.concat([call.args[1] for call in band.call_args_list
                          if call.args[3] == "GFlops"])
        self.assertEqual(
            set(zip(used.node, used.job, used.kernel, used.threads)),
            {("dine", "12200761", "peakflops_avx_fma", 16),
             ("dine2", "99900002", "peakflops_avx512_fma", 64)},
        )

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
