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

## 前端原型

已完成基于 ECharts 的 9-Panel 前端原型，见 [frontend/index.html](frontend/index.html)。组长初审稿见 [prototype_9panel_mock.html](prototype_9panel_mock.html)。

### 技术选型

- **ECharts 5.5**（CDN 引入），纯前端无构建工具
- **世界地图 GeoJSON** 本地托管 [frontend/data/world.json](frontend/data/world.json)
- 暖色纸质感 CSS（CSS 变量体系，适配 1360px / 900px 响应式断点）
- 本地开发：`cd frontend && python -m http.server 8080`，浏览器访问 `http://localhost:8080`

### 九个面板总览

| # | 面板 | 图表类型 | 数据粒度 | 核心交互 |
|---|---|---|---|---|
| 1 | **全局控制台** | 筛选器 + KPI 卡片 | — | 国家/品类/品牌/主指标/异常阈值/完整度阈值/价格区间/币种 八个筛选控件；5 个 KPI 悬停显示指标含义，实时随筛选更新；均价与币种联动，全部币种时显示—；保存筛选 + 切换对比 + 重置视图 三按钮居中于面板底部 |
| 2 | **全球地图总览** | 地图热力图 | 10 国聚合 | 点击国家聚焦放大并写入全局筛选；再次点击已选国家取消筛选恢复全球视图；选中国高亮加粗，其他国家淡化；悬停显示国家名/健康分/均价/样本量；roam关闭保持稳定布局；右侧产品详情按钮仅控制抽屉 |
| 3 | **产品异常检测散点图** | 散点图（按品类分色） | 500 mock 产品 | 横/纵轴下拉自由切换变量（糖/盐/脂肪/健康/Nutri-Score/NOVA/能量/完整度/价格/异常度）；点大小=异常度；框选/点击触发详情 |
| 4 | **品类营养结构视图** | 旭日图 | 10 品类聚合 | 颜色随主指标动态 RGB 插值；点击品类筛选散点与表格；选中后文字放正放大 |
| 5 | **营养结构平行坐标图** | 平行坐标 | 产品级（前 48 条） | 轴=糖/盐/脂肪/能量/健康/价格/异常/完整度；品类着色；随筛选联动 |
| 6 | **国家×品类矩阵热力图** | 热力图 | 10×10 矩阵 | 颜色=价格-营养性价比指数；暖色渐变 |
| 7 | **价格分布箱线图** | 箱线图 | 国家×品类 | 展示各国家在选中品类下的价格五数概括（min-Q1-median-Q3-max） |
| 8 | **产品列表与对比表** | 表格 | 产品级 Top N | 按异常/价格/健康/完整度排序（点击 chip 切换+升降序）；Top N 下拉可选 12/24/50/全部；点击行→详情；随所有筛选联动 |
| 9 | **单产品解释** | 浮动详情卡片 | 单品 | `position: fixed` 跟随滚动；分类指标+条状基准图+解释摘要；由散点框选/点击/表格行点击触发 |

### 联动逻辑

```
Panel 1 筛选控件（国家/品类/品牌/指标/阈值/价格区间/币种）
  → Panel 2 地图重绘 + Panel 3 散点过滤 + Panel 4 旭日图重着色
  → Panel 5 平行坐标过滤 + Panel 7 箱线图过滤
  → Panel 8 表格过滤重排 + KPI 实时更新

Panel 2 地图点击国家 → 聚焦放大 + 全部视图过滤（等价于 Panel 1 选择国家）
Panel 4 旭日图点击品类 → 散点/平行坐标/箱线图/表格过滤（等价于 Panel 1 选择品类）
Panel 3 / Panel 8 选中产品 → Panel 9 浮动详情面板滑出
```

### 全局状态

| 变量 | 作用 |
|---|---|
| `selectedCountry` / `selectedCategory` | 当前筛选的国家/品类 |
| `currentMetric` | 主指标（影响 Panel 2 热力色 + Panel 4 扇区色） |
| `mapZoomedTo` | 地图聚焦国家（null=世界视图） |
| `selectedBrand` / `anomalyThreshold` / `completenessThreshold` / `priceRange, selectedCurrency` | Panel 1 精细筛选 |
| `tableSortField` / `tableSortDir` / `tableTopN` | Panel 8 排序与行数 |

所有筛选条件通过 `filterProducts()` 统一函数作用到各视图数据源。

详细设计文档见 [docs/frontend.md](docs/frontend.md)。

## 下一步计划

- 基于 `products_analysis.parquet` 设计国家级、品类级和品牌级聚合表。
- 编写 Flask 后端，将前端 mock 数据替换为真实 parquet 查询结果。
- 围绕主要国家和主要品类补充案例分析，验证派生指标是否符合预期。
