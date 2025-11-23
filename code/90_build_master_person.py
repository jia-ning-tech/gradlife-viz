#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
90_build_master_person.py

构建“主表” master_person_wide：
- 每行 = 1 个受访者
- 当前包含：
    * resp_id
    * degree_label / degree_code_int
    * region_continent
    * hours_level + 原始工时文本 v089 / v089_code
    * worklife_score（工作-生活平衡评分）
    * v084_num（原始 Likert 数值）
    * 学制总时长（文本 + 数值）
    * 已读年数（文本 + 数值）
    * 是否在本国学习（文本 + flag）
    * 高工时 / 低工作生活平衡 相关标记
    * 导师 / 学校支持指数（原始均值 + z 分数 + Low/Med/High + 象限标签）

来源：
- /workspace/output/04_worklife/worklife_derived_vars.csv
    - hours_level, high_stress_group, v004_code, v089, v089_code,
      worklife_score, v084_num, high_hours, low_worklife 等
- /workspace/output/05_region/region_worklife_derived.csv
    - region_continent
- /workspace/output/02_typed_clean/data_step2_typed_clean.csv
    - v005 (总学制时长), v006 (已读年数), v016 (是否在本国就读)
    - v079_num, v091_num（导师关系 / 职业对话）
    - v097_num, v100_num, v101_num（心理健康服务 & work–life 支持）

输出：
- /workspace/output/99_master/master_person_wide.csv
- /workspace/output/99_master/master_person_wide.parquet
"""

from pathlib import Path
import numpy as np
import pandas as pd

BASE = Path("/workspace")

PATH_WORKLIFE = BASE / "output" / "04_worklife" / "worklife_derived_vars.csv"
PATH_REGION = BASE / "output" / "05_region" / "region_worklife_derived.csv"
PATH_TYPED = BASE / "output" / "02_typed_clean" / "data_step2_typed_clean.csv"

OUTPUT_DIR = BASE / "output" / "99_master"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HOURS_COL = "hours_level"
STRESS_COL = "high_stress_group"
DEGREE_CODE_COL = "v004_code"
REGION_COL = "region_continent"

SUP_NUM_COLS = ["v079_num", "v091_num", "v097_num", "v100_num", "v101_num"]


def map_duration_to_years(text):
    """
    将问卷中的“X years / Less than a year / More than 7 years”
    映射为一个近似的数值年数。
    """
    if pd.isna(text):
        return pd.NA
    t = str(text).strip().lower()
    mapping = {
        "less than a year": 0.5,
        "1 year": 1.0,
        "2 years": 2.0,
        "3 years": 3.0,
        "4 years": 4.0,
        "5 years": 5.0,
        "6 years": 6.0,
        "7 years": 7.0,
        "more than 7 years": 8.0,   # 近似上界
    }
    return mapping.get(t, pd.NA)


def standardize_series(s: pd.Series) -> pd.Series:
    """
    计算 z 分数： (x - mean) / std
    若 std=0 或全缺失，则返回全 NaN。
    """
    mean = s.mean(skipna=True)
    std = s.std(skipna=True)
    if std == 0 or np.isnan(std):
        return pd.Series(np.nan, index=s.index)
    return (s - mean) / std


def categorize_z(z: pd.Series) -> pd.Series:
    """
    把 z 分数划成三档：
      z <= -0.5       -> 'Low'
      -0.5 < z < 0.5  -> 'Medium'
      z >= 0.5        -> 'High'
    """
    def _cat(val):
        if pd.isna(val):
            return pd.NA
        if val <= -0.5:
            return "Low"
        elif val >= 0.5:
            return "High"
        else:
            return "Medium"

    return z.apply(_cat)


def main():
    # === 1. 读取 worklife_derived_vars ===
    print("读取 worklife_derived_vars ...")
    wf = pd.read_csv(PATH_WORKLIFE)
    print("worklife_derived_vars 形状:", wf.shape)
    print("worklife_derived_vars 列名示例:", list(wf.columns)[:12])

    required_cols = [HOURS_COL, STRESS_COL, DEGREE_CODE_COL]
    missing = [c for c in required_cols if c not in wf.columns]
    if missing:
        raise KeyError(
            "worklife_derived_vars.csv 缺少关键列："
            + ", ".join(missing)
            + "；请先检查 05_worklife_analysis 的输出。"
        )

    # === 2. 读取 region_worklife_derived（如有） ===
    try:
        print("读取 region_worklife_derived ...")
        region = pd.read_csv(PATH_REGION)
        print("region_worklife_derived 形状:", region.shape)
    except FileNotFoundError:
        print(f"⚠️ 找不到 {PATH_REGION}，将暂时不加入 region_continent。")
        region = None

    # 以 worklife_derived_vars 为基础
    df = wf.reset_index(drop=True)

    # 按行对齐方式拼上 region_continent
    if region is not None and len(region) == len(df) and REGION_COL in region.columns:
        print("按行对齐方式合并 region_continent ...")
        region_sub = region[[REGION_COL]].reset_index(drop=True)
        df = pd.concat([df, region_sub], axis=1)
    else:
        if region is not None:
            print(
                "⚠️ region_worklife_derived 行数与 worklife_derived_vars 不一致，"
                "或缺少 region_continent，region 信息暂时忽略。"
            )
        if REGION_COL not in df.columns:
            df[REGION_COL] = "All / unknown"

    # === 3. 读取 typed_clean，拼上学制 & 国别信息 & 支持打分 ===
    try:
        print("读取 data_step2_typed_clean ...")
        typed = pd.read_csv(PATH_TYPED)
        print("data_step2_typed_clean 形状:", typed.shape)
    except FileNotFoundError:
        print(f"⚠️ 找不到 {PATH_TYPED}，这一版将不加入学制/是否在本国学习/支持信息。")
        typed = None

    if typed is not None and len(typed) == len(df):
        print("按行对齐方式合并 v005/v006/v016 以及支持相关 *_num ...")
        base_cols = ["v005", "v006", "v016"]
        support_cols_present = [c for c in SUP_NUM_COLS if c in typed.columns]
        merge_cols = base_cols + support_cols_present

        typed_sub = typed[merge_cols].reset_index(drop=True)
        typed_sub = typed_sub.rename(
            columns={
                "v005": "degree_duration_text",
                "v006": "degree_progress_text",
                "v016": "study_in_home_country",
            }
        )
        df = pd.concat([df, typed_sub], axis=1)

        # 映射为数值年数
        df["degree_duration_years"] = df["degree_duration_text"].map(map_duration_to_years)
        df["degree_progress_years"] = df["degree_progress_text"].map(map_duration_to_years)

        # 是否在本国学习：Yes/No → 1/0
        df["study_in_home_country_flag"] = (
            df["study_in_home_country"]
            .astype(str)
            .str.strip()
            .str.lower()
            .map({"yes": 1, "no": 0})
            .astype("Int64")
        )

        # === 3.1 支持指数：导师 / 机构 ===
        sup_vars = ["v079_num", "v091_num"]
        inst_vars = ["v097_num", "v100_num", "v101_num"]

        missing_sup = [c for c in sup_vars if c not in df.columns]
        missing_inst = [c for c in inst_vars if c not in df.columns]
        if missing_sup or missing_inst:
            raise KeyError(
                "主数据中缺少构造支持指数所需的列：\n"
                f"  导师支持缺少: {missing_sup}\n"
                f"  学校支持缺少: {missing_inst}\n"
                "请确认 data_step2_typed_clean.csv 中包含这些 *_num 变量。"
            )

        # 确保为数值
        for col in sup_vars + inst_vars:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # 原始指数：简单平均
        df["supervisor_support_raw"] = df[sup_vars].mean(axis=1, skipna=True)
        df["institution_support_raw"] = df[inst_vars].mean(axis=1, skipna=True)

        # z 分数
        df["supervisor_z"] = standardize_series(df["supervisor_support_raw"])
        df["institution_z"] = standardize_series(df["institution_support_raw"])

        # 三档分类
        df["supervisor_cat"] = categorize_z(df["supervisor_z"])
        df["institution_cat"] = categorize_z(df["institution_z"])

        # 象限标签
        df["support_quadrant_label"] = (
            df["supervisor_cat"].astype("string")
            + " supervisor / "
            + df["institution_cat"].astype("string")
            + " institution"
        )

    else:
        if typed is not None:
            print(
                "⚠️ data_step2_typed_clean 行数与 worklife_derived_vars 不一致，"
                "暂不合并学制 / 本国学习 / 支持信息。"
            )

    # === 4. 构造 resp_id & degree_label ===
    df = df.reset_index(drop=True)
    df["resp_id"] = df.index + 1  # 1,2,...,N

    degree_code = pd.to_numeric(df[DEGREE_CODE_COL], errors="coerce")
    df["degree_code_int"] = degree_code.round().astype("Int64")
    degree_map = {
        1: "Doctorate",
        2: "Master's",
        3: "Dual degree",
    }
    df["degree_label"] = df["degree_code_int"].map(degree_map)

    df[STRESS_COL] = pd.to_numeric(df[STRESS_COL], errors="coerce").astype("Int64")

    # === 5. 高工时 / 低工作生活平衡相关标记（如果存在） ===
    if "high_hours" in df.columns:
        df["high_hours"] = pd.to_numeric(df["high_hours"], errors="coerce").astype("Int64")
        df["high_hours_flag"] = df["high_hours"]
    else:
        df["high_hours_flag"] = pd.NA

    if "low_worklife" in df.columns:
        df["low_worklife"] = pd.to_numeric(df["low_worklife"], errors="coerce").astype("Int64")
        df["low_worklife_flag"] = df["low_worklife"]
    else:
        df["low_worklife_flag"] = pd.NA

    df["high_hours_only_flag"] = (
        ((df["high_hours_flag"] == 1) & (df["low_worklife_flag"] != 1))
        .astype("Int64")
    )
    df["low_worklife_only_flag"] = (
        ((df["low_worklife_flag"] == 1) & (df["high_hours_flag"] != 1))
        .astype("Int64")
    )
    df["both_high_hours_and_low_wlb_flag"] = (
        ((df["high_hours_flag"] == 1) & (df["low_worklife_flag"] == 1))
        .astype("Int64")
    )

    # === 6. 选择要输出到主表的字段 ===
    cols_master = [
        "resp_id",
        "degree_label",
        "degree_code_int",
        REGION_COL,
        HOURS_COL,
        STRESS_COL,
        "v089",          # 原始工时文本
        "v089_code",     # 工时代码
        "worklife_score",
        "v084_num",
        # 学制 & 进度
        "degree_duration_text",
        "degree_duration_years",
        "degree_progress_text",
        "degree_progress_years",
        "study_in_home_country",
        "study_in_home_country_flag",
        # 高工时 / 低WLB 标记
        "high_hours_flag",
        "low_worklife_flag",
        "high_hours_only_flag",
        "low_worklife_only_flag",
        "both_high_hours_and_low_wlb_flag",
        # 支持题原始分
        "v079_num",
        "v091_num",
        "v097_num",
        "v100_num",
        "v101_num",
        # 支持指数 & 象限
        "supervisor_support_raw",
        "institution_support_raw",
        "supervisor_z",
        "institution_z",
        "supervisor_cat",
        "institution_cat",
        "support_quadrant_label",
    ]

    # 防御性过滤一下（防止某些列不存在）
    cols_master = [c for c in cols_master if c in df.columns]

    master = df[cols_master].copy()

    print("\n=== master_person_wide 预览（前 10 行）===")
    print(master.head(10).to_string(index=False))

    print("\n各学位 × 高压分布：")
    ctab = (
        master.groupby(["degree_label", STRESS_COL])
        .size()
        .reset_index(name="count")
    )
    ctab["percent_within_degree"] = (
        ctab["count"]
        / ctab.groupby("degree_label")["count"].transform("sum")
        * 100
    )
    print(ctab.to_string(index=False, float_format=lambda x: f"{x:5.1f}"))

    # 简单看一下支持象限分布
    if "support_quadrant_label" in master.columns:
        print("\n支持象限 × 高压分布（前几行）：")
        quad_tab = (
            master.groupby(["support_quadrant_label", STRESS_COL])
            .size()
            .reset_index(name="count")
            .sort_values(["support_quadrant_label", STRESS_COL])
        )
        print(quad_tab.head(12).to_string(index=False))

    # === 7. 保存 ===
    out_csv = OUTPUT_DIR / "master_person_wide.csv"
    out_parquet = OUTPUT_DIR / "master_person_wide.parquet"

    master.to_csv(out_csv, index=False)
    parquet_ok = False
    try:
        master.to_parquet(out_parquet, index=False)
        parquet_ok = True
    except Exception as e:
        print(f"⚠️ 保存 Parquet 时出错：{e}")

    print("\n已保存主表：")
    print(" - CSV   :", out_csv)
    if parquet_ok:
        print(" - Parquet:", out_parquet)
    else:
        print(" - Parquet: 未生成（可选，不影响后续分析）")


if __name__ == "__main__":
    main()
