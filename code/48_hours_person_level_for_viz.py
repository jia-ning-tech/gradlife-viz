#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
48_hours_person_level_for_viz.py

目标：
- 生成一份按“受访者级别”的工时 × 高压数据，包含：
    degree_label（学位）
    region_continent（大洲）
    country_name（目前占位，若无国家信息则为缺失）
    hours_level（工时档位）
    hours_order（工时排序用）
    high_stress_group（0/1）
    high_stress_label（文本）

- 前端可以基于这张明细表，按 degree / region / country 过滤，并即时聚合。

输入：
- /workspace/output/04_worklife/worklife_derived_vars.csv
    （包含 hours_level, high_stress_group, v004_code 等）
- /workspace/output/05_region/region_worklife_derived.csv （含 region_continent，若存在）

输出：
- /workspace/output/08_viz_data/viz_hours_person_level.csv
"""

from pathlib import Path
import pandas as pd

BASE = Path("/workspace")

PATH_WORKLIFE = BASE / "output/04_worklife/worklife_derived_vars.csv"
PATH_REGION = BASE / "output/05_region/region_worklife_derived.csv"

VIZ_DIR = BASE / "output/08_viz_data"
VIZ_DIR.mkdir(parents=True, exist_ok=True)

HOURS_COL = "hours_level"
STRESS_COL = "high_stress_group"
DEGREE_CODE_COL = "v004_code"     # 学位代码（1/2/3）
DEGREE_LABEL_COL = "degree_label"
REGION_COL = "region_continent"


def build_hours_order(values):
    """
    为 hours_level 构造排序。
    - 如果取值是 low / medium / high / very_high，就固定为
      low(0) < medium(1) < high(2) < very_high(3)。
    - 否则退回到简单的字母排序。
    """
    ser = pd.Series(values).dropna()
    unique_vals = list(ser.unique())
    norm = [str(v).strip().lower() for v in unique_vals]
    simple_set = set(norm)
    target_order = ["low", "medium", "high", "very_high"]

    # 情况一：就是我们预期的四档
    if simple_set.issubset(set(target_order)):
        order_map = {}
        for idx, cat in enumerate(target_order):
            for raw in unique_vals:
                if str(raw).strip().lower() == cat:
                    order_map[raw] = idx
        return order_map

    # 情况二：其他情况，退回字母排序（保险兜底）
    ordered = sorted(unique_vals, key=lambda x: str(x))
    return {v: i for i, v in enumerate(ordered)}



def main():
    print("读取 worklife_derived_vars ...")
    wl = pd.read_csv(PATH_WORKLIFE)
    print("worklife_derived_vars 形状:", wl.shape)

    # 尝试读取 region_worklife_derived（若不存在则略过）
    try:
        print("读取 region_worklife_derived ...")
        region = pd.read_csv(PATH_REGION)
        print("region_worklife_derived 形状:", region.shape)
    except FileNotFoundError:
        print(f"WARNING: 找不到 {PATH_REGION}，将仅使用 worklife_derived_vars（没有 region 维度）")
        region = None

    # 检查 worklife 中必须存在的列
    required_cols = [HOURS_COL, STRESS_COL, DEGREE_CODE_COL]
    missing_in_wl = [c for c in required_cols if c not in wl.columns]
    if missing_in_wl:
        raise KeyError(
            "在 worklife_derived_vars.csv 中找不到必需列："
            + ", ".join(missing_in_wl)
            + "。请检查 05_worklife_analysis 的输出。"
        )

    # 如果有 region 表，并且行数与 wl 相同，则按行对齐 concat
    if region is not None and len(region) == len(wl):
        print("按行对齐方式合并 worklife_derived_vars 与 region_worklife_derived ...")
        df = pd.concat(
            [wl.reset_index(drop=True), region[[REGION_COL]].reset_index(drop=True)],
            axis=1,
        )
    else:
        if region is not None:
            print(
                f"WARNING: region_worklife_derived 行数({len(region)}) ≠ worklife_derived_vars 行数({len(wl)})，"
                "将忽略 region，后续 region_continent 统一为 'All / unknown'"
            )
        df = wl.copy()

    # 只保留我们需要的列（后面会新增 degree_label / country_name 等）
    keep_cols = [HOURS_COL, STRESS_COL, DEGREE_CODE_COL]
    if REGION_COL in df.columns:
        keep_cols.append(REGION_COL)

    sub = df[keep_cols].copy()

    # 去除工时/高压缺失
    before = len(sub)
    sub = sub.dropna(subset=[HOURS_COL, STRESS_COL])
    after = len(sub)
    print(f"去除工时/高压缺失后样本量: {after}（删除 {before - after} 行）")

    # 构造 hours_order
    hours_order_map = build_hours_order(sub[HOURS_COL])
    sub["hours_order"] = sub[HOURS_COL].map(hours_order_map)

    # high_stress_group 保证为 0/1 Int
    sub[STRESS_COL] = pd.to_numeric(sub[STRESS_COL], errors="coerce").astype("Int64")
    sub["high_stress_label"] = sub[STRESS_COL].map({0: "Non-high-stress", 1: "High-stress"})

    # 构造 degree_label（仿照 46_support_quadrant_by_deg_region.py）
    code = pd.to_numeric(sub[DEGREE_CODE_COL], errors="coerce")
    sub["degree_code_int"] = code.round().astype("Int64")
    degree_map = {
        1: "Doctorate",
        2: "Master's",
        3: "Dual degree",
    }
    sub[DEGREE_LABEL_COL] = sub["degree_code_int"].map(degree_map)

    # 处理 region / country 占位
    if REGION_COL not in sub.columns:
        sub[REGION_COL] = "All / unknown"

    # 目前还没有干净的国家变量，先给一个占位列，方便前端统一处理
    sub["country_name"] = pd.NA

    # 输出
    out_path = VIZ_DIR / "viz_hours_person_level.csv"
    cols_out = [
        DEGREE_LABEL_COL,
        REGION_COL,
        "country_name",
        HOURS_COL,
        "hours_order",
        STRESS_COL,
        "high_stress_label",
    ]
    sub[cols_out].to_csv(out_path, index=False)
    print("已保存按人级别工时 × 高压数据到:", out_path)
    print("示例前几行：")
    print(sub[cols_out].head())


if __name__ == "__main__":
    main()
