import pandas as pd
from pathlib import Path

DATA_PATH = Path("/workspace/output/02_typed_clean/data_step2_typed_clean.csv")

df = pd.read_csv(DATA_PATH)

print("v084 原始回答的前 20 个：")
print(df["v084"].dropna().unique()[:20])

print("\n频数分布：")
print(df["v084"].value_counts(dropna=False))
