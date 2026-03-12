#!/usr/bin/env python3
# UFS Auto 测试框架统一入口
import argparse
import sys
import os
from datetime import datetime
from lib.common import Logger, EnvironmentChecker
from lib.report import ReportGenerator
from lib.test_runner import TestRunner

# 添加src目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    parser = argparse.ArgumentParser(description="UFS Auto 自动化测试框架")
    parser.add_argument("-t", "--test", choices=["all", "system", "function", "performance", "reliability", "scenario"], 
                        default="all", help="指定要运行的测试类型")
    parser.add_argument("-c", "--config", default="config/test_config.py", help="测试配置文件路径")
    parser.add_argument("-o", "--output", default="results", help="测试结果输出目录")
    parser.add_argument("-l", "--list", action="store_true", help="列出所有可用测试用例")
    parser.add_argument("-v", "--verbose", action="store_true", help="输出详细日志")
    parser.add_argument("--no-fail-fast", action="store_true", help="测试失败时不立即停止，继续执行后续用例")
    parser.add_argument("--pre-check-only", action="store_true", help="仅执行前置检查，不运行测试")
    
    args = parser.parse_args()
    
    # 初始化日志
    log_level = "DEBUG" if args.verbose else "INFO"
    logger = Logger(log_level=log_level, output_dir=args.output)
    logger.info("="*60)
    logger.info("UFS Auto 自动化测试框架启动")
    logger.info(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"测试类型: {args.test}")
    logger.info("="*60)
    
    # 前置环境检查
    env_checker = EnvironmentChecker(logger)
    logger.info("开始执行前置环境检查...")
    pre_check_result, pre_check_report = env_checker.run_all_checks()
    
    if not pre_check_result:
        logger.error("前置环境检查失败，请检查以下问题：")
        for item in pre_check_report["failed"]:
            logger.error(f"  ❌ {item['name']}: {item['message']}")
        logger.error("测试终止")
        return 1
    
    if args.pre_check_only:
        logger.info("✅ 前置环境检查全部通过")
        return 0
    
    # 列出测试用例
    if args.list:
        test_runner = TestRunner(args.config, logger, args.output)
        test_cases = test_runner.list_test_cases(args.test)
        logger.info("可用测试用例列表：")
        for test_type, cases in test_cases.items():
            logger.info(f"\n{test_type.upper()} 测试：")
            for case in cases:
                logger.info(f"  - {case['name']}: {case['description']}")
        return 0
    
    # 执行测试
    logger.info("✅ 前置环境检查全部通过，开始执行测试...")
    test_runner = TestRunner(args.config, logger, args.output, fail_fast=not args.no_fail_fast)
    
    try:
        test_result = test_runner.run_tests(args.test)
    except KeyboardInterrupt:
        logger.warning("测试被用户中断")
        return 1
    except Exception as e:
        logger.error(f"测试执行发生异常: {str(e)}", exc_info=True)
        return 1
    
    # 生成测试报告
    logger.info("测试执行完成，正在生成测试报告...")
    report_generator = ReportGenerator(args.output, logger)
    report_path = report_generator.generate_report(test_result, pre_check_report)
    
    # 输出测试总结
    logger.info("\n" + "="*60)
    logger.info("📊 测试执行总结")
    logger.info("="*60)
    logger.info(f"总用例数: {test_result['summary']['total']}")
    logger.info(f"✅ 通过: {test_result['summary']['passed']}")
    logger.info(f"❌ 失败: {test_result['summary']['failed']}")
    logger.info(f"⚠️  跳过: {test_result['summary']['skipped']}")
    logger.info(f"⌛ 总耗时: {test_result['summary']['duration']:.2f} 秒")
    logger.info(f"📝 测试报告: {report_path}")
    logger.info("="*60)
    
    # 输出失败用例详情
    if test_result['summary']['failed'] > 0:
        logger.error("\n❌ 失败用例详情：")
        for failed in test_result['failed']:
            logger.error(f"\n  测试用例: {failed['name']}")
            logger.error(f"  失败原因: {failed['error']}")
            logger.error(f"  初步分析: {failed['analysis']}")
            logger.error(f"  日志文件: {failed['log_file']}")
    
    # 后置环境检查
    logger.info("\n开始执行后置环境检查...")
    post_check_result, post_check_report = env_checker.run_post_checks()
    
    if not post_check_result:
        logger.warning("后置环境检查发现异常：")
        for item in post_check_report["failed"]:
            logger.warning(f"  ⚠️  {item['name']}: {item['message']}")
    else:
        logger.info("✅ 后置环境检查全部通过")
    
    # 测试结果返回码
    if test_result['summary']['failed'] > 0:
        logger.error("\n❌ 测试执行失败，请查看报告详情")
        return 1
    else:
        logger.info("\n✅ 所有测试执行通过")
        return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
