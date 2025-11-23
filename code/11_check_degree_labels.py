import pandas as pd
from pathlib import Path
import json

META_PATH = Path("/workspace/output/02_typed_clean/metadata_step2_typed_clean.csv")

meta = pd.read_csv(META_PATH)

# 找到 v004_code 这一行
row = meta.loc[meta["col_name"] == "v004_code"].iloc[0]

print("=== v004_code 元数据 ===")
print("col_name:", row["col_name"])
print("q_no:", row["q_no"])
print("q_type:", row["q_type"])
print("question_text:", row["question_text"])
print("raw value_labels:", row["value_labels"])

# 尝试把 value_labels 解析成 dict
try:
    labels_dict = json.loads(row["value_labels"])
    print("\n=== 解析后的标签字典 ===")
    for k, v in labels_dict.items():
        print(f"{k} -> {v}")
except Exception as e:
    print("\n解析 value_labels 时出错:", e)
