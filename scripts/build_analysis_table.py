#!/usr/bin/env python3
"""Build a one-row-per-product analysis table for FoodAtlas."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import polars as pl


PRODUCTS_PATH = Path("datasets_preprocessed/products_main.parquet")
PRICE_SUMMARY_PATH = Path("datasets_preprocessed/price_summary_by_product.parquet")
OUT_PATH = Path("datasets_preprocessed/products_analysis.parquet")
DOC_PATH = Path("docs/分析主表说明.md")


GROUP_KEYS = ["analysis_country_tag", "analysis_category_tag"]


def safe_div(num: pl.Expr, den: pl.Expr) -> pl.Expr:
    return pl.when(den != 0).then(num / den).otherwise(None)


def percentile_rank(expr: pl.Expr) -> pl.Expr:
    return expr.rank("average") / pl.len()


def robust_z(expr: pl.Expr) -> pl.Expr:
    median = expr.median().over(GROUP_KEYS)
    mad = (expr - median).abs().median().over(GROUP_KEYS)
    return safe_div(expr - median, mad + pl.lit(1e-6))


def cap_unit(expr: pl.Expr) -> pl.Expr:
    return expr.clip(0.0, 1.0)


def main() -> None:
    products = pl.scan_parquet(PRODUCTS_PATH)
    price_summary = pl.scan_parquet(PRICE_SUMMARY_PATH)

    primary_price = (
        price_summary.with_columns(
            [
                (
                    pl.col("any_same_market_match").cast(pl.Int8) * 100000
                    + pl.col("price_record_count")
                ).alias("_priority_score")
            ]
        )
        .sort(
            ["product_code", "_priority_score", "price_record_count"],
            descending=[False, True, True],
        )
        .group_by("product_code")
        .first()
        .drop("_priority_score")
        .drop(
            [
                "analysis_country_tag",
                "analysis_country_code",
                "analysis_category_tag",
            ]
        )
    )

    base = (
        products.join(primary_price, left_on="code", right_on="product_code", how="left")
        .with_columns(
            [
                (pl.col("nutrition_fields_present_count") / pl.lit(8.0)).alias(
                    "nutrient_field_fill_rate"
                ),
                (pl.col("price_record_count").fill_null(0) > 0).alias("has_price"),
                pl.col("price_record_count").fill_null(0).cast(pl.Int32),
                pl.col("any_same_market_match").fill_null(False),
                pl.when(pl.col("quality_warning_count") > 0)
                .then(True)
                .otherwise(False)
                .alias("has_quality_warning"),
                pl.when(pl.col("quality_error_count") > 0)
                .then(True)
                .otherwise(False)
                .alias("has_quality_error"),
                pl.when(pl.col("nutriscore_score").is_not_null())
                .then(-pl.col("nutriscore_score"))
                .otherwise(None)
                .alias("nutriscore_good_direction"),
                ((pl.col("nova_group") - 1) / 3.0).alias("nova_scaled"),
                pl.when(pl.col("salt_100g").is_not_null())
                .then(pl.col("salt_100g"))
                .otherwise(pl.col("sodium_100g") * 2.5)
                .alias("salt_equivalent_100g"),
                pl.when(pl.col("price_median").is_not_null() & (pl.col("price_median") > 0))
                .then(pl.col("price_median"))
                .otherwise(None)
                .alias("price_median_clean"),
            ]
        )
    )

    enriched = (
        base.with_columns(
            [
                percentile_rank(pl.col("nutriscore_good_direction")).over(GROUP_KEYS).alias(
                    "nutriscore_good_percentile"
                ),
                percentile_rank(-pl.col("nova_group")).over(GROUP_KEYS).alias(
                    "nova_good_percentile"
                ),
                percentile_rank(-pl.col("sugars_100g")).over(GROUP_KEYS).alias(
                    "sugars_good_percentile"
                ),
                percentile_rank(-pl.col("salt_equivalent_100g")).over(GROUP_KEYS).alias(
                    "salt_good_percentile"
                ),
                percentile_rank(pl.col("proteins_100g")).over(GROUP_KEYS).alias(
                    "proteins_good_percentile"
                ),
                percentile_rank(pl.col("price_median_clean")).over(
                    ["analysis_country_code", "currency", "analysis_category_tag"]
                ).alias("price_median_percentile"),
                percentile_rank(pl.col("sugars_100g")).over(GROUP_KEYS).alias(
                    "sugars_percentile"
                ),
                percentile_rank(pl.col("salt_equivalent_100g")).over(GROUP_KEYS).alias(
                    "salt_percentile"
                ),
                percentile_rank(pl.col("fat_100g")).over(GROUP_KEYS).alias("fat_percentile"),
                percentile_rank(pl.col("saturated_fat_100g")).over(GROUP_KEYS).alias(
                    "saturated_fat_percentile"
                ),
                percentile_rank(pl.col("energy_kcal_100g")).over(GROUP_KEYS).alias(
                    "energy_percentile"
                ),
                percentile_rank(pl.col("price_median_clean")).over(GROUP_KEYS).alias(
                    "price_percentile_within_peer"
                ),
            ]
        )
        .with_columns(
            [
                cap_unit(
                    0.45 * pl.col("nutriscore_good_percentile")
                    + 0.25 * pl.col("nova_good_percentile")
                    + 0.15 * pl.col("sugars_good_percentile")
                    + 0.10 * pl.col("salt_good_percentile")
                    + 0.05 * pl.col("proteins_good_percentile")
                ).alias("health_score_composite"),
                cap_unit(
                    0.50 * pl.col("completeness")
                    + 0.15 * pl.col("nutrient_field_fill_rate")
                    + 0.10 * pl.col("has_ingredients_text").cast(pl.Float64)
                    + 0.05 * pl.col("has_labels_tags").cast(pl.Float64)
                    - 0.12 * pl.col("quality_warning_count").clip(0, 5) / 5.0
                    - 0.08 * pl.col("quality_error_count").clip(0, 3) / 3.0
                ).alias("data_completeness_score"),
            ]
        )
        .with_columns(
            [
                percentile_rank(pl.col("health_score_composite")).over(GROUP_KEYS).alias(
                    "health_score_percentile"
                ),
                percentile_rank(pl.col("data_completeness_score")).over(GROUP_KEYS).alias(
                    "data_completeness_percentile"
                ),
            ]
        )
        .with_columns(
            [
                (pl.col("health_score_percentile") - pl.col("price_median_percentile")).alias(
                    "price_nutrition_value_index"
                ),
            ]
        )
        .with_columns(
            [
                robust_z(pl.col("price_median_clean")).over(GROUP_KEYS).alias(
                    "price_robust_z"
                ),
                robust_z(pl.col("sugars_100g")).over(GROUP_KEYS).alias("sugars_robust_z"),
                robust_z(pl.col("salt_equivalent_100g")).over(GROUP_KEYS).alias(
                    "salt_robust_z"
                ),
                robust_z(pl.col("saturated_fat_100g")).over(GROUP_KEYS).alias(
                    "saturated_fat_robust_z"
                ),
                robust_z(pl.col("nutriscore_score")).over(GROUP_KEYS).alias(
                    "nutriscore_robust_z"
                ),
                robust_z(pl.col("nova_group").cast(pl.Float64)).over(GROUP_KEYS).alias(
                    "nova_robust_z"
                ),
                robust_z(pl.col("data_completeness_score")).over(GROUP_KEYS).alias(
                    "data_completeness_robust_z"
                ),
            ]
        )
        .with_columns(
            [
                (
                    0.20 * pl.col("price_robust_z").abs().fill_null(0)
                    + 0.20 * pl.col("sugars_robust_z").abs().fill_null(0)
                    + 0.15 * pl.col("salt_robust_z").abs().fill_null(0)
                    + 0.15 * pl.col("saturated_fat_robust_z").abs().fill_null(0)
                    + 0.10 * pl.col("nutriscore_robust_z").abs().fill_null(0)
                    + 0.10 * pl.col("nova_robust_z").abs().fill_null(0)
                    + 0.10 * pl.col("data_completeness_robust_z").abs().fill_null(0)
                ).alias("peer_anomaly_score"),
            ]
        )
        .with_columns(
            [
                (
                    (pl.col("has_price"))
                    & (pl.col("price_median_percentile") > 0.75)
                    & (pl.col("health_score_percentile") < 0.25)
                ).alias("flag_high_price_low_health"),
                (
                    (pl.col("sugars_percentile") > 0.80)
                    & (pl.col("nova_group") >= 4)
                ).alias("flag_high_sugar_high_nova"),
                (
                    (pl.col("data_completeness_percentile") < 0.20)
                    & (pl.col("quality_warning_count") >= 2)
                ).alias("flag_low_completeness_many_warnings"),
            ]
        )
        .select(
            [
                "code",
                "product_name",
                "brands",
                "primary_brand_tag",
                "analysis_country_tag",
                "analysis_country_code",
                "analysis_category_tag",
                "nutriscore_grade",
                "nutriscore_score",
                "nova_group",
                "energy_kcal_100g",
                "energy_kj_100g",
                "fat_100g",
                "saturated_fat_100g",
                "carbohydrates_100g",
                "sugars_100g",
                "proteins_100g",
                "salt_100g",
                "salt_equivalent_100g",
                "fiber_100g",
                "completeness",
                "has_ingredients_text",
                "has_labels_tags",
                "labels_count",
                "quality_warning_count",
                "quality_error_count",
                "nutrition_fields_present_count",
                "nutrient_field_fill_rate",
                "data_completeness_score",
                "data_completeness_percentile",
                "scans_n",
                "unique_scans_n",
                "currency",
                "location_osm_address_country_code",
                "price_record_count",
                "price_min",
                "price_median",
                "price_mean",
                "price_max",
                "first_price_date",
                "last_price_date",
                "any_same_market_match",
                "has_price",
                "nutriscore_good_percentile",
                "nova_good_percentile",
                "sugars_good_percentile",
                "salt_good_percentile",
                "proteins_good_percentile",
                "sugars_percentile",
                "salt_percentile",
                "fat_percentile",
                "saturated_fat_percentile",
                "energy_percentile",
                "price_median_percentile",
                "price_percentile_within_peer",
                "health_score_composite",
                "health_score_percentile",
                "price_nutrition_value_index",
                "price_robust_z",
                "sugars_robust_z",
                "salt_robust_z",
                "saturated_fat_robust_z",
                "nutriscore_robust_z",
                "nova_robust_z",
                "data_completeness_robust_z",
                "peer_anomaly_score",
                "flag_high_price_low_health",
                "flag_high_sugar_high_nova",
                "flag_low_completeness_many_warnings",
            ]
        )
        .unique(subset=["code"], keep="first")
    )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    enriched.sink_parquet(OUT_PATH)

    write_doc()
    print(f"Wrote {OUT_PATH}")
    print(f"Wrote {DOC_PATH}")


def write_doc() -> None:
    lines = [
        "# FoodAtlas 分析主表说明",
        "",
        f"生成时间：`{datetime.now().isoformat(timespec='seconds')}`",
        "",
        "## 文件位置",
        "",
        f"- 分析主表：`{OUT_PATH}`",
        "",
        "## 设计目标",
        "",
        "该表以产品为主键，每行代表一个预处理后的食品样本，面向中期文档中确定的三类任务：",
        "- 营养结构与健康指标覆盖分析",
        "- 数据质量与产品异常检测",
        "- 价格-营养关系分析",
        "",
        "与 `products_main.parquet` 相比，该表补充了价格主摘要、同类分位数、健康评分、数据完整度评分、价格-营养性价比和异常分数，供后续前端和案例分析直接使用。",
        "",
        "## 字段分类",
        "",
        "### 1. 主键与基础识别字段",
        "",
        "- `code`：产品条码，也是主键。",
        "- `product_name`：产品名称。",
        "- `brands`：原始品牌字符串。",
        "- `primary_brand_tag`：用于统计和分组的主品牌标签。",
        "- `analysis_country_tag` / `analysis_country_code`：预处理后统一的国家标识。",
        "- `analysis_category_tag`：预处理后统一的分析品类。",
        "",
        "### 2. 原始营养字段",
        "",
        "- `nutriscore_grade` / `nutriscore_score`：Open Food Facts 的健康评分字段。",
        "- `nova_group`：食品加工程度等级。",
        "- `energy_kcal_100g` / `energy_kj_100g`：每 100g 或 100ml 能量。",
        "- `fat_100g`、`saturated_fat_100g`、`carbohydrates_100g`、`sugars_100g`、`proteins_100g`、`salt_100g`、`fiber_100g`：核心营养字段。",
        "- `salt_equivalent_100g`：统一盐口径字段，优先使用 `salt_100g`，缺失时由 `sodium_100g * 2.5` 转换。",
        "",
        "### 3. 数据质量字段",
        "",
        "- `completeness`：原始完整度评分。",
        "- `has_ingredients_text` / `has_labels_tags`：成分文本和标签字段是否存在。",
        "- `labels_count`：标签数量。",
        "- `quality_warning_count` / `quality_error_count`：质量警告和错误计数。",
        "- `nutrition_fields_present_count`：核心营养字段实际可用数。",
        "- `nutrient_field_fill_rate`：核心营养字段填充率，范围 0-1。",
        "",
        "### 4. 价格摘要字段",
        "",
        "- `currency`：主价格组的币种。",
        "- `location_osm_address_country_code`：主价格组的记录国家。",
        "- `price_record_count`：该产品在主价格组中的价格记录数。",
        "- `price_min` / `price_median` / `price_mean` / `price_max`：主价格组的摘要价格。",
        "- `first_price_date` / `last_price_date`：该价格组时间范围。",
        "- `any_same_market_match`：该价格组是否与产品分析国家一致。",
        "- `has_price`：是否存在可用价格摘要。",
        "",
        "### 5. 同类分位数字段",
        "",
        "同类定义默认为 `analysis_country_tag + analysis_category_tag`，价格分位则使用 `analysis_country_code + currency + analysis_category_tag`。",
        "",
        "- `nutriscore_good_percentile`：Nutri-Score 由差到好转换后的分位数，越大越健康。",
        "- `nova_good_percentile`：NOVA 越低越好的分位数。",
        "- `sugars_good_percentile` / `salt_good_percentile`：糖和盐由低到高转换后的健康分位数。",
        "- `proteins_good_percentile`：蛋白质由低到高的分位数。",
        "- `sugars_percentile`、`salt_percentile`、`fat_percentile`、`saturated_fat_percentile`、`energy_percentile`：原始方向分位数，用于异常解释。",
        "- `price_median_percentile`：在同国家、同币种、同品类中的价格分位数。",
        "- `price_percentile_within_peer`：在国家+品类 peer group 中的价格分位，用于异常散点图。",
        "- `data_completeness_percentile`：数据完整度分位数。",
        "- `health_score_percentile`：综合健康分在同类中的分位数。",
        "",
        "### 6. 派生评分字段",
        "",
        "- `health_score_composite`：综合健康评分，结合 Nutri-Score、NOVA、糖、盐、蛋白质的同类位置，范围约为 0-1，越高越健康。",
        "- `data_completeness_score`：分析可用性评分，结合完整度、营养字段填充率、成分文本、标签和质量警告，范围约为 0-1，越高越完整。",
        "- `price_nutrition_value_index`：价格-营养性价比指标，定义为健康分分位减价格分位，越高表示同类中相对更健康且更便宜。",
        "- `peer_anomaly_score`：同类异常程度综合分，基于价格、糖、盐、饱和脂肪、Nutri-Score、NOVA 和数据完整度的 robust z-score 绝对值加权求和。",
        "",
        "### 7. 异常标记字段",
        "",
        "- `flag_high_price_low_health`：价格分位高且健康分位低的样本。",
        "- `flag_high_sugar_high_nova`：高糖且高加工等级样本。",
        "- `flag_low_completeness_many_warnings`：完整度较低且质量警告较多样本。",
        "",
        "## 使用说明",
        "",
        "### 1. 全球样本概览地图",
        "",
        "- 直接按 `analysis_country_tag` 聚合。",
        "- 常用指标：`count(code)`、`avg(health_score_composite)`、`avg(data_completeness_score)`、`avg(nutriscore_score)`、`avg(nova_group)`。",
        "",
        "### 2. 主要国家地区营养结构视图",
        "",
        "- 按 `analysis_country_tag + analysis_category_tag` 或 `analysis_country_tag + primary_brand_tag` 聚合。",
        "- 常用指标：糖、盐、脂肪、能量、Nutri-Score、NOVA 的均值、中位数或分位数。",
        "",
        "### 3. 产品异常散点图",
        "",
        "- 每个点直接使用表中一行产品。",
        "- 推荐轴变量：`price_median`、`sugars_100g`、`salt_equivalent_100g`、`health_score_composite`、`data_completeness_score`、`peer_anomaly_score`。",
        "- 推荐编码：颜色=`analysis_category_tag` 或 `primary_brand_tag`，大小=`price_record_count` 或 `unique_scans_n`。",
        "",
        "### 4. 价格-营养关系视图",
        "",
        "- 仅过滤 `has_price = true` 且优先 `any_same_market_match = true`。",
        "- 同币种比较时按 `currency` 分面或筛选，避免直接混合不同币种。",
        "- 推荐使用 `price_median` 作为价格主变量。",
        "",
        "### 5. 产品详情解释视图",
        "",
        "- 直接展示该行原始字段与派生字段。",
        "- 详情中重点展示：营养原值、健康分、完整度分、价格分位、异常标记。",
        "",
        "## 使用限制",
        "",
        "- `price_*` 字段只代表主价格组，不代表产品所有市场价格。",
        "- 价格分析应优先限定在 `any_same_market_match = true` 的样本中。",
        "- `health_score_composite` 和 `peer_anomaly_score` 为探索性派生指标，不应解释为官方食品评级。",
        "- 该表未合并图像标注数据集；营养表/成分表抽取样例仍需单独从 `nutrient-detection-layout` 和 `ingredient-detection` 中展示。",
    ]
    DOC_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
