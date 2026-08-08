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
*(pendiente — lo llenamos en el siguiente paso)*

### Missing product_cost (~0.04%)
*(pendiente)*