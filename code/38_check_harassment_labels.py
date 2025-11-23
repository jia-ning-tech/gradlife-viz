# /workspace/code/38_check_harassment_labels.py

import pandas as pd
import json
from pathlib import Path

META_PATH = Path("/workspace/output/02_typed_clean/metadata_step2_typed_clean.csv")
DATA_PATH = Path("/workspace/output/02_typed_clean/data_step2_typed_clean.csv")

COL = "v112_code"  # Q39: discrimination / harassment [coded]


def parse_value_labels(val):
    """把 metadata 里的 value_labels 字段解析成 dict."""
    if pd.isna(val):
        return {}
    if isinstance(val, dict):
        return val
    try:
        return json.loads(val)
    except Exception:
        return {}


def main():
    meta = pd.read_csv(META_PATH)
    df = pd.read_csv(DATA_PATH)

    print("=== v112_code 在数据中的存在性 ===")
    print("v112_code in data columns:", COL in df.columns)
    print("数据形状:", df.shape)
    print()

    print("=== v112_code 元数据 ===")
    mrow = meta.loc[meta["col_name"] == COL]
    if mrow.empty:
        print("在 metadata 中没有找到列:", COL)
        return

    row = mrow.iloc[0]
    print("col_name:", row["col_name"])
    print("q_no:", row["q_no"])
    print("q_type:", row["q_type"])
    print("question_text:", row["question_text"])

    raw_labels = row.get("value_labels", None)
    print("raw value_labels:", raw_labels)
    print()

    labels_dict = parse_value_labels(raw_labels)
    print("=== 解析后的标签字典 ===")
    for k, v in labels_dict.items():
        print(f"{k} -> {v}")

    print("\n=== v112_code 频数分布（含缺失） ===")
    print(df[COL].value_counts(dropna=False))


if __name__ == "__main__":
    main()
