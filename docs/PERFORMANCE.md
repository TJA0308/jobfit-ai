# Local performance measurements

Run `python scripts/benchmark.py`. A fresh subprocess measures cold imports and
the first multipart request, then ten samples each of single uploads, batches
of ten, and concurrent waves of four uploads. The report retains raw timings,
runtime versions, input hash, actual retrieval backend, and process peak RSS.
It uses fictional short TXT resumes from the posting scenarios.

Recorded lexical run on 2026-11-15:

| Scenario | Median | Observed p95 |
| --- | ---: | ---: |
| Single request | 10.91 ms | 14.10 ms |
| Ten-resume batch request | 120.86 ms | 311.61 ms |
| Four concurrent single requests, whole wave | 112.76 ms | 151.76 ms |

Cold imports plus first request: 2.43 seconds. Whole-worker peak resident memory:
174.8 MiB. See `eval/reports/performance-lexical.json` for exact measurements.

These are local TestClient HTTP-contract measurements, including client
construction and parsing, without an external server/network. The small sample
count makes p95 descriptive only. They do not measure hosted startup, browser
latency, PDF extraction, maximum-size input, saturation, or production capacity.
Concurrent waves include thread/client setup; do not compare them as isolated
core compute throughput.

`--embeddings` explicitly requests the dense backend but disables downloads.
On this environment the optional backend was unavailable: all 46 analyses in
`performance-dense-before.json` used TF-IDF fallback. That report must not be
used to claim dense latency or an inference speedup. Install optional
dependencies and cache the pinned model before collecting real dense results.
Previous committed dense quality reports describe their own recorded runtime,
not the current environment.
