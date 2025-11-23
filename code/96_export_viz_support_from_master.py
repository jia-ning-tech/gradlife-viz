#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
96_export_viz_support_from_master.py

用途：
- 基于 master_person_wide + support_long，
  生成“支持相关条目 × 高压组”的汇总表，供后续前端可视化使用。

一行 = 一个 (支持条目 × 高压组) 组合。

支持条目来自：
- Q32.a–d: My supervisor ...
- Q35.a–f: Mental health & university support ...

输出：
1) 分析用汇总表：
   /workspace/output/12_support_master/support_by_stress.csv

2) 可视化用简化表：
   /workspace/output/08_viz_data/viz_support_by_stress.csv

字段说明（可视化表）：
- item_code         : v091_num ~ v094_num, v097_num ~ v102_num
- q_no              : Q32.a ~ Q35.f
- scale_group       : 'Q32'（supervisor）或 'Q35'（institution/mental health）
- item_short        : 简短标签（从 item_text 中抽取）
- item_text         : 完整题干
- high_stress_group : 0 = 非高压组, 1 = 高压组
- high_stress_label : 'Non-high-stress' / 'High-stress'
- n                 : 样本量（该组非缺失 score 数）
- mean_score        : 平均得分（Likert，一般 1–5）
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
      "My supervisor … Makes time for frank conversations about my career    [numeric]"
    Q35 示例：
      "My university supports good work-life balance [numeric]"

    规则：
    - 对 Q32：截掉前面的 "My supervisor …"，保留后半句。
    - 去掉末尾的 "[numeric]"。
    - 简单清理多余空格。
    """
    if not isinstance(text, str):
        return ""

    t = text.strip()

    # 去掉 [numeric]
    if "[numeric]" in t:
        t = t.replace("[numeric]", "").strip()

    # 针对 "My supervisor … ..." 的情况，按 "…" 或 "..." 切一次
    # 有时编码问题会变成 "â¦"，也处理一下
    for sep in ["…", "...", "â¦"]:
        if sep in t:
            parts = t.split(sep, 1)
            if len(parts) == 2:
                t = parts[1].strip()
                break

    # 再处理一下以 "My university" 打头的句子，直接保留整体即可
    # 这里只是防御性逻辑，不再额外截断
    return t


def main():
    print("读取 master_person_wide ...")
    master = pd.read_csv(PATH_MASTER)
    print("master_person_wide 形状:", master.shape)

    print("读取 support_long ...")
    sup_long = pd.read_csv(PATH_SUPPORT)
    print("support_long 形状:", sup_long.shape)

    # 检查 master 必需列
    for col in ["resp_id", "high_stress_group"]:
        if col not in master.columns:
            raise KeyError(f"master_person_wide 缺少必需列：{col}")

    # 检查 support_long 必需列
    required_sup_cols = ["resp_id", "item_code", "q_no", "scale_group", "item_text", "score"]
    missing_sup = [c for c in required_sup_cols if c not in sup_long.columns]
    if missing_sup:
        raise KeyError("support_long 缺少列：" + ", ".join(missing_sup))

    # 只保留我们关心的 master 列
    master_sub = master[["resp_id", "high_stress_group"]].copy()

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

    # === 1. 按 (item × 高压组) 汇总：总体 ===
    group_cols = [
        "item_code",
        "q_no",
        "scale_group",
        "item_text",
        "item_short",
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

    # 排序：先按 scale_group，再按 item_order，再按 high_stress_group
    agg = agg.sort_values(["scale_group", "item_order", "high_stress_group"])

    print("\n=== support_by_stress 总体预览（前 14 行）===")
    print(
        agg[[
            "item_code",
            "q_no",
            "scale_group",
            "item_short",
            "high_stress_group",
            "high_stress_label",
            "n",
            "mean_score",
        ]].head(14).to_string(index=False)
    )

    # === 2. 输出 ===
    out_analysis = OUT_ANALYSIS_DIR / "support_by_stress.csv"
    out_viz = OUT_VIZ_DIR / "viz_support_by_stress.csv"

    agg.to_csv(out_analysis, index=False)
    agg.to_csv(out_viz, index=False)

    print(f"\n已保存分析用支持 × 高压汇总表到: {out_analysis}")
    print(f"已保存可视化用支持 × 高压汇总表到: {out_viz}")


if __name__ == "__main__":
    main()
