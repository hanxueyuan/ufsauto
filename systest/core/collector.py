#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结果收集器 - Result Collector
负责收集测试结果、生成标准数据格式、保存原始数据
"""

import json
import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class ResultCollector:
    """测试结果收集器"""
    
    def __init__(self, output_dir: str = './results'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"结果输出目录：{self.output_dir.absolute()}")
    
    def collect(
        self,
        results: List[Dict[str, Any]],
        test_id: Optional[str] = None,
        suite_name: Optional[str] = None,
        device: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        收集测试结果
        
        Args:
            results: 测试结果列表
            test_id: 测试 ID（默认使用时间戳）
            suite_name: 测试套件名称
            device: 测试设备
            metadata: 额外元数据
        
        Returns:
            完整的报告数据结构
        """
        if test_id is None:
            test_id = f"SysTest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 创建测试输出目录
        test_dir = self.output_dir / test_id
        test_dir.mkdir(parents=True, exist_ok=True)
        
        # 计算汇总统计
        total = len(results)
        passed = sum(1 for r in results if r.get('status') == 'PASS')
        failed = sum(1 for r in results if r.get('status') == 'FAIL')
        errors = sum(1 for r in results if r.get('status') == 'ERROR')
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        # 构建报告数据
        report_data = {
            'test_id': test_id,
            'timestamp': datetime.now().isoformat(),
            'suite': suite_name,
            'device': device,
            'test_cases': results,
            'summary': {
                'total': total,
                'passed': passed,
                'failed': failed,
                'errors': errors,
                'pass_rate': pass_rate
            },
            'metadata': metadata or {}
        }
        
        # 保存 JSON 结果
        json_path = test_dir / 'results.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        logger.debug(f"结果已保存：{json_path}")
        
        # 保存每个测试用例的详细日志
        for result in results:
            if 'log_file' in result:
                try:
                    log_src = Path(result['log_file'])
                    if log_src.exists():
                        log_size = log_src.stat().st_size
                        log_dst = test_dir / f"{result['name']}.log"
                        shutil.copy2(log_src, log_dst)
                        logger.debug(f"📄 日志已复制：{result['name']} ({log_size / 1024 / 1024:.1f} MB)")
                except Exception as e:
                    # 尝试获取文件大小
                    try:
                        log_size = log_src.stat().st_size if log_src.exists() else 0
                        if log_size > 500 * 1024 * 1024:  # > 500MB
                            logger.warning(f"⚠️  大日志文件复制失败 {result['name']} ({log_size / 1024 / 1024:.1f} MB): {e}")
                            logger.warning(f"💡 文件较大，复制可能需要更多空间或时间")
                            logger.warning(f"💡 可手动清理：rm {log_dst}")
                        else:
                            logger.warning(f"⚠️  日志文件复制失败 {result['name']} ({log_size / 1024 / 1024:.1f} MB): {e}")
                        logger.warning(f"💡  建议：手动复制或删除大日志文件以释放空间")
                    except Exception:
                        logger.warning(f"⚠️  日志文件复制失败 {result['name']}: {e}")
                    # 继续处理其他结果，不中断整个流程
        
        # 保存汇总信息
        summary_path = test_dir / 'summary.txt'
        self._save_summary(summary_path, report_data)
        
        logger.info(f"测试 {test_id} 结果汇总：{passed}/{total} 通过 ({pass_rate:.1f}%)")
        
        return report_data
    
    def _save_summary(self, path: Path, report_data: Dict[str, Any]):
        """保存文本格式汇总"""
        lines = [
            "=" * 60,
            "UFS 系统测试报告",
            "=" * 60,
            "",
            f"测试 ID: {report_data['test_id']}",
            f"时间：{report_data['timestamp']}",
            f"套件：{report_data['suite']}",
            f"设备：{report_data['device']}",
            "",
            "-" * 60,
            "汇总统计",
            "-" * 60,
            f"总计：{report_data['summary']['total']} 项",
            f"通过：{report_data['summary']['passed']} 项",
            f"失败：{report_data['summary']['failed']} 项",
            f"错误：{report_data['summary']['errors']} 项",
            f"通过率：{report_data['summary']['pass_rate']:.1f}%",
            "",
            "-" * 60,
            "测试结果",
            "-" * 60,
        ]
        
        for result in report_data['test_cases']:
            status_icon = '✅' if result['status'] == 'PASS' else '❌' if result['status'] == 'FAIL' else '⚠️'
            lines.append(f"{status_icon} {result['name']}: {result['status']} ({result.get('duration', 0):.2f}s)")
        
        lines.append("")
        lines.append("=" * 60)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        logger.debug(f"汇总已保存：{path}")
    
    def get_latest_test_id(self) -> Optional[str]:
        """获取最新测试 ID"""
        test_dirs = [d for d in self.output_dir.iterdir() if d.is_dir()]
        if not test_dirs:
            return None
        
        latest = max(test_dirs, key=lambda d: d.stat().st_mtime)
        return latest.name
    
    def load_results(self, test_id: str) -> Optional[Dict[str, Any]]:
        """加载指定测试的结果"""
        json_path = self.output_dir / test_id / 'results.json'
        
        if not json_path.exists():
            logger.warning(f"结果文件不存在：{json_path}")
            return None
        
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def list_tests(self) -> List[Dict[str, Any]]:
        """列出所有测试结果"""
        tests = []
        
        for test_dir in sorted(self.output_dir.iterdir(), key=lambda d: d.stat().st_mtime, reverse=True):
            if not test_dir.is_dir():
                continue
            
            json_path = test_dir / 'results.json'
            if not json_path.exists():
                continue
            
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    tests.append({
                        'test_id': test_dir.name,
                        'timestamp': data.get('timestamp', ''),
                        'suite': data.get('suite', ''),
                        'pass_rate': data['summary']['pass_rate'],
                        'total': data['summary']['total'],
                        'passed': data['summary']['passed']
                    })
            except Exception as e:
                logger.warning(f"加载测试结果失败 {test_dir.name}: {e}")
        
        return tests
