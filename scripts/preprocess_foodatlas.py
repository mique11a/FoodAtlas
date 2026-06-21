#!/usr/bin/env python3
"""Preprocess FoodAtlas product and price data for downstream analysis."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl


RAW_PRODUCT_PATH = Path("datasets_raw/product-database/food.parquet")
RAW_PRICE_PATH = Path("datasets_raw/open-prices/prices.parquet")
OUT_DIR = Path("datasets_preprocessed")
REPORT_DIR = Path("reports")

PRODUCTS_OUT = OUT_DIR / "products_main.parquet"
PRICES_OUT = OUT_DIR / "prices_aligned.parquet"
PRICE_SUMMARY_OUT = OUT_DIR / "price_summary_by_product.parquet"
PREPROCESS_REPORT_JSON = REPORT_DIR / "preprocessing_summary.json"
PREPROCESS_REPORT_MD = REPORT_DIR / "preprocessing_summary.md"
PRICE_REPORT_JSON = REPORT_DIR / "open_prices_aligned_audit.json"
PRICE_REPORT_MD = REPORT_DIR / "open_prices_aligned_audit.md"
METRIC_PLAN_MD = REPORT_DIR / "derived_metric_design.md"


COUNTRY_TAG_TO_CODE = {
    "en:france": "FR",
    "en:united-states": "US",
    "en:germany": "DE",
    "en:spain": "ES",
    "en:united-kingdom": "GB",
    "en:italy": "IT",
    "en:switzerland": "CH",
    "en:belgium": "BE",
    "en:netherlands": "NL",
    "en:canada": "CA",
    "en:poland": "PL",
}

ANALYSIS_CATEGORY_PRIORITY = [
    "en:sugary-snacks",
    "en:appetizers",
    "en:salty-snacks",
    "en:beverages",
    "en:cereals-and-potatoes",
    "en:milk-and-dairy-products",
    "en:fish-meat-eggs",
    "en:fruits-and-vegetables",
    "en:fats-and-sauces",
    "en:composite-foods",
]


def has_list(col: str) -> pl.Expr:
    return pl.col(col).is_not_null() & (pl.col(col).list.len() > 0)


def has_present(col: str, schema: pl.Schema) -> pl.Expr:
    dtype = schema[col]
    if isinstance(dtype, pl.List):
        return has_list(col)
    return pl.col(col).is_not_null()


def has_nutrient(name: str) -> pl.Expr:
    return (
        pl.col("nutriments")
        .list.eval(pl.element().struct.field("name") == name)
        .list.any()
        .fill_null(False)
    )


def nutrient_100g(name: str) -> pl.Expr:
    return (
        pl.col("nutriments")
        .list.eval(
            pl.when(pl.element().struct.field("name") == name)
            .then(pl.element().struct.field("100g"))
            .otherwise(None)
        )
        .list.drop_nulls()
        .list.first()
        .cast(pl.Float64)
    )


def first_matching_tag(col: str, allowed: list[str]) -> pl.Expr:
    return (
        pl.col(col)
        .list.eval(
            pl.when(pl.element().is_in(allowed)).then(pl.element()).otherwise(None)
        )
        .list.drop_nulls()
        .list.first()
    )


def last_matching_tag(col: str, allowed: list[str]) -> pl.Expr:
    return (
        pl.col(col)
        .list.eval(
            pl.when(pl.element().is_in(allowed)).then(pl.element()).otherwise(None)
        )
        .list.drop_nulls()
        .list.last()
    )


def first_priority_match(col: str, priority: list[str]) -> pl.Expr:
    return pl.coalesce(
        [
            pl.when(
                pl.col(col)
                .list.eval(pl.element() == tag)
                .list.any()
                .fill_null(False)
            )
            .then(pl.lit(tag))
            .otherwise(None)
            for tag in priority
        ]
    )


def first_struct_text(col: str) -> pl.Expr:
    return (
        pl.col(col)
        .list.eval(pl.element().struct.field("text"))
        .list.drop_nulls()
        .list.first()
    )


def first_tag(col: str) -> pl.Expr:
    return pl.col(col).list.drop_nulls().list.first()


def count_or_zero_list(col: str) -> pl.Expr:
    return pl.when(pl.col(col).is_not_null()).then(pl.col(col).list.len()).otherwise(0)


def pct(n: int, total: int) -> float:
    return round(n / total * 100, 2) if total else 0.0


def to_records(df: pl.DataFrame) -> list[dict[str, Any]]:
    return df.to_dicts()


def json_default(value: Any) -> Any:
    return str(value)


def product_filter_expr(schema: pl.Schema) -> pl.Expr:
    has_code = pl.col("code").is_not_null()
    has_name = has_present("product_name", schema)
    has_country = has_list("countries_tags")
    has_category = has_list("categories_tags")
    has_brand = has_present("brands", schema) | has_list("brands_tags")
    has_energy = (
        has_nutrient("energy-kcal")
        | has_nutrient("energy-kj")
        | has_nutrient("energy")
    )
    has_fat = has_nutrient("fat")
    has_satfat = has_nutrient("saturated-fat")
    has_carbs = has_nutrient("carbohydrates")
    has_sugars = has_nutrient("sugars")
    has_proteins = has_nutrient("proteins")
    has_salt = has_nutrient("salt") | has_nutrient("sodium")
    valid_nutriscore = pl.col("nutriscore_score").is_not_null() | pl.col(
        "nutriscore_grade"
    ).is_in(["a", "b", "c", "d", "e"])
    valid_nova = pl.col("nova_group").is_in([1, 2, 3, 4])
    quality_ready = pl.col("completeness").is_not_null() & pl.col(
        "data_quality_warnings_tags"
    ).is_not_null()
    high_complete = pl.col("completeness").fill_null(0) >= 0.5

    return (
        has_code
        & has_name
        & has_country
        & has_category
        & has_brand
        & has_energy
        & has_fat
        & has_satfat
        & has_carbs
        & has_sugars
        & has_proteins
        & has_salt
        & valid_nutriscore
        & valid_nova
        & quality_ready
        & high_complete
    )


def top_tags(product_lf: pl.LazyFrame, filter_expr: pl.Expr, col: str, limit: int, exclude: set[str] | None = None) -> list[str]:
    exclude = exclude or set()
    df = (
        product_lf.filter(filter_expr)
        .select(pl.col(col))
        .explode(col)
        .drop_nulls()
        .filter(~pl.col(col).is_in(list(exclude)))
        .group_by(col)
        .len()
        .sort("len", descending=True)
        .limit(limit)
        .collect()
    )
    return df[col].to_list()


def build_products(
    product_lf: pl.LazyFrame,
    allowed_countries: list[str],
    analysis_categories: list[str],
) -> pl.LazyFrame:
    schema = product_lf.collect_schema()
    base_filter = product_filter_expr(schema)
    final_filter = (
        base_filter
        & pl.col("countries_tags")
        .list.eval(pl.element().is_in(allowed_countries))
        .list.any()
        .fill_null(False)
        & pl.col("food_groups_tags")
        .list.eval(pl.element().is_in(analysis_categories))
        .list.any()
        .fill_null(False)
    )

    energy_kcal_raw = nutrient_100g("energy-kcal")
    energy_kj_raw = nutrient_100g("energy-kj")
    energy_generic = nutrient_100g("energy")

    products = (
        product_lf.filter(final_filter)
        .select(
            [
                pl.col("code"),
                first_struct_text("product_name").alias("product_name"),
                pl.col("brands"),
                pl.col("brands_tags"),
                first_tag("brands_tags").alias("primary_brand_tag"),
                pl.col("countries_tags"),
                pl.col("categories_tags"),
                pl.col("food_groups_tags"),
                first_matching_tag("countries_tags", allowed_countries).alias(
                    "analysis_country_tag"
                ),
                first_priority_match("food_groups_tags", analysis_categories).alias(
                    "analysis_category_tag"
                ),
                first_struct_text("ingredients_text").alias("ingredients_text"),
                pl.col("nutriscore_grade"),
                pl.col("nutriscore_score").cast(pl.Float64),
                pl.col("nova_group").cast(pl.Int32),
                pl.col("completeness").cast(pl.Float64),
                count_or_zero_list("labels_tags").cast(pl.Int32).alias("labels_count"),
                count_or_zero_list("data_quality_warnings_tags")
                .cast(pl.Int32)
                .alias("quality_warning_count"),
                count_or_zero_list("data_quality_errors_tags")
                .cast(pl.Int32)
                .alias("quality_error_count"),
                pl.when(has_list("ingredients_text"))
                .then(True)
                .otherwise(False)
                .alias("has_ingredients_text"),
                pl.when(has_list("labels_tags"))
                .then(True)
                .otherwise(False)
                .alias("has_labels_tags"),
                pl.col("scans_n").cast(pl.Int32),
                pl.col("unique_scans_n").cast(pl.Int32),
                energy_kcal_raw.alias("energy_kcal_100g_raw"),
                energy_kj_raw.alias("energy_kj_100g_raw"),
                energy_generic.alias("energy_generic_100g"),
                nutrient_100g("fat").alias("fat_100g"),
                nutrient_100g("saturated-fat").alias("saturated_fat_100g"),
                nutrient_100g("carbohydrates").alias("carbohydrates_100g"),
                nutrient_100g("sugars").alias("sugars_100g"),
                nutrient_100g("proteins").alias("proteins_100g"),
                nutrient_100g("salt").alias("salt_100g"),
                nutrient_100g("sodium").alias("sodium_100g"),
                nutrient_100g("fiber").alias("fiber_100g"),
            ]
        )
        .with_columns(
            [
                pl.when(pl.col("energy_kcal_100g_raw").is_not_null())
                .then(pl.col("energy_kcal_100g_raw"))
                .when(pl.col("energy_kj_100g_raw").is_not_null())
                .then(pl.col("energy_kj_100g_raw") / 4.184)
                .when(pl.col("energy_generic_100g").is_not_null())
                .then(pl.col("energy_generic_100g") / 4.184)
                .otherwise(None)
                .alias("energy_kcal_100g"),
                pl.when(pl.col("energy_kj_100g_raw").is_not_null())
                .then(pl.col("energy_kj_100g_raw"))
                .when(pl.col("energy_kcal_100g_raw").is_not_null())
                .then(pl.col("energy_kcal_100g_raw") * 4.184)
                .when(pl.col("energy_generic_100g").is_not_null())
                .then(pl.col("energy_generic_100g"))
                .otherwise(None)
                .alias("energy_kj_100g"),
                pl.col("analysis_country_tag")
                .replace_strict(COUNTRY_TAG_TO_CODE, default=None)
                .alias("analysis_country_code"),
            ]
        )
        .with_columns(
            [
                (
                    pl.lit(0)
                    + pl.when(pl.col("energy_kcal_100g").is_not_null()).then(1).otherwise(0)
                    + pl.when(pl.col("fat_100g").is_not_null()).then(1).otherwise(0)
                    + pl.when(pl.col("saturated_fat_100g").is_not_null()).then(1).otherwise(0)
                    + pl.when(pl.col("carbohydrates_100g").is_not_null()).then(1).otherwise(0)
                    + pl.when(pl.col("sugars_100g").is_not_null()).then(1).otherwise(0)
                    + pl.when(pl.col("proteins_100g").is_not_null()).then(1).otherwise(0)
                    + pl.when(
                        pl.col("salt_100g").is_not_null() | pl.col("sodium_100g").is_not_null()
                    )
                    .then(1)
                    .otherwise(0)
                    + pl.when(pl.col("fiber_100g").is_not_null()).then(1).otherwise(0)
                )
                .cast(pl.Int32)
                .alias("nutrition_fields_present_count"),
            ]
        )
        .drop(["energy_kcal_100g_raw", "energy_kj_100g_raw", "energy_generic_100g"])
        .unique(subset=["code"], keep="first")
    )
    return products


def build_aligned_prices(products_lf: pl.LazyFrame) -> tuple[pl.LazyFrame, pl.LazyFrame]:
    product_join_cols = [
        "code",
        "product_name",
        "analysis_country_tag",
        "analysis_country_code",
        "analysis_category_tag",
        "nutriscore_grade",
        "nutriscore_score",
        "nova_group",
        "completeness",
        "quality_warning_count",
        "quality_error_count",
        "energy_kcal_100g",
        "fat_100g",
        "saturated_fat_100g",
        "carbohydrates_100g",
        "sugars_100g",
        "proteins_100g",
        "salt_100g",
        "fiber_100g",
    ]
    prices = (
        pl.scan_parquet(RAW_PRICE_PATH)
        .filter(pl.col("product_code").is_not_null())
        .join(
            products_lf.select(product_join_cols),
            left_on="product_code",
            right_on="code",
            how="inner",
        )
        .with_columns(
            [
                pl.col("price").cast(pl.Float64).alias("price_value"),
                pl.col("price_without_discount").cast(pl.Float64).alias(
                    "price_without_discount_value"
                ),
                (pl.col("price").cast(pl.Float64) > 0).alias("positive_price"),
                (
                    pl.col("location_osm_address_country_code")
                    == pl.col("analysis_country_code")
                ).alias("same_market_as_analysis_country"),
            ]
        )
        .filter(pl.col("positive_price"))
        .select(
            [
                "id",
                "product_code",
                "product_name",
                "analysis_country_tag",
                "analysis_country_code",
                "analysis_category_tag",
                "location_osm_address_country_code",
                "location_osm_address_country",
                "location_osm_address_city",
                "currency",
                "price_value",
                "price_without_discount_value",
                "price_is_discounted",
                "date",
                "proof_type",
                "source",
                "same_market_as_analysis_country",
                "nutriscore_grade",
                "nutriscore_score",
                "nova_group",
                "completeness",
                "quality_warning_count",
                "quality_error_count",
                "energy_kcal_100g",
                "fat_100g",
                "saturated_fat_100g",
                "carbohydrates_100g",
                "sugars_100g",
                "proteins_100g",
                "salt_100g",
                "fiber_100g",
            ]
        )
    )

    price_summary = (
        prices.group_by(
            [
                "product_code",
                "analysis_country_tag",
                "analysis_country_code",
                "analysis_category_tag",
                "location_osm_address_country_code",
                "currency",
            ]
        )
        .agg(
            [
                pl.len().cast(pl.Int32).alias("price_record_count"),
                pl.col("price_value").min().alias("price_min"),
                pl.col("price_value").median().alias("price_median"),
                pl.col("price_value").mean().alias("price_mean"),
                pl.col("price_value").max().alias("price_max"),
                pl.col("same_market_as_analysis_country")
                .any()
                .alias("any_same_market_match"),
                pl.col("date").min().alias("first_price_date"),
                pl.col("date").max().alias("last_price_date"),
            ]
        )
    )
    return prices, price_summary


def write_markdown(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    product_lf = pl.scan_parquet(RAW_PRODUCT_PATH)
    schema = product_lf.collect_schema()
    filter_expr = product_filter_expr(schema)

    top_countries = top_tags(
        product_lf,
        filter_expr,
        "countries_tags",
        limit=10,
        exclude={"en:world"},
    )
    analysis_categories = ANALYSIS_CATEGORY_PRIORITY

    products_lf = build_products(product_lf, top_countries, analysis_categories)
    products_lf.sink_parquet(PRODUCTS_OUT)

    products = pl.scan_parquet(PRODUCTS_OUT)
    product_rows = products.select(pl.len().alias("n")).collect()["n"][0]
    total_rows = product_lf.select(pl.len().alias("n")).collect()["n"][0]

    prices_lf, price_summary_lf = build_aligned_prices(products)
    prices_lf.sink_parquet(PRICES_OUT)
    price_summary_lf.sink_parquet(PRICE_SUMMARY_OUT)

    prices = pl.scan_parquet(PRICES_OUT)
    price_summary = pl.scan_parquet(PRICE_SUMMARY_OUT)

    unique_products_with_price = (
        price_summary.select(pl.col("product_code").n_unique().alias("n")).collect()["n"][0]
    )
    aligned_price_rows = prices.select(pl.len().alias("n")).collect()["n"][0]
    same_market_rows = (
        prices.filter(pl.col("same_market_as_analysis_country"))
        .select(pl.len().alias("n"))
        .collect()["n"][0]
    )
    same_market_non_null_currency_rows = (
        prices.filter(
            pl.col("same_market_as_analysis_country") & pl.col("currency").is_not_null()
        )
        .select(pl.len().alias("n"))
        .collect()["n"][0]
    )
    unique_products_with_same_market_price = (
        prices.filter(
            pl.col("same_market_as_analysis_country") & pl.col("currency").is_not_null()
        )
        .select(pl.col("product_code").n_unique().alias("n"))
        .collect()["n"][0]
    )
    aligned_currencies = (
        prices.group_by("currency")
        .len()
        .sort("len", descending=True)
        .collect()
        .to_dicts()
    )
    aligned_price_countries = (
        prices.group_by("location_osm_address_country_code")
        .len()
        .sort("len", descending=True)
        .collect()
        .to_dicts()
    )
    aligned_product_countries = (
        products.group_by("analysis_country_tag")
        .len()
        .sort("len", descending=True)
        .collect()
        .to_dicts()
    )
    aligned_categories = (
        products.group_by("analysis_category_tag")
        .len()
        .sort("len", descending=True)
        .collect()
        .to_dicts()
    )

    preprocessing_summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "input_product_path": str(RAW_PRODUCT_PATH),
        "input_price_path": str(RAW_PRICE_PATH),
        "output_products_path": str(PRODUCTS_OUT),
        "output_prices_path": str(PRICES_OUT),
        "output_price_summary_path": str(PRICE_SUMMARY_OUT),
        "selected_top_countries": top_countries,
        "selected_analysis_categories": analysis_categories,
        "total_raw_product_rows": int(total_rows),
        "preprocessed_product_rows": int(product_rows),
        "preprocessed_product_pct_total": pct(int(product_rows), int(total_rows)),
        "products_with_price": int(unique_products_with_price),
        "products_with_price_pct": pct(int(unique_products_with_price), int(product_rows)),
    }
    PREPROCESS_REPORT_JSON.write_text(
        json.dumps(preprocessing_summary, ensure_ascii=False, indent=2, default=json_default),
        encoding="utf-8",
    )

    preprocess_lines = [
        "# Preprocessing Summary",
        "",
        f"Generated at: `{preprocessing_summary['generated_at']}`",
        "",
        f"- Raw product rows: **{int(total_rows):,}**",
        f"- Preprocessed product rows: **{int(product_rows):,}**",
        f"- Share of raw products: **{preprocessing_summary['preprocessed_product_pct_total']:.2f}%**",
        f"- Products with at least one aligned price record: **{int(unique_products_with_price):,}**",
        f"- Share of preprocessed products with prices: **{preprocessing_summary['products_with_price_pct']:.2f}%**",
        "",
        "## Selected Top Countries",
        "",
        "| Country tag | Rows |",
        "|---|---:|",
    ]
    country_counts = {row["analysis_country_tag"]: row["len"] for row in aligned_product_countries}
    for tag in top_countries:
        preprocess_lines.append(f"| `{tag}` | {country_counts.get(tag, 0):,} |")
    preprocess_lines.extend(["", "## Selected Analysis Categories", "", "| Category tag | Rows |", "|---|---:|"])
    category_counts = {row["analysis_category_tag"]: row["len"] for row in aligned_categories}
    for tag in analysis_categories:
        preprocess_lines.append(f"| `{tag}` | {category_counts.get(tag, 0):,} |")
    write_markdown(PREPROCESS_REPORT_MD, preprocess_lines)

    price_report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "aligned_price_rows": int(aligned_price_rows),
        "unique_products_with_price": int(unique_products_with_price),
        "products_with_price_pct": pct(int(unique_products_with_price), int(product_rows)),
        "same_market_rows": int(same_market_rows),
        "same_market_rows_pct": pct(int(same_market_rows), int(aligned_price_rows)),
        "same_market_non_null_currency_rows": int(same_market_non_null_currency_rows),
        "same_market_non_null_currency_rows_pct": pct(
            int(same_market_non_null_currency_rows), int(aligned_price_rows)
        ),
        "unique_products_with_same_market_price": int(
            unique_products_with_same_market_price
        ),
        "unique_products_with_same_market_price_pct": pct(
            int(unique_products_with_same_market_price), int(product_rows)
        ),
        "aligned_currencies": aligned_currencies,
        "aligned_price_countries": aligned_price_countries,
        "price_summary_rows": int(
            price_summary.select(pl.len().alias("n")).collect()["n"][0]
        ),
        "median_price_by_currency": to_records(
            prices.group_by("currency")
            .agg(
                [
                    pl.len().alias("rows"),
                    pl.col("price_value").median().alias("median_price"),
                    pl.col("price_value").mean().alias("mean_price"),
                ]
            )
            .sort("rows", descending=True)
            .collect()
        ),
    }
    PRICE_REPORT_JSON.write_text(
        json.dumps(price_report, ensure_ascii=False, indent=2, default=json_default),
        encoding="utf-8",
    )

    price_lines = [
        "# Open Prices Aligned Audit",
        "",
        f"Generated at: `{price_report['generated_at']}`",
        "",
        f"- Aligned price rows: **{int(aligned_price_rows):,}**",
        f"- Unique preprocessed products with price records: **{int(unique_products_with_price):,}**",
        f"- Share of preprocessed products with prices: **{price_report['products_with_price_pct']:.2f}%**",
        f"- Same-market rows: **{int(same_market_rows):,}**",
        f"- Same-market row share: **{price_report['same_market_rows_pct']:.2f}%**",
        f"- Same-market rows with non-null currency: **{int(same_market_non_null_currency_rows):,}**",
        f"- Same-market usable row share: **{price_report['same_market_non_null_currency_rows_pct']:.2f}%**",
        f"- Unique products with same-market usable prices: **{int(unique_products_with_same_market_price):,}**",
        f"- Share of preprocessed products with same-market usable prices: **{price_report['unique_products_with_same_market_price_pct']:.2f}%**",
        f"- Aggregated product/currency/country price groups: **{price_report['price_summary_rows']:,}**",
        "",
        "## Top Currencies",
        "",
        "| Currency | Rows | Median price | Mean price |",
        "|---|---:|---:|---:|",
    ]
    for row in price_report["median_price_by_currency"][:12]:
        price_lines.append(
            f"| `{row['currency']}` | {row['rows']:,} | {row['median_price']:.3f} | {row['mean_price']:.3f} |"
        )
    price_lines.extend(["", "## Top Price Location Countries", "", "| Country code | Rows |", "|---|---:|"])
    for row in aligned_price_countries[:12]:
        price_lines.append(
            f"| `{row['location_osm_address_country_code']}` | {row['len']:,} |"
        )
    write_markdown(PRICE_REPORT_MD, price_lines)

    metric_lines = [
        "# Derived Metric Design",
        "",
        "## Metric Scope",
        "",
        "The preprocessed product table is suitable for global nutrition structure, peer comparison, and anomaly detection.",
        "The aligned price tables are suitable for country- and currency-specific price analysis, not global pooled price comparisons.",
        "",
        "## Proposed Derived Metrics",
        "",
        "### 1. Health Score Composite",
        "",
        "Use existing `nutriscore_score` and `nova_group` as anchors, then add nutrient-position penalties within peer groups.",
        "Recommended peer group: `analysis_country_tag + analysis_category_tag`.",
        "Suggested formulation:",
        "`health_score_composite = 0.45 * nutriscore_percentile_good + 0.25 * (1 - nova_scaled) + 0.15 * (1 - sugars_percentile) + 0.10 * (1 - salt_percentile) + 0.05 * proteins_percentile`.",
        "Interpretation: higher is healthier.",
        "",
        "### 2. Data Completeness Score",
        "",
        "This should measure how analysis-ready a product row is, not label transparency.",
        "Suggested formulation:",
        "`data_completeness_score = 0.50 * completeness + 0.15 * nutrient_field_fill_rate + 0.10 * has_ingredients_text + 0.05 * has_labels_tags - 0.12 * warning_penalty - 0.08 * error_penalty`.",
        "Where `nutrient_field_fill_rate = nutrition_fields_present_count / 8` and warning/error penalties are capped transforms of `quality_warning_count` and `quality_error_count`.",
        "",
        "### 3. Price-Nutrition Value Index",
        "",
        "Compute only within `location_osm_address_country_code + currency + analysis_category_tag`.",
        "Use aggregated price medians from `price_summary_by_product`.",
        "Suggested formulation:",
        "`value_index = health_score_composite_percentile - price_median_percentile`.",
        "Interpretation: higher means healthier than peers at a lower relative price.",
        "",
        "### 4. Peer Anomaly Score",
        "",
        "Use robust z-scores within `analysis_country_tag + analysis_category_tag` for `price_median`, `sugars_100g`, `salt_100g`, `saturated_fat_100g`, `nutriscore_score`, `nova_group`, and `data_completeness_score`.",
        "Suggested formulation:",
        "`peer_anomaly_score = weighted_sum(abs(robust_z_i))`.",
        "For directional anomalies, keep separate flags such as `high_price_low_health`, `high_sugar_high_nova`, and `low_completeness_many_warnings`.",
        "",
        "### 5. Brand Concentration Indicators",
        "",
        "At the country/category level, compute brand share, top-brand share, and Herfindahl-style concentration to identify markets dominated by a few brands.",
        "",
        "## Implementation Order",
        "",
        "1. Build peer-group percentiles on the preprocessed product table.",
        "2. Aggregate aligned prices to product/currency/country medians.",
        "3. Compute health and completeness scores.",
        "4. Join price medians back to products where available.",
        "5. Compute value index and anomaly score.",
    ]
    write_markdown(METRIC_PLAN_MD, metric_lines)

    print(f"Wrote {PRODUCTS_OUT}")
    print(f"Wrote {PRICES_OUT}")
    print(f"Wrote {PRICE_SUMMARY_OUT}")
    print(f"Wrote {PREPROCESS_REPORT_MD}")
    print(f"Wrote {PRICE_REPORT_MD}")
    print(f"Wrote {METRIC_PLAN_MD}")


if __name__ == "__main__":
    main()
