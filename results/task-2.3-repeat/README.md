# GRAPH 反向顺序复测

这是任务 2.3 最终报告所引用的聚焦复测原始数据。为检查完整 A/B 测试固定采用
“基线后优化”的顺序是否造成系统性偏差，本轮按相反顺序先运行优化版、再运行基线版。

- 范围：`GRAPH` 的 `serialize`、`deserialize`、`roundTrip`
- 配置：3 forks，5 次预热，5 次测量，每次 1 秒，单线程
- `baseline.json`：Kona 提交 `3df5992b81e37891a2e0539c18cf119fe3d61552`
- `optimized.json`：Kona 提交 `0c13d1af75d6809546cb660836bef57836c3d181`

文件保持 JMH 原始 JSON，不做后处理；完整性由同目录 `SHA256SUMS` 和
`scripts/check-results.py` 校验。
