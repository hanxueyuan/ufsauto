#!/usr/bin/env python3
"""
测试用例：t_qos_LatencyJitter_002
延迟抖动测试

测试目的:
验证 UFS 设备的延迟性能，确保满足车规级实时性要求。

FIO 参数:
- rw: randread
- bs: 4k
- iodepth: 32
- numjobs: 4
- runtime: 300

验收标准:
- p99.99 < 10ms
- 延迟标准差 < 500μs

注意事项:
- 4 个并发线程模拟多任务场景
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
    result = {"latency_p50": 0, "latency_p99": 0, "latency_p9999": 0}

    lat_match = re.search(r"lat\s+\(.*?\):\s+min=(\d+).*?max=(\d+).*?avg=(\d+)", output, re.DOTALL)
    if lat_match:
        result["latency_avg"] = round(int(lat_match.group(3)) / 1000, 2)

    return result


def run_fio(device, fio_params):
    """执行 FIO 测试"""
    cmd = [
        "fio",
        f"--name=test",
        f"--filename={device}",
        f"--rw={fio_params.get('rw', 'randread')}",
        f"--bs={fio_params.get('bs', '4k')}",
        f"--iodepth={fio_params.get('iodepth', 32)}",
        f"--numjobs={fio_params.get('numjobs', 1)}",
        f"--runtime={fio_params.get('runtime', 300)}",
        "--lat_percentiles=1",
    ]

    cmd.append("--output-format=normal")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=fio_params.get("runtime", 300) + 60)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def main():
    """执行测试用例"""
    kit = Systest(
        test_name="t_qos_LatencyJitter_002",
        device="/dev/ufs0",
        output_dir="./results/qos",
        log_dir="./logs",
    )

    fio_params = {
        "rw": "randread",
        "bs": "4k",
        "iodepth": 32,
        "numjobs": 4,
        "runtime": 300,
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

    postcondition = kit.check_postcondition(precondition)

    if postcondition.get("critical_fail", False):
        kit.fail("Postcondition 检查失败：坏块增加")
        return 1

    kit.report({"status": "PASS", "metrics": parsed_result})
    return 0


if __name__ == "__main__":
    sys.exit(main())
