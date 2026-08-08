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

### Missing product_cost (~0.04%)
*(pendiente)*