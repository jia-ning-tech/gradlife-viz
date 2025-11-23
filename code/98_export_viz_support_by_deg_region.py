#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
98_export_viz_support_by_deg_region.py

用途：
- 基于 master_person_wide + support_long，
  生成“支持相关条目 × 高压组 × 学位 × 地区（大洲）”的汇总表，
  供前端可视化使用（例如：按学位/地区对比支持感的高压/非高压差异）。

一行 = 一个 (支持条目 × 高压组 × 学位 × 地区) 组合。

支持条目来自：
- Q32.a–d: My supervisor ...
- Q35.a–f: Mental health & university support ...

输出：
1) 分析用汇总表：
   /workspace/output/12_support_master/support_by_stress_deg_region.csv

2) 可视化用简化表：
   /workspace/output/08_viz_data/viz_support_by_stress_deg_region.csv

字段说明（可视化表）：
- item_code         : v091_num ~ v094_num, v097_num ~ v102_num
- q_no              : Q32.a ~ Q35.f
- scale_group       : 'Q32'（supervisor）或 'Q35'（institution/mental health）
- item_short        : 简短标签（从 item_text 中抽取）
- item_text         : 完整题干
- degree_label      : Doctorate / Master's / Dual degree
- region_continent  : 大洲（Africa, Asia, Europe, ...）
- high_stress_group : 0 = 非高压组, 1 = 高压组
- high_stress_label : 'Non-high-stress' / 'High-stress'
- n                 : 样本量（该组合非缺失 score 数）
- mean_score        : 平均得分（Likert）
- item_order        : 条目顺序（按 scale_group + q_no 排）
"""

from pathlib import Path
import pandas as pd

BASE = Path("/workspace")

PATH_MASTER = BASE / "output" / "99_master" / "master_person_wide.csv"
PATH_SUPPORT = BASE / "output" / "99_master" / "support_long.csv"

OUT_ANALYSIS_DIR = BASE / "output" / "12_support_master"
OUT_VIZ_DIR = BASE / "output" / "08_viz_data"

OUT_ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
OUT_VIZ_DIR.mkdir(parents=True, exist_ok=True)


def make_item_short(text: str) -> str:
    """
    从长题干中提炼一个短标签。

    Q32 示例：
      "My supervisor â¦ Makes time for frank conversations about my career    [numeric]"
    Q35 示例：
      "My university supports good work-life balance [numeric]"

    规则：
    - 去掉末尾的 "[numeric]"
    - 若包含 "My supervisor ..."，尝试保留后半句（"…"/"..." /"â¦" 后面的部分）
    """
    if not isinstance(text, str):
        return ""

    t = text.strip()

    # 去掉 [numeric]
    if "[numeric]" in t:
        t = t.replace("[numeric]", "").strip()

    # 针对 "My supervisor ..." 的情况，按 "…"/"..." / "â¦" 切一次
    for sep in ["…", "...", "â¦"]:
        if sep in t:
            parts = t.split(sep, 1)
            if len(parts) == 2:
                t = parts[1].strip()
                break

    return t


def main():
    print("读取 master_person_wide ...")
    master = pd.read_csv(PATH_MASTER)
    print("master_person_wide 形状:", master.shape)

    print("读取 support_long ...")
    sup_long = pd.read_csv(PATH_SUPPORT)
    print("support_long 形状:", sup_long.shape)

    # 检查 master 必需列
    for col in ["resp_id", "degree_label", "region_continent", "high_stress_group"]:
        if col not in master.columns:
            raise KeyError(f"master_person_wide 缺少必需列：{col}")

    # 检查 support_long 必需列
    required_sup_cols = ["resp_id", "item_code", "q_no", "scale_group", "item_text", "score"]
    missing_sup = [c for c in required_sup_cols if c not in sup_long.columns]
    if missing_sup:
        raise KeyError("support_long 缺少列：" + ", ".join(missing_sup))

    # 只保留我们关心的 master 列
    master_sub = master[["resp_id", "degree_label", "region_continent", "high_stress_group"]].copy()

    # 合并：人级别信息 + 支持长表
    df = sup_long.merge(master_sub, on="resp_id", how="left")

    # 去掉 score 缺失的记录
    before = len(df)
    df = df[df["score"].notna()].copy()
    after = len(df)
    print(f"去除支持得分缺失后：{before} -> {after} 行")

    # 规范高压组标签
    df["high_stress_group"] = pd.to_numeric(df["high_stress_group"], errors="coerce").astype("Int64")
    df["high_stress_label"] = df["high_stress_group"].map(
        {0: "Non-high-stress", 1: "High-stress"}
    )

    # 简短标签
    df["item_short"] = df["item_text"].apply(make_item_short)

    # 防御性处理 degree_label / region_continent 中的缺失
    df["degree_label"] = df["degree_label"].fillna("Unknown degree")
    df["region_continent"] = df["region_continent"].fillna("Unknown region")

    # === 1. 按 (item × 高压组 × 学位 × 地区) 汇总 ===
    group_cols = [
        "item_code",
        "q_no",
        "scale_group",
        "item_text",
        "item_short",
        "degree_label",
        "region_continent",
        "high_stress_group",
        "high_stress_label",
    ]

    grp = df.groupby(group_cols)

    agg = grp["score"].agg(["count", "mean"]).reset_index()
    agg = agg.rename(columns={"count": "n", "mean": "mean_score"})

    # 为排序准备一个 item 顺序：按 scale_group + q_no 排
    order_map = (
        agg[["item_code", "scale_group", "q_no"]]
        .drop_duplicates()
        .sort_values(["scale_group", "q_no"])
        .reset_index(drop=True)
    )
    order_map["item_order"] = range(len(order_map))
    agg = agg.merge(order_map[["item_code", "item_order"]], on="item_code", how="left")

    # 排序：先按 scale_group，再按 item_order，再按 degree / region / high_stress_group
    agg = agg.sort_values(
        ["scale_group", "item_order", "degree_label", "region_continent", "high_stress_group"]
    )

    print("\n=== support_by_stress_deg_region 预览（前 16 行）===")
    print(
        agg[[
            "item_code",
            "q_no",
            "scale_group",
            "item_short",
            "degree_label",
            "region_continent",
            "high_stress_group",
            "high_stress_label",
            "n",
            "mean_score",
        ]].head(16).to_string(index=False)
    )

    # === 2. 输出 ===
    out_analysis = OUT_ANALYSIS_DIR / "support_by_stress_deg_region.csv"
    out_viz = OUT_VIZ_DIR / "viz_support_by_stress_deg_region.csv"

    agg.to_csv(out_analysis, index=False)
    agg.to_csv(out_viz, index=False)

    print(f"\n已保存分析用支持 × 高压 × 学位 × 地区汇总表到: {out_analysis}")
    print(f"已保存可视化用支持 × 高压 × 学位 × 地区汇总表到: {out_viz}")


if __name__ == "__main__":
    main()
