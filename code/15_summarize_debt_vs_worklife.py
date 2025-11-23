import pandas as pd
from pathlib import Path

INPUT_PATH = Path("/workspace/output/05_debt/debt_vs_high_stress.csv")

def main():
    df = pd.read_csv(INPUT_PATH)

    print("=== 原始交叉表 ===")
    print(df)

    print("\n=== 各类负债预期下的高压比例（high_stress_group=1） ===")
    high = df[df["high_stress_group"] == 1].copy()

    for _, row in high.iterrows():
        label = row["debt_label"]
        pct = row["percent"]
        count = row["count"]
        print(f"{label}: 高工时+低工作生活平衡 = {pct:.1f}% （人数: {count}）")

if __name__ == "__main__":
    main()
