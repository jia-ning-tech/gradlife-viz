#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
95_export_viz_satisfaction_by_deg_region.py

用途：
- 基于 master_person_wide + satisfaction_long，
  生成“各方面满意度 × 高压组 × 学位 × 地区（大洲）”的汇总表，
  供后续前端可视化使用（例如：按学位/地区对比各维度满意度的高压/非高压差异）。

一行 = 一个 (满意度维度 × 高压组 × 学位 × 地区) 组合。

输出：
1) 分析用汇总表：
   /workspace/output/11_satisfaction_master/satisfaction_by_stress_deg_region.csv

2) 可视化用简化表：
   /workspace/output/08_viz_data/viz_satisfaction_by_stress_deg_region.csv

字段说明（可视化表）：
- aspect_code        : v074_num ~ v087_num
- q_no               : Q27.a ~ Q27.n
- aspect_short       : 一个简短的维度名（从 question_text 中截取）
- aspect_text        : 完整题干
- degree_label       : Doctorate / Master's / Dual degree
- region_continent   : 大洲（Africa, Asia, Europe, ...）
- high_stress_group  : 0 = 非高压组, 1 = 高压组
- high_stress_label  : 'Non-high-stress' / 'High-stress'
- n                  : 样本量（该组合非缺失 score 数）
- mean_score         : 平均满意度（1-7）
"""

from pathlib import Path
import pandas as pd

BASE = Path("/workspace")

PATH_MASTER = BASE / "output" / "99_master" / "master_person_wide.csv"
PATH_SAT = BASE / "output" / "99_master" / "satisfaction_long.csv"

OUT_ANALYSIS_DIR = BASE / "output" / "11_satisfaction_master"
OUT_VIZ_DIR = BASE / "output" / "08_viz_data"

OUT_ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
OUT_VIZ_DIR.mkdir(parents=True, exist_ok=True)


def make_aspect_short(text: str) -> str:
    """
    从长题干中提炼一个短标签。
    规则与 94_export_viz_satisfaction_from_master.py 保持一致：
    - 去掉前面的通用引导句，只保留后面的短语，如 'Work-life balance'
    """
    if not isinstance(text, str):
        return ""

    t = text.strip()
    # 按 '?' 或 ':' 分割，再取最后一段
    for sep in ["?", ":", "â€”", "—"]:
        if sep in t:
            t = t.split(sep)[-1].strip()

    # 去掉尾部的 [numeric]
    if "[numeric]" in t:
        t = t.replace("[numeric]", "").strip()

    # 按 '.' 再分割
    if "." in t:
        t = t.split(".")[-1].strip()

    # 按两个空格分割（防御性）
    if "  " in t:
        t = t.split("  ")[-1].strip()

    return t


def main():
    print("读取 master_person_wide ...")
    master = pd.read_csv(PATH_MASTER)
    print("master_person_wide 形状:", master.shape)

    print("读取 satisfaction_long ...")
    sat_long = pd.read_csv(PATH_SAT)
    print("satisfaction_long 形状:", sat_long.shape)

    # 检查 master 必需列
    for col in ["resp_id", "degree_label", "region_continent", "high_stress_group"]:
        if col not in master.columns:
            raise KeyError(f"master_person_wide 缺少必需列：{col}")

    # 检查 satisfaction_long 必需列
    required_sat_cols = ["resp_id", "aspect_code", "q_no", "aspect_text", "score"]
    missing_sat = [c for c in required_sat_cols if c not in sat_long.columns]
    if missing_sat:
        raise KeyError("satisfaction_long 缺少列：" + ", ".join(missing_sat))

    # 只保留我们关心的 master 列
    master_sub = master[["resp_id", "degree_label", "region_continent", "high_stress_group"]].copy()

    # 合并：人级别信息 + 满意度长表
    df = sat_long.merge(master_sub, on="resp_id", how="left")

    # 去掉 score 缺失的记录
    before = len(df)
    df = df[df["score"].notna()].copy()
    after = len(df)
    print(f"去除满意度缺失后：{before} -> {after} 行")

    # 规范高压组标签
    df["high_stress_group"] = pd.to_numeric(df["high_stress_group"], errors="coerce").astype("Int64")
    df["high_stress_label"] = df["high_stress_group"].map(
        {0: "Non-high-stress", 1: "High-stress"}
    )

    # aspect 简短标签
    df["aspect_short"] = df["aspect_text"].apply(make_aspect_short)

    # 防御性处理 degree_label / region_continent 中的缺失
    df["degree_label"] = df["degree_label"].fillna("Unknown degree")
    df["region_continent"] = df["region_continent"].fillna("Unknown region")

    # === 1. 按 (aspect × 高压组 × 学位 × 地区) 汇总 ===
    group_cols = [
        "aspect_code",
        "q_no",
        "aspect_text",
        "aspect_short",
        "degree_label",
        "region_continent",
        "high_stress_group",
        "high_stress_label",
    ]

    grp = df.groupby(group_cols)

    agg = grp["score"].agg(["count", "mean"]).reset_index()
    agg = agg.rename(columns={"count": "n", "mean": "mean_score"})

    # 为排序准备一个 aspect 顺序：按 q_no 排
    order_map = (
        agg[["aspect_code", "q_no"]]
        .drop_duplicates()
        .sort_values("q_no")
        .reset_index(drop=True)
    )
    order_map["aspect_order"] = range(len(order_map))
    agg = agg.merge(order_map[["aspect_code", "aspect_order"]], on="aspect_code", how="left")

    # 排序：先按 aspect_order，再按 degree、region、high_stress_group
    agg = agg.sort_values(
        ["aspect_order", "degree_label", "region_continent", "high_stress_group"]
    )

    print("\n=== satisfaction_by_stress_deg_region 预览（前 14 行）===")
    print(
        agg[[
            "aspect_code",
            "q_no",
            "aspect_short",
            "degree_label",
            "region_continent",
            "high_stress_group",
            "high_stress_label",
            "n",
            "mean_score",
        ]].head(14).to_string(index=False)
    )

    # === 2. 输出 ===
    out_analysis = OUT_ANALYSIS_DIR / "satisfaction_by_stress_deg_region.csv"
    out_viz = OUT_VIZ_DIR / "viz_satisfaction_by_stress_deg_region.csv"

    agg.to_csv(out_analysis, index=False)
    agg.to_csv(out_viz, index=False)

    print(f"\n已保存分析用满意度 × 高压 × 学位 × 地区汇总表到: {out_analysis}")
    print(f"已保存可视化用满意度 × 高压 × 学位 × 地区汇总表到: {out_viz}")


if __name__ == "__main__":
    main()
