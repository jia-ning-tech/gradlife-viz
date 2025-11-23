#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
47_hours_vs_high_stress.py

目标：
- 基于 worklife_derived_vars.csv 中的 hours_level 和 high_stress_group，
  生成“工时 × 高压组”的两个视角：
    1）在每个高压组内部，工时档位的分布（解释高压组的工时情况）
    2）在每个工时档位内部，高压 vs 非高压的比例（解释工时与高压风险的关系）

输出：
- 分析用结果：/workspace/output/10_hours/...
- 可视化用结果：
    /workspace/output/08_viz_data/viz_hours_distribution_by_stress.csv
    /workspace/output/08_viz_data/viz_hours_high_stress_by_hours_level.csv
"""

from pathlib import Path

import pandas as pd

BASE = Path("/workspace")

DERIVED_PATH = BASE / "output/04_worklife/worklife_derived_vars.csv"

# 分析用输出目录
OUTPUT_DIR = BASE / "output/10_hours"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 前端可视化数据目录（和你现有的其它 viz_* 一致）
VIZ_DIR = BASE / "output/08_viz_data"
VIZ_DIR.mkdir(parents=True, exist_ok=True)

# 在 worklife_derived_vars.csv 里已经确认存在的列
HOURS_LEVEL_COL = "hours_level"        # 工时档位（文本，如 "31–40 hours"）
HIGH_STRESS_COL = "high_stress_group"  # 0/1，是否属于高压组


def build_hours_order(values):
    """
    根据常见的工时选项模式，构造一个合理的排序。
    如果有一些选项不在预期模式里，就按字母顺序排在后面。
    """
    unique_vals = list(pd.Series(values).dropna().unique())
    remaining = set(unique_vals)

    # 常见 Q29 工时档位的文本特征（根据你之前的问卷经验写的）
    # 如果实际文本不完全一致，后面会有 fallback。
    patterns = [
        "<",          # "<11 hours", "<10" 等
        "11",         # "11–20 hours"
        "21",         # "21–30"
        "31",         # "31–40"
        "41",         # "41–50"
        "51",         # "51–60"
        "61",         # "61–70"
        "71",         # "71–80"
        "80",         # ">80" / "More than 80"
    ]

    ordered = []
    for pat in patterns:
        for v in list(remaining):
            if pat in str(v):
                ordered.append(v)
                remaining.remove(v)

    # 其余没有匹配到的，按字母顺序追加
    ordered.extend(sorted(remaining))

    order_map = {v: i for i, v in enumerate(ordered)}
    return order_map


def main():
    print("读取 worklife_derived_vars ...")
    df = pd.read_csv(DERIVED_PATH)
    print("worklife_derived_vars 形状:", df.shape)

    # 检查必需列
    missing_cols = [c for c in [HOURS_LEVEL_COL, HIGH_STRESS_COL] if c not in df.columns]
    if missing_cols:
        raise KeyError(
            "在 worklife_derived_vars.csv 中找不到必需的列："
            + ", ".join(missing_cols)
        )

    # 只保留工时和 high_stress_group 都非缺失的样本
    df = df[[HOURS_LEVEL_COL, HIGH_STRESS_COL]].copy()
    before = len(df)
    df = df.dropna(subset=[HOURS_LEVEL_COL, HIGH_STRESS_COL])
    after = len(df)
    print(f"剔除缺失后有效样本量: {after}（删除 {before - after} 行）")

    # 把 high_stress_group 保证为 0/1 整数
    df[HIGH_STRESS_COL] = pd.to_numeric(df[HIGH_STRESS_COL], errors="coerce").astype("Int64")

    # 构造工时档位排序
    hours_order_map = build_hours_order(df[HOURS_LEVEL_COL])
    df["hours_order"] = df[HOURS_LEVEL_COL].map(hours_order_map)

    # ============================================================
    # 1) 在每个高压组内部，工时档位的分布
    #    -> 解释“高压组和非高压组的工时情况”
    # ============================================================

    dist = (
        df
        .groupby([HIGH_STRESS_COL, HOURS_LEVEL_COL], dropna=False)
        .size()
        .reset_index(name="count")
    )

    # 排序辅助列
    dist["hours_order"] = dist[HOURS_LEVEL_COL].map(hours_order_map)

    # 在每个 high_stress_group 内部算百分比
    total_by_group = dist.groupby(HIGH_STRESS_COL)["count"].transform("sum")
    dist["percent_within_stress_group"] = dist["count"] / total_by_group * 100

    # 方便前端：增加文本 label
    dist["high_stress_label"] = dist[HIGH_STRESS_COL].map({0: "Non-high-stress", 1: "High-stress"})

    # 保存分析版
    out_dist = OUTPUT_DIR / "hours_distribution_by_stress.csv"
    dist.to_csv(out_dist, index=False)
    print("已保存工时分布（按高压组分层）到：", out_dist)

    # 保存可视化版（同一份，只是放到 08_viz_data）
    viz_dist = VIZ_DIR / "viz_hours_distribution_by_stress.csv"
    dist_viz_cols = [
        HIGH_STRESS_COL,
        "high_stress_label",
        HOURS_LEVEL_COL,
        "hours_order",
        "count",
        "percent_within_stress_group",
    ]
    dist[dist_viz_cols].to_csv(viz_dist, index=False)
    print("已保存可视化用工时分布数据到：", viz_dist)

    # ============================================================
    # 2) 在每个工时档位内部，高压 vs 非高压比例
    #    -> 解释“工时越高，高压比例如何变化”
    # ============================================================

    cross = (
        df
        .groupby([HOURS_LEVEL_COL, HIGH_STRESS_COL], dropna=False)
        .size()
        .reset_index(name="count")
    )

    cross["hours_order"] = cross[HOURS_LEVEL_COL].map(hours_order_map)

    # 在每个 hours_level 内部算百分比
    total_by_hours = cross.groupby(HOURS_LEVEL_COL)["count"].transform("sum")
    cross["percent_within_hours_level"] = cross["count"] / total_by_hours * 100

    cross["high_stress_label"] = cross[HIGH_STRESS_COL].map({0: "Non-high-stress", 1: "High-stress"})

    # 保存分析版
    out_cross = OUTPUT_DIR / "hours_vs_high_stress.csv"
    cross.to_csv(out_cross, index=False)
    print("已保存工时档位 × 高压组结果到：", out_cross)

    # 保存可视化版
    viz_cross = VIZ_DIR / "viz_hours_high_stress_by_hours_level.csv"
    cross_viz_cols = [
        HOURS_LEVEL_COL,
        "hours_order",
        HIGH_STRESS_COL,
        "high_stress_label",
        "count",
        "percent_within_hours_level",
    ]
    cross[cross_viz_cols].to_csv(viz_cross, index=False)
    print("已保存可视化用工时 × 高压数据到：", viz_cross)

    print("\n工时 × 高压相关数据准备完成。")


if __name__ == "__main__":
    main()
