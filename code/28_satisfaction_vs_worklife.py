import pandas as pd
from pathlib import Path

DATA_PATH = Path("/workspace/output/02_typed_clean/data_step2_typed_clean.csv")
WORKLIFE_PATH = Path("/workspace/output/04_worklife/worklife_derived_vars.csv")
OUT_DIR = Path("/workspace/output/06_satisfaction")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Q23.a: How satisfied are you with your decision to pursue a graduate degree?
TEXT_TO_SCORE_Q23 = {
    "1 = Not at all satisfied": 1,
    "2": 2,
    "3": 3,
    "4 = Neither satisfied nor dissatisfied": 4,
    "5": 5,
    "6": 6,
    "7 = Extremely satisfied": 7,
}

# Q25.a: How satisfied are you with your graduate degree experience?
TEXT_TO_SCORE_Q25 = {
    "1 = Not at all satisfied": 1,
    "2": 2,
    "3": 3,
    "4 = Neither satisfied nor dissatisfied": 4,
    "5": 5,
    "6": 6,
    "7 = Extremely satisfied": 7,
}

def cat_satisfaction(score):
    """把 1–7 的满意度分成三档."""
    if pd.isna(score):
        return pd.NA
    try:
        s = float(score)
    except Exception:
        return pd.NA

    if s <= 3:
        return "Low satisfaction (1–3)"
    elif s == 4:
        return "Neutral (4)"
    else:  # 5–7
        return "High satisfaction (5–7)"


def make_table(df, score_col, cat_col, question_label, out_name_prefix):
    """按满意度档次 × high_stress_group 做交叉表，并导出 CSV."""
    sub = df[[cat_col, "high_stress_group"]].dropna()
    ct = (
        sub.groupby([cat_col, "high_stress_group"])
        .size()
        .reset_index(name="count")
    )
    # 每个满意度档次内部的百分比
    total_by_cat = ct.groupby(cat_col)["count"].transform("sum")
    ct["percent"] = ct["count"] / total_by_cat * 100

    ct = ct.rename(columns={cat_col: "satisfaction_level"})
    ct["question"] = question_label
    ct = ct[
        ["question", "satisfaction_level", "high_stress_group", "count", "percent"]
    ]

    out_path = OUT_DIR / f"{out_name_prefix}_vs_high_stress.csv"
    ct.to_csv(out_path, index=False)
    print(f"已导出 {question_label} × 高压组 结果到: {out_path}")
    print(ct)
    print("-" * 80)
    return ct


def main():
    # 读主数据 + 已计算好的 high_stress_group
    df = pd.read_csv(DATA_PATH)
    wl = pd.read_csv(WORKLIFE_PATH)

    if len(df) != len(wl):
        print("警告：主数据和 worklife_derived_vars 行数不一致！")
        print("data_step2_typed_clean 行数:", len(df))
        print("worklife_derived_vars 行数:", len(wl))
        return

    # 按行对齐，把 high_stress_group 合并进来
    df["high_stress_group"] = wl["high_stress_group"]
    print("合并 high_stress_group 成功。")

    # 检查相关列是否存在
    for col in ["v070", "v072"]:
        if col not in df.columns:
            print(f"警告：列 {col} 不在数据中，请检查。")

    # 映射原始文本为 1–7 分值
    df["sat_decision"] = df["v070"].map(TEXT_TO_SCORE_Q23)
    df["sat_experience"] = df["v072"].map(TEXT_TO_SCORE_Q25)

    print("\n=== Q23 决策满意度 sat_decision 数值分布 ===")
    print(df["sat_decision"].value_counts(dropna=False).sort_index())

    print("\n=== Q25 经历满意度 sat_experience 数值分布 ===")
    print(df["sat_experience"].value_counts(dropna=False).sort_index())

    # 分档：低 / 中立 / 高
    df["sat_decision_cat"] = df["sat_decision"].apply(cat_satisfaction)
    df["sat_experience_cat"] = df["sat_experience"].apply(cat_satisfaction)

    print("\n=== sat_decision_cat 分布 ===")
    print(df["sat_decision_cat"].value_counts(dropna=False))

    print("\n=== sat_experience_cat 分布 ===")
    print(df["sat_experience_cat"].value_counts(dropna=False))

    # 做交叉表并导出
    t1 = make_table(
        df,
        score_col="sat_decision",
        cat_col="sat_decision_cat",
        question_label="Decision to pursue graduate degree (Q23.a)",
        out_name_prefix="q23_decision_satisfaction",
    )

    t2 = make_table(
        df,
        score_col="sat_experience",
        cat_col="sat_experience_cat",
        question_label="Overall graduate degree experience (Q25.a)",
        out_name_prefix="q25_experience_satisfaction",
    )

    # 合并成一个长表，供 JS 可视化使用
    viz = pd.concat([t1, t2], ignore_index=True)
    viz_out = OUT_DIR / "viz_satisfaction_high_stress.csv"
    viz.to_csv(viz_out, index=False)
    print("可视化用长表已保存到:", viz_out)


if __name__ == "__main__":
    main()
