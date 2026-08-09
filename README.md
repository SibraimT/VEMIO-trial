# VEMIO, Technical Case

Demand forecasting, price elasticity, and promotional uplift analysis for a CPG client.

## Repo structure

```
vemio_case/
├── data/               # raw dataset + processed data
├── src/                # reusable functions (data cleaning)
├── notebooks/          # analysis notebook (single file, see below)
├── outputs/            # charts and result tables
├── docs/               # findings document and business recommendations
├── requirements.txt
└── README.md
```

## How to reproduce

1. Clone the repo.
2. Create an environment and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Place the csv file inside `data/`
4. Run `notebooks/vemio_case_analysis.ipynb` from top to bottom. The notebook
   covers, in order, data cleaning, EDA, and the three challenges (A: demand
   forecasting, B: price elasticity, C: promotional uplift).

## Challenges

- **Challenge A — Demand Forecasting**: weekly demand projection for selected SKUs, 8-12 weeks ahead, with time-based validation (no information leakage).
- **Challenge B — Price Elasticity**: demand-price sensitivity estimate + revenue/margin simulator.
- **Challenge C — Promotional Uplift**: incremental sales from at least 2 past promotions.

See `docs/findings.md` (full technical version) or the PDF `VEMIO_Findings_Sibraim_Tejeda.pdf` in `docs/` (1-2 page summary) for methodology, assumptions, and business recommendations.