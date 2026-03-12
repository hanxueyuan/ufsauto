# UFS 3.1 车规级测试工具集

针对UFS 3.1车载存储设备的硬件抽象层和测试工具集，符合JEDEC UFS 3.1标准，适用于车规级存储设备的功能验证、性能测试和可靠性评估。

## 功能特性

### 硬件抽象层 (UfsDevice类)
- ✅ 完整的UFS协议操作接口，遵循JEDEC JESD220E标准
- ✅ 支持描述符查询、属性读写、标志位操作
- ✅ 支持基本IO操作：读、写、擦除、解映射(Trim)
- ✅ 电源模式管理：ACTIVE/SLEEP/POWERDOWN/HIBERN8
- ✅ Write Booster功能支持（UFS 3.1特性）
- ✅ 健康状态监控和寿命评估
- ✅ 设备自检功能
- ✅ 错误处理和重试机制

### 命令行测试工具 (ufs_test_cli)
- ✅ 设备信息查询：完整的设备标识、容量、特性支持
- ✅ 健康报告：温度、寿命、健康度、异常状态监控
- ✅ 设备自检：快速/完整两种自检模式
- ✅ 性能测试：顺序读写、随机4K读写、IOPS、延迟测试
- ✅ 原始IO操作：直接读写指定LBA范围
- ✅ 电源管理：切换电源模式、功耗优化
- ✅ Write Booster管理：启用/禁用、缓冲区刷新
- ✅ 实时监控：温度、性能、状态实时显示
- ✅ 结果导出：支持JSON格式结果导出

## 系统要求

### 硬件
- UFS 3.1兼容设备
- 支持UFS子系统的Linux内核(4.19+)
- ARM64架构处理器（推荐车规级SoC）

### 软件
- Debian 12 (ARM64) 或其他支持UFS的Linux发行版
- Python 3.11+
- 内核UFS驱动支持
- root权限（访问UFS设备节点需要）

## 快速开始

### 环境搭建
```bash
# 安装依赖
apt update && apt install -y python3 python3-pip python3-tabulate
pip3 install -r requirements.txt

# 检查UFS设备
ls /dev/ufs*
```

### 基本使用
```bash
# 显示设备信息
python3 cli/ufs_test_cli.py info

# 查看健康报告
python3 cli/ufs_test_cli.py health

# 执行快速自检
python3 cli/ufs_test_cli.py selftest --short

# 性能测试（100MB顺序读写）
python3 cli/ufs_test_cli.py perf --size 100 --verify

# 实时监控设备状态
python3 cli/ufs_test_cli.py monitor --interval 1

# 读取指定LBA
python3 cli/ufs_test_cli.py read 1024 1 -o block.bin

# 写入指定LBA
python3 cli/ufs_test_cli.py write 1024 -i block.bin -y
```

## 命令详解

### info - 显示设备信息
```bash
ufs_test_cli.py info
```
显示设备制造商、型号、序列号、固件版本、容量、支持特性等基本信息。

### health - 健康报告
```bash
ufs_test_cli.py health
```
显示当前健康度、寿命使用百分比、温度、异常状态、电源模式等信息。

### selftest - 设备自检
```bash
ufs_test_cli.py selftest [--short]
```
执行设备自检，包含：
- 设备信息读取测试
- 描述符查询测试
- 基本读写验证测试
- 数据一致性校验

`--short` 参数执行快速自检，跳过耗时较长的测试项。

### perf - 性能测试
```bash
ufs_test_cli.py perf [选项]
```
选项：
- `-s, --size N`: 测试数据大小，单位MB，默认100MB
- `-b, --block-size N`: 块大小，单位字节，默认4096
- `-l, --lba N`: 测试起始LBA，默认1048576(512MB位置)
- `--lun N`: 测试LUN，默认0
- `--random`: 包含随机4K读取测试
- `--verify`: 读取时验证数据一致性
- `-o, --output FILE`: 结果导出到JSON文件

### read - 读取指定LBA
```bash
ufs_test_cli.py read LBA [COUNT] [--lun N] [-o FILE]
```
读取指定LBA范围的数据：
- `LBA`: 起始逻辑块地址
- `COUNT`: 读取块数，默认1
- `--lun`: 指定LUN，默认0
- `-o FILE`: 保存到文件，否则十六进制输出到屏幕

### write - 写入指定LBA
```bash
ufs_test_cli.py write LBA [--lun N] [-i FILE] [-y]
```
写入数据到指定LBA：
- `LBA`: 起始逻辑块地址
- `--lun`: 指定LUN，默认0
- `-i FILE`: 从文件读取数据，否则从标准输入读取
- `-y`: 不提示确认，直接执行

### erase - 擦除指定LBA
```bash
ufs_test_cli.py erase LBA COUNT [--lun N] [-y]
```
擦除指定LBA范围：
- `LBA`: 起始逻辑块地址
- `COUNT`: 擦除块数
- `--lun`: 指定LUN，默认0
- `-y`: 不提示确认，直接执行

### power - 电源管理
```bash
ufs_test_cli.py power [MODE]
```
查看或设置电源模式：
- 无参数：显示当前电源模式
- `MODE`: 要设置的模式，可选值：active, sleep, powerdown, hibern8

### wb - Write Booster管理
```bash
ufs_test_cli.py wb [--enable|--disable] [--flush]
```
管理Write Booster功能：
- 无参数：显示当前状态
- `--enable`: 启用Write Booster
- `--disable`: 禁用Write Booster
- `--flush`: 启用时刷新缓冲区

### monitor - 实时监控
```bash
ufs_test_cli.py monitor [-i SEC]
```
实时监控设备状态：
- `-i, --interval SEC`: 刷新间隔，默认1秒
- 显示内容：时间、温度、健康度、电源模式、实时读写速度

## 库使用示例

### 基本使用
```python
from ufs_device import UfsDevice, UfsPowerMode

# 打开设备
with UfsDevice("/dev/ufs0") as dev:
    # 读取设备信息
    print(f"设备型号: {dev.device_info.product_name}")
    print(f"总容量: {dev.device_info.total_capacity / (1024**3):.2f} GB")
    
    # 读取健康状态
    health = dev.get_health_report()
    print(f"健康度: {health['health_percent']}%")
    print(f"温度: {health['temperature_celsius']}°C")
    
    # 读取LBA 1024的1个块
    ok, data = dev.read_lba(1024, 1)
    if ok:
        print(f"读取成功，数据长度: {len(data)} 字节")
    
    # 写入数据
    test_data = b"Hello UFS!" + b"\x00" * 501  # 512字节
    ok, duration = dev.write_lba(1024, test_data)
    if ok:
        print(f"写入成功，耗时: {duration*1000:.2f}ms")
    
    # 设置低功耗模式
    dev.set_power_mode(UfsPowerMode.SLEEP)
```

### 高级功能
```python
# 启用Write Booster
if dev.device_info.write_booster_supported:
    dev.enable_write_booster(True)
    print("Write Booster已启用")

# 执行自检
test_results = dev.self_test(short_test=True)
if test_results['overall_result'] == 'pass':
    print("自检通过")
else:
    print(f"自检失败: {test_results['test_summary']}")

# 批量擦除
ok, duration = dev.erase_lba(1024, 1000)
if ok:
    print(f"擦除1000块成功，耗时: {duration:.2f}s")
```

## 测试用例

### 单元测试
```bash
cd tests
python -m pytest test_ufs_device.py -v
```

### 集成测试
需要实际UFS设备：
```bash
# 设置测试设备路径
export UFS_TEST_DEVICE=/dev/ufs0

# 运行集成测试
python -m pytest test_ufs_device.py::TestUfsDeviceIntegration -v
```

### 认证测试
包含JEDEC UFS 3.1协议一致性测试用例：
```bash
cd tests/compliance
python test_jedec_compliance.py
```

## 开源工具适配

本工具集支持与以下开源UFS测试工具集成：

### 1. ufs-utils (Linux官方UFS工具)
```bash
# 集成示例
ufs-utils desc /dev/ufs0
ufs_test_cli.py info
```

### 2. fio (存储性能测试)
提供fio适配脚本：
```bash
# 使用UFS设备运行fio测试
./scripts/fio_ufs_test.sh --device /dev/ufs0 --output results.json
```

### 3. blktrace (块层跟踪)
支持blktrace数据解析：
```bash
blktrace -d /dev/ufs0 -o - | blkparse -i -
./scripts/parse_blktrace.py blktrace.log
```

## 车规级测试特性

### AEC-Q100可靠性测试
- 温度循环测试：-40°C ~ 105°C
- 振动测试：符合ISO 16750标准
- 耐久性测试：PB级写入验证
- 断电保护测试：随机断电数据完整性验证

### 功能安全 (ISO 26262)
- ECC错误注入测试
- 数据完整性校验
- 错误恢复机制验证
- 安全相关寄存器访问控制

## 性能指标参考

| 测试项 | 典型值 | 单位 |
|--------|--------|------|
| 顺序读取 | 2100 | MB/s |
| 顺序写入 | 1800 | MB/s |
| 随机4K读取 | 400000 | IOPS |
| 随机4K写入 | 300000 | IOPS |
| 读取延迟 | < 50 | µs |
| 写入延迟 | < 100 | µs |

## 安全注意事项

⚠️ **危险操作警告**：
1. 直接访问UFS设备节点可能导致数据丢失，请确保在测试设备上操作
2. 写入/擦除操作会永久破坏数据，操作前务必备份重要数据
3. 电源模式切换可能导致设备无响应，测试时建议使用专用测试环境
4. 修改属性和标志位可能导致设备工作异常，需严格按照数据手册操作
5. 车规级设备的不当操作可能影响功能安全，需在专业人员指导下进行

## 目录结构

```
ufs31_test_suite/
├── src/                    # 源代码目录
│   ├── ufs_device.py       # UFS设备硬件抽象层
│   ├── ufs_protocol.py     # UFS协议定义
│   └── ufs_utils.py        # 工具函数
├── cli/                    # 命令行工具
│   └── ufs_test_cli.py     # 主命令行工具
├── tests/                  # 测试用例
│   ├── unit/               # 单元测试
│   ├── integration/        # 集成测试
│   └── compliance/         # 协议一致性测试
├── scripts/                # 辅助脚本
│   ├── env_setup.sh        # 环境搭建脚本
│   ├── fio_ufs_test.sh     # FIO性能测试脚本
│   └── stress_test.py      # 压力测试脚本
├── docs/                   # 文档
│   ├── protocol/           # 协议文档
│   ├── test_specs/         # 测试规范
│   └── api_reference.md    # API参考
├── requirements.txt        # Python依赖
└── README.md               # 本文件
```

## 构建与部署

### ARM Debian 12 环境搭建
```bash
# 下载Debian 12 ARM64镜像
wget https://cdimage.debian.org/debian-cd/current/arm64/iso-cd/debian-12.4.0-arm64-netinst.iso

# 烧录到SD卡
dd if=debian-12.4.0-arm64-netinst.iso of=/dev/mmcblk0 bs=4M status=progress

# 启动后安装必要包
apt install -y build-essential linux-headers-$(uname -r) python3-dev git
```

### 内核配置
确保内核启用以下配置：
```
CONFIG_SCSI_UFS=y
CONFIG_SCSI_UFS_BSG=y
CONFIG_SCSI_UFS_DEBUG=y
```

## 开发指南

### 代码规范
- 遵循PEP 8 Python编码规范
- 使用类型注解
- 每个函数必须有文档字符串
- 错误信息需清晰明确
- 关键操作必须有日志记录

### 扩展新功能
1. 在`src/ufs_device.py`中添加新的方法
2. 在`cli/ufs_test_cli.py`中添加对应的命令行接口
3. 编写单元测试到`tests/`目录
4. 更新文档和README

## 问题排查

### 常见问题

1. **无法打开设备：Permission denied**
   - 解决：使用root权限运行，或添加udev规则

2. **IOCTL调用失败：Invalid argument**
   - 解决：检查内核版本是否支持UFS，确认设备节点正确

3. **写入失败：Input/output error**
   - 解决：检查LBA是否在有效范围内，确认设备没有写保护

4. **性能测试结果偏低**
   - 解决：关闭后台应用，确保设备在ACTIVE电源模式，启用Write Booster

## 许可证

本项目采用Apache 2.0许可证，详见LICENSE文件。

## 技术支持

如有问题或建议，请联系开发团队：
- 协议相关：参考JEDEC JESD220E UFS 3.1规范
- 工具使用：查看文档或提交Issue
- 定制开发：支持车规级UFS测试方案定制

---
© 2024 UFS 3.1 车规项目团队
