import pandas as pd
from pathlib import Path

DATA_PATH = Path("/workspace/output/02_typed_clean/data_step2_typed_clean.csv")
META_PATH = Path("/workspace/output/02_typed_clean/metadata_step2_typed_clean.csv")

df = pd.read_csv(DATA_PATH)
meta = pd.read_csv(META_PATH)

print("数据形状:", df.shape)
print("\nq_type 分布:")
print(meta["q_type"].value_counts())

print("\n示例几列：")
print(df.head()[meta["col_name"].head(10).tolist()])
