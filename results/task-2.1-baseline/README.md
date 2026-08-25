# 任务 2.1 正式基准产物

下列文件是任务 2.1 报告中各项数据的可审计来源：

- `jmh-result.json`：由无未提交修改的 Kona 发布版构建生成的 JMH 1.37 输出，包含 GC 分析器指标；
- `environment.txt`：经过脱敏的环境信息和准确的 Kona 提交元数据；
- `SHA256SUMS`：由 `make check` 和持续集成检查的完整性清单。

生成命令如下：

```bash
export RESULT_DIR=results/reproductions/task-2.1-YYYYMMDD
make jmh-baseline KONA_SRC=/path/to/clean/TencentKona-25
make capture-environment KONA_SRC=/path/to/clean/TencentKona-25
```

SHA-256 校验和保存在 `SHA256SUMS` 中。运行 `make check-results` 可验证校验和、环境
元数据、九种场景的结果矩阵和 GC 分配指标。
