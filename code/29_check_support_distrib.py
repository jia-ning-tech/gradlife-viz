import pandas as pd
from pathlib import Path

DATA_PATH = Path("/workspace/output/02_typed_clean/data_step2_typed_clean.csv")
WORKLIFE_PATH = Path("/workspace/output/04_worklife/worklife_derived_vars.csv")

# 想看的导师 / 学校支持变量（数值版）
SUPPORT_VARS = {
    "v079_num": "Q27.f – Overall relationship with supervisor",
    "v091_num": "Q32.a – Supervisor makes time for frank conversations about my career",
    "v097_num": "Q35.a – Mental health & wellbeing services tailored to graduate students",
    "v100_num": "Q35.d – Other types of mental health/wellbeing support beyond 1:1",
    "v101_num": "Q35.e – University supports good work–life balance",
}

def main():
    df = pd.read_csv(DATA_PATH)
    wl = pd.read_csv(WORKLIFE_PATH)

    # 简单对齐一下 high_stress_group，后面分析会用到，这里先合并方便顺便看分布
    if len(df) != len(wl):
        print("警告：主数据和 worklife_derived_vars 行数不一致！")
        print("data_step2_typed_clean 行数:", len(df))
        print("worklife_derived_vars 行数:", len(wl))
        return

    df["high_stress_group"] = wl["high_stress_group"]

    print("合并 high_stress_group 成功。")

    print("\n=== 样本量 & high_stress_group 分布（整体）===")
    print("样本量:", len(df))
    print(df["high_stress_group"].value_counts(dropna=False))

    # 逐个变量检查
    for col, label in SUPPORT_VARS.items():
        print("\n" + "=" * 80)
        print(f"变量: {col}")
        print(f"题目: {label}")

        if col not in df.columns:
            print(f"⚠️ 列 {col} 不在数据中，请检查 metadata 或清洗脚本。")
            continue

        # 前几行看看
        print("\n【前 10 行示例】")
        print(df[[col, "high_stress_group"]].head(10))

        # 数值分布（1–7）
        print("\n【数值分布（含缺失）】")
        vc = df[col].value_counts(dropna=False).sort_index()
        print(vc)

        # 简单描述统计
        print("\n【描述统计】")
        print(df[col].describe())

        # 看看在高压组 vs 非高压组内的均值（先不做正式分析，只是感受一下）
        grouped_mean = df.groupby("high_stress_group")[col].mean()
        print("\n【按 high_stress_group 的均值】 (0=非高压, 1=高压)")
        print(grouped_mean)

    print("\n检查完成。")

if __name__ == "__main__":
    main()
