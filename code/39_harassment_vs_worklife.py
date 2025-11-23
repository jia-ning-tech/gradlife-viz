# /workspace/code/39_harassment_vs_worklife.py
"""
目的：
  生成「是否经历 discrimination / harassment × high_stress_group」的交叉表，
  输出到 /workspace/output/07_harassment/harassment_vs_high_stress.csv

说明：
  - 使用列 v112_code（Q39: Do you feel that you have experienced discrimination or harassment...）
  - 使用前面已经构造好的 high_stress_group（来自 04_worklife/worklife_derived_vars.csv）
"""

import pandas as pd
import json
from pathlib import Path

# 路径设置
DATA_PATH = Path("/workspace/output/02_typed_clean/data_step2_typed_clean.csv")
META_PATH = Path("/workspace/output/02_typed_clean/metadata_step2_typed_clean.csv")
WORKLIFE_PATH = Path("/workspace/output/04_worklife/worklife_derived_vars.csv")

OUTPUT_DIR = Path("/workspace/output/07_harassment")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HARASS_COL = "v112_code"   # 是否经历 discrimination / harassment 的 coded 列名


def parse_value_labels(val):
    """把 metadata 里的 value_labels 字段解析成 dict."""
    if pd.isna(val):
        return {}
    if isinstance(val, dict):
        return val
    try:
        return json.loads(val)
    except Exception:
        return {}


def main():
    print("读取数据与 metadata ...")
    df = pd.read_csv(DATA_PATH)
    meta = pd.read_csv(META_PATH)
    worklife = pd.read_csv(WORKLIFE_PATH)

    print("原始数据形状:", df.shape)
    print("worklife_derived_vars 形状:", worklife.shape)

    # 把 high_stress_group 并回 df（按行号对齐）
    if "high_stress_group" not in worklife.columns:
        raise ValueError("worklife_derived_vars.csv 中没有 high_stress_group 列，请确认 05_worklife_analysis.py 是否正确运行。")

    if len(worklife) != len(df):
        raise ValueError("data_step2_typed_clean 与 worklife_derived_vars 行数不一致，无法按索引合并。")

    df["high_stress_group"] = worklife["high_stress_group"]
    print("已将 high_stress_group 合并入主数据。")

    # 检查 HARASS_COL 是否存在
    if HARASS_COL not in df.columns:
        raise ValueError(f"数据中没有列 {HARASS_COL}，请检查列名。")

    # 从 metadata 中取出 value_labels
    mrow = meta.loc[meta["col_name"] == HARASS_COL]
    if mrow.empty:
        raise ValueError(f"在 metadata 中没有找到列 {HARASS_COL}。")

    mrow = mrow.iloc[0]
    question_text = mrow.get("question_text", "")
    raw_labels = mrow.get("value_labels", None)
    labels_dict = parse_value_labels(raw_labels)

    print("\n=== 元数据检查 ===")
    print("题目:", question_text)
    print("原始 value_labels:", raw_labels)
    print("解析后的标签字典:")
    for k, v in labels_dict.items():
        print(f"  {k} -> {v}")

    # 先看一下 v112_code 的分布
    print("\n=== v112_code 频数分布（含缺失） ===")
    print(df[HARASS_COL].value_counts(dropna=False))

    # 映射成文本标签
    def map_harass_label(x):
        if pd.isna(x):
            return pd.NA
        # x 通常是 float，如 1.0、2.0
        key = str(int(x))
        return labels_dict.get(key, f"Code {key}")

    df["harassment_label"] = df[HARASS_COL].apply(map_harass_label)

    # 只在 high_stress_group 非缺失、且 harassment_label 非缺失 的样本上做交叉
    sub = df.dropna(subset=["high_stress_group", "harassment_label"]).copy()
    sub["high_stress_group"] = sub["high_stress_group"].astype(int)

    print("\n有效样本量（用于交叉分析）:", len(sub))

    # 交叉表：骚扰经历 × 高压组
    crosstab = (
        sub.groupby(["harassment_label", "high_stress_group"])
        .size()
        .reset_index(name="count")
    )

    # 每个 harassment_label 内部的百分比
    total_by_label = crosstab.groupby("harassment_label")["count"].transform("sum")
    crosstab["percent"] = crosstab["count"] / total_by_label * 100

    # 加上题目文本，方便后续查看
    crosstab.insert(0, "question", question_text)

    out_path = OUTPUT_DIR / "harassment_vs_high_stress.csv"
    crosstab.to_csv(out_path, index=False)

    print("\n=== 交叉表预览 ===")
    print(crosstab)

    print("\n已保存骚扰/歧视经历 × 高压组交叉表到:", out_path)


if __name__ == "__main__":
    main()
