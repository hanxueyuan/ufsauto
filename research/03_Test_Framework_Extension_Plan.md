# UFS 汽车存储测试框架扩展计划

## 一、现有框架分析

### 1.1 当前 systest 架构

```
/workspace/projects/ufsauto/systest/
├── bin/                      # 可执行脚本
│   ├── SysTest              # 主入口 (systest.py)
│   ├── check_env.py         # 环境检查
│   ├── fio_wrapper.py       # fio 封装
│   └── report_gen.py        # 报告生成
├── config/                   # 配置文件
│   ├── runtime.json         # 运行时配置
│   └── test_profiles.yaml   # 测试配置文件
├── core/                     # 核心模块
│   ├── runner.py            # 测试执行器
│   ├── collector.py         # 结果收集器
│   ├── reporter.py          # 报告生成器
│   └── logger.py            # 日志系统
├── suites/                   # 测试套件
│   ├── performance/         # 性能测试
│   │   ├── t_perf_SeqReadBurst_001.py
│   │   ├── t_perf_SeqWriteBurst_002.py
│   │   ├── t_perf_RandReadBurst_003.py
│   │   ├── t_perf_RandWriteBurst_004.py
│   │   └── t_perf_MixedRw_005.py
│   └── qos/                 # QoS 测试
│       └── t_qos_LatencyPercentile_001.py
└── tools/                    # 工具模块
    ├── ufs_controller.py    # UFS 控制 (待开发)
    ├── data_validator.py    # 数据验证 (待开发)
    └── temperature_monitor.py # 温度监控 (待开发)
```

### 1.2 现有功能评估

| 模块 | 状态 | 功能 | 需要扩展 |
|------|------|------|----------|
| SysTest CLI | ✅ 完成 | 参数化执行，日志，报告 | 添加车规测试命令 |
| TestRunner | ✅ 完成 | 套件/测试发现，执行 | 添加并行执行，超时控制 |
| ResultCollector | ✅ 完成 | JSON 结果收集 | 添加数据库存储 |
| ReportGenerator | ✅ 完成 | HTML/Markdown 报告 | 添加车规模板 |
| performance 套件 | ✅ 完成 | 顺序/随机读写 | 添加 QoS，稳态测试 |
| qos 套件 | 🟡 部分 | 延迟百分位 | 完善多场景测试 |
| reliability 套件 | ❌ 缺失 | - | 全新开发 |
| automotive 套件 | ❌ 缺失 | - | 全新开发 |

### 1.3 代码质量评估

```python
# 现有代码优点
✅ 清晰的模块化设计
✅ 统一的日志系统
✅ 参数化测试执行
✅ 自动报告生成
✅ 环境检查工具

# 需要改进的方面
⚠️ 缺少测试超时控制
⚠️ 缺少并行测试执行
⚠️ 缺少设备管理抽象
⚠️ 缺少温度/电源控制集成
⚠️ 缺少车规特定功能
```

---

## 二、框架扩展设计

### 2.1 新增目录结构

```
/workspace/projects/ufsauto/systest/
├── suites/
│   ├── performance/              # [扩展] 性能测试
│   │   ├── t_perf_SeqReadBurst_001.py
│   │   ├── t_perf_SeqWriteBurst_002.py
│   │   ├── t_perf_RandReadBurst_003.py
│   │   ├── t_perf_RandWriteBurst_004.py
│   │   ├── t_perf_MixedRw_005.py
│   │   ├── t_perf_SteadyState_006.py      # [新增] 稳态性能
│   │   ├── t_perf_QoS_007.py              # [新增] QoS 一致性
│   │   ├── t_perf_HPBGain_008.py          # [新增] HPB 增益
│   │   └── t_perf_Startup_009.py          # [新增] 启动性能
│   │
│   ├── reliability/              # [新增] 可靠性测试
│   │   ├── t_rel_TempCycle_001.py         # 温度循环
│   │   ├── t_rel_PowerCycle_002.py        # 电源循环
│   │   ├── t_rel_PowerLoss_003.py         # 异常掉电
│   │   ├── t_rel_LongRun_004.py           # 长期运行
│   │   ├── t_rel_WearLevel_005.py         # 磨损测试
│   │   └── t_rel_DataRet_006.py           # 数据保持
│   │
│   ├── functional/               # [新增] 功能测试
│   │   ├── t_func_BasicRW_001.py          # 基本读写
│   │   ├── t_func_PowerMgmt_002.py        # 电源管理
│   │   ├── t_func_ErrorRec_003.py         # 错误恢复
│   │   ├── t_func_Security_004.py         # 安全功能
│   │   └── t_func_Firmware_005.py         # 固件升级
│   │
│   ├── automotive/               # [新增] 车规测试
│   │   ├── t_auto_ColdStart_001.py        # 冷启动
│   │   ├── t_auto_HighTemp_002.py         # 高温工作
│   │   ├── t_auto_LowTemp_003.py          # 低温工作
│   │   ├── t_auto_Vibration_004.py        # 振动测试
│   │   ├── t_auto_EMI_005.py              # EMI 测试
│   │   └── t_auto_Safety_006.py           # 功能安全
│   │
│   └── compatibility/            # [新增] 兼容性测试
│       ├── t_compat_ext4_001.py           # ext4 文件系统
│       ├── t_compat_F2FS_002.py           # F2FS 文件系统
│       ├── t_compat_Linux_003.py          # Linux OS
│       └── t_compat_MultiApp_004.py       # 多应用并发
│
├── tools/
│   ├── __init__.py
│   ├── ufs_device.py             # [新增] UFS 设备抽象
│   ├── temperature_chamber.py    # [新增] 温控箱控制
│   ├── power_supply.py           # [新增] 电源控制
│   ├── vibration_table.py        # [新增] 振动台控制
│   ├── data_generator.py         # [新增] 测试数据生成
│   ├── data_validator.py         # [新增] 数据完整性验证
│   ├── fio_runner.py             # [新增] fio 执行封装
│   ├── result_analyzer.py        # [新增] 结果分析
│   └── report_templates/         # [新增] 报告模板
│       ├── performance.html
│       ├── reliability.html
│       └── automotive.html
│
├── config/
│   ├── runtime.json              # 运行时配置
│   ├── test_profiles.yaml        # 测试配置
│   ├── automotive_profiles.yaml  # [新增] 车规定义文件
│   ├── device_database.yaml      # [新增] 设备数据库
│   └── threshold_config.yaml     # [新增] 通过阈值配置
│
└── core/
    ├── runner.py                 # [扩展] 测试执行器
    ├── collector.py              # [扩展] 结果收集器
    ├── reporter.py               # [扩展] 报告生成器
    ├── logger.py                 # [保持] 日志系统
    ├── device_manager.py         # [新增] 设备管理器
    ├── timeout.py                # [新增] 超时控制
    └── parallel.py               # [新增] 并行执行
```

### 2.2 核心模块设计

#### 2.2.1 UFS 设备抽象

```python
# tools/ufs_device.py
from abc import ABC, abstractmethod
from typing import Dict, Optional
from pathlib import Path

class UFSDevice(ABC):
    """UFS 设备抽象基类"""
    
    def __init__(self, device_path: str):
        self.device_path = Path(device_path)
        self.device_info = {}
        self.health_info = {}
        
    @abstractmethod
    def read(self, lba: int, length: int, buffer_size: int = 4096) -> bytes:
        """读取数据"""
        pass
    
    @abstractmethod
    def write(self, lba: int, data: bytes) -> bool:
        """写入数据"""
        pass
    
    @abstractmethod
    def get_health(self) -> Dict:
        """获取健康信息"""
        pass
    
    @abstractmethod
    def power_cycle(self):
        """电源循环"""
        pass
    
    @abstractmethod
    def set_power_state(self, state: str):
        """设置电源状态 (active/sleep/deepsleep)"""
        pass
    
    def get_info(self) -> Dict:
        """获取设备信息"""
        return {
            'path': str(self.device_path),
            'model': self.device_info.get('model', 'Unknown'),
            'capacity': self.device_info.get('capacity', 0),
            'firmware': self.device_info.get('firmware', 'Unknown'),
        }


class LinuxUFSDevice(UFSDevice):
    """Linux 系统 UFS 设备实现"""
    
    def __init__(self, device_path: str):
        super().__init__(device_path)
        self._probe_device()
    
    def _probe_device(self):
        """探测设备信息"""
        import subprocess
        try:
            # 获取容量
            result = subprocess.run(
                ['blockdev', '--getsize64', str(self.device_path)],
                capture_output=True, text=True, check=True
            )
            self.device_info['capacity'] = int(result.stdout.strip())
            
            # 获取 SMART 信息
            result = subprocess.run(
                ['smartctl', '-a', str(self.device_path)],
                capture_output=True, text=True
            )
            self._parse_smart(result.stdout)
        except Exception as e:
            logging.warning(f"Failed to probe device: {e}")
    
    def read(self, lba: int, length: int, buffer_size: int = 4096) -> bytes:
        """使用 dd 读取数据"""
        import subprocess
        offset = lba * 512  # 假设 512 字节扇区
        result = subprocess.run(
            ['dd', f'if={self.device_path}', f'bs={buffer_size}', 
             f'skip={offset//buffer_size}', f'count={length//buffer_size}'],
            capture_output=True, check=True
        )
        return result.stdout
    
    def write(self, lba: int, data: bytes) -> bool:
        """使用 dd 写入数据"""
        import subprocess
        offset = lba * 512
        process = subprocess.run(
            ['dd', f'of={self.device_path}', 'bs=512', 
             f'seek={offset//512}', 'conv=notrunc'],
            input=data, capture_output=True
        )
        return process.returncode == 0
    
    def get_health(self) -> Dict:
        """从 SMART 获取健康信息"""
        return self.health_info
    
    def power_cycle(self):
        """通过 sysfs 控制电源"""
        # 实现电源循环逻辑
        pass
    
    def set_power_state(self, state: str):
        """通过 runtime PM 设置电源状态"""
        # 实现电源状态切换
        pass
```

#### 2.2.2 温控箱控制

```python
# tools/temperature_chamber.py
import serial
import time
from typing import Optional

class TemperatureChamber:
    """温度试验箱控制"""
    
    def __init__(self, port: str = '/dev/ttyUSB0', model: str = 'ESPEC'):
        self.port = port
        self.model = model
        self.serial_conn = None
        self.current_temp = None
        self.target_temp = None
        
    def connect(self, baudrate: int = 9600) -> bool:
        """连接温控箱"""
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=baudrate,
                timeout=1
            )
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False
    
    def set_temperature(self, temp: float) -> bool:
        """设置目标温度"""
        self.target_temp = temp
        command = f"TEMP {temp:.1f}\r\n"
        self.serial_conn.write(command.encode())
        response = self.serial_conn.readline()
        return 'OK' in response.decode()
    
    def get_temperature(self) -> Optional[float]:
        """获取当前温度"""
        self.serial_conn.write(b"TEMP?\r\n")
        response = self.serial_conn.readline()
        try:
            self.current_temp = float(response.decode().strip())
            return self.current_temp
        except:
            return None
    
    def wait_stable(self, tolerance: float = 0.5, timeout: int = 3600) -> bool:
        """等待温度稳定"""
        start_time = time.time()
        stable_count = 0
        required_stable = 5  # 连续 5 次读数稳定
        
        while time.time() - start_time < timeout:
            current = self.get_temperature()
            if current is None:
                continue
            
            if self.target_temp is not None:
                if abs(current - self.target_temp) <= tolerance:
                    stable_count += 1
                    if stable_count >= required_stable:
                        return True
                else:
                    stable_count = 0
            
            time.sleep(10)  # 每 10 秒读取一次
        
        return False  # 超时
    
    def dwell(self, minutes: int):
        """保温指定时间"""
        time.sleep(minutes * 60)
    
    def start_cycle(self, temp_low: float, temp_high: float, 
                    cycles: int, dwell_time: int) -> bool:
        """启动温度循环"""
        for cycle in range(cycles):
            # 低温阶段
            self.set_temperature(temp_low)
            self.wait_stable()
            self.dwell(dwell_time)
            
            # 高温阶段
            self.set_temperature(temp_high)
            self.wait_stable()
            self.dwell(dwell_time)
            
            print(f"Cycle {cycle + 1}/{cycles} completed")
        
        return True
    
    def disconnect(self):
        """断开连接"""
        if self.serial_conn:
            self.serial_conn.close()
```

#### 2.2.3 测试执行器扩展

```python
# core/runner.py (扩展)
import concurrent.futures
import signal
from contextlib import contextmanager

class TestRunner:
    def __init__(self, ...):
        # ... 现有代码 ...
        self.timeout = None
        self.parallel_jobs = 1
        
    def set_timeout(self, seconds: int):
        """设置测试超时"""
        self.timeout = seconds
    
    def set_parallel(self, jobs: int):
        """设置并行任务数"""
        self.parallel_jobs = jobs
    
    @contextmanager
    def timeout_context(self, seconds: int):
        """超时上下文管理器"""
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Test timeout after {seconds} seconds")
        
        # 设置信号处理器
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(seconds)
        
        try:
            yield
        finally:
            # 恢复
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    
    def run_parallel(self, test_list: list, max_workers: int = 4) -> Dict:
        """并行执行测试"""
        results = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_test = {
                executor.submit(self.run_single, test): test 
                for test in test_list
            }
            
            for future in concurrent.futures.as_completed(future_to_test):
                test = future_to_test[future]
                try:
                    result = future.result()
                    results[test['id']] = result
                except Exception as e:
                    results[test['id']] = {
                        'status': 'ERROR',
                        'error': str(e)
                    }
        
        return results
```

---

## 三、开发计划

### 3.1 阶段一：基础框架扩展 (2 周)

**Week 1:**
- [ ] 扩展 TestRunner 支持超时控制
- [ ] 扩展 TestRunner 支持并行执行
- [ ] 实现 UFSDevice 抽象类
- [ ] 实现 LinuxUFSDevice 具体类
- [ ] 添加设备管理器

**Week 2:**
- [ ] 实现温度试验箱控制类
- [ ] 实现电源控制类
- [ ] 实现数据生成器
- [ ] 实现数据验证器
- [ ] 完善结果收集器 (添加数据库支持)

### 3.2 阶段二：测试套件开发 (3 周)

**Week 3 - 性能测试扩展:**
- [ ] t_perf_SteadyState_006.py - 稳态性能测试
- [ ] t_perf_QoS_007.py - QoS 一致性测试
- [ ] t_perf_HPBGain_008.py - HPB 增益测试
- [ ] t_perf_Startup_009.py - 启动性能测试

**Week 4 - 可靠性测试:**
- [ ] t_rel_TempCycle_001.py - 温度循环
- [ ] t_rel_PowerCycle_002.py - 电源循环
- [ ] t_rel_PowerLoss_003.py - 异常掉电
- [ ] t_rel_LongRun_004.py - 长期运行

**Week 5 - 车规测试:**
- [ ] t_auto_ColdStart_001.py - 冷启动
- [ ] t_auto_HighTemp_002.py - 高温工作
- [ ] t_auto_LowTemp_003.py - 低温工作
- [ ] t_auto_Safety_006.py - 功能安全

### 3.3 阶段三：集成与优化 (1 周)

**Week 6:**
- [ ] 集成所有新测试套件
- [ ] 完善报告模板
- [ ] 添加配置管理
- [ ] 编写使用文档
- [ ] 执行端到端测试

---

## 四、配置示例

### 4.1 车规定义文件

```yaml
# config/automotive_profiles.yaml

# 温度等级定义
temperature_grades:
  grade_0:
    name: "Grade 0 (Engine)"
    operating_min: -40
    operating_max: 150
    storage_min: -55
    storage_max: 150
    
  grade_1:
    name: "Grade 1 (Engine Near)"
    operating_min: -40
    operating_max: 125
    storage_min: -55
    storage_max: 150
    
  grade_2:
    name: "Grade 2 (Cabin)"
    operating_min: -40
    operating_max: 105
    storage_min: -55
    storage_max: 150
    
  grade_3:
    name: "Grade 3 (Infotainment)"
    operating_min: -40
    operating_max: 85
    storage_min: -55
    storage_max: 150

# 测试场景定义
test_scenarios:
  autonomous_driving:
    name: "Autonomous Driving"
    priority: "ASIL-D"
    bandwidth_requirement: 2000  # MB/s
    latency_requirement: 50      # ms
    capacity_requirement: 512    # GB
    tests:
      - t_perf_SeqWriteBurst_002
      - t_perf_QoS_007
      - t_auto_ColdStart_001
      - t_rel_PowerLoss_003
      
  infotainment:
    name: "Infotainment System"
    priority: "ASIL-B"
    bandwidth_requirement: 500   # MB/s
    latency_requirement: 100     # ms
    capacity_requirement: 256    # GB
    tests:
      - t_perf_RandReadBurst_003
      - t_perf_Startup_009
      - t_compat_F2FS_002
      - t_compat_MultiApp_004

# 通过阈值
pass_thresholds:
  performance:
    seq_read_bw_min: 2000    # MB/s
    seq_write_bw_min: 1200   # MB/s
    rand_read_iops_min: 200000
    rand_write_iops_min: 180000
    read_latency_p99_max: 500  # μs
    write_latency_p99_max: 1000  # μs
    
  reliability:
    temp_cycles: 1000
    power_cycles: 10000
    performance_degradation_max: 0.10  # 10%
    
  automotive:
    cold_start_time_max: 2000  # ms
    hot_start_time_max: 500    # ms
    high_temp_operation_hours: 500
    low_temp_operation_hours: 500
```

### 4.2 测试执行配置

```yaml
# config/test_profiles.yaml

# 快速测试配置 (开发用)
quick_test:
  description: "Quick sanity check"
  timeout: 300  # 5 分钟
  suites:
    - performance
  tests:
    - t_perf_SeqReadBurst_001
    - t_perf_SeqWriteBurst_002
  device: "/dev/ufs0"
  parallel: false

# 完整性能测试配置
full_performance:
  description: "Complete performance characterization"
  timeout: 7200  # 2 小时
  suites:
    - performance
  device: "/dev/ufs0"
  parallel: true
  max_workers: 4
  
# 可靠性测试配置
reliability_test:
  description: "Reliability stress test"
  timeout: 86400  # 24 小时
  suites:
    - reliability
  device: "/dev/ufs0"
  parallel: false
  temperature_chamber:
    enabled: true
    port: "/dev/ttyUSB0"
    
# 车规定义测试配置
automotive_qualification:
  description: "Automotive qualification test"
  timeout: 604800  # 7 天
  suites:
    - automotive
    - reliability
  device: "/dev/ufs0"
  parallel: false
  profile: "grade_2"
  temperature_chamber:
    enabled: true
    port: "/dev/ttyUSB0"
  power_supply:
    enabled: true
    port: "/dev/ttyUSB1"
```

---

## 五、使用示例

### 5.1 命令行使用

```bash
# 快速测试
python3 bin/SysTest run --test=t_perf_SeqReadBurst_001 --device=/dev/ufs0

# 运行整个性能套件
python3 bin/SysTest run --suite=performance --device=/dev/ufs0

# 运行车规测试 (带温度控制)
python3 bin/SysTest run --suite=automotive \
    --device=/dev/ufs0 \
    --config=config/test_profiles.yaml:automotive_qualification

# 并行执行多个测试
python3 bin/SysTest run --tests=t_perf_SeqReadBurst_001,t_perf_SeqWriteBurst_002 \
    --device=/dev/ufs0 \
    --parallel=4

# 带超时的测试
python3 bin/SysTest run --suite=reliability \
    --device=/dev/ufs0 \
    --timeout=3600

# 查看可用测试
python3 bin/SysTest list

# 生成报告
python3 bin/SysTest report --latest --format=html
```

### 5.2 Python API 使用

```python
from systest.core.runner import TestRunner
from systest.tools.ufs_device import LinuxUFSDevice
from systest.tools.temperature_chamber import TemperatureChamber

# 初始化设备
ufs = LinuxUFSDevice('/dev/ufs0')
chamber = TemperatureChamber('/dev/ttyUSB0')

# 运行温度循环测试
runner = TestRunner()
runner.set_timeout(3600)

result = runner.run_test(
    test_id='t_rel_TempCycle_001',
    device=ufs,
    params={
        'temp_low': -40,
        'temp_high': 105,
        'cycles': 100,
        'chamber': chamber
    }
)

print(f"Test status: {result['status']}")
print(f"Performance degradation: {result['degradation']*100:.1f}%")
```

---

## 六、验证计划

### 6.1 框架验证

- [ ] 单元测试覆盖率 > 80%
- [ ] 集成测试通过
- [ ] 端到端测试通过
- [ ] 性能测试 (框架自身开销 < 5%)

### 6.2 测试用例验证

- [ ] 所有新测试用例在参考设备上通过
- [ ] 测试结果可重复 (3 次运行偏差 < 5%)
- [ ] 报告生成正确
- [ ] 错误处理正确

### 6.3 文档验证

- [ ] 用户文档完整
- [ ] API 文档完整
- [ ] 示例代码可运行
- [ ] FAQ 覆盖常见问题

---

*版本：0.1*
*创建时间：2026-04-09*
*状态：计划 - 待执行*
