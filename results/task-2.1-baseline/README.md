# Task 2.1 formal baseline artifacts

These files are the auditable source for the figures in the task 2.1 report:

- `jmh-result.json`: JMH 1.37 output from the clean Kona release build, including GC profiler metrics;
- `environment.txt`: sanitized environment and exact Kona commit metadata;
- `SHA256SUMS`: integrity manifest checked by `make check` and CI.

They were produced with:

```bash
export RESULT_DIR=results/reproductions/task-2.1-YYYYMMDD
make jmh-baseline KONA_SRC=/path/to/clean/TencentKona-25
make capture-environment KONA_SRC=/path/to/clean/TencentKona-25
```

SHA-256 checksums are stored in `SHA256SUMS`; run `make check-results` to verify the
checksums, environment metadata, nine-case result matrix, and GC allocation metrics.
