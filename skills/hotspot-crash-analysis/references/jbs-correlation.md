# JBS correlation rubric

A useful JBS correlation is based on a crash fingerprint, not merely the signal name.
Compare evidence in this order:

1. Exact assertion/fatal message and source file or function.
2. Problematic-frame symbol and nearby native frames.
3. Triggering Java frame or workload and VM subsystem (compiler, GC, runtime, JNI).
4. OS, CPU architecture, GC, VM flags, and debug/release build.
5. Affected and fixed versions, including whether the vendor build contains the fix.

Label confidence as:

- `high`: distinctive message/frame and trigger match; version/platform are compatible.
- `medium`: subsystem and several frames match, but reproduction or version evidence is incomplete.
- `low`: keyword or signal similarity only. Never describe this as the known cause.

Check issue status and resolution. `Duplicate` requires following the parent issue;
`Not an Issue` is context, not a fix. A listed fix version does not prove a vendor build
contains the patch; verify its source revision or reproduce on a build known to include
the fix.

If no high/medium candidate exists, report “no credible match found” and preserve the
generated query URL. Recommend collecting the full log, exact JDK build, reproducer,
core/minidump, native-library versions, and symbolized stack before filing a new issue.
