import pandas as pd
import numpy as np
import json
from pathlib import Path

# ===== 路径配置 =====
DATA_PATH = Path("/workspace/output/02_typed_clean/data_step2_typed_clean.csv")
META_PATH = Path("/workspace/output/02_typed_clean/metadata_step2_typed_clean.csv")

OUTPUT_DIR = Path("/workspace/output/03_descriptives")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ===== 一些小工具函数 =====

def parse_value_labels(val):
    """metadata 里 value_labels 列存的是 JSON 字符串 -> 解析为 dict"""
    if pd.isna(val):
        return {}
    if isinstance(val, dict):
        return val
    try:
        return json.loads(val)
    except Exception:
        return {}

def freq_table(series):
    """给一个 Series 做频数和百分比，返回 DataFrame，第一列统一叫 code"""
    counts = series.value_counts(dropna=False)
    perc = counts / counts.sum() * 100
    out = pd.DataFrame({"count": counts, "percent": perc})

    # 把索引（原来的取值）变成普通列
    out = out.reset_index()
    # 不管 index 列原来叫什么，都强制改名为 "code"
    first_col = out.columns[0]
    out = out.rename(columns={first_col: "code"})

    return out


# ===== 主流程 =====

def main():
    print("读取数据 ...")
    df = pd.read_csv(DATA_PATH)
    meta = pd.read_csv(META_PATH)

    # 方便查找：建一个以 col_name 为索引的 metadata 视图
    meta_idx = meta.set_index("col_name")

    # ---------- 1) 单选题（single_coded） ----------
    print("处理 single_coded ...")
    single_coded_cols = meta.loc[meta["q_type"] == "single_coded", "col_name"].tolist()
    single_results = []

    for col in single_coded_cols:
        if col not in df.columns:
            continue
        q_no = meta_idx.loc[col, "q_no"]
        q_text = meta_idx.loc[col, "question_text"]
        multi_group = meta_idx.loc[col, "multi_group"]
        value_labels = parse_value_labels(meta_idx.loc[col, "value_labels"])

        ft = freq_table(df[col])
        # 把 numeric code 转成 int（有 NaN 的要先过滤）
        ft["code_int"] = pd.to_numeric(ft["code"], errors="coerce").astype("Int64")
        ft["label"] = ft["code_int"].map(lambda x: value_labels.get(int(x), np.nan) if pd.notna(x) else np.nan)

        ft["col_name"] = col
        ft["q_no"] = q_no
        ft["question_text"] = q_text
        ft["multi_group"] = multi_group

        single_results.append(ft)

    if single_results:
        single_long = pd.concat(single_results, ignore_index=True)
        single_out = OUTPUT_DIR / "single_freq_long.csv"
        single_long.to_csv(single_out, index=False)
        print(f"single_coded 频数表已保存到: {single_out}")
    else:
        print("没有检测到 single_coded 变量。")

    # ---------- 2) Likert 题（likert_numeric） ----------
    print("处理 likert_numeric ...")
    likert_cols = meta.loc[meta["q_type"] == "likert_numeric", "col_name"].tolist()
    likert_results = []

    for col in likert_cols:
        if col not in df.columns:
            continue
        q_no = meta_idx.loc[col, "q_no"]
        q_text = meta_idx.loc[col, "question_text"]
        multi_group = meta_idx.loc[col, "multi_group"]
        value_labels = parse_value_labels(meta_idx.loc[col, "value_labels"])

        ft = freq_table(df[col])
        ft["code_int"] = pd.to_numeric(ft["code"], errors="coerce").astype("Int64")
        # 如果有 value_labels，就用它；否则 label 就等于 code 本身
        ft["label"] = ft["code_int"].map(lambda x: value_labels.get(int(x), x) if pd.notna(x) else np.nan)

        ft["col_name"] = col
        ft["q_no"] = q_no
        ft["question_text"] = q_text
        ft["multi_group"] = multi_group

        likert_results.append(ft)

    if likert_results:
        likert_long = pd.concat(likert_results, ignore_index=True)
        likert_out = OUTPUT_DIR / "likert_freq_long.csv"
        likert_long.to_csv(likert_out, index=False)
        print(f"Likert 频数表已保存到: {likert_out}")
    else:
        print("没有检测到 likert_numeric 变量。")

    # ---------- 3) 多选题（二元变量 multiple_binary） ----------
    print("处理 multiple_binary ...")
    multiple_bin_cols = meta.loc[meta["q_type"] == "multiple_binary", "col_name"].tolist()
    multi_results = []

    for col in multiple_bin_cols:
        if col not in df.columns:
            continue
        row = meta_idx.loc[col]
        q_no = row["q_no"]
        q_text = row["question_text"]
        multi_group = row["multi_group"]
        value_labels = parse_value_labels(row["value_labels"])

        s = df[col]
        # 只关心“选中”的比例（值==1）
        count_selected = (s == 1).sum()
        total = s.notna().sum()
        percent_selected = count_selected / total * 100 if total > 0 else np.nan

        # 默认 label = 1 对应的标签（通常是 “selected”）
        label1 = value_labels.get(1, "selected")

        multi_results.append({
            "col_name": col,
            "q_no": q_no,
            "question_text": q_text,
            "multi_group": multi_group,
            "code": 1,
            "label": label1,
            "count": count_selected,
            "percent": percent_selected,
            "n_valid": total,
        })

    if multi_results:
        multi_long = pd.DataFrame(multi_results)
        multi_out = OUTPUT_DIR / "multiple_freq_long.csv"
        multi_long.to_csv(multi_out, index=False)
        print(f"multiple_binary 频数表已保存到: {multi_out}")
    else:
        print("没有检测到 multiple_binary 变量。")

    print("全部描述统计导出完成。")

if __name__ == "__main__":
    main()
