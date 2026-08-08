# VEMIO Technical Case — Findings

**Dataset:** 283,533 transactions, 6 SKUs, 12 warehouses, ~25 months (Jan 2025 - Jan 2027). Zero rows dropped.

## 1. Data Cleaning: Assumptions and Rules

- **Cancelled tickets** (`sell_in_quantity = 0`, 500 rows): kept with `is_cancelled` flag; excluded from demand aggregation.
- **Gift/sample transactions** (`sell_in_amount = 0`, qty > 0, 500 rows): kept with `is_gift` flag. Included in Challenge A (real units moved); excluded from Challenge B (unit_price = 0 would distort the regression).
- **Missing metadata** (1 row): category/subcategory/brand/basket are constant per `product_code`, so filled by mapping from other rows of the same SKU.
- **Missing discount/bruto** (~5.5%): derived algebraically where possible (`bruto = sell_in_amount / (1-discount)`); nulls with no promotion (`id_combo` null) treated as organic sale (`discount=0`); 3 residual rows imputed using the average discount of the same `id_combo`. One row remains null in `bruto` (gift transaction, division by zero) — left null by design, already excluded from Challenge B.
- **Missing `product_cost`** (~0.04%, 110 rows): unit cost is a **step function over time** (not constant per SKU, as initially assumed) — validated, then imputed using the median unit cost of the same SKU **within the same year-month**, flagged with `product_cost_imputed`.

## 2. Exploratory Analysis

![Weekly demand by SKU](../outputs/weekly_demand_by_sku.png)

Promotional spikes are clearly visible and align with combo date ranges, confirming promotions drive real demand shifts. Desodorante/Antitranspirante show strong annual seasonality (Mar-May, Aug). Cubito de pollo combines seasonality with an upward trend. Shampoo SKUs are noisier with weaker seasonal signal.

## 3. Challenge A: Demand Forecasting

**SKUs selected:** Desodorante 150 ml A (clean seasonality — "easy" case), Cubito de pollo c/50 (seasonality + trend, highest-volume Alimentos SKU), Shampoo Rizos 135 ml (noisy, weak seasonality — an honest "hard" case). The two remaining shampoos were left out only to keep scope focused; they also have the lowest price variation, making them weak Challenge B candidates.

**Validation:** walk-forward split — last 10 of 104 weeks held out as test, models trained only on the prior 94 weeks. No random split, no future leakage.

**Baseline (Seasonal Naive, 52-week lag):** WMAPE 18.9% (Desodorante), 10.2% (Cubito), 31.7% (Shampoo Rizos) — the floor any model must beat.

**Models:** (1) **XGBoost** — lags 1/2 weeks, month, week-of-year, promo flag/discount depth; chosen because it can see promo activity, which the baseline can't. (2) **SARIMA** — fit without a seasonal term (`(0,0,0,0)`), since 94 weeks isn't enough to estimate a reliable 52-week seasonal component. `lag_52` was excluded from XGBoost for the same reason (would discard ~half the training data). The weekly `has_promo` flag was validated against transaction-level combo dates — it correctly activates the same week each promo starts, with a visible demand jump (e.g. Antitranspirante: 457 → 760 units the week "Combo Verano" began).

**Why WMAPE as the primary metric:** MAPE weights every week equally, so a low-volume week with a small absolute error looks like a huge percentage error. WMAPE weights by actual volume sold, which better reflects the error that matters for reabasto planning — deviation from total volume, not an average of week-level percentages. MAPE/RMSE are reported as secondary reference.

## 4. Model Results & Comparison

| SKU | Naive WMAPE | XGBoost WMAPE | SARIMA WMAPE | **Best model** |
|---|---|---|---|---|
| Desodorante 150 ml A | 18.9% | **9.99%** | 58.78% | XGBoost |
| Cubito de pollo c/50 | 10.2% | **6.68%** | 17.32% | XGBoost |
| Shampoo Rizos 135 ml | 31.7% | 13.91% | **11.98%** | SARIMA |

*(Full MAPE/RMSE breakdown in the notebook.)*

**No single model wins across all SKUs.** Desodorante and Cubito are dominated by promo timing/trend, which SARIMA can't see (it even underperforms the naive baseline on both). Shampoo Rizos, the noisiest series with the least structure, favors the simpler SARIMA — XGBoost has less signal to learn from and overfits the lag features to noise. **Conclusion:** model choice should follow what dominates each SKU's pattern; per-SKU selection beats committing to one model for the whole catalog.

## 5. Final Forecast (8–12 Weeks Ahead)

![10-week forecast by SKU](../outputs/forecast_by_sku.png)

- **Cubito de pollo** (~1,060–1,150 units): consistent with trailing trend, reliable for planning.
- **Desodorante** (~650–690 units, flat): likely **underestimates** demand — `has_promo`/`avg_discount` are held at their last non-promo value, so the model can't anticipate the Feb-Mar promotional jump seen historically. Read as a **"no new promotion" baseline**, to be adjusted or re-run with `has_promo=1` if a promotion is planned.
- **Shampoo Rizos** (SARIMA): converges to a near-constant ~965 units after ~3 weeks — more reliable short-term (1-3 weeks) than further out.

**Takeaway:** point forecasts alone aren't sufficient for SKUs with known future promo activity or high noise — both should be flagged for manual review, not used as-is.

## 6. Challenge B: Price Elasticity — Desodorante 150 ml A

**SKU selection:** compared effective price CV across all 6 SKUs (excluding gift/cancelled transactions):

| SKU | Mean price | CV (%) | Transactions |
|---|---|---|---|
| **Desodorante 150 ml A** | **52.67** | **10.10** | **64,325** |
| Antitranspirante 150 ml C | 55.98 | 9.98 | 35,113 |
| Cubito de pollo c/50 | 197.76 | 7.13 | 52,508 |
| Shampoo Rizos 135 ml | 19.42 | 6.00 | 69,840 |
| Shampoo 135 ml Azul | 19.05 | 4.89 | 44,608 |
| Shampoo 180ml Verde | 16.16 | 4.79 | 16,139 |

Desodorante has the highest CV, second-highest volume (only Antitranspirante is comparable, with roughly half the sample size), and prior evidence (Challenge A) of demand responding to its promotions.

**Model:** log-log regression, `log(quantity) = β₀ + β₁·log(price) + β₂·month_dummies`. Month is controlled for because price and seasonality move together (promos run in high season); `has_promo` is not controlled separately since it's mechanically redundant with price.

**Result:** elasticity of **-2.998** (p < 0.001, t = -19.05, R² = 0.932) — a 1% price increase associates with a ~3% drop in weekly volume. Month effects confirm the seasonality from Challenge A.

![Price-demand relationship](../outputs/price_elasticity_desodorante.png)

Prices cluster around ~6 discrete levels ($44–$60.67), consistent with fixed discount tiers; the fitted curve interpolates between them.

**Price simulator:** combines the elasticity model with the latest unit cost (~$49.70) to project demand/revenue/margin for any price in the observed range. At the low end (~$44-47), simulated margin is **negative** (-13% to -6%) — those prices historically occurred when unit cost was lower (~$45); evaluated against today's cost, they'd be unprofitable.

![Revenue and margin vs. price](../outputs/price_simulator_revenue_margin.png)

**Recommendation: price in the $55–$60 zone.** No interior optimum exists: revenue is maximized at the lowest observed price ($43.99, ~1,934 units/week) and margin ($) at the highest ($60.67, ~738 units/week, ~18% margin) — both range boundaries, not a sweet spot, as expected under elastic demand. The $55-60 zone keeps margin solidly positive (~14-18%, clear of the ~$50 break-even), overlaps with historically-charged prices (real customer acceptance, not extrapolated), and avoids the ~62% volume collapse at the top of the range. All estimates stay strictly within the observed range — no extrapolation.

**Risks:** (1) estimated from distributor sell-in, not consumer demand — forward buying likely inflates the measured sensitivity; (2) cost held fixed at today's level, which has already risen ~10% historically; (3) prices cluster at ~6 discrete levels, so the curve is more reliable near them than in the gaps; (4) only month is controlled — other factors (competitor actions, macro conditions) could bias the estimate; (5) SKU-specific, doesn't generalize to other products.

## 7. Challenge C: Promotional Uplift — Desodorante 150 ml A

**Promotions analyzed:** Combo Verano Desodorante 2 (Mar–May 2026, 17.1% discount, largest promo in the dataset) and Combo Cierre Trimestre Desodorante (Sep–Oct 2026, 21.1% discount, deepest of all 19 combos) — both on the same SKU as Challenges A/B.

**Method:** before/after baseline (average of 6 non-promotional weeks immediately preceding each promo, with no overlap with another Desodorante combo). Year-over-year wasn't used because the same calendar window in the prior year also carried a promotion. **Limitation:** assumes baseline demand would've stayed flat absent the promotion — doesn't capture trend/seasonality within the window, a bigger risk for the 69-day Verano 2 than the 27-day Cierre Trimestre.

| Metric | Verano 2 | Cierre Trimestre |
|---|---|---|
| Discount depth | 17.1% | 21.1% |
| Duration | 10 weeks | 4 weeks |
| Uplift (units) | +7,436 (+109.3%) | +3,574 (+96.5%) |
| Uplift per point of discount | 6.39 | 4.57 |
| Margin/unit (normal) | $10.40 | $10.43 |
| Margin/unit (during promo) | $0.49 | **-$1.79** |
| Margin from incremental units | **+$3,678** | **-$6,384** |
| Margin lost on baseline units | -$67,446 | -$45,233 |
| **Net incremental margin** | **-$63,768** | **-$51,617** |

Both promotions moved large unit volume, but both are net-negative once baseline cannibalization is counted. The key difference: Verano 2's *incremental* units were still profitable; Cierre Trimestre's were not, even before counting the baseline loss.

**Recommendation:**
- **Replicate (with adjustment): Verano Desodorante 2.** Incremental demand is real and profitable (+$3,678 on uplift alone). The fix is discount depth, not the mechanic — a shallower discount (elasticity ≈ -3.0) should still trigger meaningful uplift while protecting baseline margin.
- **Do not replicate: Cierre Trimestre Desodorante.** Even its incremental units sold at a loss — a structural problem, not a calibration one.
- **Root cause:** unit cost has risen ~10% over the observed history, but discount depths don't appear to have been re-calibrated against that. Reviewing discount tiers against *current* cost before each promotion is likely the highest-leverage, lowest-effort fix available.