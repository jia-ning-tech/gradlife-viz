import pandas as pd
from pathlib import Path

freq_path = Path("/workspace/output/03_descriptives/single_freq_long.csv")
freq = pd.read_csv(freq_path)

HOURS_COL = "v089_code"
sub = freq.loc[freq["col_name"] == HOURS_COL, ["code", "label", "count", "percent"]]
print(sub)
