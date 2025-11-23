import pandas as pd
from pathlib import Path

META_PATH = Path("/workspace/output/02_typed_clean/metadata_step2_typed_clean.csv")

def search_meta(df, keyword, cols=("question_text", "col_name")):
    """在 metadata 中按关键词搜索，忽略大小写。"""
    key = keyword.lower()
    mask = False
    for c in cols:
        if c in df.columns:
            mask = mask | df[c].fillna("").str.lower().str.contains(key)
    hits = df.loc[mask, ["col_name", "q_no", "q_type", "multi_group", "question_text"]]
    print("=" * 80)
    print(f"★ 关键词: '{keyword}'")
    if hits.empty:
        print("  没有匹配到。")
    else:
        print(hits.to_string(index=False))
    print("=" * 80)


def main():
    meta = pd.read_csv(META_PATH)
    # 防御性：有些脚本里我们把 col_name 设为 index 过，这里先保证还在列里
    if "col_name" not in meta.columns:
        meta = meta.reset_index().rename(columns={"index": "col_name"})

    # 想看满意度 / 后悔 / 离开意向 / 推荐意愿 / 导师 & 支持等
    keywords = [
        "satisfied",
        "satisfaction",
        "regret",
        "regretted",
        "again",        # e.g. choose again / do it again
        "leave",        # intend to leave / leave program
        "quit",
        "drop out",
        "recommend",
        "recommend this",
        "supervisor",
        "adviser",
        "advisor",
        "support",
        "mental health services",
        "wellbeing",
        "bullying",     # 再确认一遍
        "harassment",
        "discrimination",
    ]

    for kw in keywords:
        search_meta(meta, kw)

    print("搜索结束。")

if __name__ == "__main__":
    main()
