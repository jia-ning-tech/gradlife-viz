import pandas as pd
from pathlib import Path

INPUT_PATH = Path("/workspace/output/04_worklife/high_stress_by_degree_labeled.csv")

def main():
    df = pd.read_csv(INPUT_PATH)

    print("=== 原始按学位×高压分布 ===")
    print(df)

    # 只保留 high_stress_group == 1 的行（高压组）
    high = df[df["high_stress_group"] == 1].copy()

    print("\n=== 各学位高压组比例（percent 列） ===")
    for _, row in high.iterrows():
        degree = row["degree_label"]
        pct = row["percent"]
        count = row["count"]
        print(f"{degree}: 高工时+低工作生活平衡 = {pct:.1f}%  （人数: {count}）")

if __name__ == "__main__":
    main()
