import pandas as pd
from pathlib import Path

DATA_PATH = Path("/workspace/output/02_typed_clean/data_step2_typed_clean.csv")
WORKLIFE_DERIVED = Path("/workspace/output/04_worklife/worklife_derived_vars.csv")  # 里面有 high_stress_group
META_PATH = Path("/workspace/output/02_typed_clean/metadata_step2_typed_clean.csv")

# 先根据 metadata 找到我们关心的地区/国家变量
REGION_COLS = [
    "v016",       # Are you studying in the country you grew up in?
    "v031",       # Which country/region in Asia?
    "v032",       # Which country in Australasia?
    "v033",       # Which country in Africa?
    "v034",       # Which country in Europe?
    "v035",       # Which country in North or Central America?
    "v036",       # Which country in South America?
    "v031_code",  # Asia country/region coded
    # 其他 *_code 列如果存在也可以在下一步补充
]

def main():
    # 读数据
    df = pd.read_csv(DATA_PATH)
    meta = pd.read_csv(META_PATH)
    # 合并 high_stress_group
    df_worklife = pd.read_csv(WORKLIFE_DERIVED)
    if "high_stress_group" not in df_worklife.columns:
        print("⚠️ worklife_derived_vars.csv 里没有 high_stress_group，先确认第 05 步脚本是否跑通。")
        return

    # 按行号拼接（两边都是原始 3253 行顺序）
    df["high_stress_group"] = df_worklife["high_stress_group"]

    print("=== 数据形状 ===")
    print(df.shape)
    print()

    # 为了防止 metadata 里 question_text 为空，先转成 str
    meta["question_text_str"] = meta["question_text"].astype(str)

    # 只保留那些真实存在于数据里的 REGION_COLS
    existing_cols = [c for c in REGION_COLS if c in df.columns]
    missing_cols = [c for c in REGION_COLS if c not in df.columns]

    print("=== 计划检查的地区/国家变量 ===")
    print("存在的列:", existing_cols)
    print("缺失的列:", missing_cols)
    print()

    for col in existing_cols:
        print("=" * 80)
        # 在 metadata 里查一下题目
        msub = meta.loc[meta["col_name"] == col]
        if not msub.empty:
            q_no = msub["q_no"].iloc[0]
            q_text = msub["question_text_str"].iloc[0]
            q_type = msub["q_type"].iloc[0]
            print(f"变量: {col}  (q_no={q_no}, q_type={q_type})")
            print("题目:", q_text)
        else:
            print(f"变量: {col}  (在 metadata 中未找到详细信息)")

        # 看前几行
        print("\n【前 10 行示例】")
        print(df[col].head(10).to_string(index=False))

        # 看频数分布
        print("\n【非缺失频数分布（前 20 项）】")
        vc = df[col].value_counts(dropna=True)
        print(vc.head(20))

        # 看一下 non-missing 占整体多少
        non_missing = vc.sum()
        print(f"\n非缺失样本量: {non_missing} / {len(df)} (占 {non_missing/len(df)*100:.1f}%)")

        # 如果想顺便看看这个变量 × high_stress_group 的粗略交叉，也可以简单看一下
        if "high_stress_group" in df.columns:
            ctab = (
                df.groupby([col, "high_stress_group"])
                  .size()
                  .reset_index(name="count")
            )
            print("\n【按 high_stress_group 粗略交叉（前 20 行）】")
            print(ctab.head(20).to_string(index=False))

        print("=" * 80)
        print()

    print("检查完成。")

if __name__ == "__main__":
    main()
