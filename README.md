# FoodAtlas

FoodAtlas 是一个基于 Open Food Facts 数据的课程项目，当前主题为“开放食品数据库中的营养结构、价格关系与标签数据质量可视分析”。项目目前已经完成数据筛选、预处理、价格对齐和分析主表构建，后续工作重点是围绕现有分析表完成聚合数据设计、前端可视化与案例分析。

## 当前进度

- 已完成中期文档撰写，见 [docs/中期文档.md](docs/中期文档.md) 和 [docs/中期文档.pdf](docs/中期文档.pdf)。
- 已完成原始数据集审计，确认 `product-database` 和 `open-prices` 的字段覆盖与可用性，结果见 [reports/dataset_audit.md](reports/dataset_audit.md)。
- 已完成 `product-database` 的筛选口径评估，最终采用 `full_nutrient_detail_ready + Top 10 国家 + Top 10 品类` 作为主筛选方案，结果见 [reports/product_filter_audit.md](reports/product_filter_audit.md)。
- 已完成主产品表预处理，生成 [datasets_preprocessed/products_main.parquet](datasets_preprocessed/products_main.parquet)。
- 已完成 `open-prices` 与主产品表的重新对齐评估，生成 [datasets_preprocessed/prices_aligned.parquet](datasets_preprocessed/prices_aligned.parquet) 和 [datasets_preprocessed/price_summary_by_product.parquet](datasets_preprocessed/price_summary_by_product.parquet)，结果见 [reports/open_prices_aligned_audit.md](reports/open_prices_aligned_audit.md)。
- 已完成分析主表构建，生成 [datasets_preprocessed/products_analysis.parquet](datasets_preprocessed/products_analysis.parquet) 以及 CSV 版本 [datasets_preprocessed/products_analysis.csv](datasets_preprocessed/products_analysis.csv)。
- 已完成分析主表字段说明，见 [docs/分析主表说明.md](docs/分析主表说明.md)。
- 已完成派生指标的初步设计方案，包括健康评分、数据完整度评分、价格-营养性价比和同类异常程度，见 [reports/derived_metric_design.md](reports/derived_metric_design.md)。

## 当前数据产物

### 原始数据

- `datasets_raw/product-database/food.parquet`
- `datasets_raw/product-database/beauty.parquet`
- `datasets_raw/open-prices/prices.parquet`

### 预处理结果

- `datasets_preprocessed/products_main.parquet`
  说明：按筛选口径提取出的主产品表，包含国家、品类、品牌、营养和数据质量核心字段。

- `datasets_preprocessed/prices_aligned.parquet`
  说明：与主产品表按条码对齐后的价格记录表。

- `datasets_preprocessed/price_summary_by_product.parquet`
  说明：按产品聚合后的价格摘要表。

- `datasets_preprocessed/products_analysis.parquet`
  说明：按产品一行的分析主表，已合并核心营养、数据质量、价格主摘要和派生指标。

- `datasets_preprocessed/products_analysis.csv`
  说明：分析主表的 CSV 导出版，便于快速检查和外部工具读取。

## 项目环境配置

### Python 环境

- 推荐使用 Conda 环境：`foodatlas`
- 当前开发环境 Python 版本：`3.10`

创建环境后可执行：

```bash
conda activate foodatlas
pip install -r requirements.txt
```

### 依赖

当前 `requirements.txt` 中的主要依赖：

- `polars`
- `pyarrow`
- `modelscope`

其中：

- `polars` 用于大规模 Parquet 数据的懒加载、审计和预处理。
- `pyarrow` 用于 Parquet 读写支持。
- `modelscope` 用于下载 Hugging Face / ModelScope 数据集镜像。

## 目录结构

```text
FoodAtlas/
├── datasets_raw/                 # 原始数据集
├── datasets_preprocessed/        # 预处理后的主数据
├── docs/                         # 中期文档与数据说明文档
├── reports/                      # 数据审计与预处理报告
├── scripts/                      # 数据下载、审计、预处理脚本
├── requirements.txt
└── README.md
```

## 主要脚本

- `scripts/download_dataset.py`
  作用：下载 Open Food Facts 数据集到 `datasets_raw/`。

- `scripts/audit_datasets.py`
  作用：审计原始数据集字段覆盖、价格对齐和整体可用性。

- `scripts/audit_product_filters.py`
  作用：评估不同产品筛选口径下的样本规模与价格匹配规模。

- `scripts/preprocess_foodatlas.py`
  作用：生成主产品表、对齐价格表和价格摘要表。

- `scripts/build_analysis_table.py`
  作用：基于预处理结果构建按产品一行的分析主表。

- `scripts/parquet_to_csv.py`
  作用：将 Parquet 导出为 CSV，当前用于导出 `products_analysis.parquet`。

## 常用命令

### 1. 重新审计原始数据

```bash
conda activate foodatlas
python scripts/audit_datasets.py
```

### 2. 重新评估产品筛选口径

```bash
conda activate foodatlas
python scripts/audit_product_filters.py
```

### 3. 重新生成预处理数据

```bash
conda activate foodatlas
python scripts/preprocess_foodatlas.py
```

### 4. 重新生成分析主表

```bash
conda activate foodatlas
python scripts/build_analysis_table.py
```

## 下一步计划

- 基于 `products_analysis.parquet` 设计国家级、品类级和品牌级聚合表。
- 根据中期文档中的视图设计，为地图、营养结构视图、异常散点图和价格关系视图准备直接可用的数据接口。
- 围绕主要国家和主要品类补充案例分析，验证派生指标是否符合预期。
