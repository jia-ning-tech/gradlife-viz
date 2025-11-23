#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
42_satisfaction_change_vs_worklife.py

目的：
  - 利用 Q26 (v073 / v073_code) “满意度变化”：
      1 = Worsened a little
      2 = Improved slightly
      3 = Significantly worsened
      4 = Stayed the same
      5 = Improved greatly

  - 重新分档为三组：
      - "Worsened"        : code in {1, 3}
      - "Stayed the same" : code == 4
      - "Improved"        : code in {2, 5}

  - 与 high_stress_group 做交叉分析
  - 导出：
      1) 详细交叉表：/workspace/output/06_satisfaction/satisfaction_change_vs_high_stress.csv
      2) 前端可视化用宽表：/workspace/output/08_viz_data/viz_satisfaction_change_high_stress.csv
"""

import pandas as pd
from pathlib import Path

DATA_PATH = Path("/workspace/output/02_typed_clean/data_step2_typed_clean.csv")
WORKLIFE_DERIVED_PATH = Path("/workspace/output/04_worklife/worklife_derived_vars.csv")

OUT_DIR_ANALYTIC = Path("/workspace/output/06_satisfaction")
OUT_DIR_VIZ = Path("/workspace/output/08_viz_data")
OUT_DIR_ANALYTIC.mkdir(parents=True, exist_ok=True)
OUT_DIR_VIZ.mkdir(parents=True, exist_ok=True)


def map_change_category(code):
    """
    把 v073_code 数值映射为三类：
      - Worsened        : 1 = Worsened a little, 3 = Significantly worsened
      - Stayed the same : 4 = Stayed the same
      - Improved        : 2 = Improved slightly, 5 = Improved greatly
    其他 & 缺失 -> <NA>
    """
    if pd.isna(code):
        return pd.NA
    try:
        c = int(code)
    except Exception:
        return pd.NA

    if c in (1, 3):
        return "Worsened"
    elif c == 4:
        return "Stayed the same"
    elif c in (2, 5):
        return "Improved"
    else:
        return pd.NA


def main():
    print("读取主数据 ...")
    df = pd.read_csv(DATA_PATH)
    print("主数据形状:", df.shape)

    # 合并 high_stress_group
    if WORKLIFE_DERIVED_PATH.exists():
        wlife = pd.read_csv(WORKLIFE_DERIVED_PATH)
        if "high_stress_group" in wlife.columns:
            df = df.merge(
                wlife[["high_stress_group"]],
                left_index=True,
                right_index=True,
                how="left",
            )
            print("已将 high_stress_group 合并进主数据。")
        else:
            print("警告：worklife_derived_vars 中没有 high_stress_group 列。")
    else:
        print("错误：未找到 worklife_derived_vars.csv。")
        return

    if "v073_code" not in df.columns:
        print("错误：数据中没有 v073_code 列，请检查。")
        return

    # === 1) 构造满意度变化三档 ===
    print("\n构造 sat_change_cat（三档：Worsened / Stayed the same / Improved）...")
    df["sat_change_cat"] = df["v073_code"].apply(map_change_category).astype("string")

    print("\n=== sat_change_cat 分布（含缺失） ===")
    print(df["sat_change_cat"].value_counts(dropna=False))

    # 只保留 sat_change_cat 和 high_stress_group 都不缺失的样本
    sub = df.dropna(subset=["sat_change_cat", "high_stress_group"]).copy()
    sub["high_stress_group"] = sub["high_stress_group"].astype(int)
    print("\n有效样本量（sat_change_cat & high_stress_group 都非缺失）:", len(sub))

    # === 2) 详细交叉表（长表） ===
    cross = (
        sub.groupby(["sat_change_cat", "high_stress_group"])
        .size()
        .reset_index(name="count")
    )

    # 每个 sat_change_cat 内部百分比（用于看“该类里面高压占比”）
    cross["percent_within_cat"] = (
        cross["count"]
        / cross.groupby("sat_change_cat")["count"].transform("sum")
        * 100
    )

    # 为了可读性，加一个描述性的 question 字段
    question_text = (
        "Q26 – Since the very start of your graduate school experience, "
        "would you say your level of satisfaction has:"
    )
    cross.insert(0, "question", question_text)

    print("\n=== Q26 满意度变化 × 高压组 交叉表（长表预览） ===")
    print(cross)

    analytic_path = OUT_DIR_ANALYTIC / "satisfaction_change_vs_high_stress.csv"
    cross.to_csv(analytic_path, index=False)
    print("\n已保存详细交叉表到:", analytic_path)

    # === 3) 前端可视化用宽表 ===
    # 目标列结构：
    #   change_label, high_stress_percent, high_stress_count, total_count
    rows = []
    for cat in sorted(cross["sat_change_cat"].unique()):
        sub_cat = cross[cross["sat_change_cat"] == cat]

        total_count = sub_cat["count"].sum()
        # 高压 = high_stress_group == 1
        high_row = sub_cat[sub_cat["high_stress_group"] == 1]
        if len(high_row) == 0:
            high_count = 0
        else:
            high_count = int(high_row["count"].iloc[0])

        high_percent = (high_count / total_count * 100) if total_count > 0 else 0.0

        rows.append(
            {
                "change_label": cat,
                "high_stress_percent": high_percent,
                "high_stress_count": high_count,
                "total_count": int(total_count),
            }
        )

    viz_df = pd.DataFrame(rows)

    print("\n=== 可视化用宽表预览 ===")
    print(viz_df)

    viz_path = OUT_DIR_VIZ / "viz_satisfaction_change_high_stress.csv"
    viz_df.to_csv(viz_path, index=False)
    print("\n已保存可视化用 CSV 到:", viz_path)
    print("\n脚本完成。")


if __name__ == "__main__":
    main()
