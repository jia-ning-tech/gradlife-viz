#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
45_support_quadrant_prep.py

目的：
  为“导师支持 × 学校支持 × 高压组（四象限视图）”准备汇总数据。

数据来源：
  1）主数据（所有题目，含 v079_num, v091_num, v097_num, v100_num, v101_num 等）：
       /workspace/output/02_typed_clean/data_step2_typed_clean.csv
  2）高压标记（high_hours / low_worklife / high_stress_group 等）：
       /workspace/output/04_worklife/worklife_derived_vars.csv

思路：
  - 不再依赖 cleaned_main.csv 或 respondent_id；
    直接用 step2 数据 + worklife_derived_vars，通过“行顺序”对齐。
  - 构造两个连续支持指数：
      supervisor_support_raw   = mean(v079_num, v091_num)
      institution_support_raw  = mean(v097_num, v100_num, v101_num)
  - 对两个指数做 z 分数，再按 z 划分三档：
      z <= -0.5       -> Low
      -0.5 < z < 0.5  -> Medium
      z >= 0.5        -> High
  - 组合成 3×3 象限：
      supervisor_cat ∈ {Low, Medium, High}
      institution_cat ∈ {Low, Medium, High}
      quadrant_label = "{sup} supervisor / {inst} institution"
  - 与 high_stress_group 交叉，得到：
      high_stress_count, non_high_stress_count, high_stress_percent,
      non_high_stress_percent, total_count
  - 导出：
      /workspace/output/07_support/support_quadrant_high_stress.csv
      /workspace/output/08_viz_data/viz_support_quadrant_high_stress.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path


# ========= 路径配置 =========
MAIN_DATA_PATH = Path("/workspace/output/02_typed_clean/data_step2_typed_clean.csv")
WORKLIFE_PATH = Path("/workspace/output/04_worklife/worklife_derived_vars.csv")

OUTPUT_DIR_ANALYTIC = Path("/workspace/output/07_support")
OUTPUT_DIR_VIZ = Path("/workspace/output/08_viz_data")
OUTPUT_DIR_ANALYTIC.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR_VIZ.mkdir(parents=True, exist_ok=True)


# ========= 小工具函数 =========
def standardize_series(s: pd.Series) -> pd.Series:
    """
    对数值列做 z 分数（均值 0，标准差 1），忽略缺失。
    """
    mean = s.mean(skipna=True)
    std = s.std(skipna=True)
    if std == 0 or np.isnan(std):
        return pd.Series(np.nan, index=s.index)
    return (s - mean) / std


def categorize_z(z: pd.Series) -> pd.Series:
    """
    把 z 分数划成三档：
      z <= -0.5       -> 'Low'
      -0.5 < z < 0.5  -> 'Medium'
      z >= 0.5        -> 'High'
    """
    def _cat(val):
        if pd.isna(val):
            return pd.NA
        if val <= -0.5:
            return "Low"
        elif val >= 0.5:
            return "High"
        else:
            return "Medium"

    return z.apply(_cat)


# ========= 读入主数据 + 合并 high_stress_group =========
def load_with_high_stress() -> pd.DataFrame:
    """
    - 读取 step2 主数据（全题）
    - 读取 worklife_derived_vars（高压标记）
    - 按行顺序对齐，把 high_stress_group 加到主数据里
    """
    print("读取主数据 ...")
    df_main = pd.read_csv(MAIN_DATA_PATH)
    print(f"主数据形状: {df_main.shape}")

    print("读取 worklife 衍生变量（high_stress_group）...")
    df_work = pd.read_csv(WORKLIFE_PATH)
    print(f"worklife_derived_vars 形状: {df_work.shape}")

    if "high_stress_group" not in df_work.columns:
        raise KeyError(
            "在 worklife_derived_vars.csv 中找不到 high_stress_group 列，"
            "请确认 /workspace/output/04_worklife/worklife_derived_vars.csv 的结构。"
        )

    if len(df_main) != len(df_work):
        raise ValueError(
            f"主数据行数({len(df_main)}) 与 worklife_derived_vars 行数({len(df_work)}) 不一致。\n"
            "当前脚本假设它们来自同一个 step2 数据框，行顺序相同。\n"
            "如果你后来对其中一个做了删行/筛选，请先重新生成 worklife_derived_vars。"
        )

    df = df_main.copy()
    df["high_stress_group"] = df_work["high_stress_group"].values

    print("\n合并完成后数据形状:", df.shape)
    print("high_stress_group 分布:")
    print(df["high_stress_group"].value_counts(dropna=False))
    return df


# ========= 构造四象限表 =========
def prepare_quadrant_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    基于 df（含 v079_num, v091_num, v097_num, v100_num, v101_num 和 high_stress_group）构造：
      supervisor_support_raw / institution_support_raw
      supervisor_z / institution_z
      supervisor_cat / institution_cat
      quadrant_label

    然后 groupby 统计：
      quadrant_label, supervisor_cat, institution_cat
      high_stress_count, non_high_stress_count,
      high_stress_percent, non_high_stress_percent, total_count
    """
    # 导师支持相关题目（满意度 / 职业对话）
    sup_vars = ["v079_num", "v091_num"]
    # 学校 / 机构支持相关题目（心理健康服务、work-life 支持等）
    inst_vars = ["v097_num", "v100_num", "v101_num"]

    missing_sup = [c for c in sup_vars if c not in df.columns]
    missing_inst = [c for c in inst_vars if c not in df.columns]
    if missing_sup or missing_inst:
        raise KeyError(
            "主数据中缺少构造支持指数所需的列：\n"
            f"  导师支持缺少: {missing_sup}\n"
            f"  学校支持缺少: {missing_inst}\n"
            "请确认 data_step2_typed_clean.csv 中包含这些 *_num 变量。"
        )

    df = df.copy()

    # 1) 原始指数：简单平均
    df["supervisor_support_raw"] = df[sup_vars].mean(axis=1, skipna=True)
    df["institution_support_raw"] = df[inst_vars].mean(axis=1, skipna=True)

    # 2) z 分数（数值越大 => 相对“更支持”）
    df["supervisor_z"] = standardize_series(df["supervisor_support_raw"])
    df["institution_z"] = standardize_series(df["institution_support_raw"])

    # 3) 三档分类
    df["supervisor_cat"] = categorize_z(df["supervisor_z"])
    df["institution_cat"] = categorize_z(df["institution_z"])

    # 4) 象限标签
    df["quadrant_label"] = (
        df["supervisor_cat"].astype("string") + " supervisor / " +
        df["institution_cat"].astype("string") + " institution"
    )

    # 5) 只保留象限 & high_stress_group 都不缺失的样本
    mask_valid = (
        df["supervisor_cat"].notna()
        & df["institution_cat"].notna()
        & df["high_stress_group"].notna()
    )
    df_valid = df.loc[
        mask_valid,
        ["quadrant_label", "supervisor_cat", "institution_cat", "high_stress_group"],
    ].copy()

    print("\n用于四象限分析的有效样本量:", len(df_valid))

    # 6) groupby 统计
    grp = (
        df_valid.groupby(
            ["quadrant_label", "supervisor_cat", "institution_cat", "high_stress_group"]
        )
        .size()
        .reset_index(name="count")
    )

    # 7) pivot 成宽表：每个象限一行，高压/非高压拆列
    pivot = grp.pivot_table(
        index=["quadrant_label", "supervisor_cat", "institution_cat"],
        columns="high_stress_group",
        values="count",
        aggfunc="sum",
        fill_value=0,
    )

    # 列 1 = 高压，列 0 = 非高压（如果不存在则补 0）
    high = pivot.get(1, pd.Series(0, index=pivot.index))
    low = pivot.get(0, pd.Series(0, index=pivot.index))

    wide = pivot.copy()
    wide["high_stress_count"] = high
    wide["non_high_stress_count"] = low
    wide["total_count"] = wide["high_stress_count"] + wide["non_high_stress_count"]

    # 百分比（象限内部）
    wide["high_stress_percent"] = np.where(
        wide["total_count"] > 0,
        wide["high_stress_count"] / wide["total_count"] * 100,
        np.nan,
    )
    wide["non_high_stress_percent"] = np.where(
        wide["total_count"] > 0,
        wide["non_high_stress_count"] / wide["total_count"] * 100,
        np.nan,
    )

    wide = wide.reset_index()

    cols_order = [
        "quadrant_label",
        "supervisor_cat",
        "institution_cat",
        "high_stress_count",
        "non_high_stress_count",
        "total_count",
        "high_stress_percent",
        "non_high_stress_percent",
    ]
    wide = wide[cols_order]

    return wide


# ========= 主流程 =========
def main():
    df = load_with_high_stress()

    print("\n开始构建四象限汇总表 ...")
    quad_wide = prepare_quadrant_table(df)

    print("\n=== 四象限汇总表预览 ===")
    print(quad_wide.head(20))

    # 保存分析版
    analytic_path = OUTPUT_DIR_ANALYTIC / "support_quadrant_high_stress.csv"
    quad_wide.to_csv(analytic_path, index=False)
    print(f"\n已保存分析用四象限汇总表到: {analytic_path}")

    # 保存前端可视化版（先用同一份）
    viz_path = OUTPUT_DIR_VIZ / "viz_support_quadrant_high_stress.csv"
    quad_wide.to_csv(viz_path, index=False)
    print(f"已保存可视化用四象限汇总表到: {viz_path}")


if __name__ == "__main__":
    main()
