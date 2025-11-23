import pandas as pd
from pathlib import Path
import json

# 路径配置
BASE = Path("/workspace")
META_PATH = BASE / "output/02_typed_clean/metadata_step2_typed_clean.csv"
BY_DEGREE_PATH = BASE / "output/04_worklife/high_stress_by_degree.csv"
OUTPUT_PATH = BASE / "output/04_worklife/high_stress_by_degree_labeled.csv"

def main():
    # 1. 读取 metadata，拿到 v004_code 的标签字典
    meta = pd.read_csv(META_PATH)
    row = meta.loc[meta["col_name"] == "v004_code"].iloc[0]
    labels_dict_raw = json.loads(row["value_labels"])  # keys 是字符串 "1","2","3"
    # 把 key 变成整数，方便和 v004_code 的数值匹配
    degree_labels = {int(k): v for k, v in labels_dict_raw.items()}

    # 2. 读取 high_stress_by_degree 结果
    df = pd.read_csv(BY_DEGREE_PATH)

    # v004_code 目前是浮点数（1.0/2.0/3.0），先转成 Int 再映射
    df["degree_code_int"] = df["v004_code"].round().astype("Int64")
    df["degree_label"] = df["degree_code_int"].map(degree_labels)

    # 3. 保存带有标签的新文件
    df.to_csv(OUTPUT_PATH, index=False)
    print("已保存带学位名称的结果到：", OUTPUT_PATH)

if __name__ == "__main__":
    main()
