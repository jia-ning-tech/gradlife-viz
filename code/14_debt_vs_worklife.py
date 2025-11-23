import pandas as pd
from pathlib import Path
import json

BASE = Path("/workspace")

DATA_PATH = BASE / "output/02_typed_clean/data_step2_typed_clean.csv"
META_PATH = BASE / "output/02_typed_clean/metadata_step2_typed_clean.csv"
DERIVED_PATH = BASE / "output/04_worklife/worklife_derived_vars.csv"

OUTPUT_DIR = BASE / "output/05_debt"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    # 1. 读取派生的 worklife 变量（里面有 high_stress_group）
    df_work = pd.read_csv(DERIVED_PATH)

    # 2. 读取原始清洗后的数据，拿到 Q17: v039_code（是否预计负债）
    df_data = pd.read_csv(DATA_PATH)
    if "v039_code" not in df_data.columns:
        print("没有找到 v039_code 列，请确认 Q17 的 coded 列名。")
        return

    # 保证行顺序一致，用 index 对齐（我们一直没有打乱顺序，所以这样是安全的）
    df_work["v039_code"] = df_data["v039_code"]

    # 3. 从 metadata 中拿到 v039_code 的标签字典
    meta = pd.read_csv(META_PATH)
    row = meta.loc[meta["col_name"] == "v039_code"].iloc[0]
    labels_dict_raw = json.loads(row["value_labels"])  # key 是字符串 "1","2","3"...
    debt_labels = {int(k): v for k, v in labels_dict_raw.items()}

    # 映射出债务预期的文本标签
    df_work["debt_code_int"] = pd.to_numeric(df_work["v039_code"], errors="coerce").astype("Int64")
    df_work["debt_label"] = df_work["debt_code_int"].map(debt_labels)

    # 4. 统计：按 debt_label × high_stress_group 交叉表
    crosstab = (
        df_work
        .groupby(["debt_label", "high_stress_group"])
        .size()
        .reset_index(name="count")
    )

    # 在每个 debt_label 内部算百分比
    total_by_debt = crosstab.groupby("debt_label")["count"].transform("sum")
    crosstab["percent"] = crosstab["count"] / total_by_debt * 100

    # 保存结果
    out_path = OUTPUT_DIR / "debt_vs_high_stress.csv"
    crosstab.to_csv(out_path, index=False)
    print("已保存债务预期 × 高压组结果到：", out_path)

if __name__ == "__main__":
    main()
