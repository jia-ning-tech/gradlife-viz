import pandas as pd
from pathlib import Path

BASE = Path("/workspace")
INPUT_PATH = BASE / "output/04_worklife/high_stress_by_degree_labeled.csv"
OUTPUT_DIR = BASE / "output/08_viz_data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "viz_degree_high_stress.csv"

def main():
    df = pd.read_csv(INPUT_PATH)

    # 只保留高压组那一行（high_stress_group == 1）
    high = df[df["high_stress_group"] == 1].copy()

    # 计算每个学位的总人数（0+1）
    totals = (
        df.groupby("degree_label")["count"]
        .sum()
        .reset_index()
        .rename(columns={"count": "total_count"})
    )

    # 合并总人数
    high = high.merge(totals, on="degree_label", how="left")

    # 重命名列，变成 JS 友好的字段名
    out = high[["degree_label", "percent", "count", "total_count"]].copy()
    out = out.rename(columns={
        "percent": "high_stress_percent",
        "count": "high_stress_count",
    })

    out.to_csv(OUTPUT_PATH, index=False)
    print("已导出可视化用的学位×高压数据到：", OUTPUT_PATH)

if __name__ == "__main__":
    main()
