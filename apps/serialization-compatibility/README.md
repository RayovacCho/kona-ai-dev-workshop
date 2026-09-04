# 序列化跨版本兼容性检查

该程序分别使用基线和优化后的 Kona JDK 写入同一个确定性对象图，并交叉读取两个流。
对象图覆盖中英文字符串、共享引用、循环引用和 `writeUnshared/readUnshared`。最后使用
`cmp` 要求两边产生完全相同的字节流，从而把“不改变 wire format”变成可执行检查。

```bash
BASELINE_JAVA_HOME=/path/to/baseline/images/jdk \
OPTIMIZED_JAVA_HOME=/path/to/optimized/images/jdk \
./run.sh
```

也可以在仓库根目录执行 `make wire-compatibility`。
