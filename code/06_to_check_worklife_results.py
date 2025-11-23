import pandas as pd
from pathlib import Path

BASE = Path("/workspace/output/04_worklife")

# 1. 看整体高压群体比例
overall_path = BASE / "high_stress_overall.csv"
overall = pd.read_csv(overall_path)
print("=== Overall high_stress_group ===")
print(overall)

# 2. 看不同学位下的高压比例
by_degree_path = BASE / "high_stress_by_degree.csv"
by_degree = pd.read_csv(by_degree_path)
print("\n=== high_stress_group by degree code ===")
print(by_degree)

# 3. 如果你想直观看每个学位编码对应什么：到 single_freq_long 查一下 v004_code
freq_path = Path("/workspace/output/03_descriptives/single_freq_long.csv")
freq = pd.read_csv(freq_path)
degree_freq = freq.loc[freq["col_name"] == "v004_code", ["code", "label", "count", "percent"]]
print("\n=== Degree code -> label ===")
print(degree_freq)
