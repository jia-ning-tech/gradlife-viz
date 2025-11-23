import pandas as pd
import json
from pathlib import Path

DATA_PATH = Path("/workspace/output/02_typed_clean/data_step2_typed_clean.csv")
WORKLIFE_PATH = Path("/workspace/output/04_worklife/worklife_derived_vars.csv")
META_PATH = Path("/workspace/output/02_typed_clean/metadata_step2_typed_clean.csv")

OUT_DIR = Path("/workspace/output/07_support")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 支持 / 关系变量（与 30 脚本一致）
SUPPORT_VARS = {
    "v079_num": "Q27.f – Overall relationship with supervisor",
    "v091_num": "Q32.a – Supervisor makes time for frank conversations about my career",
    "v097_num": "Q35.a – Mental health & wellbeing services tailored to graduate students",
    "v100_num": "Q35.d – Other types of mental health/wellbeing support beyond 1:1",
    "v101_num": "Q35.e – University supports good work–life balance",
}


def parse_value_labels(val):
    if pd.isna(val):
        return {}
    if isinstance(val, dict):
        return val
    try:
        return json.loads(val)
    except Exception:
        return {}


def clean_likert_1_to_7(x):
    """只保留 1–7 的值，其他(包括8等)视为缺失。"""
    if pd.isna(x):
        return pd.NA
    try:
        v = float(x)
    except Exception:
        return pd.NA
    if 1 <= v <= 7:
        return v
    return pd.NA


def cat_support(score):
    """把 1–7 的支持感/满意度分成三档."""
    if pd.isna(score):
        return pd.NA
    try:
        s = float(score)
    except Exception:
        return pd.NA

    if s <= 3:
        return "Low support (1–3)"
    elif s == 4:
        return "Neutral (4)"
    else:  # 5–7
        return "High support (5–7)"


def main():
    df = pd.read_csv(DATA_PATH)
    wl = pd.read_csv(WORKLIFE_PATH)

    # 合并 high_stress_group
    if len(df) != len(wl):
        print("⚠️ 警告：主数据和 worklife_derived_vars 行数不一致！")
        print("data_step2_typed_clean 行数:", len(df))
        print("worklife_derived_vars 行数:", len(wl))
        return
    df["high_stress_group"] = wl["high_stress_group"]

    # 读取 metadata，拿学位类型标签
    meta = pd.read_csv(META_PATH)
    meta_idx = meta.set_index("col_name")

    if "v004_code" not in meta_idx.index:
        print("⚠️ metadata 中找不到 v004_code（学位类型 coded）")
        return

    deg_row = meta_idx.loc["v004_code"]
    valmap = parse_value_labels(deg_row.get("value_labels", "{}"))
    # 转成 int -> label
    degree_label_map = {}
    for k, v in valmap.items():
        try:
            code_int = int(k)
            degree_label_map[code_int] = v
        except Exception:
            continue

    # 从 worklife_derived_vars 里拿 degree coded（之前在那边已经用的是 v004_code）
    if "v004_code" not in wl.columns and "v004_code" not in df.columns:
        print("⚠️ 无法在数据中找到 v004_code（学位类型）列。")
        return

    if "v004_code" in wl.columns:
        df["degree_code"] = wl["v004_code"]
    else:
        df["degree_code"] = df["v004_code"]

    df["degree_code_int"] = pd.to_numeric(df["degree_code"], errors="coerce").astype("Int64")
    df["degree_label"] = df["degree_code_int"].map(degree_label_map)

    print("=== 学位类型分布（degree_code_int × degree_label） ===")
    print(
        df.groupby(["degree_code_int", "degree_label"])
        .size()
        .reset_index(name="count")
    )

    all_tables = []

    for col, q_label in SUPPORT_VARS.items():
        print("=" * 80)
        print(f"处理变量: {col}")
        print(f"题目: {q_label}")

        if col not in df.columns:
            print(f"⚠️ 列 {col} 不在数据中，跳过。")
            continue

        # 清洗为 1–7
        clean_col = col + "_clean_deg"
        df[clean_col] = df[col].apply(clean_likert_1_to_7)

        # 分档
        cat_col = col + "_cat_deg"
        df[cat_col] = df[clean_col].apply(cat_support)

        print("\n【分档后的分布（不分学位）】")
        print(df[cat_col].value_counts(dropna=False))

        # 子集：有学位标签、有支持档次标签、有 high_stress_group
        sub = df[[cat_col, "degree_code_int", "degree_label", "high_stress_group"]].dropna(
            subset=[cat_col, "degree_code_int", "degree_label"]
        )

        # 按 支持档次 × 学位 × high_stress_group 交叉表
        ct = (
            sub.groupby([cat_col, "degree_code_int", "degree_label", "high_stress_group"])
            .size()
            .reset_index(name="count")
        )

        # 在「同一支持档次 + 学位」内部算比例
        total_by_level_deg = ct.groupby([cat_col, "degree_code_int"])["count"].transform("sum")
        ct["percent"] = ct["count"] / total_by_level_deg * 100

        # 统一列名
        ct = ct.rename(
            columns={
                cat_col: "level",
                "degree_code_int": "degree_code_int",
                "degree_label": "degree_label",
                "high_stress_group": "high_stress_group",
            }
        )
        ct["question"] = q_label
        ct["factor"] = col

        # 调整列顺序
        ct = ct[
            [
                "question",
                "factor",
                "degree_code_int",
                "degree_label",
                "level",
                "high_stress_group",
                "count",
                "percent",
            ]
        ]

        out_path = OUT_DIR / f"{col}_vs_high_stress_by_degree.csv"
        ct.to_csv(out_path, index=False)
        print(f"已导出 {q_label} × 高压组 × 学位类型 结果到: {out_path}")
        print(ct.head())
        all_tables.append(ct)
        print("-" * 80)

    # 合并所有支持变量
    if all_tables:
        viz = pd.concat(all_tables, ignore_index=True)
        viz_out = OUT_DIR / "viz_support_high_stress_by_degree.csv"
        viz.to_csv(viz_out, index=False)
        print("所有支持/关系变量 × 高压 × 学位类型 的长表已保存到:", viz_out)
    else:
        print("⚠️ 没有生成任何表，请检查 SUPPORT_VARS 的配置。")


if __name__ == "__main__":
    main()
