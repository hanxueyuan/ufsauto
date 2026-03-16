#!/usr/bin/env python3
"""
报告生成器 - Report Generator
负责生成测试报告
"""

import os
import json
from pathlib import Path
from datetime import datetime


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self, output_dir='./results', formats=None):
        self.output_dir = Path(output_dir)
        self.formats = formats or ['html', 'json']
    
    def generate(self, results, test_id):
        """生成报告"""
        output_path = self.output_dir / test_id
        output_path.mkdir(parents=True, exist_ok=True)
        
        generated_files = []
        
        # 保存 JSON 结果
        if 'json' in self.formats:
            json_file = output_path / 'results.json'
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            generated_files.append(str(json_file))
        
        # 生成 HTML 报告
        if 'html' in self.formats:
            html_file = output_path / 'report.html'
            html_content = self._generate_html(results, test_id)
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            generated_files.append(str(html_file))
        
        # 生成文本摘要
        if 'text' in self.formats:
            txt_file = output_path / 'summary.txt'
            txt_content = self._generate_text_summary(results, test_id)
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(txt_content)
            generated_files.append(str(txt_file))
        
        return generated_files[0] if generated_files else None
    
    def _generate_html(self, results, test_id):
        """生成 HTML 报告"""
        
        # 兼容两种数据结构
        if 'test_results' in results:
            summary = results['test_results'].get('summary', {})
            test_cases = results['test_results'].get('test_cases', [])
        else:
            summary = results.get('summary', {})
            test_cases = results.get('test_cases', [])
        
        system_info = results.get('system_info', {})
        device_info = results.get('device_info', {})
        
        # 生成测试结果表格
        test_rows = []
        for tc in test_cases:
            name = tc.get('test_name', 'Unknown')
            status = tc.get('status', 'UNKNOWN')
            status_class = 'pass' if status == 'PASS' else 'fail' if status == 'FAIL' else 'error'
            status_icon = '✅' if status == 'PASS' else '❌' if status == 'FAIL' else '⚠️'
            
            metrics = tc.get('metrics', {})
            bandwidth = metrics.get('bandwidth', 0)
            iops = metrics.get('iops', 0)
            latency = metrics.get('latency_avg', 0)
            
            test_rows.append(f'''
            <tr class="{status_class}">
                <td>{name}</td>
                <td>{status_icon} {status}</td>
                <td>{bandwidth if bandwidth else '-'} MB/s</td>
                <td>{iops if iops else '-'} K</td>
                <td>{latency if latency else '-'} μs</td>
            </tr>
            ''')
        
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UFS 系统测试报告 - {test_id}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f5; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #333; margin-bottom: 10px; }}
        h2 {{ color: #555; margin: 30px 0 15px; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
        .header {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 20px 0; }}
        .summary-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center; }}
        .summary-card.pass {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }}
        .summary-card.fail {{ background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%); }}
        .summary-card .value {{ font-size: 32px; font-weight: bold; }}
        .summary-card .label {{ font-size: 14px; opacity: 0.9; margin-top: 5px; }}
        table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        th {{ background: #f8f9fa; padding: 15px; text-align: left; font-weight: 600; color: #333; }}
        td {{ padding: 12px 15px; border-top: 1px solid #eee; }}
        tr.pass {{ background: #d4edda; }}
        tr.fail {{ background: #f8d7da; }}
        tr.error {{ background: #fff3cd; }}
        .info-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
        .info-card {{ background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .info-card h3 {{ color: #667eea; margin-bottom: 10px; font-size: 16px; }}
        .info-item {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; }}
        .info-item:last-child {{ border-bottom: none; }}
        .info-label {{ color: #666; }}
        .info-value {{ color: #333; font-weight: 500; }}
        .footer {{ text-align: center; padding: 20px; color: #999; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 UFS 系统测试报告</h1>
            <p style="color: #666;">测试 ID: {test_id}</p>
            <p style="color: #999; font-size: 14px;">生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <div class="value">{summary.get('total', 0)}</div>
                <div class="label">总计</div>
            </div>
            <div class="summary-card pass">
                <div class="value">{summary.get('passed', 0)}</div>
                <div class="label">通过</div>
            </div>
            <div class="summary-card fail">
                <div class="value">{summary.get('failed', 0)}</div>
                <div class="label">失败</div>
            </div>
            <div class="summary-card">
                <div class="value">{summary.get('pass_rate', 0):.1f}%</div>
                <div class="label">通过率</div>
            </div>
        </div>
        
        <h2>📋 测试结果</h2>
        <table>
            <thead>
                <tr>
                    <th>测试项</th>
                    <th>状态</th>
                    <th>带宽</th>
                    <th>IOPS</th>
                    <th>延迟</th>
                </tr>
            </thead>
            <tbody>
                {''.join(test_rows)}
            </tbody>
        </table>
        
        <h2>💻 系统信息</h2>
        <div class="info-grid">
            <div class="info-card">
                <h3>系统</h3>
                <div class="info-item"><span class="info-label">主机名</span><span class="info-value">{system_info.get('hostname', '-')}</span></div>
                <div class="info-item"><span class="info-label">内核</span><span class="info-value">{system_info.get('kernel', '-')}</span></div>
                <div class="info-item"><span class="info-label">CPU</span><span class="info-value">{system_info.get('cpu_count', 0)} 核心</span></div>
                <div class="info-item"><span class="info-label">内存</span><span class="info-value">{system_info.get('memory_total', 0)} MB</span></div>
            </div>
            <div class="info-card">
                <h3>设备</h3>
                <div class="info-item"><span class="info-label">设备路径</span><span class="info-value">{device_info.get('device_path', '-')}</span></div>
                <div class="info-item"><span class="info-label">型号</span><span class="info-value">{device_info.get('model', '-')}</span></div>
                <div class="info-item"><span class="info-label">序列号</span><span class="info-value">{device_info.get('serial', '-')}</span></div>
                <div class="info-item"><span class="info-label">容量</span><span class="info-value">{device_info.get('size', 0)} GB</span></div>
            </div>
        </div>
        
        <div class="footer">
            <p>UFS 系统测试框架 v1.0 | SysTest</p>
        </div>
    </div>
</body>
</html>
'''
        return html
    
    def _generate_text_summary(self, results, test_id):
        """生成文本摘要"""
        # 兼容两种数据结构
        if 'test_results' in results:
            summary = results['test_results'].get('summary', {})
            test_cases = results['test_results'].get('test_cases', [])
        else:
            summary = results.get('summary', {})
            test_cases = results.get('test_cases', [])
        
        lines = [
            f"UFS 系统测试报告",
            f"测试 ID: {test_id}",
            f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "测试摘要:",
            f"  总计：{summary.get('total', 0)} 项",
            f"  通过：{summary.get('passed', 0)} 项",
            f"  失败：{summary.get('failed', 0)} 项",
            f"  通过率：{summary.get('pass_rate', 0):.1f}%",
            "",
            "测试结果:",
        ]
        
        for tc in test_cases:
            name = tc.get('test_name', 'Unknown')
            status = tc.get('status', 'UNKNOWN')
            status_icon = '✅' if status == 'PASS' else '❌' if status == 'FAIL' else '⚠️'
            
            metrics = tc.get('metrics', {})
            bandwidth = metrics.get('bandwidth', 0)
            iops = metrics.get('iops', 0)
            
            line = f"  {status_icon} {name}"
            if bandwidth:
                line += f" - {bandwidth} MB/s"
            if iops:
                line += f" - {iops} K IOPS"
            lines.append(line)
        
        return '\n'.join(lines)
