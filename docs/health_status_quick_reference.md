# UFS 健康状态采集 - 快速参考

## 🚀 快速开始

### 检查 UFS 设备健康状态

```bash
# 方法 1: 使用独立监控工具
cd /workspace/projects/ufsauto
python3 systest/tools/health_monitor.py --device /dev/sda

# 方法 2: 扫描所有 UFS 设备
python3 systest/tools/health_monitor.py --scan

# 方法 3: 在 Python 代码中使用
from tools.ufs_utils import UFSDevice

ufs = UFSDevice('/dev/sda')
health = ufs.get_health_status()
print(f"Health: {health['status']}")
```

### 预期输出

**成功获取健康状态**：
```
✅ 健康状态：OK
   数据来源：sysfs

📊 详细信息:
   Pre-EOL 信息：     0x00
   寿命估算 A:        0x08
   寿命估算 B:        0x08
   寿命百分比：       80%
   关键警告标志：     0
   温度：            45°C
```

**无法获取健康状态（降级）**：
```
ℹ️  健康状态：OK
   数据来源：none

⚠️  警告：无法获取 UFS 健康状态
   可能原因:
   - 设备不是 UFS 设备
   - 内核不支持 UFS 健康查询
   - 需要 root 权限
```

---

## 📁 文件位置

| 文件 | 路径 | 说明 |
|------|------|------|
| 主工具类 | `systest/tools/ufs_utils.py` | `UFSDevice.get_health_status()` |
| 独立监控器 | `systest/tools/health_monitor.py` | `UFSHealthMonitor` 类 |
| 测试脚本 | `systest/tools/test_health_monitor.py` | 验证工具 |
| 调用点 | `systest/core/runner.py` | `TestCase.setup()` |

---

## 🔧 健康状态字段说明

### 返回数据结构

```python
{
    'status': 'OK',              # 健康状态
    'pre_eol_info': '0x00',      # Pre-EOL 信息
    'device_life_time_est_a': '0x08',  # 寿命估算 A
    'device_life_time_est_b': '0x08',  # 寿命估算 B
    'critical_warning': 0,       # 关键警告标志
    'temperature': 45,           # 温度（°C）
    'life_span': 80,             # 寿命百分比
    'source': 'sysfs'            # 数据来源
}
```

### 状态值说明

| 状态 | 说明 | 触发条件 |
|------|------|----------|
| `OK` | 正常 | 无警告，Pre-EOL=0x00 |
| `WARNING` | 警告 | （保留，暂未使用） |
| `CRITICAL` | 严重警告 | `critical_warning > 0` |
| `PRE_EOL` | 接近寿命终点 | `pre_eol_info` = 0x01 或 0x02 |
| `UNSUPPORTED` | 不支持 | 设备不支持健康查询 |

### Pre-EOL 信息值

| 值 | 说明 |
|----|------|
| `0x00` | 正常 |
| `0x01` | 警告（寿命 < 10%） |
| `0x02` | 严重（寿命 < 5%） |
| `N/A` | 不可用 |

### 寿命估算值

- 范围：`0x00` - `0x0A`（0-100%）
- 计算：`寿命百分比 = 值 × 10`
- 示例：`0x08` = 80% 寿命

---

## 🛠️ 故障排查

### 问题 1: "缺少测试前健康状态数据"

**现象**：
```
⚠️  Postcondition 检查：缺少测试前健康状态数据
```

**可能原因**：
1. 设备不是 UFS 设备（可能是 SATA SSD、NVMe 等）
2. 内核不支持 UFS 健康查询
3. 需要 root 权限
4. 设备固件不支持健康描述符

**解决方案**：
- 这是**预期行为**，测试会继续执行（降级处理）
- 在真实 UFS 设备上会自动获取健康状态
- 如需调试，运行：`python3 systest/tools/health_monitor.py --device /dev/sda --verbose`

### 问题 2: 无法找到 UFS 设备

**检查 sysfs 结构**：
```bash
# 检查 UFS 设备是否存在
ls -la /sys/bus/ufs/devices/

# 检查健康描述符
ls -la /sys/bus/ufs/devices/*/health_descriptor/

# 查看具体内容
cat /sys/bus/ufs/devices/*/health_descriptor/pre_eol_info
```

**如果目录不存在**：
- 当前设备可能不是 UFS 设备
- 内核可能未加载 UFS 驱动
- 检查内核模块：`lsmod | grep ufs`

### 问题 3: 权限错误

**症状**：
```
Permission denied: /sys/bus/ufs/devices/*/health_descriptor/*
```

**解决方案**：
```bash
# 使用 root 权限运行
sudo python3 systest/tools/health_monitor.py --device /dev/sda
```

---

## 📊 数据采集流程

```
get_health_status()
│
├─> _find_ufs_health_dir()
│   │
│   ├─ 策略 1: 扫描 /sys/bus/ufs/devices/
│   ├─ 策略 2: 从 SCSI 设备反向查找 UFS 驱动
│   └─ 策略 3: 尝试 /sys/class/ufs_device/
│
├─> _read_health_from_sysfs()  [如果找到 health_dir]
│   │
│   ├─ 读取 pre_eol_info
│   ├─ 读取 device_life_time_est_a/b
│   ├─ 读取 critical_warning
│   └─ 读取 temperature（如果可用）
│
├─> _read_health_from_scsi()  [如果 sysfs 失败]
│   │
│   └─ 使用 sg_inq 读取 VPD 页面 0xC0
│
└─> 确定最终状态
    │
    ├─ critical_warning > 0  → CRITICAL
    ├─ pre_eol_info = 0x01/0x02 → PRE_EOL
    ├─ source != 'none' → OK
    └─ source == 'none' → OK (降级)
```

---

## 🧪 测试命令

### 基础测试
```bash
# 检查设备
python3 systest/tools/health_monitor.py --device /dev/sda

# 扫描设备
python3 systest/tools/health_monitor.py --scan

# 详细输出
python3 systest/tools/health_monitor.py --device /dev/sda --verbose
```

### 集成测试
```bash
# 运行 QoS 测试套件
python3 systest/bin/systest.py --device /dev/sda --suite qos

# 运行性能测试套件
python3 systest/bin/systest.py --device /dev/sda --suite performance
```

### 调试模式
```bash
# 启用调试日志
export LOG_LEVEL=DEBUG
python3 systest/tools/health_monitor.py --device /dev/sda -v

# 查看完整日志
tail -f /var/log/ufsauto/test.log
```

---

## 📚 相关文档

- [详细调查报告](./ufs_health_investigation_report.md)
- [UFS 规范](https://www.jedec.org/standards-documents/results/jesd220)
- [Linux UFS 驱动文档](https://www.kernel.org/doc/html/latest/scsi/ufs.html)

---

## 🔗 代码示例

### 在测试用例中使用

```python
from tools.ufs_utils import UFSDevice

class MyTestCase(TestCase):
    def setup(self) -> bool:
        # 获取健康状态
        self.ufs = UFSDevice(self.device, logger=self.logger)
        self._pre_test_health = self.ufs.get_health_status()
        
        # 检查健康状态
        if self._pre_test_health['status'] != 'OK':
            self.logger.warning(f"Device health warning: {self._pre_test_health}")
        
        return True
    
    def validate(self, result: Dict[str, Any]) -> bool:
        # 获取测试后健康状态
        self._post_test_health = self.ufs.get_health_status()
        
        # 比较健康状态变化
        if self._pre_test_health['critical_warning'] != self._post_test_health['critical_warning']:
            self.record_failure(
                "Critical Warning",
                str(self._pre_test_health['critical_warning']),
                str(self._post_test_health['critical_warning'])
            )
        
        return True
```

### 使用独立监控器

```python
from tools.health_monitor import UFSHealthMonitor, scan_ufs_devices

# 扫描所有 UFS 设备
devices = scan_ufs_devices()
print(f"Found {len(devices)} UFS devices: {devices}")

# 监控指定设备
monitor = UFSHealthMonitor('/dev/sda')
health = monitor.get_health()

print(f"Status: {health['status']}")
print(f"Life span: {health.get('life_span', 'N/A')}%")
print(f"Source: {health['source']}")
```

---

**最后更新**: 2026-04-10  
**版本**: 1.0
