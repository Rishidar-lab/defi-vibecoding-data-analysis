# [New MCP Server]: DefiLlama Risk Score MCP Tool

> **Template:** `mcp_server.yml`
> **Labels:** `enhancement`, `mcp-server`

---

## MCP Server Name
`defillama-risk-mcp-server`

## MCP Category
**Security/Risk Analysis** (primary) + **Price Data/Analytics** (secondary)

## MCP Description

Arbitrum DeFi TVL has experienced a **−56% drawdown** from its Oct 2025 peak ($1.52B as of May 2026). In this environment, blindly chasing the highest APY exposes users to uncompensated volatility and protocol risk. DefiLlama already exposes free, no-auth `sigma` (APY variability), `mu` (long-run mean), and `prediction_class` (ML direction forecast) fields on every pool — but no Vibekit MCP tool currently surfaces these as risk-adjusted rankings.

This contribution proposes:
**`defillama-risk-mcp-server`** — An MCP server that fetches Arbitrum pool data from `yields.llama.fi` and exposes risk-adjusted pool rankings using DefiLlama's own sigma/mu/prediction fields. No API key required.

*(Note: This MCP server is designed to power the companion `stablecoin-yield-router-agent` template proposed in a separate issue).*

## Data Source / API

| Field | Value |
|-------|-------|
| **Primary API** | `https://yields.llama.fi/pools` |
| **Chain TVL API** | `https://api.llama.fi/v2/historicalChainTvl/Arbitrum` |
| **Authentication** | None required (free public API) |
| **Rate limits** | No published limit; polite backoff implemented |
| **Documentation** | https://api-docs.defillama.com/ |
| **Reliability** | High — DefiLlama is the canonical DeFi data source |

## MCP Tools to Implement

**Tool 1: `get_risk_adjusted_pools`**
- **Description:** Fetches all Arbitrum stablecoin pools from DefiLlama, filters by TVL ≥ $5M / ilRisk=no / outlier=false, and returns them ranked by `apyMean30d / (1 + 100 * sigma)` with prediction penalty applied.
- **Input:** `{ min_tvl_usd?: number, chain?: string, stablecoin_only?: boolean }`
- **Output:** Array of `{ pool_id, project, symbol, apy_pct, apy_mean_30d, sigma, mu, prediction_class, risk_score, tvl_usd }`

**Tool 2: `get_chain_tvl_momentum`**
- **Description:** Fetches Arbitrum chain TVL history and returns the 30-day momentum percentage. Used to trigger the de-risk shift.
- **Input:** `{ chain?: string, lookback_days?: number }`
- **Output:** `{ chain, current_tvl_usd, tvl_30d_ago_usd, momentum_pct, de_risk_triggered: boolean }`

**Tool 3: `get_pool_risk_profile`**
- **Description:** Returns the full risk profile for a specific pool by pool ID.
- **Input:** `{ pool_id: string }`
- **Output:** `{ pool_id, project, symbol, sigma, mu, prediction_class, prediction_prob_pct, apy_history_30d, risk_tier: "low" | "medium" | "high" }`

## Agent Integration Examples

**Stablecoin Yield-Router Agent:**
1. Agent calls `get_chain_tvl_momentum` at each weekly rebalance.
2. If `de_risk_triggered = true` (momentum < −15%), agent calls `get_risk_adjusted_pools` and allocates 100% to the lowest-sigma pool.
3. Otherwise, agent allocates capital across top-ranked pools (capped at 40% per pool) using the risk-adjusted score from `get_risk_adjusted_pools`.

## Authentication Requirements
**No authentication required** — DefiLlama's public API is entirely free and unauthenticated.

## Configuration Options

```
Required:
  (none — fully public API)

Optional:
  MIN_TVL_USD=5000000       # Minimum pool TVL filter (default: $5M)
  DE_RISK_THRESHOLD=-0.15   # Chain TVL momentum threshold for de-risk (default: -15%)
```

## Testing Strategy

- **Unit tests:** Mock `yields.llama.fi` and `api.llama.fi` responses; verify ranking math, de-risk trigger logic, and Zod schema validation for all tool inputs/outputs.
- **Integration tests:** Live fetch from DefiLlama APIs; verify response parsing and error handling for network failures.
- **`pnpm test`:** All tests pass within the workspace.

## Backtest Evidence (Value Add)

A backtest of the risk-tiered routing strategy using this MCP's data vs. a naive highest-APY strategy (Jan 2025 – Jun 2026) shows the value of these risk metrics:

| Metric (14d Rebalance) | Risk-Tiered Router | Naive Highest-APY |
|------------------------|--------------------|-------------------|
| Realized APY (Net of Friction) | 4.21% | **7.19%** |
| APY Volatility (Weekly σ) | **2.22%** | 2.60% |
| Exposure-Weighted Sigma | **0.1323** | 0.1700+ |

**Depeg Stress Scenario:** When a simulated −3% NAV haircut was applied to the highest-sigma pool during a market contraction (Feb 2026), the naive strategy took a **−2.98% max drawdown**. The router, using the data from this MCP, had already de-risked and avoided the drawdown entirely (max DD −0.09%).

**Research repo:** https://github.com/Rishidar-lab/defi-vibecoding-data-analysis

## Pre-submission Checklist

- [x] I have searched existing issues to avoid duplicates
- [x] I have clearly described the MCP server's functionality
- [x] I have identified the data source and API requirements
- [x] I will wait for the Vibekit team to approve this issue before continuing to implementation
