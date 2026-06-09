# Derived Metric Design

## Metric Scope

The preprocessed product table is suitable for global nutrition structure, peer comparison, and anomaly detection.
The aligned price tables are suitable for country- and currency-specific price analysis, not global pooled price comparisons.

## Proposed Derived Metrics

### 1. Health Score Composite

Use existing `nutriscore_score` and `nova_group` as anchors, then add nutrient-position penalties within peer groups.
Recommended peer group: `analysis_country_tag + analysis_category_tag`.
Suggested formulation:
`health_score_composite = 0.45 * nutriscore_percentile_good + 0.25 * (1 - nova_scaled) + 0.15 * (1 - sugars_percentile) + 0.10 * (1 - salt_percentile) + 0.05 * proteins_percentile`.
Interpretation: higher is healthier.

### 2. Data Completeness Score

This should measure how analysis-ready a product row is, not label transparency.
Suggested formulation:
`data_completeness_score = 0.50 * completeness + 0.15 * nutrient_field_fill_rate + 0.10 * has_ingredients_text + 0.05 * has_labels_tags - 0.12 * warning_penalty - 0.08 * error_penalty`.
Where `nutrient_field_fill_rate = nutrition_fields_present_count / 8` and warning/error penalties are capped transforms of `quality_warning_count` and `quality_error_count`.

### 3. Price-Nutrition Value Index

Compute only within `location_osm_address_country_code + currency + analysis_category_tag`.
Use aggregated price medians from `price_summary_by_product`.
Suggested formulation:
`value_index = health_score_composite_percentile - price_median_percentile`.
Interpretation: higher means healthier than peers at a lower relative price.

### 4. Peer Anomaly Score

Use robust z-scores within `analysis_country_tag + analysis_category_tag` for `price_median`, `sugars_100g`, `salt_100g`, `saturated_fat_100g`, `nutriscore_score`, `nova_group`, and `data_completeness_score`.
Suggested formulation:
`peer_anomaly_score = weighted_sum(abs(robust_z_i))`.
For directional anomalies, keep separate flags such as `high_price_low_health`, `high_sugar_high_nova`, and `low_completeness_many_warnings`.

### 5. Brand Concentration Indicators

At the country/category level, compute brand share, top-brand share, and Herfindahl-style concentration to identify markets dominated by a few brands.

## Implementation Order

1. Build peer-group percentiles on the preprocessed product table.
2. Aggregate aligned prices to product/currency/country medians.
3. Compute health and completeness scores.
4. Join price medians back to products where available.
5. Compute value index and anomaly score.