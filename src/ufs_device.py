#!/usr/bin/env python3
"""
UFS 3.1 设备硬件抽象层
实现UFS设备的基础操作接口，遵循JEDEC UFS 3.1标准
"""

import os
import fcntl
import struct
import time
import logging
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import IntEnum

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# UFS IOCTL 命令 (Linux UFS驱动定义)
UFS_IOCTL_MAGIC = 0xCF
UFS_IOCTL_QUERY_DESC = _IOWR(UFS_IOCTL_MAGIC, 1, "struct ufs_ioctl_query_desc")
UFS_IOCTL_QUERY_ATTR = _IOWR(UFS_IOCTL_MAGIC, 2, "struct ufs_ioctl_query_attr")
UFS_IOCTL_QUERY_FLAG = _IOWR(UFS_IOCTL_MAGIC, 3, "struct ufs_ioctl_query_flag")
UFS_IOCTL_SEND_COMMAND = _IOWR(UFS_IOCTL_MAGIC, 4, "struct ufs_ioctl_command")

# UFS 描述符类型
class UfsDescType(IntEnum):
    DEVICE = 0x00
    CONFIGURATION = 0x01
    UNIT = 0x02
    INTERCONNECT = 0x03
    STRING = 0x04
    GEOMETRY = 0x05
    POWER = 0x06

# UFS 属性ID
class UfsAttrId(IntEnum):
    bBootLunEn = 0x00
    bCurrentPowerMode = 0x01
    bActiveICCLevel = 0x02
    wPeriodicRTCUpdate = 0x03
    bRefClkFreq = 0x04
    bConfigDescrLock = 0x05
    bMaxNumOfRTT = 0x06
    wExceptionEventControl = 0x07
    wExceptionEventStatus = 0x08
    dTotalAddrSpaceUnits = 0x09
    wAvailableAddrSpaceUnits = 0x0A
    bContextConf = 0x0B
    bDeviceInfoLevel = 0x0C
    bDeviceInfo = 0x0D
    wDeviceCapabilities = 0x0E
    wDeviceFeatures = 0x0F

# UFS 标志ID
class UfsFlagId(IntEnum):
    fDeviceInit = 0x00
    fPermanentWPEn = 0x01
    fPowerOnWPEn = 0x02
    fBackgroundOpsEn = 0x03
    fPurgeEnable = 0x04
    fPhyResourceRemoval = 0x05
    fBusyRTC = 0x06
    fDeviceFatal = 0x07
    fPermanentWP = 0x08
    fPowerOnWP = 0x09
    fLogicalBlockSize = 0x0A
    fWriteBoosterEn = 0x0B
    fWriteBoosterBufFlushEn = 0x0C

# UFS 命令操作码
class UfsOpcode(IntEnum):
    NOP = 0x00
    WRITE = 0x01
    READ = 0x02
    ERASE = 0x03
    WRITE_BUFFER = 0x04
    READ_BUFFER = 0x05
    SYNCHRONIZE_CACHE = 0x06
    UNMAP = 0x07
    GET_LBA_STATUS = 0x08
    SECURITY_PROTOCOL_IN = 0x09
    SECURITY_PROTOCOL_OUT = 0x0A
    PERSISTENT_RESERVE_IN = 0x0B
    PERSISTENT_RESERVE_OUT = 0x0C
    FORMAT_UNIT = 0x0D

# UFS 电源模式
class UfsPowerMode(IntEnum):
    ACTIVE = 0x00
    SLEEP = 0x01
    POWERDOWN = 0x02
    HIBERN8 = 0x03

@dataclass
class UfsDeviceInfo:
    """UFS设备信息结构"""
    manufacturer_id: int
    product_name: str
    serial_number: str
    firmware_version: str
    spec_version: str
    total_capacity: int  # 字节
    max_lun: int
    supported_gear: List[int]
    supported_lanes: int
    write_booster_supported: bool
    hpb_supported: bool
    rpmb_supported: bool
    health_status: int
    temperature: int

@dataclass
class UfsCommandResult:
    """UFS命令执行结果"""
    success: bool
    status: int
    response: bytes
    duration: float
    error_message: Optional[str] = None

def _IOC(dir: int, type: int, nr: int, size: int) -> int:
    """构造IOCTL命令"""
    return (dir << 30) | (type << 8) | (nr << 0) | (size << 16)

def _IOWR(type: int, nr: int, size: str) -> int:
    """构造读写IOCTL命令"""
    return _IOC(3, type, nr, struct.calcsize(size))

class UfsDevice:
    """
    UFS设备硬件抽象类
    提供对UFS设备的底层操作接口
    """
    
    def __init__(self, device_path: str = "/dev/ufs0"):
        """
        初始化UFS设备
        :param device_path: UFS设备节点路径
        """
        self.device_path = device_path
        self.fd: Optional[int] = None
        self.device_info: Optional[UfsDeviceInfo] = None
        self.is_open = False
        
    def open(self) -> bool:
        """
        打开UFS设备节点
        :return: 打开成功返回True，失败返回False
        """
        try:
            if self.fd is not None:
                self.close()
                
            self.fd = os.open(self.device_path, os.O_RDWR | os.O_SYNC)
            self.is_open = True
            logger.info(f"成功打开UFS设备: {self.device_path}")
            
            # 读取设备基本信息
            self.device_info = self._read_device_info()
            return True
            
        except Exception as e:
            logger.error(f"打开UFS设备失败: {str(e)}")
            self.is_open = False
            return False
            
    def close(self) -> None:
        """关闭UFS设备节点"""
        if self.fd is not None:
            try:
                os.close(self.fd)
            except:
                pass
            self.fd = None
            self.is_open = False
            logger.info(f"已关闭UFS设备: {self.device_path}")
            
    def __enter__(self):
        self.open()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        
    def _read_device_info(self) -> UfsDeviceInfo:
        """
        读取UFS设备基本信息
        :return: UfsDeviceInfo对象
        """
        # 读取设备描述符
        device_desc = self.query_descriptor(UfsDescType.DEVICE, 0, 0)
        geom_desc = self.query_descriptor(UfsDescType.GEOMETRY, 0, 0)
        power_desc = self.query_descriptor(UfsDescType.POWER, 0, 0)
        
        # 解析设备描述符
        manufacturer_id = struct.unpack_from("<B", device_desc, 0)[0]
        product_name = struct.unpack_from("<16s", device_desc, 16)[0].decode('ascii').strip('\x00')
        serial_number = struct.unpack_from("<16s", device_desc, 32)[0].decode('ascii').strip('\x00')
        firmware_version = struct.unpack_from("<8s", device_desc, 48)[0].decode('ascii').strip('\x00')
        spec_major = struct.unpack_from("<B", device_desc, 5)[0] >> 4
        spec_minor = struct.unpack_from("<B", device_desc, 5)[0] & 0x0F
        spec_version = f"{spec_major}.{spec_minor}"
        
        # 解析几何描述符
        total_capacity = struct.unpack_from("<Q", geom_desc, 40)[0] * 512  # 转换为字节
        max_lun = struct.unpack_from("<B", geom_desc, 5)[0]
        supported_gear = []
        gear_support = struct.unpack_from("<B", geom_desc, 6)[0]
        if gear_support & 0x01:
            supported_gear.append(1)
        if gear_support & 0x02:
            supported_gear.append(2)
        if gear_support & 0x04:
            supported_gear.append(3)
        if gear_support & 0x08:
            supported_gear.append(4)
        supported_lanes = struct.unpack_from("<B", geom_desc, 7)[0]
        
        # 解析特性支持
        features = struct.unpack_from("<H", device_desc, 56)[0]
        write_booster_supported = (features & 0x0001) != 0
        hpb_supported = (features & 0x0002) != 0
        rpmb_supported = (features & 0x0004) != 0
        
        # 读取健康状态和温度
        try:
            health_status = self.query_attribute(UfsAttrId.bDeviceInfo)
            temperature = struct.unpack_from("<B", self.query_descriptor(UfsDescType.DEVICE, 0, 0), 60)[0]
        except:
            health_status = 0
            temperature = 25
            
        return UfsDeviceInfo(
            manufacturer_id=manufacturer_id,
            product_name=product_name,
            serial_number=serial_number,
            firmware_version=firmware_version,
            spec_version=spec_version,
            total_capacity=total_capacity,
            max_lun=max_lun,
            supported_gear=supported_gear,
            supported_lanes=supported_lanes,
            write_booster_supported=write_booster_supported,
            hpb_supported=hpb_supported,
            rpmb_supported=rpmb_supported,
            health_status=health_status,
            temperature=temperature
        )
        
    def query_descriptor(self, desc_type: UfsDescType, lun: int, idn: int) -> bytes:
        """
        查询UFS描述符
        :param desc_type: 描述符类型
        :param lun: 逻辑单元号
        :param idn: 描述符ID
        :return: 描述符数据
        """
        if not self.is_open or self.fd is None:
            raise RuntimeError("设备未打开")
            
        # 构造查询描述符请求
        req = struct.pack("<BBBBH", desc_type, lun, idn, 0, 4096)  # 最大4KB
        buf = bytearray(4096)
        
        try:
            # 执行IOCTL命令
            result = fcntl.ioctl(self.fd, UFS_IOCTL_QUERY_DESC, req + buf)
            # 返回实际数据
            return bytes(result[6:])
        except Exception as e:
            logger.error(f"查询描述符失败 (type={desc_type}, lun={lun}, idn={idn}): {str(e)}")
            raise
            
    def query_attribute(self, attr_id: UfsAttrId, lun: int = 0) -> int:
        """
        查询UFS属性值
        :param attr_id: 属性ID
        :param lun: 逻辑单元号
        :return: 属性值
        """
        if not self.is_open or self.fd is None:
            raise RuntimeError("设备未打开")
            
        req = struct.pack("<BBBI", attr_id, lun, 0, 0)
        buf = bytearray(4)
        
        try:
            result = fcntl.ioctl(self.fd, UFS_IOCTL_QUERY_ATTR, req + buf)
            return struct.unpack_from("<I", result, 4)[0]
        except Exception as e:
            logger.error(f"查询属性失败 (attr={attr_id}, lun={lun}): {str(e)}")
            raise
            
    def set_attribute(self, attr_id: UfsAttrId, value: int, lun: int = 0) -> bool:
        """
        设置UFS属性值
        :param attr_id: 属性ID
        :param value: 属性值
        :param lun: 逻辑单元号
        :return: 设置成功返回True
        """
        if not self.is_open or self.fd is None:
            raise RuntimeError("设备未打开")
            
        req = struct.pack("<BBBI", attr_id, lun, 1, value)  # 1表示写操作
        
        try:
            fcntl.ioctl(self.fd, UFS_IOCTL_QUERY_ATTR, req)
            return True
        except Exception as e:
            logger.error(f"设置属性失败 (attr={attr_id}, value={value}, lun={lun}): {str(e)}")
            return False
            
    def query_flag(self, flag_id: UfsFlagId, lun: int = 0) -> bool:
        """
        查询UFS标志状态
        :param flag_id: 标志ID
        :param lun: 逻辑单元号
        :return: 标志状态
        """
        if not self.is_open or self.fd is None:
            raise RuntimeError("设备未打开")
            
        req = struct.pack("<BBB", flag_id, lun, 0)
        buf = bytearray(1)
        
        try:
            result = fcntl.ioctl(self.fd, UFS_IOCTL_QUERY_FLAG, req + buf)
            return struct.unpack_from("<B", result, 3)[0] == 1
        except Exception as e:
            logger.error(f"查询标志失败 (flag={flag_id}, lun={lun}): {str(e)}")
            raise
            
    def set_flag(self, flag_id: UfsFlagId, value: bool, lun: int = 0) -> bool:
        """
        设置UFS标志状态
        :param flag_id: 标志ID
        :param value: 标志值
        :param lun: 逻辑单元号
        :return: 设置成功返回True
        """
        if not self.is_open or self.fd is None:
            raise RuntimeError("设备未打开")
            
        op = 1 if value else 2  # 1=置位, 2=清除
        req = struct.pack("<BBB", flag_id, lun, op)
        
        try:
            fcntl.ioctl(self.fd, UFS_IOCTL_QUERY_FLAG, req)
            return True
        except Exception as e:
            logger.error(f"设置标志失败 (flag={flag_id}, value={value}, lun={lun}): {str(e)}")
            return False
            
    def send_command(self, opcode: UfsOpcode, lun: int = 0, lba: int = 0, 
                    transfer_len: int = 0, data: Optional[bytes] = None,
                    timeout: int = 30000) -> UfsCommandResult:
        """
        发送UFS命令到设备
        :param opcode: 命令操作码
        :param lun: 逻辑单元号
        :param lba: 逻辑块地址
        :param transfer_len: 传输长度（块数）
        :param data: 写入数据（写命令时提供）
        :param timeout: 超时时间（毫秒）
        :return: 命令执行结果
        """
        if not self.is_open or self.fd is None:
            raise RuntimeError("设备未打开")
            
        start_time = time.time()
        
        try:
            # 构造命令结构
            cmd_buf = bytearray(64)  # CDB长度
            struct.pack_into("<B", cmd_buf, 0, opcode)
            struct.pack_into("<Q", cmd_buf, 2, lba)
            struct.pack_into("<I", cmd_buf, 10, transfer_len)
            
            # 数据缓冲区
            data_buf = bytearray(transfer_len * 512) if data is None else bytearray(data)
            
            # 构造IOCTL请求
            req = struct.pack("<BBIIH64s", 
                            lun,  # lun
                            0,    # direction: 0=read, 1=write
                            transfer_len * 512,  # data_len
                            timeout,  # timeout
                            0,  # flags
                            bytes(cmd_buf))  # cdb
            
            # 执行命令
            result = fcntl.ioctl(self.fd, UFS_IOCTL_SEND_COMMAND, req + data_buf)
            
            # 解析结果
            status = struct.unpack_from("<I", result, 64 + 4 + 4 + 2)[0]
            response = bytes(result[64 + 4 + 4 + 2 + 4:])
            
            duration = time.time() - start_time
            
            return UfsCommandResult(
                success=status == 0,
                status=status,
                response=response,
                duration=duration
            )
            
        except Exception as e:
            duration = time.time() - start_time
            return UfsCommandResult(
                success=False,
                status=-1,
                response=b'',
                duration=duration,
                error_message=str(e)
            )
            
    def read_lba(self, lba: int, count: int = 1, lun: int = 0) -> Tuple[bool, bytes]:
        """
        读取逻辑块数据
        :param lba: 起始逻辑块地址
        :param count: 读取块数
        :param lun: 逻辑单元号
        :return: (成功标志, 数据)
        """
        result = self.send_command(
            opcode=UfsOpcode.READ,
            lun=lun,
            lba=lba,
            transfer_len=count
        )
        
        if result.success:
            # 从响应中提取数据
            data = result.response[:count * 512]
            return True, data
        else:
            return False, b''
            
    def write_lba(self, lba: int, data: bytes, lun: int = 0) -> Tuple[bool, float]:
        """
        写入逻辑块数据
        :param lba: 起始逻辑块地址
        :param data: 要写入的数据，长度必须是512的倍数
        :param lun: 逻辑单元号
        :return: (成功标志, 耗时秒数)
        """
        if len(data) % 512 != 0:
            raise ValueError("数据长度必须是512字节的倍数")
            
        count = len(data) // 512
        
        result = self.send_command(
            opcode=UfsOpcode.WRITE,
            lun=lun,
            lba=lba,
            transfer_len=count,
            data=data
        )
        
        return result.success, result.duration
        
    def erase_lba(self, lba: int, count: int, lun: int = 0) -> Tuple[bool, float]:
        """
        擦除逻辑块
        :param lba: 起始逻辑块地址
        :param count: 擦除块数
        :param lun: 逻辑单元号
        :return: (成功标志, 耗时秒数)
        """
        result = self.send_command(
            opcode=UfsOpcode.ERASE,
            lun=lun,
            lba=lba,
            transfer_len=count
        )
        
        return result.success, result.duration
        
    def unmap_lba(self, lba: int, count: int, lun: int = 0) -> Tuple[bool, float]:
        """
        解映射逻辑块（Trim/Unmap）
        :param lba: 起始逻辑块地址
        :param count: 解映射块数
        :param lun: 逻辑单元号
        :return: (成功标志, 耗时秒数)
        """
        result = self.send_command(
            opcode=UfsOpcode.UNMAP,
            lun=lun,
            lba=lba,
            transfer_len=count
        )
        
        return result.success, result.duration
        
    def flush_cache(self, lun: int = 0) -> bool:
        """
        刷新设备缓存
        :param lun: 逻辑单元号
        :return: 成功返回True
        """
        result = self.send_command(
            opcode=UfsOpcode.SYNCHRONIZE_CACHE,
            lun=lun
        )
        
        return result.success
        
    def get_power_mode(self) -> UfsPowerMode:
        """
        获取当前电源模式
        :return: 电源模式
        """
        mode = self.query_attribute(UfsAttrId.bCurrentPowerMode)
        return UfsPowerMode(mode)
        
    def set_power_mode(self, mode: UfsPowerMode) -> bool:
        """
        设置电源模式
        :param mode: 目标电源模式
        :return: 成功返回True
        """
        return self.set_attribute(UfsAttrId.bCurrentPowerMode, mode.value)
        
    def enable_write_booster(self, enable: bool = True) -> bool:
        """
        启用/禁用Write Booster功能
        :param enable: True启用，False禁用
        :return: 成功返回True
        """
        if not self.device_info or not self.device_info.write_booster_supported:
            logger.warning("设备不支持Write Booster功能")
            return False
            
        return self.set_flag(UfsFlagId.fWriteBoosterEn, enable)
        
    def get_health_report(self) -> Dict[str, Any]:
        """
        获取设备健康报告
        :return: 健康状态字典
        """
        if not self.device_info:
            raise RuntimeError("设备信息未初始化")
            
        # 读取实时健康参数
        try:
            device_info = self.query_attribute(UfsAttrId.bDeviceInfo)
            available_space = self.query_attribute(UfsAttrId.wAvailableAddrSpaceUnits)
            exception_status = self.query_attribute(UfsAttrId.wExceptionEventStatus)
            temperature = struct.unpack_from("<B", self.query_descriptor(UfsDescType.DEVICE, 0, 0), 60)[0]
        except:
            device_info = 0
            available_space = 0
            exception_status = 0
            temperature = 25
            
        # 计算健康度百分比（简化模型）
        health_percent = 100 - (device_info & 0x7F)
        
        # 计算剩余寿命
        total_blocks = self.device_info.total_capacity // 512
        used_blocks = total_blocks - (available_space * 512)
        life_used = (used_blocks / total_blocks) * 100
        
        return {
            "product_name": self.device_info.product_name,
            "serial_number": self.device_info.serial_number,
            "firmware_version": self.device_info.firmware_version,
            "total_capacity_gb": round(self.device_info.total_capacity / (1024**3), 2),
            "health_percent": max(0, min(100, health_percent)),
            "life_used_percent": round(life_used, 2),
            "temperature_celsius": temperature,
            "write_booster_enabled": self.query_flag(UfsFlagId.fWriteBoosterEn),
            "background_ops_enabled": self.query_flag(UfsFlagId.fBackgroundOpsEn),
            "exception_status": exception_status,
            "power_mode": self.get_power_mode().name
        }
        
    def self_test(self, short_test: bool = True) -> Dict[str, Any]:
        """
        执行设备自检
        :param short_test: True执行快速自检，False执行完整自检
        :return: 自检结果
        """
        results = {
            "test_start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "device_open": self.is_open,
            "tests": []
        }
        
        # 测试1: 设备信息读取
        try:
            info = self.get_health_report()
            results["tests"].append({
                "name": "device_info_read",
                "status": "pass",
                "message": f"成功读取设备信息: {info['product_name']}"
            })
        except Exception as e:
            results["tests"].append({
                "name": "device_info_read",
                "status": "fail",
                "message": f"读取设备信息失败: {str(e)}"
            })
            
        # 测试2: 描述符查询
        try:
            dev_desc = self.query_descriptor(UfsDescType.DEVICE, 0, 0)
            if len(dev_desc) >= 64:
                results["tests"].append({
                    "name": "descriptor_query",
                    "status": "pass",
                    "message": f"设备描述符读取成功，长度{len(dev_desc)}字节"
                })
            else:
                results["tests"].append({
                    "name": "descriptor_query",
                    "status": "fail",
                    "message": f"描述符长度过短: {len(dev_desc)}字节"
                })
        except Exception as e:
            results["tests"].append({
                "name": "descriptor_query",
                "status": "fail",
                "message": f"查询描述符失败: {str(e)}"
            })
            
        # 测试3: 基本读写测试（如果是快速测试只读写一个块）
        test_lba = 1024  # 选择一个安全的测试LBA
        test_data = b"UFS_TEST_PATTERN_" * 32  # 512字节
        
        try:
            # 写入测试
            write_ok, write_time = self.write_lba(test_lba, test_data)
            if write_ok:
                results["tests"].append({
                    "name": "write_test",
                    "status": "pass",
                    "message": f"写入成功，耗时{write_time*1000:.2f}ms，速度{512/write_time/1024/1024:.2f} MB/s"
                })
                
                # 读取验证
                read_ok, read_data = self.read_lba(test_lba, 1)
                if read_ok and read_data == test_data:
                    results["tests"].append({
                        "name": "read_verify",
                        "status": "pass",
                        "message": "读取验证成功，数据一致"
                    })
                else:
                    results["tests"].append({
                        "name": "read_verify",
                        "status": "fail",
                        "message": "读取数据与写入数据不一致"
                    })
            else:
                results["tests"].append({
                    "name": "write_test",
                    "status": "fail",
                    "message": "写入失败"
                })
        except Exception as e:
            results["tests"].append({
                "name": "io_test",
                "status": "fail",
                "message": f"IO测试失败: {str(e)}"
            })
            
        # 统计结果
        passed = sum(1 for t in results["tests"] if t["status"] == "pass")
        total = len(results["tests"])
        results["overall_result"] = "pass" if passed == total else "fail"
        results["test_summary"] = f"{passed}/{total} 测试项通过"
        
        return results
