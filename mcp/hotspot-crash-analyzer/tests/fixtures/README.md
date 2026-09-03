# HotSpot 错误日志测试样本

`hs_err_controlled_*.log` 是受控崩溃应用在 macOS/AArch64 上生成的精简片段；
`hs_err_native_crash.log` 是用于验证非受控 Linux 原生库崩溃与 JBS 查询路径的合成样本。
它们保留解析器所需的文件头、摘要和相关栈帧，同时省略主机特有信息及无关诊断章节。

提交这些样本后，测试套件无需外部文件即可运行。按导师要求，
`apps/controlled-crash/crash-logs/` 中第一轮七类完整日志也作为原始实验证据提交；其余两轮
重复日志以及以后新生成的日志仍由 Git 忽略。
