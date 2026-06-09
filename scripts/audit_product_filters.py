#!/usr/bin/env python3
"""Evaluate practical product-database filter levels for FoodAtlas preprocessing."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl


PRODUCT_PATH = Path("datasets_raw/product-database/food.parquet")
PRICE_PATH = Path("datasets_raw/open-prices/prices.parquet")
OUT_JSON = Path("reports/product_filter_audit.json")
OUT_MD = Path("reports/product_filter_audit.md")


def pct(n: int, total: int) -> float:
    return round(n / total * 100, 2) if total else 0.0


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


def top_exploded(lf: pl.LazyFrame, col: str, limit: int = 15) -> list[dict[str, Any]]:
    return (
        lf.select(pl.col(col))
        .filter(has_list(col))
        .explode(col)
        .drop_nulls()
        .group_by(col)
        .len()
        .sort("len", descending=True)
        .limit(limit)
        .collect()
        .rename({col: "value", "len": "count"})
        .to_dicts()
    )


def json_default(value: Any) -> Any:
    return str(value)


def main() -> None:
    product_lf = pl.scan_parquet(PRODUCT_PATH)
    schema = product_lf.collect_schema()
    total = product_lf.select(pl.len().alias("n")).collect()["n"][0]

    has_code = pl.col("code").is_not_null()
    has_name = has_present("product_name", schema)
    has_country = has_list("countries_tags")
    has_category = has_list("categories_tags")
    has_brand = has_present("brands", schema) | has_list("brands_tags")
    has_nutriments = has_list("nutriments")
    has_energy = has_nutrient("energy-kcal") | has_nutrient("energy-kj") | has_nutrient("energy")
    has_fat = has_nutrient("fat")
    has_satfat = has_nutrient("saturated-fat")
    has_carbs = has_nutrient("carbohydrates")
    has_sugars = has_nutrient("sugars")
    has_protein = has_nutrient("proteins")
    has_salt = has_nutrient("salt") | has_nutrient("sodium")
    valid_nutriscore = pl.col("nutriscore_score").is_not_null() | pl.col(
        "nutriscore_grade"
    ).is_in(["a", "b", "c", "d", "e"])
    valid_nova = pl.col("nova_group").is_in([1, 2, 3, 4])
    quality_ready = pl.col("completeness").is_not_null() & pl.col(
        "data_quality_warnings_tags"
    ).is_not_null()
    high_complete = pl.col("completeness").fill_null(0) >= 0.5

    base = has_code & has_name & has_country & has_category
    any_nutrition = base & has_nutriments
    core_nutrition = base & has_energy & has_fat & has_sugars & has_salt & has_protein
    broad_health = core_nutrition & (valid_nutriscore | valid_nova)
    full_health = core_nutrition & valid_nutriscore & valid_nova
    brand_full_health = full_health & has_brand
    strict_quality = brand_full_health & quality_ready & high_complete
    full_nutrient_detail = strict_quality & has_satfat & has_carbs

    filters = {
        "base_identity_geo_category": {
            "expr": base,
            "description": "code/name/country/category are present; suitable for maps and category counts.",
        },
        "base_with_any_nutriments": {
            "expr": any_nutrition,
            "description": "Base fields plus any nutriments list; suitable for coverage diagnostics.",
        },
        "core_nutrition_ready": {
            "expr": core_nutrition,
            "description": "Base fields plus energy, fat, sugars, salt/sodium and proteins.",
        },
        "broad_health_ready": {
            "expr": broad_health,
            "description": "Core nutrition plus either Nutri-Score or NOVA; good for wider health comparisons.",
        },
        "full_health_ready": {
            "expr": full_health,
            "description": "Core nutrition plus both valid Nutri-Score and NOVA.",
        },
        "brand_full_health_ready": {
            "expr": brand_full_health,
            "description": "Full health fields plus brand; suitable for brand/category comparisons.",
        },
        "strict_quality_ready": {
            "expr": strict_quality,
            "description": "Brand health-ready products with quality fields and completeness >= 0.5.",
        },
        "full_nutrient_detail_ready": {
            "expr": full_nutrient_detail,
            "description": "Strict set plus saturated fat and carbohydrates; suitable for detailed product views.",
        },
    }

    count_exprs = [
        spec["expr"].sum().cast(pl.Int64).alias(name) for name, spec in filters.items()
    ]
    counts = product_lf.select([pl.len().alias("total"), *count_exprs]).collect().to_dicts()[0]

    price_codes = (
        pl.scan_parquet(PRICE_PATH)
        .select(pl.col("product_code").alias("code"))
        .filter(pl.col("code").is_not_null())
        .unique()
    )

    filter_rows: list[dict[str, Any]] = []
    for name, spec in filters.items():
        n = int(counts[name])
        price_n = (
            product_lf.filter(spec["expr"])
            .select("code")
            .join(price_codes, on="code", how="inner")
            .select(pl.len().cast(pl.Int64).alias("n"))
            .collect()["n"][0]
        )
        filter_rows.append(
            {
                "name": name,
                "count": n,
                "pct": pct(n, total),
                "price_matched_count": int(price_n),
                "price_matched_pct_total": pct(int(price_n), total),
                "price_matched_pct_filter": pct(int(price_n), n),
                "description": spec["description"],
            }
        )

    strict_lf = product_lf.filter(strict_quality)
    strict_summary = strict_lf.select(
        [
            pl.len().cast(pl.Int64).alias("rows"),
            pl.col("code").n_unique().alias("unique_codes"),
            pl.col("nutriscore_score").median().alias("nutriscore_score_median"),
            pl.col("nova_group").median().alias("nova_group_median"),
            pl.col("completeness").median().alias("completeness_median"),
            pl.col("completeness").mean().alias("completeness_mean"),
        ]
    ).collect().to_dicts()[0]

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "product_path": str(PRODUCT_PATH),
        "price_path": str(PRICE_PATH),
        "total_rows": int(total),
        "filters": filter_rows,
        "strict_quality_summary": strict_summary,
        "strict_top_countries": top_exploded(strict_lf, "countries_tags", 20),
        "strict_top_categories": top_exploded(strict_lf, "categories_tags", 20),
        "strict_top_brands": top_exploded(strict_lf, "brands_tags", 20),
        "strict_nutriscore_dist": strict_lf.group_by("nutriscore_grade")
        .len()
        .sort("nutriscore_grade")
        .collect()
        .to_dicts(),
        "strict_nova_dist": strict_lf.group_by("nova_group")
        .len()
        .sort("nova_group")
        .collect()
        .to_dicts(),
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=json_default), encoding="utf-8")
    write_markdown(report)
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")
    for row in filter_rows:
        print(f"{row['name']}: {row['count']:,} ({row['pct']}%), price matched {row['price_matched_count']:,}")


def write_markdown(report: dict[str, Any]) -> None:
    lines = [
        "# Product Filter Audit",
        "",
        f"Generated at: `{report['generated_at']}`",
        "",
        f"Total product rows: **{report['total_rows']:,}**",
        "",
        "## Filter Levels",
        "",
        "| Filter | Rows | % of total | Price-matched rows | % within filter | Suggested use |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in report["filters"]:
        lines.append(
            f"| `{row['name']}` | {row['count']:,} | {row['pct']:.2f}% | "
            f"{row['price_matched_count']:,} | {row['price_matched_pct_filter']:.2f}% | "
            f"{row['description']} |"
        )

    summary = report["strict_quality_summary"]
    lines.extend(
        [
            "",
            "## Recommended Main Candidate Set",
            "",
            "`strict_quality_ready` is the recommended starting point for product preprocessing.",
            "",
            f"- Rows: **{int(summary['rows']):,}**",
            f"- Unique product codes: **{int(summary['unique_codes']):,}**",
            f"- Median Nutri-Score score: **{summary['nutriscore_score_median']}**",
            f"- Median NOVA group: **{summary['nova_group_median']}**",
            f"- Median completeness: **{summary['completeness_median']:.4f}**",
            f"- Mean completeness: **{summary['completeness_mean']:.4f}**",
            "",
        ]
    )

    for title, key in [
        ("Top Countries", "strict_top_countries"),
        ("Top Categories", "strict_top_categories"),
        ("Top Brands", "strict_top_brands"),
    ]:
        lines.extend([f"## {title}", "", "| Value | Count |", "|---|---:|"])
        for row in report[key][:15]:
            lines.append(f"| `{row['value']}` | {row['count']:,} |")
        lines.append("")

    lines.extend(["## Strict Candidate Nutri-Score Distribution", "", "| Grade | Count |", "|---|---:|"])
    for row in report["strict_nutriscore_dist"]:
        lines.append(f"| `{row['nutriscore_grade']}` | {row['len']:,} |")
    lines.extend(["", "## Strict Candidate NOVA Distribution", "", "| NOVA | Count |", "|---|---:|"])
    for row in report["strict_nova_dist"]:
        lines.append(f"| `{row['nova_group']}` | {row['len']:,} |")
    lines.append("")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
