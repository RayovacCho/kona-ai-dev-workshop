# 受控崩溃应用

这个小程序从命令行接收编号，通过测试库中的 WhiteBox API 调用
`VMError::controlled_crash(int)`。它只适用于 fastdebug/slowdebug JVM，并且会故意终止
每一个被测 JVM；不要在承载其他工作的进程中运行。

## 构建和运行

先完成 Kona fastdebug 构建，然后使用该构建中的 `javac`、`jar` 和 `java`：

```bash
cd /Users/rayovac9/kona-ai-dev-workshop/apps/controlled-crash
export JAVA_HOME=/Users/rayovac9/TencentKona-25/build/macosx-aarch64-server-fastdebug/images/jdk
export PATH="$JAVA_HOME/bin:$PATH"
./build.sh
./run-crash.sh 14
```

批量测试独立启动子 JVM，避免第一个崩溃中断整个测试：

```bash
./test-crashes.sh
```

日志默认写入 `crash-logs/hs_err_pid*.log`，该目录已被 git 忽略。

| 编号 | 预期直接原因 |
|---:|---|
| 1 | HotSpot `assert` |
| 2 | HotSpot `guarantee` |
| 14 | SIGSEGV / EXCEPTION_ACCESS_VIOLATION |
| 15 | SIGFPE / EXCEPTION_INT_DIVIDE_BY_ZERO |
| 16 | 持有 `ThreadsListHandle` 时 `fatal` |
| 17 | 持有嵌套 `ThreadsListHandle` 时 `fatal` |
| 其他整数 | 带编号的通用 `fatal` |

注意：`-Xbootclasspath/a` 是必要条件。WhiteBox 原生方法只向引导类加载器加载的
`jdk.test.whitebox.WhiteBox` 注册；普通类路径（classpath）会被 VM 拒绝。
