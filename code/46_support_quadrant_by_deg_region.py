#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
46_support_quadrant_by_deg_region.py

目标：
- 在已有「导师支持 × 机构支持 四象限」的基础上，
  加上「学位类型」和「大洲/地区」两个维度。
- 输出一个长表，包含：
    degree_label, region_continent,
    supervisor_cat (Low/Medium/High),
    institution_cat (Low/Medium/High),
    quadrant_label,
    total_count, high_stress_count, non_high_stress_count,
    high_stress_percent, non_high_stress_percent
- 供前端做：
    * 3×3 热图（可按学位 / 地区过滤）
    * 排名条形图等多种可视化。

假设前置文件：
- /workspace/output/02_typed_clean/data_step2_typed_clean.csv
- /workspace/output/03_worklife/worklife_derived_vars.csv
    （至少包含 high_stress_group）
- /workspace/output/05_region/region_worklife_derived.csv
    （至少包含 region_continent）

注意：
- 不再尝试通过 ID 列 merge，而是假设三张表行顺序一致，
  用 reset_index + concat 进行列拼接（和之前大部分脚本一致）。
"""

from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path("/workspace")

PATH_MAIN = BASE_DIR / "output/02_typed_clean/data_step2_typed_clean.csv"
PATH_WORKLIFE = BASE_DIR / "output/04_worklife/worklife_derived_vars.csv"
PATH_REGION = BASE_DIR / "output/05_region/region_worklife_derived.csv"

OUT_ANALYSIS = BASE_DIR / "output/07_support/support_quadrant_by_deg_region_high_stress.csv"
OUT_VIZ = BASE_DIR / "output/08_viz_data/viz_support_quadrant_by_deg_region_high_stress.csv"


def zscore(s: pd.Series) -> pd.Series:
    """简单 z-score，忽略缺失。"""
    return (s - s.mean()) / s.std(ddof=0)


def build_support_indices(df: pd.DataFrame) -> pd.DataFrame:
    """
    在主数据上构建：
    - supervisor_index_z（导师支持 z 分）
    - institution_index_z（机构支持 z 分）
    - supervisor_cat / institution_cat：Low / Medium / High
    """

    # 这些列名是之前脚本里用过的数值列，如果你的列名不同，
    # 可以在这里调整一下即可。
    # Q27.f overall supervisor relationship
    # Q32.a career conversations with supervisor
    supervisor_cols = ["v079_num", "v091_num"]

    # Q35.a/d/e mental-health & work–life support items
    institution_cols = ["v097_num", "v100_num", "v101_num"]

    missing_sup = [c for c in supervisor_cols if c not in df.columns]
    missing_inst = [c for c in institution_cols if c not in df.columns]
    if missing_sup or missing_inst:
        raise KeyError(
            "以下支持指数所需的列在主数据中不存在，请检查列名并在脚本中修正：\n"
            f"  supervisor_cols 缺失: {missing_sup}\n"
            f"  institution_cols 缺失: {missing_inst}"
        )

    df["supervisor_index_raw"] = df[supervisor_cols].mean(axis=1)
    df["institution_index_raw"] = df[institution_cols].mean(axis=1)

    df["supervisor_index_z"] = zscore(df["supervisor_index_raw"])
    df["institution_index_z"] = zscore(df["institution_index_raw"])

    # 以 tertile（1/3, 2/3 分位）划分 Low / Medium / High
    sup_q = df["supervisor_index_z"].quantile([1 / 3, 2 / 3])
    inst_q = df["institution_index_z"].quantile([1 / 3, 2 / 3])

    def cut_to_cat(z, q_low, q_high):
        if pd.isna(z):
            return pd.NA
        if z <= q_low:
            return "Low"
        if z >= q_high:
            return "High"
        return "Medium"

    df["supervisor_cat"] = df["supervisor_index_z"].apply(
        lambda v: cut_to_cat(v, sup_q.iloc[0], sup_q.iloc[1])
    )
    df["institution_cat"] = df["institution_index_z"].apply(
        lambda v: cut_to_cat(v, inst_q.iloc[0], inst_q.iloc[1])
    )

    df["quadrant_label"] = (
        df["supervisor_cat"].astype("string")
        + " supervisor / "
        + df["institution_cat"].astype("string")
        + " institution"
    )

    return df


def add_degree_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    从 v004_code 构造学位分类：
    1 -> Doctorate
    2 -> Master's
    3 -> Dual doctorate
    """

    if "v004_code" not in df.columns:
        raise KeyError("主数据中缺少 v004_code（学位类型编码）列，请确认列名。")

    code = pd.to_numeric(df["v004_code"], errors="coerce")
    df["degree_code_int"] = code

    degree_map = {
        1: "Doctorate",
        2: "Master's",
        3: "Dual degree",
    }
    df["degree_label"] = df["degree_code_int"].map(degree_map)

    return df


def load_master_with_support_deg_region() -> pd.DataFrame:
    """读入三张表，按行对齐拼接，并构建所需的派生变量。"""

    print("读取主数据 ...")
    df_main = pd.read_csv(PATH_MAIN)
    print("主数据形状:", df_main.shape)

    print("读取 worklife_derived_vars（含 high_stress_group）...")
    df_worklife = pd.read_csv(PATH_WORKLIFE)
    print("worklife_derived_vars 形状:", df_worklife.shape)

    print("读取 region_worklife_derived（含 region_continent）...")
    df_region = pd.read_csv(PATH_REGION)
    print("region_worklife_derived 形状:", df_region.shape)

    n_main, n_work, n_reg = len(df_main), len(df_worklife), len(df_region)
    if not (n_main == n_work == n_reg):
        raise ValueError(
            f"三张表行数不一致，无法按行拼接：\n"
            f"  main: {n_main} 行\n  worklife: {n_work} 行\n  region: {n_reg} 行\n"
            "请检查前置处理是否丢行或重新排序。"
        )

    # 按行顺序对齐拼接
    df = pd.concat(
        [
            df_main.reset_index(drop=True),
            df_worklife[["high_stress_group"]].reset_index(drop=True),
            df_region[["region_continent"]].reset_index(drop=True),
        ],
        axis=1,
    )

    print("合并完成后数据形状:", df.shape)
    print("high_stress_group 分布:")
    print(df["high_stress_group"].value_counts(dropna=False))

    # 构建学位标签
    df = add_degree_labels(df)

    # 构建支持四象限
    df = build_support_indices(df)

    return df


def make_quadrant_agg(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    根据 degree_label / region_continent / supervisor_cat / institution_cat
    汇总高压 / 非高压人数及百分比。
    """

    # 只保留我们需要且不缺失的行
    keep_cols = [
        "high_stress_group",
        "degree_label",
        "region_continent",
        "supervisor_cat",
        "institution_cat",
        "quadrant_label",
    ]
    df_sub = df[keep_cols].copy()

    df_sub = df_sub.dropna(
        subset=[
            "high_stress_group",
            "degree_label",
            "region_continent",
            "supervisor_cat",
            "institution_cat",
        ]
    )

    # high_stress_group 转成 0/1
    df_sub["high_stress_group"] = pd.to_numeric(
        df_sub["high_stress_group"], errors="coerce"
    ).astype("Int64")

    df_sub = df_sub.dropna(subset=["high_stress_group"])

    print("\n用于四象限 × 学位 × 地区 分析的有效样本量:", len(df_sub))

    group_cols = [
        "degree_label",
        "region_continent",
        "supervisor_cat",
        "institution_cat",
        "quadrant_label",
    ]

    agg = (
        df_sub.groupby(group_cols, dropna=False)["high_stress_group"]
        .agg(
            total_count="size",
            high_stress_count="sum",
        )
        .reset_index()
    )

    agg["non_high_stress_count"] = agg["total_count"] - agg["high_stress_count"]
    agg["high_stress_percent"] = (
        agg["high_stress_count"] / agg["total_count"] * 100.0
    )
    agg["non_high_stress_percent"] = 100.0 - agg["high_stress_percent"]

    # 排序一下，方便阅读：按学位、地区、supervisor_cat、institution_cat
    cat_order = {"Low": 0, "Medium": 1, "High": 2}
    agg["sup_order"] = agg["supervisor_cat"].map(cat_order)
    agg["inst_order"] = agg["institution_cat"].map(cat_order)

    agg = agg.sort_values(
        [
            "degree_label",
            "region_continent",
            "sup_order",
            "inst_order",
        ]
    ).reset_index(drop=True)

    agg = agg.drop(columns=["sup_order", "inst_order"])

    print("\n=== 四象限 × 学位 × 地区 汇总表预览（前 12 行） ===")
    print(agg.head(12))

    return agg


def main():
    df = load_master_with_support_deg_region()
    agg = make_quadrant_agg(df)

    # 保存分析版（含所有列）
    OUT_ANALYSIS.parent.mkdir(parents=True, exist_ok=True)
    OUT_VIZ.parent.mkdir(parents=True, exist_ok=True)

    agg.to_csv(OUT_ANALYSIS, index=False)
    print("\n已保存分析用四象限 × 学位 × 地区汇总表到:", OUT_ANALYSIS)

    # 可视化版可以先用同一张表，前端按需筛选
    viz_cols = [
        "degree_label",
        "region_continent",
        "supervisor_cat",
        "institution_cat",
        "quadrant_label",
        "total_count",
        "high_stress_count",
        "non_high_stress_count",
        "high_stress_percent",
        "non_high_stress_percent",
    ]
    agg[viz_cols].to_csv(OUT_VIZ, index=False)
    print("已保存可视化用四象限 × 学位 × 地区汇总表到:", OUT_VIZ)


if __name__ == "__main__":
    main()
