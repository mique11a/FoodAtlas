#!/usr/bin/env python3
"""Minimal FoodAtlas backend for serving parquet-backed frontend data."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import polars as pl
from flask import Flask, jsonify, request, send_from_directory


BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"
PRODUCTS_PATH = BASE_DIR / "datasets_preprocessed" / "products_analysis.parquet"

DEFAULT_ANOMALY_LIMIT = 4000
DEFAULT_PRICE_LIMIT = 4000
ANOMALY_DISPLAY_MIN = 0.4
ANOMALY_DISPLAY_MAX = 3.5

COUNTRY_META = {
    "en:france": {"name": "法国", "enName": "France"},
    "en:united-states": {"name": "美国", "enName": "United States"},
    "en:germany": {"name": "德国", "enName": "Germany"},
    "en:spain": {"name": "西班牙", "enName": "Spain"},
    "en:united-kingdom": {"name": "英国", "enName": "United Kingdom"},
    "en:italy": {"name": "意大利", "enName": "Italy"},
    "en:belgium": {"name": "比利时", "enName": "Belgium"},
    "en:canada": {"name": "加拿大", "enName": "Canada"},
    "en:netherlands": {"name": "荷兰", "enName": "Netherlands"},
    "en:switzerland": {"name": "瑞士", "enName": "Switzerland"},
}

CATEGORY_META = {
    "en:sugary-snacks": {"name": "甜味零食", "enName": "Sugary snacks", "parent": ""},
    "en:appetizers": {"name": "开胃食品", "enName": "Appetizers", "parent": ""},
    "en:salty-snacks": {"name": "咸味零食", "enName": "Salty snacks", "parent": ""},
    "en:beverages": {"name": "饮料", "enName": "Beverages", "parent": ""},
    "en:cereals-and-potatoes": {
        "name": "谷物与土豆",
        "enName": "Cereals & potatoes",
        "parent": "",
    },
    "en:milk-and-dairy-products": {
        "name": "乳制品",
        "enName": "Milk & dairy",
        "parent": "",
    },
    "en:fish-meat-eggs": {
        "name": "鱼肉蛋类",
        "enName": "Fish, meat & eggs",
        "parent": "",
    },
    "en:fruits-and-vegetables": {
        "name": "果蔬制品",
        "enName": "Fruits & vegetables",
        "parent": "",
    },
    "en:fats-and-sauces": {
        "name": "油脂与酱料",
        "enName": "Fats & sauces",
        "parent": "",
    },
    "en:composite-foods": {
        "name": "复合食品",
        "enName": "Composite foods",
        "parent": "",
    },
}

NUTRISCORE_TO_NUM = {"a": 5, "b": 4, "c": 3, "d": 2, "e": 1}
FX_TO_EUR = {
    "EUR": 1.0,
    "USD": 0.92,
    "GBP": 1.17,
    "CHF": 1.04,
    "CAD": 0.68,
    "NOK": 0.086,
    "SEK": 0.088,
    "PLN": 0.23,
    "MXN": 0.05,
    "TWD": 0.029,
    "RUB": 0.01,
    "MAD": 0.091,
    "ADP": 1.0 / 166.386,
    "RON": 0.20,
    "UAH": 0.022,
    "ILS": 0.25,
    "INR": 0.011,
    "XPF": 0.00838,
    "CZK": 0.04,
    "ALL": 0.01,
    "PAB": 0.92,
    "JPY": 0.0061,
    "AUD": 0.61,
    "HUF": 0.0025,
    "BGN": 0.511,
    "ARS": 0.0010,
    "DKK": 0.134,
    "MYR": 0.20,
    "TND": 0.30,
    "PHP": 0.016,
    "RSD": 0.0085,
    "SGD": 0.68,
    "BAM": 0.511,
    "ISK": 0.0068,
    "KZT": 0.0018,
    "QAR": 0.25,
    "XAF": 1.0 / 655.957,
    "DOP": 0.015,
    "KRW": 0.00067,
    "TRY": 0.027,
    "THB": 0.025,
    "HKD": 0.118,
    "LYD": 0.19,
    "MRU": 0.024,
    "AED": 0.25,
    "LAK": 0.000042,
    "AFN": 0.012,
    "BMD": 0.92,
    "TZS": 0.00034,
    "DZD": 0.0069,
    "XOF": 1.0 / 655.957,
    "LBP": 0.00001,
}


def round_or_none(value: Any, digits: int) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def add_display_anomaly_column(
    df: pl.DataFrame,
    *,
    source_col: str = "peer_anomaly_score",
    target_col: str = "anomaly_display",
) -> pl.DataFrame:
    valid = df.filter(pl.col(source_col).is_not_null() & (pl.col(source_col) >= 0))
    if valid.height == 0:
        return df.with_columns(pl.lit(ANOMALY_DISPLAY_MIN).alias(target_col))

    stats = valid.select(
        [
            pl.col(source_col).quantile(0.05).alias("floor"),
            pl.col(source_col).quantile(0.98).alias("cap"),
        ]
    ).row(0, named=True)
    floor = float(stats["floor"] or ANOMALY_DISPLAY_MIN)
    cap = float(stats["cap"] or floor)
    cap = max(cap, floor + 1e-6)
    low = math.log1p(floor)
    high = max(low + 1e-6, math.log1p(cap))

    scaled = (
        (
            (pl.col(source_col).clip(floor, cap).log1p() - pl.lit(low))
            / pl.lit(high - low)
        )
        * (ANOMALY_DISPLAY_MAX - ANOMALY_DISPLAY_MIN)
        + ANOMALY_DISPLAY_MIN
    ).clip(ANOMALY_DISPLAY_MIN, ANOMALY_DISPLAY_MAX)

    return df.with_columns(
        pl.when(pl.col(source_col).is_not_null() & (pl.col(source_col) >= 0))
        .then(scaled)
        .otherwise(pl.lit(ANOMALY_DISPLAY_MIN))
        .alias(target_col)
    )


def title_from_tag(tag: str) -> str:
    return tag.removeprefix("en:").replace("-", " ").title()


def country_display(tag: str) -> dict[str, str]:
    meta = COUNTRY_META.get(tag)
    if meta:
        return meta
    fallback = title_from_tag(tag)
    return {"name": fallback, "enName": fallback}


def category_display(tag: str) -> dict[str, str]:
    meta = CATEGORY_META.get(tag)
    if meta:
        return meta
    fallback = title_from_tag(tag)
    return {"name": fallback, "enName": fallback, "parent": ""}


def brand_display(tag: str | None) -> str:
    if not tag:
        return "Unknown"
    label = tag.split(":", 1)[-1].replace("-", " ").strip()
    return label.title() if label else "Unknown"


BRAND_METRIC_META = {
    "health": {"column": "health_score_composite", "label": "品牌平均健康评分"},
    "anomaly": {"column": "anomaly_display", "label": "品牌平均异常度"},
    "completeness": {"column": "data_completeness_score", "label": "品牌平均完整度"},
    "nutriscore_num": {"column": "nutriscore_num", "label": "品牌平均 Nutri-Score"},
    "nova": {"column": "nova_group", "label": "品牌平均 NOVA"},
    "price": {"column": "price_eur_clean", "label": "品牌均价 (€)"},
    "sugars": {"column": "sugars_100g", "label": "品牌中位糖含量"},
    "salt": {"column": "salt_equivalent_100g", "label": "品牌中位盐含量"},
    "fat": {"column": "fat_100g", "label": "品牌中位脂肪含量"},
    "energy": {"column": "energy_kcal_100g", "label": "品牌中位能量"},
}


class FoodAtlasStore:
    def __init__(self, products_path: Path) -> None:
        self.products = self._load_products(products_path)
        self.country_tag_by_en = {
            meta["enName"]: tag for tag, meta in COUNTRY_META.items()
        }
        self.category_tag_by_en = {
            meta["enName"]: tag for tag, meta in CATEGORY_META.items()
        }
        self.countries = self._build_country_summary()
        self.categories = self._build_category_summary()

    def _load_products(self, products_path: Path) -> pl.DataFrame:
        columns = [
            "code",
            "product_name",
            "primary_brand_tag",
            "analysis_country_tag",
            "analysis_category_tag",
            "nutriscore_grade",
            "nova_group",
            "energy_kcal_100g",
            "fat_100g",
            "sugars_100g",
            "salt_equivalent_100g",
            "data_completeness_score",
            "quality_warning_count",
            "quality_error_count",
            "health_score_composite",
            "peer_anomaly_score",
            "price_median",
            "currency",
            "has_price",
            "price_record_count",
            "flag_high_price_low_health",
            "flag_high_sugar_high_nova",
            "flag_low_completeness_many_warnings",
        ]
        fx_rate_expr = pl.col("currency").replace(FX_TO_EUR, default=None).cast(pl.Float64)
        return pl.read_parquet(products_path, columns=columns).with_columns(
            [
                pl.col("primary_brand_tag").alias("brand_tag"),
                pl.when(pl.col("primary_brand_tag").is_not_null())
                .then(
                    pl.col("primary_brand_tag")
                    .str.replace(r"^.*?:", "")
                    .str.replace_all("-", " ")
                    .str.to_titlecase()
                )
                .otherwise(pl.lit("Unknown"))
                .alias("brand_name"),
                pl.col("product_name").fill_null(pl.col("code")).alias("product_name"),
                pl.col("nutriscore_grade")
                .str.to_lowercase()
                .replace(NUTRISCORE_TO_NUM, default=None)
                .cast(pl.Int32)
                .alias("nutriscore_num"),
                pl.when(pl.col("price_median").is_not_null() & (pl.col("price_median") > 0))
                .then(pl.col("price_median"))
                .otherwise(None)
                .alias("price_median_clean"),
                fx_rate_expr.alias("fx_rate_to_eur"),
                pl.when(
                    pl.col("price_median").is_not_null()
                    & (pl.col("price_median") > 0)
                    & fx_rate_expr.is_not_null()
                )
                .then(pl.col("price_median") * fx_rate_expr)
                .otherwise(None)
                .alias("price_eur_clean"),
            ]
        )

    def _build_country_summary(self) -> list[dict[str, Any]]:
        base_df = (
            self.products.group_by("analysis_country_tag")
            .agg(
                [
                    pl.len().alias("samples"),
                    pl.col("health_score_composite").mean().alias("health"),
                    pl.col("sugars_100g").mean().alias("sugars"),
                    pl.col("salt_equivalent_100g").mean().alias("salt"),
                    pl.col("fat_100g").mean().alias("fat"),
                    pl.col("energy_kcal_100g").mean().alias("energy"),
                    pl.col("nutriscore_num").mean().alias("nutriscore"),
                    pl.col("nova_group").mean().alias("nova"),
                    pl.col("peer_anomaly_score").mean().alias("anomaly"),
                    pl.col("price_eur_clean").is_not_null().mean().alias("price_cov"),
                ]
            )
        )
        price_df = (
            self.products.filter(pl.col("price_eur_clean").is_not_null())
            .group_by("analysis_country_tag")
            .agg(
                [
                    pl.len().alias("price_records"),
                    pl.col("price_eur_clean").mean().alias("price"),
                ]
            )
        )
        df = (
            base_df.join(price_df, on="analysis_country_tag", how="left")
            .sort("samples", descending=True)
        )
        records: list[dict[str, Any]] = []
        for row in df.iter_rows(named=True):
            display = country_display(row["analysis_country_tag"])
            records.append(
                {
                    "name": display["name"],
                    "enName": display["enName"],
                    "samples": int(row["samples"]),
                    "health": round_or_none(row["health"], 3),
                    "sugars": round_or_none(row["sugars"], 2),
                    "salt": round_or_none(row["salt"], 3),
                    "fat": round_or_none(row["fat"], 2),
                    "energy": round_or_none(row["energy"], 1),
                    "nutriscore": round_or_none(row["nutriscore"], 2),
                    "nova": round_or_none(row["nova"], 2),
                    "anomaly": round_or_none(row["anomaly"], 3),
                    "price": round_or_none(row["price"], 2),
                    "priceCurrency": "EUR" if row["price"] is not None else None,
                    "priceCov": round_or_none((row["price_cov"] or 0) * 100, 1),
                    "priceRecordCount": int(row["price_records"] or 0),
                }
            )
        return records

    def _build_category_summary(self) -> list[dict[str, Any]]:
        df = (
            self.products.group_by("analysis_category_tag")
            .agg(
                [
                    pl.len().alias("samples"),
                    pl.col("health_score_composite").mean().alias("health"),
                    pl.col("sugars_100g").mean().alias("sugars"),
                    pl.col("salt_equivalent_100g").mean().alias("salt"),
                    pl.col("fat_100g").mean().alias("fat"),
                    pl.col("energy_kcal_100g").mean().alias("energy"),
                    pl.col("nutriscore_num").mean().alias("nutriscore"),
                    pl.col("nova_group").mean().alias("nova"),
                    pl.col("peer_anomaly_score").mean().alias("anomaly"),
                    pl.col("price_eur_clean").is_not_null().mean().alias("price_cov"),
                ]
            )
            .sort("samples", descending=True)
        )
        records: list[dict[str, Any]] = []
        for row in df.iter_rows(named=True):
            display = category_display(row["analysis_category_tag"])
            records.append(
                {
                    "name": display["name"],
                    "enName": display["enName"],
                    "parent": display["parent"],
                    "samples": int(row["samples"]),
                    "health": round_or_none(row["health"], 3),
                    "sugars": round_or_none(row["sugars"], 2),
                    "salt": round_or_none(row["salt"], 3),
                    "fat": round_or_none(row["fat"], 2),
                    "energy": round_or_none(row["energy"], 1),
                    "nutriscore": round_or_none(row["nutriscore"], 2),
                    "nova": round_or_none(row["nova"], 2),
                    "anomaly": round_or_none(row["anomaly"], 3),
                    "priceCov": round_or_none((row["price_cov"] or 0) * 100, 1),
                }
            )
        return records

    def bootstrap_payload(self) -> dict[str, Any]:
        return {
            "countries": self.countries,
            "categories": self.categories,
            "supportedCurrencies": ["EUR"],
            "defaultPriceCurrency": "EUR",
            "totalProducts": self.products.height,
        }

    def _filter_products(
        self,
        *,
        country_en: str | None = None,
        category_en: str | None = None,
        priced_only: bool = False,
    ) -> pl.DataFrame:
        df = self.products
        country_tag = self.country_tag_by_en.get(country_en or "")
        category_tag = self.category_tag_by_en.get(category_en or "")

        if country_en:
            if not country_tag:
                return df.head(0)
            df = df.filter(pl.col("analysis_country_tag") == country_tag)
        if category_en:
            if not category_tag:
                return df.head(0)
            df = df.filter(pl.col("analysis_category_tag") == category_tag)
        if priced_only:
            df = df.filter(pl.col("price_eur_clean").is_not_null())
        return df

    def _sampling_groups(self, country_en: str | None, category_en: str | None) -> list[str]:
        if not country_en and not category_en:
            return ["analysis_country_tag", "analysis_category_tag"]
        if country_en and not category_en:
            return ["analysis_category_tag"]
        if not country_en and category_en:
            return ["analysis_country_tag"]
        return []

    def _sample_records(
        self,
        df: pl.DataFrame,
        *,
        limit: int,
        group_cols: list[str],
        priority_col: str | None = None,
    ) -> pl.DataFrame:
        if df.height <= limit:
            return df
        if not group_cols:
            if priority_col:
                return df.sort(priority_col, descending=True).head(limit)
            return df.sort("code").head(limit)

        priority_df = pl.DataFrame(schema=df.schema)
        if priority_col:
            priority_size = min(max(200, limit // 5), limit // 2)
            priority_df = df.sort(priority_col, descending=True).head(priority_size)
            df = df.filter(~pl.col("code").is_in(priority_df["code"].to_list()))
            if df.height + priority_df.height <= limit:
                return pl.concat(
                    [priority_df.select(df.columns), df.select(df.columns)],
                    how="vertical_relaxed",
                ).head(limit)

        group_count = max(1, df.select(group_cols).unique().height)
        remaining = max(0, limit - priority_df.height)
        per_group = max(1, remaining // group_count)

        sampled = (
            df.sort(group_cols + ["code"])
            .group_by(group_cols, maintain_order=True)
            .head(per_group)
        )
        sampled = sampled.select(df.columns)
        if sampled.height > remaining:
            sampled = sampled.head(remaining)
        elif sampled.height < remaining:
            more = (
                df.filter(~pl.col("code").is_in(sampled["code"].to_list()))
                .sort("code")
                .head(remaining - sampled.height)
            )
            sampled = pl.concat([sampled, more], how="vertical_relaxed")

        if priority_df.height == 0:
            return sampled

        merged = pl.concat(
            [priority_df.select(df.columns), sampled.select(df.columns)],
            how="vertical_relaxed",
        ).unique(
            subset=["code"], keep="first"
        )
        if merged.height > limit:
            merged = merged.head(limit)
        return merged

    def _product_records(self, df: pl.DataFrame) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for row in df.iter_rows(named=True):
            country_meta = country_display(row["analysis_country_tag"])
            category_meta = category_display(row["analysis_category_tag"])
            flags: list[str] = []
            if row["flag_high_price_low_health"]:
                flags.append("high_price_low_health")
            if row["flag_high_sugar_high_nova"]:
                flags.append("high_sugar_high_nova")
            if row["flag_low_completeness_many_warnings"]:
                flags.append("low_completeness_many_warnings")
            records.append(
                {
                    "id": row["code"],
                    "name": row["product_name"] or row["code"],
                    "brand": brand_display(row["primary_brand_tag"]),
                    "country": country_meta["enName"],
                    "countryLabel": country_meta["name"],
                    "category": category_meta["enName"],
                    "categoryLabel": category_meta["name"],
                    "sugars": round_or_none(row["sugars_100g"], 2),
                    "salt": round_or_none(row["salt_equivalent_100g"], 3),
                    "fat": round_or_none(row["fat_100g"], 2),
                    "health": round_or_none(row["health_score_composite"], 3),
                    "price": round_or_none(row["price_eur_clean"], 2),
                    "currency": "EUR" if row["price_eur_clean"] is not None else None,
                    "anomaly": round_or_none(row["peer_anomaly_score"], 3),
                    "flags": flags,
                    "nutriscore": (row["nutriscore_grade"] or "").upper() or None,
                    "nutriscore_num": row["nutriscore_num"],
                    "nova": row["nova_group"],
                    "completeness": round_or_none(row["data_completeness_score"], 3),
                    "energy": round_or_none(row["energy_kcal_100g"], 1),
                    "qualityWarnings": row["quality_warning_count"],
                    "qualityErrors": row["quality_error_count"],
                    "priceRecordCount": row["price_record_count"],
                    "flag": (
                        "high"
                        if (
                            (row["peer_anomaly_score"] or 0) >= 2.25
                            or row["flag_high_price_low_health"]
                            or row["flag_high_sugar_high_nova"]
                        )
                        else (
                            "warn"
                            if (
                                (row["peer_anomaly_score"] or 0) >= 1.45
                                or row["flag_low_completeness_many_warnings"]
                                or (row["quality_warning_count"] or 0) >= 2
                            )
                            else "good"
                        )
                    ),
                }
            )
        return records

    def anomaly_products(
        self,
        *,
        country_en: str | None = None,
        category_en: str | None = None,
        limit: int = DEFAULT_ANOMALY_LIMIT,
    ) -> dict[str, Any]:
        filtered = self._filter_products(country_en=country_en, category_en=category_en)
        sampled = self._sample_records(
            filtered,
            limit=limit,
            group_cols=self._sampling_groups(country_en, category_en),
            priority_col="peer_anomaly_score",
        )
        return {
            "total": filtered.height,
            "sampled": filtered.height > sampled.height,
            "products": self._product_records(sampled),
        }

    def price_products(
        self,
        *,
        country_en: str | None = None,
        category_en: str | None = None,
        currency: str | None = None,
        limit: int = DEFAULT_PRICE_LIMIT,
    ) -> dict[str, Any]:
        filtered = self._filter_products(
            country_en=country_en,
            category_en=category_en,
            priced_only=True,
        )
        sampled = self._sample_records(
            filtered,
            limit=limit,
            group_cols=self._sampling_groups(country_en, category_en),
            priority_col="price_eur_clean",
        )
        return {
            "currency": "EUR",
            "total": filtered.height,
            "sampled": filtered.height > sampled.height,
            "products": self._product_records(sampled),
        }

    def brand_bubbles(
        self,
        *,
        country_en: str | None = None,
        category_en: str | None = None,
        brand_query: str | None = None,
        x_metric: str = "health",
        y_metric: str = "price",
        min_products: int = 10,
        priced_min: int = 3,
        multi_category_min: int = 2,
        limit: int = 120,
    ) -> dict[str, Any]:
        filtered = self._filter_products(country_en=country_en, category_en=category_en)
        filtered = filtered.filter(pl.col("brand_tag").is_not_null())
        if brand_query:
            query = brand_query.strip().lower()
            if query:
                filtered = filtered.filter(
                    pl.col("brand_name").str.to_lowercase().str.contains(query, literal=True)
                )

        filtered = add_display_anomaly_column(filtered)

        x_meta = BRAND_METRIC_META.get(x_metric) or BRAND_METRIC_META["health"]
        y_meta = BRAND_METRIC_META.get(y_metric) or BRAND_METRIC_META["price"]

        def metric_expr(metric_key: str) -> pl.Expr:
            if metric_key in {"sugars", "salt", "fat", "energy"}:
                return pl.col(BRAND_METRIC_META[metric_key]["column"]).median().alias(metric_key)
            return pl.col(BRAND_METRIC_META[metric_key]["column"]).mean().alias(metric_key)

        grouped = (
            filtered.group_by(["brand_tag", "brand_name"])
            .agg(
                [
                    pl.len().alias("products"),
                    pl.col("analysis_category_tag").n_unique().alias("categories"),
                    pl.col("analysis_country_tag").n_unique().alias("countries"),
                    pl.col("price_eur_clean").is_not_null().sum().alias("priced_products"),
                    pl.col("price_eur_clean").is_not_null().mean().alias("price_cov"),
                    pl.col("analysis_category_tag")
                    .mode()
                    .first()
                    .alias("dominant_category_tag"),
                    metric_expr("health"),
                    metric_expr("anomaly"),
                    metric_expr("completeness"),
                    metric_expr("nutriscore_num"),
                    metric_expr("nova"),
                    metric_expr("price"),
                    metric_expr("sugars"),
                    metric_expr("salt"),
                    metric_expr("fat"),
                    metric_expr("energy"),
                ]
            )
        )

        if not category_en:
            grouped = grouped.filter(pl.col("categories") >= max(1, multi_category_min))
        grouped = grouped.filter(pl.col("products") >= max(1, min_products))

        if y_metric == "price" or x_metric == "price":
            grouped = grouped.filter(pl.col("priced_products") >= max(1, priced_min))

        grouped = grouped.filter(
            pl.col(x_metric).is_not_null() & pl.col(y_metric).is_not_null()
        )

        if limit > 0:
            grouped = grouped.sort(["products", "priced_products"], descending=[True, True]).head(limit)

        records: list[dict[str, Any]] = []
        for row in grouped.iter_rows(named=True):
            dominant_category = category_display(row["dominant_category_tag"]) if row["dominant_category_tag"] else {"name": "", "enName": "", "parent": ""}
            records.append(
                {
                    "brand": row["brand_name"],
                    "brandTag": row["brand_tag"],
                    "products": int(row["products"]),
                    "categories": int(row["categories"]),
                    "countries": int(row["countries"]),
                    "pricedProducts": int(row["priced_products"]),
                    "priceCoverage": round_or_none((row["price_cov"] or 0) * 100, 1),
                    "dominantCategory": dominant_category["enName"],
                    "dominantCategoryLabel": dominant_category["name"],
                    "health": round_or_none(row["health"], 3),
                    "anomaly": round_or_none(row["anomaly"], 3),
                    "completeness": round_or_none(row["completeness"], 3),
                    "nutriscore_num": round_or_none(row["nutriscore_num"], 3),
                    "nova": round_or_none(row["nova"], 3),
                    "price": round_or_none(row["price"], 2),
                    "sugars": round_or_none(row["sugars"], 2),
                    "salt": round_or_none(row["salt"], 3),
                    "fat": round_or_none(row["fat"], 2),
                    "energy": round_or_none(row["energy"], 1),
                }
            )

        return {
            "xMetric": x_metric,
            "yMetric": y_metric,
            "totalProducts": filtered.height,
            "brands": records,
        }


store = FoodAtlasStore(PRODUCTS_PATH)
app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")


@app.route("/")
def index() -> Any:
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/bootstrap")
def api_bootstrap() -> Any:
    return jsonify(store.bootstrap_payload())


@app.get("/api/products/anomaly")
def api_products_anomaly() -> Any:
    country = request.args.get("country") or None
    category = request.args.get("category") or None
    limit = request.args.get("limit", type=int) or DEFAULT_ANOMALY_LIMIT
    return jsonify(
        store.anomaly_products(
            country_en=country,
            category_en=category,
            limit=limit,
        )
    )


@app.get("/api/products/price")
def api_products_price() -> Any:
    country = request.args.get("country") or None
    category = request.args.get("category") or None
    currency = request.args.get("currency") or None
    limit = request.args.get("limit", type=int) or DEFAULT_PRICE_LIMIT
    return jsonify(
        store.price_products(
            country_en=country,
            category_en=category,
            currency=currency,
            limit=limit,
        )
    )


@app.get("/api/brands/bubbles")
def api_brands_bubbles() -> Any:
    country = request.args.get("country") or None
    category = request.args.get("category") or None
    brand_query = request.args.get("brand") or None
    x_metric = request.args.get("x_metric") or "health"
    y_metric = request.args.get("y_metric") or "price"
    min_products = request.args.get("min_products", type=int) or 10
    priced_min = request.args.get("priced_min", type=int) or 3
    multi_category_min = request.args.get("multi_category_min", type=int) or 2
    limit = request.args.get("limit", type=int) or 120
    return jsonify(
        store.brand_bubbles(
            country_en=country,
            category_en=category,
            brand_query=brand_query,
            x_metric=x_metric,
            y_metric=y_metric,
            min_products=min_products,
            priced_min=priced_min,
            multi_category_min=multi_category_min,
            limit=limit,
        )
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8094, debug=False)
