import pandas as pd
from pathlib import Path

META_PATH = Path("/workspace/output/02_typed_clean/metadata_step2_typed_clean.csv")

SEARCH_CONFIG = [
    # 关键词, 备注
    ("hour", "可能是每周工作时长 (hours per week) 相关题"),
    ("work-life balance", "工作-生活平衡"),
    ("work life balance", "工作-生活平衡（无连字符写法）"),
    ("overall satisfaction", "总体满意度"),
    ("satisfied", "满意度相关"),
]

def main():
    meta = pd.read_csv(META_PATH)
    meta["question_text_str"] = meta["question_text"].astype(str).str.lower()

    for keyword, desc in SEARCH_CONFIG:
        print("=" * 80)
        print(f"★ 关键词: '{keyword}' ({desc})")
        mask = meta["question_text_str"].str.contains(keyword.lower(), na=False)
        sub = meta.loc[mask, ["col_name", "q_no", "q_type", "multi_group", "question_text"]]
        if sub.empty:
            print("  没有匹配到。")
        else:
            print(sub.to_string(index=False))

    print("=" * 80)
    print("搜索结束。")

if __name__ == "__main__":
    main()
