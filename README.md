# defi-vibecoding-data-analysis

Arbitrum DeFi dataset and research for a risk-tiered stablecoin yield-router strategy, contributed to the [Arbitrum Trailblazer 2.0](https://blog.arbitrum.foundation/trailblazer-2-0-1m-in-grants-to-power-agentic-defi-on-arbitrum/) program via [EmberAGI/arbitrum-vibekit](https://github.com/EmberAGI/arbitrum-vibekit).

## Repository Structure

```
.
├── data/                          # Datasets
│   ├── arbitrum_chain_tvl_daily.csv      # Daily Arbitrum chain TVL (Jan 2025–Jun 2026)
│   ├── arbitrum_chain_tvl_monthly.csv    # Monthly seed TVL data
│   ├── arbitrum_pools_snapshot.csv       # Stablecoin pool snapshot with sigma/mu/prediction
│   ├── arbitrum_pool_histories.csv       # Per-pool APY history
│   ├── arbitrum_yields_snapshot.csv      # Seed yields snapshot
│   └── arb_vibecoding_dataset.csv        # Merged analysis dataset
├── docs/                          # Reports and documentation
│   ├── backtest_report.md                # Backtest results with risk metrics
│   ├── research_analysis.md              # Research analysis and findings
│   └── img/                             # Chart images
├── scripts/                       # Data pipeline and analysis scripts
│   ├── fetch_dataset.py                  # Regenerates all datasets from DefiLlama API
│   └── backtest.py                       # Risk-tiered router backtest (v2)
├── .env.example                   # Environment variable template
├── LICENSE                        # MIT License
└── README.md
```

## Backtest

The risk-tiered yield-router strategy was backtested against a naive highest-APY strategy on Arbitrum stablecoin pools (Jan 2025 – Jun 2026).

Key results (14d rebalance, net of 5 bps friction per leg):

| Metric | Risk-Tiered Router | Naive Highest-APY |
|--------|--------------------|-------------------|
| Realized APY (Net of Friction) | 4.21% | **7.19%** |
| APY Volatility (Weekly σ) | **2.22%** | 2.60% |
| Exposure-Weighted Sigma | **0.1323** | 0.1700+ |
| Depeg Stress Max Drawdown | **−0.09%** | −2.98% |

Full methodology, charts, and honest conclusions: **[docs/backtest_report.md](docs/backtest_report.md)**

## Vibekit Contribution

This research supports two open issues on [EmberAGI/arbitrum-vibekit](https://github.com/EmberAGI/arbitrum-vibekit):

- **[#666 — New MCP Server: DefiLlama Risk Score MCP Tool](https://github.com/EmberAGI/arbitrum-vibekit/issues/666)**
- **[#667 — New Agent Template: Risk-Tiered Stablecoin Yield-Router Agent](https://github.com/EmberAGI/arbitrum-vibekit/issues/667)**

## Data Sources

All data is fetched from the [DefiLlama public API](https://api-docs.defillama.com/) — no authentication required. Read-only data access; no mainnet transactions.

## Reproducing the Dataset

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install requests pandas matplotlib
python3 scripts/fetch_dataset.py  # regenerates data/
python3 scripts/backtest.py       # regenerates docs/backtest_report.md and docs/img/
```

## Disclaimers

Research only — not financial advice. No secrets are committed; environment variables belong in `.env` (see `.env.example`).

MIT License.
