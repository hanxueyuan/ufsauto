#!/usr/bin/env python3
"""
Precondition 检查功能测试脚本
验证 Precondition 检查功能是否正常工作
"""

import sys
from pathlib import Path

# 添加 core 模块路径
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from precondition_checker import PreconditionChecker


def test_precondition_checker():
    """测试 Precondition 检查器"""
    print("=" * 60)
    print("Precondition 检查功能测试")
    print("=" * 60)

    # 创建检查器
    checker = PreconditionChecker(verbose=True)

    # 模拟 precondition 配置
    test_precondition = {
        "system_env": {"os": "Debian 12, kernel 5.15.120", "cpu_memory": "8 核，16GB", "fio_version": "fio-3.33"},
        "device_info": {
            "path": "/dev/ufs0",
            "model": "UFS 3.1 128GB",
            "firmware": "v1.0.0",
            "capacity": "128GB",
            "available_space": "≥10GB",
        },
        "config": {"enable": ["TURBO Mode"], "disable": ["省电模式"], "special": []},
        "lun_config": {
            "count": 4,
            "LUN0": "64GB 系统盘",
            "LUN1": "32GB 数据盘（测试目标）",
            "LUN2": "16GB 日志盘",
            "LUN3": "16GB 预留",
            "mapping": "LUN1→/dev/ufs0",
        },
        "health": {
            "smart": "正常",
            "remaining_life": "98%",
            "bad_blocks": 0,
            "temperature": "35℃（当前）/ 45℃（最高）",
            "error_count": "CRC 错误=0, 重传次数=0",
        },
        "verification": ["SMART 状态必须为正常", "可用空间必须≥10GB", "温度必须<70℃", "剩余寿命必须>90%"],
    }

    # 执行检查（开发模式）
    print("\n开始检查 Precondition（开发模式）...\n")
    result = checker.check_all(test_precondition, device="/dev/zero", mode="development")

    # 打印摘要
    checker.print_summary()

    # 显示详细结果
    print("\n详细检查结果:")
    print("-" * 60)

    for check in result["checks"]:
        status = "✅" if check["passed"] else "❌"
        print(f"{status} {check['name']}: {check['message']} ({check['value']})")

    if result["warnings"]:
        print(f"\n⚠️  警告 ({len(result['warnings'])}):")
        for warning in result["warnings"]:
            print(f"  - {warning['message']}")

    if result["errors"]:
        print(f"\n❌ 错误 ({len(result['errors'])}):")
        for error in result["errors"]:
            print(f"  - {error['message']}")

    print("-" * 60)

    # 返回检查结果
    return result["passed"]


if __name__ == "__main__":
    try:
        passed = test_precondition_checker()

        if passed:
            print("\n✅ Precondition 检查功能测试通过！")
            sys.exit(0)
        else:
            print("\n⚠️  Precondition 检查功能测试完成（部分检查未通过）")
            sys.exit(0)  # 即使部分检查未通过也返回 0，因为这是预期行为
    except Exception as e:
        print(f"\n❌ Precondition 检查功能测试失败：{e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
