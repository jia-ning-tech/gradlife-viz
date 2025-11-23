#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
41_check_satisfaction_change.py

目的：
  - 检查 Q26（v073 / v073_code）“满意度变化”的原始分布
  - 解析元数据的 value_labels，看清楚每个 code 对应的文本
  - 粗略看一下不同比例在 high_stress_group 中的分布，为后面分档和可视化做准备
"""

import pandas as pd
import json
from pathlib import Path

DATA_PATH = Path("/workspace/output/02_typed_clean/data_step2_typed_clean.csv")
META_PATH = Path("/workspace/output/02_typed_clean/metadata_step2_typed_clean.csv")
WORKLIFE_DERIVED_PATH = Path("/workspace/output/04_worklife/worklife_derived_vars.csv")


def parse_value_labels(val):
    """把 metadata 里的 value_labels 字符串安全地解析成 dict。"""
    if pd.isna(val):
        return {}
    if isinstance(val, dict):
        return val
    try:
        return json.loads(val)
    except Exception:
        return {}


def main():
    print("读取主数据与 metadata ...")
    df = pd.read_csv(DATA_PATH)
    meta = pd.read_csv(META_PATH)

    # 读取 high_stress_group（来自之前的 worklife_derived_vars）
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
        print("警告：未找到 worklife_derived_vars.csv，后面无法做与 high_stress_group 的交叉。")

    print("\n数据形状:", df.shape)

    # 我们关心的列
    cols_to_check = ["v073", "v073_code", "v073_num"]
    existing_cols = [c for c in cols_to_check if c in df.columns]

    print("\n=== 存在的与 Q26 相关的列 ===")
    print(existing_cols)

    # --- 1) 打印前几行看看原始数据 ---
    for col in existing_cols:
        print("\n----------------------------------------")
        print(f"列: {col}")
        print(df[col].head(10))

    # --- 2) 从 metadata 里找 v073 / v073_code 的信息 ---
    print("\n=== metadata 中关于 Q26 的条目 ===")
    meta_q26 = meta[meta["q_no"] == "Q26"]
    if meta_q26.empty:
        print("在 metadata 中没有找到 q_no == 'Q26' 的记录，请检查。")
    else:
        print(meta_q26[["col_name", "q_no", "q_type", "question_text", "value_labels"]])

    # 尝试专门抓 v073_code 的元数据（一般带有 value_labels）
    meta_v073_code = meta_q26[meta_q26["col_name"] == "v073_code"]
    if not meta_v073_code.empty:
        row = meta_v073_code.iloc[0]
        print("\n=== v073_code 详细元数据 ===")
        print("col_name:", row.get("col_name"))
        print("q_no:", row.get("q_no"))
        print("q_type:", row.get("q_type"))
        print("question_text:", row.get("question_text"))
        print("raw value_labels:", row.get("value_labels"))

        label_dict = parse_value_labels(row.get("value_labels"))
        if label_dict:
            print("\n=== 解析后的标签字典 ===")
            # value_labels 一般是 {"1": "xxx", "2": "yyy"}，key 是字符串
            for k, v in label_dict.items():
                print(f"{k} -> {v}")
        else:
            print("\n没有成功解析 value_labels。")
    else:
        print("\n没有单独找到 col_name == 'v073_code' 的元数据记录。")

    # --- 3) 看看 v073 / v073_code 的分布 ---
    if "v073" in df.columns:
        print("\n=== v073 原始文本分布（前 20 项） ===")
        print(df["v073"].value_counts(dropna=False).head(20))

    if "v073_code" in df.columns:
        print("\n=== v073_code 数值分布（前 20 项） ===")
        print(df["v073_code"].value_counts(dropna=False).head(20))

    if "v073_num" in df.columns:
        print("\n=== v073_num 数值分布（前 20 项） ===")
        print(df["v073_num"].value_counts(dropna=False).head(20))

    # --- 4) 粗略看一下与 high_stress_group 的关系 ---
    if "high_stress_group" in df.columns and "v073_code" in df.columns:
        print("\n=== v073_code × high_stress_group 交叉（按 v073_code 内部百分比） ===")
        cross = (
            df.dropna(subset=["v073_code", "high_stress_group"])
            .groupby(["v073_code", "high_stress_group"])
            .size()
            .reset_index(name="count")
        )
        # 计算每个 v073_code 内部的百分比
        cross["percent_within_v073"] = (
            cross["count"] / cross.groupby("v073_code")["count"].transform("sum") * 100
        )

        print(cross)

        # 如果有标签字典，就顺手贴上文本
        if "label_dict" in locals() and label_dict:
            # 把 code 转成 int 再映射
            def map_label(x):
                key = str(int(x)) if pd.notna(x) else None
                return label_dict.get(key, key)

            cross["v073_label"] = cross["v073_code"].map(map_label)
            print("\n=== 带文本标签的交叉表（预览） ===")
            print(
                cross[["v073_code", "v073_label", "high_stress_group", "count", "percent_within_v073"]]
            )
    else:
        print("\n缺少 v073_code 或 high_stress_group，暂时无法做交叉分析。")

    print("\n检查完成。")


if __name__ == "__main__":
    main()
