# UFS 3.1 车规项目 C 语言编码规范

## 1. 总则
- 符合 MISRA C:2012 编码规范
- 符合 ISO 26262 ASIL B 功能安全要求
- 代码必须可预测、可测试、可维护
- 禁止使用会导致未定义行为的语法

## 2. 基本规则
### 2.1 语言特性限制
- ✅ 允许使用：C11 标准子集
- ❌ 禁止使用：
  - 递归调用
  - 动态内存分配（malloc/free）
  - goto 语句（错误处理场景除外）
  - 变长数组（VLA）
  - 联合体（union）（类型双关场景除外）
  - 位域（bit-field）（硬件寄存器操作除外）
  - 隐式类型转换
  - 三目运算符（复杂场景）
  - 宏定义中的 # 和 ## 运算符

### 2.2 类型要求
- 使用标准整数类型：uint8_t, int8_t, uint16_t, int16_t, uint32_t, int32_t, uint64_t, int64_t
- 禁止使用 char 类型存储数值，仅用于存储字符
- 枚举类型必须显式指定底层类型
- 指针类型必须明确指向的类型，禁止使用 void* 除非必要

## 3. 命名规范
- **文件名**：小写字母 + 下划线，如 `ufs_core.c`, `ufs_regs.h`
- **函数名**：小驼峰式，前缀为模块名，如 `ufsReadSector()`, `ufsSendCommand()`
- **变量名**：小驼峰式，见名知意，如 `sectorCount`, `transferLen`
- **宏定义**：大写字母 + 下划线，如 `UFS_SECTOR_SIZE`, `MAX_TRANSFER_LEN`
- **常量**：大写字母 + 下划线，如 `UFS_CMD_SCSI_READ`, `UFS_STATUS_SUCCESS`
- **类型定义**：后缀为 _t，如 `ufsCommand_t`, `ufsDevice_t`
- **枚举值**：前缀为模块名，大写字母 + 下划线，如 `UFS_STATE_IDLE`, `UFS_STATE_ACTIVE`

## 4. 格式规范
- 缩进：4 个空格，禁止使用制表符
- 行宽：最大 120 个字符
- 大括号：独占一行
- 运算符前后留空格
- 逗号后面留空格
- 指针星号靠近变量名：`uint8_t *buf` 而不是 `uint8_t* buf`

示例：
```c
int32_t ufsReadSector(ufsDevice_t *dev, uint32_t lba, uint8_t *buf, uint32_t sectorCount)
{
    if (dev == NULL || buf == NULL || sectorCount == 0)
    {
        return UFS_STATUS_INVALID_PARAM;
    }

    if (sectorCount > MAX_SECTOR_PER_TRANSFER)
    {
        sectorCount = MAX_SECTOR_PER_TRANSFER;
    }

    // 执行读取操作
    uint32_t transferLen = sectorCount * UFS_SECTOR_SIZE;
    return ufsDoTransfer(dev, UFS_CMD_READ, lba, buf, transferLen);
}
```

## 5. 注释规范
- 函数头注释：说明功能、参数、返回值、注意事项
- 复杂算法必须注释说明逻辑
- 关键变量注释说明含义和取值范围
- 硬件操作必须注释说明寄存器含义
- 禁止无用注释，禁止注释掉的代码提交

函数头示例：
```c
/**
 * @brief 读取UFS设备扇区
 * @param dev UFS设备句柄
 * @param lba 起始逻辑块地址
 * @param buf 数据缓冲区指针
 * @param sectorCount 要读取的扇区数量
 * @return 状态码
 *         UFS_STATUS_SUCCESS - 读取成功
 *         UFS_STATUS_INVALID_PARAM - 参数无效
 *         UFS_STATUS_TRANSFER_ERROR - 传输错误
 * @note 最大支持单次读取256个扇区
 */
int32_t ufsReadSector(ufsDevice_t *dev, uint32_t lba, uint8_t *buf, uint32_t sectorCount);
```

## 6. 内存安全
- 所有数组访问必须做边界检查
- 所有指针使用前必须判空
- 内存拷贝必须使用安全函数：memcpy_s, strncpy_s
- 禁止使用 strcpy, strcat 等不安全函数
- 栈深度不能超过 2KB
- 全局变量必须初始化

## 7. 错误处理
- 所有函数返回值必须检查
- 错误码必须明确，禁止使用 magic number
- 错误路径必须释放已分配的资源
- 硬件错误必须有恢复机制
- 关键操作必须有超时机制

## 8. 硬件操作
- 寄存器访问必须使用 volatile 修饰
- 硬件寄存器操作必须有读写屏障
- 中断处理函数必须尽可能短
- DMA 操作必须保证内存对齐
- 缓存操作必须符合 ARM 架构规范

## 9. 可测试性要求
- 所有外部函数必须可单元测试
- 硬件相关代码必须有抽象层
- 关键路径必须有测试点
- 错误注入点必须明确
- 调试信息必须可配置关闭

## 10. MISRA 强制规则摘要
- 规则 8.1：函数必须有原型声明
- 规则 8.13：指针参数如果是输入，应该声明为指向 const
- 规则 9.1：所有变量必须初始化
- 规则 10.1：隐式类型转换只能在非常有限的情况下使用
- 规则 11.8：禁止释放不是动态分配的内存
- 规则 12.1：表达式的值在其求值顺序下必须相同
- 规则 14.3：for 循环的控制变量必须在循环体内修改
- 规则 15.5：函数只能有一个退出点（错误处理场景除外）
- 规则 17.6：函数的参数数量不能超过 4 个
- 规则 17.8：函数参数永远不应该修改
