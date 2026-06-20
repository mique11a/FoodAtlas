# FoodAtlas

FoodAtlas 是一个基于 Open Food Facts 数据的课程项目，当前主题为“开放食品数据库中的营养结构、价格关系与标签数据质量可视分析”。项目目前已经完成数据筛选、预处理、价格对齐和分析主表构建，后续工作重点是围绕现有分析表完成聚合数据设计、前端可视化与案例分析。

## 当前进度

- 已完成中期文档撰写，见 [docs/中期文档.md](docs/中期文档.md) 和 [docs/中期文档.pdf](docs/中期文档.pdf)。
- 已完成原始数据集审计，确认 `product-database` 和 `open-prices` 的字段覆盖与可用性，结果见 [reports/dataset_audit.md](reports/dataset_audit.md)。
- 已完成 `product-database` 的筛选口径评估，当前采用 `full_nutrient_detail_ready + Top 10 国家 + 10 个互斥分析主类` 作为主筛选方案，结果见 [reports/product_filter_audit.md](reports/product_filter_audit.md)。
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

已完成基于 ECharts 的 9-Panel 前端实现，见 [frontend/index.html](frontend/index.html)。较早的 mock 原型见 [frontend/prototype_9panel_mock.html](frontend/prototype_9panel_mock.html)。

### 技术选型

- **ECharts 5.5**（CDN 引入），前端仍为单文件原型
- **Flask + Polars** 作为最小查询后端，直接读取 `datasets_preprocessed/products_analysis.parquet`
- **世界地图 GeoJSON** 本地托管 [frontend/data/world.json](frontend/data/world.json)
- 暖色纸质感 CSS（CSS 变量体系，适配 1360px / 900px 响应式断点）
- 本地开发：先执行 `conda activate foodatlas && python app.py` 启动后端，再访问 `http://127.0.0.1:8094`

### 九个面板总览

| # | 面板 | 图表类型 | 数据粒度 | 核心交互 |
|---|---|---|---|---|
| 1 | **全局控制台** | 筛选器 + KPI 卡片 | — | 国家/品类/品牌/主指标/异常阈值/完整度阈值/价格区间七个筛选控件；5 个 KPI 随筛选实时更新；保存筛选会把当前筛选与表格状态写入内存并给出“已保存”反馈；“产品对比”按钮会聚焦到 Panel 8 的对比区，并优先把当前选中产品加入对比；重置视图直接刷新前端页面并恢复初始状态 |
| 2 | **全球地图总览** | 地图热力图 | 10 国聚合 | 主指标支持健康、价格、糖、盐、脂肪、能量、Nutri-Score 和 NOVA；地图颜色与 tooltip 中的主指标/均价均基于当前筛选后的工作样本按国家动态重算；点击国家聚焦并写入全局国家筛选；再次点击或“返回世界”恢复全局视图；roam 关闭；右侧按钮仅控制产品解释抽屉 |
| 3 | **产品异常检测散点图** | 散点图（按品类分色） | 产品级真实样本 | X 轴可切换糖/盐/脂肪/健康/Nutri-Score/NOVA/能量/完整度，Y 轴在此基础上额外支持价格；点大小映射异常度；点击单点或框选结果可打开 Panel 9 详情 |
| 4 | **品类营养结构视图** | 旭日图 | 10 品类聚合 | 颜色随主指标动态 RGB 插值；当前 10 类使用互斥主类口径（如 Sugary snacks、Beverages、Milk & dairy 等），避免父子类同时并列；点击品类写入全局品类筛选并联动散点/排行图/箱线图/表格；选中后标签放正放大 |
| 5 | **同类定位排行图** | 排序散点图 | 当前 peer group Top 60 | 在当前国家/品类条件下，按价格、健康评分、Nutri-Score、NOVA、糖、盐、脂肪、能量、完整度或异常度对同类产品排序；中位线用于定位群体中部；若当前选中产品未落在默认前 60 中，会补入并高亮；同时受 Panel 3 图例保留品类约束；点击点可打开 Panel 9 详情 |
| 6 | **品牌定位气泡图** | 气泡散点图 | 品牌聚合 | 以品牌为粒度聚合产品；X 轴可切换健康、糖、盐、脂肪、能量、完整度、Nutri-Score、NOVA、异常度，Y 轴可切换以上全部指标并额外支持均价；气泡大小映射品牌覆盖品类数，颜色映射主导品类；仅展示主导品类仍在 Panel 3 图例中保留的品牌；点击气泡会写入品牌筛选并联动其它视图 |
| 7 | **价格分布箱线图** | 箱线图 | 国家×品类 | 展示各国家在当前品类下的价格五数概括（min-Q1-median-Q3-max）；支持本图独立品类下拉，默认跟随全局品类；点击箱体可反向选中国家 |
| 8 | **产品列表与对比表** | 表格 + 对比区 | 产品级 Top N | 支持按异常/价格/健康/完整度排序（点击 chip 切换字段与升降序）；其中健康排序为“健康评分优先，完整度与较低异常度辅助打破并列”；Top N 下拉可选 12/24/50/全部；支持按产品名或品牌名搜索；点击行打开详情；可勾选最多 3 个产品加入对比区并并列展示核心指标；支持清空对比 |
| 9 | **产品解释** | 悬浮抽屉详情卡 | 单品 / 最多 3 品并列 | `position: fixed` 悬浮抽屉；由散点点击/框选、排行图点击、表格行点击或对比卡点击触发；若对比区已有产品则优先展示最多 3 个选中产品，否则展示当前高亮产品；每个产品展示关键指标与同类分位条，底部共享一张同类分位雷达图，并附一条绿色中位基线 |

### 联动逻辑

```text
Panel 1 筛选控件（国家/品类/品牌/指标/阈值/价格区间）
  → Panel 2 地图重绘 + Panel 3 散点过滤 + Panel 4 旭日图重着色
  → Panel 5 同类定位排行图重绘 + Panel 6 品牌气泡图重新请求聚合
  → Panel 7 箱线图过滤 + Panel 8 表格过滤结果更新 + KPI 实时更新

Panel 2 地图点击国家 → 聚焦放大 + 全部视图过滤（等价于 Panel 1 选择国家）；地图热力值随当前国家/品类/品牌/阈值/搜索条件动态重算
Panel 3 图例显隐品类 → 保留或隐藏对应品类样本，并同步约束 Panel 5 同类排行与 Panel 6 品牌气泡图
Panel 4 旭日图点击品类 → 散点/排行图/箱线图/品牌图/表格过滤（等价于 Panel 1 选择品类）
Panel 5 指标切换 → 同一 peer group 下按不同指标重新排序；点击点 → 打开详情并高亮当前产品
Panel 6 品牌气泡图切换 X/Y 轴或最小样本阈值 → 重新请求品牌聚合；点击气泡 → 写入品牌筛选并联动散点图/排行图/箱线图/表格，同时将 Panel 6 重绘为该品牌集合
Panel 7 箱线图点击箱体 → 写入国家筛选并联动其他视图
Panel 8 勾选产品 → 加入对比区；点击表格行或对比卡 → Panel 9 悬浮详情抽屉滑出；清空对比后 Panel 9 回退到当前高亮产品
Panel 1 “产品对比”按钮 → 聚焦 Panel 8 对比区；若当前已有选中产品则自动补入对比
Panel 1 “重置视图”按钮 → 直接执行页面刷新
```

### 全局状态

| 变量 | 作用 |
|---|---|
| `selectedCountry` / `selectedCategory` | 当前筛选的国家/品类 |
| `currentMetric` | 主指标（影响 Panel 2 热力色 + Panel 4 扇区色） |
| `mapZoomedTo` | 地图聚焦国家（null=世界视图） |
| `selectedBrand` / `anomalyThreshold` / `completenessThreshold` / `priceRange` | Panel 1 精细筛选 |
| `anomalyLegendSelection` | Panel 3 图例保留的品类集合，同时影响 Panel 5 与 Panel 6 |
| `brandBubbleX` / `brandBubbleY` / `brandMinProducts` | Panel 6 品牌气泡图的轴变量与品牌最小样本阈值 |
| `savedFilters` | Panel 1 “保存筛选”暂存的当前筛选与表格状态快照 |
| `tableSortField` / `tableSortDir` / `tableTopN` / `tableSearchTerm` | Panel 8 排序、行数与搜索 |
| `comparedProductIds` / `selectedProductId` | Panel 8 对比区与 Panel 9 产品解释抽屉的多产品/当前高亮状态 |
| `peerMetricSelect` / `boxplotCategoryOverride` | Panel 5 当前定位指标与 Panel 7 独立品类选择 |

所有全局筛选条件通过 `filterProducts()` 统一函数作用到各视图数据源；其中 Panel 3 的图例显隐由 `anomalyLegendSelection` 额外控制，并继续影响 Panel 5 与 Panel 6 的可见数据。

补充说明：仓库中的 [docs/frontend.md](docs/frontend.md) 仍保留了一版较早的前端设计记录，其中部分视图描述已落后于当前实现。涉及当前页面结构、联动逻辑和指标口径时，以 [frontend/index.html](frontend/index.html) 与本 README 为准。

### 前端使用的派生指标与显示口径

这一节只记录**当前前端实际使用**的指标口径。完整字段说明见 [docs/分析主表说明.md](docs/分析主表说明.md)，真实计算逻辑以 [scripts/build_analysis_table.py](scripts/build_analysis_table.py) 为准。

#### `health`：前端“健康评分”

前端中的 `health` 直接对应后端主表字段 `health_score_composite`。它不是 Open Food Facts 的原生字段，也不是简单把 Nutri-Score 映射成数字。

计算分组：`analysis_country_tag + analysis_category_tag`

计算公式：

```text
health_score_composite =
  0.45 * nutriscore_good_percentile
+ 0.25 * nova_good_percentile
+ 0.15 * sugars_good_percentile
+ 0.10 * salt_good_percentile
+ 0.05 * proteins_good_percentile
```

然后整体截断到 `[0, 1]`。

相关中间量：

- `nutriscore_good_percentile`：对 `-nutriscore_score` 做分位排序，越大越健康
- `nova_good_percentile`：对 `-nova_group` 做分位排序，越大表示加工程度越低
- `sugars_good_percentile` / `salt_good_percentile`：对 `-sugars_100g`、`-salt_equivalent_100g` 做分位排序，越大越健康
- `proteins_good_percentile`：对 `proteins_100g` 做分位排序，越大表示蛋白质相对更高

解释：

- 这个分数更适合做**同类相对健康度**比较
- 它是探索性派生指标，不应解释为官方食品评级

#### `completeness`：前端“完整度”

前端中的 `completeness` 对应 `data_completeness_score`，表示该产品记录对分析的可用程度，而不是“标签透明度”。

计算公式：

```text
data_completeness_score =
  0.50 * completeness
+ 0.15 * nutrient_field_fill_rate
+ 0.10 * has_ingredients_text
+ 0.05 * has_labels_tags
- 0.12 * min(quality_warning_count, 5) / 5
- 0.08 * min(quality_error_count, 3) / 3
```

其中：

- `nutrient_field_fill_rate = nutrition_fields_present_count / 8`
- `has_ingredients_text` 和 `has_labels_tags` 在公式中按 `0/1` 使用

解释：

- 分数越高，说明这条记录越适合进入分析
- 它衡量的是“分析可用性”，不直接表示食品本身质量高低

#### `anomalyRaw`：后端原始异常值

前端产品对象中的 `anomalyRaw` 对应后端主表字段 `peer_anomaly_score`。

计算分组：`analysis_country_tag + analysis_category_tag`

后端先对以下字段分别计算 robust z-score：

- `price_median_clean`
- `sugars_100g`
- `salt_equivalent_100g`
- `saturated_fat_100g`
- `nutriscore_score`
- `nova_group`
- `data_completeness_score`

其中 robust z-score 的形式为：

```text
robust_z(x) = (x - median_group) / (MAD_group + 1e-6)
```

然后按绝对值加权求和：

```text
peer_anomaly_score =
  0.20 * |price_robust_z|
+ 0.20 * |sugars_robust_z|
+ 0.15 * |salt_robust_z|
+ 0.15 * |saturated_fat_robust_z|
+ 0.10 * |nutriscore_robust_z|
+ 0.10 * |nova_robust_z|
+ 0.10 * |data_completeness_robust_z|
```

解释：

- 它表示产品在同国家、同品类里的综合偏离程度
- 分数越高，说明越偏离群体主流
- 它是探索性指标，不等于“问题产品”的官方判断

#### 前端展示用 `anomaly`

前端并不直接把 `peer_anomaly_score` 原值画出来，而是先做可视化归一化，避免极端值压坏散点图。

处理步骤在 [frontend/index.html](frontend/index.html) 的 `normalizeAnomalyProducts()` 中：

1. 在当前前端工作样本中取 `anomalyRaw`
2. 用 `5% 分位` 作为下界 `floor`
3. 用 `98% 分位` 作为上界 `cap`
4. 对裁剪后的值做 `log1p` 压缩
5. 再线性映射到 `[0.4, 3.5]`

即：

```text
display_anomaly = map(log1p(clamp(anomalyRaw, q05, q98))) -> [0.4, 3.5]
```

因此：

- Panel 1 里的异常阈值筛选针对的是**前端展示异常值**
- Panel 3 散点图中看到的异常度也是这个显示口径
- 它保留排序关系和相对层次，但不再等于后端原始异常分
- 当前工作样本上限控制在约 `4000`：
  - 国家 + 品类同时选中时加载 `3200`
  - 仅选择其一时加载 `3600`
  - 全局视图加载 `4000`

#### 前端状态分类 `flag`

后端仍会返回原始 `flag` 字段，但当前前端显示时不再直接使用它作为列表状态标签。原因是原始 `peer_anomaly_score` 分布存在极端长尾，直接套后端阈值会导致“几乎全表都是异常或关注”。

当前前端使用 `displayFlag` 作为展示状态，分为 `high / warn / good`，逻辑在 [frontend/index.html](frontend/index.html) 的 `deriveDisplayFlag()` 中：

- `high`
  - `display_anomaly >= 3.0`
  - 或 `health < 0.30` 且 `completeness < 0.50`
  - 或 `Nutri-Score = E`
- `warn`
  - `display_anomaly >= 2.15`
  - 或 `health < 0.45`
  - 或 `completeness < 0.58`
  - 或 `Nutri-Score = D`
- `good`
  - 其余样本

界面文案上：

- `good` 显示为“健康”
- `warn` 显示为“关注”
- `high` 显示为“异常”

这个口径的目标不是替代后端异常检测，而是让产品列表、详情抽屉和 case study 中的状态标签更接近人可读、可比较的展示结果。

三个布尔标记由主表构建脚本生成：

- `flag_high_price_low_health`
  - `has_price = true`
  - `price_median_percentile > 0.75`
  - `health_score_percentile < 0.25`
- `flag_high_sugar_high_nova`
  - `sugars_percentile > 0.80`
  - `nova_group >= 4`
- `flag_low_completeness_many_warnings`
  - `data_completeness_percentile < 0.20`
  - `quality_warning_count >= 2`

#### 散点图与排行图中的点大小

Panel 3 散点图：

- 点大小使用前端展示异常值 `anomaly`
- 公式为：

```text
ratio = (anomaly - 0.4) / (3.5 - 0.4)
size = 6 + sqrt(clamp(ratio, 0, 1)) * 12
```

因此大点表示异常程度更高。

Panel 5 同类定位排行图：

- 点大小使用 `priceRecordCount`
- 公式为：

```text
size = min(14, 7 + log2(priceRecordCount + 1))
```

因此大点表示价格记录更多，价格摘要相对更稳定。

#### 产品列表中的“健康排序”

Panel 8 的健康排序不再只按 `health` 单字段生硬降序，而是使用前端组合排序值：

```text
table_health_sort_value =
  1000 * health
+ 120 * completeness
- 35 * display_anomaly
+ 8 * nutriscore_num
```

当排序值相同或接近时，再用：

1. 更高 `completeness`
2. 更低 `display_anomaly`
3. 产品名称字母序

依次打破并列。

这样做的目的，是避免“健康分很高，但同时数据很差或异常度很高”的产品长期挤在最前面。

#### 产品解释抽屉中的“同类分位”

Panel 9 中的价格分位、健康分位、Nutri-Score 分位、完整度分位和雷达图分位，当前并不是直接读取后端主表里的 percentile 字段，而是前端根据当前工作样本即时计算：

- 优先使用“同国家 + 同品类”产品作为 peers
- 若同国家 peers 不存在，则回退到“同品类”产品

因此：

- 它更适合交互解释和 case study
- 它表示的是当前前端工作样本中的相对位置，不是全量数据库的官方分位
- 若对比区同时选择了 2 到 3 个产品，则这些产品共享同一张雷达图；绿色虚线表示当前 peer group 的 50 分位基线

#### KPI、箱线图与品牌气泡图的口径说明

Panel 1 的 KPI、Panel 7 的箱线图以及 Panel 9 的分位解释，都是基于前端当前加载的 `PRODUCTS` 工作集实时计算的。

当前工作集由两个接口合并得到：

- `/api/products/anomaly`
- `/api/products/price`

因此：

- 这些视图足以支持探索性分析与 case study
- 但不应被误解为整张主表的严格全量统计

Panel 6 品牌定位气泡图基于后端接口 `/api/brands/bubbles`，直接读取 `products_analysis.parquet` 做品牌级聚合；前端再根据 Panel 3 当前保留的品类图例二次过滤，仅显示主导品类仍处于可见状态的品牌。默认聚合口径如下：

```text
group by = brand_tag + brand_name
```

聚合字段与规则：

```text
products = 品牌样本量
categories = 覆盖品类数
countries = 覆盖国家数
priced_products = 有欧元价格的产品数
priceCoverage = priced_products / products

health / completeness / nutriscore_num / nova / price = 均值
sugars / salt / fat / energy = 中位数
anomaly = 先对产品级 peer_anomaly_score 做展示压缩，再取品牌均值
```

阈值逻辑：

- 默认仅保留 `products >= 10`
- 若当前未选定品类，则要求 `categories >= 2`，避免只在单一小类中出现的弱代表性品牌挤占视图
- 若已选定品类，则放宽为 `categories >= 1`
- 只要 X 或 Y 使用 `price`，就额外要求 `priced_products >= 3`

品牌异常度说明：

- 后端原始 `peer_anomaly_score` 存在极端长尾，不适合直接做品牌平均后上屏
- 因此 Panel 6 的 `anomaly` 轴先参考前端产品散点图的思路，对产品级异常值做 `5%-98% 分位裁剪 + log1p 压缩 + [0.4, 3.5] 映射`
- 再对压缩后的产品级异常度做品牌均值

因此：

- 它适合做品牌层面的相对定位与 case study 入口
- 不应把其中的品牌异常度直接解释为统计学意义上的原始异常分

#### 品牌气泡图中的点大小

Panel 6 品牌定位气泡图：

- 点大小不再使用品牌样本量，而是使用品牌覆盖品类数 `categories`
- 公式为：

```text
size = 8 + max(0, categories - 1) * 3.2
```

因此：

- 大点表示这个品牌覆盖的分析主类更多
- 它更适合辅助判断品牌是否具有跨品类代表性，而不是单纯表示品牌样本多寡

## 下一步计划

- 继续校正后端异常值主表的稳健性，减少 `peer_anomaly_score` 极端长尾对派生分析的影响。
- 围绕主要国家和主要品类补充案例分析，验证派生指标是否符合预期。
