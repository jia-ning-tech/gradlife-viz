#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
44_mental_help_viz_export_by_degree.py

读取：
  /workspace/output/06_mental_health/mental_help_vs_high_stress_by_degree.csv

该文件是 43_mental_help_vs_worklife_by_degree.py 生成的长表：
  help_label × degree_code_int × degree_label × high_stress_group × count × percent_within_help_degree

本脚本将其整理成前端可视化用的宽表：
  help_label, degree_code_int, degree_label,
  high_stress_percent, high_stress_count,
  non_high_stress_count, total_count

输出到：
  /workspace/output/08_viz_data/viz_mental_help_by_degree_high_stress.csv
"""

from pathlib import Path
import pandas as pd

BASE_DIR = Path("/workspace")
OUTPUT_DIR = BASE_DIR / "output"

IN_LONG = OUTPUT_DIR / "06_mental_health" / "mental_help_vs_high_stress_by_degree.csv"
OUT_VIZ = OUTPUT_DIR / "08_viz_data" / "viz_mental_help_by_degree_high_stress.csv"


def main():
    print("读取长表:", IN_LONG)
    df = pd.read_csv(IN_LONG)

    print("原始长表形状:", df.shape)
    print(df.head())

    # 确保 high_stress_group 是整数 0/1
    df["high_stress_group"] = df["high_stress_group"].astype(int)

    # 为了安全，先按 help_label + degree 汇总出总样本数
    group_keys = ["help_label", "degree_code_int", "degree_label"]

    # 总样本数
    total_df = (
        df.groupby(group_keys)["count"]
        .sum()
        .reset_index(name="total_count")
    )

    # 高压组（high_stress_group == 1）的样本数
    high_df = (
        df[df["high_stress_group"] == 1]
        .groupby(group_keys)["count"]
        .sum()
        .reset_index(name="high_stress_count")
    )

    # 合并
    merged = total_df.merge(
        high_df,
        on=group_keys,
        how="left",
    )

    # 没有高压样本的组合，high_stress_count 置 0
    merged["high_stress_count"] = merged["high_stress_count"].fillna(0).astype(int)

    # 非高压样本数
    merged["non_high_stress_count"] = (
        merged["total_count"] - merged["high_stress_count"]
    ).astype(int)

    # 高压比例（在该 help_label × degree 组合内部）
    merged["high_stress_percent"] = (
        merged["high_stress_count"] / merged["total_count"] * 100
    )

    # 排序：按 help_label -> degree_code_int
    merged = merged.sort_values(
        by=["help_label", "degree_code_int"]
    ).reset_index(drop=True)

    print("\n=== 可视化用宽表预览 ===")
    print(merged.head(20))

    # 输出
    OUT_VIZ.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(OUT_VIZ, index=False, float_format="%.6f")

    print("\n已保存可视化用的 心理健康求助×高压×学位 数据到:")
    print(" ", OUT_VIZ)


if __name__ == "__main__":
    main()
