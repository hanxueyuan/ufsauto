#!/usr/bin/env python3
"""
测试用例：t_scenario_ModelLoad_002
算法模型加载测试

测试目的:
模拟 AI 模型加载和推理场景，验证 UFS 设备在大文件顺序读取和随机读取混合负载下的性能表现，
确保满足≥1500 MB/s 的读取带宽要求。



Test Steps:
1. 模拟 AI 模型加载和推理并发场景
2. 配置参数：rw=randrw, rwmixread=70, bs=128k, iodepth=16, numjobs=4, runtime=300
3. 4 个并发线程持续运行 300 秒（5 分钟）
4. 监控读取带宽和加载时间
5. 收集测试结果

验收标准:
- 读取带宽 ≥ 1500 MB/s
- 模型加载时间 < 5 秒

注意事项:
- 模拟 AI 模型权重加载 + 推理并发场景
- 70% 读 30% 写模拟真实推理负载
- 128K 块大小模拟模型文件读取
- 如果带宽不足，检查队列深度和并发数
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from runner import TestRunner


def main():
    print("=" * 80)
    print("测试用例：t_scenario_ModelLoad_002")
    print("算法模型加载测试")
    print("=" * 80)
    print()

    runner = TestRunner(
        device="/dev/ufs0", output_dir="./results/scenario", verbose=True, check_precondition=True, mode="development"
    )

    print("开始执行测试...")
    print()

    result = runner.run_test("t_scenario_ModelLoad_002")

    print()
    print("=" * 80)
    print("测试结果")
    print("=" * 80)

    status = result.get("status", "UNKNOWN")
    print("✅ PASS" if status == "PASS" else "❌ FAIL" if status == "FAIL" else f"状态：{status}")

    metrics = result.get("metrics", {})
    if metrics:
        print()
        print("测试指标:")
        bandwidth = metrics.get("bandwidth", 0)
        if bandwidth:
            print(f"  - 读取带宽：{bandwidth} MB/s")

    print()
    print("验收目标:")
    print("  - 读取带宽 ≥ 1500 MB/s")
    print("  - 模型加载时间 < 5 秒")
    print()
    print("=" * 80)

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
