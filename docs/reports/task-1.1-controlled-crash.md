# 任务 1.1 报告：WhiteBox controlledCrash

## 实现摘要

在 Kona JDK 25 的测试 WhiteBox Java 类中新增 `controlledCrash(int)`，并在 HotSpot
WhiteBox JNI 表中新增仅限 `ASSERT` 构建的入口。入口直接复用已有
`VMError::controlled_crash`，未新增崩溃机制。配套应用负责参数校验、危险提示、统一
JVM 参数与错误日志位置，批量脚本保证不同编号在独立进程中执行。

## 改动文件

- Kona 源库：`src/hotspot/share/prims/whitebox.cpp`
- Kona 源库：`test/lib/jdk/test/whitebox/WhiteBox.java`
- Kona 源库：`test/hotspot/jtreg/runtime/whitebox/ControlledCrashTest.java`
- 作业库：`apps/controlled-crash/`

JDK 侧改动以独立 Kona fork 的
[实现提交](https://github.com/RayovacCho/TencentKona-25/commit/3dfb920595202df2dfa5b9f5b6c3b124cf32aabf)
为准，本仓库不重复保存补丁文件。

## 验证记录

2026-08-22 在 macOS AArch64 上完成 fastdebug `images` 构建，并运行全部用例。HotSpot
最终以 SIGABRT（shell 显示 `Abort trap: 6`）结束错误处理流程；表中的“直接原因”取自
各自 `hs_err` 的首段，而不是把最终 SIGABRT 当作所有用例的原始故障。

| 编号 | 预期 | 实测退出码/信号 | hs_err 关键行 | 状态 |
|---:|---|---|---|---|
| 1 | assert | 134 / SIGABRT (6) | `assert(how == 0) failed: test assert` | 通过 |
| 2 | guarantee | 134 / SIGABRT (6) | `guarantee(how == 0) failed: test guarantee` | 通过 |
| 14 | SIGSEGV | 134 / SIGABRT (6) | `SIGSEGV`；问题帧为 `VMError::controlled_crash` | 通过 |
| 15 | SIGFPE | 134 / SIGABRT (6) | `SIGFPE`；栈帧为 `__pthread_kill`（macOS 实现） | 通过 |
| 16 | fatal + 活动 handle | 134 / SIGABRT (6) | `Force crash with an active ThreadsListHandle.` | 通过 |
| 17 | fatal + 嵌套 handle | 134 / SIGABRT (6) | `Force crash with a nested ThreadsListHandle.` | 通过 |
| 99 | 通用 fatal | 134 / SIGABRT (6) | `Crashing with number 99` | 通过 |

复现命令：

```bash
export WORKSHOP_ROOT=/path/to/kona-ai-dev-workshop
export KONA_SRC=/path/to/TencentKona-25
export JAVA_HOME="$KONA_SRC/build/macosx-aarch64-server-fastdebug/images/jdk"
export PATH="$JAVA_HOME/bin:$PATH"
cd "$WORKSHOP_ROOT/apps/controlled-crash"
./build.sh
./test-crashes.sh
```

WhiteBox 接口的 jtreg 回归测试：

```bash
cd "$KONA_SRC"
make test CONF=macosx-aarch64-server-fastdebug \
    TEST=test/hotspot/jtreg/runtime/whitebox/ControlledCrashTest.java
```

## 结论

fastdebug 构建、WhiteBox Java/JNI 调用链、参数化应用和七类崩溃测试均已完成。每个
用例均产生独立 `hs_err`，其错误类别与 `VMError::controlled_crash` 的实现一致。完整日志
保留在本地 `apps/controlled-crash/crash-logs/`，按仓库约定不提交。
