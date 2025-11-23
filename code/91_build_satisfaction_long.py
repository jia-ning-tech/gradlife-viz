#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
91_build_satisfaction_long.py

构建 “满意度长表” satisfaction_long，用于后续所有满意度可视化和分析。

一行 = 一位受访者对 “学位某一个方面” 的满意度评分。

目前覆盖问卷 Q27：
- How satisfied are you with each of the following attributes or aspects of your degree?

包括这些方面（根据 metadata_step2_typed_clean）：
- Availability of funding
- Hours worked
- Social environment
- Degree of independence
- Recognition from supervisor
- Overall relationship with supervisor
- Overall compensation and benefits
- Vacation time
- Guidance received from adviser in lab/research
- Ability to attend meetings and conferences
- Work-life balance
- Career pathway guidance and advice
- Quality of teaching
- Balance of teaching and practical elements

使用的文件：
- /workspace/output/99_master/master_person_wide.csv
    - 提供 resp_id（与行号对应）
- /workspace/output/02_typed_clean/data_step2_typed_clean.csv
    - v074_num ~ v087_num 等满意度数值列
- /workspace/output/02_typed_clean/metadata_step2_typed_clean.csv
    - 提供这些列的 question_text / q_no / q_type

输出：
- /workspace/output/99_master/satisfaction_long.csv

字段结构：
- resp_id
- aspect_code   : 原始列名，如 v084_num
- q_no          : 问卷题号，如 "Q27.k"
- aspect_text   : 完整题目文本（英文）
- score         : 数值 Likert 评分（一般 1–7）
"""

from pathlib import Path
import pandas as pd

BASE = Path("/workspace")

PATH_MASTER = BASE / "output" / "99_master" / "master_person_wide.csv"
PATH_TYPED = BASE / "output" / "02_typed_clean" / "data_step2_typed_clean.csv"
PATH_META = BASE / "output" / "02_typed_clean" / "metadata_step2_typed_clean.csv"

OUTPUT_DIR = BASE / "output" / "99_master"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_CSV = OUTPUT_DIR / "satisfaction_long.csv"


def main():
    # === 0. 读取 master_person_wide（只需要 resp_id 和行数对齐） ===
    print("读取 master_person_wide ...")
    master = pd.read_csv(PATH_MASTER)
    print("master_person_wide 形状:", master.shape)

    # 我们假定 master 的行顺序与原始数据一致（resp_id = 行号 + 1）
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

    # === 2. 读取 metadata_step2_typed_clean，筛选 Q27 的 numeric 列 ===
    print("读取 metadata_step2_typed_clean ...")
    meta = pd.read_csv(PATH_META)
    print("metadata_step2_typed_clean 形状:", meta.shape)

    # Q27 的 numeric 列：q_no 以 "Q27" 开头且 q_type 为 likert_numeric
    mask_q27 = meta["q_no"].astype(str).str.startswith("Q27")
    mask_num = meta["q_type"] == "likert_numeric"
    meta_q27 = meta[mask_q27 & mask_num].copy()

    if meta_q27.empty:
        raise RuntimeError("在 metadata_step2_typed_clean 中没有找到 Q27 的 likert_numeric 列，请检查元数据。")

    print("\nQ27 满意度数值列：")
    print(meta_q27[["col_name", "q_no", "question_text"]].to_string(index=False))

    sat_cols = meta_q27["col_name"].tolist()

    # 确保这些列在 typed_clean 中存在
    missing = [c for c in sat_cols if c not in typed.columns]
    if missing:
        raise KeyError("data_step2_typed_clean 中缺少以下 Q27 数值列： " + ", ".join(missing))

    # === 3. 构造 long 格式 ===
    # 为 typed 加上 resp_id，按行号对齐
    typed = typed.reset_index(drop=True).copy()
    typed["resp_id"] = master["resp_id"].values

    # 只取 resp_id + Q27 数值列
    wide = typed[["resp_id"] + sat_cols].copy()

    # 宽转长
    long_df = wide.melt(
        id_vars=["resp_id"],
        value_vars=sat_cols,
        var_name="aspect_code",
        value_name="score",
    )

    # 合并元数据获取文本信息
    meta_q27_small = meta_q27[["col_name", "q_no", "question_text"]].rename(
        columns={"col_name": "aspect_code", "question_text": "aspect_text"}
    )

    long_df = long_df.merge(meta_q27_small, on="aspect_code", how="left")

    # 调整列顺序
    long_df = long_df[["resp_id", "aspect_code", "q_no", "aspect_text", "score"]]

    print("\n=== satisfaction_long 示例前 12 行 ===")
    print(long_df.head(12).to_string(index=False))

    # 简单看一下每个维度的非缺失样本量
    print("\n每个满意度维度的非缺失样本量：")
    cnt = (
        long_df
        .groupby("aspect_code")["score"]
        .count()
        .reset_index(name="n_non_missing")
        .merge(meta_q27_small[["aspect_code", "aspect_text"]], on="aspect_code", how="left")
        .sort_values("aspect_code")
    )
    print(cnt.to_string(index=False))

    # === 4. 输出 ===
    long_df.to_csv(OUT_CSV, index=False)
    print(f"\n已保存满意度长表到: {OUT_CSV}")


if __name__ == "__main__":
    main()
