# VEMIO Technical Case — Findings

## 1. Data Cleaning: Assumptions and Rules

**Dataset:** 283,533 transactions, 6 SKUs, 12 warehouses, ~25 months (Jan 2025 - Jan 2027).

### Cancelled tickets (sell_in_quantity = 0, 500 rows)
Kept in the dataset with an `is_cancelled` flag rather than dropped, to preserve
traceability. Excluded from any demand aggregation, since they represent no
actual unit movement.

### Gift/sample transactions (sell_in_amount = 0, sell_in_quantity > 0, 500 rows)
Kept with an `is_gift` flag. Included in demand forecasting (Challenge A), since
these are real units that left inventory. Excluded from price/elasticity analysis
(Challenge B), since unit_price = 0 does not reflect a real market price and would
distort the regression.

### Missing product metadata (1 row)
Category, subcategory, brand, and basket were null for one row. Validated that
these fields are constant per `product_code` across the dataset, so the missing
values were filled by mapping from other rows of the same SKU — no row dropped.

### Missing discount / bruto (~5.5%)
`discount`, `bruto`, and `sell_in_amount` are algebraically related:
`bruto = sell_in_amount / (1 - discount)`. Most nulls were resolved by deriving
one column from the other two. For rows with no promotion (`id_combo` null),
missing values were treated as an organic sale (`discount = 0`).

For 3 residual rows that belonged to a promotion but had both `discount` and
`bruto` missing, `discount` was imputed using the average discount of that same
`id_combo` (from other transactions in the same promotion), then `bruto` was
derived from it.

One row remains null in `bruto`: it is a gift/sample transaction
(`sell_in_amount = 0`, `discount = 1.0`), where `bruto = amount / (1-discount)`
is mathematically undefined (division by zero). Since gift rows are already
excluded from price/elasticity analysis, this was left null rather than forcing
an arbitrary value.

### Missing product_cost (~0.04%, 110 rows)
Initially assumed unit cost (`product_cost / sell_in_quantity`) would be
constant per SKU, like `product_margin`. Validation showed this is false:
unit cost is a **step function over time** — it stays fixed for months, then
jumps to a new level (consistent with periodic supplier cost updates).

Missing values were imputed using the median unit cost of that same
`product_code` **within the same year-month**, not a global median, to avoid
mixing an old cost period with a new one. A `product_cost_imputed` flag was
added for traceability.

### Cleaning summary
All nulls resolved except one `bruto` value (gift transaction, left null by
design — see above). Zero rows dropped from the original 283,533.

## 2. Exploratory Analysis

Weekly demand was plotted for all 6 SKUs over the full 104-week history
(`outputs/weekly_demand_by_sku.png`). Key observations:

- **Promotional spikes are clearly visible** and align with the combo date
  ranges in the data (e.g. Antitranspirante's largest spike, ~Aug-Sep 2025,
  matches "Combo Quincena"; Desodorante's largest spike, ~Mar-May 2026,
  matches "Combo Verano Desodorante 2"). This confirms promotions are driving
  real, measurable demand shifts — not just noise.
- **Desodorante / Antitranspirante** show strong, clear annual seasonality
  (demand rises each summer, Mar-May and Aug), consistent with a personal-care
  category tied to warm weather.
- **Cubito de pollo** shows a different pattern: seasonality *combined with* an
  upward trend (each yearly cycle ends at a higher level than the previous
  one) — a useful test of whether a model can separate trend from seasonality.
- **Shampoo SKUs (Azul, Verde, Rizos)** are noisier, with weaker seasonal
  signal — expected to be harder to forecast accurately.

## 3. Challenge A: Demand Forecasting

**SKU selection:** Desodorante 150 ml A, Cubito de pollo c/50, and Shampoo
Rizos 135 ml were chosen (out of the 6 available) to represent contrasting
demand patterns:
- *Desodorante 150 ml A* — strong, clear seasonality (the "easy" case).
- *Cubito de pollo c/50* — seasonality + trend combined, largest volume in
  the Alimentos category (a more complex case).
- *Shampoo Rizos 135 ml* — noisier demand, weaker seasonal signal (an honest
  "hard" case to show model limitations, rather than cherry-picking only
  well-behaved SKUs).

Shampoo 135 ml Azul and Shampoo 180ml Verde were excluded from this challenge
only to keep the analysis focused and readable — not because they lack value.
Shampoo 135 ml Azul and 180ml Verde also show the lowest price variation
(CV ~4.8-4.9%), making them weaker candidates for Challenge B regardless.

**Validation strategy:** the last 10 weeks of the 104-week history were held
out as a test set. All models are trained only on the prior 94 weeks and
evaluated on that unseen 10-week window — a walk-forward split, never random,
to avoid future information leakage.

**Baseline — Seasonal Naive:** predicts demand as equal to the same week, 52
weeks prior, respecting the annual seasonality observed in the EDA. This
baseline is the floor any more sophisticated model (SARIMA, XGBoost) must
beat to justify its added complexity.

**Baseline results:** WMAPE of 18.9% (Desodorante), 10.2% (Cubito de pollo),
and 31.7% (Shampoo Rizos). The error ranking matches the EDA: SKUs with
cleaner seasonal patterns forecast better with a naive approach, while
Desodorante's error is inflated by year-over-year shifts in promotional
timing that seasonal naive cannot capture.

**Models evaluated:**

1. **XGBoost (gradient boosting on tabular features)** — chosen first because
   it can directly incorporate a promo flag and lag features, which is
   exactly what seasonal naive is missing (see the Desodorante observation
   above). Features: lags (1, 2, 52 weeks), month, week-of-year, and
   promo-activity flag/discount depth for that week.
2. **SARIMA (Seasonal ARIMA)** — a classical statistical baseline that models
   the series purely from its own past values (trend + seasonality), without
   external regressors like promo activity. Included as a second comparison
   point to validate whether a simpler, more interpretable model performs
   competitively without promo information.

Both are compared against the Seasonal Naive baseline using the same
walk-forward 10-week holdout.

The weekly promo flag (`has_promo`) was validated against the known combo
date ranges — it correctly activates the same week each promotion starts,
with a visible demand jump (e.g. Antitranspirante: 457 → 760 units the week
"Combo Verano" began), confirming correct alignment between transaction-level
and weekly-aggregated data.

`lag_52` was excluded as a feature: with only 94 training weeks per SKU,
it would have discarded roughly half the training data (the entire first
year lacks a valid 52-week lag). `month` and `week_of_year` were used
instead to capture seasonality without that data loss.