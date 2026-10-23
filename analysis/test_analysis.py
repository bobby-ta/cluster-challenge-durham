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

    def make_grid_run(self, job="123_8", threads=8, experiment="grid", host="b103"):
        run = self.results / "dine" / experiment / job
        run.mkdir(parents=True)
        (run / "meta.txt").write_text(
            f"git=abc123\nhost={host}\nargs=T={threads} MAX_L=32 PERFCTR= NUMACTL=\n"
            "--- env\nGRID_CONFIG=cpu-avx2\nOMP_PROC_BIND=spread\nOMP_PLACES=cores\n"
            "GRID_ENV_ROOT=/fixture/build\n"
        )
        (run / "build-flags.txt").write_text("CXX=g++\nCXXFLAGS=-O3 -mavx2\n")
        (run / "ldd.txt").write_text("libgomp.so => /fixture/libgomp.so (0x1234)\n")
        return run

    def grid_json(self):
        return json.dumps({"flops": [{"L": 24, "Precision": "FP32", "Gflops_dwf4": 123.0}]})

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
            axpy = list(csv.DictReader(f))
        self.assertEqual(len(axpy), 1)
        self.assertAlmostEqual(float(axpy[0]["GBps"]), 105 * 2**30 / 1e9)
        self.assertEqual(float(axpy[0]["Grid_raw_GiBps"]), 105)
        self.assertEqual(axpy[0]["bandwidth_unit"], "GB/s")

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

    def test_later_success_cannot_hide_failed_group(self):
        run = self.make_grid_run()
        for group in ("MEM", "FLOPS_SP"):
            (run / f"result-{group}.json").write_text(self.grid_json())
            (run / f"perfctr-{group}.csv").write_text(
                "Runtime (RDTSC) [s],10\nSP [MFLOP/s],1000\nMemory bandwidth [MBytes/s],500\n"
            )
        (self.results / "runlog.csv").write_text(
            "job,node,experiment,status,note\n"
            "123_8,dine,grid,fail,perfctr MEM T=8 exit 124\n"
            "123_8,dine,grid,ok,perfctr FLOPS_SP T=8 10s\n"
        )
        with patch.object(collect, "RESULTS", self.results), patch.object(collect, "OUT", self.out):
            self.assertEqual(list(collect.runs("*", "grid*")), [])
            collect.grid()
            collect.perfctr()
        with (self.out / "grid.csv").open() as f:
            self.assertEqual({r["file"] for r in csv.DictReader(f)}, {"result-FLOPS_SP.json"})
        with (self.out / "perfctr.csv").open() as f:
            self.assertEqual({r["group"] for r in csv.DictReader(f)}, {"FLOPS_SP"})

    def test_provenance_separates_build_host_and_affinity_but_not_aslr(self):
        runs = [self.make_grid_run(job=f"100_{t}", threads=t) for t in (1, 2, 4, 8, 16)]
        (runs[1] / "ldd.txt").write_text("libgomp.so => /fixture/libgomp.so (0xabcd)\n")
        (runs[2] / "build-flags.txt").write_text("CXX=clang++\nCXXFLAGS=-O3 -mavx2\n")
        (runs[3] / "meta.txt").write_text((runs[3] / "meta.txt").read_text().replace("host=b103", "host=b104"))
        (runs[4] / "meta.txt").write_text((runs[4] / "meta.txt").read_text().replace("OMP_PLACES=cores", "OMP_PLACES={0},{2}"))
        metadata = [collect.grid_metadata(run) for run in runs]
        self.assertEqual(metadata[0]["provenance_id"], metadata[1]["provenance_id"])
        self.assertEqual(len({r["provenance_id"] for r in metadata}), 4)
        self.assertEqual(metadata[0]["host"], "b103")
        self.assertEqual(metadata[4]["omp_places"], "{0},{2}")

    def test_missing_build_metadata_isolates_unlogged_legacy_runs(self):
        runs = [self.make_grid_run(job=job) for job in ("100_8", "101_8")]
        for run in runs:
            (run / "build-flags.txt").unlink()
        self.assertNotEqual(*(collect.grid_metadata(run)["provenance_id"] for run in runs))
        with patch.object(collect, "RESULTS", self.results):
            self.assertEqual(len(list(collect.runs("*", "grid*"))), 2)

    def test_overnight_records_are_left_to_the_campaign_adapter(self):
        run = self.make_grid_run(experiment="grid-overnight-campaign")
        (run / "record.json").write_text('{"status":"ok","mode":"scaling"}')
        (run / "result.json").write_text(self.grid_json())
        with patch.object(collect, "RESULTS", self.results), patch.object(collect, "OUT", self.out):
            collect.grid()
        self.assertFalse((self.out / "grid.csv").exists())

    def test_counter_runtime_stat_uses_max_and_unlogged_rows_are_not_plot_eligible(self):
        run = self.make_grid_run()
        (run / "result-FLOPS_SP.json").write_text(self.grid_json())
        (run / "perfctr-FLOPS_SP.csv").write_text(
            "Runtime (RDTSC) [s],10,11\nRuntime (RDTSC) [s] STAT,21,10,11,10.5\n"
            "SP [MFLOP/s],1000,2000\nSP [MFLOP/s] STAT,3000,1000,2000,1500\n"
        )
        with patch.object(collect, "RESULTS", self.results), patch.object(collect, "OUT", self.out):
            collect.perfctr()
        with (self.out / "perfctr.csv").open() as f:
            rows = list(csv.DictReader(f))
        values = {r["metric"]: float(r["value"]) for r in rows}
        self.assertEqual(values["Runtime (RDTSC) [s]"], 11)
        self.assertEqual(values["SP [MFLOP/s]"], 3000)
        self.assertTrue(all(r["runtime_s"] == "11.0" for r in rows))
        self.assertTrue(all(r["plot_eligible"] == "False" for r in rows))

    def test_nonfinite_and_nonpositive_grid_metrics_are_not_collected(self):
        run = self.make_grid_run()
        (run / "result.json").write_text(json.dumps({"flops": [
            {"L": 24, "Precision": "FP32", "Gflops_dwf4": float("nan")},
            {"L": 32, "Precision": "FP32", "Gflops_dwf4": -1},
        ]}))
        with patch.object(collect, "RESULTS", self.results), patch.object(collect, "OUT", self.out):
            collect.grid()
        self.assertFalse((self.out / "grid.csv").exists())


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
        df["file"] = "result.json"
        df["provenance_id"] = "fixture-build-host-runtime"
        with tempfile.TemporaryDirectory() as tmp, patch.object(plots, "FIGS", Path(tmp)):
            plots.grid_plots(df)
            for name in ("grid_scaling_dine", "grid_weak_scaling_dine", "grid_vs_L"):
                self.assertTrue((Path(tmp) / f"{name}.pdf").stat().st_size > 0)
                self.assertTrue((Path(tmp) / f"{name}.png").stat().st_size > 0)

    def test_tagged_scaling_does_not_pool_other_builds_or_instrumented_runs(self):
        import pandas as pd
        df = pd.DataFrame([
            dict(node="dine", experiment="grid-cover-scaling", precision="FP32", L=24,
                 threads=t, Gflops_dwf4=value, provenance_id=build, file=file)
            for t, value, build, file in [(1, 10, "gcc-host1", "result.json"),
                                           (8, 80, "gcc-host1", "result.json"),
                                           (8, 160, "clang-host1", "result.json"),
                                           (8, 9999, "gcc-host1", "result-MEM.json")]
        ])
        with tempfile.TemporaryDirectory() as tmp, patch.object(plots, "FIGS", Path(tmp)), \
                patch.object(plots, "band", wraps=plots.band) as band, \
                patch.object(plots, "save", side_effect=lambda fig, name: plots.plt.close(fig)):
            plots.grid_plots(df)
        self.assertTrue(band.call_args_list)
        for call in band.call_args_list:
            data = call.args[1]
            self.assertEqual(data.provenance_id.nunique(), 1)
            self.assertLess(data.Gflops_dwf4.max(), 9999)

    def test_grid_weak_pairs_cannot_cross_provenance_and_stale_figures_are_removed(self):
        import pandas as pd
        df = pd.DataFrame([
            dict(node="dine", experiment="grid-cover-scaling", precision="FP32", file="result.json",
                 L=24, threads=8, Gflops_dwf4=80, provenance_id="gcc"),
            dict(node="dine", experiment="grid-cover-scaling", precision="FP32", file="result.json",
                 L=32, threads=24, Gflops_dwf4=230, provenance_id="clang"),
        ])
        with tempfile.TemporaryDirectory() as tmp, patch.object(plots, "FIGS", Path(tmp)), \
                patch.object(plots, "save", side_effect=lambda fig, name: plots.plt.close(fig)) as save:
            for name in ("grid_weak_scaling_dine", "grid_scaling_dine2", "grid_vs_L"):
                (Path(tmp) / f"{name}.pdf").write_bytes(b"stale")
            plots.grid_plots(df)
            self.assertNotIn("grid_weak_scaling_dine", [c.args[1] for c in save.call_args_list])
            self.assertEqual(list(Path(tmp).iterdir()), [])
            plots.grid_plots(None)

    def counter_frame(self, pair_ids=("paired", "paired"), builds=("gcc", "gcc"), times=(100, 102)):
        import pandas as pd
        return pd.DataFrame([
            dict(node="dine", threads=8, provenance_id=build, counter_pair_id=pair,
                 measurement_id=source, scope="whole_process", plot_eligible=True,
                 metric=metric, value=value, runtime_s=runtime, workload_fingerprint="same-cases")
            for pair, build, runtime, source, metric, value in [
                (pair_ids[0], builds[0], times[0], "job1/FLOPS_SP", "SP [MFLOP/s]", 20000),
                (pair_ids[1], builds[1], times[1], "job2/MEM", "Memory bandwidth [MBytes/s]", 10000),
            ]
        ])

    def test_counter_pairs_require_matching_identity_and_runtime(self):
        points = plots.counter_points(self.counter_frame())
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0]["counter_mode"], "separate_passes")
        self.assertEqual(points[0]["SP_GFLOPs"], 20)
        self.assertEqual(points[0]["DRAM_GBps"], 10)
        self.assertEqual(points[0]["approximate_SP_FLOP_per_byte"], 2)
        for frame in [self.counter_frame(pair_ids=("run:job1", "run:job2")),
                      self.counter_frame(builds=("gcc", "clang")),
                      self.counter_frame(times=(100, 200))]:
            self.assertEqual(plots.counter_points(frame), [])

    def test_counter_pairs_reject_ambiguous_repeats_and_unverified_output(self):
        import pandas as pd
        frame = self.counter_frame()
        additional = frame.iloc[[0]].copy()
        additional["measurement_id"] = "job3/FLOPS_SP"
        self.assertEqual(plots.counter_points(pd.concat([frame, additional])), [])
        self.assertEqual(plots.counter_points(pd.concat([frame, frame])), [])
        frame.loc[0, "plot_eligible"] = False
        self.assertEqual(plots.counter_points(frame), [])
        self.assertEqual(plots.counter_points(frame.drop(columns="provenance_id")), [])

    def test_counter_simultaneous_metrics_use_the_same_pass(self):
        frame = self.counter_frame(times=(100, 100))
        frame["measurement_id"] = "one-job/MEM_SP"
        points = plots.counter_points(frame)
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0]["counter_mode"], "simultaneous")
        self.assertEqual(points[0]["runtime_relative_difference"], 0)

    def test_actual_workload_cases_must_match_between_counter_passes(self):
        base = {"flops": [{"L": 24, "Precision": "FP32", "Gflops_dwf4": 123}],
                "axpy": [{"L": 16, "size_MB": 12, "GBps": 50}]}
        other_speed = json.loads(json.dumps(base))
        other_speed["flops"][0]["Gflops_dwf4"] = 999
        self.assertEqual(collect.workload_fingerprint(base), collect.workload_fingerprint(other_speed))
        other_cases = json.loads(json.dumps(base))
        other_cases["axpy"][0]["L"] = 32
        self.assertNotEqual(collect.workload_fingerprint(base), collect.workload_fingerprint(other_cases))
        frame = self.counter_frame()
        frame.loc[1, "workload_fingerprint"] = "different-cases"
        self.assertEqual(plots.counter_points(frame), [])


if __name__ == "__main__":
    unittest.main()
