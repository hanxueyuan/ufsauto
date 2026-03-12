#!/usr/bin/env python3
"""
UFS 3.1 测试命令行工具
提供UFS设备的测试、诊断和性能评估功能
"""

import argparse
import json
import sys
import time
import os
from typing import List, Dict, Any
from tabulate import tabulate

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ufs_device import UfsDevice, UfsPowerMode, UfsDescType, UfsAttrId, UfsFlagId

def bytes_to_human(n: int) -> str:
    """将字节转换为人类可读格式"""
    symbols = ('B', 'KB', 'MB', 'GB', 'TB', 'PB')
    prefix = {}
    for i, s in enumerate(symbols[1:]):
        prefix[s] = 1 << (i + 1) * 10
    for s in reversed(symbols[1:]):
        if n >= prefix[s]:
            value = float(n) / prefix[s]
            return '%.2f %s' % (value, s)
    return '%.2f %s' % (n, symbols[0])

def format_duration(seconds: float) -> str:
    """格式化时间"""
    if seconds < 0.001:
        return f"{seconds * 1000000:.2f} µs"
    elif seconds < 1:
        return f"{seconds * 1000:.2f} ms"
    else:
        return f"{seconds:.2f} s"

def cmd_info(args):
    """显示UFS设备基本信息"""
    with UfsDevice(args.device) as dev:
        if not dev.is_open:
            print(f"错误：无法打开设备 {args.device}", file=sys.stderr)
            return 1
            
        info = dev.device_info
        
        print("\n=== UFS 设备信息 ===")
        print(f"设备路径: {args.device}")
        print(f"制造商ID: 0x{info.manufacturer_id:02X}")
        print(f"产品名称: {info.product_name}")
        print(f"序列号: {info.serial_number}")
        print(f"固件版本: {info.firmware_version}")
        print(f"协议版本: UFS {info.spec_version}")
        print(f"总容量: {bytes_to_human(info.total_capacity)} ({info.total_capacity} 字节)")
        print(f"最大LUN数量: {info.max_lun}")
        print(f"支持的速率等级: {', '.join(map(str, info.supported_gear))}")
        print(f"支持的通道数: {info.supported_lanes}")
        print(f"Write Booster支持: {'是' if info.write_booster_supported else '否'}")
        print(f"HPB支持: {'是' if info.hpb_supported else '否'}")
        print(f"RPMB支持: {'是' if info.rpmb_supported else '否'}")
        print(f"当前温度: {info.temperature} °C")
        print(f"健康状态: {info.health_status}")
        
        # 显示当前状态
        print("\n=== 当前状态 ===")
        power_mode = dev.get_power_mode()
        print(f"电源模式: {power_mode.name}")
        print(f"Write Booster启用: {'是' if dev.query_flag(UfsFlagId.fWriteBoosterEn) else '否'}")
        print(f"后台操作启用: {'是' if dev.query_flag(UfsFlagId.fBackgroundOpsEn) else '否'}")
        print(f"设备已初始化: {'是' if dev.query_flag(UfsFlagId.fDeviceInit) else '否'}")
        
        return 0

def cmd_health(args):
    """显示设备健康报告"""
    with UfsDevice(args.device) as dev:
        if not dev.is_open:
            print(f"错误：无法打开设备 {args.device}", file=sys.stderr)
            return 1
            
        health = dev.get_health_report()
        
        print("\n=== UFS 健康报告 ===")
        print(f"设备: {health['product_name']} ({health['serial_number']})")
        print(f"固件版本: {health['firmware_version']}")
        print(f"总容量: {health['total_capacity_gb']} GB")
        print(f"健康度: {health['health_percent']}%")
        print(f"使用寿命已使用: {health['life_used_percent']}%")
        print(f"当前温度: {health['temperature_celsius']} °C")
        print(f"电源模式: {health['power_mode']}")
        print(f"Write Booster已启用: {'是' if health['write_booster_enabled'] else '否'}")
        print(f"后台操作已启用: {'是' if health['background_ops_enabled'] else '否'}")
        print(f"异常状态标志: 0x{health['exception_status']:04X}")
        
        # 温度警告
        if health['temperature_celsius'] > 85:
            print("\n⚠️  警告：设备温度过高！")
        elif health['temperature_celsius'] > 70:
            print("\nℹ️  提示：设备温度较高")
            
        # 健康度警告
        if health['health_percent'] < 30:
            print("⚠️  警告：设备健康度较低，建议备份数据！")
        elif health['health_percent'] < 70:
            print("ℹ️  提示：设备健康度中等")
            
        return 0

def cmd_selftest(args):
    """执行设备自检"""
    print(f"开始执行UFS设备{'快速' if args.short else '完整'}自检...")
    print(f"测试设备: {args.device}")
    print("=" * 50)
    
    with UfsDevice(args.device) as dev:
        if not dev.is_open:
            print(f"错误：无法打开设备 {args.device}", file=sys.stderr)
            return 1
            
        results = dev.self_test(short_test=args.short)
        
        print(f"\n测试开始时间: {results['test_start_time']}")
        print(f"整体结果: {'✅ 通过' if results['overall_result'] == 'pass' else '❌ 失败'}")
        print(f"测试总结: {results['test_summary']}")
        print("\n详细测试结果:")
        
        for test in results['tests']:
            status = "✅ PASS" if test['status'] == 'pass' else "❌ FAIL"
            print(f"  {test['name']:<25} {status} - {test['message']}")
            
        # 如果有失败项，返回错误码
        if results['overall_result'] != 'pass':
            return 1
            
        return 0

def cmd_perf(args):
    """性能测试"""
    block_size = args.block_size
    transfer_size = args.size * 1024 * 1024  # 转换为字节
    block_count = transfer_size // block_size
    
    if transfer_size % block_size != 0:
        print(f"警告：传输大小不是块大小的整数倍，将使用 {block_count * block_size} 字节", file=sys.stderr)
        
    print(f"\n=== UFS 性能测试 ===")
    print(f"设备: {args.device}")
    print(f"测试块大小: {bytes_to_human(block_size)}")
    print(f"测试传输大小: {bytes_to_human(transfer_size)}")
    print(f"测试LUN: {args.lun}")
    print(f"起始LBA: {args.lba}")
    
    with UfsDevice(args.device) as dev:
        if not dev.is_open:
            print(f"错误：无法打开设备 {args.device}", file=sys.stderr)
            return 1
            
        # 准备测试数据
        test_data = os.urandom(transfer_size)
        results = {}
        
        # 写入测试
        print("\n▶️  开始顺序写入测试...")
        start_time = time.time()
        write_ok = True
        bytes_written = 0
        
        for i in range(block_count):
            offset = i * block_size
            lba = args.lba + (i * block_size // 512)
            data = test_data[offset:offset + block_size]
            ok, _ = dev.write_lba(lba, data, lun=args.lun)
            if not ok:
                write_ok = False
                break
            bytes_written += block_size
            
        write_time = time.time() - start_time
        write_speed = bytes_written / write_time if write_time > 0 else 0
        
        if write_ok:
            results['write'] = {
                'size': bytes_written,
                'time': write_time,
                'speed': write_speed
            }
            print(f"✅ 写入完成: {bytes_to_human(bytes_written)} 在 {format_duration(write_time)} 内")
            print(f"   写入速度: {bytes_to_human(write_speed)}/s")
        else:
            print("❌ 写入测试失败")
            
        # 读取测试
        print("\n▶️  开始顺序读取测试...")
        start_time = time.time()
        read_ok = True
        bytes_read = 0
        verify_ok = True
        
        for i in range(block_count):
            offset = i * block_size
            lba = args.lba + (i * block_size // 512)
            ok, data = dev.read_lba(lba, block_size // 512, lun=args.lun)
            if not ok:
                read_ok = False
                break
            bytes_read += len(data)
            if args.verify and data != test_data[offset:offset + block_size]:
                verify_ok = False
                print(f"⚠️  数据验证失败在LBA {lba}")
                
        read_time = time.time() - start_time
        read_speed = bytes_read / read_time if read_time > 0 else 0
        
        if read_ok:
            results['read'] = {
                'size': bytes_read,
                'time': read_time,
                'speed': read_speed
            }
            print(f"✅ 读取完成: {bytes_to_human(bytes_read)} 在 {format_duration(read_time)} 内")
            print(f"   读取速度: {bytes_to_human(read_speed)}/s")
            if args.verify:
                print(f"   数据验证: {'✅ 通过' if verify_ok else '❌ 失败'}")
        else:
            print("❌ 读取测试失败")
            
        # 随机IO测试（如果指定）
        if args.random:
            print("\n▶️  开始随机4K读取测试...")
            import random
            random_lbas = [args.lba + random.randint(0, block_count * (block_size // 512)) for _ in range(1000)]
            
            start_time = time.time()
            for lba in random_lbas:
                dev.read_lba(lba, 8, lun=args.lun)  # 4K = 8 * 512
                
            random_time = time.time() - start_time
            iops = 1000 / random_time if random_time > 0 else 0
            results['random_read_4k'] = {
                'iops': iops,
                'avg_latency': random_time * 1000 / 1000
            }
            print(f"✅ 随机读取测试完成: 1000次4K读取")
            print(f"   平均IOPS: {iops:.2f}")
            print(f"   平均延迟: {random_time * 1000 / 1000:.2f} ms")
            
        # 输出结果汇总
        print("\n=== 性能测试结果汇总 ===")
        table_data = []
        if 'write' in results:
            table_data.append(["顺序写入", 
                             f"{bytes_to_human(results['write']['speed'])}/s",
                             f"{format_duration(results['write']['time'])}"])
        if 'read' in results:
            table_data.append(["顺序读取",
                             f"{bytes_to_human(results['read']['speed'])}/s",
                             f"{format_duration(results['read']['time'])}"])
        if 'random_read_4k' in results:
            table_data.append(["随机4K读取",
                             f"{results['random_read_4k']['iops']:.0f} IOPS",
                             f"{results['random_read_4k']['avg_latency']:.2f} ms"])
                             
        print(tabulate(table_data, headers=["测试项目", "性能", "耗时"], tablefmt="grid"))
        
        # 保存结果到文件（如果指定）
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"\n结果已保存到: {args.output}")
            
        return 0

def cmd_read(args):
    """读取指定LBA数据"""
    with UfsDevice(args.device) as dev:
        if not dev.is_open:
            print(f"错误：无法打开设备 {args.device}", file=sys.stderr)
            return 1
            
        print(f"读取LBA {args.lba}，共 {args.count} 块...")
        ok, data = dev.read_lba(args.lba, args.count, lun=args.lun)
        
        if not ok:
            print("读取失败", file=sys.stderr)
            return 1
            
        print(f"读取成功，共 {len(data)} 字节")
        
        # 输出格式
        if args.output:
            with open(args.output, 'wb') as f:
                f.write(data)
            print(f"数据已保存到: {args.output}")
        else:
            # 十六进制输出
            for i in range(0, len(data), 16):
                chunk = data[i:i+16]
                hex_str = ' '.join(f'{b:02X}' for b in chunk)
                ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
                print(f'{i:08X}: {hex_str:<47}  {ascii_str}')
                
        return 0

def cmd_write(args):
    """写入数据到指定LBA"""
    # 读取输入数据
    if args.input:
        with open(args.input, 'rb') as f:
            data = f.read()
    else:
        # 从标准输入读取
        data = sys.stdin.buffer.read()
        
    # 对齐到512字节
    if len(data) % 512 != 0:
        padding = b'\x00' * (512 - len(data) % 512)
        data += padding
        print(f"警告：数据长度不是512的倍数，已填充 {len(padding)} 字节", file=sys.stderr)
        
    block_count = len(data) // 512
    
    print(f"准备写入 {len(data)} 字节 ({block_count} 块) 到LBA {args.lba}...")
    
    if not args.yes:
        confirm = input("确认执行写入操作？这可能会覆盖现有数据！(y/N): ")
        if confirm.lower() != 'y':
            print("操作已取消")
            return 0
            
    with UfsDevice(args.device) as dev:
        if not dev.is_open:
            print(f"错误：无法打开设备 {args.device}", file=sys.stderr)
            return 1
            
        ok, duration = dev.write_lba(args.lba, data, lun=args.lun)
        
        if ok:
            speed = len(data) / duration if duration > 0 else 0
            print(f"✅ 写入成功！耗时 {format_duration(duration)}，速度 {bytes_to_human(speed)}/s")
            return 0
        else:
            print("❌ 写入失败", file=sys.stderr)
            return 1

def cmd_erase(args):
    """擦除指定LBA范围"""
    print(f"准备擦除LBA {args.lba} 到 {args.lba + args.count - 1}，共 {args.count} 块...")
    
    if not args.yes:
        confirm = input("确认执行擦除操作？这会永久删除数据！(y/N): ")
        if confirm.lower() != 'y':
            print("操作已取消")
            return 0
            
    with UfsDevice(args.device) as dev:
        if not dev.is_open:
            print(f"错误：无法打开设备 {args.device}", file=sys.stderr)
            return 1
            
        ok, duration = dev.erase_lba(args.lba, args.count, lun=args.lun)
        
        if ok:
            print(f"✅ 擦除成功！耗时 {format_duration(duration)}")
            return 0
        else:
            print("❌ 擦除失败", file=sys.stderr)
            return 1

def cmd_power(args):
    """电源管理命令"""
    with UfsDevice(args.device) as dev:
        if not dev.is_open:
            print(f"错误：无法打开设备 {args.device}", file=sys.stderr)
            return 1
            
        if args.mode:
            try:
                mode = UfsPowerMode[args.mode.upper()]
                ok = dev.set_power_mode(mode)
                if ok:
                    print(f"✅ 成功设置电源模式为 {mode.name}")
                else:
                    print(f"❌ 设置电源模式失败", file=sys.stderr)
                    return 1
            except KeyError:
                print(f"错误：无效的电源模式 {args.mode}，可用模式: {', '.join(m.name for m in UfsPowerMode)}", file=sys.stderr)
                return 1
        else:
            # 显示当前电源模式
            mode = dev.get_power_mode()
            print(f"当前电源模式: {mode.name}")
            
            # 显示电源相关属性
            print(f"当前ICC级别: {dev.query_attribute(UfsAttrId.bActiveICCLevel)}")
            print(f"参考时钟频率: {dev.query_attribute(UfsAttrId.bRefClkFreq)} MHz")
            
        return 0

def cmd_wb(args):
    """Write Booster管理"""
    with UfsDevice(args.device) as dev:
        if not dev.is_open:
            print(f"错误：无法打开设备 {args.device}", file=sys.stderr)
            return 1
            
        if not dev.device_info.write_booster_supported:
            print("错误：设备不支持Write Booster功能", file=sys.stderr)
            return 1
            
        if args.enable is not None:
            ok = dev.enable_write_booster(args.enable)
            if ok:
                print(f"✅ Write Booster已{'启用' if args.enable else '禁用'}")
            else:
                print(f"❌ 操作失败", file=sys.stderr)
                return 1
                
            if args.flush and args.enable:
                # 刷新Write Booster缓冲区
                ok = dev.set_flag(UfsFlagId.fWriteBoosterBufFlushEn, True)
                if ok:
                    print("✅ Write Booster缓冲区已刷新")
                else:
                    print("❌ 刷新缓冲区失败", file=sys.stderr)
                    return 1
        else:
            # 显示当前状态
            enabled = dev.query_flag(UfsFlagId.fWriteBoosterEn)
            flush_enabled = dev.query_flag(UfsFlagId.fWriteBoosterBufFlushEn)
            print(f"Write Booster功能: {'支持' if dev.device_info.write_booster_supported else '不支持'}")
            print(f"当前状态: {'已启用' if enabled else '已禁用'}")
            print(f"缓冲区自动刷新: {'已启用' if flush_enabled else '已禁用'}")
            
        return 0

def cmd_monitor(args):
    """实时监控设备状态"""
    print(f"开始监控UFS设备状态，刷新间隔 {args.interval} 秒，按Ctrl+C停止...")
    print("时间\t\t温度(°C)\t健康度(%)\t电源模式\t写入速度\t读取速度")
    
    try:
        with UfsDevice(args.device) as dev:
            if not dev.is_open:
                print(f"错误：无法打开设备 {args.device}", file=sys.stderr)
                return 1
                
            while True:
                timestamp = time.strftime("%H:%M:%S")
                health = dev.get_health_report()
                
                # 简单性能采样
                test_lba = 1024
                test_data = b'X' * 4096
                _, write_time = dev.write_lba(test_lba, test_data)
                write_speed = 4096 / write_time if write_time > 0 else 0
                _, read_data = dev.read_lba(test_lba, 8)
                read_speed = 4096 / write_time if write_time > 0 else 0
                
                print(f"{timestamp}\t{health['temperature_celsius']:>3}\t\t{health['health_percent']:>3}\t\t{health['power_mode']:<10}\t{bytes_to_human(write_speed)}/s\t{bytes_to_human(read_speed)}/s")
                
                time.sleep(args.interval)
                
    except KeyboardInterrupt:
        print("\n监控已停止")
        return 0

def main():
    parser = argparse.ArgumentParser(description='UFS 3.1 测试命令行工具')
    parser.add_argument('-d', '--device', default='/dev/ufs0', help='UFS设备路径 (默认: /dev/ufs0)')
    parser.add_argument('--json', action='store_true', help='以JSON格式输出结果')
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # info 命令
    parser_info = subparsers.add_parser('info', help='显示设备基本信息')
    parser_info.set_defaults(func=cmd_info)
    
    # health 命令
    parser_health = subparsers.add_parser('health', help='显示设备健康报告')
    parser_health.set_defaults(func=cmd_health)
    
    # selftest 命令
    parser_selftest = subparsers.add_parser('selftest', help='执行设备自检')
    parser_selftest.add_argument('--short', action='store_true', help='执行快速自检')
    parser_selftest.set_defaults(func=cmd_selftest)
    
    # perf 命令
    parser_perf = subparsers.add_parser('perf', help='性能测试')
    parser_perf.add_argument('-s', '--size', type=int, default=100, help='测试数据大小(MB) (默认: 100)')
    parser_perf.add_argument('-b', '--block-size', type=int, default=4096, help='块大小(字节) (默认: 4096)')
    parser_perf.add_argument('-l', '--lba', type=int, default=1024*1024, help='测试起始LBA (默认: 1048576)')
    parser_perf.add_argument('--lun', type=int, default=0, help='测试LUN (默认: 0)')
    parser_perf.add_argument('--random', action='store_true', help='包含随机IO测试')
    parser_perf.add_argument('--verify', action='store_true', help='读取验证')
    parser_perf.add_argument('-o', '--output', help='结果输出文件')
    parser_perf.set_defaults(func=cmd_perf)
    
    # read 命令
    parser_read = subparsers.add_parser('read', help='读取指定LBA数据')
    parser_read.add_argument('lba', type=int, help='起始LBA地址')
    parser_read.add_argument('count', type=int, nargs='?', default=1, help='读取块数 (默认: 1)')
    parser_read.add_argument('--lun', type=int, default=0, help='LUN (默认: 0)')
    parser_read.add_argument('-o', '--output', help='输出文件路径，不指定则十六进制输出到屏幕')
    parser_read.set_defaults(func=cmd_read)
    
    # write 命令
    parser_write = subparsers.add_parser('write', help='写入数据到指定LBA')
    parser_write.add_argument('lba', type=int, help='起始LBA地址')
    parser_write.add_argument('--lun', type=int, default=0, help='LUN (默认: 0)')
    parser_write.add_argument('-i', '--input', help='输入文件路径，不指定则从标准输入读取')
    parser_write.add_argument('-y', '--yes', action='store_true', help='不提示确认，直接执行')
    parser_write.set_defaults(func=cmd_write)
    
    # erase 命令
    parser_erase = subparsers.add_parser('erase', help='擦除指定LBA范围')
    parser_erase.add_argument('lba', type=int, help='起始LBA地址')
    parser_erase.add_argument('count', type=int, help='擦除块数')
    parser_erase.add_argument('--lun', type=int, default=0, help='LUN (默认: 0)')
    parser_erase.add_argument('-y', '--yes', action='store_true', help='不提示确认，直接执行')
    parser_erase.set_defaults(func=cmd_erase)
    
    # power 命令
    parser_power = subparsers.add_parser('power', help='电源管理')
    parser_power.add_argument('mode', nargs='?', choices=[m.name.lower() for m in UfsPowerMode], 
                             help='电源模式 (active, sleep, powerdown, hibern8)，不指定则显示当前模式')
    parser_power.set_defaults(func=cmd_power)
    
    # wb 命令
    parser_wb = subparsers.add_parser('wb', help='Write Booster管理')
    parser_wb.add_argument('--enable', action='store_true', default=None, help='启用Write Booster')
    parser_wb.add_argument('--disable', dest='enable', action='store_false', help='禁用Write Booster')
    parser_wb.add_argument('--flush', action='store_true', help='启用时刷新缓冲区')
    parser_wb.set_defaults(func=cmd_wb)
    
    # monitor 命令
    parser_monitor = subparsers.add_parser('monitor', help='实时监控设备状态')
    parser_monitor.add_argument('-i', '--interval', type=int, default=1, help='刷新间隔(秒) (默认: 1)')
    parser_monitor.set_defaults(func=cmd_monitor)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
        
    try:
        return args.func(args)
    except Exception as e:
        print(f"错误: {str(e)}", file=sys.stderr)
        if os.getenv('DEBUG', '0') == '1':
            import traceback
            traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
