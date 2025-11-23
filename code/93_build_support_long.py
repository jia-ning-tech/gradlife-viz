#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
93_build_support_long.py

构建 “支持相关长表” support_long，用于后续所有
导师支持 / 学校&心理健康支持 的可视化与分析。

一行 = 一位受访者对 “某一个支持条目” 的评分。

涵盖两块题（根据 metadata_step2_typed_clean）：

- Q32.a–d: My supervisor ...
    - v091_num, v092_num, v093_num, v094_num
- Q35.a–e: Mental health & university support ...
    - v097_num, v098_num, v099_num, v100_num, v101_num

使用的文件：
- /workspace/output/99_master/master_person_wide.csv
    - 提供 resp_id（与行号一致）
- /workspace/output/02_typed_clean/data_step2_typed_clean.csv
    - 提供各 *_num 数值列
- /workspace/output/02_typed_clean/metadata_step2_typed_clean.csv
    - 提供 col_name / q_no / question_text / q_type

输出：
- /workspace/output/99_master/support_long.csv

字段：
- resp_id
- item_code   : 原始列名，如 v097_num
- q_no        : 问卷题号，如 "Q32.a"
- scale_group : 'Q32' 或 'Q35'
- item_text   : 完整题目文本
- score       : 数值评分
"""

from pathlib import Path
import pandas as pd

BASE = Path("/workspace")

PATH_MASTER = BASE / "output" / "99_master" / "master_person_wide.csv"
PATH_TYPED = BASE / "output" / "02_typed_clean" / "data_step2_typed_clean.csv"
PATH_META = BASE / "output" / "02_typed_clean" / "metadata_step2_typed_clean.csv"

OUTPUT_DIR = BASE / "output" / "99_master"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_CSV = OUTPUT_DIR / "support_long.csv"


def main():
    # === 0. 读取 master_person_wide（只需要 resp_id 和行数对齐） ===
    print("读取 master_person_wide ...")
    master = pd.read_csv(PATH_MASTER)
    print("master_person_wide 形状:", master.shape)

    if "resp_id" not in master.columns:
        raise KeyError("master_person_wide 中缺少 resp_id 列，请先确认 90_build_master_person.py 的输出。")

    n_master = len(master)

    # === 1. 读取 typed_clean ===
    print("读取 data_step2_typed_clean ...")
    typed = pd.read_csv(PATH_TYPED)
    print("data_step2_typed_clean 形状:", typed.shape)

    if len(typed) != n_master:
        raise ValueError(
            f"master_person_wide 行数 ({n_master}) 与 data_step2_typed_clean 行数 ({len(typed)}) 不一致，"
            "请检查前序清洗步骤。"
        )

    # === 2. 读取 metadata_step2_typed_clean，筛选 Q32 和 Q35 的 numeric 列 ===
    print("读取 metadata_step2_typed_clean ...")
    meta = pd.read_csv(PATH_META)
    print("metadata_step2_typed_clean 形状:", meta.shape)

    meta["q_no_str"] = meta["q_no"].astype(str)
    meta["q_type_str"] = meta["q_type"].astype(str)
    meta["col_name_str"] = meta["col_name"].astype(str)

    # 支持题：
    # - 题号以 Q32 或 Q35 开头
    # - q_type 中包含 "likert_numeric"（如果没有，就退一步用 "numeric"）
    # - 列名以 "_num" 结尾（避免选到 code / text 列）
    mask_q32 = meta["q_no_str"].str.startswith("Q32")
    mask_q35 = meta["q_no_str"].str.startswith("Q35")
    mask_likert_num = meta["q_type_str"].str.contains("likert_numeric", case=False, na=False)
    mask_any_num = meta["q_type_str"].str.contains("numeric", case=False, na=False)
    mask_is_num_col = meta["col_name_str"].str.endswith("_num")

    meta_support = meta[(mask_is_num_col) & (mask_likert_num) & (mask_q32 | mask_q35)].copy()

    # 如果没有严格的 likert_numeric，就退一步用任何 numeric 类型
    if meta_support.empty:
        print("⚠️ 没有找到 q_type = likert_numeric 的 Q32/Q35 *_num 列，退一步使用任何 numeric 类型。")
        meta_support = meta[(mask_is_num_col) & (mask_any_num) & (mask_q32 | mask_q35)].copy()

    if meta_support.empty:
        raise RuntimeError(
            "在 metadata_step2_typed_clean 中没有找到 Q32 或 Q35 的 *_num numeric 列，"
            "请检查元数据的 q_no / q_type / col_name。"
        )

    print("\n支持相关数值列（Q32 & Q35）：")
    print(meta_support[["col_name", "q_no", "question_text"]].to_string(index=False))

    support_cols = meta_support["col_name"].tolist()

    # 确保这些列在 typed_clean 中存在
    missing = [c for c in support_cols if c not in typed.columns]
    if missing:
        raise KeyError("data_step2_typed_clean 中缺少以下支持题数值列： " + ", ".join(missing))

    # === 3. 构造 long 格式 ===
    # 为 typed 加上 resp_id，按行号对齐
    typed = typed.reset_index(drop=True).copy()
    typed["resp_id"] = master["resp_id"].values

    # 只取 resp_id + 支持数值列
    wide = typed[["resp_id"] + support_cols].copy()

    # 宽转长
    long_df = wide.melt(
        id_vars=["resp_id"],
        value_vars=support_cols,
        var_name="item_code",
        value_name="score",
    )

    # 合并元数据获取文本信息
    meta_support_small = meta_support[["col_name", "q_no", "question_text"]].rename(
        columns={"col_name": "item_code", "question_text": "item_text"}
    )

    long_df = long_df.merge(meta_support_small, on="item_code", how="left")

    # 增加 scale_group（Q32 / Q35）
    def detect_group(q_no_str: str) -> str:
        if isinstance(q_no_str, str):
            if q_no_str.startswith("Q32"):
                return "Q32"
            if q_no_str.startswith("Q35"):
                return "Q35"
        return "other"

    long_df["scale_group"] = long_df["q_no"].astype(str).apply(detect_group)

    # 调整列顺序
    long_df = long_df[["resp_id", "item_code", "q_no", "scale_group", "item_text", "score"]]

    print("\n=== support_long 示例前 12 行 ===")
    print(long_df.head(12).to_string(index=False))

    # 简单看一下每个条目的非缺失样本量
    print("\n每个支持条目的非缺失样本量：")
    cnt = (
        long_df
        .groupby(["scale_group", "item_code"])["score"]
        .count()
        .reset_index(name="n_non_missing")
        .merge(
            meta_support_small[["item_code", "item_text"]],
            on="item_code",
            how="left"
        )
        .sort_values(["scale_group", "item_code"])
    )
    print(cnt.to_string(index=False))

    # === 4. 输出 ===
    long_df.to_csv(OUT_CSV, index=False)
    print(f"\n已保存支持相关长表到: {OUT_CSV}")


if __name__ == "__main__":
    main()
