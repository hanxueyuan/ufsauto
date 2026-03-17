#!/usr/bin/env python3
"""
测试用例：t_performance_SequentialReadSustained_002
顺序读带宽 (Sustained) 测试

测试目的:
验证 UFS 设备的顺序读带宽 Sustained 性能，评估设备在长时间连续读取下的稳定带宽，
确保满足车规级 UFS 3.1 的≥1800 MB/s 要求。

FIO 参数:
- rw: read（顺序读）
- bs: 128k（块大小）
- iodepth: 32（队列深度）
- numjobs: 1（单线程）
- runtime: 300（运行 300 秒）
- time_based: True（基于时间的测试）

验收标准:
- PASS: 平均带宽 ≥ 1800 MB/s（允许 5% 误差，即≥1710 MB/s）
- FAIL: 平均带宽 < 1710 MB/s

注意事项:
- Sustained 测试时间长（300 秒），反映设备持续性能
- 测试过程中监控设备温度，防止过热降频
- 建议重复测试 3 次取平均值
"""

import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from systest import Systest


def parse_fio_output(output):
    """解析 FIO 输出"""
    result = {"bandwidth": 0, "iops": 0, "latency_avg": 0, "latency_stddev": 0}

    bw_match = re.search(r"bw=\((\d+)/s\)", output)
    if bw_match:
        bw_str = bw_match.group(1)
        if "KiB" in bw_str:
            result["bandwidth"] = round(int(bw_str.replace("KiB", "").replace(",", "")) / 1024, 2)
        elif "MiB" in bw_str:
            result["bandwidth"] = round(float(bw_str.replace("MiB", "").replace(",", "")), 2)
        elif "GiB" in bw_str:
            result["bandwidth"] = round(float(bw_str.replace("GiB", "").replace(",", "")) * 1024, 2)

    iops_match = re.search(r"iops=(\d+)", output)
    if iops_match:
        result["iops"] = int(iops_match.group(1))

    lat_match = re.search(r"lat\s+\(.*?\):\s+avg=(\d+)", output)
    if lat_match:
        result["latency_avg"] = round(int(lat_match.group(1)) / 1000, 2)

    return result


def run_fio(device, fio_params):
    """执行 FIO 测试"""
    cmd = [
        "fio",
        f"--name=test",
        f"--filename={device}",
        f"--rw={fio_params.get('rw', 'read')}",
        f"--bs={fio_params.get('bs', '128k')}",
        f"--iodepth={fio_params.get('iodepth', 32)}",
        f"--numjobs={fio_params.get('numjobs', 1)}",
        f"--runtime={fio_params.get('runtime', 300)}",
    ]

    if fio_params.get("time_based", False):
        cmd.append("--time_based")

    cmd.append("--output-format=normal")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=fio_params.get("runtime", 300) + 60)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "FIO 执行超时"
    except Exception as e:
        return False, "", str(e)


def validate_result(parsed_result, expected_bandwidth, tolerance=0.05):
    """验证测试结果"""
    actual_bandwidth = parsed_result.get("bandwidth", 0)
    min_bandwidth = expected_bandwidth * (1 - tolerance)
    return actual_bandwidth >= min_bandwidth


def main():
    """执行测试用例"""
    kit = Systest(
        test_name="t_performance_SequentialReadSustained_002",
        device="/dev/ufs0",
        output_dir="./results/performance",
        log_dir="./logs",
    )

    fio_params = {
        "rw": "read",
        "bs": "128k",
        "iodepth": 32,
        "numjobs": 1,
        "runtime": 300,
        "time_based": True,
    }

    precondition = kit.check_precondition(mode="development")
    if not precondition.get("passed", True) and precondition.get("errors"):
        kit.fail("Precondition 检查失败，跳过测试")
        kit.report({"status": "SKIP", "reason": "Precondition 失败", "precondition": precondition})
        return 1

    kit.step("执行 FIO 测试")
    success, output, error = run_fio(kit.device, fio_params)

    if not success:
        kit.fail(f"FIO 执行失败：{error}")
        kit.report({"status": "FAIL", "reason": f"FIO 执行失败：{error}", "precondition": precondition})
        return 1

    parsed_result = parse_fio_output(output)
    kit.info(f"FIO 输出解析结果：{parsed_result}")

    expected_bandwidth = 1800
    tolerance = 0.05
    passed = validate_result(parsed_result, expected_bandwidth, tolerance)

    min_bandwidth = expected_bandwidth * (1 - tolerance)
    kit.info(f"验证结果：{parsed_result['bandwidth']} MB/s >= {min_bandwidth} MB/s → {'PASS' if passed else 'FAIL'}")

    postcondition = kit.check_postcondition(precondition)

    if postcondition.get("critical_fail", False):
        kit.fail("Postcondition 检查失败：坏块数量增加")
        kit.report(
            {
                "status": "FAIL",
                "reason": "Postcondition 检查失败：坏块数量增加",
                "metrics": parsed_result,
                "precondition": precondition,
                "postcondition": postcondition,
            }
        )
        return 1

    status = "PASS" if passed else "FAIL"
    kit.report(
        {
            "status": status,
            "metrics": parsed_result,
            "precondition": precondition,
            "postcondition": postcondition,
        }
    )

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
