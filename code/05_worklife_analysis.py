import pandas as pd
import numpy as np
from pathlib import Path
import json

DATA_PATH = Path("/workspace/output/02_typed_clean/data_step2_typed_clean.csv")
META_PATH = Path("/workspace/output/02_typed_clean/metadata_step2_typed_clean.csv")

OUTPUT_DIR = Path("/workspace/output/04_worklife")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ======== 在这里填你自己的变量名（已经根据 metadata 查好）========
# 原始工时选项文本所在列（没有 _code 的那一列）
HOURS_TEXT_COL = "v089"          # Q29 原始回答文本
HOURS_COL = "v089_code"          # 若后续要用 code 频数可以保留

# 工作–生活平衡满意度：原始文本所在列（注意：不是 _num）
WORKLIFE_TEXT_COL = "v084"       # Q27.k 原始回答文本
WORKLIFE_COL = "v084_num"        # 暂时不用它做高低判断，但可以保留

# 学位类型：Which of the following degrees are you currently studying for? [coded]
DEGREE_COL = "v004_code"     

# 地区变量先留空，后面需要再加
REGION_COL = ""              # 或者写 None 也可以

# === 用原始工时文字定义“高工时” ===
# 这里的 key 一定要和 v089 的原始文本完全一致（注意大小写和空格）
HOURS_TEXT_TO_LEVEL = {
    "Less than 11 hours": "low",
    "11-20 hours": "low",
    "21-30 hours": "medium",
    "31-40 hours": "medium",
    "41-50 hours": "high",
    "51-60 hours": "high",
    "61-70 hours": "very_high",
    "71-80 hours": "very_high",
    "More than 80 hours": "very_high",
}

HIGH_LEVELS = {"high", "very_high"}


# === 用原始 work-life balance 文本映射到 1–7 分数 ===
# 下面的 key 必须和你刚刚看到的 v084 原始值一模一样
WORKLIFE_TEXT_TO_SCORE = {
    "1 = Not at all satisfied": 1,
    "2": 2,
    "3": 3,
    "4 = Neither satisfied not dissatisfied": 4,
    "5": 5,
    "6": 6,
    "7 = Extremely satisfied": 7,
    # "Not applicable" 不在字典里 → map 之后会是 NaN
}

LOW_WORKLIFE_THRESHOLD = 3  # 1/2/3 视为“低工作生活平衡”





def parse_value_labels(val):
    if pd.isna(val):
        return {}
    if isinstance(val, dict):
        return val
    try:
        return json.loads(val)
    except Exception:
        return {}


def main():
    df = pd.read_csv(DATA_PATH)
    meta = pd.read_csv(META_PATH).set_index("col_name")

    # 简单检查一下变量是否存在
    for col in [HOURS_COL, WORKLIFE_COL, DEGREE_COL, REGION_COL]:
        if col and col not in df.columns:
            print(f"警告：列 {col} 不在数据中，请检查变量名是否填写正确。")

    # --- 构造高工时变量 ---
    # --- 构造高工时变量（基于原始文字映射） ---
    print("构造 high_hours 变量 ...")

    # 先把原始文本标准化一下（去空格）
    df["hours_text_clean"] = df[HOURS_TEXT_COL].astype("string").str.strip()

    # 映射到我们定义的 level（low/medium/high/...）
    df["hours_level"] = df["hours_text_clean"].map(HOURS_TEXT_TO_LEVEL)

    # 再根据 level 判断是否为“高工时”
    df["high_hours"] = np.where(df["hours_level"].isin(HIGH_LEVELS), 1, 0)


    # --- 构造低工作生活平衡变量 ---
    # --- 构造低工作生活平衡变量（基于原始文本映射） ---
    print("构造 low_worklife 变量 ...")

    # 标准化文本，去掉前后空格
    df["worklife_text_clean"] = df[WORKLIFE_TEXT_COL].astype("string").str.strip()

    # 映射到我们定义的 1–7 分数
    df["worklife_score"] = df["worklife_text_clean"].map(WORKLIFE_TEXT_TO_SCORE)

    # 判断是否“低工作生活平衡”：score 不为空 且 <= 阈值
    df["low_worklife"] = np.where(
        (df["worklife_score"].notna()) & (df["worklife_score"] <= LOW_WORKLIFE_THRESHOLD),
        1,
        0,
    )


    # --- 组合：高工时 & 低平衡 ---
    print("构造 high_stress_group 变量 ...")
    df["high_stress_group"] = np.where((df["high_hours"] == 1) & (df["low_worklife"] == 1), 1, 0)

    # 保存一份带这三个派生变量的子表，方便以后别的分析用
    # deriv_cols = [HOURS_COL, WORKLIFE_COL, "high_hours", "low_worklife", "high_stress_group"]
    deriv_cols = [
        HOURS_TEXT_COL,
        HOURS_COL,
        WORKLIFE_TEXT_COL,
        WORKLIFE_COL,
        "hours_level",
        "high_hours",
        "worklife_score",
        "low_worklife",
        "high_stress_group",
    ]
    if DEGREE_COL:
        deriv_cols.append(DEGREE_COL)
    if REGION_COL:
        deriv_cols.append(REGION_COL)


    df[deriv_cols].to_csv(OUTPUT_DIR / "worklife_derived_vars.csv", index=False)

    # --- 1) 高压群体整体比例 ---
    overall = (
        df["high_stress_group"]
        .value_counts(dropna=False)
        .rename_axis("high_stress_group")
        .reset_index(name="count")
    )
    overall["percent"] = overall["count"] / overall["count"].sum() * 100
    overall.to_csv(OUTPUT_DIR / "high_stress_overall.csv", index=False)
    print("已导出整体高压群体比例。")

    # --- 2) 按学位类型分组 ---
    if DEGREE_COL:
        degree_counts = (
            df.groupby([DEGREE_COL, "high_stress_group"])
            .size()
            .reset_index(name="count")
        )
        # 计算每个学位内的百分比
        total_by_degree = degree_counts.groupby(DEGREE_COL)["count"].transform("sum")
        degree_counts["percent"] = degree_counts["count"] / total_by_degree * 100
        degree_counts.to_csv(OUTPUT_DIR / "high_stress_by_degree.csv", index=False)
        print("已导出按学位类型分组的高压群体比例。")

    # --- 3) 按地区分组 ---
    if REGION_COL:
        region_counts = (
            df.groupby([REGION_COL, "high_stress_group"])
            .size()
            .reset_index(name="count")
        )
        total_by_region = region_counts.groupby(REGION_COL)["count"].transform("sum")
        region_counts["percent"] = region_counts["count"] / total_by_region * 100
        region_counts.to_csv(OUTPUT_DIR / "high_stress_by_region.csv", index=False)
        print("已导出按地区分组的高压群体比例。")

    print("工作–生活平衡相关分析完成。输出目录：", OUTPUT_DIR)

if __name__ == "__main__":
    main()
