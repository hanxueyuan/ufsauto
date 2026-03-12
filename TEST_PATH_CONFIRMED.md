# 测试路径确认和分区信息

## 📊 磁盘分区信息（从截图获取）
| 设备 | 挂载点 | 大小 | 可用空间 | 文件系统 | 备注 |
|------|--------|------|----------|----------|------|
| `/dev/sda` | 多分区 | ~128GB | | ext4 | UFS 设备，分为多个分区 |
| `/dev/sda41` | `/mapdata` | 40G | 36G | ext4 | **可用空间最大，适合作为测试路径** |
| `/dev/sda43` | `/dataloop?` | 44G | 42G | ext4 | 可用空间也很大，可作为备选 |
| `/dev/sda33` | `/otadata` | 30G | 28G | ext4 |  |
| `/dev/sda37` | `/applog` | 9.8G | 9.3G | ext4 |  |
| `/dev/sda24` | `/app` | 2.9G | 1.4G | ext4 |  |
| `/home` | overlay | 224M | 132M | overlay | 空间太小，不适合测试 |

---
## ✅ 最终测试路径确定
**测试目录**：`/mapdata/ufs_test/`
**原因**：
1. 可用空间最大：36GB 可用，足够存放测试文件和临时数据
2. 独立分区：测试不会影响系统分区和其他业务分区
3. 读写性能好：ext4 文件系统，适合 IO 密集型测试
4. 安全：即使测试占满空间，也不会影响系统正常运行

---
## 🔧 测试环境初始化命令
```bash
# 创建测试目录
mkdir -p /mapdata/ufs_test
chmod 777 /mapdata/ufs_test

# 确认目录可写
cd /mapdata/ufs_test
dd if=/dev/zero of=test.img bs=1M count=100 && rm test.img
echo "Test directory is ready"
```

---
## 📋 下一步需要确认的信息
还需要执行以下命令获取更多信息：
```bash
# 1. 确认 UFS 设备名称
lsblk -d

# 2. 查看系统内核是否支持 UFS 相关特性
dmesg | grep -i ufs | head -30

# 3. 检查可用的命令
which dd md5sum grep awk sed lsblk dmesg df free

# 4. 查看 CPU 架构和核心数
lscpu 2>/dev/null || cat /proc/cpuinfo | grep "processor" | wc -l

# 5. 查看内存大小
free -h
```

这些信息确认后，我就可以开始编写完全适配当前环境的测试脚本了。
