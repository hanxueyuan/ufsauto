# UFS SysTest AutoResearch Program

## 当前状态
- 分支：`autoresearch/mar22`
- 单元测试：72 通过，0 失败
- 框架：已完成设计原则对齐（5 种状态、Fail-Continue/Fail-Stop、性能测试 annotations）
- 7 个 case 已按新设计原则改造完毕

## 迭代目标

### Phase 1：测试 case 质量提升（当前阶段）
**单一指标**：case 评估评分（场景覆盖度 + 断言充分性，1-10 分）
**修改范围**：`systest/suites/**/*.py`

每轮迭代：
1. 选一个评分最低的 case
2. 分析不足（场景覆盖矩阵 + 断言清单）
3. 改进代码
4. 运行 `pytest systest/tests/ -q`
5. 全绿 → `git commit -m "keep: {描述}"`，失败 → `git reset --hard HEAD`
6. 记录到 `results.tsv`

**Phase 1 完成标准**：所有 case 评分 ≥ 6

### Phase 2：补充缺失测试类型
**单一指标**：场景矩阵覆盖率
**修改范围**：`systest/suites/` 新增 suite

缺失的测试类型：
- `functional/` — 数据读写正确性、Trim 验证、错误处理
- `endurance/` — 长时间稳态、写入放大
- `stress/` — 满盘、高并发、极端参数

每轮迭代：
1. 从场景矩阵中选最重要的缺失场景
2. 创建新 case（遵循 design_principles.md）
3. 运行测试
4. keep / discard
5. 更新场景矩阵覆盖率

### Phase 3：框架增强
**单一指标**：框架代码覆盖率（这时候才有意义——框架稳定了，提升覆盖率才有价值）
**修改范围**：`systest/core/*.py` + `systest/tests/*.py`

增强方向：
- 多次运行取中位数（repeat 支持）
- baseline 对比（历史结果回归检测）
- 参数化测试（一个 case 文件跑多种配置）
- 测试报告增强（annotations 汇总、趋势图）

## 规则

1. **每轮只改一个方向** — 不要同时改 case 和框架
2. **改完必须跑测试** — `pytest systest/tests/ -q`，全绿才能 commit
3. **没改进就回滚** — `git reset --hard HEAD`，零成本
4. **记录每一轮** — `results.tsv` 里写 commit hash、指标、状态、描述
5. **遵循 design_principles.md** — 所有改动必须符合设计原则
6. **不碰生产配置** — 只改代码和测试

## results.tsv 格式

```
round	commit	tests_pass	tests_fail	coverage	score	status	description
```
