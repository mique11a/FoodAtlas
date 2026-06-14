# FoodAtlas 前端文档

生成时间：2026-06-14

## 技术选型

| 项 | 选择 | 理由 |
|---|---|---|
| 图表库 | ECharts 5.5（CDN） | 内置地图、旭日图、散点图、平行坐标，中文文档完善 |
| 架构 | 纯静态 HTML + JS | 原型阶段零构建工具，一个文件即开即用 |
| 地图数据 | 本地 `frontend/data/world.json` | 避免 CDN 网络问题，文件约 1MB |
| 本地运行 | `python -m http.server 8080` | 浏览器 `file://` 协议会拦截 fetch 请求 |

## 文件结构

```
frontend/
├── index.html          # 主页面（单文件包含 CSS + JS）
└── data/
    └── world.json      # 世界地图 GeoJSON（Apache ECharts 官方源）
```

## 五个视图详情

### ① 全球食品样本概览地图

- **图表类型**：地图热力图（`geo` + `map` series）
- **数据**：10 个目标国家的聚合指标（mock）
- **视觉编码**：颜色 = 顶部指标选择器选中的指标值（暖色渐变）
- **交互**：
  - 点击国家 → 地图聚焦放大到该国，其他国家淡化，该国英文名加粗显示
  - 地图右上出现「返回世界」按钮
  - 下方视图 ②③④ 同步过滤到该国
- **关键实现**：`mapZoomedTo` 变量控制聚焦状态；未选中国家设 `value: -1` + `outOfRange` 颜色实现淡化

### ② 品类营养结构视图

- **图表类型**：旭日图（`sunburst`）
- **数据**：8 个品类的样本数 + 6 项指标均值（sugars/salt/fat/energy/nutriscore/nova/health）
- **视觉编码**：
  - 弧长（扇区大小）= 该品类样本数
  - 颜色 = 顶部指标值从浅暖到深暖（RGB 插值，非 visualMap，无渐变过渡）
- **交互**：
  - 点击品类 → 散点图 ③④ 过滤到该品类
  - 选中后扇区占满圆盘，文字放正 + 放大（22px）
  - 再点击同一品类 → 取消选中
- **已知限制**：颜色切换无渐变（旭日图不支持 `visualMap`，颜色写死在 `itemStyle` 中）

### ③ 产品异常检测散点图

- **图表类型**：散点图，按品类分系列（`series: [...8个]`）
- **数据**：50 个 mock 产品（模拟 `products_analysis.parquet` 行）
- **视觉编码**：
  - X/Y 轴 = 下拉框选择的变量（糖/盐/脂肪/健康评分/能量/Nutri-Score/NOVA/完整度/异常度/价格）
  - 颜色 = 品类（8 色固定调色板）
  - 大小 = 异常度 `peer_anomaly_score`
- **交互**：
  - 横纵轴下拉框切换 → 动态重建 `value: [xVal, yVal]` 重绘
  - 框选离群区域（ECharts brush 工具）→ 标记候选异常
  - 点击/框选点 → ⑤ 详情面板从点击位置圆形扩散弹出
- **关键实现**：`CATEGORIES.map(cat => series)` 每个品类一个系列，支持图例筛选

### ④ 价格-营养关系视图

- **图表类型**：散点图
- **数据**：有价格的 mock 产品
- **视觉编码**：
  - X = 中位价格（€）
  - Y = 健康评分（当前固定，待接入纵轴切换）
  - 颜色 = 健康评分（绿/橙/红）
- **交互**：点击点 → ⑤ 详情面板弹出
- **待完善**：纵轴指标切换、币种筛选

### ⑤ 产品详情解释视图

- **展示内容**：产品名称、国家、品类、Nutri-Score、NOVA、糖/盐/脂肪/健康评分/异常度/价格/数据完整度 + 异常标记
- **动画**：CSS `clip-path: circle()` 从点击位置扩散 / 收缩，0.35s
- **关闭**：点击 ✕ 按钮或重置
- **待完善**：同类分位数对比条（需要后端查询）

## 全局状态管理

| 变量 | 类型 | 作用 |
|---|---|---|
| `selectedCountry` | string | 当前选中的国家（英文名），空 = 全部 |
| `selectedCategory` | string | 当前选中的品类（英文名），空 = 全部 |
| `currentMetric` | string | 顶部指标选择器值，影响 ①② 的颜色 |
| `mapZoomedTo` | string\|null | 地图聚焦的国家，null = 世界视图 |
| `lastClickPos` | {x, y} | ⑤ 弹出的动画原点（相对面板的百分比）|

### 刷新触发链

```
refreshAll()
  ├── renderMap(currentMetric)    # ①
  ├── renderSunburst()            # ②
  ├── renderAnomaly()             # ③
  └── renderPrice()               # ④

指标切换 → renderMap() + renderSunburst()
散点轴切换 → renderAnomaly() only
重置 → 清空所有状态 → refreshAll()
```

## 数据对接（待实现）

当前所有数据为 JavaScript 硬编码 mock。后端完成后替换方式：

```javascript
// 当前（mock）
const data = scatterData;

// 未来（真实 API）
const data = await fetch(`/api/products?country=${selectedCountry}&category=${selectedCategory}`)
  .then(r => r.json());
```

后端只需提供约 3-4 个接口：

| 接口 | 参数 | 返回 | 用途 |
|---|---|---|---|
| `/api/countries` | metric | 国家聚合表 | ① 地图 |
| `/api/categories` | metric | 品类聚合表 | ② 旭日图 |
| `/api/products/scatter` | country, category | 产品行列表 | ③④ 散点 |
| `/api/products/:id` | - | 单品全字段 + 分位数 | ⑤ 详情 |

## 运行方式

```bash
cd frontend
python -m http.server 8080
# 浏览器打开 http://localhost:8080
```

无需安装依赖，ECharts 从 CDN 加载，地图从本地文件加载。
