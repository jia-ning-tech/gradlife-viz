import pandas as pd
import numpy as np
from pathlib import Path
import json
import re

# ============ 路径配置 ============
DATA_STEP1_PATH = Path("/workspace/output/01_cleaning/data_step1_raw_clean.csv")
# META_STEP1_PATH = Path("/workspace/output/01_cleaning/metadata_step1_basic.csv")
META_STEP1_PATH = Path("/workspace/output/01_cleaning/metadata_step1_basic.xlsx")

OUTPUT_DIR = Path("/workspace/output/02_typed_clean")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DATA_OUT_PATH = OUTPUT_DIR / "data_step2_typed_clean.csv"
META_OUT_PATH = OUTPUT_DIR / "metadata_step2_typed_clean.csv"

# ============ 一些辅助函数 ============

def standardize_str(x):
    """统一去掉前后空格，小写，便于比较。"""
    if pd.isna(x):
        return np.nan
    return str(x).strip()

def slugify(text, max_len=30):
    """
    把一句英文题目/选项变成简短变量名片段：
    'Work-life balance' -> 'work_life_balance'
    """
    if text is None or (isinstance(text, float) and np.isnan(text)):
        return ""
    text = str(text)
    # 只保留字母数字和空格
    text = re.sub(r"[^0-9a-zA-Z\s]+", "", text)
    # 多空格压缩
    text = re.sub(r"\s+", " ", text).strip().lower()
    # 截断
    words = text.split(" ")[:5]
    slug = "_".join(words)
    return slug[:max_len]

def infer_from_orig_code(row):
    """
    利用 orig_code_row1 粗略推断 q_no 和 multi_group，减少手工工作量。
    规则：
      - 'ID.xxx' → q_no='ID.xxx', q_type='id'
      - 'Q5:1' → q_no='Q5', multi_group='Q5'
      - 'Q2' → q_no='Q2'
    不会覆盖你已经手工填好的 q_no/q_type/multi_group。
    """
    code = str(row.get("orig_code_row1", "")).strip()
    q_no = row.get("q_no")
    q_type = row.get("q_type")
    multi_group = row.get("multi_group")

    # 如果已经有内容就不动
    if pd.notna(q_no):
        pass
    else:
        if code.startswith("ID."):
            q_no = code
        elif code.startswith("Q"):
            # 例如 Q5:1, Q5:2
            if ":" in code:
                q_no = code.split(":")[0]
            else:
                q_no = code

    # ID 开头的变量默认标为 id 类型（如果没标过）
    if pd.isna(q_type) and code.startswith("ID."):
        q_type = "id"

    # 带冒号的 Qx:y 归为一个 multi_group（如果没标过）
    if pd.isna(multi_group) and code.startswith("Q") and ":" in code:
        multi_group = code.split(":")[0]

    return pd.Series({"q_no": q_no, "q_type": q_type, "multi_group": multi_group})


def encode_single_choice(series):
    """
    单选题：把文本类别自动编码为 1..k，并返回编码后的 Series 和 映射 dict。
    映射 dict: {code(int): label(str)}
    """
    s = series.astype("string").map(standardize_str)
    # 保留原始显示文本（未小写）当 label
    # 用 value_counts 排序，让高频选项编号靠前，便于查看
    value_counts = s.value_counts(dropna=True)
    categories = list(value_counts.index)

    code_map = {cat: i+1 for i, cat in enumerate(categories)}
    encoded = s.map(code_map)

    # 生成标签映射（把 None/nan 排除）
    value_labels = {int(v): str(k) for k, v in code_map.items() if k is not None and k == k}
    return encoded, value_labels


def encode_likert(series):
    """
    Likert 题默认也用单选逻辑自动编码。
    如果后续你想用“强烈反对/同意”明确映射，可以改这里/增加参数。
    """
    return encode_single_choice(series)


def encode_multiple_choice(df, cols):
    """
    多选题的一组列：
      - 假设：任意非空/非明显否定值视为选中(1)，否则为 0。
      - 返回一个新的 DataFrame（同样的列名，但都是 0/1）。
    你之后可以根据实际选项文本再细改逻辑。
    """
    df_multi = pd.DataFrame(index=df.index)

    for col in cols:
        s = df[col]

        def to_binary(x):
            if pd.isna(x):
                return 0
            txt = str(x).strip().lower()
            if txt in ["", "nan", "none", "no", "not selected", "0", "false"]:
                return 0
            # 其它一律视为“选中”
            return 1

        df_multi[col] = s.map(to_binary)

    return df_multi


def clean_open_text(series):
    """
    开放题：主要是统一成 string，另外可以新增“是否作答”的辅助列。
    """
    s = series.astype("string")
    answered = s.notna() & (s.str.strip() != "")
    return s, answered.astype(int)


# ============ 主流程 ============
def read_csv_safely(path):
    """
    尝试用多种编码读取 CSV，避免 UnicodeDecodeError。
    优先 utf-8 / utf-8-sig，如果都不行就退到 latin1。
    """
    encodings_to_try = ["utf-8", "utf-8-sig", "latin1"]
    last_error = None
    for enc in encodings_to_try:
        try:
            print(f"尝试用编码 {enc} 读取: {path}")
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError as e:
            print(f"用编码 {enc} 读取失败：{e}")
            last_error = e
    # 如果都失败，就把最后一个错误抛出去
    raise last_error

def main():
    print("加载 step1 数据和 metadata ...")
    df = pd.read_csv(DATA_STEP1_PATH)          # 原来的数据基本没事
    # meta = read_csv_safely(META_STEP1_PATH) 
    meta = pd.read_excel(META_STEP1_PATH)       # ✅ 用 Excel 读取 metadata

    # 确保这些列存在
    for col in ["q_no", "q_type", "multi_group", "value_type", "value_labels"]:
        if col not in meta.columns:
            meta[col] = None

    # ---------- 1) 利用 orig_code_row1 补全 q_no / multi_group / 部分 q_type ----------
    print("根据 orig_code_row1 粗略推断 q_no, q_type(id), multi_group ...")
    inferred = meta.apply(infer_from_orig_code, axis=1)
    meta["q_no"] = meta["q_no"].combine_first(inferred["q_no"])
    meta["q_type"] = meta["q_type"].combine_first(inferred["q_type"])
    meta["multi_group"] = meta["multi_group"].combine_first(inferred["multi_group"])

    # ---------- 2) 按题型清洗 ----------
    print("开始按 q_type 清洗变量 ...")

    df_clean = df.copy()
    updated_value_labels = {}  # {col_name: dict(code->label)}

    # 先把 q_type / multi_group 读出来，避免类型问题
    meta["q_type"] = meta["q_type"].astype("string")
    meta["multi_group"] = meta["multi_group"].astype("string")

    # (a) 单选题
    single_vars = meta.loc[meta["q_type"] == "single", "col_name"].tolist()
    print(f"  单选题数量: {len(single_vars)}")
    for col in single_vars:
        print(f"    编码 single: {col}")
        encoded, val_labels = encode_single_choice(df_clean[col])
        new_col = f"{col}_code"
        df_clean[new_col] = encoded
        updated_value_labels[new_col] = val_labels
        # 在 metadata 中为新列添加记录
        question_text = meta.loc[meta["col_name"] == col, "question_text"].iloc[0]
        q_no = meta.loc[meta["col_name"] == col, "q_no"].iloc[0]
        new_row = {
            "col_name": new_col,
            "question_text": question_text + " [coded]",
            "orig_code_row1": meta.loc[meta["col_name"] == col, "orig_code_row1"].iloc[0],
            "q_no": q_no,
            "q_type": "single_coded",
            "multi_group": meta.loc[meta["col_name"] == col, "multi_group"].iloc[0],
            "value_type": "numeric",
            "value_labels": json.dumps(val_labels, ensure_ascii=False),
        }
        meta = pd.concat([meta, pd.DataFrame([new_row])], ignore_index=True)

    # (b) Likert 题
    likert_vars = meta.loc[meta["q_type"] == "likert", "col_name"].tolist()
    print(f"  Likert 题数量: {len(likert_vars)}")
    for col in likert_vars:
        print(f"    编码 likert: {col}")
        encoded, val_labels = encode_likert(df_clean[col])
        new_col = f"{col}_num"
        df_clean[new_col] = encoded
        updated_value_labels[new_col] = val_labels
        question_text = meta.loc[meta["col_name"] == col, "question_text"].iloc[0]
        q_no = meta.loc[meta["col_name"] == col, "q_no"].iloc[0]
        new_row = {
            "col_name": new_col,
            "question_text": question_text + " [numeric]",
            "orig_code_row1": meta.loc[meta["col_name"] == col, "orig_code_row1"].iloc[0],
            "q_no": q_no,
            "q_type": "likert_numeric",
            "multi_group": meta.loc[meta["col_name"] == col, "multi_group"].iloc[0],
            "value_type": "numeric",
            "value_labels": json.dumps(val_labels, ensure_ascii=False),
        }
        meta = pd.concat([meta, pd.DataFrame([new_row])], ignore_index=True)

    # (c) 多选题：按 multi_group 分组处理
    # 约定：你在 metadata 中给这一组列都标 q_type="multiple"，并且 multi_group 相同（例如 "Q5"）
    multiple_meta = meta.loc[meta["q_type"] == "multiple"].copy()
    print(f"  多选题条目数量: {multiple_meta.shape[0]}")
    for group, sub_meta in multiple_meta.groupby("multi_group"):
        cols = sub_meta["col_name"].tolist()
        if group == "nan" or pd.isna(group):
            # 没有 multi_group 的，就先跳过或单独处理
            print(f"    [跳过] multi_group 为空的 multiple 列: {cols}")
            continue
        print(f"    处理多选组 {group}: {cols}")
        df_multi = encode_multiple_choice(df_clean, cols)

        # 为每一列创建二元变量（覆盖原列或新建列都可以，这里选择新建 *_bin）
        for col in cols:
            new_col = f"{col}_bin"
            df_clean[new_col] = df_multi[col]
            val_labels = {0: "not_selected", 1: "selected"}
            updated_value_labels[new_col] = val_labels

            # 更新 metadata，为新列增加记录
            row_original = meta.loc[meta["col_name"] == col].iloc[0]
            new_row = {
                "col_name": new_col,
                "question_text": str(row_original["question_text"]) + " [binary]",
                "orig_code_row1": row_original["orig_code_row1"],
                "q_no": row_original["q_no"],
                "q_type": "multiple_binary",
                "multi_group": row_original["multi_group"],
                "value_type": "numeric",
                "value_labels": json.dumps(val_labels, ensure_ascii=False),
            }
            meta = pd.concat([meta, pd.DataFrame([new_row])], ignore_index=True)

    # (d) 开放题：保留文本 + 是否作答
    open_vars = meta.loc[meta["q_type"] == "open", "col_name"].tolist()
    print(f"  开放题数量: {len(open_vars)}")
    for col in open_vars:
        print(f"    处理 open: {col}")
        text, answered = clean_open_text(df_clean[col])
        df_clean[col] = text  # 覆盖原列为标准化文本
        new_col = f"{col}_answered"
        df_clean[new_col] = answered

        # 在 metadata 中添加 answered 列记录
        row_original = meta.loc[meta["col_name"] == col].iloc[0]
        new_row = {
            "col_name": new_col,
            "question_text": str(row_original["question_text"]) + " [answered_flag]",
            "orig_code_row1": row_original["orig_code_row1"],
            "q_no": row_original["q_no"],
            "q_type": "open_answered_flag",
            "multi_group": row_original["multi_group"],
            "value_type": "numeric",
            "value_labels": json.dumps({0: "no", 1: "yes"}, ensure_ascii=False),
        }
        meta = pd.concat([meta, pd.DataFrame([new_row])], ignore_index=True)

    # (e) numeric：简单转为数值（例如已经是数字/区间中点）
    numeric_vars = meta.loc[meta["q_type"] == "numeric", "col_name"].tolist()
    print(f"  数值题数量: {len(numeric_vars)}")
    for col in numeric_vars:
        print(f"    转为 numeric: {col}")
        df_clean[col] = pd.to_numeric(df_clean[col], errors="coerce")
        # 在 metadata 标记 value_type
        meta.loc[meta["col_name"] == col, "value_type"] = "numeric"

    # id 类型就原样复制，只标记 value_type
    id_vars = meta.loc[meta["q_type"] == "id", "col_name"].tolist()
    print(f"  ID 类变量数量: {len(id_vars)}")
    for col in id_vars:
        meta.loc[meta["col_name"] == col, "value_type"] = "id"

    # ---------- 3) 保存结果 ----------
    print("保存清洗后的数据和更新后的 metadata ...")
    df_clean.to_csv(DATA_OUT_PATH, index=False)
    meta.to_csv(META_OUT_PATH, index=False)

    print(f"数据已保存到: {DATA_OUT_PATH}")
    print(f"metadata 已保存到: {META_OUT_PATH}")
    print("完成。")

if __name__ == "__main__":
    main()
