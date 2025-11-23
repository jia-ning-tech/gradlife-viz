import pandas as pd
from pathlib import Path

# ========= 路径配置 =========
DATA_PATH = Path("/workspace/data/data.xlsx")
OUTPUT_DIR = Path("/workspace/output/01_cleaning")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ========= 读取原始 Excel（不使用任何行作为表头）=========

print(f"读取原始数据：{DATA_PATH}")
df_raw = pd.read_excel(DATA_PATH, header=None)

print("原始数据形状（含前两行表头）：", df_raw.shape)

# 第 1 行：原始编号（可能错位，但先保留以防后续对照）
row_codes = df_raw.iloc[0, :].copy()

# 第 2 行：问题文本（真正有意义的 header）
row_questions = df_raw.iloc[1, :].copy()

# 从第 3 行开始是正式数据
df_data = df_raw.iloc[2:, :].copy().reset_index(drop=True)

# ========= 生成规范的技术变量名 =========
# 例如 v001, v002, v003, ...
n_cols = df_data.shape[1]
col_names = [f"v{str(i+1).zfill(3)}" for i in range(n_cols)]
df_data.columns = col_names

print("生成技术变量名示例：", col_names[:10])

# ========= 构建基础 metadata 表 =========

metadata = pd.DataFrame({
    "col_name": col_names,               # 之后分析中真正使用的列名
    "question_text": row_questions.values,  # 来自第 2 行
    "orig_code_row1": row_codes.values      # 来自第 1 行（可能错位）
})

# 预留一些后面要填的列（先设为 None / 空）
metadata["q_no"] = None        # 问卷题号（如 Q1, Q2, Q12_a 等，后面人工/半自动补）
metadata["q_type"] = None      # 题型：single/multiple/likert/grid/open/numeric...
metadata["multi_group"] = None # 对于矩阵/多列题，标记它们属于哪个题组
metadata["value_type"] = None  # numeric/category/text...
metadata["value_labels"] = None  # 之后可以存 JSON 字符串或留空

# ========= 保存清洗后的数据和 metadata =========

data_out_path = OUTPUT_DIR / "data_step1_raw_clean.csv"
meta_out_path = OUTPUT_DIR / "metadata_step1_basic.csv"

df_data.to_csv(data_out_path, index=False)
metadata.to_csv(meta_out_path, index=False)

print(f"已保存数据到: {data_out_path}")
print(f"已保存元数据到: {meta_out_path}")

# ========= 简单查看一下前几列，方便你在 Jupyter 里检查 =========
print("\n【数据前 5 行】")
print(df_data.head())

print("\n【metadata 前 10 行】")
print(metadata.head(10))
