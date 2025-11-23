import pandas as pd
from pathlib import Path

INPUT_PATH = Path("/workspace/output/05_region/region_vs_high_stress.csv")
OUTPUT_DIR = Path("/workspace/output/08_viz_data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    df = pd.read_csv(INPUT_PATH)

    # 确保列名正确
    expected_cols = {"region_continent", "high_stress_group", "count", "percent_within_region"}
    if not expected_cols.issubset(df.columns):
        print("⚠️ 输入文件列名不符合预期，请检查:", INPUT_PATH)
        print("实际列名:", df.columns.tolist())
        return

    # 先计算每个地区的总人数
    total_by_region = df.groupby("region_continent")["count"].sum().rename("total_count")

    # 高压组（high_stress_group = 1）
    high = df.loc[df["high_stress_group"] == 1].copy()
    high = high.set_index("region_continent")

    # 非高压组（high_stress_group = 0）
    low = df.loc[df["high_stress_group"] == 0].copy()
    low = low.set_index("region_continent")

    # 组装可视化用宽表
    regions = sorted(df["region_continent"].unique())

    rows = []
    for reg in regions:
        if pd.isna(reg):
            continue
        tot = total_by_region.get(reg, 0)

        high_row = high.loc[reg] if reg in high.index else None
        low_row = low.loc[reg] if reg in low.index else None

        high_count = int(high_row["count"]) if high_row is not None else 0
        high_pct = float(high_row["percent_within_region"]) if high_row is not None else 0.0

        low_count = int(low_row["count"]) if low_row is not None else 0
        low_pct = float(low_row["percent_within_region"]) if low_row is not None else 0.0

        rows.append({
            "region_continent": reg,
            "high_stress_count": high_count,
            "high_stress_percent": high_pct,
            "non_high_stress_count": low_count,
            "non_high_stress_percent": low_pct,
            "total_count": int(tot),
        })

    out_df = pd.DataFrame(rows)

    # 为了美观按 total_count 降序排一下
    out_df = out_df.sort_values("total_count", ascending=False).reset_index(drop=True)

    out_path = OUTPUT_DIR / "viz_region_high_stress.csv"
    out_df.to_csv(out_path, index=False)
    print("已导出可视化用的 地区×高压 数据到:", out_path)
    print("\n预览前几行：")
    print(out_df.head())

if __name__ == "__main__":
    main()
