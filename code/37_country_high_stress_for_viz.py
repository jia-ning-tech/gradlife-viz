#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从 region_worklife_derived 行级数据里，整理出「国家 × 高压」的可视化用宽表：
- 输入:  /workspace/output/05_region/region_worklife_derived.csv
- 输出:  /workspace/output/08_viz_data/viz_country_high_stress.csv

输出列：
- region_continent   （六大洲/地区）
- country_name       （国家/地区名称）
- high_stress_count
- high_stress_percent
- non_high_stress_count
- non_high_stress_percent
- total_count
"""

from pathlib import Path
import pandas as pd


BASE_DIR = Path("/workspace")
INPUT_PATH = BASE_DIR / "output" / "05_region" / "region_worklife_derived.csv"
VIZ_DIR = BASE_DIR / "output" / "08_viz_data"
VIZ_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_VIZ = VIZ_DIR / "viz_country_high_stress.csv"


def main():
    print("读取行级数据:", INPUT_PATH)
    df = pd.read_csv(INPUT_PATH)

    print("原始数据形状:", df.shape)

    # 检查需要的列
    needed_cols = [
        "high_stress_group",
        "region_continent",
        "v031",  # Asia
        "v032",  # Australasia
        "v033",  # Africa
        "v034",  # Europe
        "v035",  # North / Central America
        "v036",  # South America
    ]
    missing = [c for c in needed_cols if c not in df.columns]
    if missing:
        raise ValueError(f"缺少必要列: {missing}")

    # 1) 构造 country_name：在六个国家变量中选出非缺失的那个
    country_cols = ["v031", "v032", "v033", "v034", "v035", "v036"]
    # 行内从左到右回填，然后取第一个非空
    df["country_name"] = (
        df[country_cols]
        .bfill(axis=1)
        .iloc[:, 0]
    )

    # 有些行可能全部为空（region_continent 也可能是 <NA>），统一视为缺失
    df.loc[df["country_name"].isna(), "country_name"] = pd.NA

    print("\n=== country_name 分布（前 20 项）===")
    print(df["country_name"].value_counts(dropna=False).head(20))

    # 只保留 high_stress_group 非缺失、country_name 非缺失、region_continent 非缺失 的行
    sub = df.dropna(subset=["high_stress_group", "country_name", "region_continent"])
    print("\n有效样本量（国家和高压组都不缺失）:", len(sub))

    # 2) 计算 「国家 × 高压组」的计数和组内百分比
    grp = (
        sub.groupby(
            ["region_continent", "country_name", "high_stress_group"], dropna=False
        )["high_stress_group"]
        .size()
        .reset_index(name="count")
    )

    # 组内（某个国家内）总样本
    grp["total_in_country"] = grp.groupby(
        ["region_continent", "country_name"]
    )["count"].transform("sum")

    grp["percent_within_country"] = grp["count"] / grp["total_in_country"] * 100

    print("\n=== 国家 × 高压组（长表，前 20 行）===")
    print(grp.head(20))

    # 3) 转成宽表：一行一个国家
    # high_stress_group: 0 = 非高压, 1 = 高压
    # 先透视 count
    pivot_counts = grp.pivot_table(
        index=["region_continent", "country_name"],
        columns="high_stress_group",
        values="count",
        fill_value=0,
    )

    pivot_counts = pivot_counts.rename(
        columns={
            0: "non_high_stress_count",
            1: "high_stress_count",
        }
    )

    # 如果某些国家没有某一类（全是高压或全是非高压），上面的 rename 会缺列，这里补齐
    for col in ["non_high_stress_count", "high_stress_count"]:
        if col not in pivot_counts.columns:
            pivot_counts[col] = 0

    pivot_counts = pivot_counts.reset_index()

    # 计算总样本 & 百分比
    pivot_counts["total_count"] = (
        pivot_counts["non_high_stress_count"] + pivot_counts["high_stress_count"]
    ).astype(int)

    # 避免除 0
    pivot_counts["high_stress_percent"] = (
        pivot_counts["high_stress_count"] / pivot_counts["total_count"].where(
            pivot_counts["total_count"] != 0, pd.NA
        )
        * 100
    )

    pivot_counts["non_high_stress_percent"] = (
        pivot_counts["non_high_stress_count"] / pivot_counts["total_count"].where(
            pivot_counts["total_count"] != 0, pd.NA
        )
        * 100
    )

    # 排序：先按大洲，再按总样本量（从大到小）
    pivot_counts = pivot_counts.sort_values(
        by=["region_continent", "total_count"], ascending=[True, False]
    ).reset_index(drop=True)

    print("\n=== 可视化用宽表（前 20 行）===")
    print(
        pivot_counts[
            [
                "region_continent",
                "country_name",
                "high_stress_count",
                "high_stress_percent",
                "non_high_stress_count",
                "non_high_stress_percent",
                "total_count",
            ]
        ].head(20)
    )

    # 4) 输出到 08_viz_data
    viz_df = pivot_counts[
        [
            "region_continent",
            "country_name",
            "high_stress_count",
            "high_stress_percent",
            "non_high_stress_count",
            "non_high_stress_percent",
            "total_count",
        ]
    ].copy()

    viz_df.to_csv(OUTPUT_VIZ, index=False, encoding="utf-8-sig")
    print("\n已导出可视化用的 国家×高压 数据到:", OUTPUT_VIZ)


if __name__ == "__main__":
    main()
