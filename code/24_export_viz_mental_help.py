import pandas as pd
from pathlib import Path

BASE = Path("/workspace")
INPUT_PATH = BASE / "output/06_mental_health/mental_help_vs_high_stress.csv"
OUTPUT_DIR = BASE / "output/08_viz_data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "viz_mental_help_high_stress.csv"

def main():
    df = pd.read_csv(INPUT_PATH)

    # 只保留高压组那一行（high_stress_group == 1）
    high = df[df["high_stress_group"] == 1].copy()

    # 计算每个 help_label 的总人数（0+1）
    totals = (
        df.groupby("help_label")["count"]
        .sum()
        .reset_index()
        .rename(columns={"count": "total_count"})
    )

    # 合并总人数
    high = high.merge(totals, on="help_label", how="left")

    # 重命名列，变成 JS 友好的字段名
    out = high[["help_label", "percent", "count", "total_count"]].copy()
    out = out.rename(columns={
        "percent": "high_stress_percent",
        "count": "high_stress_count",
    })

    out.to_csv(OUTPUT_PATH, index=False)
    print("已导出可视化用的 心理健康求助×高压 数据到：", OUTPUT_PATH)

if __name__ == "__main__":
    main()
