# [New Agent Template]: Risk-Tiered Stablecoin Yield-Router Agent

> **Template:** `agent_template.yml`
> **Labels:** `enhancement`, `agent-template`

---

## Agent Name
`stablecoin-yield-router-agent`

## Agent Description

Arbitrum DeFi TVL has experienced a **−56% drawdown** from its Oct 2025 peak. In this environment, blindly chasing the highest APY exposes users to uncompensated volatility and protocol risk.

This agent template automatically allocates capital across Arbitrum stablecoin pools using a risk-tiered strategy. Instead of just picking the highest APY, it uses DefiLlama's `sigma` (APY variability) and `prediction_class` (ML direction forecast) to score pools on a risk-adjusted basis. It also features a macro "de-risk" trigger that shifts all capital to the safest pool when Arbitrum chain TVL momentum drops sharply.

*(Note: This agent relies on the `defillama-risk-mcp-server` proposed in companion issue #666).*

## Required Protocols
- **Primary protocols:** Any Arbitrum stablecoin pool indexed by DefiLlama (e.g., Aave V3, Compound V3, Fluid, Morpho).
- **Required MCP:** `defillama-risk-mcp-server` (for risk scoring and chain TVL momentum).

## Automation Level
**Automated** - Agent executes based on conditions (e.g., rebalances every 14 days, or immediately if the de-risk trigger fires).

## Code Architecture

**Skills & Tools structure:**
- `rebalancePortfolio`: Calculates current holdings, calls MCP to get target allocations, and executes swaps/deposits.
- `checkDeRiskTrigger`: Calls MCP to check chain TVL momentum. If triggered, overrides target allocation to 100% lowest-sigma pool.

**Agent components:**
- Uses the standard Vibekit wallet context provider for transaction execution.
- Scheduled automation hook (e.g., cron job every 14 days) to trigger rebalancing.

**Integration patterns:**
- Uses the `defillama-risk-mcp-server` for off-chain data.
- Uses standard ERC-4626 / protocol-specific adapters (already in Vibekit) for on-chain execution.

## Testing Requirements

- **Unit tests:** Mock the MCP responses and verify the agent calculates the correct swap/deposit amounts to reach the target allocation.
- **Integration tests:** Run against an Arbitrum fork (e.g., Anvil) to verify deposit/withdraw transactions succeed.
- **Live testing:** Deploy with a small amount of USDC to verify the scheduled rebalance works on mainnet.

## Additional Information (Backtest Evidence)

A backtest of this agent's logic vs. a naive highest-APY strategy (Jan 2025 – Jun 2026) shows the value of the risk-tiered approach:

| Metric (14d Rebalance) | Risk-Tiered Router | Naive Highest-APY |
|------------------------|--------------------|-------------------|
| Realized APY (Net of Friction) | 4.21% | **7.19%** |
| APY Volatility (Weekly σ) | **2.22%** | 2.60% |
| Exposure-Weighted Sigma | **0.1323** | 0.1700+ |

**Depeg Stress Scenario:** When a simulated −3% NAV haircut was applied to the highest-sigma pool during a market contraction (Feb 2026), the naive strategy took a **−2.98% max drawdown**. The router had already de-risked via the chain TVL trigger and avoided the drawdown entirely (max DD −0.09%).

**Research repo:** https://github.com/Rishidar-lab/defi-vibecoding-data-analysis

## Pre-submission Checklist

- [x] I have searched existing issues and templates to avoid duplicates
- [x] I have clearly described the agent's purpose and functionality
- [x] I have identified the required protocols and integrations
- [x] I understand this agent will be created in the typescript/community/ directory
- [x] I will wait for the Vibekit team to approve this issue before continuing to implementation
