#!/usr/bin/env python3
"""
测试用例：t_performance_MixedRw_009
混合读写性能测试

测试目的:
验证 UFS 设备的性能，确保满足车规级要求。

FIO 参数:
- rw: randrw
- bs: 128k
- iodepth: 32
- numjobs: 1
- runtime: 300

验收标准:
- PASS: ≥ 1000 MB/s
- FAIL: < 950.0 MB/s

注意事项:
- 70% 读 30% 写模拟真实负载
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
    result = {"bandwidth": 0, "iops": 0, "latency_avg": 0}

    bw_match = re.search(r"bw=\((\d+)/s\)", output)
    if bw_match:
        bw_str = bw_match.group(1)
        if "KiB" in bw_str:
            result["bandwidth"] = round(int(bw_str.replace("KiB", "").replace(",", "")) / 1024, 2)
        elif "MiB" in bw_str:
            result["bandwidth"] = round(float(bw_str.replace("MiB", "").replace(",", "")), 2)

    iops_match = re.search(r"iops=(\d+)", output)
    if iops_match:
        result["iops"] = int(iops_match.group(1))

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
        f"--runtime={fio_params.get('runtime', 60)}",
    ]

    if fio_params.get("time_based", False):
        cmd.append("--time_based")

    cmd.append("--output-format=normal")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=fio_params.get("runtime", 60) + 60)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def validate_result(parsed_result, expected, tolerance=0.05):
    """验证测试结果"""
    if "MB/s" == "KIOPS":
        actual = parsed_result.get("iops", 0) / 1000
    else:
        actual = parsed_result.get("bandwidth", 0)
    min_val = expected * (1 - tolerance)
    return actual >= min_val


def main():
    """执行测试用例"""
    kit = Systest(
        test_name="t_performance_MixedRw_009",
        device="/dev/ufs0",
        output_dir="./results/performance",
        log_dir="./logs",
    )

    fio_params = {
        "rw": "randrw",
        "bs": "128k",
        "iodepth": 32,
        "numjobs": 1,
        "runtime": 300,
        "time_based": True,
    }

    precondition = kit.check_precondition(mode="development")
    if not precondition.get("passed", True) and precondition.get("errors"):
        kit.fail("Precondition 检查失败")
        kit.report({"status": "SKIP", "reason": "Precondition 失败"})
        return 1

    kit.step("执行 FIO 测试")
    success, output, error = run_fio(kit.device, fio_params)

    if not success:
        kit.fail(f"FIO 执行失败：{error}")
        kit.report({"status": "FAIL", "reason": error})
        return 1

    parsed_result = parse_fio_output(output)

    expected = 1000
    passed = validate_result(parsed_result, expected)

    postcondition = kit.check_postcondition(precondition)

    if postcondition.get("critical_fail", False):
        kit.fail("Postcondition 检查失败：坏块增加")
        return 1

    status = "PASS" if passed else "FAIL"
    kit.report({"status": status, "metrics": parsed_result})
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
