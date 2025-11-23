import pandas as pd
from pathlib import Path

INPUT_PATH = Path("/workspace/output/06_mental_health/mental_help_vs_high_stress.csv")

def main():
    df = pd.read_csv(INPUT_PATH)

    print("=== 原始交叉表 ===")
    print(df)

    print("\n=== 各类心理健康求助状态下的高压比例（high_stress_group=1） ===")
    high = df[df["high_stress_group"] == 1].copy()

    for _, row in high.iterrows():
        label = row["help_label"]
        pct = row["percent"]
        count = row["count"]
        print(f"{label}: 高工时+低工作生活平衡 = {pct:.1f}% （人数: {count}）")

if __name__ == "__main__":
    main()
