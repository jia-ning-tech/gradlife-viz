import pandas as pd
from pathlib import Path

META_PATH = Path("/workspace/output/02_typed_clean/metadata_step2_typed_clean.csv")

SEARCH_TERMS = [
    "mental health",
    "stress",
    "stressed",
    "anxiety",
    "anxious",
    "depression",
    "depressed",
    "burnout",
    "wellbeing",
    "well-being",
    "bullying",
    "harassment",
]

def main():
    meta = pd.read_csv(META_PATH)
    meta["question_text_str"] = meta["question_text"].astype(str).str.lower()

    for term in SEARCH_TERMS:
        print("=" * 80)
        print(f"★ 关键词: '{term}'")
        mask = meta["question_text_str"].str.contains(term.lower(), na=False)
        sub = meta.loc[mask, ["col_name", "q_no", "q_type", "multi_group", "question_text"]]
        if sub.empty:
            print("  没有匹配到。")
        else:
            print(sub.to_string(index=False))

    print("=" * 80)
    print("搜索结束。")

if __name__ == "__main__":
    main()
