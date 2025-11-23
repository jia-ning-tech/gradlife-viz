from pathlib import Path
import pandas as pd

CSV_PATH = Path("/workspace/output/01_cleaning/metadata_step1_basic.csv")
XLSX_PATH = Path("/workspace/output/01_cleaning/metadata_step1_basic.xlsx")

# 这里用 latin1 是因为你刚才成功用 latin1 读过
meta = pd.read_csv(CSV_PATH, encoding="latin1")
meta.to_excel(XLSX_PATH, index=False)

print("已导出为 Excel 文件：", XLSX_PATH)
