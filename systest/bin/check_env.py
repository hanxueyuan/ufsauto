#!/usr/bin/env python3
"""
环境检查脚本 - 验证 CI/CD 环境与开发板环境一致性

使用方法:
    python3 bin/SysTest check-env
    python3 bin/SysTest check-env --report
"""

import sys
import os
import json
import subprocess
import platform
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 不使用自定义 Logger，直接用 print

# 环境要求配置
ENV_REQUIREMENTS = {
    "python_min_version": (3, 10),
    "fio_min_version": "3.30",
    "kernel_min_version": (5, 10),
    "required_packages": ["sg3-utils", "hdparm"],
    "required_modules": ["ufshcd"],
    "required_groups": ["disk"],
}

# 开发板环境基线（需要根据实际开发板更新）
BASELINE = {
    "kernel_version": "5.15.0",
    "fio_version": "3.33",
    "python_version": "3.10.12",
    "ubuntu_version": "22.04",
}


class EnvironmentChecker:
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "checks": [],
            "passed": True,
            "warnings": [],
            "errors": [],
        }

    def log_check(self, name, passed, details="", critical=False):
        """记录检查结果"""
        check = {
            "name": name,
            "passed": passed,
            "details": details,
            "critical": critical,
        }
        self.results["checks"].append(check)

        if not passed:
            if critical:
                self.results["errors"].append(f"{name}: {details}")
                self.results["passed"] = False
            else:
                self.results["warnings"].append(f"{name}: {details}")

        if self.verbose:
            status = "✅" if passed else "❌"
            print(f"{status} {name}: {details}")

    def check_python_version(self):
        """检查 Python 版本"""
        current = sys.version_info[:2]
        required = ENV_REQUIREMENTS["python_min_version"]
        baseline = BASELINE["python_version"]

        passed = current >= required
        details = (
            f"当前：{sys.version.split()[0]}, "
            f"要求：≥{'.'.join(map(str, required))}, "
            f"基线：{baseline}"
        )
        self.log_check("Python 版本", passed, details, critical=True)

    def check_fio_version(self):
        """检查 FIO 版本"""
        try:
            result = subprocess.run(
                ["fio", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            # 解析版本号 (e.g., "fio-3.33")
            version_str = result.stdout.strip()
            version = version_str.replace("fio-", "")
            major_minor = tuple(map(int, version.split(".")[:2]))

            required = tuple(map(int, ENV_REQUIREMENTS["fio_min_version"].split(".")))
            baseline = BASELINE["fio_version"]

            passed = major_minor >= required
            details = f"当前：{version}, 要求：≥{ENV_REQUIREMENTS['fio_min_version']}, 基线：{baseline}"
        except FileNotFoundError:
            passed = False
            details = "fio 未安装"
        except Exception as e:
            passed = False
            details = f"检查失败：{str(e)}"

        self.log_check("FIO 版本", passed, details, critical=True)

    def check_kernel_version(self):
        """检查 Linux 内核版本"""
        try:
            version_str = platform.release()
            # 解析版本 (e.g., "5.15.0-76-generic")
            parts = version_str.split(".")
            major = int(parts[0])
            minor = int(parts[1].split("-")[0])
            current = (major, minor)

            required = ENV_REQUIREMENTS["kernel_min_version"]
            baseline = BASELINE["kernel_version"]

            passed = current >= required
            details = (
                f"当前：{version_str}, "
                f"要求：≥{'.'.join(map(str, required))}, "
                f"基线：{baseline}"
            )
        except Exception as e:
            passed = False
            details = f"检查失败：{str(e)}"

        self.log_check("Linux 内核版本", passed, details, critical=True)

    def check_ubuntu_version(self):
        """检查 Ubuntu 版本"""
        try:
            with open("/etc/os-release") as f:
                content = f.read()
                for line in content.split("\n"):
                    if line.startswith("VERSION="):
                        version = line.split("=")[1].strip('"')
                        passed = "22.04" in version or "20.04" in version
                        baseline = BASELINE["ubuntu_version"]
                        details = f"当前：{version}, 基线：{baseline}"
                        self.log_check("Ubuntu 版本", passed, details, critical=False)
                        return
            self.log_check("Ubuntu 版本", False, "无法检测版本", critical=False)
        except Exception as e:
            self.log_check("Ubuntu 版本", False, f"检查失败：{str(e)}", critical=False)

    def check_required_packages(self):
        """检查必需的系统包"""
        for pkg in ENV_REQUIREMENTS["required_packages"]:
            try:
                result = subprocess.run(
                    ["dpkg", "-l", pkg],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                passed = result.returncode == 0 and pkg in result.stdout
                details = f"{pkg}: {'已安装' if passed else '未安装'}"
            except Exception as e:
                passed = False
                details = f"检查失败：{str(e)}"

            self.log_check(f"系统包：{pkg}", passed, details, critical=False)

    def check_kernel_modules(self):
        """检查必需的 Kernel 模块"""
        try:
            result = subprocess.run(
                ["lsmod"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            modules = result.stdout

            for mod in ENV_REQUIREMENTS["required_modules"]:
                passed = mod in modules
                details = f"{mod}: {'已加载' if passed else '未加载'}"
                self.log_check(f"Kernel 模块：{mod}", passed, details, critical=False)
        except Exception as e:
            self.log_check("Kernel 模块", False, f"检查失败：{str(e)}", critical=False)

    def check_user_groups(self):
        """检查用户组权限"""
        try:
            import grp
            import pwd

            user = pwd.getpwuid(os.getuid()).pw_name
            groups = [g.gr_name for g in grp.getgrall() if user in g.gr_mem]

            has_disk = "disk" in groups
            is_root = os.getuid() == 0

            passed = has_disk or is_root
            details = (
                f"用户：{user}, 组：{', '.join(groups)}, "
                f"disk 组：{'✓' if has_disk else '✗'}, "
                f"root: {'✓' if is_root else '✗'}"
            )
        except Exception as e:
            passed = False
            details = f"检查失败：{str(e)}"

        self.log_check("用户权限", passed, details, critical=True)

    def check_device_access(self):
        """检查 UFS 设备访问权限"""
        devices = ["/dev/ufs0", "/dev/sda", "/dev/nvme0n1"]
        found = False

        for device in devices:
            if os.path.exists(device):
                found = True
                try:
                    # 检查读写权限
                    if os.access(device, os.R_OK | os.W_OK):
                        details = f"{device}: 可读写"
                        passed = True
                    else:
                        details = f"{device}: 权限不足"
                        passed = False
                except Exception as e:
                    details = f"{device}: {str(e)}"
                    passed = False
                break

        if not found:
            details = "未找到 UFS/存储设备 (CI 环境可能正常)"
            passed = True  # CI 环境可能没有实际设备

        self.log_check("设备访问", passed, details, critical=False)

    def check_fio_permissions(self):
        """检查 FIO 运行权限"""
        try:
            # 尝试运行 fio --minimal 测试权限
            result = subprocess.run(
                ["fio", "--minimal", "--name=test", "--rw=read", "--size=1M"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            passed = result.returncode == 0
            details = "FIO 可正常运行" if passed else f"FIO 运行失败：{result.stderr[:100]}"
        except Exception as e:
            passed = False
            details = f"检查失败：{str(e)}"

        self.log_check("FIO 权限", passed, details, critical=True)

    def run_all_checks(self):
        """运行所有检查"""
        print("=" * 60)
        print("UFS SysTest 环境检查")
        print("=" * 60)
        print()

        self.check_python_version()
        self.check_fio_version()
        self.check_kernel_version()
        self.check_ubuntu_version()
        self.check_required_packages()
        self.check_kernel_modules()
        self.check_user_groups()
        self.check_device_access()
        self.check_fio_permissions()

        print()
        print("=" * 60)

        # 总结
        total = len(self.results["checks"])
        passed = sum(1 for c in self.results["checks"] if c["passed"])
        warnings = len(self.results["warnings"])
        errors = len(self.results["errors"])

        print(f"总计：{total} 项检查")
        print(f"通过：{passed}/{total}")
        print(f"警告：{warnings}")
        print(f"错误：{errors}")
        print()

        if self.results["passed"]:
            print("✅ 环境检查通过")
        else:
            print("❌ 环境检查失败，请修复以下问题:")
            for error in self.results["errors"]:
                print(f"  - {error}")

        return self.results["passed"]

    def generate_report(self, output_path="env_check_report.json"):
        """生成检查报告"""
        with open(output_path, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\n报告已保存：{output_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="环境检查工具")
    parser.add_argument(
        "--report",
        action="store_true",
        help="生成 JSON 报告",
    )
    parser.add_argument(
        "--output",
        default="env_check_report.json",
        help="报告输出路径",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="详细输出",
    )

    args = parser.parse_args()

    checker = EnvironmentChecker(verbose=args.verbose)
    passed = checker.run_all_checks()

    if args.report:
        checker.generate_report(args.output)

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
