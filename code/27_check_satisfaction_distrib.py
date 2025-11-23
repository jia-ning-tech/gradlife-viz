import pandas as pd
from pathlib import Path

DATA_PATH = Path("/workspace/output/02_typed_clean/data_step2_typed_clean.csv")

def main():
    df = pd.read_csv(DATA_PATH)

    cols_to_show = ["v070", "v070_num", "v072", "v072_num"]
    exist_cols = [c for c in cols_to_show if c in df.columns]

    print("存在的相关列：", exist_cols)
    print("\n=== 前 10 行示例 ===")
    print(df[exist_cols].head(10))

    # Q23: decision to pursue a graduate degree
    if "v070" in df.columns:
        print("\n=== v070 原始文本分布 ===")
        print(df["v070"].value_counts(dropna=False))

    if "v070_num" in df.columns:
        print("\n=== v070_num 数值分布 ===")
        print(df["v070_num"].value_counts(dropna=False).sort_index())

    # Q25: overall graduate degree experience
    if "v072" in df.columns:
        print("\n=== v072 原始文本分布 ===")
        print(df["v072"].value_counts(dropna=False))

    if "v072_num" in df.columns:
        print("\n=== v072_num 数值分布 ===")
        print(df["v072_num"].value_counts(dropna=False).sort_index())

    print("\n检查完成。")

if __name__ == "__main__":
    main()
