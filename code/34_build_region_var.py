import pandas as pd
from pathlib import Path

DATA_PATH = Path("/workspace/output/02_typed_clean/data_step2_typed_clean.csv")
WORKLIFE_DERIVED = Path("/workspace/output/04_worklife/worklife_derived_vars.csv")

OUTPUT_DIR = Path("/workspace/output/05_region")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    # 读主数据
    df = pd.read_csv(DATA_PATH)
    print("原始数据形状:", df.shape)

    # 读 high_stress_group
    wf = pd.read_csv(WORKLIFE_DERIVED)
    if "high_stress_group" not in wf.columns:
        print("⚠️ worklife_derived_vars.csv 里没有 high_stress_group，请先确认第 05 步脚本。")
        return

    # 按行号拼接（两边都是 3253 行）
    df["high_stress_group"] = wf["high_stress_group"]

    # 构造大洲/地区变量
    # v031: Asia; v032: Australasia; v033: Africa; v034: Europe
    # v035: North/Central America; v036: South America
    region = pd.Series(pd.NA, index=df.index, dtype="object")

    if "v031" in df.columns:
        region = region.mask(df["v031"].notna(), "Asia")
    if "v032" in df.columns:
        region = region.mask(df["v032"].notna(), "Australasia")
    if "v033" in df.columns:
        region = region.mask(df["v033"].notna(), "Africa")
    if "v034" in df.columns:
        region = region.mask(df["v034"].notna(), "Europe")
    if "v035" in df.columns:
        region = region.mask(df["v035"].notna(), "North/Central America")
    if "v036" in df.columns:
        region = region.mask(df["v036"].notna(), "South America")

    df["region_continent"] = region

    print("\n=== region_continent 分布（含缺失）===")
    print(df["region_continent"].value_counts(dropna=False))

    # 简单看一下 Region × high_stress_group
    if "high_stress_group" in df.columns:
        ctab = (
            df.groupby(["region_continent", "high_stress_group"])
              .size()
              .reset_index(name="count")
        )
        ctab["percent_within_region"] = (
            ctab["count"] /
            ctab.groupby("region_continent")["count"].transform("sum") * 100
        )
        print("\n=== Region × high_stress_group 粗略交叉 ===")
        print(ctab.to_string(index=False))

        # 保存这个交叉表
        ctab.to_csv(OUTPUT_DIR / "region_vs_high_stress.csv", index=False)

    # 再保存一个行级子表，后面前端可能用得到
    cols_to_save = [
        "region_continent",
        "high_stress_group",
        "v031", "v032", "v033", "v034", "v035", "v036",
    ]
    cols_to_save = [c for c in cols_to_save if c in df.columns]

    df[cols_to_save].to_csv(OUTPUT_DIR / "region_worklife_derived.csv", index=False)

    print("\n已保存：")
    print(" - 行级子表:", OUTPUT_DIR / "region_worklife_derived.csv")
    print(" - 交叉表:", OUTPUT_DIR / "region_vs_high_stress.csv")

if __name__ == "__main__":
    main()
