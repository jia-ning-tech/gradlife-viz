#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
43_mental_help_vs_worklife_by_degree.py

心理健康求助 (v095_code) × 高压组 (high_stress_group) × 学位类型 (v004_code)
导出长表，供后续可视化 / 分学位对比使用。
"""

from pathlib import Path
import pandas as pd
import json

BASE_DIR = Path("/workspace")
OUTPUT_DIR = BASE_DIR / "output"

# 跟之前所有脚本保持一致的路径
DATA_PATH = OUTPUT_DIR / "02_typed_clean" / "data_step2_typed_clean.csv"
META_PATH = OUTPUT_DIR / "02_typed_clean" / "metadata_step2_typed_clean.csv"
WORKLIFE_DERIVED_PATH = OUTPUT_DIR / "04_worklife" / "worklife_derived_vars.csv"

OUT_LONG = OUTPUT_DIR / "06_mental_health" / "mental_help_vs_high_stress_by_degree.csv"


def parse_value_labels(meta_df: pd.DataFrame, col_name: str) -> dict:
    """
    从 metadata 中取出某个变量的 value_labels（JSON 字符串），解析成 {int: str} 字典。
    """
    row = meta_df.loc[meta_df["col_name"] == col_name]
    if row.empty:
        raise ValueError(f"在 metadata 中找不到 {col_name} 的元数据。")

    row = row.iloc[0]
    raw = row.get("value_labels", "")

    print(f"\n=== {col_name} 元数据 ===")
    print(f"col_name: {row['col_name']}")
    print(f"q_no: {row['q_no']}")
    print(f"q_type: {row['q_type']}")
    print("question_text:", row["question_text"])
    print("raw value_labels:", raw)

    mapping = {}
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            for k, v in parsed.items():
                try:
                    code_int = int(k)
                except ValueError:
                    continue
                mapping[code_int] = v
        except Exception as e:
            print("解析 value_labels JSON 出错:", e)

    print(f"\n=== 解析后的 {col_name} 标签字典 ===")
    for k, v in mapping.items():
        print(f"{k} -> {v}")
    return mapping


def main():
    print("读取主数据与 worklife 衍生变量 ...")
    df_main = pd.read_csv(DATA_PATH)
    df_worklife = pd.read_csv(WORKLIFE_DERIVED_PATH)

    print("主数据形状:", df_main.shape)
    print("worklife_derived_vars 形状:", df_worklife.shape)

    # 我们之前的脚本都是假设两张表的行顺序一致，这里沿用同样假设
    if len(df_main) != len(df_worklife):
        raise ValueError("主数据与 worklife_derived_vars 行数不一致，请检查。")

    # 把 high_stress_group 和 v004_code 从 worklife_derived_vars / 主数据 拿到一个统一 df 里
    df = df_main.copy()
    if "high_stress_group" not in df_worklife.columns:
        raise ValueError("在 worklife_derived_vars 中找不到 high_stress_group 列。")

    df["high_stress_group"] = df_worklife["high_stress_group"]

    # 简单检查：高压分布
    print("\n=== high_stress_group 分布 ===")
    print(df["high_stress_group"].value_counts(dropna=False))

    # 只保留我们需要的几个变量
    needed_cols = ["v004_code", "v095_code", "high_stress_group"]
    missing = [c for c in needed_cols if c not in df.columns]
    if missing:
        raise ValueError(f"主数据中缺少列: {missing}")

    df_sub = df[needed_cols].copy()
    print("\n子集数据形状:", df_sub.shape)

    # 读取 metadata，用来解析学位和心理求助标签
    meta = pd.read_csv(META_PATH)

    # 学位标签映射 (v004_code)
    degree_label_map = parse_value_labels(meta, "v004_code")

    # 心理健康求助标签映射 (v095_code)
    help_label_map = parse_value_labels(meta, "v095_code")

    # 处理学位代码：v004_code 是 float(1.0/2.0/3.0)，转成 Int64 再贴标签
    df_sub["degree_code_int"] = df_sub["v004_code"].round().astype("Int64")
    df_sub["degree_label"] = df_sub["degree_code_int"].map(degree_label_map)

    print("\n=== 学位类型分布（degree_code_int × degree_label） ===")
    print(
        df_sub.groupby(["degree_code_int", "degree_label"], dropna=False)["v004_code"]
        .count()
        .reset_index(name="count")
    )

    # 处理心理健康求助：v095_code -> Int -> help_label
    df_sub["help_code_int"] = df_sub["v095_code"].round().astype("Int64")
    df_sub["help_label"] = df_sub["help_code_int"].map(help_label_map)

    print("\n=== 心理健康求助 help_label 分布（含缺失） ===")
    print(df_sub["help_label"].value_counts(dropna=False))

    # 只保留 help_label、degree_code_int、high_stress_group 都非缺失的样本
    df_valid = df_sub[
        df_sub["help_label"].notna()
        & df_sub["degree_code_int"].notna()
        & df_sub["high_stress_group"].notna()
    ].copy()

    df_valid["high_stress_group"] = df_valid["high_stress_group"].astype(int)

    print(
        "\n有效样本量（help_label & degree & high_stress_group 都非缺失）:",
        len(df_valid),
    )

    # 分组统计：help_label × degree × high_stress_group
    group_cols = ["help_label", "degree_code_int", "degree_label", "high_stress_group"]
    df_ct = (
        df_valid.groupby(group_cols)["v004_code"]
        .count()
        .reset_index(name="count")
    )

    # 在每个 help_label × degree 内部算“高压/非高压”的百分比
    df_ct["percent_within_help_degree"] = (
        df_ct.groupby(["help_label", "degree_code_int"])["count"]
        .transform(lambda x: x / x.sum() * 100)
    )

    # 排序：按 help_label、degree，然后 high_stress_group=0/1
    df_ct = df_ct.sort_values(
        by=["help_label", "degree_code_int", "high_stress_group"]
    ).reset_index(drop=True)

    print("\n=== 心理健康求助 × 高压组 × 学位类型 交叉表（预览） ===")
    print(df_ct.head(20))

    # 保存
    OUT_LONG.parent.mkdir(parents=True, exist_ok=True)
    df_ct.to_csv(OUT_LONG, index=False)
    print("\n已保存心理健康求助 × 高压组 × 学位类型交叉表到:")
    print(" ", OUT_LONG)


if __name__ == "__main__":
    main()
