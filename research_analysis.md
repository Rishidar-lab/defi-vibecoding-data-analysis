# Research Analysis — DeFi Vibecoding Competition & Arbitrum Dataset

*Prepared: 2026-06-10 · Status: working draft · Not financial advice*

## 1. Competition landscape and selection

### 1.1 Opportunities surveyed

| Program | Official URL | Status | Registration | Submission format | Deadline | Reward | Eligible themes | Protocol support |
|---|---|---|---|---|---|---|---|---|
| **Arbitrum Trailblazer 2.0 (Vibekit)** | https://blog.arbitrum.foundation/trailblazer-2-0-1m-in-grants-to-power-agentic-defi-on-arbitrum/ | Open (retroactive program, launched Jun 2025; described as ongoing in Arbitrum Builder's Block #001, Aug 2025, and still referenced in the Vibekit repo README as of this writing). No published end date — re-verify before submitting. | GitHub account; submission form linked from the blog post; grant payout will require a wallet and likely KYC with the Arbitrum Foundation | GitHub PR/repo into EmberAGI/arbitrum-vibekit (community dir) + submission form | None published | Up to **$10k per submission** from a $1M pool | Deployed DeFi agents with profitable/novel strategies; agent templates; modular add-ons; integrations; backtesting suites; frontend components (trade history, P&L); Farcaster mini-apps | Pendle, GMX, Aave, Camelot at launch; Hyperbolic, Playgrounds, Eliza, Trendmoon, Allora as tools |
| **Ember bounty board (Vibekit Contribution Center)** | https://github.com/orgs/EmberAGI/projects/13 | Open (118 open issues on the repo; issue-first workflow per CONTRIBUTIONS.md) | GitHub account only | GitHub issue → approval → PR referencing the issue | Rolling | Per-bounty; contributions "might qualify for the Trailblazer Fund 2.0" per repo README | Bug fixes, docs, protocol plugins (Ember Plugin System), MCP tools, agent templates, UI | Same as Vibekit |
| Encode AI London 2026 (Vibe Coding / Onchain AI tracks) | https://www.encodeclub.com/programmes/ai-london-2026 | Closed (Mar 2026) | Event registration | Pitch deck + repo | Passed | Hardware + credits | AI agents, vibe coding, onchain AI | Generic |
| BridgeMind Vibeathon | https://www.bridgemind.ai/vibeathon | Open (rolling) | None stated | Public GitHub repo + 3–5 min demo video | Rolling | $5k pool (BTC) | Tools for agentic coders (MCP servers, CLI, extensions) — not DeFi-specific | None |

### 1.2 Selected target

**Arbitrum Trailblazer 2.0 via Vibekit contributions.** Rationale: highest-confidence official sourcing (Arbitrum Foundation blog + Vibekit repo), open/retroactive with no deadline pressure, GitHub-native submission, $10k/submission cap with a $1M pool, explicit priority for *complex DeFi strategy templates and backtesting suites* — which is exactly what a data-driven strategy repo feeds into — and confirmed support for the protocols this dataset targets (Aave, GMX, Pendle, Camelot). Feasible solo. The Ember bounty board is the tactical entry point: the CONTRIBUTIONS.md workflow requires opening an issue and getting team approval **before** building, and warns that duplicate or plugin-bypassing contributions are not integrated or rewarded.

Submission-path notes (verified from CONTRIBUTIONS.md):
1. Open an issue (agent template / MCP tool / protocol integration template) and wait for team approval.
2. Fork EmberAGI/arbitrum-vibekit, build in `typescript/community/`, follow TESTING.md, run `pnpm test`.
3. PR referencing the issue; review acknowledged in 2–3 days, feedback within a week.
4. Separately submit the deployed agent/template through the Trailblazer form linked from the Foundation blog post.

## 2. Dataset methodology

### 2.1 Sources (all free, no-auth, citing DefiLlama)

| Dataset | Endpoint | Format | Auth |
|---|---|---|---|
| Arbitrum chain TVL history | `https://api.llama.fi/v2/historicalChainTvl/Arbitrum` | JSON | None |
| All-pool yield snapshot (APY, TVL, sigma, mu, ML predictions, IL risk) | `https://yields.llama.fi/pools` | JSON | None |
| Per-pool APY/TVL history | `https://yields.llama.fi/chart/{pool_id}` | JSON | None |
| Token price history | `https://coins.llama.fi/chart/{coins}` | JSON | None |
| Protocol fees/revenue | `https://api.llama.fi/summary/fees/{protocol}` | JSON | None |

Documented but not used here: official subgraphs (Aave v3 Arbitrum, GMX synthetics-stats, Pendle backend API at `api-v2.pendle.finance`), Camelot API, Dune (needs API key — flagged for user action if SQL-level granularity is wanted), and direct Arbitrum RPC reads (e.g., Aave `getReserveData`) for trust-minimized verification.

### 2.2 What was collected vs. what the pipeline regenerates

This environment has restricted egress, so two **seed files** were transcribed from live API fetches made on 2026-06-10:

- `data/arbitrum_chain_tvl_monthly.csv` — month-start TVL points downsampled from the full daily series (Sep 2021 → 27 May 2026).
- `data/arbitrum_yields_snapshot.csv` — the Arbitrum pools present in the top-TVL slice of `/pools` (truncation limited coverage to pools ≥ ~$75M TVL; GMX/Pendle/Camelot pools sit below that cutoff and are **not** in the seed file).

`scripts/fetch_dataset.py` regenerates the complete, untruncated dataset (full daily chain TVL, *all* Arbitrum pools, top-25 pool APY/TVL histories for the Vibekit protocols, merged long-format `data/arb_vibecoding_dataset.csv` with the schema `timestamp, asset, protocol, chain, apy_pct, tvl_usd, apy_vol_30d, sigma, mu, stablecoin, ilRisk, exposure, prediction_class`). Run it on a machine with open internet before any modeling.

## 3. Exploratory findings (from seed data)

**Chain TVL regime.** Arbitrum DeFi TVL peaked at ~$3.44B in the sampled series (Oct 2025) and stands at ~$1.52B as of 27 May 2026 — a **−56% drawdown from the cycle peak**, with −37% over 12 months and −46% over 6 months. The historical max drawdown in the series is **−72%** (2021 peak → mid-2022 trough). Excluding the launch bootstrap, monthly TVL changes average +0.4% with a 16.1% standard deviation; the worst sampled month was −33.8% (Feb 2026) and the best +59.5%. Any strategy or backtest built on this data must assume regime shifts of this magnitude are normal, not tail events.

**Yield structure.** Among the highest-TVL Arbitrum pools captured: stablecoin savings rates cluster tightly at **3.6% APY** (Sky sUSDS and Spark USDS, ~$359M each) with extremely low APY volatility (sigma 0.001–0.007) and "Stable/Up" ML predictions at 72–88% confidence. The outlier is USD.AI's sUSDAI at **8.07% APY** ($289M TVL) — but it carries a 30-day unlock, ~7× the APY sigma of the savings rates, and a "Down" prediction, a textbook illustration that excess stablecoin yield prices in liquidity and sustainability risk. Blue-chip collateral supply on Aave v3 Arbitrum (WBTC 0.05%, weETH ~0%) confirms supply-side lending yield on majors is effectively zero — those markets exist for borrowing/looping, not passive yield.

**Initial strategy insights for a Vibekit agent.**
1. A *risk-tiered stablecoin yield router* (3.6% risk-free-ish tier vs. higher-sigma 6–8% tier, sized by sigma, prediction class, exposure, and unlock terms) matches the data and Trailblazer's "make yield searching 10x easier" framing.
2. The −56% TVL drawdown argues for agents with explicit *de-risking triggers* tied to chain/pool TVL momentum, not just APY chasing.
3. DefiLlama's per-pool `sigma`/`mu`/`predictions` fields are an underused, free risk-scoring layer that an agent template can consume directly — a defensible contribution angle (e.g., an MCP tool exposing risk-adjusted pool rankings).
4. Avoid high-APY DEX LP pools flagged `outlier: true` or `ilRisk: yes` with triple-digit headline APYs (observed cross-chain in the snapshot); these are fee spikes, not sustainable yield.

## 4. Risks and limitations

- **Data gaps:** the seed yield snapshot omits sub-$75M pools (all GMX/Pendle/Camelot pools) due to sandbox truncation; the merged dataset must be regenerated with the script before drawing protocol-level conclusions. Monthly TVL downsampling understates daily volatility and drawdown depth.
- **Survivorship/measurement bias:** DefiLlama TVL excludes double counting and liquid staking by methodology choice; APY fields mix base and reward emissions whose USD value decays with token price.
- **Model bias:** DefiLlama prediction classes are a third-party ML output with unpublished calibration — treat as a feature, not ground truth.
- **Market risk:** the current −56% TVL regime can deepen; past APY is not predictive.
- **Smart-contract & depeg risk:** stablecoin "savings" rates depend on issuer solvency and peg integrity.
- **Regulatory:** grant payouts may require KYC; recipients are responsible for local tax/legal treatment (relevant for an India-based solo participant). No mainnet transactions are made by this repo; all data access is read-only.
- **Program risk:** Trailblazer 2.0 has no published deadline; funds could be exhausted or terms revised — verify on the official blog and Discord before investing build time.

## 5. Next steps

1. Run `scripts/fetch_dataset.py` on an unrestricted machine; commit the full dataset.
2. Open a Vibekit issue proposing the contribution (e.g., "risk-adjusted yield-routing agent template + DefiLlama risk MCP tool") and wait for approval per CONTRIBUTIONS.md.
3. Backtest the stablecoin router on `arbitrum_pool_histories.csv`; report Sharpe-style risk-adjusted yield and drawdown behavior across the Feb–May 2026 regime.
4. Build the template in `typescript/community/`, test per TESTING.md, PR, then file the Trailblazer submission form.

## Bibliography

1. Arbitrum Foundation, "Trailblazer 2.0: $1M in Grants to Power Agentic DeFi on Arbitrum," Jun 2025. https://blog.arbitrum.foundation/trailblazer-2-0-1m-in-grants-to-power-agentic-defi-on-arbitrum/
2. Arbitrum Foundation, Grants page. https://arbitrum.foundation/grants
3. Arbitrum Foundation, "The Arbitrum Builder's Block #001," Aug 2025 ("Trailblazer 2.0 is still ongoing"). https://blog.arbitrum.foundation/the-arbitrum-builders-block-001/
4. EmberAGI, arbitrum-vibekit repository and CONTRIBUTIONS.md. https://github.com/EmberAGI/arbitrum-vibekit
5. EmberAGI, Vibekit Contribution Center (bounty board). https://github.com/orgs/EmberAGI/projects/13
6. Ember AI, "Introducing Arbitrum Vibekit & the Trailblazer Fund 2.0," Jun 2025. https://www.emberai.xyz/blog/introducing-arbitrum-vibekit-and-the-trailblazer-fund-2-0
7. DefiLlama API documentation. https://api-docs.defillama.com/ — data fetched 2026-06-10 from api.llama.fi and yields.llama.fi (free endpoints, no auth). Data © DefiLlama, cited per their FAQ request.
