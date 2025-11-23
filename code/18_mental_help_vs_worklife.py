import pandas as pd
from pathlib import Path
import json

BASE = Path("/workspace")

DATA_PATH = BASE / "output/02_typed_clean/data_step2_typed_clean.csv"
META_PATH = BASE / "output/02_typed_clean/metadata_step2_typed_clean.csv"
DERIVED_PATH = BASE / "output/04_worklife/worklife_derived_vars.csv"

OUTPUT_DIR = BASE / "output/06_mental_health"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    # 1. 读取已有的 worklife 派生数据（里面有 high_stress_group）
    df_work = pd.read_csv(DERIVED_PATH)

    # 2. 读取清洗后的主数据，拿到 v095_code（Q33：是否收到/需要焦虑抑郁相关的帮助）
    df_data = pd.read_csv(DATA_PATH)
    if "v095_code" not in df_data.columns:
        print("没有找到 v095_code 列，请确认列名是否正确。")
        return

    # 保持行顺序，用 index 对齐
    df_work["v095_code"] = df_data["v095_code"]

    # 3. 从 metadata 中解析 v095_code 的标签字典
    meta = pd.read_csv(META_PATH)
    row = meta.loc[meta["col_name"] == "v095_code"].iloc[0]
    labels_raw = row["value_labels"]
    labels_dict = json.loads(labels_raw)          # key 是字符串
    help_labels = {int(k): v for k, v in labels_dict.items()}

    # 映射出文本标签
    df_work["help_code_int"] = pd.to_numeric(df_work["v095_code"], errors="coerce").astype("Int64")
    df_work["help_label"] = df_work["help_code_int"].map(help_labels)

    # 4. 统计：按 help_label × high_stress_group 分组
    crosstab = (
        df_work
        .groupby(["help_label", "high_stress_group"])
        .size()
        .reset_index(name="count")
    )

    # 在每个 help_label 内部算百分比
    total_by_help = crosstab.groupby("help_label")["count"].transform("sum")
    crosstab["percent"] = crosstab["count"] / total_by_help * 100

    # 5. 保存结果
    out_path = OUTPUT_DIR / "mental_help_vs_high_stress.csv"
    crosstab.to_csv(out_path, index=False)
    print("已保存心理健康求助 × 高压组结果到：", out_path)

if __name__ == "__main__":
    main()
