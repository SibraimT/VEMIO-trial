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

![Weekly demand by SKU](../outputs/weekly_demand_by_sku.png)

Weekly demand was plotted for all 6 SKUs over the full 104-week history
(`../outputs/weekly_demand_by_sku.png`). Key observations:

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

## 4. Model Results & Comparison

**XGBoost results (Test 10 weeks):**

| SKU | MAPE | WMAPE | RMSE |
|---|---|---|---|
| Desodorante 150 ml A | 10.26% | 9.99% | 77.82 |
| Cubito de pollo c/50 | 6.49% | 6.68% | 86.76 |
| Shampoo Rizos 135 ml | 14.85% | 13.91% | 168.58 |

**SARIMA results (Test 10 weeks):**

| SKU | MAPE | WMAPE | RMSE |
|---|---|---|---|
| Desodorante 150 ml A | 59.87% | 58.78% | 371.59 |
| Cubito de pollo c/50 | 15.85% | 17.32% | 218.28 |
| Shampoo Rizos 135 ml | 12.68% | 11.98% | 128.76 |

SARIMA was fit without a seasonal component (`seasonal_order=(0,0,0,0)`):
with only 94 training weeks, there is not even two full annual cycles to
estimate a 52-week seasonal term reliably — the same reasoning used to
exclude `lag_52` from XGBoost's features.

**Model selection (best WMAPE per SKU):**

| SKU | Best model | WMAPE |
|---|---|---|
| Desodorante 150 ml A | XGBoost | 9.99% |
| Cubito de pollo c/50 | XGBoost | 6.68% |
| Shampoo Rizos 135 ml | SARIMA | 11.98% |

**Key finding — no single model wins across all SKUs:**

- **Desodorante** is the clearest case for promo-aware modeling. SARIMA
  (58.78% WMAPE) performs *worse than the naive baseline* — it extrapolates
  the tail of a recent promotion after it ends, since it has no visibility
  into promo activity. XGBoost, which uses `has_promo`/`avg_discount` as
  features, roughly halves the baseline's error.
- **Cubito de pollo** shows the same pattern: SARIMA (17.32%) underperforms
  both XGBoost (6.68%) and even the naive baseline (10.2%), because it was
  deliberately fit without seasonality — exactly the signal that drives this
  SKU (seasonality + trend, per the EDA).
- **Shampoo Rizos**, the noisiest series, is the one case where the simpler
  model wins: SARIMA (11.98%) slightly beats XGBoost (13.91%). With limited
  training data (92 weeks) and weak seasonal/promo structure, XGBoost has
  less signal to learn from and is more exposed to overfitting the lag
  features to noise.

**Conclusion:** model choice should be driven by what dominates each SKU's
demand pattern — promo timing and seasonality favor a feature-rich model
(XGBoost); noisy, weakly-structured series favor a simpler autoregressive
model (SARIMA). A per-SKU model selection outperforms committing to a single
model for the full catalog.

## 4. Model Results & Comparison

**XGBoost results (Test 10 weeks):**

| SKU | MAPE | WMAPE | RMSE |
|---|---|---|---|
| Desodorante 150 ml A | 10.26% | 9.99% | 77.82 |
| Cubito de pollo c/50 | 6.49% | 6.68% | 86.76 |
| Shampoo Rizos 135 ml | 14.85% | 13.91% | 168.58 |

**SARIMA results (Test 10 weeks):**

| SKU | MAPE | WMAPE | RMSE |
|---|---|---|---|
| Desodorante 150 ml A | 59.87% | 58.78% | 371.59 |
| Cubito de pollo c/50 | 15.85% | 17.32% | 218.28 |
| Shampoo Rizos 135 ml | 12.68% | 11.98% | 128.76 |

SARIMA was fit without a seasonal component (`seasonal_order=(0,0,0,0)`):
with only 94 training weeks, there is not even two full annual cycles to
estimate a 52-week seasonal term reliably — the same reasoning used to
exclude `lag_52` from XGBoost's features.

**Model selection (best WMAPE per SKU):**

| SKU | Best model | WMAPE |
|---|---|---|
| Desodorante 150 ml A | XGBoost | 9.99% |
| Cubito de pollo c/50 | XGBoost | 6.68% |
| Shampoo Rizos 135 ml | SARIMA | 11.98% |

**Key finding — no single model wins across all SKUs:**

- **Desodorante** is the clearest case for promo-aware modeling. SARIMA
  (58.78% WMAPE) performs *worse than the naive baseline* — it extrapolates
  the tail of a recent promotion after it ends, since it has no visibility
  into promo activity. XGBoost, which uses `has_promo`/`avg_discount` as
  features, roughly halves the baseline's error.
- **Cubito de pollo** shows the same pattern: SARIMA (17.32%) underperforms
  both XGBoost (6.68%) and even the naive baseline (10.2%), because it was
  deliberately fit without seasonality — exactly the signal that drives this
  SKU (seasonality + trend, per the EDA).
- **Shampoo Rizos**, the noisiest series, is the one case where the simpler
  model wins: SARIMA (11.98%) slightly beats XGBoost (13.91%). With limited
  training data (92 weeks) and weak seasonal/promo structure, XGBoost has
  less signal to learn from and is more exposed to overfitting the lag
  features to noise.

**Conclusion:** model choice should be driven by what dominates each SKU's
demand pattern — promo timing and seasonality favor a feature-rich model
(XGBoost); noisy, weakly-structured series favor a simpler autoregressive
model (SARIMA). A per-SKU model selection outperforms committing to a single
model for the full catalog.

## 5. Final Forecast (8–12 Weeks Ahead)

![10-week forecast by SKU](../outputs/forecast_by_sku.png)

The winning model per SKU was re-trained on the full history and used to
forecast 10 weeks ahead:

- **Cubito de pollo** (~1060–1150 units) is consistent with the trailing
  trend and considered reliable for planning purposes.
- **Desodorante** (~650–690 units, flat) likely **underestimates** actual
  demand for this window. This SKU has a strong Feb–Mar seasonal spike each
  year tied to "Combo Verano" promotions; since `has_promo`/`avg_discount`
  are held constant at their last observed (non-promo) value — the only
  information available about the future — the model has no way to
  anticipate a promotional jump. This forecast should be read as a
  **"no new promotion" baseline scenario**, to be adjusted upward manually
  if a promotion is planned, or re-run with `has_promo=1` and a realistic
  `avg_discount` for the relevant weeks.
- **Shampoo Rizos** (SARIMA) converges to a near-constant ~965 units after
  ~3 weeks, losing the volatility visible historically — an expected
  property of a non-seasonal ARIMA at this horizon, more reliable as a
  short-term (1–3 week) estimate than further out.

**Takeaway:** point forecasts alone are not sufficient for SKUs with known
future promotional activity (Desodorante) or high noise (Shampoo Rizos) —
both should be flagged for manual review / scenario adjustment rather than
used as-is for inventory planning.

## 6. Challenge B: SKU Selection

The case requires one SKU with sufficient historical price/discount variation
for elasticity estimation. Effective price (`sell_in_amount / sell_in_quantity`,
excluding gift and cancelled transactions) was compared across all 6 SKUs by
coefficient of variation (CV):

| SKU | Mean price | Std | CV (%) | Transactions |
|---|---|---|---|---|
| **Desodorante 150 ml A** | **52.67** | **5.32** | **10.10** | **64,325** |
| Antitranspirante 150 ml C | 55.98 | 5.58 | 9.98 | 35,113 |
| Cubito de pollo c/50 | 197.76 | 14.10 | 7.13 | 52,508 |
| Shampoo Rizos 135 ml | 19.42 | 1.17 | 6.00 | 69,840 |
| Shampoo 135 ml Azul | 19.05 | 0.93 | 4.89 | 44,608 |
| Shampoo 180ml Verde | 16.16 | 0.77 | 4.79 | 16,139 |

**Selected: Desodorante 150 ml A** — highest price CV among all SKUs, second-
highest transaction volume (only Antitranspirante has a comparable CV, but
with roughly half the sample size), and prior evidence from Challenge A of
demand clearly responding to its promotions — favorable conditions for an
elasticity estimate to reflect a real price-demand relationship rather than
noise.

## 7. Challenge B: Elasticity Model Approach

**Model:** log-log regression of quantity on price, controlling for calendar
month:

```
log(quantity) = β₀ + β₁ · log(price) + β₂ · month_dummies
```

**Why log-log:** the coefficient β₁ in this specification is directly
interpretable as price elasticity (% change in demand per 1% change in
price) — the standard definition of price sensitivity, and the one the case
asks to estimate.

**Why control for month:** Desodorante has strong seasonality (confirmed in
Challenge A — Feb-Mar and Aug-Sep spikes tied to "Combo Verano"), and price
also falls during those same windows since that's when promotions run.
Without controlling for month, the model would confuse two distinct effects:
demand rising because price fell (real elasticity) vs. demand rising because
it's high season, with price coincidentally falling too. Leaving this
uncontrolled would inflate the elasticity estimate, overstating how
price-sensitive demand actually is.

**Why not also control for promo activity:** `has_promo` and `price` are
not independent — a lower price *is* how a promo manifests, mechanically.
Including both would introduce collinearity and make the price coefficient
unstable. It's also unnecessary here: the elasticity simulator only needs to
answer "at this price, what demand do we expect," regardless of whether that
price originated from a formal promotion or an organic discount.

## 8. Challenge B: Elasticity Estimate

![Price-demand relationship — Desodorante 150 ml A](../outputs/price_elasticity_desodorante.png)

**Result:** estimated price elasticity of **-2.998** (p < 0.001, t = -19.05,
R² = 0.932). Demand is elastic (|elasticity| > 1): a 1% price increase is
associated with a ~3% drop in weekly volume. Month fixed effects confirm the
seasonality already seen in Challenge A — May through September carry large,
highly significant positive coefficients relative to January.

**Caveat:** this elasticity is higher than typical for a recurring
personal-care product (often -1 to -2 in the category). A likely driver:
this measures **sell-in to distributor**, not consumer-level sales. When
price drops during a promotion, distributors often buy ahead of immediate
need ("forward buying") to capture the discount, inflating that week's
recorded volume beyond true end-consumer demand. This is a real limitation
of estimating elasticity from sell-in data — the result should be read as
"distributor order response to price," not strictly "consumer demand," and
is flagged here rather than presented as an unconditional number.

**Additional note:** observed prices cluster around a handful of discrete
levels (~$44, $46.5, $48, $55, $57.5, $60.5) rather than varying
continuously — consistent with a small number of fixed discount tiers
across combos, rather than daily price changes. The fitted curve
interpolates between these clusters; confidence in the elasticity estimate
is strongest near the observed price levels and weaker in the gaps between
them.

## 9. Challenge B: Price Simulator

A simulator was built combining the fitted elasticity model with current
unit cost to project, for any price within the observed range
($43.99–$60.67): expected demand, revenue, and margin ($ and %).

**Key finding:** at the lower end of the observed price range (~$44-47),
simulated margin is negative (-13% to -6%). This reflects the cost-basis
assumption above — those price levels were historically paired with a lower
unit cost (~$45 in early 2025), but the simulator uses today's unit cost
(~$49.70). Under current cost conditions, those historical low prices would
be unprofitable, regardless of the demand gain they'd generate. This
effectively rules out the bottom of the observed range as a viable pricing
zone today.

**No interior optimum:** across the observed price range, revenue is
maximized at the lowest price ($43.99) and margin ($) at the highest
($60.67) — both range boundaries, not an interior "sweet spot." This
follows directly from elastic demand (elasticity ≈ -3.0): revenue falls
and margin rises monotonically with price throughout this range.

**Recommended pricing zone: $55–$60**, not a single point. This range keeps
margin solidly positive (14-18%), overlaps with prices already charged
historically (so customer acceptance is evidenced, not extrapolated), and
avoids the ~62% volume collapse seen at the top of the range ($44 →
~1,934 units/week vs. $60.67 → ~738 units/week).