import pandas as pd
from pathlib import Path

META_PATH = Path("/workspace/output/02_typed_clean/metadata_step2_typed_clean.csv")

# 你可以在这里填你关心的题号
QNOS = ["Q21", "Q2", "Q19", "Q17"]  # 例子：Q21=工作时长, Q2=学位类型, Q19/Q17=满意度相关

def main():
    meta = pd.read_csv(META_PATH)
    for q in QNOS:
        print("=" * 80)
        print("题号:", q)
        sub = meta.loc[meta["q_no"] == q, ["col_name", "q_no", "q_type", "multi_group", "question_text"]]
        if sub.empty:
            print("  没有匹配到。")
        else:
            print(sub.to_string(index=False))

if __name__ == "__main__":
    main()
