# /workspace/code/40_harassment_viz_export.py
"""
从 39_harassment_vs_worklife.py 生成的交叉表中，
导出前端可视化使用的宽表：
  /workspace/output/08_viz_data/viz_harassment_high_stress.csv

目标格式类似 bullying 那一份：
  harassment_label, high_stress_percent, high_stress_count, total_count
"""

import pandas as pd
from pathlib import Path

# 输入：刚刚生成的交叉表
INPUT_PATH = Path("/workspace/output/07_harassment/harassment_vs_high_stress.csv")
# 输出目录（与其他 viz_xxx 对齐）
VIZ_DIR = Path("/workspace/output/08_viz_data")
VIZ_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_PATH = VIZ_DIR / "viz_harassment_high_stress.csv"


def main():
    print("读取交叉表:", INPUT_PATH)
    df = pd.read_csv(INPUT_PATH)

    print("原始交叉表预览：")
    print(df)

    # 我们只保留 high_stress_group == 1 的那几行，
    # 因为 high_stress_percent 是“在该类中，高压组的比例”
    high = df[df["high_stress_group"] == 1].copy()

    # 计算 total_count：同一个 harassment_label 下，0+1 的和
    total_by_label = (
        df.groupby("harassment_label")["count"]
        .sum()
        .rename("total_count")
        .reset_index()
    )

    # 合并 total_count
    high = high.merge(total_by_label, on="harassment_label", how="left")

    # 重命名列，给前端一个简单的结构
    high = high.rename(
        columns={
            "harassment_label": "harassment_label",
            "percent": "high_stress_percent",
            "count": "high_stress_count",
        }
    )

    # 只保留需要的列，并做一下排序（可选）
    high = high[["harassment_label", "high_stress_percent", "high_stress_count", "total_count"]]

    print("\n导出给前端用的宽表：")
    print(high)

    high.to_csv(OUTPUT_PATH, index=False)
    print("\n已保存可视化用的骚扰/歧视 × 高压数据到:", OUTPUT_PATH)


if __name__ == "__main__":
    main()
