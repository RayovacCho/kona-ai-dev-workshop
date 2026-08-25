# HotSpot error log test fixtures

These files are reduced excerpts of `hs_err_pid*.log` files produced by the
controlled-crash application on macOS/AArch64. They retain the header, summary,
and relevant stack frames used by the parser while omitting host-specific and
unrelated diagnostic sections.

The checked-in fixtures make the test suite self-contained. Full crash logs
generated under `apps/controlled-crash/crash-logs/` remain ignored because they
are large, host-specific runtime artifacts.
