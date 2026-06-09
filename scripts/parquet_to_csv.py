import pandas as pd
import csv
df = pd.read_parquet("/home/yuki_noa/FoodAtlas/datasets_preprocessed/products_analysis.parquet")
df.to_csv(
    "/home/yuki_noa/FoodAtlas/datasets_preprocessed/products_analysis.csv",
    escapechar='\\',          # 使用反斜杠作为转义字符
    quoting=csv.QUOTE_MINIMAL # 或者使用 csv.QUOTE_NONNUMERIC
)
print("保存成功！")