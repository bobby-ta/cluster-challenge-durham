"""Theoretical node peaks. Fill in from the spec sheet and the recon job, and cite sources
in the report. Each value is per node.

Compute peak  = sockets * cores * GHz * flops/cycle/core
Memory peak   = sockets * channels * MT/s * 8 bytes
"""

NODES = {
    "dine": dict(
        cpu="2x AMD EPYC 7302 (Zen 2, 16c)",
        sockets=2, cores=16,
        ghz_base=3.0, ghz_boost=3.3,       # AMD spec sheet; check what recon/cpupower reports
        dp_flops_cycle=16,                 # 2x 256-bit FMA pipes: 2 * 4 DP * 2
        sp_flops_cycle=32,
        channels=8, mts=3200,              # TODO: confirm DIMM speed (DDR4-3200 is the max for Rome)
    ),
    "dine2": dict(
        cpu="TODO from recon",
        sockets=None, cores=None, ghz_base=None, ghz_boost=None,
        dp_flops_cycle=None, sp_flops_cycle=None, channels=None, mts=None,
    ),
}


def peaks(node, clock="base"):
    n = NODES[node]
    if n["cores"] is None:
        return None
    ghz = n[f"ghz_{clock}"]
    c = n["sockets"] * n["cores"] * ghz
    return dict(
        gflops_dp=c * n["dp_flops_cycle"],
        gflops_sp=c * n["sp_flops_cycle"],
        gbs=n["sockets"] * n["channels"] * n["mts"] * 8 / 1000,
    )


if __name__ == "__main__":
    for node in NODES:
        print(node, peaks(node), peaks(node, "boost"))
