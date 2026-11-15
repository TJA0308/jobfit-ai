"""Local in-process HTTP benchmark. No production/network-load claims.

Run from a fresh worker process; model downloads are disabled even with --embeddings.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parent.parent


def peak_rss_bytes():
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in (
                    "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                    "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage",
                    "PagefileUsage", "PeakPagefileUsage")]
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return counters.PeakWorkingSetSize
    import resource
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak if sys.platform == "darwin" else peak * 1024


def worker(args):
    started = perf_counter()
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["JOBFIT_ENABLE_EMBEDDINGS"] = "1" if args.embeddings else "0"
    sys.path.insert(0, str(ROOT))
    from fastapi.testclient import TestClient
    from api_server import app
    from jobfit_ai.reproducibility import runtime_manifest

    dataset_path = ROOT / "eval/current_openings.json"
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    jobs = dataset["jobs"]
    backends = Counter()

    def request(batch=False, index=0):
        job = jobs[index % len(jobs)]
        resume = job["profiles"][0]["resume"].encode()
        field = "resume_files" if batch else "resume_file"
        files = [(field, (f"sample-{i}.txt", resume, "text/plain")) for i in range(10 if batch else 1)]
        # A client per task avoids sharing client session state across threads.
        with TestClient(app) as client:
            response = client.post("/match/batch" if batch else "/match",
                data={"job_description": job["job_description"], "use_embeddings": str(args.embeddings).lower()},
                files=files)
        if response.status_code != 200:
            raise RuntimeError(f"Benchmark request failed: HTTP {response.status_code}")
        analyses = response.json()["analyses"] if batch else [response.json()]
        return Counter(item["evidence_backend"] for item in analyses)

    backends.update(request())
    cold_ms = (perf_counter() - started) * 1000
    scenarios = {}
    for name in ("single", "batch_10", "concurrent_single"):
        durations = []
        for iteration in range(args.repeats):
            start = perf_counter()
            if name == "concurrent_single":
                with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
                    results = list(pool.map(request, [False] * args.concurrency, range(args.concurrency)))
                for result in results:
                    backends.update(result)
            else:
                backends.update(request(name == "batch_10", iteration))
            durations.append((perf_counter() - start) * 1000)
        scenarios[name] = {"runs": len(durations), "p50_ms": round(statistics.median(durations), 2),
            "p95_ms": round(sorted(durations)[math.ceil(.95 * len(durations)) - 1], 2),
            "raw_ms": [round(value, 2) for value in durations],
            "requests_per_run": args.concurrency if name == "concurrent_single" else 1}
    import hashlib
    return {"runtime": runtime_manifest(), "dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "mode": "dense_requested_offline" if args.embeddings else "lexical",
        "cold_import_and_first_request_ms": round(cold_ms, 2),
        "process_peak_rss_bytes": peak_rss_bytes(), "actual_evidence_backends": dict(backends),
        "scenarios": scenarios,
        "limits": "Synthetic short TXT resumes; local TestClient HTTP contracts, not external network. Cold timing includes imports and first request, excludes interpreter spawn. Peak RSS is whole worker high-water mark. Batch is ten resumes/request; concurrent latency is wall time for a wave. Small run counts and p95 are descriptive, not an SLO."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--embeddings", action="store_true")
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--json-output", type=Path, default=ROOT / "eval/reports/performance-lexical.json")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not 3 <= args.repeats <= 100 or not 1 <= args.concurrency <= 16:
        parser.error("Use 3–100 repetitions and 1–16 concurrent requests.")
    if args.worker:
        print(json.dumps(worker(args)))
        return
    command = [sys.executable, str(Path(__file__).resolve()), "--worker", "--repeats", str(args.repeats),
               "--concurrency", str(args.concurrency)]
    if args.embeddings:
        command.append("--embeddings")
    process = subprocess.run(command, capture_output=True, text=True, check=True, cwd=ROOT)
    report = json.loads(process.stdout)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "runtime"}, indent=2))


if __name__ == "__main__":
    main()
