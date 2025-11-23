import pandas as pd
from pathlib import Path

DERIV_PATH = Path("/workspace/output/04_worklife/worklife_derived_vars.csv")

df = pd.read_csv(DERIV_PATH)

print("=== high_hours 分布 ===")
print(df["high_hours"].value_counts(dropna=False))

print("\n=== low_worklife 分布 ===")
print(df["low_worklife"].value_counts(dropna=False))

print("\n=== high_stress_group 分布 ===")
print(df["high_stress_group"].value_counts(dropna=False))

print("\n=== hours_level 前 10 个取值 ===")
print(df["hours_level"].value_counts(dropna=False).head(10))

print("\n=== worklife_score 前 10 个取值 ===")
print(df["worklife_score"].value_counts(dropna=False).head(10))
