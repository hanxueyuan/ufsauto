#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
可靠性寿命计算工具
功能：温度/电压加速因子计算、DPPM 估算、HTOL 时间换算、AEC-Q100 样本量计算

作者：团长 1
创建日期：2026-03-28
依据：AEC-Q100 Rev-H、JESD47
"""

import math
from dataclasses import dataclass
from typing import Optional, Dict, List


# 物理常数
K_BOLTZMANN = 8.617e-5  # 玻尔兹曼常数 (eV/K)


@dataclass
class TemperatureAcceleration:
    """温度加速因子计算结果"""
    af_temp: float  # 温度加速因子
    tu_celsius: float  # 使用温度 (℃)
    ta_celsius: float  # 加速温度 (℃)
    ea_ev: float  # 活化能 (eV)
    equivalent_hours: float  # 等效使用小时数


@dataclass
class VoltageAcceleration:
    """电压加速因子计算结果"""
    af_voltage: float  # 电压加速因子
    vu_volts: float  # 使用电压 (V)
    va_volts: float  # 加速电压 (V)
    gamma: float  # 电压加速系数
    equivalent_hours: float  # 等效使用小时数


@dataclass
class HTOLCalculation:
    """HTOL 寿命计算结果"""
    af_total: float  # 总加速因子
    test_hours: float  # 测试时间 (小时)
    equivalent_years: float  # 等效使用年数
    tu_celsius: float  # 使用温度 (℃)
    ta_celsius: float  # 加速温度 (℃)
    ea_ev: float  # 活化能 (eV)
    vu_volts: Optional[float]  # 使用电压 (V)
    va_volts: Optional[float]  # 加速电压 (V)
    gamma: Optional[float]  # 电压加速系数


@dataclass
class LTPDSampleSize:
    """LTPD 抽样方案"""
    ltpd: float  # LTPD 值
    confidence: float  # 置信度
    acceptance_number: int  # 接收数 (c)
    sample_size: int  # 样本量


class ReliabilityCalculator:
    """可靠性寿命计算器"""
    
    # LTPD 抽样表（部分常用值）
    LTPD_TABLE = {
        # (LTPD, confidence, c) -> sample_size
        (1.0, 0.60, 0): 51,
        (1.0, 0.90, 0): 230,
        (1.0, 0.95, 0): 299,
        (1.5, 0.60, 0): 34,
        (1.5, 0.90, 0): 153,
        (1.5, 0.95, 0): 199,
        (2.0, 0.60, 0): 25,
        (2.0, 0.90, 0): 114,
        (2.0, 0.95, 0): 148,
    }
    
    # 典型活化能参考值
    EA_TYPICAL = {
        'general': 0.7,      # 通用 IC
        'mos': 0.85,         # MOS 器件
        'bipolar': 1.0,      # 双极型
        'flash': 0.8,        # 闪存
        'epitaxial': 1.1,    # 外延层
    }
    
    def calculate_temp_acceleration(
        self,
        tu_celsius: float,
        ta_celsius: float,
        ea_ev: float = 0.7,
        test_hours: float = 1000
    ) -> TemperatureAcceleration:
        """
        计算温度加速因子
        
        公式：AFT = exp[(Ea/k) × (1/Tu - 1/TA)]
        
        Args:
            tu_celsius: 使用温度 (℃)
            ta_celsius: 加速温度 (℃)
            ea_ev: 活化能 (eV)，默认 0.7
            test_hours: 测试时间 (小时)
        
        Returns:
            TemperatureAcceleration 对象
        """
        # 转换为开尔文
        tu_kelvin = tu_celsius + 273.15
        ta_kelvin = ta_celsius + 273.15
        
        # 计算加速因子
        exponent = (ea_ev / K_BOLTZMANN) * (1/tu_kelvin - 1/ta_kelvin)
        af_temp = math.exp(exponent)
        
        # 计算等效小时数
        equivalent_hours = test_hours * af_temp
        
        return TemperatureAcceleration(
            af_temp=af_temp,
            tu_celsius=tu_celsius,
            ta_celsius=ta_celsius,
            ea_ev=ea_ev,
            equivalent_hours=equivalent_hours
        )
    
    def calculate_voltage_acceleration(
        self,
        vu_volts: float,
        va_volts: float,
        gamma: float = 2.0,
        test_hours: float = 1000
    ) -> VoltageAcceleration:
        """
        计算电压加速因子
        
        公式：AFV = exp[γ × (VA - VU)]
        
        Args:
            vu_volts: 使用电压 (V)
            va_volts: 加速电压 (V)
            gamma: 电压加速系数，由 Fab 提供（典型 1-3）
            test_hours: 测试时间 (小时)
        
        Returns:
            VoltageAcceleration 对象
        """
        # 计算加速因子
        exponent = gamma * (va_volts - vu_volts)
        af_voltage = math.exp(exponent)
        
        # 计算等效小时数
        equivalent_hours = test_hours * af_voltage
        
        return VoltageAcceleration(
            af_voltage=af_voltage,
            vu_volts=vu_volts,
            va_volts=va_volts,
            gamma=gamma,
            equivalent_hours=equivalent_hours
        )
    
    def calculate_htol_life(
        self,
        tu_celsius: float = 85,
        ta_celsius: float = 150,
        ea_ev: float = 0.8,
        vu_volts: Optional[float] = None,
        va_volts: Optional[float] = None,
        gamma: Optional[float] = None,
        test_hours: float = 500
    ) -> HTOLCalculation:
        """
        计算 HTOL 等效寿命
        
        Args:
            tu_celsius: 使用温度 (℃)，默认 85℃（车规 Grade 2）
            ta_celsius: 加速温度 (℃)，默认 150℃
            ea_ev: 活化能 (eV)，默认 0.8（闪存）
            vu_volts: 使用电压 (V)，可选
            va_volts: 加速电压 (V)，可选
            gamma: 电压加速系数，可选
            test_hours: 测试时间 (小时)，默认 500（Grade 2 推荐）
        
        Returns:
            HTOLCalculation 对象
        """
        # 温度加速因子
        temp_result = self.calculate_temp_acceleration(
            tu_celsius, ta_celsius, ea_ev, test_hours
        )
        af_total = temp_result.af_temp
        
        # 电压加速因子（如果提供）
        if vu_volts and va_volts and gamma:
            volt_result = self.calculate_voltage_acceleration(
                vu_volts, va_volts, gamma, test_hours
            )
            af_total *= volt_result.af_voltage
        
        # 转换为年（按 8760 小时/年计算）
        equivalent_years = (test_hours * af_total) / 8760
        
        return HTOLCalculation(
            af_total=af_total,
            test_hours=test_hours,
            equivalent_years=equivalent_years,
            tu_celsius=tu_celsius,
            ta_celsius=ta_celsius,
            ea_ev=ea_ev,
            vu_volts=vu_volts,
            va_volts=va_volts,
            gamma=gamma
        )
    
    def get_ltpd_sample_size(
        self,
        ltpd: float = 1.0,
        confidence: float = 0.90,
        acceptance_number: int = 0
    ) -> LTPDSampleSize:
        """
        获取 LTPD 抽样方案样本量
        
        Args:
            ltpd: LTPD 值（缺陷密度），常用 1.0 或 1.5
            confidence: 置信度（0.60/0.90/0.95）
            acceptance_number: 接收数 (c)，常用 0
        
        Returns:
            LTPDSampleSize 对象
        """
        key = (ltpd, confidence, acceptance_number)
        
        if key in self.LTPD_TABLE:
            sample_size = self.LTPD_TABLE[key]
        else:
            # 如果表中没有，使用近似公式计算
            # n = -ln(1 - confidence) / (ltpd / 100)
            import math
            sample_size = int(math.ceil(-math.log(1 - confidence) / (ltpd / 100)))
        
        return LTPDSampleSize(
            ltpd=ltpd,
            confidence=confidence,
            acceptance_number=acceptance_number,
            sample_size=sample_size
        )
    
    def calculate_dppm(
        self,
        failures: int,
        sample_size: int,
        confidence: float = 0.90
    ) -> Dict[str, float]:
        """
        计算 DPPM（每百万缺陷数）
        
        公式：DPPM = (m/n) × 10^6 = (FIT × t) / 1000
        
        Args:
            failures: 失效数
            sample_size: 样本量
            confidence: 置信度
        
        Returns:
            包含 DPPM、FIT、可靠性的字典
        """
        if sample_size == 0:
            return {'error': '样本量不能为 0'}
        
        # DPPM 计算
        dppm = (failures / sample_size) * 1_000_000
        
        # FIT 计算（假设测试 1000 小时）
        # FIT = (failures / sample_size) × 10^9 / test_hours
        test_hours = 1000
        fit = (failures / sample_size) * 1_000_000_000 / test_hours
        
        # 可靠性计算（指数分布）
        # R(t) = exp(-FIT × t / 10^9)
        reliability_1year = math.exp(-fit * 8760 / 1_000_000_000)
        reliability_10years = math.exp(-fit * 87600 / 1_000_000_000)
        
        return {
            'dppm': dppm,
            'fit': fit,
            'reliability_1year': reliability_1year,
            'reliability_10years': reliability_10years,
            'failures': failures,
            'sample_size': sample_size,
            'confidence': confidence,
        }
    
    def calculate_required_test_time(
        self,
        target_years: float = 10,
        tu_celsius: float = 55,
        ta_celsius: float = 125,
        ea_ev: float = 0.7,
        vu_volts: Optional[float] = None,
        va_volts: Optional[float] = None,
        gamma: Optional[float] = None
    ) -> float:
        """
        计算达到目标寿命所需的测试时间
        
        Args:
            target_years: 目标等效寿命（年）
            tu_celsius: 使用温度 (℃)
            ta_celsius: 加速温度 (℃)
            ea_ev: 活化能 (eV)
            vu_volts: 使用电压 (V)，可选
            va_volts: 加速电压 (V)，可选
            gamma: 电压加速系数，可选
        
        Returns:
            所需测试时间（小时）
        """
        # 计算总加速因子
        htol_result = self.calculate_htol_life(
            tu_celsius, ta_celsius, ea_ev,
            vu_volts, va_volts, gamma,
            test_hours=1  # 先算 1 小时的加速因子
        )
        af_total = htol_result.af_total
        
        # 计算所需测试时间
        target_hours = target_years * 8760
        required_hours = target_hours / af_total
        
        return required_hours
    
    def print_htol_report(self, calculation: HTOLCalculation) -> str:
        """生成 HTOL 计算报告"""
        lines = [
            "=" * 60,
            "HTOL 寿命计算报告",
            "=" * 60,
            "",
            "测试条件:",
            f"  加速温度 (TA): {calculation.ta_celsius}℃",
            f"  使用温度 (TU): {calculation.tu_celsius}℃",
            f"  活化能 (Ea): {calculation.ea_ev} eV",
            f"  测试时间: {calculation.test_hours} 小时",
        ]
        
        if calculation.vu_volts and calculation.va_volts and calculation.gamma:
            lines.extend([
                f"  使用电压 (VU): {calculation.vu_volts} V",
                f"  加速电压 (VA): {calculation.va_volts} V",
                f"  电压加速系数 (γ): {calculation.gamma}",
            ])
        
        lines.extend([
            "",
            "计算结果:",
            f"  总加速因子 (AF): {calculation.af_total:.1f}x",
            f"  等效使用寿命: {calculation.equivalent_years:.1f} 年",
            "",
        ])
        
        if calculation.equivalent_years >= 10:
            lines.append("✅ 满足 10 年车规寿命要求")
        else:
            lines.append(f"⚠️ 不满足 10 年车规寿命要求（仅 {calculation.equivalent_years:.1f} 年）")
        
        lines.append("=" * 60)
        
        return '\n'.join(lines)


def main():
    """示例用法"""
    calc = ReliabilityCalculator()
    
    print("\n" + "=" * 60)
    print("车规级 UFS 3.1 可靠性寿命计算示例（Grade 2: 0℃~105℃）")
    print("=" * 60 + "\n")
    
    # 示例 1：HTOL 寿命计算（仅温度加速）- Grade 2 推荐方案
    print("【示例 1】HTOL 寿命计算（Grade 2 推荐方案）")
    print("-" * 40)
    result1 = calc.calculate_htol_life(
        tu_celsius=85,      # Grade 2 使用温度
        ta_celsius=150,     # HTOL 测试温度
        ea_ev=0.8,          # 闪存活化能
        test_hours=500      # Grade 2 推荐测试时间
    )
    print(calc.print_htol_report(result1))
    print()
    
    # 示例 2：HTOL 寿命计算（温度 + 电压加速）- Grade 2 长寿命方案
    print("【示例 2】HTOL 寿命计算（Grade 2 长寿命方案）")
    print("-" * 40)
    result2 = calc.calculate_htol_life(
        tu_celsius=85,
        ta_celsius=150,
        ea_ev=0.8,
        vu_volts=1.8,       # 使用电压
        va_volts=1.98,      # 加速电压 (1.1×)
        gamma=2.0,          # 电压加速系数
        test_hours=1634     # 10 年等效寿命所需时间
    )
    print(calc.print_htol_report(result2))
    print()
    
    # 示例 3：LTPD 样本量计算
    print("【示例 3】LTPD 抽样方案")
    print("-" * 40)
    ltpd_90 = calc.get_ltpd_sample_size(ltpd=1.0, confidence=0.90)
    ltpd_60 = calc.get_ltpd_sample_size(ltpd=1.0, confidence=0.60)
    print(f"LTPD 1.0, 90% 置信度：需要 {ltpd_90.sample_size} 颗样品")
    print(f"LTPD 1.0, 60% 置信度：需要 {ltpd_60.sample_size} 颗样品")
    print()
    
    # 示例 4：DPPM 计算
    print("【示例 4】DPPM 计算")
    print("-" * 40)
    dppm_result = calc.calculate_dppm(failures=0, sample_size=231)
    print(f"测试 231 颗，0 失效:")
    print(f"  DPPM: {dppm_result['dppm']}")
    print(f"  FIT: {dppm_result['fit']}")
    print(f"  1 年可靠性：{dppm_result['reliability_1year']*100:.4f}%")
    print(f"  10 年可靠性：{dppm_result['reliability_10years']*100:.4f}%")
    print()
    
    # 示例 5：计算所需测试时间（Grade 2）
    print("【示例 5】达到 3 年寿命所需测试时间（Grade 2）")
    print("-" * 40)
    required_hours = calc.calculate_required_test_time(
        target_years=3,
        tu_celsius=85,
        ta_celsius=150,
        ea_ev=0.8
    )
    print(f"目标：3 年等效寿命（Grade 2 标准）")
    print(f"条件：TA=150℃, TU=85℃, Ea=0.8eV")
    print(f"所需测试时间：{required_hours:.1f} 小时")
    if required_hours <= 500:
        print("✅ 标准 500 小时 HTOL 测试即可满足")
    else:
        print(f"⚠️ 需要测试 {required_hours:.0f} 小时")
    print()
    
    # 示例 6：Grade 1 vs Grade 2 对比
    print("【示例 6】Grade 1 vs Grade 2 对比")
    print("-" * 40)
    r1 = calc.calculate_htol_life(55, 125, 0.7, test_hours=1000)
    r2 = calc.calculate_htol_life(85, 150, 0.8, test_hours=500)
    print(f"Grade 1 (TA=125℃, TU=55℃, Ea=0.7, 1000h): {r1.equivalent_years:.1f}年")
    print(f"Grade 2 (TA=150℃, TU=85℃, Ea=0.8, 500h):  {r2.equivalent_years:.1f}年")
    print()


if __name__ == '__main__':
    main()
