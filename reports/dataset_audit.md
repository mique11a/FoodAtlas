# FoodAtlas Dataset Audit

Generated at: `2026-05-30T23:44:25`

## Files

- Product food parquet: `datasets/product-database/food.parquet`
- Product beauty parquet: `datasets/product-database/beauty.parquet`
- Price parquet: `datasets/open-prices/prices.parquet`

## Scale

- Food product rows: **4,503,112**
- Beauty product rows: **62,829**
- Price rows: **260,509**
- Product columns: **111**
- Price columns: **48**

### Product Field Coverage

| Field | Present rows | Coverage |
|---|---:|---:|
| `code` | 4,503,112 | 100.00% |
| `product_name` | 4,225,579 | 93.84% |
| `brands` | 2,929,498 | 65.05% |
| `brands_tags` | 2,821,703 | 62.66% |
| `countries_tags` | 4,480,278 | 99.49% |
| `main_countries_tags` | 0 | 0.00% |
| `categories` | 1,978,882 | 43.94% |
| `categories_tags` | 1,835,456 | 40.76% |
| `food_groups_tags` | 1,437,227 | 31.92% |
| `nutriscore_grade` | 4,458,976 | 99.02% |
| `nutriscore_score` | 1,361,245 | 30.23% |
| `nova_group` | 1,121,732 | 24.91% |
| `nova_groups_tags` | 4,459,002 | 99.02% |
| `nutrient_levels_tags` | 1,514,625 | 33.64% |
| `nutriments` | 3,491,944 | 77.55% |
| `labels_tags` | 1,221,619 | 27.13% |
| `ingredients_text` | 1,274,913 | 28.31% |
| `completeness` | 4,503,093 | 100.00% |
| `data_quality_warnings_tags` | 4,451,963 | 98.86% |
| `data_quality_errors_tags` | 171,482 | 3.81% |
| `scans_n` | 1,558,962 | 34.62% |
| `unique_scans_n` | 1,558,962 | 34.62% |

### Product Derived Quality

| Field | Present rows | Coverage |
|---|---:|---:|
| `valid_nutriscore_grade_a_to_e` | 1,361,245 | 30.23% |
| `usable_nutrition_score` | 1,361,245 | 30.23% |
| `has_country_and_category` | 1,828,253 | 40.60% |
| `has_country_category_and_brand` | 1,462,039 | 32.47% |
| `completeness_at_least_0_5` | 1,217,400 | 27.03% |

### Product Nutrient Coverage

| Field | Present rows | Coverage |
|---|---:|---:|
| `energy-kcal` | 3,285,545 | 72.96% |
| `energy-kj` | 2,288,073 | 50.81% |
| `fat` | 3,257,271 | 72.33% |
| `saturated-fat` | 3,021,283 | 67.09% |
| `carbohydrates` | 3,260,310 | 72.40% |
| `sugars` | 3,079,604 | 68.39% |
| `fiber` | 1,737,405 | 38.58% |
| `proteins` | 3,261,953 | 72.44% |
| `salt` | 2,847,956 | 63.24% |
| `sodium` | 2,847,958 | 63.24% |
| `nova-group` | 1,069,414 | 23.75% |
| `nutrition-score-fr` | 412,623 | 9.16% |

### Price Field Coverage

| Field | Present rows | Coverage |
|---|---:|---:|
| `id` | 260,509 | 100.00% |
| `type` | 260,509 | 100.00% |
| `product_code` | 252,311 | 96.85% |
| `product_name` | 172,359 | 66.16% |
| `category_tag` | 8,198 | 3.15% |
| `labels_tags` | 3,030 | 1.16% |
| `origins_tags` | 6,959 | 2.67% |
| `price` | 260,509 | 100.00% |
| `price_is_discounted` | 260,509 | 100.00% |
| `price_without_discount` | 19,362 | 7.43% |
| `price_per` | 8,198 | 3.15% |
| `currency` | 260,338 | 99.93% |
| `date` | 260,323 | 99.93% |
| `location_osm_address_country` | 259,794 | 99.73% |
| `location_osm_address_country_code` | 259,589 | 99.65% |
| `location_osm_address_city` | 256,408 | 98.43% |
| `location_osm_lat` | 259,794 | 99.73% |
| `location_osm_lon` | 259,794 | 99.73% |
| `location_osm_display_name` | 259,794 | 99.73% |
| `proof_type` | 260,380 | 99.95% |
| `source` | 243,705 | 93.55% |

### Price Derived Quality

| Field | Present rows | Coverage |
|---|---:|---:|
| `positive_price` | 260,496 | 100.00% |
| `price_currency_date_geo_ready` | 259,600 | 99.65% |
| `barcode_price_ready` | 251,409 | 96.51% |

## Product-Price Join

- Unique product codes: **4,503,052**
- Unique price product codes: **119,300**
- Matched unique product codes: **99,554**
- Price rows with product code: **252,311**
- Matched price rows: **225,636**
- Matched price rows ratio: **89.43%**

### Top Product Countries

| Value | Count |
|---|---:|
| `en:france` | 1,232,024 |
| `en:united-states` | 911,563 |
| `en:germany` | 407,928 |
| `en:spain` | 353,680 |
| `en:italy` | 266,117 |
| `en:united-kingdom` | 186,164 |
| `en:canada` | 119,730 |
| `en:switzerland` | 103,315 |
| `en:belgium` | 99,393 |
| `en:ireland` | 78,530 |

### Top Product Categories

| Value | Count |
|---|---:|
| `en:plant-based-foods-and-beverages` | 541,063 |
| `en:plant-based-foods` | 472,186 |
| `en:snacks` | 328,178 |
| `en:sweet-snacks` | 241,267 |
| `en:beverages` | 225,166 |
| `en:dairies` | 171,923 |
| `en:cereals-and-potatoes` | 163,488 |
| `en:meats-and-their-products` | 147,207 |
| `en:fermented-foods` | 133,395 |
| `en:fermented-milk-products` | 128,558 |

### Top Product Brands

| Value | Count |
|---|---:|
| `xx:carrefour` | 24,210 |
| `xx:lidl` | 18,987 |
| `xx:coop` | 17,137 |
| `xx:u` | 16,221 |
| `xx:aldi` | 15,411 |
| `xx:nestle` | 14,294 |
| `xx:auchan` | 12,438 |
| `xx:bonarea` | 12,326 |
| `xx:hacendado` | 11,421 |
| `xx:tesco` | 9,941 |

### Top Price Currencies

| Value | Count |
|---|---:|
| `EUR` | 207,129 |
| `USD` | 27,261 |
| `NOK` | 14,775 |
| `SEK` | 2,881 |
| `GBP` | 1,882 |
| `PLN` | 1,197 |
| `CHF` | 773 |
| `CAD` | 648 |
| `JPY` | 543 |
| `RUB` | 467 |

### Top Price Location Country Codes

| Value | Count |
|---|---:|
| `FR` | 184,473 |
| `US` | 27,074 |
| `NO` | 14,776 |
| `DE` | 13,500 |
| `SE` | 2,841 |
| `BE` | 2,239 |
| `GB` | 1,948 |
| `IT` | 1,385 |
| `PL` | 1,180 |
| `FI` | 1,095 |

## Task Support

### T1_global_nutrition_structure

- Status: `strong`
- Reason: 4,503,112 food rows; country/category fields are present; valid Nutri-Score A-E coverage is 30.23% and numeric Nutri-Score coverage is 30.23%. NOVA coverage is 24.91%; sugar/salt/fat coverage is 68.39%/63.24%/72.33%.

### T2_price_health_relationship

- Status: `limited_but_feasible`
- Reason: 260,509 price rows; 100.0% have prices, 99.93% have currency, 99.93% have dates, and 99.65% are ready for price-date-geo analysis. 89.43% of barcode price rows match the product database. Currency normalization and country coverage filtering are needed before cross-country price comparisons.

### T3_label_transparency

- Status: `strong`
- Reason: Completeness coverage is 100.0%; labels coverage is 27.13%; ingredients coverage is 28.31%; quality warning/error tags are available for transparency diagnostics.

### T4_peer_comparison_and_anomalies

- Status: `strong_for_product_anomalies_limited_for_price_anomalies`
- Reason: The product database supports category/brand/country peer comparison at large scale. Price-based anomalies should be scoped to countries and categories with enough matched price records.
