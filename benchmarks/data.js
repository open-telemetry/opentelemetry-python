window.BENCHMARK_DATA = {
  "lastUpdate": 1607890059949,
  "repoUrl": "https://github.com/open-telemetry/opentelemetry-python",
  "entries": {
    "OpenTelemetry Python Benchmarks - Python 3.7 -": [
      {
        "commit": {
          "author": {
            "email": "enowell@amazon.com",
            "name": "(Eliseo) Nathaniel Ruiz Nowell",
            "username": "NathanielRN"
          },
          "committer": {
            "email": "noreply@github.com",
            "name": "GitHub",
            "username": "web-flow"
          },
          "distinct": true,
          "id": "2f1f13f96742284ba3e86f413148e80fe4988686",
          "message": "Use gh-pages to save performance benchmarks results (#1469)",
          "timestamp": "2020-12-13T12:05:16-08:00",
          "tree_id": "5bd658914eea3e94fa977897bf34fa99db03fd90",
          "url": "https://github.com/open-telemetry/opentelemetry-python/commit/2f1f13f96742284ba3e86f413148e80fe4988686"
        },
        "date": 1607890058972,
        "tool": "pytest",
        "benches": [
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_span",
            "value": 26735.75072386535,
            "unit": "iter/sec",
            "range": "stddev: 0.0000012285106160498254",
            "extra": "mean: 37.40310157467776 usec\nrounds: 4509"
          },
          {
            "name": "opentelemetry-sdk/tests/performance/benchmarks/trace/test_benchmark_trace.py::test_simple_start_as_current_span",
            "value": 20632.162258153763,
            "unit": "iter/sec",
            "range": "stddev: 0.0000015211268819551615",
            "extra": "mean: 48.46801743257924 usec\nrounds: 6310"
          }
        ]
      }
    ]
  }
}