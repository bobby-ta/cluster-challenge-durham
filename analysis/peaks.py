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
        # recon 12198164 likwid-topology: L3 groups (0 32 1 33) ... = 2 cores per 16 MB L3
        l1_kb=32, l2_kb=512, l3_kb=16384, l3_cores=2,
    ),
    "dine2": dict(
        # recon 12202559: 2 sockets, 32 physical cores/socket, AVX-512.
        # Vendor upper bounds: https://www.intel.com/content/www/us/en/products/sku/231737/
        # intel-xeon-gold-6430-processor-60m-cache-2-10-ghz/specifications.html
        # DDR5-4400 is the supported MAX, not verified installed DIMM speed.
        cpu="2x Intel Xeon Gold 6430 (Sapphire Rapids, 32c)",
        sockets=2, cores=32, ghz_base=2.1, ghz_boost=3.4,
        dp_flops_cycle=32,             # 2x 512-bit FMA: 2 * 8 DP * 2
        sp_flops_cycle=64,
        channels=8, mts=4400,          # upper bound until DIMM speed is verified
        # recon 12202559 likwid-topology: 48 kB L1d + 2 MB L2 per core, 60 MB L3 per socket
        l1_kb=48, l2_kb=2048, l3_kb=61440, l3_cores=32,
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
