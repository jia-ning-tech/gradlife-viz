#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
97_add_country_gender_labels_to_master.py  (修正版)

用途：
- 在 master_person_wide 上补充两个“可筛选维度”：
  1) country_name        （从 /output/05_region/region_worklife_derived.csv 拿）
  2) gender_label        （其实是 Q52.a: How well is your degree preparing you..., 不是性别）

⚠️ 注意：
- 目前数据和 metadata 显示，v197/v197_num 对应的是 Q52.a（学位准备程度自评），
  并非 Gender。为了不打断你现有的代码，我们暂时保留列名 gender_code/gender_label，
  但在分析和界面上请把它理解为“degree_preparedness”（学位准备程度），
  后面如果你愿意，我们可以再写一个脚本把列名改得更准确。

依赖文件：
- /workspace/output/99_master/master_person_wide.csv
- /workspace/output/05_region/region_worklife_derived.csv   （用于 country_name）
- /workspace/output/02_typed_clean/data_step2_typed_clean.csv

输出：
- 更新后的 master_person_wide.csv
- 更新后的 master_person_wide.parquet
"""

from pathlib import Path
import pandas as pd

BASE = Path("/workspace")

PATH_MASTER = BASE / "output" / "99_master" / "master_person_wide.csv"
PATH_MASTER_PARQUET = BASE / "output" / "99_master" / "master_person_wide.parquet"

# ✅ 修正路径：region_worklife_derived 在 05_region 目录下
PATH_REGION = BASE / "output" / "05_region" / "region_worklife_derived.csv"

PATH_TYPED = BASE / "output" / "02_typed_clean" / "data_step2_typed_clean.csv"


def add_country_name(master: pd.DataFrame) -> pd.DataFrame:
    """
    如果 region_worklife_derived 存在且包含 country_name，
    按行号对齐，添加 country_name 列。
    """
    if not PATH_REGION.exists():
        print(f"⚠️ 未找到 {PATH_REGION}，将跳过 country_name 的合并。")
        return master

    region = pd.read_csv(PATH_REGION)
    print("region_worklife_derived 形状:", region.shape)
    print("region_worklife_derived 列名示例:", list(region.columns)[:10])

    # 按行对齐
    if len(region) != len(master):
        print("⚠️ region_worklife_derived 行数与 master 不一致，将按最小行数截断对齐。")
        n = min(len(region), len(master))
        region = region.iloc[:n].reset_index(drop=True)
        master = master.iloc[:n].reset_index(drop=True)
    else:
        region = region.reset_index(drop=True)
        master = master.reset_index(drop=True)

    if "country_name" not in region.columns:
        print("⚠️ region_worklife_derived 中没有 country_name 列，将跳过 country_name。")
        return master

    master["country_name"] = region["country_name"]
    print("✅ 已按行对齐方式添加 country_name 列。")
    return master


def add_gender_like_label(master: pd.DataFrame) -> pd.DataFrame:
    """
    通过 typed_clean 中的 v197/v197_num 关系，构造一个文字标签列。
    ⚠️ 这实际上是 Q52.a（学位准备程度自评），不是性别。

    - master.gender_code 已经由之前的脚本 92_add_demographics_to_master.py 填成 v197_num
    - 这里我们只是在 master 上补充一个对应的文字版本 gender_label
    """
    if "gender_code" not in master.columns:
        print("⚠️ master_person_wide 中没有 gender_code 列，将跳过 gender_label。")
        return master

    if not PATH_TYPED.exists():
        print(f"⚠️ 未找到 {PATH_TYPED}，无法从 typed_clean 推断 gender_label。")
        return master

    typed = pd.read_csv(PATH_TYPED)
    print("data_step2_typed_clean 形状:", typed.shape)
    print("data_step2_typed_clean 列名示例:", list(typed.columns)[:15])

    if ("v197_num" in typed.columns) and ("v197" in typed.columns):
        print("使用 v197_num 与 v197 之间的关系构造 gender_label 映射（实际是 Q52.a 学位准备程度）...")
        mapping_df = (
            typed[["v197_num", "v197"]]
            .dropna()
            .drop_duplicates()
            .sort_values("v197_num")
        )
        print("v197 映射表：")
        print(mapping_df.to_string(index=False))

        mapping = mapping_df.set_index("v197_num")["v197"].to_dict()
        master["gender_label"] = master["gender_code"].map(mapping)

        n_missing = master["gender_label"].isna().sum()
        if n_missing > 0:
            print(f"⚠️ 有 {n_missing} 行 gender_code 未在 v197 映射中找到对应文字，将填为 'Unknown gender-like label'.")
            master["gender_label"] = master["gender_label"].fillna("Unknown gender-like label")

        print("✅ 已在 master 中添加 gender_label 列（注意：这是 Q52.a 学位准备程度，不是性别）。")
        return master

    print("⚠️ typed_clean 中未同时找到 v197_num 和 v197，将跳过 gender_label。")
    return master


def main():
    # === 1. 读取 master_person_wide ===
    print("读取 master_person_wide ...")
    master = pd.read_csv(PATH_MASTER)
    print("master_person_wide 形状:", master.shape)
    print("master_person_wide 列名示例:", list(master.columns)[:20])

    # === 2. 添加 country_name ===
    master = add_country_name(master)

    # === 3. 添加 gender_label（实际是 Q52.a 学位准备程度） ===
    master = add_gender_like_label(master)

    # === 4. 预览新增列 ===
    preview_cols = [c for c in [
        "resp_id",
        "degree_label",
        "region_continent",
        "country_name",
        "gender_code",
        "gender_label",
        "high_stress_group"
    ] if c in master.columns]

    print("\n=== master_person_wide 新增列预览（前 10 行）===")
    print(master[preview_cols].head(10).to_string(index=False))

    if "country_name" in master.columns:
        n_country_non_missing = master["country_name"].notna().sum()
        print(f"\ncountry_name 非缺失样本量: {n_country_non_missing}")
        print("country_name 示例类别：", master["country_name"].dropna().unique()[:10])

    if "gender_label" in master.columns:
        n_gender_non_missing = master["gender_label"].notna().sum()
        print(f"\ngender_label 非缺失样本量: {n_gender_non_missing}")
        print("gender_label 分布（实际是 Q52.a 学位准备程度）：")
        print(master["gender_label"].value_counts(dropna=False))

    # === 5. 保存 ===
    master.to_csv(PATH_MASTER, index=False)
    print(f"\n已更新并保存 master_person_wide 到: {PATH_MASTER}")

    try:
        master.to_parquet(PATH_MASTER_PARQUET, index=False)
        print(f"已更新 master_person_wide.parquet 到: {PATH_MASTER_PARQUET}")
    except Exception as e:
        print(f"⚠️ 保存 Parquet 时出错（可忽略，仅 CSV 必须成功）：{e}")


if __name__ == "__main__":
    main()
