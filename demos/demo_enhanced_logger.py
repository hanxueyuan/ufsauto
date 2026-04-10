
""" 增强版日志系统演示脚本 """

importsys

frompathlibimportPath

sys.path.insert(0,str(Path(__file__).parent/'systest'/'core'))

fromlogger_enhancedimportget_enhanced_logger,close_all_loggers

importlogging

defdemo_enhanced_logging():

    """ 演示增强版日志功能 """

print("="*80)

print("增强版日志系统演示")

print("="*80)

print()

logger=get_enhanced_logger(

test_id='demo_performance_test',

log_dir='/tmp/ufs_demo_logs',

console_level=logging.DEBUG,

file_level=logging.DEBUG,

enable_json=False

)

print("\n--- 1. 基础日志级别演示 ---\n")

logger.debug('调试信息：FIO 参数配置 - bs=128k, iodepth=1, size=1G')

logger.info('测试开始：顺序读性能测试')

logger.warning('警告：设备温度偏高 (45°C)')

print("\n--- 2. 前置条件检查演示 ---\n")

logger.precondition(

check_name='设备存在性检查',

params={'device':'/dev/sda','expected':True},

passed=True,

details='设备正常识别'

)

logger.precondition(

check_name='可用空间检查',

params={'required':'2GB','available':'50GB'},

passed=True

)

logger.precondition(

check_name='FIO 工具检查',

params={'command':'fio','min_version':'5.0'},

passed=True,

details='当前版本 5.19'

)

logger.precondition(

check_name='设备权限检查',

params={'device':'/dev/sda','readable':False,'writable':False},

passed=False,

details='权限不足，需要 root 或 disk 组成员'

)

print("\n--- 3. 测试步骤记录演示 ---\n")

logger.test_step(

step_num=1,

description='创建测试文件',

params={'size':'1GB','path':'/mapdata/ufs_test/ufs_test_seq_read','pattern':'0x00'}

)

logger.test_step(

step_num=2,

description='预填充测试文件（避免稀疏文件）',

params={'method':'dd','bs':'1M','count':1024}

)

logger.test_step(

step_num=3,

description='执行 FIO 顺序读测试',

params={

'rw':'read',

'bs':'128k',

'size':'1G',

'runtime':60,

'iodepth':1,

'ioengine':'sync',

'direct':True

}

)

logger.test_step(

step_num=4,

description='收集性能指标',

params={'metrics':['bandwidth','iops','latency_mean','latency_p99999']}

)

print("\n--- 4. 性能结果记录演示 ---\n")

logger.result('顺序读带宽',537.4,'MB/s','显著不达标（目标 2100 MB/s，达标率 25.6%）')

logger.result('随机读 IOPS',8992,'ops','显著不达标（目标 150000，达标率 6.0%）')

logger.result('平均延迟',231.9,'μs','超出限制（目标 200 μs，超出 15.9%）')

logger.result('尾部延迟 (p99.999)',4500,'μs','达标（目标 5000 μs）')

logger.result('顺序写带宽',2150.5,'MB/s','达标（目标 2000 MB/s）')

logger.result('随机写 IOPS',152000,'ops','达标（目标 150000）')

print("\n--- 5. 断言检查演示 ---\n")

logger.assertion(

assertion_name='带宽达标',

expected='≥2100 MB/s',

actual='537.4 MB/s',

passed=False,

tolerance='90%'

)

logger.assertion(

assertion_name='IOPS 达标',

expected='≥150000',

actual='8992',

passed=False

)

logger.assertion(

assertion_name='平均延迟达标',

expected='≤200 μs',

actual='231.9 μs',

passed=False

)

logger.assertion(

assertion_name='尾部延迟达标',

expected='≤5000 μs',

actual='4500 μs',

passed=True

)

print("\n--- 6. 后置条件检查演示 ---\n")

logger.postcondition(

check_name='设备健康状态',

pre_value='OK',

post_value='OK',

passed=True,

details='测试前后健康状态无变化'

)

logger.postcondition(

check_name='坏块数量',

pre_value=0,

post_value=2,

passed=False,

details='检测到新增 2 个坏块'

)

logger.postcondition(

check_name='设备温度',

pre_value='40°C',

post_value='45°C',

passed=True,

details='温度上升在正常范围内（<10°C）'

)

print("\n--- 7. 失败记录演示 ---\n")

logger.fail(

msg='带宽性能测试失败',

expected='≥2100 MB/s',

actual='537.4 MB/s',

reason='带宽性能显著不达标 (25.6% < 90%)'

)

logger.fail(

msg='IOPS 性能测试失败',

expected='≥150000',

actual='8992',

reason='IOPS 性能显著不达标 (6.0% < 90%)'

)

logger.fail(

msg='延迟性能测试失败',

expected='≤200 μs',

actual='231.9 μs',

reason='平均延迟超出限制 (115.9% > 100%)'

)

print("\n--- 8. 错误处理演示（带堆栈） ---\n")

try:

        raiseRuntimeError('FIO 执行超时：设备在 60 秒内未响应')

exceptException:

        logger.error('FIO 测试执行失败',exc_info=True)

print("\n--- 9. 测试完成总结 ---\n")

logger.info('测试完成：seq_read_burst - FAIL (61.89s)')

logger.info('Failure reasons: Has 3 Fail-Continue items')

logger.info('Total 3 Fail-Continue items:')

logger.info('  1. 带宽性能：Expected ≥2100 MB/s, Actual 537.4 MB/s (25.6% < 90%)')

logger.info('  2. IOPS 性能：Expected ≥150000, Actual 8992 (6.0% < 90%)')

logger.info('  3. 平均延迟：Expected ≤200 μs, Actual 231.9 μs (115.9% > 100%)')

print("\n--- 10. 日志文件位置 ---\n")

print(f"完整日志文件：{logger.get_log_file()}")

print(f"错误日志文件：{logger.get_error_file()}")

logger.close()

close_all_loggers()

print()

print("="*80)

print("演示完成！请查看日志文件获取详细输出。")

print("="*80)

if__name__=='__main__':

    demo_enhanced_logging()
