# Product Filter Audit

Generated at: `2026-06-08T08:44:31`

Total product rows: **4,503,112**

## Filter Levels

| Filter | Rows | % of total | Price-matched rows | % within filter | Suggested use |
|---|---:|---:|---:|---:|---|
| `base_identity_geo_category` | 1,789,127 | 39.73% | 83,760 | 4.68% | code/name/country/category are present; suitable for maps and category counts. |
| `base_with_any_nutriments` | 1,631,800 | 36.24% | 80,993 | 4.96% | Base fields plus any nutriments list; suitable for coverage diagnostics. |
| `core_nutrition_ready` | 1,414,024 | 31.40% | 74,476 | 5.27% | Base fields plus energy, fat, sugars, salt/sodium and proteins. |
| `broad_health_ready` | 1,389,664 | 30.86% | 73,850 | 5.31% | Core nutrition plus either Nutri-Score or NOVA; good for wider health comparisons. |
| `full_health_ready` | 819,677 | 18.20% | 59,948 | 7.31% | Core nutrition plus both valid Nutri-Score and NOVA. |
| `brand_full_health_ready` | 702,128 | 15.59% | 59,081 | 8.41% | Full health fields plus brand; suitable for brand/category comparisons. |
| `strict_quality_ready` | 688,334 | 15.29% | 58,892 | 8.56% | Brand health-ready products with quality fields and completeness >= 0.5. |
| `full_nutrient_detail_ready` | 671,100 | 14.90% | 58,211 | 8.67% | Strict set plus saturated fat and carbohydrates; suitable for detailed product views. |

## Recommended Main Candidate Set

`strict_quality_ready` is the recommended starting point for product preprocessing.

- Rows: **688,334**
- Unique product codes: **688,324**
- Median Nutri-Score score: **11.0**
- Median NOVA group: **4.0**
- Median completeness: **0.6875**
- Mean completeness: **0.7207**

## Top Countries

| Value | Count |
|---|---:|
| `en:france` | 244,578 |
| `en:united-states` | 194,676 |
| `en:germany` | 83,338 |
| `en:spain` | 36,299 |
| `en:united-kingdom` | 34,248 |
| `en:italy` | 26,757 |
| `en:switzerland` | 22,203 |
| `en:belgium` | 21,505 |
| `en:world` | 19,906 |
| `en:netherlands` | 14,277 |
| `en:canada` | 10,710 |
| `en:poland` | 8,714 |
| `en:australia` | 6,337 |
| `en:portugal` | 6,300 |
| `en:austria` | 6,211 |

## Top Categories

| Value | Count |
|---|---:|
| `en:plant-based-foods-and-beverages` | 213,796 |
| `en:plant-based-foods` | 186,502 |
| `en:snacks` | 153,272 |
| `en:sweet-snacks` | 108,169 |
| `en:cereals-and-potatoes` | 75,360 |
| `en:dairies` | 71,098 |
| `en:beverages` | 62,064 |
| `en:fermented-foods` | 54,339 |
| `en:desserts` | 52,678 |
| `en:fermented-milk-products` | 52,277 |
| `en:meats-and-their-products` | 51,208 |
| `en:meals` | 50,445 |
| `en:fruits-and-vegetables-based-foods` | 49,115 |
| `en:biscuits-and-cakes` | 48,942 |
| `en:cereals-and-their-products` | 47,696 |

## Top Brands

| Value | Count |
|---|---:|
| `xx:carrefour` | 11,752 |
| `xx:u` | 9,029 |
| `xx:auchan` | 6,259 |
| `xx:lidl` | 5,478 |
| `xx:marque-repere` | 4,693 |
| `xx:aldi` | 4,661 |
| `xx:nestle` | 4,375 |
| `xx:casino` | 4,266 |
| `xx:coop` | 3,986 |
| `xx:hacendado` | 3,226 |
| `xx:leader-price` | 2,927 |
| `xx:tesco` | 2,735 |
| `xx:migros` | 2,703 |
| `xx:picard` | 2,516 |
| `xx:monoprix` | 2,329 |

## Strict Candidate Nutri-Score Distribution

| Grade | Count |
|---|---:|
| `a` | 105,130 |
| `b` | 70,412 |
| `c` | 150,517 |
| `d` | 168,340 |
| `e` | 193,935 |

## Strict Candidate NOVA Distribution

| NOVA | Count |
|---|---:|
| `1` | 88,899 |
| `2` | 17,260 |
| `3` | 155,642 |
| `4` | 426,533 |
