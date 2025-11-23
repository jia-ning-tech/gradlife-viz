import pandas as pd
from pathlib import Path

META_PATH = Path("/workspace/output/02_typed_clean/metadata_step2_typed_clean.csv")

# 你可以在这里添加 / 修改自己想搜索的关键词
SEARCH_TERMS = [
    "hours per week",
    "work-life balance",
    "work life balance",
    "satisfaction",
    "mental health",
    "bullying",
    "discrimination",
    "debt",
    "finances",
    "career",
]

def main():
    meta = pd.read_csv(META_PATH)
    meta["question_text_str"] = meta["question_text"].astype(str).str.lower()

    for term in SEARCH_TERMS:
        term_lower = term.lower()
        print("=" * 80)
        print(f"★ 关键词: {term}")
        mask = meta["question_text_str"].str.contains(term_lower, na=False)
        sub = meta.loc[mask, ["col_name", "q_no", "q_type", "multi_group", "question_text"]]
        if sub.empty:
            print("  没有匹配到变量。")
        else:
            print(sub.to_string(index=False))
    print("=" * 80)
    print("搜索结束。")

if __name__ == "__main__":
    main()
