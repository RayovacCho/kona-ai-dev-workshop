# 任务 1.1 规划：运行期受控触发 JVM 崩溃

## 目标与验收条件

1. Kona JDK 25 能完成 fastdebug 构建。
2. `WhiteBox.controlledCrash(int)` 能从 Java 到达 `VMError::controlled_crash(int)`。
3. 独立应用能接收编号并触发对应崩溃。
4. 至少验证 assert、guarantee、SIGSEGV、SIGFPE 和 fatal，保留命令、退出结果及
   `hs_err` 摘要。
5. 源码改动留在 Kona 源库；规划、应用、补丁与报告留在作业库。

## 实施设计

调用链为：

```text
ControlledCrash.main
  -> WhiteBox.controlledCrash(int) native
  -> WB_ControlledCrash(JNIEnv*, jobject, jint)
  -> VMError::controlled_crash(int)
  -> HotSpot 致命错误处理器 -> hs_err_pid*.log
```

`VMError::controlled_crash` 由 `ASSERT` 条件编译保护，所以 C++ 入口和 JNI 注册项也使用
`#ifdef ASSERT`。这使发布版构建仍可编译，但不会暴露一个无法实现的原生入口。调用者
还必须显式开启诊断选项与 WhiteBox API。

## 执行步骤

1. 在 Kona 源库修改 `whitebox.cpp` 和 `WhiteBox.java`。
2. 配置并构建 fastdebug：

   ```bash
   export KONA_SRC=/path/to/TencentKona-25
   cd "$KONA_SRC"
   bash configure --with-debug-level=fastdebug
   make images
   ```

3. 构建并运行 `apps/controlled-crash`。
4. 执行 `test-crashes.sh`，逐个检查错误日志中的信号/错误、问题帧、
   VM 版本和 `VMError::controlled_crash` 栈帧。
5. 将真实环境和结果填入 `docs/reports/task-1.1-controlled-crash.md`。

## 风险控制

- 每个用例使用新 JVM，测试脚本自身不进入目标 JVM。
- 构建产物不入库；按导师要求，七类用例各提交第一轮的一份完整 `hs_err`，其余重复日志不入库。
- 本 API 仅用于可信测试代码；WhiteBox 本身可读写任意地址，不能交给不可信应用。
- macOS/Linux 的信号文案可能不同，验收以编号对应的错误类别和原生栈为准。
