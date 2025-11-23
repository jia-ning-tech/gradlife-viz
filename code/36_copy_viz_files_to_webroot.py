from pathlib import Path
import shutil

# 源数据目录：之前所有 Python 导出的可视化 CSV 都在这里
SRC_DIR = Path("../output/08_viz_data")

# 目标目录：前端页面的“网站根目录”下面的 output 目录
# region_high_stress.html 位于 /workspace/09_js_demo/ 里，
# 它用的相对路径是 ../output/08_viz_data/xxx.csv
DST_DIR = Path("../08_viz_data")

DST_DIR.mkdir(parents=True, exist_ok=True)

print(f"源目录: {SRC_DIR}")
print(f"目标目录: {DST_DIR}")

count = 0
for src in SRC_DIR.glob("*.csv"):
    dst = DST_DIR / src.name
    shutil.copy2(src, dst)
    print(f"复制: {src.name} -> {dst}")
    count += 1

print(f"\n总共复制 {count} 个 CSV 文件。")
print("现在前端页面用的 ../output/08_viz_data/xxx.csv 路径应该都能访问到了。")
