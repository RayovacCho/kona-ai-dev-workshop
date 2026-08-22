---
name: hotspot-crash-analysis
description: Analyze HotSpot hs_err_pid error logs, identify the immediate JVM crash cause, correlate credible OpenJDK JBS issues, and recommend mitigations. Use for JVM fatal errors, native signals, internal errors, and crash-log triage; not for ordinary Java exception stack traces.
---

# HotSpot crash analysis

Use the `hotspot-crash-analyzer` MCP tools when available. Start with
`analyze_hotspot_crash`; if network lookup is unavailable, use its parsed result and
give the generated JBS search URL so the user can continue manually.

Treat the log as primary evidence. Establish the direct cause from the fatal-error
header, error message, problematic frame, current thread, and top native/Java frames.
Do not mistake the signal used by HotSpot's fatal-error termination path for the
original failure recorded in the header.

Before claiming a JBS match, read [references/jbs-correlation.md](references/jbs-correlation.md).
Call a search result a candidate until `get_jbs_issue` has supplied its description and
its signature, affected build/platform, trigger, and stack context have been compared
with the log. Include JBS key, title, status, affected
and fixed versions, URL, and a confidence level. It is valid—and preferable—to conclude
that no credible known issue was found.

Recognize intentional crash tests. `VMError::controlled_crash`,
`WhiteBox.controlledCrash`, `-XX:+WhiteBoxAPI`, and messages such as `test assert` or
`Crashing with number` are strong evidence that the crash was deliberately injected.
In that case, state that it is not evidence of a product defect and do not present
generic signal-related JBS hits as matches.
When historical context is requested, search exact mechanism or test symbols such as
`VMError::controlled_crash` or `ThreadsListHandleInErrorHandlingTest`; label those
issues as mechanism-related context unless the observed output demonstrates the same
failure described by the issue.

Return a concise report containing:

1. verdict and confidence;
2. direct cause with quoted log evidence;
3. failure path and relevant environment;
4. JBS assessment, including rejected false positives when useful;
5. prioritized remediation or next diagnostic actions.

Keep fact, inference, and recommendation visibly distinct. Redact credentials and
sensitive command-line values when reproducing log excerpts.
