#!/usr/bin/env python3
"""Audit the local FoodAtlas datasets.

The script is intentionally based on Polars lazy scans so the 7GB product
database does not need to be loaded into memory at once.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import polars as pl


PRODUCT_REQUIRED = {
    "identity": ["code", "product_name", "brands", "brands_tags"],
    "geography": ["countries_tags", "main_countries_tags"],
    "category": ["categories", "categories_tags", "food_groups_tags"],
    "health": [
        "nutriscore_grade",
        "nutriscore_score",
        "nova_group",
        "nova_groups_tags",
        "nutrient_levels_tags",
        "nutriments",
    ],
    "label_transparency": [
        "labels_tags",
        "ingredients_text",
        "completeness",
        "data_quality_warnings_tags",
        "data_quality_errors_tags",
    ],
    "popularity": ["scans_n", "unique_scans_n", "popularity_tags"],
}

PRICE_REQUIRED = {
    "identity": ["id", "product_code", "product_name", "category_tag"],
    "price": [
        "price",
        "price_without_discount",
        "price_is_discounted",
        "price_per",
        "currency",
        "date",
    ],
    "geography": [
        "location_osm_lat",
        "location_osm_lon",
        "location_osm_address_country",
        "location_osm_address_country_code",
        "location_osm_address_city",
        "location_osm_display_name",
    ],
    "provenance": ["proof_type", "source", "created", "updated"],
}

NUTRIENTS_OF_INTEREST = [
    "energy-kcal",
    "energy-kj",
    "fat",
    "saturated-fat",
    "carbohydrates",
    "sugars",
    "fiber",
    "proteins",
    "salt",
    "sodium",
    "nova-group",
    "nutrition-score-fr",
]

PRODUCT_CORE_FIELDS = [
    "code",
    "product_name",
    "brands",
    "brands_tags",
    "countries_tags",
    "main_countries_tags",
    "categories",
    "categories_tags",
    "food_groups_tags",
    "nutriscore_grade",
    "nutriscore_score",
    "nova_group",
    "nova_groups_tags",
    "nutrient_levels_tags",
    "nutriments",
    "labels_tags",
    "ingredients_text",
    "completeness",
    "data_quality_warnings_tags",
    "data_quality_errors_tags",
    "scans_n",
    "unique_scans_n",
]

PRICE_CORE_FIELDS = [
    "id",
    "type",
    "product_code",
    "product_name",
    "category_tag",
    "labels_tags",
    "origins_tags",
    "price",
    "price_is_discounted",
    "price_without_discount",
    "price_per",
    "currency",
    "date",
    "location_osm_address_country",
    "location_osm_address_country_code",
    "location_osm_address_city",
    "location_osm_lat",
    "location_osm_lon",
    "location_osm_display_name",
    "proof_type",
    "source",
]


@dataclass(frozen=True)
class DatasetPaths:
    product_food: Path
    product_beauty: Path
    prices: Path


def json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Path):
        return str(value)
    return str(value)


def pct(part: int | float | None, whole: int | float | None) -> float | None:
    if part is None or whole in (None, 0):
        return None
    return round(float(part) / float(whole) * 100.0, 2)


def scan(path: Path) -> pl.LazyFrame:
    return pl.scan_parquet(path)


def list_present_expr(column: str) -> pl.Expr:
    return pl.col(column).is_not_null() & (pl.col(column).list.len() > 0)


def present_expr(column: str, dtype: pl.DataType) -> pl.Expr:
    if isinstance(dtype, pl.List):
        return list_present_expr(column)
    return pl.col(column).is_not_null()


def scalar(value: pl.DataFrame, column: str) -> Any:
    return value[column][0]


def schema_summary(path: Path) -> dict[str, Any]:
    lf = scan(path)
    schema = lf.collect_schema()
    return {
        "path": str(path),
        "file_size_bytes": path.stat().st_size,
        "columns": len(schema.names()),
        "schema": {name: str(dtype) for name, dtype in schema.items()},
    }


def row_count(path: Path) -> int:
    return int(scalar(scan(path).select(pl.len().alias("rows")).collect(), "rows"))


def coverage(lf: pl.LazyFrame, rows: int, fields: list[str]) -> dict[str, dict[str, Any]]:
    schema = lf.collect_schema()
    expressions: list[pl.Expr] = []
    for field in fields:
        if field not in schema:
            continue
        expressions.append(
            present_expr(field, schema[field]).sum().cast(pl.Int64).alias(field)
        )

    raw = lf.select(expressions).collect().to_dicts()[0] if expressions else {}
    return {
        field: {
            "present_rows": int(count),
            "coverage_pct": pct(int(count), rows),
        }
        for field, count in raw.items()
    }


def top_list_values(
    lf: pl.LazyFrame, column: str, limit: int = 20
) -> list[dict[str, Any]]:
    return (
        lf.select(pl.col(column))
        .filter(list_present_expr(column))
        .explode(column)
        .group_by(column)
        .len()
        .sort("len", descending=True)
        .limit(limit)
        .collect()
        .rename({column: "value", "len": "count"})
        .to_dicts()
    )


def top_scalar_values(
    lf: pl.LazyFrame, column: str, limit: int = 20
) -> list[dict[str, Any]]:
    return (
        lf.select(pl.col(column))
        .filter(pl.col(column).is_not_null())
        .group_by(column)
        .len()
        .sort("len", descending=True)
        .limit(limit)
        .collect()
        .rename({column: "value", "len": "count"})
        .to_dicts()
    )


def nutrient_coverage(lf: pl.LazyFrame, rows: int) -> dict[str, dict[str, Any]]:
    expressions = []
    for nutrient in NUTRIENTS_OF_INTEREST:
        has_nutrient = (
            pl.col("nutriments")
            .list.eval(pl.element().struct.field("name") == nutrient)
            .list.any()
            .fill_null(False)
        )
        expressions.append(has_nutrient.sum().cast(pl.Int64).alias(nutrient))

    raw = lf.select(expressions).collect().to_dicts()[0]
    return {
        nutrient: {
            "present_rows": int(count),
            "coverage_pct": pct(int(count), rows),
        }
        for nutrient, count in raw.items()
    }


def numeric_summary(lf: pl.LazyFrame, columns: list[str]) -> dict[str, dict[str, Any]]:
    schema = lf.collect_schema()
    expressions: list[pl.Expr] = []
    for column in columns:
        if column not in schema:
            continue
        expressions.extend(
            [
                pl.col(column).min().alias(f"{column}__min"),
                pl.col(column).median().alias(f"{column}__median"),
                pl.col(column).mean().alias(f"{column}__mean"),
                pl.col(column).quantile(0.95).alias(f"{column}__p95"),
                pl.col(column).quantile(0.99).alias(f"{column}__p99"),
                pl.col(column).max().alias(f"{column}__max"),
            ]
        )

    values = lf.select(expressions).collect().to_dicts()[0] if expressions else {}
    result: dict[str, dict[str, Any]] = {}
    for column in columns:
        keys = [
            f"{column}__min",
            f"{column}__median",
            f"{column}__mean",
            f"{column}__p95",
            f"{column}__p99",
            f"{column}__max",
        ]
        if not all(key in values for key in keys):
            continue
        result[column] = {
            "min": values[keys[0]],
            "median": values[keys[1]],
            "mean": values[keys[2]],
            "p95": values[keys[3]],
            "p99": values[keys[4]],
            "max": values[keys[5]],
        }
    return result


def product_derived_quality(lf: pl.LazyFrame, rows: int) -> dict[str, dict[str, Any]]:
    valid_grade = pl.col("nutriscore_grade").is_in(["a", "b", "c", "d", "e"])
    usable_health = valid_grade | pl.col("nutriscore_score").is_not_null()
    has_country_category = list_present_expr("countries_tags") & list_present_expr(
        "categories_tags"
    )
    has_peer_group = has_country_category & (
        pl.col("brands").is_not_null() | list_present_expr("brands_tags")
    )
    raw = (
        lf.select(
            [
                valid_grade.sum().cast(pl.Int64).alias("valid_nutriscore_grade_a_to_e"),
                usable_health.sum().cast(pl.Int64).alias("usable_nutrition_score"),
                has_country_category.sum().cast(pl.Int64).alias("has_country_and_category"),
                has_peer_group.sum().cast(pl.Int64).alias("has_country_category_and_brand"),
                (pl.col("completeness") >= 0.5)
                .sum()
                .cast(pl.Int64)
                .alias("completeness_at_least_0_5"),
            ]
        )
        .collect()
        .to_dicts()[0]
    )
    return {
        name: {"present_rows": int(count), "coverage_pct": pct(int(count), rows)}
        for name, count in raw.items()
    }


def price_derived_quality(lf: pl.LazyFrame, rows: int) -> dict[str, dict[str, Any]]:
    price_positive = pl.col("price") > 0
    geo_complete = pl.col("location_osm_lat").is_not_null() & pl.col(
        "location_osm_lon"
    ).is_not_null()
    analysis_ready = (
        price_positive
        & pl.col("currency").is_not_null()
        & pl.col("date").is_not_null()
        & geo_complete
    )
    barcode_analysis_ready = analysis_ready & pl.col("product_code").is_not_null()
    raw = (
        lf.select(
            [
                price_positive.sum().cast(pl.Int64).alias("positive_price"),
                analysis_ready.sum().cast(pl.Int64).alias("price_currency_date_geo_ready"),
                barcode_analysis_ready.sum()
                .cast(pl.Int64)
                .alias("barcode_price_ready"),
            ]
        )
        .collect()
        .to_dicts()[0]
    )
    return {
        name: {"present_rows": int(count), "coverage_pct": pct(int(count), rows)}
        for name, count in raw.items()
    }


def date_summary(lf: pl.LazyFrame, column: str) -> dict[str, Any]:
    raw = (
        lf.select(
            [
                pl.col(column).min().alias("min"),
                pl.col(column).max().alias("max"),
                pl.col(column).is_not_null().sum().cast(pl.Int64).alias("present_rows"),
            ]
        )
        .collect()
        .to_dicts()[0]
    )
    return raw


def product_price_join_summary(product_lf: pl.LazyFrame, price_lf: pl.LazyFrame) -> dict[str, Any]:
    product_codes = product_lf.select(pl.col("code")).filter(pl.col("code").is_not_null()).unique()
    price_codes = (
        price_lf.select(pl.col("product_code"))
        .filter(pl.col("product_code").is_not_null())
        .unique()
    )
    matched_codes = price_codes.join(
        product_codes,
        left_on="product_code",
        right_on="code",
        how="inner",
    )
    matched_price_rows = price_lf.filter(
        pl.col("product_code").is_not_null()
    ).join(product_codes, left_on="product_code", right_on="code", how="inner")

    counts = pl.concat(
        [
            product_codes.select(pl.len().cast(pl.Int64).alias("value")).with_columns(
                pl.lit("unique_product_codes").alias("metric")
            ),
            price_codes.select(pl.len().cast(pl.Int64).alias("value")).with_columns(
                pl.lit("unique_price_product_codes").alias("metric")
            ),
            matched_codes.select(pl.len().cast(pl.Int64).alias("value")).with_columns(
                pl.lit("matched_unique_product_codes").alias("metric")
            ),
            price_lf.select(
                pl.col("product_code").is_not_null().sum().cast(pl.Int64).alias("value")
            ).with_columns(pl.lit("price_rows_with_product_code").alias("metric")),
            matched_price_rows.select(pl.len().cast(pl.Int64).alias("value")).with_columns(
                pl.lit("matched_price_rows").alias("metric")
            ),
        ],
        how="diagonal",
    ).collect()

    raw = {row["metric"]: int(row["value"]) for row in counts.to_dicts()}
    return {
        **raw,
        "matched_unique_price_code_pct": pct(
            raw.get("matched_unique_product_codes"),
            raw.get("unique_price_product_codes"),
        ),
        "matched_price_rows_pct": pct(
            raw.get("matched_price_rows"),
            raw.get("price_rows_with_product_code"),
        ),
    }


def required_field_matrix(schema: dict[str, Any], required: dict[str, list[str]]) -> dict[str, Any]:
    return {
        group: {field: field in schema for field in fields}
        for group, fields in required.items()
    }


def assess_task_support(report: dict[str, Any]) -> dict[str, Any]:
    product_rows = report["products"]["food_rows"]
    price_rows = report["prices"]["rows"]
    product_cov = report["products"]["coverage"]
    nutrient_cov = report["products"]["nutrient_coverage"]
    price_cov = report["prices"]["coverage"]
    product_quality = report["products"]["derived_quality"]
    price_quality = report["prices"]["derived_quality"]
    join = report["join"]

    def cov(field: str) -> float:
        return float(product_cov.get(field, {}).get("coverage_pct") or 0.0)

    def pcov(field: str) -> float:
        return float(price_cov.get(field, {}).get("coverage_pct") or 0.0)

    def ncov(field: str) -> float:
        return float(nutrient_cov.get(field, {}).get("coverage_pct") or 0.0)

    def qcov(field: str) -> float:
        return float(product_quality.get(field, {}).get("coverage_pct") or 0.0)

    def pqcov(field: str) -> float:
        return float(price_quality.get(field, {}).get("coverage_pct") or 0.0)

    return {
        "T1_global_nutrition_structure": {
            "status": "strong",
            "reason": (
                f"{product_rows:,} food rows; country/category fields are present; "
                f"valid Nutri-Score A-E coverage is {qcov('valid_nutriscore_grade_a_to_e')}% "
                f"and numeric Nutri-Score coverage is {cov('nutriscore_score')}%. "
                f"NOVA coverage is {cov('nova_group')}%; sugar/salt/fat coverage is "
                f"{ncov('sugars')}%/{ncov('salt')}%/{ncov('fat')}%."
            ),
        },
        "T2_price_health_relationship": {
            "status": "limited_but_feasible",
            "reason": (
                f"{price_rows:,} price rows; {pcov('price')}% have prices, "
                f"{pcov('currency')}% have currency, {pcov('date')}% have dates, "
                f"and {pqcov('price_currency_date_geo_ready')}% are ready for "
                "price-date-geo analysis. "
                f"{join.get('matched_price_rows_pct')}% of barcode price rows match the "
                "product database. Currency normalization and country coverage filtering "
                "are needed before cross-country price comparisons."
            ),
        },
        "T3_label_transparency": {
            "status": "strong",
            "reason": (
                f"Completeness coverage is {cov('completeness')}%; labels coverage is "
                f"{cov('labels_tags')}%; ingredients coverage is {cov('ingredients_text')}%; "
                "quality warning/error tags are available for transparency diagnostics."
            ),
        },
        "T4_peer_comparison_and_anomalies": {
            "status": "strong_for_product_anomalies_limited_for_price_anomalies",
            "reason": (
                "The product database supports category/brand/country peer comparison at "
                "large scale. Price-based anomalies should be scoped to countries and "
                "categories with enough matched price records."
            ),
        },
    }


def build_report(paths: DatasetPaths) -> dict[str, Any]:
    product_lf = scan(paths.product_food)
    price_lf = scan(paths.prices)

    product_schema = schema_summary(paths.product_food)
    price_schema = schema_summary(paths.prices)

    product_rows = row_count(paths.product_food)
    beauty_rows = row_count(paths.product_beauty) if paths.product_beauty.exists() else None
    price_rows = row_count(paths.prices)

    report: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "files": {
            "product_food": str(paths.product_food),
            "product_beauty": str(paths.product_beauty),
            "prices": str(paths.prices),
        },
        "products": {
            "schema": product_schema,
            "food_rows": product_rows,
            "beauty_rows": beauty_rows,
            "required_fields": required_field_matrix(
                product_schema["schema"], PRODUCT_REQUIRED
            ),
            "coverage": coverage(product_lf, product_rows, PRODUCT_CORE_FIELDS),
            "derived_quality": product_derived_quality(product_lf, product_rows),
            "nutrient_coverage": nutrient_coverage(product_lf, product_rows),
            "numeric_summary": numeric_summary(
                product_lf,
                [
                    "completeness",
                    "nutriscore_score",
                    "nova_group",
                    "scans_n",
                    "unique_scans_n",
                ],
            ),
            "top_countries_tags": top_list_values(product_lf, "countries_tags"),
            "top_categories_tags": top_list_values(product_lf, "categories_tags"),
            "top_brands_tags": top_list_values(product_lf, "brands_tags"),
            "top_nutriscore_grade": top_scalar_values(product_lf, "nutriscore_grade"),
            "top_nova_group": top_scalar_values(product_lf, "nova_group"),
        },
        "prices": {
            "schema": price_schema,
            "rows": price_rows,
            "required_fields": required_field_matrix(price_schema["schema"], PRICE_REQUIRED),
            "coverage": coverage(price_lf, price_rows, PRICE_CORE_FIELDS),
            "derived_quality": price_derived_quality(price_lf, price_rows),
            "numeric_summary": numeric_summary(price_lf, ["price", "price_without_discount"]),
            "date_summary": date_summary(price_lf, "date"),
            "top_currency": top_scalar_values(price_lf, "currency"),
            "top_price_per": top_scalar_values(price_lf, "price_per"),
            "top_location_country_code": top_scalar_values(
                price_lf, "location_osm_address_country_code"
            ),
            "top_proof_type": top_scalar_values(price_lf, "proof_type"),
        },
        "join": product_price_join_summary(product_lf, price_lf),
    }
    report["task_support"] = assess_task_support(report)
    return report


def format_count(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def coverage_table(title: str, data: dict[str, dict[str, Any]]) -> list[str]:
    lines = [f"### {title}", "", "| Field | Present rows | Coverage |", "|---|---:|---:|"]
    for field, stats in data.items():
        lines.append(
            f"| `{field}` | {format_count(stats['present_rows'])} | "
            f"{format_count(stats['coverage_pct'])}% |"
        )
    lines.append("")
    return lines


def top_table(title: str, data: list[dict[str, Any]]) -> list[str]:
    lines = [f"### {title}", "", "| Value | Count |", "|---|---:|"]
    for row in data[:10]:
        lines.append(f"| `{row['value']}` | {format_count(row['count'])} |")
    lines.append("")
    return lines


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines: list[str] = []
    lines.extend(
        [
            "# FoodAtlas Dataset Audit",
            "",
            f"Generated at: `{report['generated_at']}`",
            "",
            "## Files",
            "",
            f"- Product food parquet: `{report['files']['product_food']}`",
            f"- Product beauty parquet: `{report['files']['product_beauty']}`",
            f"- Price parquet: `{report['files']['prices']}`",
            "",
            "## Scale",
            "",
            f"- Food product rows: **{format_count(report['products']['food_rows'])}**",
            f"- Beauty product rows: **{format_count(report['products']['beauty_rows'])}**",
            f"- Price rows: **{format_count(report['prices']['rows'])}**",
            f"- Product columns: **{report['products']['schema']['columns']}**",
            f"- Price columns: **{report['prices']['schema']['columns']}**",
            "",
        ]
    )

    lines.extend(coverage_table("Product Field Coverage", report["products"]["coverage"]))
    lines.extend(
        coverage_table("Product Derived Quality", report["products"]["derived_quality"])
    )
    lines.extend(
        coverage_table("Product Nutrient Coverage", report["products"]["nutrient_coverage"])
    )
    lines.extend(coverage_table("Price Field Coverage", report["prices"]["coverage"]))
    lines.extend(coverage_table("Price Derived Quality", report["prices"]["derived_quality"]))

    join = report["join"]
    lines.extend(
        [
            "## Product-Price Join",
            "",
            f"- Unique product codes: **{format_count(join.get('unique_product_codes'))}**",
            f"- Unique price product codes: **{format_count(join.get('unique_price_product_codes'))}**",
            f"- Matched unique product codes: **{format_count(join.get('matched_unique_product_codes'))}**",
            f"- Price rows with product code: **{format_count(join.get('price_rows_with_product_code'))}**",
            f"- Matched price rows: **{format_count(join.get('matched_price_rows'))}**",
            f"- Matched price rows ratio: **{format_count(join.get('matched_price_rows_pct'))}%**",
            "",
        ]
    )

    lines.extend(top_table("Top Product Countries", report["products"]["top_countries_tags"]))
    lines.extend(top_table("Top Product Categories", report["products"]["top_categories_tags"]))
    lines.extend(top_table("Top Product Brands", report["products"]["top_brands_tags"]))
    lines.extend(top_table("Top Price Currencies", report["prices"]["top_currency"]))
    lines.extend(
        top_table(
            "Top Price Location Country Codes",
            report["prices"]["top_location_country_code"],
        )
    )

    lines.extend(["## Task Support", ""])
    for task, data in report["task_support"].items():
        lines.extend(
            [
                f"### {task}",
                "",
                f"- Status: `{data['status']}`",
                f"- Reason: {data['reason']}",
                "",
            ]
        )

    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=Path("datasets"),
        help="Directory containing product-database/ and open-prices/.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("reports"),
        help="Directory where audit reports are written.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = DatasetPaths(
        product_food=args.dataset_dir / "product-database" / "food.parquet",
        product_beauty=args.dataset_dir / "product-database" / "beauty.parquet",
        prices=args.dataset_dir / "open-prices" / "prices.parquet",
    )

    missing = [str(path) for path in (paths.product_food, paths.product_beauty, paths.prices) if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing dataset files: {', '.join(missing)}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(paths)

    json_path = args.out_dir / "dataset_audit.json"
    md_path = args.out_dir / "dataset_audit.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=json_default),
        encoding="utf-8",
    )
    write_markdown(report, md_path)

    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    print("Task support summary:")
    for task, data in report["task_support"].items():
        print(f"- {task}: {data['status']}")


if __name__ == "__main__":
    main()
