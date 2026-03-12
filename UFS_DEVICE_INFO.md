# UFS 设备和环境信息确认

## 📊 硬件信息
| 项 | 配置 | 说明 |
|-----|------|------|
| UFS 设备 | `/dev/sda` | 238.2GB（实际可用128GB为用户分区） |
| 其他存储设备 | `/dev/sdb`(32M), `/dev/sdc`(32M) | 系统存储，非测试对象 |
| 内核驱动 | `ufshcd-hobot` | 地平线定制的 UFS 主机控制器驱动 |
| UFS 特性 | 支持 Trim、Write Booster 等 UFS 3.1 特性 | 从内核日志确认 |

## 🔧 系统环境确认
| 项 | 配置 |
|-----|------|
| 系统 | Debian 12 (Bookworm) aarch64 |
| 内核 | Linux 6.1.112-rt43 |
| 测试路径 | `/mapdata/ufs_test/`（36GB可用，ext4） |
| 软件源 | 官方 Debian 源，支持 apt 安装所有需要的工具 |
| 网络 | 可访问外网，IP: 192.168.195.3 |

## ✅ 环境准备命令
```bash
# 1. 安装所有需要的测试工具
apt update && apt install -y fio stress-ng ufs-utils python3 python3-pip mdadm parted util-linux

# 2. 安装 Python 依赖
pip3 install pytest pytest-html

# 3. 创建测试目录
mkdir -p /mapdata/ufs_test
chmod 777 /mapdata/ufs_test

# 4. 验证环境
cd /mapdata/ufs_test
fio --version
stress-ng --version
python3 --version
```

## 📋 测试脚本开发优先级
1. **基础环境检查脚本** - 自动检查系统环境、工具安装情况、测试目录可用空间
2. **基础功能测试脚本** - 文件读写、拷贝、删除、并发操作等测试
3. **性能测试脚本** - fio 自动化测试，自动生成性能报告
4. **可靠性测试脚本** - 压力测试、数据完整性测试、异常场景测试
5. **一键测试框架** - 统一入口，自动执行所有测试并生成报告

所有脚本都将适配当前环境，无需额外配置，上传即可运行。
