# UFS 性能测试套件

包含顺序读写、随机读写、混合读写等性能测试用例。

## 测试项列表

- `seq_read_burst` - 顺序读带宽 (Burst)
- `seq_read_sustained` - 顺序读带宽 (Sustained)
- `seq_write_burst` - 顺序写带宽 (Burst)
- `seq_write_sustained` - 顺序写带宽 (Sustained)
- `rand_read_burst` - 随机读 IOPS (Burst)
- `rand_read_sustained` - 随机读 IOPS (Sustained)
- `rand_write_burst` - 随机写 IOPS (Burst)
- `rand_write_sustained` - 随机写 IOPS (Sustained)
- `mixed_rw` - 混合读写性能

## 验收标准

| 测试项 | 目标值 | 单位 |
|--------|--------|------|
| seq_read_burst | ≥2100 | MB/s |
| seq_read_sustained | ≥1800 | MB/s |
| seq_write_burst | ≥1650 | MB/s |
| seq_write_sustained | ≥250 | MB/s |
| rand_read_burst | ≥200 | KIOPS |
| rand_read_sustained | ≥105 | KIOPS |
| rand_write_burst | ≥330 | KIOPS |
| rand_write_sustained | ≥60 | KIOPS |

## 执行示例

```bash
# 执行整个性能套件
SysTest run -s performance -d /dev/ufs0

# 执行单个测试项
SysTest run -t seq_read_burst -d /dev/ufs0 -v

# 执行并生成详细报告
SysTest run -s performance -d /dev/ufs0 --format html,json
```
