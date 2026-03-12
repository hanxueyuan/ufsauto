# UFS 3.1 测试工具 API 参考文档

## UfsDevice 类

UFS设备的硬件抽象层，提供所有UFS设备操作接口。

### 构造函数

```python
UfsDevice(device_path: str = "/dev/ufs0")
```

参数：
- `device_path`: UFS设备节点路径，默认`/dev/ufs0`

### 方法

#### open() -> bool
打开UFS设备节点。

返回值：
- 成功返回True，失败返回False

#### close() -> None
关闭UFS设备节点。

#### 上下文管理器支持
UfsDevice支持with语句：
```python
with UfsDevice("/dev/ufs0") as dev:
    # 使用设备
```

#### query_descriptor(desc_type: UfsDescType, lun: int, idn: int) -> bytes
查询UFS描述符。

参数：
- `desc_type`: 描述符类型，枚举UfsDescType
- `lun`: 逻辑单元号
- `idn`: 描述符ID

返回值：
- 描述符数据字节流

#### query_attribute(attr_id: UfsAttrId, lun: int = 0) -> int
查询UFS属性值。

参数：
- `attr_id`: 属性ID，枚举UfsAttrId
- `lun`: 逻辑单元号，默认0

返回值：
- 属性整数值

#### set_attribute(attr_id: UfsAttrId, value: int, lun: int = 0) -> bool
设置UFS属性值。

参数：
- `attr_id`: 属性ID
- `value`: 要设置的值
- `lun`: 逻辑单元号，默认0

返回值：
- 成功返回True，失败返回False

#### query_flag(flag_id: UfsFlagId, lun: int = 0) -> bool
查询UFS标志状态。

参数：
- `flag_id`: 标志ID，枚举UfsFlagId
- `lun`: 逻辑单元号，默认0

返回值：
- 标志状态，True为置位，False为清除

#### set_flag(flag_id: UfsFlagId, value: bool, lun: int = 0) -> bool
设置UFS标志状态。

参数：
- `flag_id`: 标志ID
- `value`: True置位，False清除
- `lun`: 逻辑单元号，默认0

返回值：
- 成功返回True，失败返回False

#### send_command(opcode: UfsOpcode, lun: int = 0, lba: int = 0, transfer_len: int = 0, data: Optional[bytes] = None, timeout: int = 30000) -> UfsCommandResult
发送UFS命令到设备。

参数：
- `opcode`: 命令操作码，枚举UfsOpcode
- `lun`: 逻辑单元号，默认0
- `lba`: 逻辑块地址，默认0
- `transfer_len`: 传输长度（块数），默认0
- `data`: 写入数据（写命令时提供）
- `timeout`: 超时时间（毫秒），默认30000

返回值：
- UfsCommandResult对象，包含命令执行结果

#### read_lba(lba: int, count: int = 1, lun: int = 0) -> Tuple[bool, bytes]
读取逻辑块数据。

参数：
- `lba`: 起始逻辑块地址
- `count`: 读取块数，默认1
- `lun`: 逻辑单元号，默认0

返回值：
- 元组(成功标志, 数据)，成功时数据为读取的字节流

#### write_lba(lba: int, data: bytes, lun: int = 0) -> Tuple[bool, float]
写入逻辑块数据。

参数：
- `lba`: 起始逻辑块地址
- `data`: 要写入的数据，长度必须是512的倍数
- `lun`: 逻辑单元号，默认0

返回值：
- 元组(成功标志, 耗时秒数)

#### erase_lba(lba: int, count: int, lun: int = 0) -> Tuple[bool, float]
擦除逻辑块。

参数：
- `lba`: 起始逻辑块地址
- `count`: 擦除块数
- `lun`: 逻辑单元号，默认0

返回值：
- 元组(成功标志, 耗时秒数)

#### unmap_lba(lba: int, count: int, lun: int = 0) -> Tuple[bool, float]
解映射逻辑块（Trim/Unmap）。

参数：
- `lba`: 起始逻辑块地址
- `count`: 解映射块数
- `lun`: 逻辑单元号，默认0

返回值：
- 元组(成功标志, 耗时秒数)

#### flush_cache(lun: int = 0) -> bool
刷新设备缓存。

参数：
- `lun`: 逻辑单元号，默认0

返回值：
- 成功返回True

#### get_power_mode() -> UfsPowerMode
获取当前电源模式。

返回值：
- UfsPowerMode枚举值：ACTIVE, SLEEP, POWERDOWN, HIBERN8

#### set_power_mode(mode: UfsPowerMode) -> bool
设置电源模式。

参数：
- `mode`: 目标电源模式，UfsPowerMode枚举

返回值：
- 成功返回True

#### enable_write_booster(enable: bool = True) -> bool
启用/禁用Write Booster功能。

参数：
- `enable`: True启用，False禁用

返回值：
- 成功返回True，设备不支持时返回False

#### get_health_report() -> Dict[str, Any]
获取设备健康报告。

返回字典包含：
- `product_name`: 产品名称
- `serial_number`: 序列号
- `firmware_version`: 固件版本
- `total_capacity_gb`: 总容量（GB）
- `health_percent`: 健康度百分比（0-100）
- `life_used_percent`: 使用寿命已使用百分比
- `temperature_celsius`: 当前温度（摄氏度）
- `write_booster_enabled`: Write Booster是否启用
- `background_ops_enabled`: 后台操作是否启用
- `exception_status`: 异常状态标志
- `power_mode`: 当前电源模式名称

#### self_test(short_test: bool = True) -> Dict[str, Any]
执行设备自检。

参数：
- `short_test`: True执行快速自检，False执行完整自检

返回字典包含：
- `test_start_time`: 测试开始时间
- `overall_result`: 整体结果（pass/fail）
- `test_summary`: 测试总结
- `tests`: 详细测试结果列表

### 属性

#### device_info: UfsDeviceInfo
设备信息对象，包含以下字段：
- `manufacturer_id`: 制造商ID
- `product_name`: 产品名称
- `serial_number`: 序列号
- `firmware_version`: 固件版本
- `spec_version`: UFS协议版本
- `total_capacity`: 总容量（字节）
- `max_lun`: 最大LUN数量
- `supported_gear`: 支持的速率等级列表
- `supported_lanes`: 支持的通道数
- `write_booster_supported`: 是否支持Write Booster
- `hpb_supported`: 是否支持HPB
- `rpmb_supported`: 是否支持RPMB
- `health_status`: 健康状态值
- `temperature`: 当前温度

#### is_open: bool
设备是否已打开。

#### fd: Optional[int]
设备文件描述符。

## 枚举类型

### UfsDescType (描述符类型)
- `DEVICE = 0x00`: 设备描述符
- `CONFIGURATION = 0x01`: 配置描述符
- `UNIT = 0x02`: 单元描述符
- `INTERCONNECT = 0x03`: 互连描述符
- `STRING = 0x04`: 字符串描述符
- `GEOMETRY = 0x05`: 几何描述符
- `POWER = 0x06`: 电源描述符

### UfsAttrId (属性ID)
- `bBootLunEn = 0x00`: 启动LUN启用
- `bCurrentPowerMode = 0x01`: 当前电源模式
- `bActiveICCLevel = 0x02`: 当前ICC级别
- `wPeriodicRTCUpdate = 0x03`: 周期RTC更新
- `bRefClkFreq = 0x04`: 参考时钟频率
- `bConfigDescrLock = 0x05`: 配置描述符锁定
- `bMaxNumOfRTT = 0x06`: 最大RTT数量
- `wExceptionEventControl = 0x07`: 异常事件控制
- `wExceptionEventStatus = 0x08`: 异常事件状态
- `dTotalAddrSpaceUnits = 0x09`: 总地址空间单元
- `wAvailableAddrSpaceUnits = 0x0A`: 可用地址空间单元
- `bContextConf = 0x0B`: 上下文配置
- `bDeviceInfoLevel = 0x0C`: 设备信息级别
- `bDeviceInfo = 0x0D`: 设备信息
- `wDeviceCapabilities = 0x0E`: 设备能力
- `wDeviceFeatures = 0x0F`: 设备特性

### UfsFlagId (标志ID)
- `fDeviceInit = 0x00`: 设备初始化
- `fPermanentWPEn = 0x01`: 永久写保护启用
- `fPowerOnWPEn = 0x02`: 上电写保护启用
- `fBackgroundOpsEn = 0x03`: 后台操作启用
- `fPurgeEnable = 0x04`: 擦除启用
- `fPhyResourceRemoval = 0x05`: 物理资源移除
- `fBusyRTC = 0x06`: RTC忙
- `fDeviceFatal = 0x07`: 设备致命错误
- `fPermanentWP = 0x08`: 永久写保护状态
- `fPowerOnWP = 0x09`: 上电写保护状态
- `fLogicalBlockSize = 0x0A`: 逻辑块大小
- `fWriteBoosterEn = 0x0B`: Write Booster启用
- `fWriteBoosterBufFlushEn = 0x0C`: Write Booster缓冲区刷新启用

### UfsOpcode (命令操作码)
- `NOP = 0x00`: 空操作
- `WRITE = 0x01`: 写入
- `READ = 0x02`: 读取
- `ERASE = 0x03`: 擦除
- `WRITE_BUFFER = 0x04`: 写缓冲区
- `READ_BUFFER = 0x05`: 读缓冲区
- `SYNCHRONIZE_CACHE = 0x06`: 同步缓存
- `UNMAP = 0x07`: 解映射
- `GET_LBA_STATUS = 0x08`: 获取LBA状态
- `SECURITY_PROTOCOL_IN = 0x09`: 安全协议输入
- `SECURITY_PROTOCOL_OUT = 0x0A`: 安全协议输出
- `PERSISTENT_RESERVE_IN = 0x0B`: 持久保留输入
- `PERSISTENT_RESERVE_OUT = 0x0C`: 持久保留输出
- `FORMAT_UNIT = 0x0D`: 格式化单元

### UfsPowerMode (电源模式)
- `ACTIVE = 0x00`: 活动模式
- `SLEEP = 0x01`: 睡眠模式
- `POWERDOWN = 0x02`: 掉电模式
- `HIBERN8 = 0x03`: 休眠模式

## 数据结构

### UfsCommandResult
命令执行结果：
- `success: bool`: 执行是否成功
- `status: int`: 命令状态码
- `response: bytes`: 响应数据
- `duration: float`: 执行耗时（秒）
- `error_message: Optional[str]`: 错误信息（失败时）

### UfsDeviceInfo
设备信息，详见UfsDevice.device_info属性说明。

## 错误处理

所有方法在遇到严重错误时会抛出异常，常见异常类型：
- `RuntimeError`: 设备未打开、操作失败
- `ValueError`: 参数无效
- `IOError`: 设备IO错误
- `OSError`: 系统调用错误

建议在关键操作处使用try-except块捕获异常。

## 示例代码

### 基本设备操作
```python
from ufs_device import UfsDevice, UfsPowerMode

# 打开设备
with UfsDevice("/dev/ufs0") as dev:
    # 获取设备信息
    print(f"设备: {dev.device_info.product_name}")
    print(f"容量: {dev.device_info.total_capacity / (1024**3):.2f} GB")
    
    # 读取健康状态
    health = dev.get_health_report()
    print(f"健康度: {health['health_percent']}%")
    print(f"温度: {health['temperature_celsius']}°C")
    
    # 执行自检
    test_result = dev.self_test()
    if test_result['overall_result'] == 'pass':
        print("自检通过")
    else:
        print("自检失败")
```

### 数据读写
```python
# 写入数据
data = b"Hello UFS!" * 64  # 512字节
ok, write_time = dev.write_lba(1024, data)
if ok:
    print(f"写入成功，耗时: {write_time*1000:.2f}ms")
    
# 读取数据
ok, read_data = dev.read_lba(1024, 1)
if ok and read_data == data:
    print("数据验证成功")
```

### 电源管理
```python
# 获取当前电源模式
mode = dev.get_power_mode()
print(f"当前电源模式: {mode.name}")

# 设置为睡眠模式
dev.set_power_mode(UfsPowerMode.SLEEP)
time.sleep(1)

# 唤醒到活动模式
dev.set_power_mode(UfsPowerMode.ACTIVE)
```

### Write Booster使用
```python
if dev.device_info.write_booster_supported:
    # 启用Write Booster
    dev.enable_write_booster(True)
    
    # 执行高速写入
    large_data = os.urandom(100 * 1024 * 1024)  # 100MB
    ok, time = dev.write_lba(2048, large_data)
    print(f"写入速度: {100 / time:.2f} MB/s")
    
    # 刷新缓冲区
    dev.set_flag(UfsFlagId.fWriteBoosterBufFlushEn, True)
```

## 性能优化建议

1. **块大小选择**：
   - 大文件传输使用1MB块大小获得最大带宽
   - 随机访问使用4KB块大小获得最高IOPS
   - 对齐到512字节边界

2. **队列深度**：
   - 顺序读写使用32-64队列深度
   - 随机读写使用16-32队列深度
   - 低延迟场景使用4-8队列深度

3. **电源模式**：
   - 性能测试时确保设备在ACTIVE模式
   - 空闲时切换到SLEEP模式降低功耗
   - Write Booster只有在ACTIVE模式下生效

4. **缓存策略**：
   - 使用direct IO绕过系统缓存获得真实设备性能
   - 关键数据写入后调用flush_cache确保持久化
   - 批量操作后统一刷新缓存提高效率

## 安全注意事项

1. **权限要求**：
   - 访问UFS设备需要root权限
   - 生产环境建议配置udev规则控制访问权限
   - 避免普通用户直接访问原始设备

2. **数据安全**：
   - 所有写入/擦除操作会永久破坏数据
   - 测试前确保备份重要数据
   - 建议在专用测试设备上进行开发和测试

3. **设备稳定性**：
   - 修改属性和标志位可能导致设备工作异常
   - 电源模式切换可能导致IO超时
   - 压力测试可能导致设备过热，需适当散热
