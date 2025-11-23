import pandas as pd
from pathlib import Path

META_PATH = Path("/workspace/output/02_typed_clean/metadata_step2_typed_clean.csv")

# 想要搜索的关键词，可以根据需要再加
KEYWORDS = [
    "country",
    "region",
    "location",
    "continent",
    "where do you live",
    "where are you based",
    "geographic",
    "geographical",
    "world region",
]

def main():
    meta = pd.read_csv(META_PATH)

    # 为了防止空值报错，先把 question_text 转成字符串
    meta["question_text_str"] = meta["question_text"].astype(str)

    print("=== metadata 形状 ===")
    print(meta.shape)
    print("")

    for kw in KEYWORDS:
        print("=" * 80)
        print(f"★ 关键词: '{kw}'")
        mask = meta["question_text_str"].str.contains(kw, case=False, na=False)
        subset = meta.loc[mask, ["col_name", "q_no", "q_type", "multi_group", "question_text"]]

        if subset.empty:
            print("  没有匹配到。")
        else:
            # 防止输出太长，只看前 20 行，如果你想全看可以去掉 head(20)
            print(subset.head(20).to_string(index=False))
        print("=" * 80)
        print("")

if __name__ == "__main__":
    main()
