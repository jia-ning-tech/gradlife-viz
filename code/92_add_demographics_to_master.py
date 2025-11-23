#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
92_add_demographics_to_master.py  （修正版）

用途：
- 在 master_person_wide 上添加（或修正）两个“人口学/背景”维度：
  1) degree_prep_code / degree_prep_label
     -> 实际对应问卷 Q52.a：
        How well is your current graduate degree preparing you for your desired career path?
  2) caring_responsibility_code / caring_responsibility_label
     -> 对应问卷 Q53：
        Caring responsibilities（照护责任）

⚠️ 说明：
- 之前版本错误地把 Q52 映射为 gender_code / gender_label，容易被误认为“性别”。
  这个版本会：
  - 如果 master 中存在 gender_code / gender_label，先删掉它们；
  - 然后用新的列名 degree_prep_* / caring_responsibility_* 重新写入。

依赖文件：
- /workspace/output/99_master/master_person_wide.csv
- /workspace/output/02_typed_clean/data_step2_typed_clean.csv
- /workspace/output/02_typed_clean/metadata_step2_typed_clean.csv

输出：
- 覆盖更新 /workspace/output/99_master/master_person_wide.csv
- 同时尽量更新 master_person_wide.parquet（如有 pyarrow）
"""

from pathlib import Path
import pandas as pd

BASE = Path("/workspace")

PATH_MASTER = BASE / "output" / "99_master" / "master_person_wide.csv"
PATH_MASTER_PARQUET = BASE / "output" / "99_master" / "master_person_wide.parquet"
PATH_TYPED = BASE / "output" / "02_typed_clean" / "data_step2_typed_clean.csv"
PATH_META = BASE / "output" / "02_typed_clean" / "metadata_step2_typed_clean.csv"


def find_numeric_col_for_q(meta: pd.DataFrame, q_no: str, fallback: str | None = None) -> str | None:
    """
    在 metadata 中寻找某个题号 q_no 对应的数值列（* _num）。
    如果找不到，则返回 fallback。
    """
    if meta is None or meta.empty:
        return fallback

    sub = meta[meta["q_no"] == q_no]
    if sub.empty:
        return fallback

    candidates = sub[sub["col_name"].str.endswith("_num", na=False)]["col_name"].tolist()
    if candidates:
        return candidates[0]

    return fallback


def find_text_col_for_q(meta: pd.DataFrame, q_no: str, fallback: str | None = None) -> str | None:
    """
    在 metadata 中寻找某个题号 q_no 对应的文字列（不以 _num 结尾）。
    如果找不到，则返回 fallback。
    """
    if meta is None or meta.empty:
        return fallback

    sub = meta[meta["q_no"] == q_no]
    if sub.empty:
        return fallback

    candidates = sub[~sub["col_name"].str.endswith("_num", na=False)]["col_name"].tolist()
    if candidates:
        return candidates[0]

    return fallback


def main():
    # === 1. 读取 master_person_wide ===
    print("读取 master_person_wide ...")
    master = pd.read_csv(PATH_MASTER)
    print("master_person_wide 形状:", master.shape)
    print("master_person_wide 列名示例:", list(master.columns)[:20])

    # === 2. 删除旧的误导性列（gender_*）===
    cols_to_drop = []
    for c in ["gender_code", "gender_label"]:
        if c in master.columns:
            cols_to_drop.append(c)
    if cols_to_drop:
        print(f"⚠️ 将从 master 中删除旧列（避免误认性别）：{cols_to_drop}")
        master = master.drop(columns=cols_to_drop)
    else:
        print("未发现旧的 gender_* 列，无需删除。")

    # 也顺便删除旧的 caring_responsibility_code/label（如果存在，稍后会重建）
    old_care_cols = []
    for c in ["caring_responsibility_code", "caring_responsibility_label"]:
        if c in master.columns:
            old_care_cols.append(c)
    if old_care_cols:
        print(f"将重建照护责任列，先删除旧列: {old_care_cols}")
        master = master.drop(columns=old_care_cols)

    # === 3. 读取 typed_clean 和 metadata ===
    print("读取 data_step2_typed_clean ...")
    typed = pd.read_csv(PATH_TYPED)
    print("data_step2_typed_clean 形状:", typed.shape)

    print("读取 metadata_step2_typed_clean ...")
    meta = pd.read_csv(PATH_META)
    print("metadata_step2_typed_clean 形状:", meta.shape)

    # 行数对齐检查
    if len(typed) != len(master):
        print("⚠️ typed_clean 与 master 行数不一致，将按照最小行数截断对齐。")
        n = min(len(typed), len(master))
        master = master.iloc[:n].reset_index(drop=True)
        typed = typed.iloc[:n].reset_index(drop=True)
    else:
        master = master.reset_index(drop=True)
        typed = typed.reset_index(drop=True)

    # === 4. 确定 Q52、Q53 的数值列和文字列 ===
    # Q52: degree preparation（学位准备程度）
    q52_num = find_numeric_col_for_q(meta, "Q52", fallback="v197_num" if "v197_num" in typed.columns else None)
    q52_txt = find_text_col_for_q(meta, "Q52", fallback="v197" if "v197" in typed.columns else None)

    # Q53: caring responsibilities
    q53_num = find_numeric_col_for_q(meta, "Q53", fallback="v206_num" if "v206_num" in typed.columns else None)
    q53_txt = find_text_col_for_q(meta, "Q53", fallback="v206" if "v206" in typed.columns else None)

    print("\n为 Q52 选择 numeric 列:", q52_num, "，文字列:", q52_txt)
    print("为 Q53 选择 numeric 列:", q53_num, "，文字列:", q53_txt)

    if q52_num is None or q53_num is None:
        raise RuntimeError("无法在 typed_clean/metadata 中找到 Q52 或 Q53 的数值列，请检查元数据。")

    # === 5. 构建新的人口学/背景子表 ===
    demo_cols = [q52_num, q53_num]
    if q52_txt is not None:
        demo_cols.append(q52_txt)
    if q53_txt is not None:
        demo_cols.append(q53_txt)

    demo = typed[demo_cols].copy()

    # 数值列重命名
    demo = demo.rename(columns={
        q52_num: "degree_prep_code",
        q53_num: "caring_responsibility_code"
    })

    # 文本列（如果存在）重命名
    if q52_txt is not None:
        demo = demo.rename(columns={q52_txt: "degree_prep_label"})
    else:
        demo["degree_prep_label"] = pd.NA

    if q53_txt is not None:
        demo = demo.rename(columns={q53_txt: "caring_responsibility_label"})
    else:
        demo["caring_responsibility_label"] = pd.NA

    # 加上 resp_id，方便预览
    if "resp_id" in master.columns:
        demo.insert(0, "resp_id", master["resp_id"])
    else:
        demo.insert(0, "resp_id", range(1, len(demo) + 1))

    print("\n示例：新的人口学/背景子表前 10 行：")
    print(demo.head(10).to_string(index=False))

    # === 6. 把 demo 合并回 master（按行号对齐）===
    # 因为已经确保行数对齐，可以直接按列追加
    for col in ["degree_prep_code", "degree_prep_label",
                "caring_responsibility_code", "caring_responsibility_label"]:
        master[col] = demo[col]

    # === 7. 简单统计 ===
    print("\n合并后 master_person_wide 前 10 行（含新增列）：")
    preview_cols = [c for c in [
        "resp_id",
        "degree_label",
        "region_continent",
        "degree_prep_code",
        "degree_prep_label",
        "caring_responsibility_code",
        "caring_responsibility_label",
        "high_stress_group"
    ] if c in master.columns]
    print(master[preview_cols].head(10).to_string(index=False))

    if "degree_prep_code" in master.columns:
        print("\ndegree_prep_code 非缺失样本量:", master["degree_prep_code"].notna().sum())
        print("degree_prep_label 分布：")
        print(master["degree_prep_label"].value_counts(dropna=False))

    if "caring_responsibility_code" in master.columns:
        print("\ncaring_responsibility_code 非缺失样本量:", master["caring_responsibility_code"].notna().sum())
        print("caring_responsibility_label 分布：")
        print(master["caring_responsibility_label"].value_counts(dropna=False))

    # === 8. 保存覆盖 master_person_wide ===
    master.to_csv(PATH_MASTER, index=False)
    print(f"\n已更新并保存 master_person_wide 到: {PATH_MASTER}")

    try:
        master.to_parquet(PATH_MASTER_PARQUET, index=False)
        print(f"已更新 master_person_wide.parquet 到: {PATH_MASTER_PARQUET}")
    except Exception as e:
        print(f"⚠️ 保存 Parquet 时出错（可忽略，仅 CSV 必须成功）：{e}")


if __name__ == "__main__":
    main()
