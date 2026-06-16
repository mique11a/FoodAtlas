#!/usr/bin/env python3
"""Minimal FoodAtlas backend for serving parquet-backed frontend data."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl
from flask import Flask, jsonify, request, send_from_directory


BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"
PRODUCTS_PATH = BASE_DIR / "datasets_preprocessed" / "products_analysis.parquet"

DEFAULT_ANOMALY_LIMIT = 4000
DEFAULT_PRICE_LIMIT = 4000

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
    "en:sweet-snacks": {"name": "甜食", "enName": "Sweet snacks", "parent": "零食"},
    "en:plant-based-foods": {
        "name": "植物基食品",
        "enName": "Plant-based foods",
        "parent": "",
    },
    "en:cereals-and-potatoes": {
        "name": "谷物与土豆",
        "enName": "Cereals & potatoes",
        "parent": "",
    },
    "en:desserts": {"name": "甜点", "enName": "Desserts", "parent": ""},
    "en:beverages": {"name": "饮料", "enName": "Beverages", "parent": ""},
    "en:snacks": {"name": "零食", "enName": "Snacks", "parent": ""},
    "en:fermented-milk-products": {
        "name": "发酵乳制品",
        "enName": "Fermented milk",
        "parent": "乳制品",
    },
    "en:dairies": {"name": "乳制品", "enName": "Dairies", "parent": ""},
    "en:plant-based-foods-and-beverages": {
        "name": "植物基食品与饮料",
        "enName": "Plant-based foods & beverages",
        "parent": "植物基食品",
    },
    "en:fermented-foods": {
        "name": "发酵食品",
        "enName": "Fermented foods",
        "parent": "",
    },
}

NUTRISCORE_TO_NUM = {"a": 5, "b": 4, "c": 3, "d": 2, "e": 1}


def round_or_none(value: Any, digits: int) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


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
        return pl.read_parquet(products_path, columns=columns).with_columns(
            [
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
            ]
        )

    def _build_country_summary(self) -> list[dict[str, Any]]:
        df = (
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
                ]
            )
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
                }
            )
        return records

    def bootstrap_payload(self) -> dict[str, Any]:
        return {
            "countries": self.countries,
            "categories": self.categories,
            "defaultPriceCurrency": "EUR",
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
            df = df.filter(pl.col("has_price") & pl.col("currency").is_not_null())
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

    def _dominant_currency(self, df: pl.DataFrame) -> str | None:
        if df.height == 0:
            return None
        currency_counts = (
            df.group_by("currency")
            .len()
            .filter(pl.col("currency").is_not_null())
            .sort("len", descending=True)
        )
        if currency_counts.height == 0:
            return None
        return currency_counts.item(0, "currency")

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
                    "brand": row["primary_brand_tag"],
                    "country": country_meta["enName"],
                    "countryLabel": country_meta["name"],
                    "category": category_meta["enName"],
                    "categoryLabel": category_meta["name"],
                    "sugars": round_or_none(row["sugars_100g"], 2),
                    "salt": round_or_none(row["salt_equivalent_100g"], 3),
                    "fat": round_or_none(row["fat_100g"], 2),
                    "health": round_or_none(row["health_score_composite"], 3),
                    "price": round_or_none(row["price_median_clean"], 2),
                    "currency": row["currency"],
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
        target_currency = currency or self._dominant_currency(filtered) or "EUR"
        filtered = filtered.filter(pl.col("currency") == target_currency)
        sampled = self._sample_records(
            filtered,
            limit=limit,
            group_cols=self._sampling_groups(country_en, category_en),
            priority_col="price_median_clean",
        )
        return {
            "currency": target_currency,
            "total": filtered.height,
            "sampled": filtered.height > sampled.height,
            "products": self._product_records(sampled),
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


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8091, debug=False)
