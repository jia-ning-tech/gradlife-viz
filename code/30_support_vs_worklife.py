import pandas as pd
from pathlib import Path

DATA_PATH = Path("/workspace/output/02_typed_clean/data_step2_typed_clean.csv")
WORKLIFE_PATH = Path("/workspace/output/04_worklife/worklife_derived_vars.csv")

OUT_DIR = Path("/workspace/output/07_support")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 想分析的支持/关系变量（Likert numeric）
SUPPORT_VARS = {
    "v079_num": "Q27.f – Overall relationship with supervisor",
    "v091_num": "Q32.a – Supervisor makes time for frank conversations about my career",
    "v097_num": "Q35.a – Mental health & wellbeing services tailored to graduate students",
    "v100_num": "Q35.d – Other types of mental health/wellbeing support beyond 1:1",
    "v101_num": "Q35.e – University supports good work–life balance",
}

def clean_likert_1_to_7(x):
    """只保留 1–7 的值，其他(包括8、0等)视为缺失。"""
    if pd.isna(x):
        return pd.NA
    try:
        v = float(x)
    except Exception:
        return pd.NA
    if 1 <= v <= 7:
        return v
    return pd.NA

def cat_support(score):
    """把 1–7 的支持感/满意度分成三档."""
    if pd.isna(score):
        return pd.NA
    try:
        s = float(score)
    except Exception:
        return pd.NA

    if s <= 3:
        return "Low support (1–3)"
    elif s == 4:
        return "Neutral (4)"
    else:  # 5–7
        return "High support (5–7)"

def make_table(df, var_col, cat_col, question_label, out_prefix):
    """
    按支持档次 × high_stress_group 做交叉表，并导出 CSV。

    返回一个标准化的长表：
    question, factor, level, high_stress_group, count, percent
    """
    sub = df[[cat_col, "high_stress_group"]].dropna()
    ct = (
        sub.groupby([cat_col, "high_stress_group"])
        .size()
        .reset_index(name="count")
    )
    # 每个档次内部的百分比
    total_by_cat = ct.groupby(cat_col)["count"].transform("sum")
    ct["percent"] = ct["count"] / total_by_cat * 100

    # 统一列名，方便之后合并
    ct = ct.rename(
        columns={
            cat_col: "level",
            "high_stress_group": "high_stress_group",
            "count": "count",
            "percent": "percent",
        }
    )
    ct["question"] = question_label
    ct["factor"] = var_col  # 用变量名做一个因子标记

    # 调整列顺序
    ct = ct[
        ["question", "factor", "level", "high_stress_group", "count", "percent"]
    ]

    out_path = OUT_DIR / f"{out_prefix}_vs_high_stress.csv"
    ct.to_csv(out_path, index=False)
    print(f"已导出 {question_label} × 高压组 结果到: {out_path}")
    print(ct)
    print("-" * 80)
    return ct

def main():
    df = pd.read_csv(DATA_PATH)
    wl = pd.read_csv(WORKLIFE_PATH)

    if len(df) != len(wl):
        print("⚠️ 警告：主数据和 worklife_derived_vars 行数不一致！")
        print("data_step2_typed_clean 行数:", len(df))
        print("worklife_derived_vars 行数:", len(wl))
        return

    df["high_stress_group"] = wl["high_stress_group"]
    print("合并 high_stress_group 成功。")

    all_tables = []

    for col, q_label in SUPPORT_VARS.items():
        print("=" * 80)
        print(f"处理变量: {col}")
        print(f"题目: {q_label}")

        if col not in df.columns:
            print(f"⚠️ 列 {col} 不在数据中，跳过。")
            continue

        # 清洗为 1–7
        clean_col = col + "_clean"
        df[clean_col] = df[col].apply(clean_likert_1_to_7)

        print("\n【清洗后数值分布（1–7，含缺失）】")
        print(df[clean_col].value_counts(dropna=False).sort_index())

        # 分档：低 / 中立 / 高 支持
        cat_col = col + "_cat"
        df[cat_col] = df[clean_col].apply(cat_support)

        print("\n【分档后的分布】")
        print(df[cat_col].value_counts(dropna=False))

        # 做交叉表
        prefix = col
        ct = make_table(
            df,
            var_col=col,
            cat_col=cat_col,
            question_label=q_label,
            out_prefix=prefix,
        )
        all_tables.append(ct)

    # 合并所有支持变量的长表
    if all_tables:
        viz = pd.concat(all_tables, ignore_index=True)
        viz_out = OUT_DIR / "viz_support_high_stress.csv"
        viz.to_csv(viz_out, index=False)
        print("所有支持/关系变量的可视化长表已保存到:", viz_out)
    else:
        print("⚠️ 没有生成任何表，请检查 SUPPORT_VARS 的配置。")

if __name__ == "__main__":
    main()
