"""
UFS 3.1 功能测试 - 协议命令测试
包含UFS 3.1协议规定的各种命令测试用例
"""
import pytest
from src.test_base import UFSTestBase

pytestmark = [pytest.mark.functional, pytest.mark.ufs31]

class TestUFSProtocolCommands(UFSTestBase):
    """UFS协议命令测试类"""
    
    def test_nop_command(self):
        """测试NOP命令（空操作命令）"""
        # NOP命令操作码: 0x00
        result = self.ufs.send_command(0x00)
        assert result["status"] == 0, "NOP命令执行失败"
        
    def test_inquiry_command(self):
        """测试INQUIRY命令（查询设备信息）"""
        # INQUIRY命令操作码: 0x12
        result = self.ufs.send_command(0x12, [0x00, 0x00, 0x00, 0x24, 0x00])
        assert result["status"] == 0, "INQUIRY命令执行失败"
        assert len(result["response"]) >= 36, "INQUIRY响应长度不足"
        
    def test_test_unit_ready_command(self):
        """测试TEST UNIT READY命令（测试设备就绪状态）"""
        # TEST UNIT READY命令操作码: 0x00
        result = self.ufs.send_command(0x00)
        assert result["status"] == 0, "TEST UNIT READY命令执行失败，设备未就绪"
        
    def test_request_sense_command(self):
        """测试REQUEST SENSE命令（请求感知数据）"""
        # REQUEST SENSE命令操作码: 0x03
        result = self.ufs.send_command(0x03, [0x00, 0x00, 0x00, 0x12, 0x00])
        assert result["status"] == 0, "REQUEST SENSE命令执行失败"
        assert len(result["response"]) >= 18, "REQUEST SENSE响应长度不足"
        
    def test_read_capacity_command(self):
        """测试READ CAPACITY命令（读取容量信息）"""
        # READ CAPACITY(10)命令操作码: 0x25
        result = self.ufs.send_command(0x25, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        assert result["status"] == 0, "READ CAPACITY命令执行失败"
        assert len(result["response"]) == 8, "READ CAPACITY响应长度应为8字节"
        
        # 解析容量信息
        lba_count = int.from_bytes(result["response"][0:4], byteorder='big')
        block_size = int.from_bytes(result["response"][4:8], byteorder='big')
        
        assert lba_count > 0, "LBA总数为0"
        assert block_size == 4096, f"块大小应为4096，实际为{block_size}"
        
    def test_mode_sense_command(self):
        """测试MODE SENSE命令（读取模式页）"""
        # MODE SENSE(6)命令操作码: 0x1A
        # 读取缓存模式页（页代码0x08）
        result = self.ufs.send_command(0x1A, [0x00, 0x08, 0x00, 0xFF, 0x00])
        assert result["status"] == 0, "MODE SENSE命令执行失败"
        assert len(result["response"]) >= 4, "MODE SENSE响应长度不足"
        
    def test_mode_select_command(self):
        """测试MODE SELECT命令（设置模式页）"""
        # MODE SELECT(6)命令操作码: 0x15
        # 这里只测试命令执行成功，实际设置需要根据具体模式页格式
        mode_data = bytes([0x00, 0x00, 0x00, 0x00])
        result = self.ufs.send_command(0x15, [0x00, 0x00, 0x00, len(mode_data), 0x00])
        assert result["status"] == 0, "MODE SELECT命令执行失败"
        
    def test_start_stop_unit_command(self):
        """测试START STOP UNIT命令（启动/停止设备）"""
        # START STOP UNIT命令操作码: 0x1B
        
        # 停止设备
        result = self.ufs.send_command(0x1B, [0x00, 0x00, 0x00, 0x00, 0x00])
        assert result["status"] == 0, "STOP UNIT命令执行失败"
        
        # 启动设备
        result = self.ufs.send_command(0x1B, [0x00, 0x00, 0x00, 0x01, 0x00])
        assert result["status"] == 0, "START UNIT命令执行失败"
        
    def test_sync_cache_command(self):
        """测试SYNCHRONIZE CACHE命令（同步缓存）"""
        # SYNCHRONIZE CACHE(10)命令操作码: 0x35
        result = self.ufs.send_command(0x35, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        assert result["status"] == 0, "SYNCHRONIZE CACHE命令执行失败"
        
    def test_verify_command(self):
        """测试VERIFY命令（验证数据）"""
        # VERIFY(10)命令操作码: 0x2F
        # 验证LBA 0的1个块
        result = self.ufs.send_command(0x2F, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00])
        assert result["status"] == 0, "VERIFY命令执行失败"
        
    def test_write_same_command(self):
        """测试WRITE SAME命令（写入相同数据）"""
        # WRITE SAME(10)命令操作码: 0x41
        # 向LBA 0写入10个相同的块
        result = self.ufs.send_command(0x41, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x0A, 0x00])
        assert result["status"] == 0, "WRITE SAME命令执行失败"
        
    def test_unmap_command(self):
        """测试UNMAP命令（取消映射，等同于TRIM）"""
        # UNMAP命令操作码: 0x42
        # 取消映射LBA 0-100
        unmap_data = bytes([
            0x00, 0x00, 0x00, 0x08,  # 数据描述符长度
            0x00, 0x00, 0x00, 0x00,  # LBA低32位
            0x00, 0x00, 0x00, 0x64   # 块数（100）
        ])
        result = self.ufs.send_command(0x42, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, len(unmap_data), 0x00])
        assert result["status"] == 0, "UNMAP命令执行失败"
        
    def test_get_lba_status_command(self):
        """测试GET LBA STATUS命令（获取LBA状态）"""
        # GET LBA STATUS命令操作码: 0x43
        result = self.ufs.send_command(0x43, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        assert result["status"] == 0, "GET LBA STATUS命令执行失败"
        
    def test_security_protocol_in_command(self):
        """测试SECURITY PROTOCOL IN命令（安全协议输入）"""
        # SECURITY PROTOCOL IN命令操作码: 0xA2
        # 读取安全协议信息
        result = self.ufs.send_command(0xA2, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        assert result["status"] == 0, "SECURITY PROTOCOL IN命令执行失败"
        
    def test_persistent_reserve_in_command(self):
        """测试PERSISTENT RESERVE IN命令（持久保留输入）"""
        # PERSISTENT RESERVE IN命令操作码: 0x5E
        result = self.ufs.send_command(0x5E, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        assert result["status"] == 0, "PERSISTENT RESERVE IN命令执行失败"
        
    def test_report_luns_command(self):
        """测试REPORT LUNS命令（报告逻辑单元号）"""
        # REPORT LUNS命令操作码: 0xA0
        result = self.ufs.send_command(0xA0, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        assert result["status"] == 0, "REPORT LUNS命令执行失败"
        assert len(result["response"]) >= 16, "REPORT LUNS响应长度不足"
        
    def test_format_unit_command(self):
        """测试FORMAT UNIT命令（格式化设备）"""
        # FORMAT UNIT命令操作码: 0x04
        # 注意：格式化会清除所有数据，这里使用快速格式化
        result = self.ufs.send_command(0x04, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        assert result["status"] == 0, "FORMAT UNIT命令执行失败"
        
    def test_write_buffer_command(self):
        """测试WRITE BUFFER命令（写入缓冲区）"""
        # WRITE BUFFER命令操作码: 0x3B
        # 写入数据缓冲区
        result = self.ufs.send_command(0x3B, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        assert result["status"] == 0, "WRITE BUFFER命令执行失败"
        
    def test_read_buffer_command(self):
        """测试READ BUFFER命令（读取缓冲区）"""
        # READ BUFFER命令操作码: 0x3C
        result = self.ufs.send_command(0x3C, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        assert result["status"] == 0, "READ BUFFER命令执行失败"
        
    def test_log_sense_command(self):
        """测试LOG SENSE命令（读取日志页）"""
        # LOG SENSE命令操作码: 0x4D
        # 读取支持的日志页列表
        result = self.ufs.send_command(0x4D, [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF, 0x00])
        assert result["status"] == 0, "LOG SENSE命令执行失败"
        
    def test_invalid_command_handling(self):
        """测试无效命令处理"""
        # 发送一个无效的命令操作码
        result = self.ufs.send_command(0xFF)  # 0xFF不是有效的UFS命令
        # 无效命令应该返回非零状态码
        assert result["status"] != 0, "无效命令应该返回错误状态"
